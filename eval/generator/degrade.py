"""Turn a rendered report into a phone photo (plan 14.2 step 3): clean, or degraded with a slight rotation, blur,
an uneven shadow and heavy JPEG compression, like a WhatsApp forward."""
import io
import random

import pymupdf
from PIL import Image, ImageFilter


def to_photo(pdf: bytes, rng: random.Random, degraded: bool, dpi: int = 150) -> bytes:
    with pymupdf.open(stream=pdf, filetype="pdf") as doc:
        pix = doc[0].get_pixmap(dpi=dpi)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    quality = 90
    if degraded:
        img = img.rotate(rng.uniform(-5, 5), resample=Image.BICUBIC, expand=True, fillcolor=(235, 235, 230))
        img = img.filter(ImageFilter.GaussianBlur(rng.uniform(0.4, 1.1)))
        img = _shadow(img, rng.uniform(0.55, 0.85))
        quality = rng.randint(40, 70)
    out = io.BytesIO()
    img.save(out, "JPEG", quality=quality)
    return out.getvalue()


def _shadow(img: Image.Image, darkest: float) -> Image.Image:
    """Darker towards one side, as when a phone shades the page."""
    w, h = img.size
    gradient = Image.linear_gradient("L").rotate(90).resize((w, h))  # rotate while square: no black corners
    mask = gradient.point(lambda p: int(255 * (darkest + (1 - darkest) * p / 255)))
    return Image.composite(img, Image.new("RGB", img.size, (0, 0, 0)), mask)
