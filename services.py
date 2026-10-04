import base64
import io
import time
from datetime import datetime, timezone

from PIL import Image
from sqlalchemy import select

from app.api.schemas import EventIn
from app.c2pa.reader import read_credentials
from app.config import settings
from app.core.canonical import digest
from app.core.eip712 import domain, event_hash, recover_event, recover_witness
from app.core.hashing import sha256
from app.core.perceptual import hashes, search
from app.core.pixelhash import decode, pixel_sha256
from app.db import audit
from app.db.models import Actor, Corroboration, Event, EventParent, Lineage, Version, uid
from app.engine.policy import load_policy
from app.engine.verdict import evaluate

ACTIONS = [
    "",
    "AI_GENERATION",
    "AI_EDIT",
    "AI_UPSCALE",
    "RESIZE",
    "CROP",
    "COMPRESS",
    "REENCODE",
    "FILTER",
    "BLUR",
    "HUMAN_EDIT",
    "COMPOSITE",
    "PUBLISH",
    "OTHER",
]


def fingerprint(data):
    image, mime = decode(data)
    with Image.open(io.BytesIO(data)) as source:
        public_text = " ".join(
            str(source.info.get(k, "")) for k in ("Software", "software", "Description", "description", "parameters")
        )
        public_text += str(source.getexif().get(305, ""))
    metadata_claim = any(
        word in public_text.lower() for word in ("generated", "model", "stable diffusion", "midjourney", "dall-e")
    )
    return {
        "sha256": sha256(data),
        "pixel_sha256": pixel_sha256(image),
        "phash": hashes(image),
        "mime": mime,
        "width": image.width,
        "height": image.height,
        "bytes": len(data),
        "c2pa": read_credentials(data, mime),
        "metadata_claim": metadata_claim,
    }, image


def version_dict(v):
    return {
        k: getattr(v, k)
        for k in (
            "id",
            "lineage_id",
            "sha256",
            "pixel_sha256",
            "phash",
            "mime",
            "width",
            "height",
            "bytes",
            "c2pa",
            "declared_origin",
            "thumbnail",
        )
    }


def register(db, data, declared=None, thumbnail=False, lineage_id=None):
    info, image = fingerprint(data)
    embedded_claim = info.pop("metadata_claim", False)
    if embedded_claim and not declared:
        declared = "Embedded user-declared metadata"
    existing = db.scalar(select(Version).where(Version.sha256 == info["sha256"]))
    if existing:
        return existing
    if lineage_id is None:
        lineage = Lineage()
        db.add(lineage)
        db.flush()
        lineage_id = lineage.id
    thumb = None
    if thumbnail:
        image.thumbnail((256, 256))
        stream = io.BytesIO()
        image.convert("RGB").save(stream, format="JPEG", quality=75)
        thumb = "data:image/jpeg;base64," + base64.b64encode(stream.getvalue()).decode()
    v = Version(**info, lineage_id=lineage_id, declared_origin=declared, thumbnail=thumb)
    db.add(v)
    db.flush()
    audit.append(db, "REGISTER_VERSION", v.id)
    return v


def scope_for(chain):
    return domain(settings.chain_id, chain.contract.address if chain.contract else "0x" + "00" * 20)


def add_event(db, incoming: EventIn, chain, gateway=False):
    p = incoming.payload.model_dump()
    params = incoming.params.model_dump(exclude_none=True)
    eid = event_hash(p, scope_for(chain))
    if digest(params) != p["paramsHash"]:
        raise ValueError("paramsHash does not match canonical public parameters")
    actor = db.get(Actor, p["actorId"])
    if not actor or recover_event(p, scope_for(chain), incoming.signature).lower() != actor.signer_address.lower():
        raise ValueError("SIGNER_MISMATCH")
    v = db.scalar(select(Version).where(Version.sha256 == p["outputSha256"]))
    if not v:
        raise ValueError("Register the output image before submitting its event")
    if p["outputPixelSha256"] != v.pixel_sha256 or p["outputPHash"] != int(v.phash["p"], 16):
        raise ValueError("BINDING_MISMATCH")
    if db.get(Event, eid):
        return eid
    db.add(
        Event(
            event_hash=eid,
            actor_id=p["actorId"],
            output_version=v.id,
            payload=p,
            params=params,
            signature=incoming.signature,
            gateway_replay=gateway,
        )
    )
    db.flush()
    if p["parentEventIds"]:
        known_parent = db.get(Event, p["parentEventIds"][0])
        if known_parent:
            v.lineage_id = db.get(Version, known_parent.output_version).lineage_id
    for i, parent in enumerate(p["parentEventIds"]):
        db.add(EventParent(child_event=eid, position=i, parent_event=parent, input_sha256=p["inputSha256"][i]))
    audit.append(db, "REGISTER_EVENT", eid)
    return eid


