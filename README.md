# scanner-mcp

![License: MIT](https://img.shields.io/github/license/AminHA1248/scanner-mcp?color=blue)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
![MCP](https://img.shields.io/badge/MCP-server-8A2BE2)
![Stars](https://img.shields.io/github/stars/AminHA1248/scanner-mcp?style=social)

> **Let Claude scan and read paper documents** from any USB or network scanner.

<p align="center">
  <img src="https://raw.githubusercontent.com/AminHA1248/scanner-mcp/main/docs/demo.gif" alt="Ask Claude to scan a document; it calls the scan_document tool and reads the page back" width="760">
</p>

A **generic MCP server** that exposes a scanning tool to Claude (and any other MCP
client). It works with **network scanners** through the standard **eSCL / AirScan /
Mopria** protocol and with **USB scanners** through the platform driver stack —
**WIA** on Windows and **SANE** on Linux/macOS. No vendor-specific driver code.

When Claude needs to read a paper document, it can call `scan_document`, and the page
image is returned inline so Claude can read it directly (optionally OCR'd to text, or
saved as PDF).

## What it exposes

| Tool | Purpose |
|------|---------|
| `list_scanners` | Discover every scanner reachable from this machine (network + USB). |
| `scan_document` | Scan a page/stack and return it as inline images, a saved file, and/or OCR text. |

Backends are auto-detected and degrade gracefully — the same server runs on any OS and
lights up whatever scanners it can reach:

- **eSCL** (`_uscan._tcp` mDNS) — driverless network MFPs/scanners. *Cross-platform.*
- **WIA** — USB (and some network) scanners on **Windows**, driven via PowerShell COM.
- **TWAIN** — Windows scanners that expose only a TWAIN data source (older/pro units
  with no usable WIA driver). Optional; needs `pytwain` + a TWAIN DSM (see below).
- **SANE** (`scanimage`) — USB/network scanners on **Linux** and **macOS**.

## Install

```bash
pip install scanner-mcp
# optional OCR support (also needs the Tesseract binary installed):
pip install "scanner-mcp[ocr]"
# optional TWAIN backend, Windows only (also needs a TWAIN DSM, see below):
pip install "scanner-mcp[twain]"
```

<details>
<summary>Or install from source (for development)</summary>

```bash
git clone https://github.com/AminHA1248/scanner-mcp
cd scanner-mcp
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -e ".[twain]"    # editable install; add [ocr] too if you want OCR
```
</details>

Platform prerequisites:

- **Windows**: nothing extra for WIA — it and PowerShell ship with Windows. Install the
  scanner's normal Windows driver so it appears in *Devices*.
  - **TWAIN (optional)**: install `pytwain` (`pip install -e ".[twain]"`) and make sure a
    TWAIN **DSM** is present. 64-bit Python needs `TWAINDSM.dll` (shipped by most TWAIN
    2.x drivers or the TWAIN DSM redistributable); 32-bit Python can use the classic
    `twain_32.dll`. If neither is installed, the TWAIN backend just stays disabled.
- **Linux**: `sudo apt install sane-utils` (provides `scanimage`).
- **macOS**: `brew install sane-backends` for USB; network scanners work via eSCL with no extras.
- **Network scanners**: just be on the same LAN/subnet; mDNS handles discovery.

## Connect it to Claude

### Claude Desktop — one-click extension (easiest)
Download `scanner-mcp-<version>.mcpb` from the
[latest release](https://github.com/AminHA1248/scanner-mcp/releases/latest) and open it
via **Settings → Extensions → Install extension…**. Requires Python 3.10+ with
`pip install scanner-mcp` (the extension tells you if it's missing). Details:
[docs/EXTENSION.md](docs/EXTENSION.md).

### Claude Desktop — manual config
Edit `claude_desktop_config.json` (Settings → Developer → Edit Config):

```json
{
  "mcpServers": {
    "scanner": {
      "command": "scanner-mcp"
    }
  }
}
```

If `scanner-mcp` isn't found (its Scripts/bin dir isn't on Claude's PATH), use the full
path to the launcher — e.g. `C:\Users\you\...\Scripts\scanner-mcp.exe` on Windows or
`/path/to/venv/bin/scanner-mcp` on macOS/Linux — or `python -m scanner_mcp.server`.

### Claude Code (CLI)
```bash
claude mcp add scanner -- scanner-mcp
```

Restart the client, then ask Claude: *"List my scanners"* or *"Scan the document on the
glass and read it."*

## How you actually run it

You normally **don't launch anything yourself** — Claude Desktop/Code starts the
`scanner-mcp` server in the background (per the config above) and calls its tools when
you ask. Running `scanner-mcp` by hand just starts the MCP server, which waits silently
for JSON-RPC on stdin; it is not an interactive shell.

To test the hardware **without Claude**, use the bundled CLI, [`test_scan.py`](test_scan.py):

```bash
# from the project folder, using the venv's Python
python test_scan.py --list                 # discover scanners
python test_scan.py --dpi 300              # scan (auto-selects if only one)
python test_scan.py --scanner "<id>" --source adf --format pdf
```

## Configuration (env vars)

| Variable | Default | Meaning |
|----------|---------|---------|
| `SCANNER_MCP_SAVE_DIR` | `~/Scans` | Where scans are written. |
| `SCANNER_MCP_LOG` | `INFO` | Log level. |

## `scan_document` options

`scanner_id` (from `list_scanners`; auto if only one), `source`
(`auto`/`platen`/`adf`/`adf-duplex`), `resolution` (DPI), `color_mode`
(`color`/`gray`/`lineart`), `output_format` (`png`/`jpeg`/`pdf`), `save_dir`,
`return_image` (inline images for Claude to read), `ocr` (extract text).

## Notes & limitations

- **eSCL** covers most scanners sold in the last ~decade (anything "AirPrint/AirScan"
  or "Mopria" capable). Older USB-only units go through WIA/SANE instead.
- PDF output for multi-page WIA scans is assembled with Pillow.
- HTTPS eSCL devices use self-signed certs, so TLS verification is disabled for them
  (typical for LAN scanners); prefer a trusted network.
- This server performs local hardware I/O only — it does not send anything to the cloud.

## License

MIT
