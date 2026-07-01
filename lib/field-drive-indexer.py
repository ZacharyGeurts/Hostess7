#!/usr/bin/env pythong
"""Field drive table indexer — flat sorted paths, bucket prefetch, Sovereigntime history."""
from __future__ import annotations

import bisect
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any, Iterator

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
INDEX_DIR = STATE / "field-drive-index"
TABLE_PATH = INDEX_DIR / "table.json"
HISTORY_PATH = INDEX_DIR / "history.jsonl"
TOMBSTONE_PATH = STATE / "field-soft-vault" / "tombstones.jsonl"
SCHEMA = "field-drive-index/v1"

SKIP_DIRS = frozenset({
    ".git", "__pycache__", "node_modules", ".venv", ".venv-browser",
    "build", "dist", ".nexus-state", ".nexus-field-drive", "nexus-field",
})
SKIP_SUFFIXES = (".pyc", ".tmp", ".swp", ".o", ".o.d", ".a", ".map")

_SOVEREIGN = None
_CONVERTER = None


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _sovereign() -> Any:
    global _SOVEREIGN
    if _SOVEREIGN is None:
        _SOVEREIGN = _load_module("sovereign_clock", INSTALL / "lib" / "sovereign-clock.py")
    return _SOVEREIGN


def sovereign_ns() -> int:
    mod = _sovereign()
    if mod:
        return int(mod.ns_linear())
    import time
    return time.time_ns()


def sovereign_z(section: str = "drive_index") -> str:
    mod = _sovereign()
    if mod:
        return mod.utc_z(section)
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _drive_system_roots() -> list[Path]:
    fds = _load_module("field_drive_system", INSTALL / "lib" / "field-drive-system.py")
    if not fds:
        return []
    out: list[Path] = []
    for fn_name in ("primary_field_root", "publish_field_root"):
        fn = getattr(fds, fn_name, None)
        if not callable(fn):
            continue
        try:
            p = Path(fn())
            if p.is_dir() and p not in out:
                out.append(p.resolve())
            nf = p / "nexus-field"
            if nf.is_dir() and nf not in out:
                out.append(nf.resolve())
        except Exception:
            continue
    discover = getattr(fds, "discover_all_drives", None)
    if callable(discover):
        try:
            for drive in discover() or []:
                raw = str(drive.get("path") or drive.get("root") or "")
                if not raw:
                    continue
                p = Path(raw)
                if p.is_dir() and p not in out:
                    out.append(p.resolve())
        except Exception:
            pass
    return out


def _index_roots() -> list[Path]:
    """Whole field drive — TEAM storage, nexus-field, SG tree, install lib."""
    global _CONVERTER
    if _CONVERTER is None:
        _CONVERTER = _load_module("field_drive_converter", INSTALL / "lib" / "field-drive-converter.py")
    out: list[Path] = []
    if _CONVERTER and hasattr(_CONVERTER, "resolve_roots"):
        for p in _CONVERTER.resolve_roots():
            if p.is_dir() and p not in out:
                out.append(p.resolve())
    sg = Path(os.environ.get("SG_ROOT", INSTALL.parent))
    wide = os.environ.get("FIELD_INDEX_WIDE", "").strip().lower() in ("1", "true", "yes")
    candidates = [
        *_drive_system_roots(),
        INSTALL,
        INSTALL / "lib",
        INSTALL / "data",
        INSTALL / "panel",
        Path(os.environ.get("HOSTESS7_TEAM_FIELD", sg / "NewLatest" / "Hostess7" / "cache" / "fieldstorage")),
        sg / "Grok16" / "examples",
        sg / "Grok16" / "lib",
        sg / "Grok16" / "scripts",
        sg / "Grok16" / "data",
        sg / "World_Redata" / "redata",
    ]
    if wide:
        candidates.extend([sg, sg / "Grok16", sg / "NewLatest"])
    for p in candidates:
        if p.is_dir() and p not in out:
            out.append(p.resolve())
    extra = os.environ.get("FIELD_INDEX_ROOTS", "").strip()
    if extra:
        for part in extra.split(":"):
            p = Path(part).expanduser()
            if p.is_dir() and p not in out:
                out.append(p.resolve())
    return out


def _sort_key(path: str) -> str:
    return path.replace("\\", "/").lower()


def _base_key(path: str) -> str:
    name = Path(path).name
    return name.lower()


def _bucket_id(base_key: str) -> int:
    if not base_key:
        return 0
    return ord(base_key[0]) % 256


def _content_hash(path: Path) -> str | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    return hashlib.sha256(data).hexdigest()


def _load_tombstoned() -> set[str]:
    out: set[str] = set()
    if not TOMBSTONE_PATH.is_file():
        return out
    try:
        for line in TOMBSTONE_PATH.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            doc = json.loads(line)
            if doc.get("active", True):
                p = str(doc.get("path") or "")
                if p:
                    out.add(_sort_key(p))
    except (OSError, json.JSONDecodeError):
        pass
    return out


def _should_skip_dir(name: str) -> bool:
    return name in SKIP_DIRS or name.startswith(".") and name not in (".launch",)


