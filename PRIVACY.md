# Privacy Policy

_Last updated: 2026-07-13_

scanner-mcp is a **local** MCP server. It runs entirely on your own machine and exists
only to let an MCP client (such as Claude) discover and operate scanners you already own.

## Data collection

scanner-mcp **collects no personal data** and contains **no analytics, telemetry, tracking,
or "phone-home" behavior**. It has no servers, accounts, or backend of its own.

The only data it handles is what you explicitly ask it to produce:

- **Scanned images/PDFs** you create by calling the `scan_document` tool.
- **Scanner metadata** (device names, IDs, capabilities) returned by `list_scanners`.

## Usage and storage

- Scans are written **only to your local machine** — by default `~/Scans`, or the folder
  you configure (`SCANNER_MCP_SAVE_DIR` / the extension's "Save folder" setting).
- Scanned images are also returned to the MCP client that requested them (e.g. Claude) so
  it can display or read the document, exactly as you asked. What that client does with
  the content is governed by **that client's** privacy policy, not this one.
- Network access is limited to your **local network and USB bus**: mDNS discovery of eSCL
  scanners and communication with the scanner you select. scanner-mcp does not transmit
  your scans or metadata to the internet or to the author.

## Third-party sharing

None. scanner-mcp does not sell, share, or transmit your data to any third party. It has
no third-party integrations beyond the optional, locally-run OCR engine (Tesseract) if you
choose to install it, which also runs entirely on your machine.

## Data retention

scanner-mcp retains **nothing** itself — it holds a scan only in memory long enough to
save the file and return it to the client. Saved files remain on your disk until **you**
delete them; the software never deletes or manages them on your behalf.

## Contact

Questions or concerns:

- GitHub issues: https://github.com/AminHA1248/scanner-mcp/issues
- Email: amin.h.a@gmail.com
