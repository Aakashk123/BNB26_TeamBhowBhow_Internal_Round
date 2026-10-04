import io
from datetime import datetime, timedelta, timezone

import pytest
from PIL import Image

from app.c2pa.reader import read_credentials


def signed_fixture():
    c2pa = pytest.importorskip("c2pa", reason="C2PA_UNAVAILABLE: optional native validator is not installed")
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

    root_key = ec.generate_private_key(ec.SECP256R1())
    key = ec.generate_private_key(ec.SECP256R1())
    now = datetime.now(timezone.utc)
    root_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "ModelLedger Test Root")])
    leaf_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "ModelLedger Test Signer")])
    ca = (
        x509.CertificateBuilder()
        .subject_name(root_name)
        .issuer_name(root_name)
        .public_key(root_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=30))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(x509.KeyUsage(False, False, False, False, False, True, True, False, False), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(root_key.public_key()), False)
        .sign(root_key, hashes.SHA256())
    )
    cert = (
        x509.CertificateBuilder()
        .subject_name(leaf_name)
        .issuer_name(root_name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=7))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.KeyUsage(True, False, False, False, False, False, False, False, False), critical=True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.EMAIL_PROTECTION]), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(root_key.public_key()), False)
        .sign(root_key, hashes.SHA256())
    )
    pem = (cert.public_bytes(serialization.Encoding.PEM) + ca.public_bytes(serialization.Encoding.PEM)).decode()
    signer = c2pa.Signer.from_callback(
        lambda data: key.sign(data, ec.ECDSA(hashes.SHA256())), c2pa.C2paSigningAlg.ES256, pem
    )
    image = io.BytesIO()
    Image.new("RGB", (60, 40), "#24a182").save(image, format="JPEG")
    image.seek(0)
    result = io.BytesIO()
    manifest = {
        "claim_generator": "ModelLedger Test SIMULATED",
        "title": "Fixture",
        "format": "image/jpeg",
        "assertions": [
            {
                "label": "c2pa.actions",
                "data": {
                    "actions": [
                        {
                            "action": "c2pa.created",
                            "digitalSourceType": "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia",
                        }
                    ]
                },
            }
        ],
    }
    with c2pa.Builder(manifest) as builder:
        builder.sign(signer, "image/jpeg", image, result)
    return result.getvalue()


def test_real_c2pa_untrusted_and_altered_claim():
    data = signed_fixture()
    state = read_credentials(data, "image/jpeg")
    assert state["state"] == "VALID", state
    assert state["signer_trusted"] is False
    from app.adversarial.scenarios import NOW, SCOPE
    from app.engine.policy import load_policy
    from app.engine.verdict import evaluate

    policy, _ = load_policy()
    report = evaluate(
        {
            "domain": SCOPE,
            "events": {},
            "heads": [],
            "version": None,
            "binding": {"tier": "NONE"},
            "input": {"c2pa": state},
        },
        policy,
        NOW,
    )
    assert report["origin_trust"] == "SELF_ASSERTED"
    assert report["origin"]["assurance"] == "A1"
    assert report["status"] == "UNVERIFIABLE"
    changed = data.replace(b"c2pa.created", b"c2pa.edited!")
    assert changed != data
    state = read_credentials(changed, "image/jpeg")
    assert state["state"] == "INVALID", state
