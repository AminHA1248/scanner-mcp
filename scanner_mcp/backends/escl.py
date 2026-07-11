"""eSCL backend: driverless network scanning (a.k.a. Apple AirScan / Mopria eScan).

eSCL is an HTTP/XML protocol supported by the vast majority of modern network
multifunction printers and scanners. Devices are discovered over mDNS
(``_uscan._tcp`` / ``_uscans._tcp``) and scanned with a small set of HTTP calls:

    GET  {base}/ScannerCapabilities   -> supported resolutions / max page size
    POST {base}/ScanJobs              -> 201 Created, Location: {job}
    GET  {job}/NextDocument           -> page bytes (repeat until 404)

No vendor driver is required, which is what makes this backend "generic".
"""

from __future__ import annotations

import logging
import re
import time
import xml.etree.ElementTree as ET

import httpx

from ..models import ScannerInfo, ScanOptions, ScanResult
from .base import Backend

log = logging.getLogger("scanner_mcp.escl")

_COLOR = {"color": "RGB24", "gray": "Grayscale8", "lineart": "BlackAndWhite1"}
_FORMAT_MIME = {"png": "image/png", "jpeg": "image/jpeg", "pdf": "application/pdf"}
# eSCL scan regions are always expressed in units of 1/300 inch.
_A4_300 = (2480, 3508)


def _discover(timeout: float = 2.5) -> list[dict]:
    """Discover eSCL devices via mDNS. Returns dicts with base url + metadata."""
    try:
        from zeroconf import ServiceBrowser, ServiceListener, Zeroconf
    except Exception:
        log.debug("zeroconf unavailable; skipping eSCL discovery")
        return []

    found: dict[str, dict] = {}

    class _Listener(ServiceListener):
        def __init__(self, secure: bool):
            self.secure = secure

        def _resolve(self, zc, type_, name):
            info = zc.get_service_info(type_, name, timeout=int(timeout * 1000))
            if not info:
                return
            addrs = info.parsed_addresses() or []
            if not addrs:
                return
            host = addrs[0]
            props = {
                (k.decode() if isinstance(k, bytes) else k): (
                    v.decode(errors="replace") if isinstance(v, bytes) else v
                )
                for k, v in (info.properties or {}).items()
            }
            rs = props.get("rs", "eSCL").strip("/")
            scheme = "https" if self.secure else "http"
            base = f"{scheme}://{host}:{info.port}/{rs}"
            found[base] = {
                "base": base,
                "host": host,
                "port": info.port,
                "name": props.get("ty") or name.split(".")[0],
                "note": props.get("note", ""),
                "uuid": props.get("UUID") or props.get("uuid", ""),
            }

        def add_service(self, zc, type_, name):
            self._resolve(zc, type_, name)

        def update_service(self, zc, type_, name):
            self._resolve(zc, type_, name)

        def remove_service(self, zc, type_, name):
            pass

    zc = Zeroconf()
    try:
        ServiceBrowser(zc, "_uscan._tcp.local.", _Listener(secure=False))
        ServiceBrowser(zc, "_uscans._tcp.local.", _Listener(secure=True))
        time.sleep(timeout)
    finally:
        zc.close()
    return list(found.values())


