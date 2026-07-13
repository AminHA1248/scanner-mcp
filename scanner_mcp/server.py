"""MCP server exposing scan tools over every available backend.

Tools:
  * list_scanners   - discover scanners across all backends
  * scan_document   - scan and return the pages (inline images for Claude to read,
                      and/or a saved file, and/or OCR'd text)

Run over stdio (how Claude Desktop / Claude Code launch it):  ``scanner-mcp``
"""

from __future__ import annotations

import datetime as _dt
import json
import logging
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp import Image as MCPImage

from .backends import all_backends, backend_for
from .imaging import have_pil
from .models import ScanOptions
from .ocr import ocr_available, ocr_image

# Treat empty env values (e.g. from an unset bundle user_config field) as unset.
logging.basicConfig(level=os.environ.get("SCANNER_MCP_LOG") or "INFO")
log = logging.getLogger("scanner_mcp")

mcp = FastMCP("scanner")

#: Where scans are saved when the caller doesn't specify save_dir.
_DEFAULT_SAVE_DIR = Path(os.environ.get("SCANNER_MCP_SAVE_DIR") or (Path.home() / "Scans"))
#: Cap on how many page images we inline back to the model, to bound response size.
_MAX_INLINE_PAGES = 10

_EXT = {"image/png": "png", "image/jpeg": "jpg", "application/pdf": "pdf"}


@mcp.tool()
def list_scanners() -> str:
    """List all scanners reachable from this machine.

    Discovers network scanners over mDNS (eSCL/AirScan) and local USB scanners via the
    platform driver stack (WIA on Windows, SANE on Linux/macOS). Returns a JSON array of
    scanners with their ``id`` (pass this to ``scan_document``), ``name``, ``backend``,
    ``connection`` type and supported ``sources``.
    """
    scanners = []
    active = []
    for backend in all_backends():
        active.append(backend.name)
        try:
            for s in backend.list_scanners():
                scanners.append(s.to_dict())
        except Exception as exc:
            log.warning("backend %s failed to list: %s", backend.name, exc)
    return json.dumps(
        {"backends_active": active, "count": len(scanners), "scanners": scanners},
        indent=2,
    )


@mcp.tool()
def scan_document(
    scanner_id: str = "",
    source: str = "auto",
    resolution: int = 300,
    color_mode: str = "color",
    output_format: str = "png",
    save_dir: str = "",
    return_image: bool = True,
    ocr: bool = False,
) -> list:
    """Scan a document and return it so Claude can read it.

    Args:
        scanner_id: Which scanner to use (from ``list_scanners``). If omitted and exactly
            one scanner is found, that one is used; if several are found, an error lists them.
        source: ``auto`` | ``platen`` (flatbed glass) | ``adf`` (document feeder) |
            ``adf-duplex`` (feeder, both sides).
        resolution: DPI (150 fast, 300 documents, 600 fine). Default 300.
        color_mode: ``color`` | ``gray`` | ``lineart`` (1-bit black & white).
        output_format: ``png`` | ``jpeg`` | ``pdf``. PDF is best for multi-page archives;
            images let Claude view the page inline.
        save_dir: Folder to save the scan in. Defaults to ~/Scans (or $SCANNER_MCP_SAVE_DIR).
        return_image: If true and the output is an image, the page images are returned
            inline so Claude can read the document directly. Ignored for PDF.
        ocr: If true, also OCR each page to text (requires Tesseract + pytesseract).

    Returns a summary plus, when applicable, inline page images and/or OCR text.
    """
    if source not in ("auto", "platen", "adf", "adf-duplex"):
        raise ValueError(f"invalid source: {source!r}")
    if color_mode not in ("color", "gray", "lineart"):
        raise ValueError(f"invalid color_mode: {color_mode!r}")
    if output_format not in ("png", "jpeg", "pdf"):
        raise ValueError(f"invalid output_format: {output_format!r}")

    scanner_id = scanner_id or _autoselect()
    backend = backend_for(scanner_id)
    if backend is None:
        raise ValueError(
            f"no backend owns scanner id {scanner_id!r}. Run list_scanners to see valid ids."
        )

    if output_format == "pdf" and not have_pil() and backend.prefix in ("wia",):
        raise RuntimeError("PDF output needs Pillow installed (pip install pillow).")

    opts = ScanOptions(
        source=source,  # type: ignore[arg-type]
        resolution=int(resolution),
        color_mode=color_mode,  # type: ignore[arg-type]
        output_format=output_format,  # type: ignore[arg-type]
    )
    result = backend.scan(scanner_id, opts)

    saved_paths = _save(result.pages, result.mime, save_dir)

    summary = {
        "status": "ok",
        "scanner_id": scanner_id,
        "backend": result.backend,
        "pages": len(result.pages),
        "mime": result.mime,
        "saved_to": [str(p) for p in saved_paths],
    }

    content: list = []

    # Inline images so the model can actually read the document.
    is_image = result.mime.startswith("image/")
    if return_image and is_image:
        img_fmt = "jpeg" if result.mime == "image/jpeg" else "png"
        for data in result.pages[:_MAX_INLINE_PAGES]:
            content.append(MCPImage(data=data, format=img_fmt))
        if len(result.pages) > _MAX_INLINE_PAGES:
            summary["note"] = (
                f"only first {_MAX_INLINE_PAGES} of {len(result.pages)} pages shown inline; "
                "all pages were saved to disk."
            )
    elif return_image and result.mime == "application/pdf":
        summary["note"] = "PDF cannot be shown inline; open the saved file or rescan as png to view."

    # Optional OCR.
    if ocr:
        if not ocr_available():
            summary["ocr"] = "unavailable (install tesseract-ocr and pytesseract)"
        elif is_image:
            texts = [ocr_image(p) or "" for p in result.pages]
            summary["ocr"] = "included below"
            joined = "\n\n".join(f"--- page {i+1} ---\n{t}" for i, t in enumerate(texts))
            content.append(f"OCR text:\n{joined}")
        else:
            summary["ocr"] = "OCR only supported for image output_format (use png/jpeg)"

    content.insert(0, json.dumps(summary, indent=2))
    return content


def _autoselect() -> str:
    scanners = []
    for backend in all_backends():
        try:
            scanners.extend(backend.list_scanners())
        except Exception:
            continue
    if not scanners:
        raise RuntimeError("no scanners found. Ensure the scanner is powered on and on the same network/USB.")
    if len(scanners) > 1:
        listing = "; ".join(f"{s.name} ({s.id})" for s in scanners)
        raise RuntimeError(f"multiple scanners found — pass scanner_id. Options: {listing}")
    return scanners[0].id


def _save(pages: list[bytes], mime: str, save_dir: str) -> list[Path]:
    target = Path(save_dir) if save_dir else _DEFAULT_SAVE_DIR
    target.mkdir(parents=True, exist_ok=True)
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    ext = _EXT.get(mime, "bin")
    out: list[Path] = []
    if mime == "application/pdf":
        p = target / f"scan-{stamp}.pdf"
        p.write_bytes(pages[0])
        out.append(p)
    else:
        for i, data in enumerate(pages, 1):
            suffix = "" if len(pages) == 1 else f"-p{i}"
            p = target / f"scan-{stamp}{suffix}.{ext}"
            p.write_bytes(data)
            out.append(p)
    return out


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
