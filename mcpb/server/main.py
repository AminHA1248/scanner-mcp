"""Entry point for the scanner-mcp MCP bundle.

This bundle runs the installed `scanner-mcp` package on the user's own Python, so
that platform-specific, compiled dependencies (Pillow, zeroconf, pywin32/pytwain)
resolve correctly per OS instead of being vendored into the bundle.

Prerequisite: Python 3.10+ on PATH as `python`, with the package installed:
    python -m pip install scanner-mcp
"""

import sys


def _fail(msg: str) -> None:
    sys.stderr.write(msg + "\n")
    sys.exit(1)


try:
    from scanner_mcp.server import main
except ModuleNotFoundError:
    _fail(
        "scanner-mcp is not installed for this Python interpreter.\n"
        "Install it and restart Claude:\n"
        "    python -m pip install scanner-mcp\n"
    )


if __name__ == "__main__":
    main()
