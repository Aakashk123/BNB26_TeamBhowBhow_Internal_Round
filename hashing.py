import hashlib


def sha256(data: bytes) -> str:
    return "0x" + hashlib.sha256(data).hexdigest()
