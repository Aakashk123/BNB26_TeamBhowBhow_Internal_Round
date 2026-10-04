import hashlib
import io
import json
import secrets
import time
import zipfile
from collections import OrderedDict, defaultdict, deque
from contextlib import asynccontextmanager
from threading import RLock

from eth_account import Account
from eth_account._utils.legacy_transactions import Transaction
from eth_account.messages import encode_defunct
from eth_account.typed_transactions import TypedTransaction
from eth_utils import keccak
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from hexbytes import HexBytes
from pydantic import TypeAdapter, ValidationError
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.formparsers import MultiPartParser

from app.api import services
from app.api.schemas import ActorIn, AdminIn, CorroborationIn, DisclosureIn, EventIn, HashRequest, Op, Params, Report
from app.api.transform import apply
from app.certificate import builder
from app.chain.client import Chain, get_chain
from app.config import settings
from app.core.canonical import canonical, digest
from app.core.commitments import disclose
from app.core.eip712 import ZERO, event_hash, recover_witness, sign_event
from app.core.pixelhash import MAX_BYTES
from app.db import audit
from app.db.models import Actor, Certificate, Corroboration, Event, VerificationReport, Version
from app.db.session import get_db

MultiPartParser.spool_max_size = 26 * 1024 * 1024
cache_lock = RLock()
transient: OrderedDict[str, tuple[float, str, dict]] = OrderedDict()
limiter: dict[str, deque] = defaultdict(deque)


@asynccontextmanager
async def lifespan(app):
    yield
    transient.clear()
    limiter.clear()


app = FastAPI(
    title="ModelLedger",
    version="1.0.0",
    lifespan=lifespan,
    description="Evidence-based image provenance. A signature is a claim, not proof of model execution.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Dev-Api-Key"],
)


class BodyLimit:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        length = dict(scope.get("headers", [])).get(b"content-length", b"0")
        try:
            if int(length) > 27 * 1024 * 1024:
                return await JSONResponse(
                    {"error": {"code": "INPUT_TOO_LARGE", "message": "Request exceeds 27 MiB"}}, 413
                )(scope, receive, send)
        except ValueError:
            return await JSONResponse({"error": {"code": "BAD_LENGTH", "message": "Invalid Content-Length"}}, 400)(
                scope, receive, send
            )
        size = 0

        async def limited():
            nonlocal size
            message = await receive()
            size += len(message.get("body", b""))
            if size > 27 * 1024 * 1024:
                raise HTTPException(413, "Request exceeds 27 MiB")
            return message

        await self.app(scope, limited, send)


app.add_middleware(BodyLimit)


@app.middleware("http")
async def guard(request, call_next):
    now = time.monotonic()
    ip = request.client.host if request.client else "unknown"
    if len(limiter) > 10000:
        for old in list(limiter):
            if not limiter[old] or limiter[old][-1] < now - 60:
                del limiter[old]
    bucket = limiter[ip]
    while bucket and bucket[0] < now - 60:
        bucket.popleft()
    if len(bucket) >= settings.rate_limit_per_minute:
        return JSONResponse(
            {"error": {"code": "RATE_LIMITED", "message": "Try again shortly"}}, 429, headers={"Retry-After": "60"}
        )
    bucket.append(now)
    session = request.cookies.get("ml_session", "")
    if len(session) != 64 or any(c not in "0123456789abcdef" for c in session):
        session = secrets.token_hex(32)
    request.state.owner = hashlib.sha256(session.encode()).hexdigest()
    response = await call_next(request)
    response.set_cookie(
        "ml_session", session, httponly=True, secure=settings.env == "production", samesite="strict", max_age=30 * 86400
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(HTTPException)
async def http_error(request, exc):
    return JSONResponse({"error": {"code": "REQUEST_FAILED", "message": str(exc.detail)}}, exc.status_code)


@app.exception_handler(ValidationError)
@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    return JSONResponse(
        {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request fields are invalid",
                "fields": [".".join(map(str, e["loc"])) for e in exc.errors()],
            }
        },
        422,
    )


@app.exception_handler(ValueError)
async def value_error(request, exc):
    return JSONResponse({"error": {"code": "INVALID_EVIDENCE", "message": str(exc)[:200]}}, 422)


@app.exception_handler(IntegrityError)
async def conflict_error(request, exc):
    return JSONResponse(
        {"error": {"code": "CONFLICT", "message": "A concurrent registration already exists; retry the request"}}, 409
    )


