#!/usr/bin/env pythong
"""Programming language manuals — H7c with embedded figures; GUI + text readers."""
from __future__ import annotations

import base64
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-lang-manuals-doctrine.json"
SHELF = INSTALL / "library" / "dewey" / "000-computer-science"
SCHEMA = "field-lang-manuals/v1"
INDEX = STATE / "field-lang-manuals-index.json"


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        _p = INSTALL / "lib" / "sovereign-clock.py"
        _s = importlib.util.spec_from_file_location("sovereign_clock_lm", _p)
        if not _s or not _s.loader:
            raise ImportError("sovereign-clock.py missing")
        _SOVEREIGN_CLOCK_MOD = importlib.util.module_from_spec(_s)
        _s.loader.exec_module(_SOVEREIGN_CLOCK_MOD)
    return _SOVEREIGN_CLOCK_MOD.utc_z()


_SOVEREIGN_CLOCK_MOD = None


def _mod(name: str, rel: str) -> Any | None:
    path = INSTALL / "lib" / rel
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _save_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def lang_ids() -> list[str]:
    seed = _load_json(INSTALL / "data" / "field-program-combinatronic-seed.json", {})
    return sorted((seed.get("language_packs") or {}).keys())


def manual_paths(lang_id: str) -> dict[str, Path]:
    book_id = f"explaining_{lang_id}"
    base = SHELF / book_id
    return {
        "dir": base,
        "h7c": base / f"{book_id}.h7c",
        "book_json": base / "book.json",
        "cover": INSTALL / "Queen" / "world" / "assets" / "combinatronic" / "books" / f"{lang_id}.png",
    }


def _book_meta(lang_id: str) -> dict[str, Any]:
    paths = manual_paths(lang_id)
    meta = _load_json(paths["book_json"], {})
    if meta:
        return meta
    visuals = _mod("visuals_lm", "field-combinatronic-visuals.py")
    label = lang_id.replace("_", " ").title()
    if visuals and hasattr(visuals, "LANG_LABELS"):
        label = visuals.LANG_LABELS.get(lang_id, label)
    return {
        "id": f"explaining_{lang_id}",
        "title": f"Explaining {label}",
        "author": "Hostess 7",
        "format": "h7c",
        "combinatronic_lang": lang_id,
        "dewey": "000",
    }


def read_manual(lang_id: str) -> dict[str, Any]:
    """Decompress H7c manual with embedded figures."""
    paths = manual_paths(lang_id)
    h7c = paths["h7c"]
    if not h7c.is_file():
        return {"ok": False, "error": "manual_missing", "lang_id": lang_id, "path": str(h7c)}
    h7c_mod = _mod("h7c_lm", "field-h7c-compression.py")
    if not h7c_mod:
        return {"ok": False, "error": "h7c_module_missing"}
    blob = h7c.read_bytes()
    header, text, stats = h7c_mod.decompress_h7c(blob, verify=True, with_figures=True)
    raw_figs = stats.pop("_figures_raw", {}) or {}
    figures: dict[str, Any] = {}
    for fid, spec in raw_figs.items():
        data = spec.get("data") or b""
        figures[fid] = {
            "id": fid,
            "mime": spec.get("mime") or "image/png",
            "alt": spec.get("alt") or fid,
            "bytes": len(data),
            "sha256": spec.get("sha256"),
            "data_url": f"data:{spec.get('mime') or 'image/png'};base64,{base64.b64encode(data).decode('ascii')}" if data else "",
        }
    return {
        "schema": SCHEMA,
        "ok": True,
        "lang_id": lang_id,
        "book": _book_meta(lang_id),
        "header": {k: v for k, v in header.items() if k != "figures"},
        "text": text,
        "char_count": len(text),
        "figures": figures,
        "figure_ids": sorted(figures.keys()),
        "stats": stats,
        "path": str(h7c),
    }


def text_dump(lang_id: str) -> str:
    doc = read_manual(lang_id)
    if not doc.get("ok"):
        return f"ERROR: {doc.get('error', 'read_failed')} ({lang_id})\n"
    return str(doc.get("text") or "")


