#!/usr/bin/env pythong
"""H7c library corrector — page-wise edits, Corrects sections, h7c/4 block repack."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
STATE.mkdir(parents=True, exist_ok=True)
DOCTRINE = INSTALL / "data" / "field-h7c-doctrine.json"
DEWEY_ROOT = INSTALL / "library" / "dewey"
MANIFEST = STATE / "field-h7c-correct-manifest.json"
CORRECTS_HDR = "## Corrects"
CANONICAL_LAYER = 1
_NEEDS_CORRECTION_RE = re.compile(
    r"layer 0|Layer 0|field depth · layer 0|at layer 0|field_layer 0|"
    r"one amplitude at layer 0|H7c v[123]\b|depth zero on all corpus",
    re.IGNORECASE,
)


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


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _h7c_mod() -> Any:
    path = INSTALL / "lib" / "field-h7c-compression.py"
    spec = importlib.util.spec_from_file_location("field_h7c_correct", path)
    if not spec or not spec.loader:
        raise ImportError("field-h7c-compression.py missing")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _glob_h7c() -> list[Path]:
    dewey = INSTALL / "lib" / "field-dewey-library.py"
    if dewey.is_file():
        spec = importlib.util.spec_from_file_location("dewey_lib", dewey)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "glob_h7c_files"):
                return mod.glob_h7c_files()
    return sorted(DEWEY_ROOT.rglob("*.h7c"))


def _strip_corrects(page: str) -> str:
    idx = page.find(f"\n{CORRECTS_HDR}")
    if idx < 0:
        idx = page.find(f"{CORRECTS_HDR}\n")
        if idx == 0:
            return ""
    if idx >= 0:
        return page[:idx].rstrip()
    return page


def _split_pages(text: str) -> tuple[list[str], str]:
    """Return pages and joiner used between them."""
    body = text.strip()
    if "\n---\n" in body:
        return [p.strip() for p in body.split("\n---\n") if p.strip()], "\n---\n"
    pages: list[str] = []
    chunk: list[str] = []
    for line in body.split("\n"):
        if line.startswith("## ") and chunk:
            pages.append("\n".join(chunk).strip())
            chunk = [line]
        else:
            chunk.append(line)
    if chunk:
        pages.append("\n".join(chunk).strip())
    return [p for p in pages if p], "\n\n"


def _join_pages(pages: list[str], joiner: str) -> str:
    return joiner.join(pages).strip() + "\n"


def _apply_line_rules(page: str) -> tuple[str, list[str]]:
    notes: list[str] = []
    out = page

    replacements: tuple[tuple[str, str, str], ...] = (
        (r"\blayer 0\b", "field layer 1", "Field layer 0 abolished → field layer 1"),
        (r"\bLayer 0\b", "Layer 1", "Layer 0 label promoted to Layer 1"),
        (r"field depth · layer 0", "field depth · layer 1", "Field depth display → layer 1"),
        (r"at layer 0", "at field layer 1", "Amplitude anchor → field layer 1"),
        (r"field_layer 0", "field_layer 1", "field_layer 0 → field_layer 1"),
        (r"one amplitude at layer 0", "one amplitude at field layer 1", "Single amplitude → field layer 1"),
        (r"depth zero on all corpus", "canonical field layer 1 on all corpus", "Corpus depth wording aligned"),
        (r"Depth zero\. Depth fields", "Field layer 1. Depth fields", "Singularizer motto aligned"),
        (r"\bH7c v1\b", "H7c block (v4)", "Format label → H7c block"),
        (r"\bH7c v2\b", "H7c block (v4)", "Format label → H7c block"),
        (r"\bH7c v3\b", "H7c block (v4)", "Format label → H7c block"),
        (r"Hostess 7 Condenser\) — lossless", "Hostess 7 Condenser · field layer 1) — lossless", "Condenser stamp → field layer 1"),
    )

    for pattern, repl, note in replacements:
        if re.search(pattern, out):
            out = re.sub(pattern, repl, out)
            notes.append(note)

    lines = [ln.rstrip() for ln in out.split("\n")]
    collapsed: list[str] = []
    blank_run = 0
    for ln in lines:
        if not ln.strip():
            blank_run += 1
            if blank_run <= 2:
                collapsed.append("")
            continue
        blank_run = 0
        collapsed.append(ln)
    normalized = "\n".join(collapsed)
    if normalized != out:
        notes.append("Normalized trailing whitespace and excess blank lines")
        out = normalized

    return out, notes


def correct_page(page: str) -> tuple[str, list[str]]:
    base = _strip_corrects(page)
    corrected, notes = _apply_line_rules(base)
    if not notes:
        return page, []
    block = "\n\n## Corrects\n\n" + "\n".join(f"- {n}" for n in notes)
    return corrected + block, notes


def correct_text(text: str) -> tuple[str, list[str], int]:
    pages, joiner = _split_pages(text)
    all_notes: list[str] = []
    corrected_pages: list[str] = []
    pages_touched = 0
    for page in pages:
        new_page, notes = correct_page(page)
        corrected_pages.append(new_page)
        if notes:
            pages_touched += 1
            all_notes.extend(notes)
    return _join_pages(corrected_pages, joiner), all_notes, pages_touched


def correct_h7c_path(
    path: Path,
    *,
    apply: bool = False,
    force_block: bool = True,
    h7c: Any | None = None,
) -> dict[str, Any]:
    h7c = h7c or _h7c_mod()
    blob = path.read_bytes()
    magic_v4 = getattr(h7c, "MAGIC_V4", b"H7C\x04")
    was_block = blob[:4] == magic_v4
    try:
        header, text, stats = h7c.decompress_h7c(blob, verify=True, update_balance_table=False)
    except Exception as exc:
        return {"ok": False, "path": str(path), "error": str(exc)}

    new_text, notes, pages_touched = correct_text(text)
    if was_block and not notes and new_text == text:
        return {
            "ok": True,
            "path": str(path),
            "changed": False,
            "applied": False,
            "skipped": "already_corrected",
            "was_block": True,
            "inner_format": header.get("format"),
        }

    repack_block = force_block and not was_block
    text_changed = new_text != text

    if repack_block and not text_changed:
        new_text = text
        if not new_text.endswith("\n"):
            new_text += "\n"
        pages, joiner = _split_pages(new_text)
        if pages:
            last = pages[-1]
            if CORRECTS_HDR not in last:
                pages[-1] = last + (
                    "\n\n## Corrects\n\n"
                    "- Repacked as H7c/4 ironclad block — field layer 1; inner text lossless."
                )
                new_text = _join_pages(pages, joiner)
                notes.append("Repacked as H7c/4 ironclad block — field layer 1")
                pages_touched = max(pages_touched, 1)
        text_changed = True

    changed = text_changed or repack_block
    row: dict[str, Any] = {
        "ok": True,
        "path": str(path),
        "changed": changed,
        "applied": False,
        "was_block": was_block or bool(stats.get("block_wrapper")),
        "inner_format": header.get("format"),
        "pages": len(_split_pages(new_text)[0]),
        "pages_corrected": pages_touched,
        "corrections": sorted(set(notes)),
        "text_sha_before": header.get("text_sha256"),
    }

    if not changed:
        row["skipped"] = "already_current"
        return row

    meta = {
        k: v
        for k, v in header.items()
        if k in ("id", "title", "source", "dewey", "author", "category", "ironclad_citation", "hostess7_lane")
    }
    meta.setdefault("ironclad_citation", "ironclad:h7c:1")
    meta["corrected_at"] = _now()
    meta["field_layer"] = CANONICAL_LAYER
    meta["block_wrapper"] = True
    meta["corrections_applied"] = len(notes)

    packed = h7c.pack_h7c(
        new_text, meta, use_optimizer=True, format_version=2, update_balance_table=False,
    )
    packed = h7c.wrap_h7c_block(packed, meta)
    _, round_text, round_stats = h7c.decompress_h7c(packed, verify=True, update_balance_table=False)
    if round_text != new_text:
        return {**row, "ok": False, "error": "roundtrip_mismatch"}

    row["text_sha_after"] = hashlib_hex(round_text)
    row["bytes_before"] = len(blob)
    row["bytes_after"] = len(packed)
    row["block_format"] = round_stats.get("block_format")

    if apply:
        snap = path.with_suffix(".h7c.snap.tmp")
        snap.write_bytes(packed)
        snap.replace(path)
        row["applied"] = True

    return row


def hashlib_hex(text: str) -> str:
    import hashlib
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def annotate_missing_corrects(
    path: Path,
    *,
    apply: bool = False,
    h7c: Any | None = None,
) -> dict[str, Any]:
    """Add last-page ## Corrects for block-repacked books that lack any Corrects section."""
    h7c = h7c or _h7c_mod()
    blob = path.read_bytes()
    if blob[:4] != getattr(h7c, "MAGIC_V4", b"H7C\x04"):
        return {"ok": True, "path": str(path), "skipped": "not_block", "changed": False}
    try:
        header, text, _ = h7c.decompress_h7c(blob, verify=False, update_balance_table=False)
    except Exception as exc:
        return {"ok": False, "path": str(path), "error": str(exc)}
    if CORRECTS_HDR in text:
        return {"ok": True, "path": str(path), "skipped": "has_corrects", "changed": False}
    pages, joiner = _split_pages(text)
    note = "Repacked as H7c/4 ironclad block — field layer 1; inner text lossless."
    pages[-1] = pages[-1].rstrip() + f"\n\n## Corrects\n\n- {note}\n"
    new_text = _join_pages(pages, joiner)
    meta = {
        k: v
        for k, v in header.items()
        if k in ("id", "title", "source", "dewey", "author", "category", "ironclad_citation", "hostess7_lane")
    }
    meta.setdefault("ironclad_citation", "ironclad:h7c:1")
    meta["corrected_at"] = _now()
    meta["field_layer"] = CANONICAL_LAYER
    meta["block_wrapper"] = True
    meta["corrections_applied"] = 1
    packed = h7c.wrap_h7c_block(
        h7c.pack_h7c(new_text, meta, use_optimizer=False, format_version=2, update_balance_table=False),
        meta,
    )
    if apply:
        snap = path.with_suffix(".h7c.snap.tmp")
        snap.write_bytes(packed)
        snap.replace(path)
    return {
        "ok": True,
        "path": str(path),
        "changed": True,
        "applied": apply,
        "annotation": note,
    }


