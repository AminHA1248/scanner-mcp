"""WIA backend: Windows Image Acquisition for USB (and some network) scanners.

Windows exposes scanners through the WIA COM automation layer. Rather than depend on
pywin32, this backend drives WIA through short PowerShell scripts, so it works on a
stock Windows install. On non-Windows platforms the backend reports itself unavailable.
"""

from __future__ import annotations

import json
import logging
import platform
import subprocess
import tempfile
from pathlib import Path

from ..models import ScannerInfo, ScanOptions, ScanResult
from .base import Backend

log = logging.getLogger("scanner_mcp.wia")

# WIA image format GUIDs.
_WIA_FORMAT = {
    "png": "{B96B3CAF-0728-11D3-9D7B-0000F81EF32E}",
    "jpeg": "{B96B3CAE-0728-11D3-9D7B-0000F81EF32E}",
    "bmp": "{B96B3CAB-0728-11D3-9D7B-0000F81EF32E}",
}
# WIA_IPA_DATATYPE values.
_WIA_DATATYPE = {"lineart": 0, "gray": 2, "color": 3}

_LIST_PS = r"""
$ErrorActionPreference = 'Stop'
$dm = New-Object -ComObject WIA.DeviceManager
$out = @()
foreach ($info in $dm.DeviceInfos) {
    if ($info.Type -eq 1) {  # 1 = Scanner
        $name = ''
        foreach ($p in $info.Properties) { if ($p.Name -eq 'Name') { $name = $p.Value } }
        $out += [PSCustomObject]@{ Id = $info.DeviceID; Name = $name }
    }
}
$out | ConvertTo-Json -Compress
"""

# Placeholders filled in by _scan_ps().
_SCAN_PS = r"""
$ErrorActionPreference = 'Stop'
$deviceId = '__DEVICE_ID__'
$outDir   = '__OUT_DIR__'
$formatId = '__FORMAT_ID__'
$ext      = '__EXT__'
$dpi      = __DPI__
$dataType = __DATATYPE__
$useAdf   = [bool]__USE_ADF__

function Set-WiaProp($props, $id, $value) {
    foreach ($p in $props) { if ($p.PropertyID -eq $id) { try { $p.Value = $value } catch {} ; return } }
}

$dm = New-Object -ComObject WIA.DeviceManager
$devInfo = $null
foreach ($info in $dm.DeviceInfos) { if ($info.DeviceID -eq $deviceId) { $devInfo = $info } }
if ($null -eq $devInfo) { throw "scanner not found: $deviceId" }
$device = $devInfo.Connect()

# Document handling: 1 = Feeder, 2 = Flatbed (WIA_DPS_DOCUMENT_HANDLING_SELECT = 3088).
if ($useAdf) { Set-WiaProp $device.Properties 3088 1 } else { Set-WiaProp $device.Properties 3088 2 }

$saved = @()
$page = 0
while ($true) {
    $page++
    if ($page -gt 100) { break }
    try {
        $item = $device.Items.Item(1)
    } catch { break }

    Set-WiaProp $item.Properties 6147 $dpi        # horizontal resolution
    Set-WiaProp $item.Properties 6148 $dpi        # vertical resolution
    Set-WiaProp $item.Properties 4103 $dataType   # WIA_IPA_DATATYPE

    try {
        $image = $item.Transfer($formatId)
    } catch {
        if ($page -eq 1) { throw }   # nothing scanned at all -> real error
        break                        # feeder empty -> normal end
    }

    $path = Join-Path $outDir ("page-{0}.{1}" -f $page, $ext)
    if (Test-Path $path) { Remove-Item $path -Force }
    $image.SaveFile($path)
    $saved += $path

    if (-not $useAdf) { break }      # flatbed = single page

    # Stop if the feeder reports no more pages (WIA_DPS_DOCUMENT_HANDLING_STATUS = 3087, bit 1 = feed ready).
    $status = 0
    foreach ($p in $device.Properties) { if ($p.PropertyID -eq 3087) { $status = $p.Value } }
    if (($status -band 1) -eq 0) { break }
}
($saved | ConvertTo-Json -Compress)
"""


class WIABackend(Backend):
    name = "WIA (Windows)"
    prefix = "wia"

    def available(self) -> bool:
        return platform.system() == "Windows"

    # -- helpers --------------------------------------------------------------

    @staticmethod
    def _run_ps(script: str, timeout: int = 600) -> str:
        with tempfile.NamedTemporaryFile("w", suffix=".ps1", delete=False, encoding="utf-8") as f:
            f.write(script)
            script_path = f.name
        try:
            proc = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    script_path,
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if proc.returncode != 0:
                raise RuntimeError((proc.stderr or proc.stdout or "PowerShell error").strip())
            return proc.stdout.strip()
        finally:
            try:
                Path(script_path).unlink()
            except OSError:
                pass

    # -- API ------------------------------------------------------------------

    def list_scanners(self) -> list[ScannerInfo]:
        try:
            out = self._run_ps(_LIST_PS, timeout=30)
        except Exception as exc:
            log.debug("WIA list failed: %s", exc)
            return []
        if not out:
            return []
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            return []
        if isinstance(data, dict):
            data = [data]
        scanners = []
        for d in data:
            scanners.append(
                ScannerInfo(
                    id=f"wia:{d['Id']}",
                    name=d.get("Name") or "WIA Scanner",
                    backend=self.name,
                    connection="usb",
                    sources=["platen", "adf"],
                    detail={"device_id": d["Id"]},
                )
            )
        return scanners

    def scan(self, scanner_id: str, options: ScanOptions) -> ScanResult:
        device_id = scanner_id[len("wia:") :]
        # WIA only writes image formats; PDF is assembled by the server layer.
        want_pdf = options.output_format == "pdf"
        img_fmt = "jpeg" if options.output_format == "jpeg" else "png"
        format_id = _WIA_FORMAT[img_fmt]
        datatype = _WIA_DATATYPE.get(options.color_mode, 3)
        use_adf = options.source in ("adf", "adf-duplex")

        with tempfile.TemporaryDirectory(prefix="scanmcp_") as td:
            script = (
                _SCAN_PS.replace("__DEVICE_ID__", device_id.replace("'", "''"))
                .replace("__OUT_DIR__", td.replace("\\", "\\\\"))
                .replace("__FORMAT_ID__", format_id)
                .replace("__EXT__", img_fmt)
                .replace("__DPI__", str(int(options.resolution)))
                .replace("__DATATYPE__", str(datatype))
                .replace("__USE_ADF__", "$true" if use_adf else "$false")
            )
            out = self._run_ps(script)
            try:
                saved = json.loads(out) if out else []
            except json.JSONDecodeError:
                saved = []
            if isinstance(saved, str):
                saved = [saved]
            raw_pages = [Path(p).read_bytes() for p in saved if Path(p).exists()]

        if not raw_pages:
            raise RuntimeError("WIA scan produced no output (is paper loaded / lid closed?)")

        # Many WIA drivers ignore the requested format GUID and hand back a BMP.
        # Normalize every page to the requested image format so callers always get
        # valid PNG/JPEG bytes (and a much smaller file than raw BMP).
        from ..imaging import convert_image, have_pil, images_to_pdf

        if have_pil():
            pages = [convert_image(p, img_fmt) for p in raw_pages]
        else:
            pages = raw_pages  # best effort; bytes may actually be BMP

        mime = f"image/{img_fmt}"
        if want_pdf:
            pages = [images_to_pdf(pages)]
            mime = "application/pdf"
        return ScanResult(pages=pages, mime=mime, backend=self.name, scanner_id=scanner_id)