def _strip_ns(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


class ESCLBackend(Backend):
    name = "eSCL (network / AirScan)"
    prefix = "escl"

    def __init__(self, discovery_timeout: float = 2.5):
        self._discovery_timeout = discovery_timeout

    def available(self) -> bool:
        try:
            import zeroconf  # noqa: F401
        except Exception:
            return False
        return True

    def list_scanners(self) -> list[ScannerInfo]:
        scanners = []
        for dev in _discover(self._discovery_timeout):
            scanners.append(
                ScannerInfo(
                    id=f"escl:{dev['base']}",
                    name=dev["name"],
                    backend=self.name,
                    connection="network",
                    sources=["platen", "adf"],
                    detail={k: v for k, v in dev.items() if k != "base"},
                )
            )
        return scanners

    # -- scanning -------------------------------------------------------------

    def _base_url(self, scanner_id: str) -> str:
        return scanner_id[len("escl:") :]

    def _max_region(self, client: httpx.Client, base: str) -> tuple[int, int]:
        try:
            r = client.get(f"{base}/ScannerCapabilities", timeout=10)
            r.raise_for_status()
            root = ET.fromstring(r.content)
            w = h = None
            for el in root.iter():
                tag = _strip_ns(el.tag)
                if tag == "MaxWidth" and el.text:
                    w = int(el.text)
                elif tag == "MaxHeight" and el.text:
                    h = int(el.text)
            if w and h:
                return w, h
        except Exception as exc:
            log.debug("capabilities fetch failed (%s); using A4 default", exc)
        return _A4_300

    def _build_settings(self, opts: ScanOptions, region: tuple[int, int]) -> str:
        w, h = region
        source = "Feeder" if opts.source in ("adf", "adf-duplex") else "Platen"
        duplex = "true" if opts.source == "adf-duplex" else "false"
        color = _COLOR.get(opts.color_mode, "RGB24")
        doc_format = _FORMAT_MIME.get(opts.output_format, "image/png")
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<scan:ScanSettings xmlns:scan="http://schemas.hp.com/imaging/escl/2011/05/03"
                   xmlns:pwg="http://www.pwg.org/schemas/2010/12/sm">
  <pwg:Version>2.6</pwg:Version>
  <pwg:ScanRegions pwg:MustHonor="false">
    <pwg:ScanRegion>
      <pwg:XOffset>0</pwg:XOffset>
      <pwg:YOffset>0</pwg:YOffset>
      <pwg:Width>{w}</pwg:Width>
      <pwg:Height>{h}</pwg:Height>
      <pwg:ContentRegionUnits>escl:ThreeHundredthsOfInches</pwg:ContentRegionUnits>
    </pwg:ScanRegion>
  </pwg:ScanRegions>
  <pwg:InputSource>{source}</pwg:InputSource>
  <scan:Duplex>{duplex}</scan:Duplex>
  <scan:ColorMode>{color}</scan:ColorMode>
  <scan:XResolution>{opts.resolution}</scan:XResolution>
  <scan:YResolution>{opts.resolution}</scan:YResolution>
  <pwg:DocumentFormat>{doc_format}</pwg:DocumentFormat>
  <scan:DocumentFormatExt>{doc_format}</scan:DocumentFormatExt>
</scan:ScanSettings>"""

    def scan(self, scanner_id: str, options: ScanOptions) -> ScanResult:
        base = self._base_url(scanner_id)
        verify = not base.startswith("https")  # printers ship self-signed certs
        client = httpx.Client(verify=False if base.startswith("https") else True)
        try:
            region = self._max_region(client, base)
            body = self._build_settings(options, region)
            resp = client.post(
                f"{base}/ScanJobs",
                content=body.encode("utf-8"),
                headers={"Content-Type": "text/xml"},
                timeout=30,
            )
            if resp.status_code not in (200, 201):
                raise RuntimeError(
                    f"scanner rejected job ({resp.status_code}): {resp.text[:200]}"
                )
            job = resp.headers.get("Location")
            if not job:
                raise RuntimeError("scanner did not return a job Location header")
            if job.startswith("/"):
                # Some devices return a relative path.
                root = re.match(r"^(https?://[^/]+)", base)
                job = (root.group(1) if root else base) + job

            pages = self._retrieve_pages(client, job)
            mime = _FORMAT_MIME.get(options.output_format, "image/png")
            if not pages:
                raise RuntimeError("scan produced no pages (empty feeder?)")
            return ScanResult(pages=pages, mime=mime, backend=self.name, scanner_id=scanner_id)
        finally:
            client.close()

    def _retrieve_pages(self, client: httpx.Client, job: str) -> list[bytes]:
        pages: list[bytes] = []
        for _ in range(200):  # hard cap to avoid runaway feeders
            r = client.get(f"{job}/NextDocument", timeout=120)
            if r.status_code == 404:
                break  # no more pages
            if r.status_code == 503:
                time.sleep(1.0)  # device still warming up / scanning
                continue
            r.raise_for_status()
            if not r.content:
                break
            pages.append(r.content)
        return pages