def store_report(db, owner, report):
    if report["saved"]:
        db.add(VerificationReport(id=report["report_id"], owner=owner, report=report))
        db.commit()
    else:
        with cache_lock:
            while transient and (next(iter(transient.values()))[0] < time.monotonic() - 1800 or len(transient) >= 1000):
                transient.popitem(last=False)
            transient[report["report_id"]] = (time.monotonic(), owner, report)
    return report


def load_report(db, owner, report_id):
    with cache_lock:
        item = transient.get(report_id)
    if item and item[1] == owner and item[0] >= time.monotonic() - 1800:
        return item[2]
    row = db.get(VerificationReport, report_id)
    if row and row.owner == owner:
        return row.report
    raise HTTPException(404, "Report not found in this browser session; unsaved reports expire after 30 minutes")


def require_chain(chain):
    try:
        if chain.ready():
            return
    except Exception:
        pass
    raise HTTPException(503, "Configured chain is unavailable")


@app.get("/api/v1/health")
def health(db: Session = Depends(get_db), chain: Chain = Depends(get_chain)):
    db.execute(text("SELECT 1"))
    try:
        ready = chain.ready()
    except Exception:
        ready = False
    return {
        "status": "healthy" if ready else "degraded",
        "database": True,
        "chain": ready,
        "demo": settings.enable_demo,
        "simulated_evidence_allowed": settings.allow_simulated,
        "engine_version": "1.0.0",
    }


@app.post("/api/v1/verify", response_model=Report)
def verify_file(
    request: Request,
    file: UploadFile = File(...),
    save_history: bool = Form(False),
    db: Session = Depends(get_db),
    chain: Chain = Depends(get_chain),
):
    data = file.file.read(MAX_BYTES + 1)
    info, _ = services.fingerprint(data)
    report = services.verify(db, info, chain, save_history)
    return store_report(db, request.state.owner, report)


@app.post("/api/v1/verify/by-hash", response_model=Report)
def verify_hash(body: HashRequest, request: Request, db: Session = Depends(get_db), chain: Chain = Depends(get_chain)):
    info = {"sha256": body.sha256.lower(), "c2pa": {"state": "NOT_CHECKED", "valid": None, "signer_trusted": False}}
    report = services.verify(db, info, chain, body.save_history)
    return store_report(db, request.state.owner, report)


@app.post("/api/v1/register")
def register(
    file: UploadFile = File(...),
    declared_origin: str | None = Form(None, max_length=120),
    save_thumbnail: bool = Form(False),
    signed_event: str | None = Form(None, max_length=32768),
    db: Session = Depends(get_db),
    chain: Chain = Depends(get_chain),
):
    incoming = EventIn.model_validate_json(signed_event) if signed_event else None
    lineage_id = None
    if incoming and incoming.payload.parentEventIds:
        parent = db.get(Event, incoming.payload.parentEventIds[0])
        if parent:
            lineage_id = db.get(Version, parent.output_version).lineage_id
    v = services.register(db, file.file.read(MAX_BYTES + 1), declared_origin, save_thumbnail, lineage_id)
    eid = services.add_event(db, incoming, chain) if incoming else None
    db.commit()
    return {"version": services.version_dict(v), "event_hash": eid, "claim": "SIGNED" if eid else "SELF_ASSERTED"}


@app.post("/api/v1/events")
def events(body: EventIn, db: Session = Depends(get_db), chain: Chain = Depends(get_chain)):
    eid = services.add_event(db, body, chain)
    db.commit()
    return {"event_hash": eid}


@app.post("/api/v1/events/{event_id}/corroborations")
def corroborate(event_id: str, body: CorroborationIn, db: Session = Depends(get_db), chain: Chain = Depends(get_chain)):
    require_chain(chain)
    if not db.get(Event, event_id):
        raise HTTPException(404, "Event not found")
    evidence = body.evidence.model_dump(exclude_none=True)
    evidence_hash = digest(evidence)
    signer = recover_witness(event_id, body.kind, evidence_hash, services.scope_for(chain), body.signature)
    match = any(
        c["signer"].lower() == signer.lower() and c["kind"] == body.kind and c["evidence_hash"] == evidence_hash
        for c in chain.witness_records(event_id)
    )
    if not match:
        raise ValueError("Corroboration must first be anchored by an approved independent witness")
    db.add(
        Corroboration(
            event_hash=event_id,
            kind=body.kind,
            evidence_hash=evidence_hash,
            evidence=evidence,
            signature=body.signature,
        )
    )
    audit.append(db, "CORROBORATION", event_id)
    db.commit()
    return {"event_hash": event_id, "evidence_hash": evidence_hash}