def catalog(*, refresh_index: bool = False) -> dict[str, Any]:
    manuals: list[dict[str, Any]] = []
    visuals = _mod("visuals_lm", "field-combinatronic-visuals.py")
    labels = getattr(visuals, "LANG_LABELS", {}) if visuals else {}
    for lang_id in lang_ids():
        paths = manual_paths(lang_id)
        h7c = paths["h7c"]
        meta = _book_meta(lang_id)
        entry = {
            "lang_id": lang_id,
            "book_id": meta.get("id") or f"explaining_{lang_id}",
            "title": meta.get("title") or f"Explaining {labels.get(lang_id, lang_id)}",
            "label": labels.get(lang_id, lang_id.replace("_", " ").title()),
            "ready": h7c.is_file(),
            "path": str(h7c) if h7c.is_file() else None,
            "cover": meta.get("cover") or f"/world/assets/combinatronic/books/{lang_id}.png",
            "format": meta.get("format", "h7c"),
            "embedded_figures": meta.get("embedded_figures") or ["cover", "syntax", "op_map"],
            "command_count": meta.get("command_count"),
        }
        if h7c.is_file():
            entry["bytes"] = h7c.stat().st_size
        manuals.append(entry)
    doc = {
        "schema": SCHEMA,
        "ok": True,
        "updated": _now(),
        "count": len(manuals),
        "ready_count": sum(1 for m in manuals if m.get("ready")),
        "manuals": manuals,
        "gui_reader": "/field-lang-manuals",
        "text_reader": "field-lang-manual-reader.py text <lang_id>",
        "h7_reader": "H7Reader.openSecure(book_id)",
    }
    if refresh_index:
        _save_json(INDEX, doc)
    return doc


def generate(lang_id: str | None = None, *, all_langs: bool = False) -> dict[str, Any]:
    visuals = _mod("visuals_lm", "field-combinatronic-visuals.py")
    if not visuals or not hasattr(visuals, "generate_book"):
        return {"ok": False, "error": "visuals_module_missing"}
    if all_langs or not lang_id:
        if hasattr(visuals, "generate_all"):
            rep = visuals.generate_all(chips_only=False, books_only=True)
            return {"ok": rep.get("ok", True), "action": "generate_all", **rep}
        results = []
        for lid in lang_ids():
            try:
                results.append(visuals.generate_book(lid))
            except Exception as exc:
                results.append({"ok": False, "lang_id": lid, "error": str(exc)})
        return {"ok": all(r.get("ok") for r in results), "results": results}
    return visuals.generate_book(lang_id)


def posture() -> dict[str, Any]:
    cat = catalog()
    doctrine = _load_json(DOCTRINE, {})
    return {
        "schema": SCHEMA,
        "ok": True,
        "doctrine": doctrine.get("title"),
        "catalog": cat,
        "index": str(INDEX),
        "checked_at": _now(),
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "catalog").strip().lower()
    lang = (sys.argv[2] if len(sys.argv) > 2 else "").strip()
    if cmd in ("catalog", "json", "list"):
        print(json.dumps(catalog(refresh_index="--save" in sys.argv), ensure_ascii=False, indent=2))
        return 0
    if cmd == "read" and lang:
        print(json.dumps(read_manual(lang), ensure_ascii=False, indent=2))
        return 0
    if cmd == "text" and lang:
        sys.stdout.write(text_dump(lang))
        return 0
    if cmd == "generate":
        if lang in ("all", "*"):
            print(json.dumps(generate(all_langs=True), ensure_ascii=False, indent=2))
        elif lang:
            print(json.dumps(generate(lang), ensure_ascii=False, indent=2))
        else:
            print(json.dumps(generate(all_langs=True), ensure_ascii=False, indent=2))
        return 0
    if cmd == "posture":
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    print(
        "usage: field-lang-manual-reader.py [catalog|read|text|generate|posture] [lang_id|all] [--save]",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())