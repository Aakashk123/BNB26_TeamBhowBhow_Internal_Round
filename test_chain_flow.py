from sqlalchemy import select

from app.api.services import fingerprint, verify
from app.config import settings
from app.core.eip712 import ZERO
from app.db.models import Actor, Event
from app.seed.demo import h, seed


def test_real_evm_four_hop_and_gateway(db, chain, client, tmp_path):
    seed(db, chain, chain.keys[0], keys=chain.keys[1:8], out_dir=tmp_path)
    data = (tmp_path / "04-final.jpg").read_bytes()
    report = verify(db, fingerprint(data)[0], chain)
    assert report["status"] == "VERIFIED", report["reasons"]
    assert report["counts"]["verified"] == 4 and len(report["graph"]["nodes"]) == 4
    assert report["simulated"]
    assert client.post("/api/v1/verify", files={"file": ("final.jpg", data)}).json()["status"] == "VERIFIED"
    unknown = client.post(
        "/api/v1/verify", files={"file": ("unknown.png", (tmp_path / "unregistered-blur.png").read_bytes())}
    ).json()
    assert unknown["status"] == "UNVERIFIABLE"
    key = chain.keys[9]
    name = "ModelLedger Transform Gateway"
    actor_id = h(name)
    chain.send(chain.contract.functions.registerActor(actor_id, h("gateway-org"), ZERO), key)
    chain.send(chain.contract.functions.approveActor(actor_id), chain.keys[0])
    db.add(Actor(actor_id=actor_id, name=name, provider="ModelLedger", kind="TOOL", **chain.actor(actor_id)))
    db.commit()
    previous = settings.gateway_key
    settings.gateway_key = key
    try:
        response = client.post(
            "/api/v1/transform",
            files={"file": ("final.jpg", data)},
            data={"operations": '[{"action":"RESIZE","width":400,"height":300}]'},
        )
        assert response.status_code == 200, response.text
        import io
        import zipfile

        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            output = z.read("transformed.jpg")
        result = client.post("/api/v1/verify", files={"file": ("transformed.jpg", output)}).json()
        assert result["status"] == "VERIFIED", result
        assert result["counts"]["verified"] == 5
    finally:
        settings.gateway_key = previous
    # Compromise the origin key retroactively; descendants must no longer verify.
    origin = db.scalar(select(Event).where(Event.actor_id == h("SIMULATED Model A")))
    at = chain.anchor(origin.event_hash)["block_time"]
    chain.send(chain.contract.functions.revokeActor(origin.actor_id, at), chain.keys[0])
    result = verify(db, fingerprint(data)[0], chain)
    assert result["status"] == "PROVENANCE_INVALID"
    assert "KEY_COMPROMISED_WINDOW" in [r["code"] for r in result["reasons"]]
