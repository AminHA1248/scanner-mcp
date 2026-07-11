#!/usr/bin/env python
"""Command-line sanity check for scanner-mcp — no Claude required.

Examples:
    # List every scanner reachable from this machine
    python test_scan.py --list

    # Scan with the only/first scanner at 300 DPI to a PNG
    python test_scan.py

    # Pick a scanner, resolution, source and format
    python test_scan.py --scanner "wia:SWD\\Escl\\..." --dpi 300 --source platen --format png

    # Multi-page feeder scan straight to a PDF
    python test_scan.py --source adf --format pdf

Run inside the project venv:
    .venv\\Scripts\\python.exe test_scan.py --list      (Windows)
    .venv/bin/python test_scan.py --list                (macOS/Linux)
"""

from __future__ import annotations

import argparse
import sys
import time

from scanner_mcp.backends import all_backends, backend_for
from scanner_mcp.models import ScanOptions
from scanner_mcp.server import _save


def cmd_list() -> int:
    backends = all_backends()
    print(f"Active backends: {', '.join(b.name for b in backends) or '(none)'}\n")
    found = 0
    for b in backends:
        try:
            scanners = b.list_scanners()
        except Exception as exc:
            print(f"  [{b.prefix}] list error: {exc}")
            continue
        for s in scanners:
            found += 1
            print(f"  {s.name}")
            print(f"      id:         {s.id}")
            print(f"      connection: {s.connection}   sources: {', '.join(s.sources)}")
    if not found:
        print("  No scanners found. Power the scanner on and ensure it's on the same "
              "network / plugged in via USB.")
        return 1
    return 0


def pick_scanner(explicit: str | None) -> str:
    if explicit:
        return explicit
    scanners = []
    for b in all_backends():
        try:
            scanners.extend(b.list_scanners())
        except Exception:
            pass
    if not scanners:
        sys.exit("No scanners found — nothing to scan.")
    if len(scanners) > 1:
        print("Multiple scanners found; pass --scanner with one of:")
        for s in scanners:
            print(f"  {s.id}   ({s.name})")
        sys.exit(1)
    print(f"Using: {scanners[0].name}  ({scanners[0].id})")
    return scanners[0].id


def cmd_scan(args: argparse.Namespace) -> int:
    scanner_id = pick_scanner(args.scanner)
    backend = backend_for(scanner_id)
    if backend is None:
        sys.exit(f"No backend owns scanner id {scanner_id!r}")

    opts = ScanOptions(
        source=args.source,
        resolution=args.dpi,
        color_mode=args.color,
        output_format=args.format,
    )

    attempts = max(1, args.retries)
    last_err: Exception | None = None
    for i in range(1, attempts + 1):
        t0 = time.time()
        try:
            res = backend.scan(scanner_id, opts)
            dt = time.time() - t0
            total = sum(len(p) for p in res.pages)
            print(f"Scan OK in {dt:.1f}s — {len(res.pages)} page(s), {res.mime}, {total/1024:.0f} KB")
            paths = _save(res.pages, res.mime, args.out or "")
            for p in paths:
                print("  saved:", p)
            return 0
        except Exception as exc:
            last_err = exc
            msg = str(exc).splitlines()[0]
            if i < attempts:
                print(f"[attempt {i}/{attempts}] not ready: {msg} — retrying in {args.wait}s "
                      "(wake the scanner if it's asleep)")
                time.sleep(args.wait)
            else:
                print(f"[attempt {i}/{attempts}] failed: {msg}")
    print(f"\nScan failed: {last_err}")
    return 2


def main() -> int:
    ap = argparse.ArgumentParser(description="Sanity-check scanner-mcp without Claude.")
    ap.add_argument("--list", action="store_true", help="list scanners and exit")
    ap.add_argument("--scanner", help="scanner id (from --list); default: the only one found")
    ap.add_argument("--dpi", type=int, default=300, help="resolution in DPI (default 300)")
    ap.add_argument("--source", default="platen",
                    choices=["auto", "platen", "adf", "adf-duplex"], help="paper source")
    ap.add_argument("--color", default="color",
                    choices=["color", "gray", "lineart"], help="color mode")
    ap.add_argument("--format", default="png",
                    choices=["png", "jpeg", "pdf"], help="output format")
    ap.add_argument("--out", help="output directory (default ~/Scans)")
    ap.add_argument("--retries", type=int, default=1,
                    help="scan attempts if the device isn't ready (default 1)")
    ap.add_argument("--wait", type=int, default=8, help="seconds between retries (default 8)")
    args = ap.parse_args()

    if args.list:
        return cmd_list()
    return cmd_scan(args)


if __name__ == "__main__":
    raise SystemExit(main())
