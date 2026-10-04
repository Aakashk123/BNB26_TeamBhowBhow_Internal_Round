import io

import pytest
from hypothesis import given
from hypothesis import settings as hypothesis_settings
from hypothesis import strategies as st
from PIL import Image, PngImagePlugin

from app.adversarial.scenarios import KEYS, NOW, SCOPE, base, catalog, run
from app.core.canonical import canonical
from app.core.commitments import commit, disclose, leaf
from app.core.eip712 import event_hash, recover_event, recover_report, sign_report
from app.core.hashing import sha256
from app.core.merkle import proof, tree, verify
from app.core.perceptual import distance, hashes, search
from app.core.pixelhash import decode, pixel_sha256
from app.engine.policy import load_policy
from app.engine.verdict import evaluate


@given(st.binary(max_size=10000))
def test_hash_deterministic(data):
    assert sha256(data) == sha256(data)
    assert len(sha256(data)) == 66


@given(st.text(max_size=200), st.sampled_from(["prompt", "seed", "operator_id"]))
def test_private_proof(value, field):
    root, packages = commit({field: value})
    p = packages[0]
    assert disclose(field, value, p["salt"], p["proof"], root)
    assert not disclose(field, value + "changed", p["salt"], p["proof"], root)
    assert not disclose(field, value, "0x" + "00" * 16, p["proof"], root)
    assert len(p["proof"]) == 3


def test_merkle_invalid_inputs():
    for leaves in ([], [b"a" * 32] * 3, [b"a"] * 2):
        with pytest.raises(ValueError):
            tree(leaves)
    t = tree([b"a" * 32, b"b" * 32])
    assert verify(b"a" * 32, proof(t, 0), "0x" + t[-1][0].hex())
    assert not verify(b"a" * 32, ["bad"], "0x" + t[-1][0].hex())
    assert not verify(b"a" * 32, ["0x00"], "0x" + t[-1][0].hex())
    with pytest.raises(ValueError):
        proof(t, 5)
    with pytest.raises(ValueError):
        commit({"unknown": "value"})
    with pytest.raises(ValueError):
        leaf("prompt", "value", "00")
    assert not disclose("unknown", "v", "bad", [], "bad")


def test_lossless_pixel_binding():
    im = Image.new("RGB", (32, 16), "#fea000")
    b = io.BytesIO()
    im.save(b, format="PNG")
    meta = PngImagePlugin.PngInfo()
    meta.add_text("description", "User-declared Model X")
    c = io.BytesIO()
    im.save(c, format="PNG", pnginfo=meta)
    a, _ = decode(b.getvalue())
    other, _ = decode(c.getvalue())
    assert sha256(b.getvalue()) != sha256(c.getvalue())
    assert pixel_sha256(a) == pixel_sha256(other)
    assert pixel_sha256(im) != pixel_sha256(im.convert("RGBA"))
    assert distance("0", "f") == 4
    assert search(hashes(im), [("IMG", hashes(im))], 0)[0]["relationship"] == "UNVERIFIED"
    assert search(hashes(im), [], 0) == []


@pytest.mark.parametrize("data", [b"", b"not an image", b"x" * (25 * 1024 * 1024 + 1)])
def test_invalid_upload(data):
    with pytest.raises(ValueError):
        decode(data)


def test_canonical_and_report_signature():
    assert canonical({"b": 1, "a": 2}) == b'{"a":2,"b":1}'
    with pytest.raises(ValueError):
        canonical({"a": float("nan")})
    report = {"status": "UNVERIFIABLE"}
    sig = sign_report(report, KEYS[0])
    from eth_account import Account

    assert recover_report(report, sig) == Account.from_key(KEYS[0]).address
    assert recover_report({"status": "VERIFIED"}, sig) != Account.from_key(KEYS[0]).address


@given(
    st.sampled_from(["actorId", "modelRef", "outputSha256", "outputPixelSha256", "paramsHash", "privateRoot", "nonce"]),
    st.integers(0, 255),
)
@hypothesis_settings(max_examples=40)
def test_signed_bit_flip(field, bit):
    s = base()
    e = next(iter(s["events"].values()))
    value = int(e["payload"][field], 16) ^ (1 << bit)
    e["payload"][field] = "0x" + value.to_bytes(32, "big").hex()
    policy, _ = load_policy()
    assert evaluate(s, policy, NOW)["status"] == "PROVENANCE_INVALID"


@pytest.mark.parametrize("scenario", [s["id"] for s in catalog()])
def test_adversarial(scenario):
    result = run(scenario)
    assert result["passed"], result


def test_domain_replay():
    s = base()
    e = next(iter(s["events"].values()))
    other = {**SCOPE, "chainId": 31338}
    assert recover_event(e["payload"], other, e["signature"]) != e["actor"]["signer_address"]
    assert event_hash(e["payload"], other) != s["heads"][0]


def test_engine_boundaries():
    policy, _ = load_policy()
    s = base()
    e = next(iter(s["events"].values()))
    e["anchor"] = {}
    assert evaluate(s, policy, NOW)["origin_trust"] == "SELF_ASSERTED"
    s = base()
    e = next(iter(s["events"].values()))
    e["params"]["width"] = 1
    assert evaluate(s, policy, NOW)["status"] == "PROVENANCE_INVALID"
    s = base()
    s["allow_simulated"] = False
    assert evaluate(s, policy, NOW)["status"] == "UNVERIFIABLE"
    s = base()
    e = next(iter(s["events"].values()))
    e["corroborations"][0]["evidence"]["observed"] = False
    assert evaluate(s, policy, NOW)["status"] == "PROVENANCE_INVALID"
    s = base()
    e = next(iter(s["events"].values()))
    e["corroborations"][0]["approved"] = False
    assert evaluate(s, policy, NOW)["status"] == "UNVERIFIABLE"


def test_experimental_watermark_is_not_a_trust_signal():
    from app.core.watermark import embed, score

    image = Image.new("RGB", (80, 80), (120, 120, 120))
    key = b"test-watermark-key-public"
    marked = embed(image, key)
    assert marked.size == image.size
    assert score(marked, key) > score(image, key)
    with pytest.raises(ValueError):
        embed(image, b"short")
    with pytest.raises(ValueError):
        embed(image, key, 4)


@given(st.sampled_from(["action", "outputPHash", "claimedAt"]), st.integers(0, 6))
@hypothesis_settings(max_examples=15)
def test_signed_numeric_field_bit_flip(field, bit):
    s = base()
    e = next(iter(s["events"].values()))
    e["payload"][field] ^= 1 << bit
    policy, _ = load_policy()
    assert evaluate(s, policy, NOW)["status"] == "PROVENANCE_INVALID"


def test_signed_parent_array_bit_flip():
    s = base()
    e = next(iter(s["events"].values()))
    e["payload"]["parentEventIds"] = ["0x" + "01" * 32]
    e["payload"]["inputSha256"] = ["0x" + "02" * 32]
    policy, _ = load_policy()
    assert evaluate(s, policy, NOW)["status"] == "PROVENANCE_INVALID"
