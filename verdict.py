"""Pure policy evaluation: all network and database reads happen before this function."""

from typing import Any

from app.core.canonical import digest
from app.core.eip712 import ZERO, event_hash, recover_event, recover_witness
from app.core.perceptual import distance
from app.engine.reasons import Code, reason


def evaluate(snapshot: dict[str, Any], policy: dict[str, Any], now: int) -> dict[str, Any]:
    events: dict[str, Any] = snapshot.get("events", {})
    version = snapshot.get("version")
    reasons: list[dict[str, str]] = []
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    states: dict[str, dict[str, Any]] = {}
    ordered: list[str] = []
    marks: dict[str, int] = {}
    gaps = 0
    conflicts = 0
    skew = int(policy["max_clock_skew_seconds"])
    scope = snapshot["domain"]
    roots: list[str] = snapshot.get("heads", [])
    stack = [(eid, False) for eid in reversed(roots)]
    while stack:
        eid, closing = stack.pop()
        if closing:
            marks[eid] = 2
            ordered.append(eid)
            continue
        if marks.get(eid) == 1:
            reasons.append(reason(Code.PARENT_CYCLE, eid, "invalid"))
            continue
        if marks.get(eid) == 2:
            continue
        if len(marks) >= int(policy["max_graph_nodes"]):
            reasons.append(reason(Code.GRAPH_LIMIT, eid))
            gaps += 1
            break
        if eid not in events:
            if eid not in marks:
                gaps += 1
                reasons.append(reason(Code.PARENT_UNAVAILABLE, eid))
                marks[eid] = 2
                nodes.append({"id": eid, "label": "Missing evidence", "status": "UNKNOWN", "missing": True})
            continue
        marks[eid] = 1
        stack.append((eid, True))
        stack.extend((pid, False) for pid in reversed(events[eid]["payload"]["parentEventIds"]))

    for eid in ordered:
        item = events[eid]
        p = item["payload"]
        v = item["version"]
        actor = item.get("actor") or {}
        local: list[dict[str, str]] = []

        def add(code: Code, invalid: bool = False) -> None:
            local.append(reason(code, eid, "invalid" if invalid else "warning"))

        assurance = "A0"
        signed = False
        try:
            actual = event_hash(p, scope)
            if actual != eid or digest(item["params"]) != p["paramsHash"]:
                add(Code.EVENT_HASH_MISMATCH, True)
                add(Code.SIG_INVALID, True)
            signer = recover_event(p, scope, item["signature"])
            if not actor or signer.lower() != actor.get("signer_address", "").lower():
                add(Code.SIGNER_MISMATCH, True)
            else:
                signed = True
                assurance = "A1"
        except (ValueError, TypeError, KeyError, OverflowError):
            add(Code.SIG_INVALID, True)
        if (
            p["outputSha256"] != v["sha256"]
            or p["outputPixelSha256"] != v["pixel_sha256"]
            or int(p["outputPHash"]) != int(v["phash"]["p"], 16)
        ):
            add(Code.BINDING_MISMATCH, True)
        params = item["params"]
        if params.get("width") != v["width"] or params.get("height") != v["height"]:
            add(Code.DIMENSION_MISMATCH, True)
        if params.get("mime") != v["mime"]:
            add(Code.FORMAT_MISMATCH, True)
        anchor = item.get("anchor") or {}
        anchored_at = int(anchor.get("block_time", 0))
        anchored = anchored_at > 0 and anchor.get("actor_id") == p["actorId"]
        at = anchored_at if anchored else now
        if p["claimedAt"] > now + skew or (anchored and p["claimedAt"] > anchored_at + skew):
            add(Code.TIME_PARADOX, True)
        if actor.get("revoked_from") and at >= actor["revoked_from"]:
            add(Code.KEY_COMPROMISED_WINDOW, True)
        approved = signed and bool(actor.get("approved_at")) and actor["approved_at"] <= at
        if approved:
            assurance = "A2"
        else:
            add(Code.ACTOR_UNAPPROVED)
        parents = p["parentEventIds"]
        inputs = p["inputSha256"]
        if len(parents) != len(inputs) or (p["action"] == 1 and parents):
            add(Code.PARENT_REF_MISMATCH, True)
        if p["action"] != 1 and not parents:
            gaps += 1
            add(Code.UNATTESTED_TRANSFORMATION)
        plausible = True
        for i, parent_id in enumerate(parents):
            parent = events.get(parent_id)
            if parent:
                pv = parent["version"]
                if i >= len(inputs) or inputs[i] not in (pv["sha256"], pv["pixel_sha256"]):
                    add(Code.PARENT_REF_MISMATCH, True)
                if p["claimedAt"] < parent["payload"]["claimedAt"]:
                    add(Code.TIME_PARADOX, True)
                parent_time = (parent.get("anchor") or {}).get("block_time", 0)
                if anchored and parent_time > anchored_at:
                    add(Code.TIME_PARADOX, True)
                if p["action"] in policy["deterministic_actions"]:
                    pd = distance(v["phash"]["p"], pv["phash"]["p"])
                    if pd > int(policy.get("derivation_threshold", 24)):
                        plausible = False
                        add(Code.DERIVATION_IMPLAUSIBLE, True)
            edge_id = parent_id + ":" + eid
            edges.append(
                {
                    "id": edge_id,
                    "source": parent["version"]["id"] if parent else parent_id,
                    "target": v["id"],
                    "event_hash": eid,
                    "action": params.get("ops", []),
                    "label": str(item.get("action_name", p["action"]))
                    if parent
                    else "UNKNOWN / UNVERIFIED TRANSFORMATION",
                    "unknown": not bool(parent),
                }
            )
        first = item.get("first_claim", eid)
        conflict = first not in (ZERO, eid) and p["action"] == 1
        if conflict:
            conflicts += 1
            add(Code.CONFLICTING_ORIGIN)
        counted: dict[str, str] = {}
        for c in item.get("corroborations", []):
            try:
                org = c["org_id"]
                if not c.get("approved") or org == actor.get("org_id") or org in counted:
                    continue
                if digest(c["evidence"]) != c["evidence_hash"]:
                    add(Code.BINDING_MISMATCH, True)
                    continue
                if not c["evidence"].get("observed", False):
                    continue
                signer = recover_witness(eid, c["kind"], c["evidence_hash"], scope, c["signature"])
                if signer.lower() != c["signer"].lower() or not c.get("on_chain"):
                    continue
                if c["evidence"].get("simulated") and not snapshot.get("allow_simulated", False):
                    continue
                if c["kind"] != 1:
                    # TEE and provider-detector adapters must establish validity explicitly.
                    if not c.get("adapter_verified", False):
                        continue
                kind = {1: "WITNESS", 2: "TEE", 3: "WATERMARK"}[c["kind"]]
                counted[org] = kind
                local.append(reason(Code("CORROBORATED_BY_" + kind), eid, "info"))
            except (ValueError, TypeError, KeyError):
                add(Code.SIG_INVALID, True)
        if not anchored:
            add(Code.NOT_ANCHORED)
        if len(counted) < int(policy["independent_corroborations"]) and p["action"] in policy["ai_actions"]:
            add(Code.NO_CORROBORATION)
        if approved and anchored and not conflict and len(counted) >= int(policy["independent_corroborations"]):
            assurance = "A3"
        deterministic_ops = {"RESIZE", "CROP", "COMPRESS", "REENCODE"}
        if p["action"] in policy["deterministic_actions"] and any(
            op.get("action") not in deterministic_ops for op in params.get("ops", [])
        ):
            add(Code.DERIVATION_IMPLAUSIBLE, True)
            plausible = False
        trusted = assurance == "A3" or (approved and p["action"] in policy["deterministic_actions"] and plausible)
        if approved and item.get("gateway_replay") and parents:
            trusted = True
        invalid = any(r["severity"] == "invalid" for r in local)
        state = "INVALID" if invalid else "TRUSTED" if trusted else "SELF_ASSERTED"
        states[eid] = {
            "status": state,
            "assurance": assurance,
            "actor": actor.get("name", "Unknown signer"),
            "corroborations": list(counted.values()),
        }
        nodes.append({"id": v["id"], "label": v["id"], "status": state, "version": v, "event_hash": eid, **states[eid]})
        reasons.extend(local)

    c2pa = snapshot.get("input", {}).get("c2pa", {})
    if c2pa.get("state") == "INVALID":
        reasons.append(reason(Code.C2PA_SIGNATURE_INVALID, "upload", "invalid"))
    elif c2pa.get("state") in ("C2PA_UNAVAILABLE", "C2PA_UNEVALUABLE"):
        reasons.append(reason(Code(c2pa["state"]), "upload"))
    if not snapshot.get("audit_valid", True) and version:
        reasons.append(reason(Code.AUDIT_CHAIN_BROKEN, "audit", "invalid"))
    if not snapshot.get("chain_available", True) and ordered:
        reasons.append(reason(Code.CHAIN_UNAVAILABLE, "chain"))
    candidates = snapshot.get("candidates", [])
    if not version and candidates:
        reasons.append(reason(Code.SIMILARITY_ONLY, "upload"))
        gaps += 1
        nodes = [{"id": c["version_id"], "label": c["version_id"], "status": "UNKNOWN"} for c in candidates]
        nodes.append({"id": "upload", "label": "Current upload", "status": "UNKNOWN"})
        edges = [
            {
                "id": str(i),
                "source": c["version_id"],
                "target": "upload",
                "unknown": True,
                "label": "UNKNOWN / UNVERIFIED TRANSFORMATION",
            }
            for i, c in enumerate(candidates)
        ]
    declared = bool(version and version.get("declared_origin")) or bool(snapshot.get("metadata_claim"))
    if declared:
        reasons.append(reason(Code.SELF_DECLARED_METADATA, "upload"))
    if version and not nodes:
        nodes.append(
            {
                "id": version["id"],
                "label": version["id"],
                "status": "SELF_ASSERTED" if declared else "UNKNOWN",
                "version": version,
            }
        )
    verified = sum(s["status"] == "TRUSTED" for s in states.values())
    invalids = sum(r["severity"] == "invalid" for r in reasons)
    bound = snapshot.get("binding", {}).get("tier") in ("B1", "B2", "B3")
    if invalids:
        status = "PROVENANCE_INVALID"
    elif bound and states and verified == len(states) and gaps == 0 and conflicts == 0:
        status = "VERIFIED"
    elif verified:
        status = "PARTIALLY_VERIFIED"
    else:
        status = "UNVERIFIABLE"
    origin_events = [
        eid for eid in ordered if not events[eid]["payload"]["parentEventIds"] and events[eid]["payload"]["action"] == 1
    ]
    origin = (
        states[origin_events[0]].copy()
        if origin_events
        else {"actor": version.get("declared_origin") if version else None, "assurance": "A0", "corroborations": []}
    )
    origin_trust = (
        "TRUSTED"
        if origin.get("status") == "TRUSTED" and not invalids
        else "SELF_ASSERTED"
        if declared or origin_events
        else "UNVERIFIABLE"
    )
    if c2pa.get("valid") and not origin_events and not invalids:
        origin = {
            "actor": c2pa.get("signer", "Content Credentials signer"),
            "assurance": "A2" if c2pa.get("signer_trusted") else "A1",
            "corroborations": [],
        }
        origin_trust = "SELF_ASSERTED"
        if not c2pa.get("signer_trusted"):
            reasons.append(reason(Code.C2PA_VALID_UNTRUSTED_SIGNER, "C2PA"))
        reasons.append(reason(Code.NO_CORROBORATION, "C2PA"))
        if not nodes:
            nodes.append({"id": "upload", "label": "Embedded Content Credentials", "status": "SELF_ASSERTED", **origin})
        for i in range(int(c2pa.get("ingredients", 0))):
            parent_id = "c2pa-ingredient-" + str(i)
            nodes.append({"id": parent_id, "label": "Unresolved C2PA ingredient", "status": "UNKNOWN"})
            edges.append(
                {
                    "id": parent_id + ":upload",
                    "source": parent_id,
                    "target": nodes[0]["id"],
                    "unknown": True,
                    "label": "UNKNOWN / UNVERIFIED TRANSFORMATION",
                }
            )
            gaps += 1
    if invalids:
        origin_trust = "UNVERIFIABLE"
    for edge in edges:
        event_state = states.get(edge.get("event_hash", ""), {})
        edge["status"] = event_state.get("status", "UNKNOWN")
        if edge["status"] != "TRUSTED":
            edge["unknown"] = True
    unique_nodes = {n["id"]: n for n in nodes}
    return {
        "status": status,
        "origin_trust": origin_trust,
        "origin": origin,
        "binding": snapshot.get("binding", {"tier": "NONE"}),
        "graph": {"nodes": list(unique_nodes.values()), "edges": edges, "gaps": gaps, "conflicts": conflicts},
        "counts": {
            "verified": verified,
            "unverified": len(states) - verified,
            "gaps": gaps,
            "conflicts": conflicts,
            "tamper_warnings": invalids,
        },
        "reasons": reasons,
        "candidates": candidates,
        "privacy": {
            "private_roots_present": sum(events[eid]["payload"]["privateRoot"] != ZERO for eid in ordered),
            "plaintext_stored": False,
        },
        "simulated": bool(snapshot.get("allow_simulated"))
        and any(c["evidence"].get("simulated") for eid in ordered for c in events[eid].get("corroborations", [])),
    }