def snapshot(db, info, chain):
    policy, policy_hash = load_policy()
    v = db.scalar(select(Version).where(Version.sha256 == info["sha256"]))
    tier = "B1" if v else "NONE"
    if v is None and info.get("pixel_sha256"):
        v = db.scalar(select(Version).where(Version.pixel_sha256 == info["pixel_sha256"]).order_by(Version.created_at))
        if v:
            tier = "B2"
    try:
        available = chain.ready()
    except Exception:
        available = False
    snap = {
        "input": info,
        "metadata_claim": bool(info.get("metadata_claim")),
        "version": version_dict(v) if v else None,
        "domain": scope_for(chain),
        "events": {},
        "heads": [],
        "binding": {"tier": tier, "version_id": v.id if v else None},
        "candidates": [],
        "audit_valid": audit.verify(db)["valid"],
        "chain_available": available,
        "allow_simulated": settings.allow_simulated,
    }
    if v:
        heads = list(db.scalars(select(Event).where(Event.output_version == v.id).order_by(Event.created_at)))
        if available and heads:
            heads.sort(key=lambda e: chain.anchor(e.event_hash)["block_time"] or 2**64)
        # The first anchored claim is evaluated. Competing origins stay explicit below.
        snap["heads"] = [heads[0].event_hash] if heads else []
        queue = list(snap["heads"])
        while queue and len(snap["events"]) < policy["max_graph_nodes"]:
            eid = queue.pop()
            if eid in snap["events"]:
                continue
            e = db.get(Event, eid)
            if not e:
                continue
            actor = db.get(Actor, e.actor_id)
            actor_data = (
                {
                    k: getattr(actor, k)
                    for k in ("name", "org_id", "signer_address", "status", "approved_at", "revoked_from")
                }
                if actor
                else {}
            )
            anchor = {}
            first = eid
            witness_records = []
            if available:
                actor_data.update(chain.actor(e.actor_id))
                anchor = chain.anchor(eid)
                first = "0x" + bytes(chain.contract.functions.firstClaim(e.payload["outputSha256"]).call()).hex()
                witness_records = chain.witness_records(eid)
            else:
                # Cached approvals are not authoritative during an RPC outage.
                actor_data["approved_at"] = 0
            corroborations = []
            for c in db.scalars(select(Corroboration).where(Corroboration.event_hash == eid)):
                try:
                    signer = recover_witness(eid, c.kind, c.evidence_hash, scope_for(chain), c.signature)
                except (ValueError, TypeError):
                    signer = "INVALID"
                match = next(
                    (
                        r
                        for r in witness_records
                        if r["signer"].lower() == signer.lower()
                        and r["kind"] == c.kind
                        and r["evidence_hash"] == c.evidence_hash
                    ),
                    {},
                )
                corroborations.append(
                    {
                        **match,
                        "evidence": c.evidence,
                        "signature": c.signature,
                        "kind": c.kind,
                        "evidence_hash": c.evidence_hash,
                    }
                )
            snap["events"][eid] = {
                "payload": e.payload,
                "params": e.params,
                "signature": e.signature,
                "version": version_dict(db.get(Version, e.output_version)),
                "actor": actor_data,
                "anchor": anchor,
                "first_claim": first,
                "corroborations": corroborations,
                "action_name": ACTIONS[e.payload["action"]],
                "gateway_replay": e.gateway_replay,
            }
            queue.extend(e.payload["parentEventIds"])
    elif info.get("phash"):
        records = [(v.id, v.phash) for v in db.scalars(select(Version).limit(10000))]
        snap["candidates"] = search(info["phash"], records, policy["candidate_threshold"], policy["max_candidates"])
    return snap, policy, policy_hash


def verify(db, info, chain, save=False):
    snap, policy, policy_hash = snapshot(db, info, chain)
    result = evaluate(snap, policy, int(time.time()))
    return {
        **result,
        "report_id": uid("VR"),
        "engine_version": "1.0.0",
        "policy_hash": policy_hash,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "input": info,
        "saved": save,
        "chain": {
            "chain_id": settings.chain_id,
            "contract_address": chain.contract.address if chain.contract else None,
            "available": snap["chain_available"],
        },
    }
