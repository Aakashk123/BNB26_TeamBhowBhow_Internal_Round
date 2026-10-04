"""SIMULATED providers with genuine local EVM anchors and independent witness signatures."""

import io
import json
from pathlib import Path

import numpy as np
from eth_account import Account
from eth_utils import keccak
from modelledger_sdk import Provider
from PIL import Image, ImageDraw, ImageFilter
from sqlalchemy import select

from app.api.schemas import EventIn
from app.api.services import add_event, register, scope_for, version_dict
from app.config import ROOT, settings
from app.core.canonical import digest
from app.core.eip712 import ZERO, sign_witness
from app.db import audit
from app.db.models import Actor, Corroboration, Event


def h(text):
    return "0x" + keccak(text=text).hex()


def image(seed=34):
    rng = np.random.default_rng(seed)
    im = Image.new("RGB", (800, 600), "#dfeee9")
    d = ImageDraw.Draw(im)
    for i in range(30):
        x, y = map(int, rng.integers(0, 600, 2))
        radius = int(rng.integers(30, 180))
        color = tuple(map(int, rng.integers(45, 200, 3)))
        d.ellipse((x, y, x + radius, y + radius), fill=color)
    d.rectangle((0, 510, 800, 600), fill="#153e34")
    d.text((30, 535), "MODELLEDGER / SIMULATED GENERATOR", fill="#d1e6d9")
    return im


def encode(im, fmt="PNG", **kwargs):
    b = io.BytesIO()
    im.save(b, format=fmt, **kwargs)
    return b.getvalue()


def seed(db, chain, admin_key, keys=None, out_dir=None):
    if settings.env == "production":
        raise ValueError("Demo seeding is disabled in production")
    keypath = ROOT / ".runtime/demo-keys.json"
    if keys is None:
        if keypath.exists():
            keys = json.loads(keypath.read_text())
        else:
            keys = ["0x" + Account.create().key.hex() for _ in range(7)]
            keypath.parent.mkdir(exist_ok=True)
            keypath.write_text(json.dumps(keys))
            keypath.chmod(0o600)
    out = Path(out_dir or ROOT / "demo/samples")
    out.mkdir(parents=True, exist_ok=True)
    names = [
        "SIMULATED Model A",
        "SIMULATED Model B",
        "SIMULATED Tool C",
        "SIMULATED Platform D",
        "SIMULATED Rogue R",
        "SIMULATED Impostor",
        "SIMULATED Witness W1",
    ]
    for i, name in enumerate(names):
        account = Account.from_key(keys[i])
        if chain.web3.eth.get_balance(account.address) < 10**17:
            transaction = chain.web3.eth.send_transaction(
                {"from": Account.from_key(admin_key).address, "to": account.address, "value": 10**18}
            )
            chain.web3.eth.wait_for_transaction_receipt(transaction)
        actor_id = h(name)
        if chain.actor(actor_id)["status"] == 0:
            chain.send(chain.contract.functions.registerActor(actor_id, h("org-" + str(i)), ZERO), keys[i])
        if i < 4 and chain.actor(actor_id)["status"] == 1:
            chain.send(chain.contract.functions.approveActor(actor_id), admin_key)
        if not db.get(Actor, actor_id):
            db.add(
                Actor(
                    actor_id=actor_id,
                    name=name,
                    provider="SIMULATED demo organization " + str(i),
                    kind="MODEL" if i < 2 else "TOOL",
                    **chain.actor(actor_id),
                )
            )
    witness = Account.from_key(keys[6])
    chain.send(chain.contract.functions.approveWitness(witness.address, h("independent-witness")), admin_key)
    db.flush()
    images = [
        image(),
        image().resize((1000, 750)),
        image().resize((1000, 750)).crop((20, 20, 950, 700)).filter(ImageFilter.GaussianBlur(0.5)),
    ]
    outputs = [encode(images[0]), encode(images[1]), encode(images[2]), encode(images[2], "JPEG", quality=88)]
    operations = [
        [{"action": "AI_GENERATION"}],
        [{"action": "AI_UPSCALE"}],
        [{"action": "CROP", "box": [20, 20, 950, 700]}, {"action": "BLUR", "radius": 0.5}],
        [{"action": "REENCODE", "format": "JPEG", "quality": 88}],
    ]
    actions = [1, 3, 9, 7]
    parents = []
    lineage = None
    manifest = []
    for i, data in enumerate(outputs):
        v = register(db, data, thumbnail=True, lineage_id=lineage)
        lineage = v.lineage_id
        provider = Provider("", keys[i], h(names[i]), settings.chain_id, chain.contract.address)
        existing = db.scalar(select(Event).where(Event.output_version == v.id, Event.actor_id == h(names[i])))
        if existing:
            signed = {"payload": existing.payload, "params": existing.params, "signature": existing.signature}
            eid = existing.event_hash
        else:
            signed = provider.signed_event(
                version_dict(v), operations[i], action=actions[i], parents=parents, simulated=True
            )
            eid = add_event(db, EventIn(**signed), chain, gateway=(i == 2))
        if not chain.anchor(eid)["block_time"]:
            chain.send(
                chain.contract.functions.anchorEvent(tuple(signed["payload"].values()), signed["signature"]), keys[i]
            )
        evidence = {"observed": True, "method": "direct_observation", "simulated": True}
        eh = digest(evidence)
        sig = sign_witness(eid, 1, eh, scope_for(chain), keys[6])
        if not chain.contract.functions.witnessedBy(eid, h("independent-witness")).call():
            chain.send(chain.contract.functions.witness(eid, 1, eh, sig), keys[6])
            db.add(Corroboration(event_hash=eid, kind=1, evidence_hash=eh, evidence=evidence, signature=sig))
        parents = [{"event_hash": eid, "sha256": v.sha256}]
        filename = f"{i + 1:02d}-" + ["generation.png", "upscale.png", "multi-edit.png", "final.jpg"][i]
        (out / filename).write_bytes(data)
        manifest.append(
            {
                "file": filename,
                "title": [
                    "Model A · Generation",
                    "Model B · Upscale",
                    "Tool C · Crop + blur",
                    "Platform D · Final export",
                ][i],
                "expected": "VERIFIED · SIMULATED",
            }
        )
        provider.close()
    unknown = encode(image(778).filter(ImageFilter.GaussianBlur(14)))
    (out / "unknown.png").write_bytes(unknown)
    manifest.append({"file": "unknown.png", "title": "Unknown origin", "expected": "UNVERIFIABLE"})
    (out / "unregistered-blur.png").write_bytes(encode(images[0].filter(ImageFilter.GaussianBlur(8))))
    manifest.append(
        {
            "file": "unregistered-blur.png",
            "title": "Unregistered heavy blur",
            "expected": "Similarity only · UNVERIFIABLE",
        }
    )
    audit.append(db, "SEED_SIMULATED_DEMO", "four-hop")
    db.commit()
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def main():
    from app.chain.client import Chain
    from app.db.session import SessionLocal

    if not settings.enable_demo:
        raise ValueError("Set ENABLE_DEMO=true explicitly")
    with SessionLocal() as db:
        seed(db, Chain(), settings.registrar_key)
    print("SIMULATED demo seeded with actual EVM anchors and signed witness records")


if __name__ == "__main__":
    main()
