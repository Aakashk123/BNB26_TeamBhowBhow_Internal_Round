import io
import struct
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.hashing import sha256

MAX_BYTES = 25 * 1024 * 1024
MAX_PIXELS = 25_000_000
Image.MAX_IMAGE_PIXELS = MAX_PIXELS
ALLOWED = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}


def decode(data: bytes) -> tuple[Image.Image, str]:
    if not data or len(data) > MAX_BYTES:
        raise ValueError("Image must contain 1 byte to 25 MiB")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as source:
                if source.format not in ALLOWED or getattr(source, "is_animated", False):
                    raise ValueError("Only static PNG, JPEG and WebP images are supported")
                if source.width * source.height > MAX_PIXELS:
                    raise ValueError("Image exceeds 25 million pixels")
                mime = ALLOWED[source.format]
                source.load()
                oriented = ImageOps.exif_transpose(source)
                mode = "RGBA" if "A" in oriented.getbands() or "transparency" in oriented.info else "RGB"
                return oriented.convert(mode), mime
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ValueError("Unsafe or undecodable image") from exc


def pixel_sha256(image: Image.Image) -> str:
    header = b"ModelLedgerPixels/v1\0" + struct.pack(">II", image.width, image.height) + image.mode.encode() + b"\0"
    return sha256(header + image.tobytes())
