#!/usr/bin/env pythong
"""NEXUS incremental update — apply only catalog-diff files from a release tree."""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parent.parent))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))


def _load_catalog_mod():
    spec = importlib.util.spec_from_file_location(
        "nexus_file_catalog",
        Path(__file__).resolve().parent / "nexus-file-catalog.py",
    )
    if not spec or not spec.loader:
        raise ImportError("nexus-file-catalog.py missing")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _fetch_json(url: str, timeout: int = 20) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "NEXUS-Shield-Incremental"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "NEXUS-Shield-Incremental"})
    with urllib.request.urlopen(req, timeout=120) as resp, dest.open("wb") as out:
        shutil.copyfileobj(resp, out)


def _find_extract_root(base: Path, version: str) -> Path | None:
    ver = version.lstrip("v")
    for candidate in (
        base / f"nexus-shield-{ver}",
        base / f"nexus-shield-{version}",
    ):
        if (candidate / "install-all.sh").is_file() or (candidate / "nexus.sh").is_file():
            return candidate
    for found in base.rglob("install-all.sh"):
        return found.parent
    for found in base.rglob("nexus.sh"):
        return found.parent
    return None


def plan_update(
    *,
    install_root: Path | None = None,
    remote_catalog_url: str,
    local_catalog_path: Path | None = None,
) -> dict[str, Any]:
    cat = _load_catalog_mod()
    root = install_root or INSTALL
    local_path = local_catalog_path or root / "data" / "nexus-file-catalog.json"
    if local_path.is_file():
        local_doc = cat.load_catalog(local_path)
    else:
        local_doc = cat.build_catalog(root)
    try:
        remote_doc = _fetch_json(remote_catalog_url)
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError, OSError) as exc:
        return {"ok": False, "error": "remote_catalog_fetch_failed", "detail": str(exc)}
    if remote_doc.get("schema") != cat.SCHEMA:
        return {"ok": False, "error": "unsupported_remote_catalog"}
    diff = cat.diff_catalogs(local_doc, remote_doc)
    paths = [r["path"] for r in diff.get("changed") or []] + [r["path"] for r in diff.get("added") or []]
    return {
        "ok": True,
        "apply_via": "incremental",
        "remote_catalog_url": remote_catalog_url,
        "paths": paths,
        **diff,
    }


def apply_incremental(
    *,
    install_root: Path | None = None,
    source_root: Path,
    paths: list[str],
    remove_paths: list[str] | None = None,
) -> dict[str, Any]:
    root = install_root or INSTALL
    applied: list[str] = []
    missing: list[str] = []
    for rel in paths:
        src = source_root / rel
        dst = root / rel
        if not src.is_file():
            missing.append(rel)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        applied.append(rel)
    removed: list[str] = []
    for rel in remove_paths or []:
        dst = root / rel
        if dst.is_file():
            dst.unlink()
            removed.append(rel)
    return {
        "ok": len(missing) == 0,
        "applied": applied,
        "applied_count": len(applied),
        "missing": missing,
        "removed": removed,
        "install_root": str(root),
        "source_root": str(source_root),
    }


def apply_from_tarball(
    *,
    install_root: Path | None = None,
    tarball_url: str,
    target_version: str,
    remote_catalog_url: str,
    local_catalog_path: Path | None = None,
) -> dict[str, Any]:
    plan = plan_update(
        install_root=install_root,
        remote_catalog_url=remote_catalog_url,
        local_catalog_path=local_catalog_path,
    )
    if not plan.get("ok"):
        return plan
    paths = plan.get("paths") or []
    if not paths:
        return {"ok": True, "already_current": True, "applied_count": 0, "message": "catalog matches remote"}
    with tempfile.TemporaryDirectory(prefix="nexus-inc-", dir=str(STATE)) as tmp:
        archive = Path(tmp) / "release.tar.gz"
        try:
            _download(tarball_url, archive)
        except (urllib.error.URLError, OSError) as exc:
            return {"ok": False, "error": "tarball_download_failed", "detail": str(exc)}
        extract_base = Path(tmp) / "extract"
        extract_base.mkdir(parents=True, exist_ok=True)
        with tarfile.open(archive, "r:gz") as tf:
            tf.extractall(extract_base)
        source_root = _find_extract_root(extract_base, target_version)
        if not source_root:
            return {"ok": False, "error": "extract_root_missing"}
        result = apply_incremental(
            install_root=install_root,
            source_root=source_root,
            paths=paths,
            remove_paths=plan.get("removed") or [],
        )
        result["plan"] = {
            "changed_count": plan.get("changed_count"),
            "added_count": plan.get("added_count"),
            "remote_version": plan.get("remote_version"),
            "local_version": plan.get("local_version"),
        }
        return result


def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "usage: nexus-incremental-update.py [plan|apply] ..."}, ensure_ascii=False))
        return 1
    cmd = sys.argv[1]
    if cmd == "plan":
        url = os.environ.get("NEXUS_UPDATE_CATALOG_URL") or (sys.argv[2] if len(sys.argv) > 2 else "")
        if not url:
            print(json.dumps({"ok": False, "error": "missing_catalog_url"}, ensure_ascii=False))
            return 1
        print(json.dumps(plan_update(remote_catalog_url=url), ensure_ascii=False, indent=2))
        return 0
    if cmd == "apply":
        url = os.environ.get("NEXUS_UPDATE_CATALOG_URL", "")
        tarball = os.environ.get("NEXUS_UPDATE_TARBALL_URL", "")
        target = os.environ.get("NEXUS_UPDATE_TARGET", "")
        if not url or not tarball or not target:
            print(json.dumps({"ok": False, "error": "missing_env"}, ensure_ascii=False))
            return 1
        print(json.dumps(
            apply_from_tarball(
                tarball_url=tarball,
                target_version=target,
                remote_catalog_url=url,
            ),
            ensure_ascii=False,
            indent=2,
        ))
        return 0
    print(json.dumps({"error": "unknown_command"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())