def annotate_sweep(*, apply: bool = False, limit: int = 0) -> dict[str, Any]:
    paths = _glob_h7c()
    if limit > 0:
        paths = paths[:limit]
    STATE.mkdir(parents=True, exist_ok=True)
    bal = STATE / "field-h7c-balance-table.json"
    if not bal.is_file():
        bal.write_text("{}\n", encoding="utf-8")
    h7c = _h7c_mod()
    changed = 0
    errors: list[dict[str, Any]] = []
    for i, path in enumerate(paths):
        row = annotate_missing_corrects(path, apply=apply, h7c=h7c)
        if not row.get("ok"):
            errors.append(row)
        elif row.get("changed"):
            changed += 1
        if (i + 1) % 100 == 0:
            print(f"annotate {i + 1}/{len(paths)} changed={changed}", file=sys.stderr, flush=True)
    return {
        "schema": "field-h7c-annotate-sweep/v1",
        "updated": _now(),
        "ok": not errors,
        "apply": apply,
        "book_count": len(paths),
        "annotated_count": changed,
        "errors": errors[:16],
    }


def sweep(*, apply: bool = False, limit: int = 0, progress: bool = True) -> dict[str, Any]:
    paths = _glob_h7c()
    if limit > 0:
        paths = paths[:limit]
    rows: list[dict[str, Any]] = []
    changed_n = 0
    corrected_pages = 0
    errors: list[dict[str, Any]] = []
    t0 = time.perf_counter()
    h7c = _h7c_mod()
    total = len(paths)

    for i, path in enumerate(paths):
        row = correct_h7c_path(path, apply=apply, h7c=h7c)
        rows.append(row)
        if not row.get("ok"):
            errors.append(row)
            continue
        if row.get("changed"):
            changed_n += 1
            corrected_pages += int(row.get("pages_corrected") or 0)
        if progress and (i + 1) % 50 == 0:
            print(f"h7c-correct {i + 1}/{total} changed={changed_n}", file=sys.stderr, flush=True)

    manifest = {
        "schema": "field-h7c-correct-manifest/v1",
        "updated": _now(),
        "ok": len(errors) == 0,
        "apply": apply,
        "book_count": len(paths),
        "changed_count": changed_n,
        "pages_corrected_total": corrected_pages,
        "error_count": len(errors),
        "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
        "canonical_field_layer": CANONICAL_LAYER,
        "errors": errors[:32],
        "sample": [r for r in rows if r.get("changed")][:24],
    }
    if apply:
        _save(MANIFEST, manifest)
    return manifest


def main() -> int:
    apply = "--apply" in sys.argv
    limit = 0
    for arg in sys.argv[1:]:
        if arg.startswith("--limit="):
            limit = int(arg.split("=", 1)[1])
    cmd = next((a for a in sys.argv[1:] if not a.startswith("-")), "sweep").strip().lower()

    if cmd == "one" and len(sys.argv) >= 3:
        path = Path(sys.argv[2])
        out = correct_h7c_path(path, apply=apply)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("ok") else 1

    if cmd in ("sweep", "json", "all"):
        out = sweep(apply=apply, limit=limit)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("ok") else 1

    if cmd == "annotate":
        out = annotate_sweep(apply=apply, limit=limit)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("ok") else 1

    print(json.dumps({
        "error": "usage",
        "cmds": ["sweep [--apply] [--limit=N]", "annotate [--apply] [--limit=N]", "one <path> [--apply]", "json"],
    }))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())