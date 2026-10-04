import secrets

from eth_utils.crypto import keccak

from .merkle import proof, tree, verify

FIELDS = {"prompt", "negative_prompt", "seed", "sampler_params", "source_file_sha256", "operator_id"}


def leaf(field: str, value: str, salt: str) -> bytes:
    raw = bytes.fromhex(salt.removeprefix("0x"))
    if field not in FIELDS or len(raw) != 16:
        raise ValueError("Unknown private field or invalid salt")
    return bytes(keccak(keccak(text=field) + raw + keccak(text=value)))


def commit(values: dict[str, str]) -> tuple[str, list[dict[str, object]]]:
    if not values or not values.keys() <= FIELDS:
        raise ValueError("One to six supported private fields required")
    records = [
        {"field": field, "value": value, "salt": "0x" + secrets.token_hex(16)}
        for field, value in sorted(values.items())
    ]
    leaves = [leaf(r["field"], r["value"], r["salt"]) for r in records]
    leaves.extend(secrets.token_bytes(32) for _ in range(8 - len(leaves)))
    levels = tree(leaves)
    packages: list[dict[str, object]] = [{**r, "proof": proof(levels, i)} for i, r in enumerate(records)]
    return "0x" + levels[-1][0].hex(), packages


def disclose(field: str, value: str, salt: str, siblings: list[str], root: str) -> bool:
    try:
        return len(siblings) == 3 and verify(leaf(field, value, salt), siblings, root)
    except ValueError:
        return False
