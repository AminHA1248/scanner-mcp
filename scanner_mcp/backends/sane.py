"""SANE backend: wraps the ``scanimage`` CLI (Linux, and macOS via Homebrew).

Covers most USB scanners plus many network scanners through SANE's own backends.
Requires the ``sane-utils`` package (provides ``scanimage``); if it is not on PATH the
backend reports itself unavailable and is skipped.
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from ..models import ScannerInfo, ScanOptions, ScanResult
from .base import Backend

log = logging.getLogger("scanner_mcp.sane")

_MODE = {"color": "Color", "gray": "Gray", "lineart": "Lineart"}
# scanimage understands png/jpeg/tiff/pdf via --format on recent versions.
_FORMAT = {"png": ("png", "image/png"), "jpeg": ("jpeg", "image/jpeg"), "pdf": ("pdf", "application/pdf")}
_DEVICE_RE = re.compile(r"device `([^']+)' is a (.+)")


class SaneBackend(Backend):
    name = "SANE (scanimage)"
    prefix = "sane"

    def available(self) -> bool:
        return shutil.which("scanimage") is not None

    def list_scanners(self) -> list[ScannerInfo]:
        try:
            out = subprocess.run(
                ["scanimage", "-L"],
                capture_output=True,
                text=True,
                timeout=20,
            ).stdout
        except Exception as exc:
            log.debug("scanimage -L failed: %s", exc)
            return []
        scanners = []
        for line in out.splitlines():
            m = _DEVICE_RE.search(line)
            if not m:
                continue
            dev, desc = m.group(1), m.group(2)
            conn = "network" if any(t in dev for t in ("net:", "airscan", "escl")) else "usb"
            scanners.append(
                ScannerInfo(
                    id=f"sane:{dev}",
                    name=desc.strip(),
                    backend=self.name,
                    connection=conn,
                    sources=["platen", "adf"],
                    detail={"device": dev},
                )
            )
        return scanners

    def scan(self, scanner_id: str, options: ScanOptions) -> ScanResult:
        device = scanner_id[len("sane:") :]
        fmt_name, mime = _FORMAT.get(options.output_format, ("png", "image/png"))
        mode = _MODE.get(options.color_mode, "Color")

        with tempfile.TemporaryDirectory(prefix="scanmcp_") as td:
            tmp = Path(td)
            cmd = [
                "scanimage",
                "-d", device,
                "--format", fmt_name,
                "--resolution", str(options.resolution),
                "--mode", mode,
            ]
            source = self._source_arg(options)
            multipage = options.source in ("adf", "adf-duplex")
            if source:
                cmd += ["--source", source]

            if multipage:
                # --batch writes out-1.ext, out-2.ext, ... for every fed sheet.
                pattern = str(tmp / f"out-%d.{fmt_name}")
                cmd += ["--batch=" + pattern]
                self._run(cmd, allow_no_docs=True)
                files = sorted(tmp.glob(f"out-*.{fmt_name}"), key=_page_index)
            else:
                out_file = tmp / f"out.{fmt_name}"
                cmd += ["-o", str(out_file)]
                self._run(cmd)
                files = [out_file] if out_file.exists() else []

            pages = [f.read_bytes() for f in files if f.exists() and f.stat().st_size > 0]

        if not pages:
            raise RuntimeError("scanimage produced no output (check device/source and that paper is loaded)")
        return ScanResult(pages=pages, mime=mime, backend=self.name, scanner_id=scanner_id)

    @staticmethod
    def _source_arg(options: ScanOptions) -> str | None:
        if options.source == "platen":
            return "Flatbed"
        if options.source == "adf":
            return "ADF"
        if options.source == "adf-duplex":
            return "ADF Duplex"
        return None  # "auto": let the driver decide

    @staticmethod
    def _run(cmd: list[str], allow_no_docs: bool = False) -> None:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if proc.returncode != 0:
            err = (proc.stderr or "").strip()
            # scanimage --batch exits non-zero with "no more documents" once the
            # feeder empties, which is a normal end-of-batch condition.
            if allow_no_docs and re.search(r"no more documents|Document feeder out of documents", err, re.I):
                return
            raise RuntimeError(f"scanimage failed: {err or proc.stdout.strip()}")


def _page_index(p: Path) -> int:
    m = re.search(r"out-(\d+)\.", p.name)
    return int(m.group(1)) if m else 0
