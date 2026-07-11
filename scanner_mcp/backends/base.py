"""Backend abstraction. Each backend discovers scanners and performs scans."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import ScannerInfo, ScanOptions, ScanResult


class Backend(ABC):
    #: Human-readable backend name.
    name: str = "base"
    #: Prefix used on scanner ids owned by this backend (e.g. "escl").
    prefix: str = "base"

    def available(self) -> bool:
        """Whether this backend can run in the current environment."""
        return True

    def handles(self, scanner_id: str) -> bool:
        return scanner_id.startswith(self.prefix + ":")

    @abstractmethod
    def list_scanners(self) -> list[ScannerInfo]:
        ...

    @abstractmethod
    def scan(self, scanner_id: str, options: ScanOptions) -> ScanResult:
        ...
