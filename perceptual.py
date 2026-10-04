import imagehash
import numpy as np
from PIL import Image


def hashes(image: Image.Image) -> dict[str, str]:
    return {"d": str(imagehash.dhash(image)), "p": str(imagehash.phash(image)), "w": str(imagehash.whash(image))}


def distance(left: str, right: str) -> int:
    return (int(left, 16) ^ int(right, 16)).bit_count()


def search(
    query: dict[str, str], records: list[tuple[str, dict[str, str]]], threshold: int, limit: int = 10
) -> list[dict[str, object]]:
    if not records:
        return []
    matrix = np.array([[int(h[k], 16) for k in ("d", "p", "w")] for _, h in records], dtype=np.uint64)
    target = np.array([int(query[k], 16) for k in ("d", "p", "w")], dtype=np.uint64)
    x = np.bitwise_xor(matrix, target)
    counts = np.unpackbits(x.view(np.uint8).reshape(-1, 3, 8), axis=2).sum(axis=2)
    votes = np.sort(counts, axis=1)[:, 1]  # median: at least two independent hash families agree
    order = np.argsort(votes, kind="stable")
    return [
        {"version_id": records[int(i)][0], "hamming": int(votes[i]), "relationship": "UNVERIFIED"}
        for i in order
        if votes[i] <= threshold
    ][:limit]
