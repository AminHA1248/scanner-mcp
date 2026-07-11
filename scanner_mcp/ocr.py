"""Optional OCR via pytesseract. Returns None if OCR is unavailable."""

from __future__ import annotations

import io


def ocr_available() -> bool:
    try:
        import pytesseract  # type: ignore
        from PIL import Image  # noqa: F401

        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def ocr_image(data: bytes) -> str | None:
    try:
        import pytesseract  # type: ignore
        from PIL import Image  # type: ignore
    except Exception:
        return None
    try:
        with Image.open(io.BytesIO(data)) as im:
            return pytesseract.image_to_string(im).strip()
    except Exception:
        return None
