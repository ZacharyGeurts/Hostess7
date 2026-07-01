#!/usr/bin/env pythong
"""Build individual Hostess 7 anatomical .H7 books — one book per body part."""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(_LIB.parent)))
HOSTESS7 = Path(os.environ.get("HOSTESS7_ROOT", str(INSTALL / "Hostess7")))
DENSE = INSTALL / "data" / "hostess7-human-anatomy-dense.json"
INDEX = INSTALL / "data" / "hostess7-anatomy-books-index.json"

_EXTRACTS: dict[str, str] = {
    "eye": (
        "Eye anatomy: fibrous tunic (cornea transparent, sclera), vascular uvea (choroid, ciliary body, iris), "
        "retina (rods dim/night, cones color/fovea centralis). Lens accommodation; aqueous and vitreous humor. "
        "Extraocular muscles LR6SO4R3. Threat protection: no_flash, whiteout_reject, laser corridor — correlate with field-eye-threat-doctrine."
    ),
    "ear": (
        "Ear: external (pinna, canal, tympanic membrane), middle (ossicles malleus/incus/stapes, Eustachian tube), "
        "inner (cochlea hearing, vestibule/semicircular canals balance). Organ of Corti hair cells. Vestibular utricle/saccule."
    ),
    "genitalia_male": (
        "Male genitalia: penis root, body, glans; corpora cavernosa and spongiosum; prepuce. "
        "Scrotum thermoregulation for testes. Urethra prostatic, membranous, spongy segments. "
        "Educational anatomy — clinical correlation with reproductive_male book."
    ),
    "genitalia_female": (
        "Female genitalia / vulva: mons pubis, labia majora/minora, clitoris, vestibule, "
        "greater vestibular (Bartholin) glands. Vaginal fornix. Educational anatomy — "
        "clinical correlation with reproductive_female book; not gynecologic diagnosis."
    ),
}


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def books_index() -> dict[str, Any]:
    idx = _load(INDEX, {})
    dense = _load(DENSE, {})
    sections = {s["id"]: s for s in dense.get("sections") or [] if s.get("id")}
    books = []
    for row in idx.get("books") or []:
        sec_id = row.get("section")
        sec = sections.get(sec_id) or {}
        extract = row.get("extract")
        body = _EXTRACTS.get(str(extract or "")) or sec.get("body") or ""
        if extract and sec.get("body") and extract not in _EXTRACTS:
            body = sec.get("body", "")
        books.append({**row, "body_preview": body[:200], "has_body": bool(body)})
    return {
        "schema": "hostess7-anatomy-books-index/v1",
        "updated": _ts(),
        "ok": True,
        "book_count": len(books),
        "books": books,
        "disclaimer": idx.get("disclaimer") or dense.get("disclaimer"),
    }


def _book_doc(entry: dict[str, Any], dense: dict[str, Any]) -> dict[str, Any]:
    sections = {s["id"]: s for s in dense.get("sections") or [] if s.get("id")}
    sec = sections.get(str(entry.get("section") or "")) or {}
    extract = entry.get("extract")
    if extract and str(extract) in _EXTRACTS:
        body = _EXTRACTS[str(extract)]
        title = entry.get("title") or str(extract).replace("_", " ").title()
    else:
        body = sec.get("body") or ""
        title = entry.get("title") or sec.get("title") or entry.get("id")
    return {
        "schema": "hostess7-anatomy-book/v1",
        "id": entry.get("id"),
        "title": title,
        "region": entry.get("region"),
        "dewey": dense.get("dewey", "611"),
        "dewey_label": dense.get("dewey_label", "Human anatomy"),
        "author": dense.get("author", "Hostess 7 Biology Chamber"),
        "license": dense.get("license"),
        "disclaimer": dense.get("disclaimer"),
        "body": body,
        "parent_section": entry.get("section"),
        "extract": extract,
    }


def build_text(doc: dict[str, Any]) -> str:
    lines = [
        f"# {doc.get('title', 'Anatomy')}",
        "",
        doc.get("disclaimer", ""),
        "",
        f"Dewey {doc.get('dewey')} — {doc.get('dewey_label')}",
        f"Book ID: {doc.get('id')}",
        "",
        str(doc.get("body") or "").strip(),
        "",
    ]
    return "\n".join(lines).strip() + "\n"