@app.get("/api/v1/events/{event_id}")
def event_get(event_id: str, db: Session = Depends(get_db), chain: Chain = Depends(get_chain)):
    record = db.get(Event, event_id)
    if not record:
        raise HTTPException(404, "Event not found")
    try:
        anchor = chain.anchor(event_id)
    except Exception:
        anchor = None
    return {
        "event_hash": record.event_hash,
        "payload": record.payload,
        "params": record.params,
        "signature": record.signature,
        "anchor": anchor,
        "gateway_replay": record.gateway_replay,
    }


@app.get("/api/v1/actors")
def actors(db: Session = Depends(get_db), chain: Chain = Depends(get_chain)):
    rows = []
    for a in db.scalars(select(Actor).order_by(Actor.name).limit(1000)):
        entry = {c.name: getattr(a, c.name) for c in Actor.__table__.columns}
        try:
            entry.update(chain.actor(a.actor_id))
            entry["chain_checked"] = True
        except Exception:
            entry["chain_checked"] = False
        rows.append(entry)
    return rows


@app.post("/api/v1/actors")
def actor_register(body: ActorIn, db: Session = Depends(get_db), chain: Chain = Depends(get_chain)):
    require_chain(chain)
    info = chain.actor(body.actor_id)
    if info["status"] == 0:
        raise ValueError("Actor must self-register on the registry contract first")
    signed = {
        "actor_id": body.actor_id,
        "name": body.name,
        "provider": body.provider,
        "kind": body.kind,
        "domain": services.scope_for(chain),
    }
    signer = Account.recover_message(encode_defunct(primitive=canonical(signed)), signature=body.signature)
    if signer.lower() != info["signer_address"].lower():
        raise ValueError("Actor profile must be signed by its registered owner")
    if db.get(Actor, body.actor_id):
        raise HTTPException(409, "Actor profile already exists")
    db.add(Actor(actor_id=body.actor_id, name=body.name, provider=body.provider, kind=body.kind, **info))
    audit.append(db, "REGISTER_ACTOR", body.actor_id)
    db.commit()
    return {"actor_id": body.actor_id, **info}


@app.post("/api/v1/actors/{actor_id}/{operation}")
def actor_admin(
    actor_id: str,
    operation: str,
    body: AdminIn,
    request: Request,
    db: Session = Depends(get_db),
    chain: Chain = Depends(get_chain),
):
    require_chain(chain)
    if operation not in ("approve", "revoke"):
        raise HTTPException(404, "Unknown operation")
    function = (
        chain.contract.functions.approveActor(actor_id)
        if operation == "approve"
        else chain.contract.functions.revokeActor(actor_id, body.effective_from or int(time.time()))
    )
    if (
        settings.env == "dev"
        and settings.dev_api_key
        and secrets.compare_digest(request.headers.get("X-Dev-Api-Key", ""), settings.dev_api_key)
    ):
        tx = chain.send(function, settings.registrar_key)
    elif body.raw_transaction:
        # Production users sign the exact transaction in their wallet. Contract access control and chain nonce prevent replay.
        recovered = Account.recover_transaction(body.raw_transaction)
        if not chain.contract.functions.hasRole(chain.contract.functions.REGISTRAR_ROLE().call(), recovered).call():
            raise HTTPException(403, "Transaction signer does not hold REGISTRAR_ROLE")
        raw = HexBytes(body.raw_transaction)
        decoded = (
            TypedTransaction.from_bytes(raw).as_dict() if raw[0] <= 0x7F else Transaction.from_bytes(raw).as_dict()
        )
        destination = "0x" + bytes(decoded["to"]).hex()
        calldata = "0x" + bytes(decoded["data"]).hex()
        chain_id = decoded.get("chainId")
        if chain_id is None:
            chain_id = (decoded["v"] - 35) // 2
        if (
            destination.lower() != chain.contract.address.lower()
            or calldata.lower() != function._encode_transaction_data().lower()
            or chain_id != settings.chain_id
            or decoded.get("value", 0)
        ):
            raise ValueError("Sign the exact requested operation for this registry and chain")
        tx = "0x" + chain.web3.eth.send_raw_transaction(body.raw_transaction).hex().removeprefix("0x")
        receipt = chain.web3.eth.wait_for_transaction_receipt(tx)
        sent = chain.web3.eth.get_transaction(tx)
        if (
            sent.to.lower() != chain.contract.address.lower()
            or sent.input.hex().removeprefix("0x") != function._encode_transaction_data().removeprefix("0x")
            or receipt.status != 1
        ):
            raise ValueError("Signed transaction did not execute the requested registry operation")
    else:
        raise HTTPException(403, "A registrar-signed transaction is required")
    audit.append(db, operation.upper() + "_ACTOR", actor_id)
    db.commit()
    return {"transaction": tx, "actor": chain.actor(actor_id)}


