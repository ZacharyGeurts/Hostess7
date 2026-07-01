#!/usr/bin/env pythong
"""Training X — school-style programming textbooks with code examples and research."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SEED = INSTALL / "data" / "field-program-combinatronic-seed.json"
SHELF = INSTALL / "library" / "dewey" / "000-computer-science"
PANEL = STATE / "field-training-textbook-panel.json"
READER_PROFILE = "training-textbook"

LANG_LABELS: dict[str, str] = {
    "python": "Python",
    "c": "C",
    "cxx": "C++",
    "rust": "Rust",
    "javascript": "JavaScript",
}


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _h7s_read_json(path: Path, default: Any = None) -> Any:
    fs_py = INSTALL / "lib" / "field-h7s-fs.py"
    if path.suffix.lower() == ".json" and fs_py.is_file():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("_h7s_fs_io", fs_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "read_json"):
                    return mod.read_json(path, default=default)
        except Exception:
            pass
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}

def _load(path: Path, default: Any = None) -> Any:
    return _h7s_read_json(path, default=default)


def _h7c_mod():
    path = INSTALL / "lib" / "field-h7c-compression.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("field_h7c_compression_train", path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _visuals_mod():
    path = INSTALL / "lib" / "field-combinatronic-visuals.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("field_combinatronic_visuals_train", path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def chapter_outline(lang_id: str) -> list[dict[str, Any]]:
    label = LANG_LABELS.get(lang_id, lang_id.replace("_", " ").title())
    return [
        {"id": "ch01", "title": f"Introduction to {label}", "words_target": 2200, "exercises": 4},
        {"id": "ch02", "title": "Types, values, and variables", "words_target": 2800, "exercises": 6},
        {"id": "ch03", "title": "Control flow and functions", "words_target": 3000, "exercises": 8},
        {"id": "ch04", "title": "Modules and the standard library", "words_target": 2600, "exercises": 6},
        {"id": "ch05", "title": f"{label} in the Field / g16 ecosystem", "words_target": 2400, "exercises": 5},
    ]


def write_training_chapter(lang_id: str, chapter: dict[str, Any], *, seed: dict[str, Any]) -> str:
    label = LANG_LABELS.get(lang_id, lang_id.replace("_", " ").title())
    packs = seed.get("language_packs") or {}
    pack = packs.get(lang_id) or {}
    cmds = pack.get("commands") or {}
    cid = chapter["id"]
    title = chapter["title"]
    lines = [
        f"# {title}",
        "",
        f"**Training {label}** · {cid} · Hostess 7 school textbook",
        "",
        f"This chapter is part of the Training {label} line — exercises, worked examples,",
        "and research notes. Pair with the Explaining manual for reference semantics.",
        "",
        "## Learning objectives",
        "",
        f"- Read and write core {label} constructs in the Field program facet.",
        "- Map surface syntax to canonical combinatronic ops.",
        "- Complete exercises using Queen Code and g16 belt runners.",
        "",
        "## Worked example",
        "",
        f"```text",
        f"# {label} sample — boils to declare + assign + call",
        f"keyword_sample = \"{next(iter(cmds.keys()), 'main')}\"",
        f"```",
        "",
        "## Research note",
        "",
        f"Command inventory for {label}: {len(cmds)} seeded keywords.",
        "Consult Field Research book plates for algorithm and memory citations.",
        "",
        "## Exercises",
        "",
    ]
    for n in range(1, int(chapter.get("exercises") or 4) + 1):
        lines.extend([
            f"### Exercise {cid}.{n}",
            f"1. Identify the canonical op for a {label} construct from the seed.",
            f"2. Run `field-program-combinatronic.py boil {lang_id}` and record the mapping.",
            f"3. Submit via Queen Code Run menu when `.launch` is configured.",
            "",
        ])
    return "\n".join(lines) + "\n"


def write_training_textbook(lang_id: str, *, seed: dict[str, Any] | None = None) -> str:
    seed = seed or _load(SEED, {})
    label = LANG_LABELS.get(lang_id, lang_id.replace("_", " ").title())
    parts = [
        f"# Training {label}",
        "",
        f"School-style textbook · Hostess 7 · reader profile `{READER_PROFILE}`",
        "",
        f"- **Language:** {lang_id}",
        f"- **Chapters:** {len(chapter_outline(lang_id))}",
        f"- **Generated:** {_now()}",
        "",
    ]
    for ch in chapter_outline(lang_id):
        parts.append(write_training_chapter(lang_id, ch, seed=seed))
    return "\n".join(parts)


def pack_training_h7(lang_id: str, text: str) -> Path:
    h7c = _h7c_mod()
    if not h7c:
        raise RuntimeError("field-h7c-compression.py missing")
    label = LANG_LABELS.get(lang_id, lang_id.replace("_", " ").title())
    book_id = f"training_{lang_id}"
    dest = SHELF / book_id
    dest.mkdir(parents=True, exist_ok=True)
    h7c_path = dest / f"{book_id}.h7c"
    visuals = _visuals_mod()
    figures: dict[str, dict[str, Any]] = {}
    if visuals:
        try:
            cover = visuals.render_book_cover(lang_id, label=label)
            accent = getattr(visuals, "LANG_ACCENT", {}).get(lang_id, (94, 234, 212))
            figures["cover"] = {
                "path": cover,
                "alt": f"Training {label}",
                "plate_key": "cover",
                "accent": accent,
            }
        except Exception:
            pass
    meta = {
        "id": book_id,
        "title": f"Training {label}",
        "author": "Hostess 7",
        "license": "Field",
        "subject": "programming languages",
        "category": "computer science",
        "dewey": "000",
        "combinatronic_lang": lang_id,
        "reader_profile": READER_PROFILE,
        "uploaded": _now(),
        "reader": "NEXUS_H7C",
    }
    packed = h7c.pack_h7c(text, meta, use_optimizer=True, format_version=3, figures=figures or None)
    h7c_path.write_bytes(packed)
    rel = str(h7c_path.relative_to(INSTALL))
    ein = "H7C-TRAIN-" + hashlib.sha256(text.encode()).hexdigest()[:12]
    book_json = {
        "id": book_id,
        "title": f"Training {label}",
        "author": "Hostess 7",
        "dewey": "000",
        "ein": ein,
        "format": "h7c",
        "format_version": 3,
        "reader_profile": READER_PROFILE,
        "manual_reader": "/field-lang-manuals",
        "h7c": rel,
        "field_path": rel,
        "github_shelf": "000-computer-science",
        "combinatronic_lang": lang_id,
        "chapters": [c["id"] for c in chapter_outline(lang_id)],
        "updated": _now(),
    }
    (dest / "book.json").write_text(json.dumps(book_json, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return h7c_path


def forge_training(lang_id: str) -> dict[str, Any]:
    seed = _load(SEED, {})
    if lang_id not in (seed.get("language_packs") or {}):
        return {"ok": False, "error": "language_not_in_seed", "lang_id": lang_id}
    text = write_training_textbook(lang_id, seed=seed)
    path = pack_training_h7(lang_id, text)
    doc = {
        "ok": True,
        "lang_id": lang_id,
        "book_id": f"training_{lang_id}",
        "h7c_path": str(path),
        "char_count": len(text),
        "chapters": len(chapter_outline(lang_id)),
        "updated": _now(),
    }
    _save(PANEL, doc)
    return doc


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else __import__("sys").argv[1:]
    if not args or args[0] in ("-h", "--help", "help"):
        print("Usage: field-training-textbook-forge.py forge LANG [panel]")
        return 0
    if args[0] == "forge":
        lang = args[1] if len(args) > 1 else "python"
        print(json.dumps(forge_training(lang), ensure_ascii=False, indent=2))
        return 0
    if args[0] == "panel":
        print(json.dumps(_load(PANEL, {}), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"ok": False, "error": "unknown_command"}, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())