def h7_out_path(book_id: str, dewey: str = "611") -> Path:
    safe = re.sub(r"[^a-z0-9_]+", "_", book_id.lower())
    base = HOSTESS7 / "cache" / "fieldstorage" / "textbooks" / "dewey" / dewey / "parts"
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{safe}.h7"


def build_book(book_id: str, *, write: bool = True) -> dict[str, Any]:
    idx = _load(INDEX, {})
    dense = _load(DENSE, {})
    entry = next((b for b in idx.get("books") or [] if b.get("id") == book_id), None)
    if not entry:
        return {"ok": False, "error": "book_not_found", "book_id": book_id}
    doc = _book_doc(entry, dense)
    text = build_text(doc)
    out = h7_out_path(book_id, str(dense.get("dewey") or "611"))
    if not write:
        return {"ok": True, "book_id": book_id, "path": str(out), "char_count": len(text), "dry_run": True}
    scripts = HOSTESS7 / "scripts"
    if not scripts.is_dir():
        scripts = INSTALL / "Hostess7" / "scripts"
    sys.path.insert(0, str(scripts))
    from field_h7_book import write_h7  # noqa: WPS433

    meta = {
        "id": doc.get("id"),
        "title": doc.get("title"),
        "region": doc.get("region"),
        "dewey": doc.get("dewey"),
        "part_book": True,
        "parent_section": doc.get("parent_section"),
        "packed": _ts(),
        "reader": "Hostess7_only",
    }
    stats = write_h7(out, text, meta)
    return {"ok": True, "book_id": book_id, "path": str(out), **stats}


def build_all_books(*, write: bool = True) -> dict[str, Any]:
    idx = _load(INDEX, {})
    results: list[dict[str, Any]] = []
    for row in idx.get("books") or []:
        bid = str(row.get("id") or "")
        if bid:
            results.append(build_book(bid, write=write))
    ok = sum(1 for r in results if r.get("ok"))
    return {
        "ok": ok == len(results),
        "updated": _ts(),
        "book_count": len(results),
        "built_ok": ok,
        "books": results,
    }


def build_h7(*, write: bool = True) -> dict[str, Any]:
    """Legacy entry — build dense combined book + all part books."""
    dense = _load(DENSE)
    text_lines = [f"# {dense.get('title')}", "", dense.get("disclaimer", ""), ""]
    for sec in dense.get("sections") or []:
        text_lines.append(f"## {sec.get('title')}")
        text_lines.append(str(sec.get("body") or ""))
        text_lines.append("")
    text = "\n".join(text_lines).strip() + "\n"
    scripts = HOSTESS7 / "scripts"
    if not scripts.is_dir():
        scripts = INSTALL / "Hostess7" / "scripts"
    sys.path.insert(0, str(scripts))
    from field_h7_book import write_h7  # noqa: WPS433

    dewey = str(dense.get("dewey") or "611")
    bid = str(dense.get("id") or "h7_human_anatomy_dense")
    base = HOSTESS7 / "cache" / "fieldstorage" / "textbooks" / "dewey" / dewey
    base.mkdir(parents=True, exist_ok=True)
    out = base / f"{bid}.h7"
    combined: dict[str, Any] = {"ok": True, "path": str(out), "dry_run": not write}
    if write:
        combined = write_h7(out, text, {
            "id": bid,
            "title": dense.get("title"),
            "dense": True,
            "section_count": len(dense.get("sections") or []),
            "packed": _ts(),
        })
    parts = build_all_books(write=write)
    return {"ok": combined.get("ok", True) and parts.get("ok", True), "combined": combined, "parts": parts}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "build").strip().lower()
    if cmd in ("index", "json", "list"):
        print(json.dumps(books_index(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "build":
        print(json.dumps(build_h7(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "build-all":
        print(json.dumps(build_all_books(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "build-one" and len(sys.argv) > 2:
        print(json.dumps(build_book(sys.argv[2]), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: hostess7-anatomy-book.py [build|build-all|index|build-one ID]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())