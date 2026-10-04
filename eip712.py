from typing import Any

from eth_account import Account
from eth_account.messages import encode_defunct, encode_typed_data
from eth_utils.crypto import keccak

from app.core.canonical import canonical
from app.core.hashing import sha256

ZERO = "0x" + "00" * 32
EVENT_TYPES = {
    "Event": [
        {"name": name, "type": kind}
        for name, kind in [
            ("actorId", "bytes32"),
            ("action", "uint8"),
            ("modelRef", "bytes32"),
            ("parentEventIds", "bytes32[]"),
            ("inputSha256", "bytes32[]"),
            ("outputSha256", "bytes32"),
            ("outputPixelSha256", "bytes32"),
            ("outputPHash", "uint64"),
            ("paramsHash", "bytes32"),
            ("privateRoot", "bytes32"),
            ("claimedAt", "uint64"),
            ("nonce", "bytes32"),
        ]
    ]
}
WITNESS_TYPES = {
    "Witness": [
        {"name": name, "type": kind}
        for name, kind in [("eventHash", "bytes32"), ("kind", "uint8"), ("evidenceHash", "bytes32")]
    ]
}


def domain(chain_id: int, contract: str) -> dict[str, Any]:
    return {"name": "ModelLedger", "version": "1", "chainId": chain_id, "verifyingContract": contract}


def event_hash(payload: dict[str, Any], scope: dict[str, Any]) -> str:
    encoded = encode_typed_data(scope, EVENT_TYPES, payload)
    return "0x" + keccak(b"\x19" + encoded.version + encoded.header + encoded.body).hex()


def sign_event(payload: dict[str, Any], scope: dict[str, Any], key: str) -> str:
    return str("0x" + Account.sign_message(encode_typed_data(scope, EVENT_TYPES, payload), key).signature.hex())


def recover_event(payload: dict[str, Any], scope: dict[str, Any], signature: str) -> str:
    return str(Account.recover_message(encode_typed_data(scope, EVENT_TYPES, payload), signature=signature))


def sign_witness(event: str, kind: int, evidence: str, scope: dict[str, Any], key: str) -> str:
    message = {"eventHash": event, "kind": kind, "evidenceHash": evidence}
    return str("0x" + Account.sign_message(encode_typed_data(scope, WITNESS_TYPES, message), key).signature.hex())


def recover_witness(event: str, kind: int, evidence: str, scope: dict[str, Any], signature: str) -> str:
    message = {"eventHash": event, "kind": kind, "evidenceHash": evidence}
    return str(Account.recover_message(encode_typed_data(scope, WITNESS_TYPES, message), signature=signature))


def sign_report(report: dict[str, Any], key: str) -> str:
    return str("0x" + Account.sign_message(encode_defunct(hexstr=sha256(canonical(report))), key).signature.hex())


def recover_report(report: dict[str, Any], signature: str) -> str:
    return str(Account.recover_message(encode_defunct(hexstr=sha256(canonical(report))), signature=signature))
