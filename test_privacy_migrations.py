import io
import json
from pathlib import Path

import pytest
from alembic.config import Config
from modelledger_sdk import Provider
from PIL import Image
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from alembic import command
from app.api.schemas import EventIn
from app.api.services import add_event, fingerprint, register, verify, version_dict
from app.core.commitments import commit
from app.core.eip712 import ZERO
from app.db import audit
from app.db.models import Actor
from app.seed.demo import h


def test_private_prompt_absent_from_database_report_and_chain(db, chain, client):
    secret = "PRIVACY_PROBE_9d8f_a_private_story_that_must_never_be_stored"
    root, packages = commit({"prompt": secret, "seed": "owner-private-seed"})
    actor_id = h("privacy-provider")
    key = chain.keys[1]
    chain.send(chain.contract.functions.registerActor(actor_id, h("privacy-org"), ZERO), key)
    db.add(
        Actor(actor_id=actor_id, name="Privacy Test Provider", provider="TEST", kind="MODEL", **chain.actor(actor_id))
    )
    db.flush()
    output = io.BytesIO()
    Image.new("RGB", (50, 50), "#389180").save(output, format="PNG")
    data = output.getvalue()
    version = register(db, data)
    provider = Provider("", key, actor_id, chain.web3.eth.chain_id, chain.contract.address)
    event = provider.signed_event(version_dict(version), [{"action": "AI_GENERATION"}], private_root=root)
    eid = add_event(db, EventIn(**event), chain)
    tx = chain.send(chain.contract.functions.anchorEvent(tuple(event["payload"].values()), event["signature"]), key)
    db.commit()
    report = verify(db, fingerprint(data)[0], chain)
    package = packages[0]
    request = {**package, "event_hash": eid}
    response = client.post("/api/v1/disclosures/verify", json=request)
    assert response.status_code == 200 and response.json()["valid"]
    request["salt"] = "0x" + "00" * 16
    assert client.post("/api/v1/disclosures/verify", json=request).json()["valid"] is False
    dumps = []
    for table in ("versions", "events", "corroborations", "verification_reports", "audit_log"):
        dumps.append(str(db.execute(text("SELECT * FROM " + table)).all()))
    transaction = chain.web3.eth.get_transaction(tx)
    public = json.dumps(report) + "".join(dumps) + transaction["input"].hex() + response.text
    assert secret not in public and secret.encode().hex() not in public
    assert "owner-private-seed" not in public
    provider.close()


def test_empty_database_migration_append_only_and_audit(tmp_path, monkeypatch):
    import app.db.session as session_module

    database = create_engine("sqlite:///" + str(tmp_path / "migration.db"))
    monkeypatch.setattr(session_module, "engine", database)
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    command.upgrade(config, "head")
    with Session(database) as db:
        audit.append(db, "TEST", "subject")
        db.commit()
        assert audit.verify(db)["valid"]
        for query in ("UPDATE audit_log SET row_hash='bad'", "DELETE FROM audit_log"):
            with pytest.raises(Exception):
                db.execute(text(query))
                db.commit()
            db.rollback()
        db.execute(text("DROP TRIGGER immutable_audit_log_UPDATE"))
        db.execute(text("UPDATE audit_log SET row_hash='bad'"))
        db.commit()
        assert not audit.verify(db)["valid"]
    database.dispose()