def iter_files(roots: list[Path]) -> Iterator[Path]:
    """Single-pass depth walk — deepest paths collected, sorted once at build."""
    for root in roots:
        if not root.is_dir():
            continue
        stack: list[Path] = [root]
        while stack:
            current = stack.pop()
            try:
                with os.scandir(current) as it:
                    dirs: list[Path] = []
                    for entry in it:
                        try:
                            if entry.is_symlink():
                                continue
                            if entry.is_dir(follow_symlinks=False):
                                if not _should_skip_dir(entry.name):
                                    dirs.append(Path(entry.path))
                                continue
                            if not entry.is_file(follow_symlinks=False):
                                continue
                            p = Path(entry.path)
                            if p.suffix.lower() in SKIP_SUFFIXES:
                                continue
                            yield p
                        except OSError:
                            continue
                    stack.extend(reversed(dirs))
            except OSError:
                continue


def _stat_entry(path: Path) -> dict[str, Any] | None:
    try:
        st = path.stat()
    except OSError:
        return None
    resolved = str(path.resolve())
    base = path.name
    return {
        "path": resolved,
        "sort_key": _sort_key(resolved),
        "base_key": _base_key(resolved),
        "bucket": _bucket_id(_base_key(resolved)),
        "size": int(st.st_size),
        "mtime_ns": int(st.st_mtime_ns),
        "mode": int(st.st_mode),
        "ext": path.suffix.lower(),
        "name": base,
    }


def build_table(*, roots: list[Path] | None = None, include_tombstoned: bool = False) -> dict[str, Any]:
    """Prefetch every file under roots, sort once, bucket for instant prefix lookup."""
    roots = roots or _index_roots()
    tombstoned = _load_tombstoned() if not include_tombstoned else set()
    t0_ns = sovereign_ns()
    raw: list[dict[str, Any]] = []
    for fp in iter_files(roots):
        row = _stat_entry(fp)
        if not row:
            continue
        if row["sort_key"] in tombstoned:
            continue
        raw.append(row)

    drive_alg = os.environ.get("G16_BEST_DRIVE_SORT", "").strip() or "timsort_key"
    if drive_alg == "radix_bucket_256":
        buckets: dict[int, list[dict[str, Any]]] = {}
        for row in raw:
            buckets.setdefault(int(row.get("bucket") or 0), []).append(row)
        raw = []
        for b in sorted(buckets):
            raw.extend(sorted(buckets[b], key=lambda r: r["sort_key"]))
    else:
        raw.sort(key=lambda r: r["sort_key"])
    buckets: dict[str, list[int]] = {str(i): [] for i in range(256)}
    for idx, row in enumerate(raw):
        buckets[str(row["bucket"])].append(idx)

    indexed_ns = sovereign_ns()
    table = {
        "schema": SCHEMA,
        "indexed_at": sovereign_z("drive_index"),
        "indexed_at_ns": indexed_ns,
        "build_ms": round((indexed_ns - t0_ns) / 1_000_000, 2),
        "roots": [str(r) for r in roots],
        "file_count": len(raw),
        "entries": raw,
        "buckets": buckets,
        "algorithm": {
            "sort": drive_alg,
            "lookup": "bisect_lower_bound",
            "buckets": 256,
            "power_sort": True,
        },
    }
    return table


