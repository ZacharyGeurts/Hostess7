#!/usr/bin/env pythong
"""NEXUS file catalog — every install-tree file with role, hash, and description.

Drives incremental updates (hash diff) and 0.9+ release manifests.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterator

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parent.parent))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
SCHEMA = "nexus-file-catalog/v1"

EXCLUDE_DIR_NAMES = {
    ".git",
    ".nexus-state",
    ".nexus-state-test",
    ".nexus-field-drive",
    ".wiki-publish",
    ".pages-publish",
    "dist",
    "cache",
    "state",
    "__pycache__",
    "AMOURANTHRTX",
    "Grok16",
    "GrokPy",
    "PythonG",
    "KILROY",
    "Final_Eye",
    "Final_Ear",
            "ZNetwork",
    "World_Redata",
    "World_Repack",
    "Field_Primer",
    "Spiderweb",
}
EXCLUDE_PREFIXES = (
    "Queen/build",
    "Queen/build-",
    "Queen/vendor",
    "Queen/cache",
    "Queen/field/sovereign",
    "Queen/field-gecko/profile",
    "Queen/.venv",
    "Hostess7/cache",
    "Hostess7/zac",
    "Textbook/staging",
    "hostess7-training-viewer/",
)
EXCLUDE_GLOBS = ("*.pyc", "*.log", "*.jsonl", "*.img", "MANIFEST.sha256.bak")

ROLE_PREFIXES: list[tuple[str, str]] = [
    ("lib/", "runtime"),
    ("panel/", "panel"),
    ("config/", "config"),
    ("data/", "data"),
    ("scripts/", "scripts"),
    ("bin/", "bin"),
    ("install/", "install"),
    ("Queen/", "queen"),
    ("Hostess7/", "hostess7"),
    ("nxf/", "manifest"),
    ("wiki/", "wiki"),
    ("docs/", "docs"),
    ("assets/", "assets"),
]

ROLE_LABELS = {
    "runtime": "NEXUS runtime module",
    "panel": "Threat panel UI asset",
    "config": "Configuration",
    "data": "Field data / doctrine seed",
    "scripts": "Release and boot script",
    "bin": "CLI entrypoint",
    "install": "Installer payload",
    "queen": "Queen field browser",
    "hostess7": "Hostess 7 field corpus",
    "manifest": "NXF release manifest",
    "wiki": "Wiki documentation",
    "docs": "Documentation",
    "assets": "Branding / static asset",
    "root": "Top-level launcher",
}


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_version(root: Path) -> str:
    common = root / "lib" / "nexus-common.sh"
    if common.is_file():
        m = re.search(r'NEXUS_VERSION="([^"]+)"', common.read_text(encoding="utf-8", errors="replace"))
        if m:
            return m.group(1)
    return os.environ.get("NEXUS_VERSION", "unknown")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _role_for(rel: str) -> str:
    for prefix, role in ROLE_PREFIXES:
        if rel.startswith(prefix):
            return role
    return "root"


def _basename_hint(name: str) -> str:
    stem = Path(name).stem.replace("-", " ").replace("_", " ")
    return stem.strip() or name


def _first_line_doc(path: Path) -> str | None:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")[:4096]
    except OSError:
        return None
    if path.suffix == ".py":
        m = re.search(r'"""(.*?)"""', text, re.DOTALL)
        if m:
            line = m.group(1).strip().splitlines()[0].strip()
            return line[:240] if line else None
        m = re.search(r"'''(.*?)'''", text, re.DOTALL)
        if m:
            line = m.group(1).strip().splitlines()[0].strip()
            return line[:240] if line else None
        for line in text.splitlines()[:8]:
            s = line.strip()
            if s.startswith("#") and len(s) > 2:
                return s.lstrip("# ").strip()[:240]
    if path.suffix in (".sh", ".bash"):
        for line in text.splitlines()[:12]:
            s = line.strip()
            if s.startswith("#") and not s.startswith("#!"):
                body = s.lstrip("# ").strip()
                if body and not body.startswith("shellcheck"):
                    return body[:240]
    if path.suffix == ".html":
        m = re.search(r"<title[^>]*>([^<]+)</title>", text, re.I)
        if m:
            return m.group(1).strip()[:240]
    if path.suffix == ".json":
        try:
            doc = json.loads(text)
            if isinstance(doc, dict):
                for key in ("title", "name", "description", "id", "label"):
                    val = doc.get(key)
                    if isinstance(val, str) and val.strip():
                        return val.strip()[:240]
        except json.JSONDecodeError:
            pass
    if path.suffix in (".md", ".txt"):
        for line in text.splitlines()[:6]:
            s = line.strip().lstrip("#").strip()
            if s:
                return s[:240]
    return None


def _describe(rel: str, path: Path) -> str:
    doc = _first_line_doc(path)
    if doc:
        return doc
    role = _role_for(rel)
    label = ROLE_LABELS.get(role, "NEXUS file")
    hint = _basename_hint(path.name)
    return f"{label}: {hint}"


def _excluded(rel: str) -> bool:
    parts = Path(rel).parts
    for part in parts:
        if part in EXCLUDE_DIR_NAMES:
            return True
        if part.startswith(".nexus-"):
            return True
    for prefix in EXCLUDE_PREFIXES:
        if rel == prefix or rel.startswith(prefix):
            return True
    name = Path(rel).name
    for pat in EXCLUDE_GLOBS:
        if pat.startswith("*") and name.endswith(pat[1:]):
            return True
    return False


def _prune_walk_dirs(root: Path, dirpath: str, names: list[str]) -> None:
    rel_dir = Path(dirpath).relative_to(root).as_posix()
    if rel_dir == ".":
        rel_dir = ""
    drop: list[str] = []
    for name in names:
        child = f"{rel_dir}/{name}" if rel_dir else name
        if name in EXCLUDE_DIR_NAMES or name.startswith(".nexus-"):
            drop.append(name)
            continue
        for prefix in EXCLUDE_PREFIXES:
            if child == prefix.rstrip("/") or child.startswith(prefix):
                drop.append(name)
                break
    for name in drop:
        names.remove(name)


def iter_catalog_files(root: Path) -> Iterator[Path]:
    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        _prune_walk_dirs(root, dirpath, dirnames)
        base = Path(dirpath)
        for name in sorted(filenames):
            path = base / name
            rel = path.relative_to(root).as_posix()
            if _excluded(rel):
                continue
            yield path


def build_catalog(root: Path | None = None) -> dict[str, Any]:
    root = root or INSTALL
    version = _read_version(root)
    files: list[dict[str, Any]] = []
    by_role: dict[str, int] = {}
    for path in iter_catalog_files(root):
        rel = path.relative_to(root).as_posix()
        role = _role_for(rel)
        by_role[role] = by_role.get(role, 0) + 1
        try:
            size = path.stat().st_size
        except OSError:
            size = 0
        row = {
            "path": rel,
            "sha256": _sha256(path),
            "size": size,
            "role": role,
            "description": _describe(rel, path),
            "deleted": False,
            "destroyed": False,
        }
        try:
            fsu = Path(__file__).resolve().parent / "field-filesystem-update.py"
            if fsu.is_file():
                import importlib.util
                spec = importlib.util.spec_from_file_location("field_filesystem_update", fsu)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    row = mod.enrich_catalog_row(row)
        except Exception:
            pass
        files.append(row)
    return {
        "schema": SCHEMA,
        "product": "nexus-shield",
        "version": version,
        "generated_at": _now(),
        "install_root": str(root),
        "file_count": len(files),
        "roles": by_role,
        "files": files,
    }


def load_catalog(path: Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("schema") != SCHEMA:
        raise ValueError(f"unsupported catalog schema: {doc.get('schema')}")
    return doc


def catalog_index(doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["path"]: row for row in doc.get("files") or [] if row.get("path")}


def diff_catalogs(local: dict[str, Any], remote: dict[str, Any]) -> dict[str, Any]:
    loc = catalog_index(local)
    rem = catalog_index(remote)
    changed: list[dict[str, Any]] = []
    added: list[dict[str, Any]] = []
    removed: list[str] = []
    for path, row in rem.items():
        prev = loc.get(path)
        if not prev:
            added.append(row)
        elif prev.get("sha256") != row.get("sha256"):
            changed.append({**row, "previous_sha256": prev.get("sha256")})
    for path in loc:
        if path not in rem:
            removed.append(path)
    return {
        "ok": True,
        "local_version": local.get("version"),
        "remote_version": remote.get("version"),
        "changed": changed,
        "added": added,
        "removed": removed,
        "changed_count": len(changed),
        "added_count": len(added),
        "removed_count": len(removed),
        "total_delta": len(changed) + len(added),
    }


def _corps_learn_catalog(file_count: int) -> None:
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "nexus_librarian_corps",
            Path(__file__).resolve().parent / "nexus-librarian-corps.py",
        )
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            mod.learn("nexus_file_catalog", detail=f"file_count={file_count}")
    except Exception:
        pass


def write_catalog(path: Path, root: Path | None = None) -> dict[str, Any]:
    doc = build_catalog(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _corps_learn_catalog(doc.get("file_count", 0))
    return doc


def main() -> int:
    root = INSTALL
    if len(sys.argv) < 2:
        print(json.dumps(build_catalog(root), ensure_ascii=False))
        return 0
    cmd = sys.argv[1]
    if cmd == "build":
        out = Path(sys.argv[2]) if len(sys.argv) > 2 else root / "data" / "nexus-file-catalog.json"
        doc = write_catalog(out, root)
        print(json.dumps({"ok": True, "path": str(out), "file_count": doc["file_count"], "version": doc["version"]}, ensure_ascii=False))
        return 0
    if cmd == "stats":
        doc = build_catalog(root)
        print(json.dumps({"ok": True, "file_count": doc["file_count"], "roles": doc["roles"], "version": doc["version"]}, ensure_ascii=False))
        return 0
    if cmd == "diff" and len(sys.argv) > 2:
        remote_path = Path(sys.argv[2])
        local_doc = build_catalog(root)
        remote_doc = load_catalog(remote_path) if remote_path.is_file() else json.loads(remote_path.read_text())
        print(json.dumps(diff_catalogs(local_doc, remote_doc), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: nexus-file-catalog.py [build PATH|stats|diff REMOTE]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())