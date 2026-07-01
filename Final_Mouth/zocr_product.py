"""Final_Mouth product metadata — sovereign voice / speech release."""
from __future__ import annotations

from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent
_VERSION_FILE = _ROOT / "VERSION"


def _read_version() -> str:
    try:
        return _VERSION_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return "1.0.0"


PRODUCT_ID = "Final_Mouth"
PRODUCT_NAME = "The Final Mouth"
VERSION = _read_version()
SCHEMA = "final-mouth-product/v1"
CODENAME = "mouth-stoard"
LICENSE = "proprietary"
REPO = "https://github.com/ZacharyGeurts/Final_Mouth"


def product_info() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "product": PRODUCT_ID,
        "name": PRODUCT_NAME,
        "version": VERSION,
        "codename": CODENAME,
        "license": LICENSE,
        "repo": REPO,
        "format": "VOCAL1",
        "codec": "GVC1",
        "rule": "We never presume speech loss. Confidence always in Voice.",
        "twins": {"living": "Loquor", "truth": "Veritas Vox"},
        "textbook": "docs/index.html",
    }