"""Deterministic adversarial evidence snapshots; no mock RPC or simulated TEE is trusted in production."""

import copy

from eth_account import Account
from eth_utils import keccak

from app.core.canonical import digest
from app.core.eip712 import ZERO, domain, event_hash, sign_event, sign_witness
from app.engine.policy import load_policy
from app.engine.verdict import evaluate

NOW = 1800000000
SCOPE = domain(31337, "0x" + "ab" * 20)
# Public test-only keys derived deterministically; never used by the deployed application.
KEYS = ["0x" + keccak(text="MODELLEDGER PUBLIC TEST FIXTURE " + str(i)).hex() for i in range(8)]


def h(value):
    return "0x" + keccak(text=value).hex()


def event(index=0, parent=None, approved=True, corroborated=True, action=1):
    actor_id = h("actor" + str(index))
    output = h("image" + str(index))
    params = {
        "width": 256,
        "height": 256,
        "mime": "image/png",
        "ops": [{"action": "AI_GENERATION" if action == 1 else "RESIZE"}],
        "simulated": True,
    }
    payload = {
        "actorId": actor_id,
        "action": action,
        "modelRef": h("model"),
        "parentEventIds": [parent[0]] if parent else [],
        "inputSha256": [parent[1]["payload"]["outputSha256"]] if parent else [],
        "outputSha256": output,
        "outputPixelSha256": h("pixels" + str(index)),
        "outputPHash": 0,
        "paramsHash": digest(params),
        "privateRoot": ZERO,
        "claimedAt": NOW - 100 + index,
        "nonce": h("nonce" + str(index)),
    }
    eid = event_hash(payload, SCOPE)
    evidence = {"observed": True, "method": "direct_observation", "simulated": True}
    evidence_hash = digest(evidence)
    record = {
        "signer": Account.from_key(KEYS[7]).address,
        "org_id": h("independent"),
        "kind": 1,
        "evidence_hash": evidence_hash,
        "evidence": evidence,
        "signature": sign_witness(eid, 1, evidence_hash, SCOPE, KEYS[7]),
        "approved": True,
        "on_chain": True,
    }
    return eid, {
        "payload": payload,
        "params": params,
        "signature": sign_event(payload, SCOPE, KEYS[index]),
        "version": {
            "id": "IMG-" + str(index + 1).zfill(3),
            "sha256": output,
            "pixel_sha256": payload["outputPixelSha256"],
            "phash": {"d": "0" * 16, "p": "0" * 16, "w": "0" * 16},
            "width": 256,
            "height": 256,
            "mime": "image/png",
        },
        "actor": {
            "name": "SIMULATED Model " + str(index),
            "signer_address": Account.from_key(KEYS[index]).address,
            "org_id": h("org" + str(index)),
            "approved_at": NOW - 200 if approved else 0,
            "revoked_from": 0,
        },
        "anchor": {"actor_id": actor_id, "block_time": NOW - 80 + index},
        "first_claim": eid,
        "corroborations": [record] if corroborated else [],
    }


def base():
    e = event()
    return {
        "domain": SCOPE,
        "events": {e[0]: e[1]},
        "heads": [e[0]],
        "version": e[1]["version"],
        "binding": {"tier": "B1", "version_id": "IMG-001"},
        "input": {"c2pa": {"state": "NONE"}},
        "audit_valid": True,
        "allow_simulated": True,
        "candidates": [],
    }


