# Claude Desktop extension (`.mcpb` bundle)

scanner-mcp ships as an **MCP Bundle** (`.mcpb`, formerly `.dxt`) for one-click install
in **Claude Desktop → Settings → Extensions**. The bundle source lives in [`mcpb/`](../mcpb).

## Install (users)

1. Download `scanner-mcp-<version>.mcpb` from the
   [latest release](https://github.com/AminHA1248/scanner-mcp/releases/latest).
2. In Claude Desktop: **Settings → Extensions → Install extension…** and pick the file
   (or drag it onto the window).
3. Optionally set a **Save folder** in the extension's settings (defaults to `~/Scans`).

### Prerequisite

This is a Python MCP server, so the bundle runs your own Python rather than vendoring
per-OS compiled dependencies (Pillow, zeroconf, pytwain). You need **Python 3.10+ on
`PATH`** with the package installed:

```bash
python -m pip install scanner-mcp
```

If it isn't installed, the extension logs a message telling you the exact command.

## Build the bundle (maintainers)

Requires Node (for the `mcpb` CLI) and Python+Pillow (for the icon).

```bash
python mcpb/make_icon.py                                   # regenerate icon.png
npx @anthropic-ai/mcpb pack mcpb dist/scanner-mcp-<ver>.mcpb
npx @anthropic-ai/mcpb validate mcpb/manifest.json         # optional
```

CI also builds and attaches the `.mcpb` to every GitHub Release
(see [`.github/workflows/publish.yml`](../.github/workflows/publish.yml)).

## What's in the bundle

| File | Purpose |
|------|---------|
| `manifest.json` | MCP Bundle manifest (v0.2): metadata, tools, user config, launch command |
| `server/main.py` | Entry point — runs the installed `scanner_mcp.server` |
| `icon.png` | 512×512 extension icon |

The manifest maps two settings to the server's env vars: **Save folder** →
`SCANNER_MCP_SAVE_DIR`, **Log level** → `SCANNER_MCP_LOG`.

## Getting into Anthropic's directory

The `.mcpb` is the prerequisite artifact for submitting to Claude Desktop's **Extensions**
listing (the appropriate venue for a *local* server — the "Browse connectors" pool is for
*remote*, hosted connectors, which a local-hardware scanner can't be). Submission is a
reviewed process; check Anthropic's current connector/extensions submission docs for the
live intake. Meanwhile the bundle already gives your GitHub users one-click install.
