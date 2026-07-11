"""Image helpers: format conversion and combining pages into a PDF.

All functions degrade gracefully if Pillow is unavailable so that a backend which
already produces the requested format keeps working without the optional dependency.
"""

from __future__ import annotations

import io

try:
    from PIL import Image  # type: ignore

    _HAVE_PIL = True
except Exception:  # pragma: no cover - optional dependency
    _HAVE_PIL = False


def have_pil() -> bool:
    return _HAVE_PIL


def convert_image(data: bytes, target: str) -> bytes:
    """Convert a single image to ``target`` format ('png' or 'jpeg')."""
    if not _HAVE_PIL:
        return data
    fmt = "JPEG" if target.lower() in ("jpg", "jpeg") else "PNG"
    with Image.open(io.BytesIO(data)) as im:
        if fmt == "JPEG" and im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        out = io.BytesIO()
        im.save(out, format=fmt)
        return out.getvalue()


def images_to_pdf(pages: list[bytes]) -> bytes:
    """Combine one or more image pages into a single PDF."""
    if not _HAVE_PIL:
        raise RuntimeError(
            "Pillow is required to build a PDF from image pages. Install with 'pip install pillow'."
        )
    if not pages:
        raise ValueError("no pages to combine")
    imgs = []
    for data in pages:
        im = Image.open(io.BytesIO(data))
        imgs.append(im.convert("RGB"))
    out = io.BytesIO()
    imgs[0].save(out, format="PDF", save_all=True, append_images=imgs[1:])
    return out.getvalue()