@app.get("/api/v1/versions/{version_id}")
def version_get(version_id: str, db: Session = Depends(get_db)):
    v = db.get(Version, version_id)
    if not v:
        raise HTTPException(404, "Version not found")
    return services.version_dict(v)


@app.get("/api/v1/versions")
def versions(db: Session = Depends(get_db)):
    return [
        services.version_dict(v) for v in db.scalars(select(Version).order_by(Version.created_at.desc()).limit(100))
    ]


@app.get("/api/v1/lineages/{lineage_id}/graph")
def lineage_graph(lineage_id: str, db: Session = Depends(get_db), chain: Chain = Depends(get_chain)):
    versions = list(db.scalars(select(Version).where(Version.lineage_id == lineage_id)))
    if not versions:
        raise HTTPException(404, "Lineage not found")
    nodes, edges = {}, {}
    for version in versions:
        report = services.verify(db, services.version_dict(version), chain)
        for node in report["graph"]["nodes"]:
            nodes[node["id"]] = node
        for edge in report["graph"]["edges"]:
            edges[edge["id"]] = edge
    return {"nodes": list(nodes.values()), "edges": list(edges.values())}


@app.get("/api/v1/reports/{report_id}", response_model=Report)
def report_get(report_id: str, request: Request, db: Session = Depends(get_db)):
    return load_report(db, request.state.owner, report_id)


@app.get("/api/v1/history")
def history(request: Request, db: Session = Depends(get_db)):
    return [
        r.report
        for r in db.scalars(
            select(VerificationReport)
            .where(VerificationReport.owner == request.state.owner)
            .order_by(VerificationReport.created_at.desc())
            .limit(100)
        )
    ]


@app.get("/api/v1/reports/{report_id}/certificate")
def certificate(report_id: str, request: Request, format: str = "json", db: Session = Depends(get_db)):
    report = load_report(db, request.state.owner, report_id)
    cert = db.scalar(select(Certificate).where(Certificate.report_id == report_id)) if report["saved"] else None
    envelope = cert.envelope if cert else builder.build(report, settings.issuer_key)
    if not cert and report["saved"]:
        db.add(Certificate(id=envelope["document"]["certificate_id"], report_id=report_id, envelope=envelope))
        db.commit()
    if format == "pdf":
        return Response(
            builder.pdf(envelope),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{report_id}.pdf"'},
        )
    if format != "json":
        raise HTTPException(422, "Format must be json or pdf")
    return JSONResponse(envelope, headers={"Content-Disposition": f'attachment; filename="{report_id}.json"'})


@app.get("/.well-known/modelledger-issuer.json")
def issuer(chain: Chain = Depends(get_chain)):
    if not settings.issuer_key:
        raise HTTPException(503, "Issuer not configured")
    address = Account.from_key(settings.issuer_key).address
    try:
        anchored = chain.contract.functions.issuer().call().lower() == address.lower()
    except Exception:
        anchored = False
    return {"issuer": address, "algorithm": "EIP-191(SHA-256(RFC8785))", "on_chain": anchored}


@app.post("/api/v1/certificates/verify")
def certificate_verify(body: dict, chain: Chain = Depends(get_chain)):
    info = issuer(chain)
    return {
        "valid": builder.verify(body, info["issuer"]),
        "issuer": info["issuer"],
        "issuer_on_chain": info["on_chain"],
        "scope": "Historical signed report; rerun image verification for current revocation status",
    }


