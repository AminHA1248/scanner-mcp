"""TWAIN backend: Windows scanners exposed through the legacy TWAIN API.

Complements WIA. Some scanners — often older units, or professional document
scanners — ship only a TWAIN data source and no usable WIA driver. This backend
reaches those through the optional ``pytwain`` package (imported as ``twain``).

Requirements (all Windows-only):
  * ``pip install "scanner-mcp[twain]"`` (installs pytwain), and
  * a TWAIN **DSM** (Data Source Manager) present on the system:
      - 64-bit Python needs ``TWAINDSM.dll`` (shipped by TWAIN 2.x drivers or the
        TWAIN DSM redistributable), or
      - use 32-bit Python, which can load the classic ``twain_32.dll``.

If pytwain is missing or no DSM/driver is installed, the backend simply reports
itself unavailable and is skipped — the rest of the server keeps working.
"""

from __future__ import annotations

import logging
import platform

from ..models import ScannerInfo, ScanOptions, ScanResult
from .base import Backend

log = logging.getLogger("scanner_mcp.twain")

# pytwain logs a noisy INFO/ERROR pair when no TWAIN DSM is installed (the common
# case on machines with only WIA scanners). Keep our own graceful handling; hush its.
logging.getLogger("twain").setLevel(logging.CRITICAL)

# TWAIN pixel types: TWPT_BW=0, TWPT_GRAY=1, TWPT_RGB=2.
_PIXELTYPE = {"color": 2, "gray": 1, "lineart": 0}


def _desktop_hwnd():
    """A window handle for the TWAIN source manager; TWAIN requires one."""
    import ctypes

    try:
        return ctypes.windll.user32.GetDesktopWindow()
    except Exception:
        return 0


class TWAINBackend(Backend):
    name = "TWAIN (Windows)"
    prefix = "twain"

    def __init__(self):
        self._avail: bool | None = None  # cached availability probe

    # -- availability ---------------------------------------------------------

    def available(self) -> bool:
        if self._avail is not None:
            return self._avail
        self._avail = self._probe()
        return self._avail

    def _probe(self) -> bool:
        if platform.system() != "Windows":
            return False
        try:
            import twain  # noqa: F401
        except Exception:
            log.debug("pytwain not installed; TWAIN backend disabled")
            return False
        # The DSM only loads if a TWAIN data-source manager is actually installed.
        sm = None
        try:
            sm = self._open_sm()
            return True
        except Exception as exc:
            log.debug("TWAIN DSM not available (%s); backend disabled", exc)
            return False
        finally:
            self._close(sm)

    # -- helpers --------------------------------------------------------------

    @staticmethod
    def _open_sm():
        import twain

        return twain.SourceManager(_desktop_hwnd())

    @staticmethod
    def _close(obj) -> None:
        if obj is None:
            return
        try:
            obj.close()
        except Exception:
            try:
                obj.destroy()
            except Exception:
                pass

    @staticmethod
    def _set_cap(src, cap: int, type_id: int, value) -> None:
        """Set a capability, ignoring sources that don't support it."""
        try:
            src.set_capability(cap, type_id, value)
        except Exception as exc:
            log.debug("capability %s not set: %s", cap, exc)

    # -- API ------------------------------------------------------------------

    def list_scanners(self) -> list[ScannerInfo]:
        if not self.available():
            return []
        sm = None
        try:
            sm = self._open_sm()
            names = list(sm.source_list)
        except Exception as exc:
            log.debug("TWAIN source enumeration failed: %s", exc)
            return []
        finally:
            self._close(sm)

        scanners = []
        for name in names:
            scanners.append(
                ScannerInfo(
                    id=f"twain:{name}",
                    name=name,
                    backend=self.name,
                    connection="unknown",
                    sources=["platen", "adf"],
                    detail={"source": name},
                )
            )
        return scanners

    def scan(self, scanner_id: str, options: ScanOptions) -> ScanResult:
        import twain

        source_name = scanner_id[len("twain:") :]
        sm = None
        src = None
        try:
            sm = self._open_sm()
            src = sm.open_source(source_name)
            if src is None:
                raise RuntimeError(f"could not open TWAIN source {source_name!r}")

            self._configure(src, options, twain)

            # Non-UI acquisition: don't pop the driver's dialog.
            src.request_acquire(show_ui=False, modal_ui=False)

            raw_pages = self._transfer(src, twain, multipage=options.source in ("adf", "adf-duplex"))
        finally:
            self._close(src)
            self._close(sm)

        if not raw_pages:
            raise RuntimeError("TWAIN scan produced no images (empty feeder or cancelled?)")

        # TWAIN native transfer yields BMP (DIB) bytes; normalize to the requested format.
        from ..imaging import convert_image, have_pil, images_to_pdf

        want_pdf = options.output_format == "pdf"
        img_fmt = "jpeg" if options.output_format == "jpeg" else "png"
        if have_pil():
            pages = [convert_image(p, img_fmt) for p in raw_pages]
        else:
            pages = raw_pages  # best effort; bytes are BMP

        mime = f"image/{img_fmt}"
        if want_pdf:
            pages = [images_to_pdf(pages)]
            mime = "application/pdf"
        return ScanResult(pages=pages, mime=mime, backend=self.name, scanner_id=scanner_id)

    def _configure(self, src, options: ScanOptions, twain) -> None:
        self._set_cap(src, twain.ICAP_PIXELTYPE, twain.TWTY_UINT16,
                      _PIXELTYPE.get(options.color_mode, 2))
        for cap in (twain.ICAP_XRESOLUTION, twain.ICAP_YRESOLUTION):
            self._set_cap(src, cap, twain.TWTY_FIX32, float(options.resolution))

        use_adf = options.source in ("adf", "adf-duplex")
        self._set_cap(src, twain.CAP_FEEDERENABLED, twain.TWTY_BOOL, 1 if use_adf else 0)
        if options.source == "adf-duplex":
            self._set_cap(src, twain.CAP_DUPLEXENABLED, twain.TWTY_BOOL, 1)

    @staticmethod
    def _transfer(src, twain, multipage: bool) -> list[bytes]:
        pages: list[bytes] = []
        for _ in range(200):  # hard cap against runaway feeders
            try:
                handle, pending = src.xfer_image_natively()
            except Exception as exc:
                # Raised when the source has no (more) images to transfer.
                log.debug("native transfer ended: %s", exc)
                break
            try:
                bmp = twain.dib_to_bm_file(handle)  # path=None -> returns BMP bytes
                if bmp:
                    pages.append(bmp)
            finally:
                try:
                    twain.global_handle_free(handle)
                except Exception:
                    pass
            if not multipage or pending == 0:
                break
        return pages
