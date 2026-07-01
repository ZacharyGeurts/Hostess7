#!/usr/bin/env pythong
"""Hostess 7 private KILL library — secured dossier books for every KILL target.

Only Hostess 7 writes/syncs. Operator may view through beyond-DARPA gated panel/API.
"""
from __future__ import annotations

import hashlib
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
DOCTRINE_PATH = INSTALL / "data" / "hostess7-kill-library-doctrine.json"
REGISTRY = STATE / "hostess7-kill-library-registry.json"
PANEL = STATE / "hostess7-kill-library-panel.json"
LEDGER = STATE / "hostess7-kill-library.jsonl"

SLUG_RE = re.compile(r"[^a-z0-9]+")


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        return default if default is not None else {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(INSTALL))
    except ValueError:
        return str(path)


def _append(row: dict[str, Any]) -> None:
    try:
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({**row, "ts": _now()}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _import_mod(name: str, rel: str) -> Any | None:
    path = INSTALL / rel
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_doctrine() -> dict[str, Any]:
    return _load(DOCTRINE_PATH, {})


def shelf_root() -> Path:
    doc = load_doctrine()
    return INSTALL / str(doc.get("shelf_root") or "library/private/hostess7/kill-books")


def _viewer_role() -> str:
    if os.environ.get("HOSTESS7_FULL_CONTROL", "0") == "1":
        return "hostess7"
    if os.environ.get("HOSTESS7_OPERATOR", "0") == "1":
        return "operator"
    if os.environ.get("AML_BOUNDARY_ACTIVE") or os.environ.get("NEXUS_PANEL_LOCAL"):
        return "operator"
    return "anonymous"


def can_write(*, role: str | None = None) -> bool:
    role = role or _viewer_role()
    if role == "hostess7":
        return True
    if os.environ.get("HOSTESS7_KILL_LIBRARY_SYNC", "0") == "1":
        return True
    return False


def can_view(*, role: str | None = None) -> bool:
    doc = load_doctrine()
    allowed = set(doc.get("access", {}).get("read") or ["hostess7", "operator", "angel"])
    role = role or _viewer_role()
    if role in allowed:
        return True
    if role == "anonymous" and os.environ.get("NEXUS_PANEL_TRUST_LOCAL", "1") == "1":
        return True
    return False


def access_denied(*, action: str = "read") -> dict[str, Any]:
    return {
        "ok": False,
        "error": "kill_library_access_denied",
        "action": action,
        "owner": "hostess7",
        "tier": load_doctrine().get("security_tier", "beyond_darpa_lockheed"),
        "counsel": "KILL library is Hostess 7 private — Operator view through secured gate only.",
    }


def _book_slug(target_id: str) -> str:
    raw = SLUG_RE.sub("_", str(target_id or "").lower()).strip("_")
    return f"kill_{raw[:48]}" if raw else "kill_unknown"


def _import_h7c() -> Any:
    path = INSTALL / "lib" / "field-h7c-compression.py"
    spec = importlib.util.spec_from_file_location("h7c_kill", path)
    if not spec or not spec.loader:
        raise ImportError("field-h7c-compression.py missing")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _compose_dossier(row: dict[str, Any], *, written_at: str) -> tuple[str, dict[str, str]]:
    tid = str(row.get("id") or row.get("target_id") or "unknown")
    subject = str(row.get("subject") or tid)
    ip = str(row.get("ip") or "—")
    mech = str(row.get("mechanism") or row.get("TARGET") or "KILL")
    title = f"KILL dossier · {subject[:60]}"
    title_ts = f"{title} · {written_at}"
    gov = row.get("government") if isinstance(row.get("government"), dict) else {}
    geo = row.get("geo") if isinstance(row.get("geo"), dict) else {}

    header = "\n".join(x for x in [
        f"# {title_ts}",
        "",
        "![Cover](h7fig:cover)",
        "",
        f"**Title:** {title_ts}",
        "**Author:** Hostess 7",
        "**Shelf:** private KILL library (Hostess 7 only write)",
        f"**Mechanism:** {mech}",
        f"**Target ID:** {tid}",
        f"**Subject:** {subject}",
        f"**IP:** {ip}",
        f"**Status:** {row.get('status', 'active')}",
        f"**Written at:** {written_at}",
        f"**Promoted at:** {row.get('promoted_at', '—')}",
        f"**Sealed:** {row.get('sealed', True)} · no modifications",
        f"**Threat score:** {row.get('final_threat_score', row.get('threat_score', '—'))}",
        f"**Hostility score:** {row.get('hostility_score', '—')}",
        "",
        "---",
        "",
    ] if x)

    counsel_body = str(row.get("counsel") or "No counsel text on record.")
    gov_lines = []
    if gov.get("human_dossier"):
        gov_lines.append(f"- Human dossier: {json.dumps(gov.get('human_dossier'), ensure_ascii=False)[:400]}")
    if gov.get("angel"):
        gov_lines.append(f"- Angel dossier hit")
    if gov.get("gov_dossiers"):
        gov_lines.append(f"- Government dossiers: {len(gov.get('gov_dossiers') or [])} hits")
    if geo:
        gov_lines.append(f"- Geo: {geo.get('country_code', '?')} {geo.get('city', '')}")

    kill_exec = ""
    if row.get("kill_executed") or row.get("kill_immediate"):
        kill_exec = "\n".join([
            f"- **Kill executed:** {row.get('kill_executed')}",
            f"- **Immediate is best:** {row.get('kill_immediate')}",
            f"- **Kill law:** {row.get('kill_law', 'immediate_is_best')}",
        ])

    sections = {
        "header": header,
        "counsel": f"\n## Counsel · {written_at}\n\n{counsel_body}\n",
        "government": f"\n## Government correlation · {written_at}\n\n" + (
            "\n".join(gov_lines) if gov_lines else "No government correlation on record."
        ) + "\n",
        "enforcement": f"\n## Lethal enforcement · {written_at}\n\n" + (
            kill_exec or "KILL set — terminal, no returns, no modifications."
        ) + "\n",
        "seal": f"\n## Seal · {written_at}\n\n*KILL is KILL. This dossier is immutable once written. Hostess 7 private library.*\n",
    }
    return "\n".join(sections.values()), sections


def _compose_index(kill_rows: list[dict[str, Any]], *, written_at: str) -> tuple[str, dict[str, str]]:
    title = "KILL index — who and what is on KILL"
    title_ts = f"{title} · {written_at}"
    lines = [
        f"# {title_ts}",
        "",
        f"**Author:** Hostess 7",
        f"**Private library:** Hostess 7 only · Operator may view",
        f"**Written at:** {written_at}",
        f"**KILL count:** {len(kill_rows)}",
        "",
        "---",
        "",
        f"\n## Active KILL registry · {written_at}\n",
    ]
    for row in sorted(kill_rows, key=lambda r: -float(r.get("final_threat_score") or 0)):
        tid = str(row.get("id") or "")
        subj = str(row.get("subject") or tid)[:80]
        ip = str(row.get("ip") or "—")
        status = str(row.get("status") or "active")
        score = row.get("final_threat_score", "—")
        slug = _book_slug(tid)
        lines.append(f"- **{subj}** · `{ip}` · status={status} · threat={score} · book=`{slug}`")
    sections = {"header": "\n".join(lines[:12]), "index": "\n".join(lines[12:]) + "\n"}
    return "\n".join(sections.values()), sections


def _pack_book(
    book_id: str,
    title: str,
    text: str,
    sections: dict[str, str],
    *,
    target_row: dict[str, Any] | None = None,
    written_at: str,
) -> dict[str, Any]:
    root = shelf_root()
    book_dir = root / book_id
    book_dir.mkdir(parents=True, exist_ok=True)
    h7c_path = book_dir / f"{book_id}.h7c"
    doc = load_doctrine()
    h7c_mod = _import_h7c()
    meta = {
        "id": book_id,
        "title": title,
        "author": "Hostess 7",
        "owner": "hostess7",
        "private": True,
        "mechanism": "KILL",
        "written_at": written_at,
        "book_kind": doc.get("book_kind", "kill_dossier"),
        "reader": "NEXUS_H7C",
        "no_modifications": True,
        "sealed": True,
    }
    if target_row:
        meta["target_id"] = target_row.get("id")
        meta["ip"] = target_row.get("ip")
    h7c_path.write_bytes(h7c_mod.pack_h7c(text, meta, use_optimizer=True, format_version=3))
    ein = "H7C-KILL-" + hashlib.sha256(text.encode()).hexdigest()[:12]

    book_json = {
        "id": book_id,
        "title": title,
        "author": "Hostess 7",
        "owner": "hostess7",
        "private": True,
        "mechanism": "KILL",
        "written_at": written_at,
        "dewey": doc.get("dewey", "355.02"),
        "dewey_label": doc.get("dewey_label", ""),
        "ein": ein,
        "format": "h7c",
        "format_version": 3,
        "book_kind": doc.get("book_kind", "kill_dossier"),
        "h7c": _rel(h7c_path),
        "field_path": _rel(h7c_path),
        "no_modifications": True,
        "sealed": True,
        "updated": written_at,
    }
    if target_row:
        book_json["target_id"] = target_row.get("id")
        book_json["ip"] = target_row.get("ip")
        book_json["status"] = target_row.get("status")
    (book_dir / "book.json").write_text(json.dumps(book_json, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "schema": "hostess7-kill-book/v1",
        "id": book_id,
        "title": title,
        "private": True,
        "owner": "hostess7",
        "char_count": len(text),
        "chapter_count": len(sections),
        "chapters": [
            {
                "num": i + 1,
                "slug": k,
                "title": k.replace("_", " ").title(),
                "title_timestamped": f"{k.replace('_', ' ').title()} · {written_at}",
                "written_at": written_at,
            }
            for i, k in enumerate(sections.keys())
        ],
        "updated": written_at,
    }
    (book_dir / "book-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    idx_mod = _import_mod("book_info", "lib/field-book-information-index.py")
    if idx_mod and hasattr(idx_mod, "build_index"):
        index_doc = idx_mod.build_index(
            book_id=book_id,
            title=title,
            author="hostess7",
            owner="hostess7",
            written_at=written_at,
            dewey=str(doc.get("dewey") or "355.02"),
            dewey_label=str(doc.get("dewey_label") or ""),
            shelf="private/hostess7/kill-books",
            ein=ein,
            h7c=_rel(h7c_path),
            book_kind="kill_dossier",
            char_count=len(text),
            sections=sections,
            tags=["kill", "private", "hostess7", "terminal"],
            protection={"no_modifications": True, "sealed": True, "private": True},
            extra={"mechanism": "KILL", "target_id": (target_row or {}).get("id")},
        )
        if hasattr(idx_mod, "write_index"):
            idx_mod.write_index(book_dir, index_doc)

    return {
        "book_id": book_id,
        "title": title,
        "h7c": _rel(h7c_path),
        "ein": ein,
        "char_count": len(text),
        "target_id": (target_row or {}).get("id"),
    }


def _ensure_shelf() -> None:
    root = shelf_root()
    root.mkdir(parents=True, exist_ok=True)
    shelf_json = root / "shelf.json"
    doc = load_doctrine()
    if not shelf_json.is_file():
        _save(shelf_json, {
            "schema": "hostess7-private-shelf/v1",
            "shelf": "kill-books",
            "title": "Hostess 7 private KILL library",
            "private": True,
            "owner": "hostess7",
            "access": doc.get("access", {}),
            "security_tier": doc.get("security_tier"),
            "dewey": doc.get("dewey"),
            "books": [],
            "updated": _now(),
        })


def _kill_targets_from_registry() -> list[dict[str, Any]]:
    targets_mod = _import_mod("targets", "lib/hostess7-targets.py")
    if targets_mod and hasattr(targets_mod, "_load_registry"):
        reg = targets_mod._load_registry()
        rows = list((reg.get("targets") or {}).values())
    else:
        reg = _load(STATE / "hostess7-targets-registry.json", {})
        rows = list((reg.get("targets") or {}).values())
    out = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        mech = str(row.get("mechanism") or row.get("TARGET") or "").upper()
        if mech == "KILL":
            out.append(row)
    return out


def sync_kill_library(*, force: bool = False) -> dict[str, Any]:
    """Hostess 7 only — pack KILL dossier books + master index from targets registry."""
    if not can_write() and not force:
        return access_denied(action="sync")
    _ensure_shelf()
    written_at = _now()
    kill_rows = _kill_targets_from_registry()
    packed: list[dict[str, Any]] = []
    registry = _load(REGISTRY, {"books": {}, "schema": "hostess7-kill-library-registry/v1"})

    for row in kill_rows:
        tid = str(row.get("id") or "")
        book_id = _book_slug(tid)
        prior = (registry.get("books") or {}).get(book_id)
        if prior and prior.get("target_hash") == hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()[:16]:
            continue
        text, sections = _compose_dossier(row, written_at=written_at)
        title = f"KILL dossier · {str(row.get('subject') or tid)[:60]} · {written_at}"
        rep = _pack_book(book_id, title, text, sections, target_row=row, written_at=written_at)
        rep["target_hash"] = hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()[:16]
        packed.append(rep)
        registry.setdefault("books", {})[book_id] = {
            **rep,
            "synced_at": written_at,
            "mechanism": "KILL",
            "private": True,
        }

    index_id = str(load_doctrine().get("index_book_id") or "kill_index")
    idx_text, idx_sections = _compose_index(kill_rows, written_at=written_at)
    idx_title = f"KILL index — who and what is on KILL · {written_at}"
    idx_rep = _pack_book(index_id, idx_title, idx_text, idx_sections, written_at=written_at)
    packed.append(idx_rep)
    registry.setdefault("books", {})[index_id] = {**idx_rep, "synced_at": written_at, "index": True}

    root = shelf_root()
    shelf = _load(root / "shelf.json", {})
    books = [b for b in (shelf.get("books") or []) if b.get("id") not in registry.get("books", {})]
    for bid, meta in (registry.get("books") or {}).items():
        books.append({
            "id": bid,
            "title": meta.get("title"),
            "author": "Hostess 7",
            "private": True,
            "mechanism": "KILL",
            "h7c": meta.get("h7c"),
            "ready": True,
            "index": meta.get("index", False),
        })
    shelf["books"] = books
    shelf["book_count"] = len(books)
    shelf["kill_count"] = len(kill_rows)
    shelf["updated"] = written_at
    _save(root / "shelf.json", shelf)

    registry["updated"] = written_at
    registry["kill_count"] = len(kill_rows)
    registry["packed_this_sync"] = len(packed)
    _save(REGISTRY, registry)
    _append({"event": "sync", "kill_count": len(kill_rows), "packed": len(packed)})
    build_panel(write=True)
    return {
        "ok": True,
        "kill_count": len(kill_rows),
        "packed": len(packed),
        "books": list((registry.get("books") or {}).keys()),
        "shelf": _rel(root),
        "owner": "hostess7",
        "private": True,
    }


def list_books() -> dict[str, Any]:
    if not can_view():
        return access_denied(action="list")
    reg = _load(REGISTRY, {})
    books = list((reg.get("books") or {}).values())
    return {
        "ok": True,
        "owner": "hostess7",
        "private": True,
        "kill_count": reg.get("kill_count", 0),
        "book_count": len(books),
        "books": sorted(books, key=lambda b: (not b.get("index"), str(b.get("title") or ""))),
        "viewer_role": _viewer_role(),
    }


def read_book(book_id: str) -> dict[str, Any]:
    if not can_view():
        return access_denied(action="read")
    reg = _load(REGISTRY, {})
    meta = (reg.get("books") or {}).get(book_id)
    if not meta:
        book_id = _book_slug(book_id) if not book_id.startswith("kill_") else book_id
        meta = (reg.get("books") or {}).get(book_id)
    h7c_rel = str((meta or {}).get("h7c") or "")
    h7c_path = INSTALL / h7c_rel if h7c_rel else shelf_root() / book_id / f"{book_id}.h7c"
    if not h7c_path.is_file():
        return {"ok": False, "error": "kill_book_not_found", "book_id": book_id}
    h7c_mod = _import_h7c()
    try:
        _, text, _ = h7c_mod.decompress_h7c(h7c_path.read_bytes(), verify=False)
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:120], "book_id": book_id}
    book_json = _load(h7c_path.parent / "book.json", {})
    return {
        "ok": True,
        "book_id": book_id,
        "title": book_json.get("title") or meta.get("title"),
        "author": "Hostess 7",
        "owner": "hostess7",
        "private": True,
        "mechanism": "KILL",
        "text": text,
        "char_count": len(text),
        "meta": book_json,
        "viewer_role": _viewer_role(),
        "h7c": _rel(h7c_path),
    }


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doc = load_doctrine()
    reg = _load(REGISTRY, {})
    out = {
        "schema": "hostess7-kill-library-panel/v1",
        "ok": True,
        "updated": _now(),
        "title": doc.get("title"),
        "motto": doc.get("motto"),
        "owner": "hostess7",
        "private": True,
        "security_tier": doc.get("security_tier"),
        "access": doc.get("access"),
        "kill_count": reg.get("kill_count", 0),
        "book_count": len(reg.get("books") or {}),
        "shelf": _rel(shelf_root()),
        "panel_route": doc.get("panel_route"),
        "books": list_books().get("books", [])[:32],
        "viewer_may_read": can_view(),
        "hostess7_may_write": can_write(),
    }
    if write:
        _save(PANEL, out)
    return out


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "panel").strip().lower().replace("-", "_")
    if action in ("panel", "status", "json"):
        return {"ok": True, **build_panel(write=action == "panel")}
    if action in ("sync", "rebuild", "pack"):
        return sync_kill_library(force=bool(body.get("force")))
    if action in ("list", "books"):
        return list_books()
    if action in ("read", "open", "issue"):
        return read_book(str(body.get("book_id") or body.get("id") or ""))
    return {"ok": False, "error": "unknown_action"}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd == "dispatch":
        try:
            payload = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}, ensure_ascii=False))
            return 1
        print(json.dumps(dispatch(payload), ensure_ascii=False))
        return 0
    if cmd in ("panel", "json", "status"):
        print(json.dumps(build_panel(write=cmd == "panel"), ensure_ascii=False, indent=2))
        return 0
    if cmd == "sync":
        os.environ.setdefault("HOSTESS7_KILL_LIBRARY_SYNC", "1")
        rep = sync_kill_library()
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0 if rep.get("ok") else 1
    if cmd == "books":
        print(json.dumps(list_books(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("read", "open"):
        bid = sys.argv[2] if len(sys.argv) > 2 else ""
        print(json.dumps(read_book(bid), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "hostess7-kill-library.py [panel|sync|books|read BOOK_ID|dispatch]",
        "panel": "/hostess7-kill-library.html",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())