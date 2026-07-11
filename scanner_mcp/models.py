"""Shared data types used across backends and the server."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

ColorMode = Literal["color", "gray", "lineart"]
Source = Literal["auto", "platen", "adf", "adf-duplex"]
OutputFormat = Literal["png", "jpeg", "pdf"]


@dataclass
class ScannerInfo:
    """A scanner discovered by a backend.

    ``id`` is globally unique and backend-qualified (e.g. ``escl:http://host:port/eSCL``,
    ``sane:epson2:libusb:001:002``, ``wia:{device-guid}``). The backend prefix before the
    first ``:`` is used to route scan requests to the owning backend.
    """

    id: str
    name: str
    backend: str
    connection: str = "unknown"  # "network" | "usb" | "unknown"
    sources: list[str] = field(default_factory=list)
    detail: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ScanOptions:
    source: Source = "auto"
    resolution: int = 300
    color_mode: ColorMode = "color"
    output_format: OutputFormat = "png"


@dataclass
class ScanResult:
    """Result of a scan: one or more page payloads plus their MIME type.

    For image formats ``pages`` holds one entry per page. For PDF, ``pages`` holds a
    single entry containing the whole multi-page document.
    """

    pages: list[bytes]
    mime: str  # "image/png" | "image/jpeg" | "application/pdf"
    backend: str
    scanner_id: str