def save_table(table: dict[str, Any]) -> Path:
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    tmp = TABLE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(table, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(TABLE_PATH)
    _append_history({
        "action": "index_build",
        "sovereign_ns": table.get("indexed_at_ns"),
        "sovereign_at": table.get("indexed_at"),
        "file_count": table.get("file_count"),
        "roots": table.get("roots"),
    })
    return TABLE_PATH


def load_table() -> dict[str, Any]:
    if not TABLE_PATH.is_file():
        return {"schema": SCHEMA, "entries": [], "file_count": 0}
    try:
        return json.loads(TABLE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema": SCHEMA, "entries": [], "file_count": 0}


def _append_history(doc: dict[str, Any]) -> None:
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    doc.setdefault("sovereign_ns", sovereign_ns())
    doc.setdefault("sovereign_at", sovereign_z("drive_index"))
    with HISTORY_PATH.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(doc, ensure_ascii=False) + "\n")
    store = _load_module("efficient_store", INSTALL / "lib" / "efficient_store.py")
    if store and hasattr(store, "append_record"):
        try:
            store.append_record("drive.index", doc)
        except Exception:
            pass


def locate(path: str, *, table: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Exact path lookup — O(log n) on sorted flat index."""
    table = table or load_table()
    entries: list[dict[str, Any]] = table.get("entries") or []
    if not entries:
        return None
    key = _sort_key(path)
    keys = [e["sort_key"] for e in entries]
    idx = bisect.bisect_left(keys, key)
    if idx < len(entries) and entries[idx]["sort_key"] == key:
        return entries[idx]
    return None


def search(
    query: str,
    *,
    limit: int = 64,
    table: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Prefix / substring search — bucket-accelerated when query is one char."""
    table = table or load_table()
    entries: list[dict[str, Any]] = table.get("entries") or []
    if not entries or not query:
        return []
    q = query.lower().strip()
    out: list[dict[str, Any]] = []

    def _matches(row: dict[str, Any]) -> bool:
        sk = row.get("sort_key") or ""
        bk = row.get("base_key") or ""
        return sk.startswith(q) or bk.startswith(q) or q in bk

    buckets = table.get("buckets") or {}
    path_query = "/" in q or q.startswith(".")

    if path_query:
        keys = [e["sort_key"] for e in entries]
        start = bisect.bisect_left(keys, q)
        for row in entries[start:]:
            if row["sort_key"].startswith(q):
                out.append(row)
                if len(out) >= limit:
                    break
            elif row["sort_key"] > q and not row["sort_key"].startswith(q[: min(4, len(q))]):
                break
        return out

    first = ord(q[0]) % 256
    order = [first] + [bi for bi in range(256) if bi != first]
    for bi in order:
        for idx in buckets.get(str(bi), []):
            if idx >= len(entries):
                continue
            row = entries[idx]
            if _matches(row):
                out.append(row)
                if len(out) >= limit:
                    return out
    return out


def now_snapshot() -> dict[str, Any]:
    """Table indexer view of exact-now files with sovereign stamp."""
    table = load_table()
    if not table.get("entries"):
        table = build_table()
        save_table(table)
    return {
        "schema": "field-drive-now/v1",
        "sovereign_at": table.get("indexed_at"),
        "sovereign_ns": table.get("indexed_at_ns"),
        "file_count": table.get("file_count"),
        "build_ms": table.get("build_ms"),
        "table_path": str(TABLE_PATH),
        "history_path": str(HISTORY_PATH),
    }


def diff_since(path: str) -> list[dict[str, Any]]:
    """Return history lines mentioning a path (rollback lineage)."""
    key = _sort_key(path)
    out: list[dict[str, Any]] = []
    if not HISTORY_PATH.is_file():
        return out
    try:
        for line in HISTORY_PATH.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            doc = json.loads(line)
            p = _sort_key(str(doc.get("path") or ""))
            if p == key or key in str(doc.get("original_path") or ""):
                out.append(doc)
    except (OSError, json.JSONDecodeError):
        pass
    return out


def history_for_path(path: str, *, limit: int = 12) -> list[dict[str, Any]]:
    """Always-files lineage hook — recent index/timeshift events for a path."""
    rows = diff_since(path)
    if rows:
        return rows[-limit:]
    if not HISTORY_PATH.is_file():
        return []
    norm = path.replace("\\", "/").lower()
    tail: list[dict[str, Any]] = []
    try:
        lines = [ln for ln in HISTORY_PATH.read_text(encoding="utf-8").splitlines() if ln.strip()]
    except OSError:
        return []
    for line in reversed(lines):
        try:
            doc = json.loads(line)
        except json.JSONDecodeError:
            continue
        blob = json.dumps(doc, ensure_ascii=False).lower()
        if norm and norm in blob:
            tail.append(doc)
        elif doc.get("action") in ("index_build", "timeshift_checkpoint", "timeshift_rollback"):
            tail.append(doc)
        if len(tail) >= limit:
            break
    return list(reversed(tail))


def panel_json() -> dict[str, Any]:
    table = load_table()
    now = now_snapshot()
    return {
        "schema": SCHEMA,
        "now": now,
        "file_count": table.get("file_count", 0),
        "indexed_at": table.get("indexed_at"),
        "roots": table.get("roots", []),
        "table_path": str(TABLE_PATH),
        "history_path": str(HISTORY_PATH),
        "tombstone_path": str(TOMBSTONE_PATH),
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd == "build":
        table = build_table()
        path = save_table(table)
        print(json.dumps({"ok": True, "path": str(path), "file_count": table["file_count"]}, ensure_ascii=False, indent=2))
        return 0
    if cmd == "now":
        print(json.dumps(now_snapshot(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "locate" and len(sys.argv) > 2:
        hit = locate(sys.argv[2])
        print(json.dumps(hit or {"ok": False, "error": "not_indexed"}, ensure_ascii=False, indent=2))
        return 0 if hit else 1
    if cmd == "search" and len(sys.argv) > 2:
        hits = search(sys.argv[2], limit=int(os.environ.get("FIELD_INDEX_SEARCH_LIMIT", "64")))
        print(json.dumps({"query": sys.argv[2], "count": len(hits), "hits": hits}, ensure_ascii=False, indent=2))
        return 0
    if cmd == "history" and len(sys.argv) > 2:
        print(json.dumps(diff_since(sys.argv[2]), ensure_ascii=False, indent=2))
        return 0
    if cmd == "panel":
        print(json.dumps(panel_json(), ensure_ascii=False, indent=2))
        return 0
    print(
        json.dumps(
            {
                "error": "usage",
                "cmds": ["build", "now", "locate PATH", "search QUERY", "history PATH", "panel"],
            },
            ensure_ascii=False,
        ),
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())