@app.post("/api/v1/disclosures/verify")
def disclosure(body: DisclosureIn, db: Session = Depends(get_db), chain: Chain = Depends(get_chain)):
    require_chain(chain)
    event = db.get(Event, body.event_hash)
    if not event or not chain.anchor(body.event_hash)["block_time"]:
        raise HTTPException(404, "Anchored event not found")
    if event_hash(event.payload, services.scope_for(chain)) != body.event_hash:
        raise ValueError("EVENT_HASH_MISMATCH")
    return {
        "valid": disclose(body.field, body.value, body.salt, body.proof, event.payload["privateRoot"]),
        "stored": False,
    }


@app.get("/api/v1/audit/verify")
def audit_verify(db: Session = Depends(get_db)):
    return audit.verify(db)


@app.post("/api/v1/transform")
def transform(
    file: UploadFile = File(...),
    operations: str = Form(..., max_length=8192),
    db: Session = Depends(get_db),
    chain: Chain = Depends(get_chain),
):
    require_chain(chain)
    if not settings.gateway_key:
        raise HTTPException(503, "Transform gateway key is not configured")
    ops = TypeAdapter(list[Op]).validate_json(operations)
    if not 1 <= len(ops) <= 16:
        raise ValueError("Use one to sixteen ordered operations")
    data = file.file.read(MAX_BYTES + 1)
    info, _ = services.fingerprint(data)
    snap, policy, policy_hash = services.snapshot(db, info, chain)
    if not snap["version"] or not snap["heads"]:
        raise ValueError("Input must be bound to a registered signed version")
    report = services.verify(db, info, chain)
    if report["status"] == "PROVENANCE_INVALID":
        raise ValueError("Cannot transform evidence that fails integrity validation")
    output = apply(data, ops)
    v = services.register(db, output, lineage_id=snap["version"]["lineage_id"])
    actor_id = "0x" + keccak(text="ModelLedger Transform Gateway").hex()
    params = Params(width=v.width, height=v.height, mime=v.mime, ops=ops).model_dump(exclude_none=True)
    payload = {
        "actorId": actor_id,
        "action": services.ACTIONS.index(ops[-1].action),
        "modelRef": ZERO,
        "parentEventIds": [snap["heads"][0]],
        "inputSha256": [snap["version"]["sha256"]],
        "outputSha256": v.sha256,
        "outputPixelSha256": v.pixel_sha256,
        "outputPHash": int(v.phash["p"], 16),
        "paramsHash": digest(params),
        "privateRoot": ZERO,
        "claimedAt": int(time.time()),
        "nonce": "0x" + secrets.token_hex(32),
    }
    signed = EventIn(
        payload=payload, params=params, signature=sign_event(payload, services.scope_for(chain), settings.gateway_key)
    )
    eid = services.add_event(db, signed, chain, gateway=True)
    transaction = chain.send(
        chain.contract.functions.anchorEvent(tuple(payload.values()), signed.signature), settings.gateway_key
    )
    db.commit()
    archive = io.BytesIO()
    extension = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}[v.mime]
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("transformed." + extension, output)
        z.writestr(
            "event.json", json.dumps({"event_hash": eid, "transaction": transaction, **signed.model_dump()}, indent=2)
        )
    return Response(
        archive.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="modelledger-transform.zip"'},
    )


@app.get("/api/v1/adversarial/scenarios")
def scenarios():
    from app.adversarial.scenarios import catalog

    return catalog()


@app.post("/api/v1/adversarial/run/{scenario_id}")
def adversarial(scenario_id: str):
    from app.adversarial.scenarios import run

    try:
        return run(scenario_id)
    except KeyError:
        raise HTTPException(404, "Unknown scenario") from None


@app.get("/api/v1/demo/samples")
def demo_samples():
    if not settings.enable_demo:
        return []
    from app.config import ROOT

    manifest = ROOT / "demo/samples/manifest.json"
    return json.loads(manifest.read_text()) if manifest.exists() else []


@app.get("/api/v1/demo/samples/{name}")
def demo_sample(name: str):
    from app.config import ROOT

    allowed = {item["file"] for item in demo_samples()}
    if name not in allowed:
        raise HTTPException(404, "Demo sample not found")
    data = (ROOT / "demo/samples" / name).read_bytes()
    return Response(data, media_type="image/jpeg" if name.endswith(".jpg") else "image/png")
