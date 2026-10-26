"""Validate and normalise uploaded images. Images are processed in memory only."""
import base64
import io

from PIL import Image, ImageOps, UnidentifiedImageError

from errors import ApiError

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}
FORMAT_OK = {"JPEG", "PNG", "WEBP"}
MAX_SIDE = 1600
Image.MAX_IMAGE_PIXELS = 40_000_000


def prepare_image(data, filename, mimetype):
    """Return base64 (no data: prefix) of a re-encoded JPEG, or raise ApiError(400)."""
    name = (filename or "").lower()
    ext = name[name.rfind("."):] if "." in name else ""
    if ext not in ALLOWED_EXT:
        raise ApiError("Unsupported file type. Use a JPG, JPEG, PNG or WEBP image.", "bad_image", 400)
    if (mimetype or "").lower() not in ALLOWED_MIME:
        raise ApiError("Unsupported image content type. Use JPG, PNG or WEBP.", "bad_image", 400)
    if not data:
        raise ApiError("The uploaded image is empty.", "bad_image", 400)
    try:
        img = Image.open(io.BytesIO(data))
        if img.format not in FORMAT_OK:
            raise ApiError("The file is not a valid JPG, PNG or WEBP image.", "bad_image", 400)
        img.load()
    except ApiError:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, ValueError):
        raise ApiError("The file could not be read as an image. It may be corrupt or too large.", "bad_image", 400)
    img = ImageOps.exif_transpose(img)  # also drops EXIF (location etc.) when re-encoding
    if img.mode not in ("RGB", "L"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        rgba = img.convert("RGBA")
        background.paste(rgba, mask=rgba.split()[3])
        img = background
    else:
        img = img.convert("RGB")
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode("ascii")
