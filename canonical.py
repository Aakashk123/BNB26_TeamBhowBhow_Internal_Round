"""RFC 8785 canonical JSON; floats outside JCS are rejected by the library."""

from typing import Any

import rfc8785
from eth_utils.crypto import keccak


def canonical(value: Any) -> bytes:
    return bytes(rfc8785.dumps(value))


def digest(value: Any) -> str:
    return "0x" + keccak(canonical(value)).hex()
