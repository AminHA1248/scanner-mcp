"""Backend registry.

Backends are probed lazily; any that raise on construction or report themselves as
unavailable (missing tools/OS support) are simply skipped, so the same server runs on
Windows, macOS and Linux and exposes whatever scanners it can reach.
"""

from __future__ import annotations

import logging

from .base import Backend

log = logging.getLogger("scanner_mcp.backends")


def all_backends() -> list[Backend]:
    from .escl import ESCLBackend
    from .sane import SaneBackend
    from .wia import WIABackend

    backends: list[Backend] = []
    for cls in (ESCLBackend, SaneBackend, WIABackend):
        try:
            b = cls()
        except Exception as exc:  # pragma: no cover - defensive
            log.debug("backend %s failed to construct: %s", cls.__name__, exc)
            continue
        try:
            if b.available():
                backends.append(b)
        except Exception as exc:  # pragma: no cover - defensive
            log.debug("backend %s availability check failed: %s", cls.__name__, exc)
    return backends


def backend_for(scanner_id: str) -> Backend | None:
    for b in all_backends():
        if b.handles(scanner_id):
            return b
    return None


__all__ = ["Backend", "all_backends", "backend_for"]
