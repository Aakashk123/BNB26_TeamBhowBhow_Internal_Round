from eth_utils.crypto import keccak


def pair(left: bytes, right: bytes) -> bytes:
    return bytes(keccak(min(left, right) + max(left, right)))


def tree(leaves: list[bytes]) -> list[list[bytes]]:
    if not leaves or len(leaves) & (len(leaves) - 1):
        raise ValueError("Use a nonempty power-of-two leaf count")
    if any(len(leaf) != 32 for leaf in leaves):
        raise ValueError("Each leaf must be 32 bytes")
    levels = [leaves[:]]
    while len(levels[-1]) > 1:
        row = levels[-1]
        levels.append([pair(row[i], row[i + 1]) for i in range(0, len(row), 2)])
    return levels


def proof(levels: list[list[bytes]], index: int) -> list[str]:
    if not 0 <= index < len(levels[0]):
        raise ValueError("Leaf index out of range")
    result = []
    for row in levels[:-1]:
        result.append("0x" + row[index ^ 1].hex())
        index //= 2
    return result


def verify(leaf: bytes, siblings: list[str], root: str) -> bool:
    try:
        if len(leaf) != 32 or len(siblings) > 32:
            return False
        for sibling in siblings:
            other = bytes.fromhex(sibling.removeprefix("0x"))
            if len(other) != 32:
                return False
            leaf = pair(leaf, other)
        return "0x" + leaf.hex() == root.lower()
    except ValueError:
        return False
