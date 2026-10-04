"""Embedded-only validation. Remote manifests are never fetched (SSRF/privacy boundary)."""

import io
import json
from pathlib import Path

from app.core.hashing import sha256


def read_credentials(data: bytes, mime: str) -> dict:
    try:
        import c2pa
    except ImportError:
        return {"state": "C2PA_UNAVAILABLE", "valid": None, "signer_trusted": False}
    anchors = Path(__file__).resolve().parents[3] / "config/c2pa_trust"
    trust = "\n".join(p.read_text() for p in anchors.glob("*.pem"))
    settings = {"verify": {"verify_after_reading": True, "remote_manifest_fetch": False, "verify_trust": True}}
    if trust:
        settings["trust"] = {"trust_anchors": trust}
    try:
        with c2pa.Context.from_dict(settings) as context:
            with c2pa.Reader(mime, io.BytesIO(data), context=context) as reader:
                raw = reader.json()
                obj = json.loads(raw)
                state = reader.get_validation_state()
        active = obj.get("manifests", {}).get(obj.get("active_manifest"), {})
        # Never persist raw assertions: embedded manifests can contain private prompts.
        failures = [s.get("code", "") for s in obj.get("validation_status", [])]
        return {
            "state": "VALID"
            if state in ("Valid", "Trusted")
            else "INVALID"
            if state == "Invalid"
            else "C2PA_UNEVALUABLE",
            "valid": state in ("Valid", "Trusted"),
            "signer_trusted": state == "Trusted",
            "manifest_hash": sha256(raw.encode()),
            "validation_codes": failures,
            "actions": [
                a.get("action", "unknown")
                for assertion in active.get("assertions", [])
                if assertion.get("label", "").startswith("c2pa.actions")
                for a in assertion.get("data", {}).get("actions", [])
            ],
            "ingredients": len(active.get("ingredients", [])),
            "signer": active.get("signature_info", {}).get("issuer", "Content Credentials signer"),
        }
    except c2pa.C2paError as exc:
        name = type(exc).__name__
        if name == "ManifestNotFound" or "ManifestNotFound" in str(exc):
            return {"state": "NONE", "valid": None, "signer_trusted": False}
        # Malformed or unreachable data is unevaluable unless validator explicitly reports Invalid.
        return {"state": "C2PA_UNEVALUABLE", "valid": None, "signer_trusted": False, "error_type": name}
