"""EXPERIMENTAL keyed watermark spike. Never a binding or a production trust signal."""

import hashlib
import hmac

import numpy as np
from numpy.typing import NDArray
from PIL import Image, ImageFilter


def pattern(key: bytes, size: tuple[int, int]) -> NDArray[np.float64]:
    if len(key) < 16:
        raise ValueError("Watermark key must contain at least 128 bits")
    seed = int.from_bytes(hmac.new(key, b"modelledger-watermark-experimental-v1", hashlib.sha256).digest()[:8], "big")
    rng = np.random.default_rng(seed)
    raw = (
        Image.fromarray(rng.integers(0, 256, (256, 256), dtype=np.uint8))
        .filter(ImageFilter.GaussianBlur(0.7))
        .resize(size)
    )
    p = np.asarray(raw, dtype=np.float64)
    p -= p.mean()
    return p / max(float(p.std()), 1e-9)


def embed(image: Image.Image, key: bytes, amplitude: float = 1.5) -> Image.Image:
    if not 0 < amplitude <= 3:
        raise ValueError("Experimental amplitude must be in (0, 3]")
    rgb = np.asarray(image.convert("RGB"), dtype=np.float64)
    signal = pattern(key, image.size)[..., None]
    return Image.fromarray(np.clip(rgb + amplitude * signal, 0, 255).astype(np.uint8))


def score(image: Image.Image, key: bytes) -> float:
    gray = image.convert("L").resize((256, 256))
    residual = np.asarray(gray, dtype=np.float64) - np.asarray(
        gray.filter(ImageFilter.GaussianBlur(2)), dtype=np.float64
    )
    p = pattern(key, (256, 256))
    return float(np.sum(residual * p) / max(float(np.linalg.norm(residual)), 1e-9))
