#!/usr/bin/env pythong
"""NXF — NEXUS eXchange Field manifest (compact install/update descriptor).

Single JSON file (~1KB) shipped with releases or fetched as latest.nxf from GitHub.
Drives nxf-install.sh, nexus-update.py, and Queen browser update button.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "nxf/v1"
REPO = os.environ.get("NEXUS_GITHUB_REPO", "ZacharyGeurts/NEXUS-Shield")
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        import importlib.util
        _p = Path(__file__).resolve().parent / "sovereign-clock.py"
        _s = importlib.util.spec_from_file_location("sovereign_clock", _p)
        if not _s or not _s.loader:
            raise ImportError("sovereign-clock.py missing")
        _SOVEREIGN_CLOCK_MOD = importlib.util.module_from_spec(_s)
        _s.loader.exec_module(_SOVEREIGN_CLOCK_MOD)
    return _SOVEREIGN_CLOCK_MOD.utc_z()


_SOVEREIGN_CLOCK_MOD = None



def _parse_version(text: str) -> tuple[int, ...]:
    m = re.search(r"(\d+(?:\.\d+)*)", text or "")
    if not m:
        return (0,)
    return tuple(int(x) for x in m.group(1).split("."))


def _read_local_version() -> str:
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("nexus_version", INSTALL / "lib" / "nexus_version.py")
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.read_version(str(INSTALL))
    except Exception:
        pass
    common = INSTALL / "lib" / "nexus-common.sh"
    if common.is_file():
        m = re.search(r'NEXUS_VERSION="([^"]+)"', common.read_text(encoding="utf-8", errors="replace"))
        if m:
            return m.group(1)
    return os.environ.get("NEXUS_VERSION", "unknown")


def _fetch_text(url: str, timeout: int = 14) -> str | None:
    req = urllib.request.Request(url, headers={"User-Agent": "NEXUS-Shield-NXF"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
        return None


def _fetch_json(url: str, timeout: int = 14) -> dict[str, Any] | list[Any] | None:
    text = _fetch_text(url, timeout=timeout)
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _validate(doc: dict[str, Any]) -> dict[str, Any]:
    if doc.get("schema") != SCHEMA:
        raise ValueError(f"unsupported schema: {doc.get('schema')}")
    if not doc.get("version"):
        raise ValueError("missing version")
    if not doc.get("repo"):
        doc["repo"] = REPO
    return doc


def pack_urls(doc: dict[str, Any]) -> dict[str, str]:
    pack = doc.get("pack") or {}
    out: dict[str, str] = {}
    for key in ("source", "installers", "nxf"):
        row = pack.get(key) or {}
        if isinstance(row, dict) and row.get("url"):
            out[key] = str(row["url"])
    return out


def from_release(version: str, tag_name: str, release: dict[str, Any] | None = None) -> dict[str, Any]:
    ver = version.lstrip("v")
    tag = tag_name if tag_name.startswith("v") else f"v{ver}"
    base = f"https://github.com/{REPO}/releases/download/{tag}"
    source_name = f"nexus-shield-{ver}-source.tar.gz"
    inst_name = f"nexus-shield-{ver}-installers.tar.gz"
    nxf_name = f"nexus-shield-{ver}.nxf"
    source_url = f"{base}/{source_name}"
    inst_url = f"{base}/{inst_name}"
    nxf_url = f"{base}/{nxf_name}"
    if isinstance(release, dict):
        assets = {str(a.get("name") or ""): str(a.get("browser_download_url") or "") for a in release.get("assets") or []}
        if source_name in assets:
            source_url = assets[source_name]
        if inst_name in assets:
            inst_url = assets[inst_name]
        if nxf_name in assets:
            nxf_url = assets[nxf_name]
    return _validate({
        "schema": SCHEMA,
        "product": "nexus-shield",
        "version": ver,
        "tag": tag,
        "repo": REPO,
        "published_at": release.get("published_at") if isinstance(release, dict) else None,
        "install": {
            "system": "/usr/local/lib/nexus-shield",
            "state": "/var/lib/nexus-shield",
            "portable": "in-tree",
        },
        "pack": {
            "source": {"name": source_name, "url": source_url},
            "installers": {"name": inst_name, "url": inst_url},
            "nxf": {"name": nxf_name, "url": nxf_url},
        },
        "entry": "install-all.sh",
        "portable_entry": "install.sh",
        "launcher": "nexus.sh",
        "queen": {
            "browser": "http://127.0.0.1:9481/world/browser.html",
            "panel": 9477,
            "world": 9481,
        },
        "channels": ["release", "portable", "github"],
        "catalog": {
            "name": f"nexus-file-catalog-{ver}.json",
            "url": f"{base}/nexus-file-catalog-{ver}.json",
        },
        "update": {"mode": "release", "lock": "github-update.lock", "incremental": True},
    })


def fetch_github_nxf(version: str | None = None, tag: str | None = None) -> dict[str, Any] | None:
    ver = (version or "").lstrip("v")
    tag_name = tag or (f"v{ver}" if ver else "")
    candidates: list[str] = []
    if ver:
        candidates.append(f"https://github.com/{REPO}/releases/download/{tag_name}/nexus-shield-{ver}.nxf")
    candidates.extend([
        f"https://github.com/{REPO}/releases/latest/download/latest.nxf",
        f"https://raw.githubusercontent.com/{REPO}/main/nxf/latest.nxf",
    ])
    for url in candidates:
        text = _fetch_text(url)
        if not text:
            continue
        try:
            return _validate(json.loads(text))
        except (json.JSONDecodeError, ValueError):
            continue
    return None


def fetch_latest() -> dict[str, Any]:
    """Resolve newest NXF from GitHub releases/latest, tags, or synthesized manifest."""
    candidates: list[dict[str, Any]] = []

    rel = _fetch_json(f"https://api.github.com/repos/{REPO}/releases/latest")
    if isinstance(rel, dict) and rel.get("tag_name"):
        ver = str(rel["tag_name"]).lstrip("v")
        nxf = fetch_github_nxf(ver, str(rel["tag_name"]))
        if nxf:
            candidates.append(nxf)
        else:
            candidates.append(from_release(ver, str(rel["tag_name"]), rel))

    tags = _fetch_json(f"https://api.github.com/repos/{REPO}/tags?per_page=8")
    if isinstance(tags, list):
        for row in tags:
            tag_name = str(row.get("name") or "")
            ver = tag_name.lstrip("v")
            if ver and re.match(r"^\d+\.\d+", ver):
                nxf = fetch_github_nxf(ver, tag_name)
                candidates.append(nxf or from_release(ver, tag_name, None))
                break

    local = INSTALL / "nxf" / "latest.nxf"
    if local.is_file():
        try:
            candidates.append(_validate(json.loads(local.read_text(encoding="utf-8"))))
        except (OSError, json.JSONDecodeError, ValueError):
            pass

    if not candidates:
        return {"ok": False, "error": "no_release", "repo": REPO, "checked_at": _now()}

    best = max(candidates, key=lambda c: _parse_version(str(c.get("version") or "0")))
    urls = pack_urls(best)
    return {
        "ok": True,
        "nxf": best,
        "version": best.get("version"),
        "tag": best.get("tag"),
        "source_tarball": urls.get("source"),
        "installers_tarball": urls.get("installers"),
        "nxf_url": urls.get("nxf"),
        "entry": best.get("entry") or "install-all.sh",
        "launcher": best.get("launcher") or "nexus.sh",
        "repo": best.get("repo") or REPO,
        "checked_at": _now(),
    }


def check_update(force: bool = False) -> dict[str, Any]:
    cache = STATE / "nxf-update-check.json"
    current = _read_local_version()
    if cache.is_file() and not force:
        try:
            cached = json.loads(cache.read_text(encoding="utf-8"))
            age = time.time() - float(cached.get("cached_epoch") or 0)
            if age < int(os.environ.get("NEXUS_UPDATE_CACHE_TTL", "3600")) and cached.get("current") == current:
                return cached
        except (OSError, json.JSONDecodeError, ValueError):
            pass

    latest_doc = fetch_latest()
    if not latest_doc.get("ok"):
        return {**latest_doc, "current": current, "update_available": False}

    latest = str(latest_doc.get("version") or current)
    update_available = _parse_version(latest) > _parse_version(current)
    nxf = latest_doc.get("nxf") or {}
    out: dict[str, Any] = {
        "ok": True,
        "schema": SCHEMA,
        "current": current,
        "previous": current,
        "latest": latest,
        "update_available": update_available,
        "update_mode": "release",
        "apply_via": "nxf_release",
        "source_tarball": latest_doc.get("source_tarball"),
        "installers_tarball": latest_doc.get("installers_tarball"),
        "nxf_url": latest_doc.get("nxf_url"),
        "install_script": nxf.get("entry") or "install-all.sh",
        "install_command": (
            f"curl -fsSL https://raw.githubusercontent.com/{REPO}/main/install-remote.sh | bash"
        ),
        "release_url": f"https://github.com/{REPO}/releases/tag/{nxf.get('tag') or f'v{latest}'}",
        "github_repo": REPO,
        "tag_name": nxf.get("tag") or f"v{latest}",
        "queen_browser": (nxf.get("queen") or {}).get("browser"),
        "tristate_installer_url": os.environ.get(
            "NEXUS_TRISTATE_INSTALLER_URL",
            "http://127.0.0.1:9477/underlay-f9?sector=underlay",
        ),
        "checked_at": _now(),
        "cached_epoch": time.time(),
    }
    catalog = nxf.get("catalog") or {}
    catalog_url = str(catalog.get("url") or "")
    if update_available:
        out["previous"] = current
        out["label"] = f"{current} → {latest}"
        if catalog_url and nxf.get("update", {}).get("incremental"):
            out["apply_via"] = "incremental"
            out["catalog_url"] = catalog_url
            out["catalog_name"] = catalog.get("name")
    else:
        out["label"] = f"v{current}"

    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        tmp = cache.with_suffix(".tmp")
        tmp.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(cache)
    except OSError:
        pass
    return out


def load_file(path: Path) -> dict[str, Any]:
    return _validate(json.loads(path.read_text(encoding="utf-8")))


def write_manifest(path: Path, *, version: str | None = None, install_root: Path | None = None) -> dict[str, Any]:
    root = install_root or INSTALL
    ver = version or _read_local_version()
    tag = f"v{ver.lstrip('v')}"
    doc = from_release(ver.lstrip("v"), tag, None)
    doc["generated_at"] = _now()
    doc["install"]["portable"] = str(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    return doc


def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps(check_update(), ensure_ascii=False))
        return 0
    cmd = sys.argv[1]
    if cmd == "check":
        force = "--force" in sys.argv
        print(json.dumps(check_update(force=force), ensure_ascii=False))
        return 0
    if cmd == "latest":
        print(json.dumps(fetch_latest(), ensure_ascii=False))
        return 0
    if cmd == "read" and len(sys.argv) > 2:
        print(json.dumps(load_file(Path(sys.argv[2])), ensure_ascii=False))
        return 0
    if cmd == "write" and len(sys.argv) > 2:
        doc = write_manifest(Path(sys.argv[2]))
        print(json.dumps({"ok": True, "path": sys.argv[2], "version": doc.get("version")}, ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: nxf.py [check|latest|read PATH|write PATH]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())