def fixtures():
    out = []

    def add(id, title, s, status, trust, codes=()):
        out.append(
            {
                "id": id,
                "title": title,
                "snapshot": s,
                "expected": {"status": status, "origin_trust": trust, "codes": list(codes)},
            }
        )

    s = base()
    prior = (s["heads"][0], next(iter(s["events"].values())))
    for i in range(1, 4):
        prior = event(i, prior, action=2 if i == 1 else 4)
        s["events"][prior[0]] = prior[1]
    s["heads"] = [prior[0]]
    s["version"] = prior[1]["version"]
    add("honest-chain", "Honest four-hop signed chain", s, "VERIFIED", "TRUSTED")
    s = base()
    next(iter(s["events"].values()))["corroborations"] = []
    add(
        "authorized-lie",
        "Authorized signer lies without a witness",
        s,
        "UNVERIFIABLE",
        "SELF_ASSERTED",
        ["NO_CORROBORATION"],
    )
    s = base()
    next(iter(s["events"].values()))["actor"]["approved_at"] = 0
    add("unapproved-key", "Unapproved key claims a model", s, "UNVERIFIABLE", "SELF_ASSERTED", ["ACTOR_UNAPPROVED"])
    s = base()
    e = next(iter(s["events"].values()))
    e["signature"] = sign_event(e["payload"], SCOPE, KEYS[6])
    add("impersonation", "Attacker impersonates Model A", s, "PROVENANCE_INVALID", "UNVERIFIABLE", ["SIGNER_MISMATCH"])
    s = base()
    next(iter(s["events"].values()))["payload"]["modelRef"] = h("tampered")
    add(
        "field-tampering",
        "Signed field changes after signing",
        s,
        "PROVENANCE_INVALID",
        "UNVERIFIABLE",
        ["SIG_INVALID"],
    )
    s = base()
    parent = (s["heads"][0], next(iter(s["events"].values())))
    child = event(1, parent, action=4)
    child[1]["payload"]["inputSha256"] = [h("swapped")]
    s["events"][child[0]] = child[1]
    s["heads"] = [child[0]]
    add(
        "parent-swap",
        "Consumed parent hash is altered",
        s,
        "PROVENANCE_INVALID",
        "UNVERIFIABLE",
        ["PARENT_REF_MISMATCH"],
    )
    s = base()
    next(iter(s["events"].values()))["version"]["sha256"] = h("different-image")
    add(
        "wrong-binding",
        "Valid record attached to different pixels",
        s,
        "PROVENANCE_INVALID",
        "UNVERIFIABLE",
        ["BINDING_MISMATCH"],
    )
    s = base()
    s["binding"]["tier"] = "B2"
    add("metadata-strip", "Lossless metadata stripping retains pixel binding", s, "VERIFIED", "TRUSTED")
    s = base()
    parent = event(1, (h("missing"), next(iter(s["events"].values()))), action=4)
    s["events"] = {parent[0]: parent[1]}
    s["heads"] = [parent[0]]
    add(
        "missing-middle",
        "Missing parent is an explicit graph gap",
        s,
        "PARTIALLY_VERIFIED",
        "UNVERIFIABLE",
        ["PARENT_UNAVAILABLE"],
    )
    s = base()
    next(iter(s["events"].values()))["payload"]["claimedAt"] = NOW + 1000
    add("time-travel", "Future timestamp exceeds clock skew", s, "PROVENANCE_INVALID", "UNVERIFIABLE", ["TIME_PARADOX"])
    s = base()
    next(iter(s["events"].values()))["actor"]["revoked_from"] = NOW - 90
    add(
        "revoked-window",
        "Retroactive key compromise covers anchor",
        s,
        "PROVENANCE_INVALID",
        "UNVERIFIABLE",
        ["KEY_COMPROMISED_WINDOW"],
    )
    s = base()
    next(iter(s["events"].values()))["actor"]["revoked_from"] = NOW - 10
    add("before-revocation", "Anchor predates key compromise", s, "VERIFIED", "TRUSTED")
    s = base()
    next(iter(s["events"].values()))["first_claim"] = h("earlier")
    add(
        "conflicting-origin",
        "Later conflicting origin is downgraded",
        s,
        "UNVERIFIABLE",
        "SELF_ASSERTED",
        ["CONFLICTING_ORIGIN"],
    )
    s = base()
    e = next(iter(s["events"].values()))
    e["corroborations"][0]["org_id"] = e["actor"]["org_id"]
    add(
        "sybil-witness",
        "Witness from the signer organization does not count",
        s,
        "UNVERIFIABLE",
        "SELF_ASSERTED",
        ["NO_CORROBORATION"],
    )
    s = base()
    s.update(
        events={},
        heads=[],
        version=None,
        binding={"tier": "B5"},
        candidates=[{"version_id": "IMG-001", "hamming": 2, "relationship": "UNVERIFIED"}],
    )
    add("laundering", "Similarity cannot transfer a signature", s, "UNVERIFIABLE", "UNVERIFIABLE", ["SIMILARITY_ONLY"])
    s = base()
    s.update(events={}, heads=[], metadata_claim=True)
    add(
        "fake-exif",
        "Fake model metadata remains self-declared",
        s,
        "UNVERIFIABLE",
        "SELF_ASSERTED",
        ["SELF_DECLARED_METADATA"],
    )
    s = base()
    eid = s["heads"][0]
    s["events"][eid]["payload"]["parentEventIds"] = [eid]
    s["events"][eid]["payload"]["inputSha256"] = [s["version"]["sha256"]]
    add("parent-cycle", "Parent cycle is rejected", s, "PROVENANCE_INVALID", "UNVERIFIABLE", ["PARENT_CYCLE"])
    s = base()
    s["input"]["c2pa"]["state"] = "INVALID"
    add(
        "c2pa-tamper",
        "C2PA validator reports invalid evidence",
        s,
        "PROVENANCE_INVALID",
        "UNVERIFIABLE",
        ["C2PA_SIGNATURE_INVALID"],
    )
    s = base()
    s["audit_valid"] = False
    add("audit-tamper", "Audit chain breaks", s, "PROVENANCE_INVALID", "UNVERIFIABLE", ["AUDIT_CHAIN_BROKEN"])
    s = base()
    s.update(events={}, heads=[], version=None, binding={"tier": "NONE"})
    add("unknown-image", "Unknown image has insufficient evidence", s, "UNVERIFIABLE", "UNVERIFIABLE")
    return out


def catalog():
    return [{k: v for k, v in s.items() if k != "snapshot"} for s in fixtures()] + [
        {
            "id": "privacy-proof",
            "title": "Correct disclosure succeeds, wrong salt fails",
            "expected": {"status": "PASS"},
        }
    ]


def run(scenario_id):
    if scenario_id == "privacy-proof":
        from app.core.commitments import commit, disclose

        root, packages = commit({"prompt": "MODELLEDGER_PRIVATE_PROBE"})
        p = packages[0]
        correct = disclose(p["field"], p["value"], p["salt"], p["proof"], root)
        incorrect = disclose(p["field"], p["value"], "0x" + "00" * 16, p["proof"], root)
        return {
            "id": scenario_id,
            "passed": correct and not incorrect,
            "actual": {"status": "PASS" if correct and not incorrect else "FAIL"},
            "expected": {"status": "PASS"},
            "scope": "Real cryptographic proof check; no private value returned",
        }
    scenario = next((s for s in fixtures() if s["id"] == scenario_id), None)
    if not scenario:
        raise KeyError(scenario_id)
    policy, _ = load_policy()
    report = evaluate(copy.deepcopy(scenario["snapshot"]), policy, NOW)
    expected = scenario["expected"]
    codes = {r["code"] for r in report["reasons"]}
    passed = (
        report["status"] == expected["status"]
        and report["origin_trust"] == expected["origin_trust"]
        and set(expected["codes"]) <= codes
    )
    return {
        "id": scenario_id,
        "passed": passed,
        "expected": expected,
        "actual": report,
        "scope": "SIMULATED evidence snapshot; production engine, real signatures",
    }
