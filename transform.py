import io

from PIL import Image, ImageEnhance, ImageFilter

from app.core.pixelhash import MAX_PIXELS, decode


def apply(data, ops):
    image, mime = decode(data)
    fmt = {"image/png": "PNG", "image/jpeg": "JPEG", "image/webp": "WEBP"}[mime]
    quality = 90
    for op in ops:
        action = op.action
        if action == "RESIZE":
            if not op.width or not op.height or op.width * op.height > MAX_PIXELS:
                raise ValueError("Resize requires width and height within pixel limit")
            image = image.resize((op.width, op.height), Image.Resampling.LANCZOS)
        elif action == "CROP":
            if not op.box:
                raise ValueError("Crop requires [left, top, right, bottom]")
            left, top, right, bottom = op.box
            if not (0 <= left < right <= image.width and 0 <= top < bottom <= image.height):
                raise ValueError("Crop box outside image bounds")
            image = image.crop(tuple(op.box))
        elif action == "BLUR":
            image = image.filter(ImageFilter.GaussianBlur(op.radius if op.radius is not None else 1))
        elif action == "FILTER":
            image = ImageEnhance.Contrast(image).enhance(op.factor if op.factor is not None else 1)
        elif action not in ("COMPRESS", "REENCODE"):
            raise ValueError("Gateway supports resize, crop, blur, contrast, compress and reencode")
        if op.format:
            fmt = op.format
        if op.quality:
            quality = op.quality
    if fmt == "JPEG":
        image = image.convert("RGB")
    output = io.BytesIO()
    image.save(output, format=fmt, quality=quality)
    return output.getvalue()
