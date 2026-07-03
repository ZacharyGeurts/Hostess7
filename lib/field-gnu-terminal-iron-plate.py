#!/usr/bin/env pythong
"""GNU EOL Terminal iron plate — shell ≡ terminal · combinatronic optional · plate meld fuse."""
from __future__ import annotations

import importlib.util
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-gnu-terminal-iron-plate-doctrine.json"
PANEL = STATE / "field-gnu-terminal-iron-plate-panel.json"
EMBED = "panel/field-gnu-terminal-embed.html"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _save_atomic(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _import_py(path: Path, name: str) -> Any | None:
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _terminal_status() -> dict[str, Any]:
    mod = _import_py(INSTALL / "lib" / "field-gnu-terminal.py", "field_gnu_terminal")
    if mod and hasattr(mod, "terminal_status"):
        try:
            return mod.terminal_status()
        except Exception as exc:
            return {"ok": False, "error": str(exc)[:120]}
        return {"ok": False, "missing": "field-gnu-terminal.py"}


def _identity_slice() -> dict[str, Any]:
    mod = _import_py(INSTALL / "lib" / "field-gnu-identity-verify.py", "gnu_identity")
    if mod and hasattr(mod, "verify_all"):
        try:
            return mod.verify_all(write=False)
        except Exception as exc:
            return {"ok": False, "error": str(exc)[:120]}
    return {"ok": False, "missing": "field-gnu-identity-verify.py"}


def _ironclad_cite() -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    iron = doctrine.get("ironclad") or {}
    ic = _import_py(INSTALL / "lib" / "ironclad-field-sanity.py", "ironclad_field_sanity")
    cite = ""
    if ic and hasattr(ic, "cite_field_sanity"):
        try:
            cite = ic.cite_field_sanity(2) or ""
        except Exception:
            pass
    return {
        "meld_citation": iron.get("meld_citation") or "ironclad:gnu_terminal:1",
        "field_sanity_cite": cite or iron.get("field_sanity_cite") or "ironclad:field_sanity:2",
        "books": iron.get("books") or ["gnu_terminal"],
    }


def _embed_present() -> bool:
    return (INSTALL / EMBED).is_file()


def posture(*, write: bool = True) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    surface = doctrine.get("surface") or {}
    term = _terminal_status()
    ident = _identity_slice()
    iron = _ironclad_cite()
    meld_path = STATE / "field-plate-meld.json"
    meld_gen = None
    if meld_path.is_file():
        try:
            meld_gen = _load(meld_path, {}).get("generation")
        except Exception:
            pass
    doc = {
        "ok": True,
        "schema": "field-gnu-terminal-iron-plate/v1",
        "at": _now(),
        "posture": "Field Tech Terminal — GNU EOL · shell ≡ terminal · wiki · combinatronic optional",
        "shell_terminal_identical": True,
        "combinatronic_optional": True,
        "embed": surface.get("embed"),
        "api": surface.get("api"),
        "aliases": surface.get("aliases"),
        "combinatronic_commands": surface.get("combinatronic_commands"),
        "embed_present": _embed_present(),
        "terminal": term,
        "identity": ident,
        "ironclad": iron,
        "dedication": doctrine.get("dedication") or {},
        "plate_meld_generation": meld_gen,
        "gnu": doctrine.get("gnu") or {},
        "policy": doctrine.get("policy") or {},
    }
    if write:
        _save_atomic(PANEL, doc)
    return doc


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "posture"):
        print(json.dumps(posture(write=True), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: field-gnu-terminal-iron-plate.py [json|posture]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())