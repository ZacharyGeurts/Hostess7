#!/usr/bin/env pythong
"""NEXUS update checker — live GitHub release/tag compare (no stubs)."""
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

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
CACHE = STATE / "update-check.json"
REPO = os.environ.get("NEXUS_GITHUB_REPO", "ZacharyGeurts/NEXUS-Shield")
CACHE_TTL_SEC = int(os.environ.get("NEXUS_UPDATE_CACHE_TTL", "3600"))
UPDATE_MODE = os.environ.get("NEXUS_UPDATE_MODE", "release").strip().lower() or "release"
TRISTATE_URL = os.environ.get(
    "NEXUS_TRISTATE_INSTALLER_URL",
    "http://127.0.0.1:9477/underlay-f9?sector=underlay",
)


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
    return os.environ.get("NEXUS_VERSION", "unknown")


def _fetch_json(url: str, timeout: int = 12) -> dict[str, Any] | list[Any] | None:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "NEXUS-Shield-Update-Checker",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError, OSError):
        return None


def _installer_assets(version: str, tag_name: str, release: dict[str, Any] | None = None) -> dict[str, Any]:
    """Resolve release tarball URLs — same path as Tristate install-all.sh."""
    ver = version.lstrip("v")
    tag = tag_name if tag_name.startswith("v") else f"v{ver}"
    source_name = f"nexus-shield-{ver}-source.tar.gz"
    inst_name = f"nexus-shield-{ver}-installers.tar.gz"
    base = f"https://github.com/{REPO}/releases/download/{tag}"
    source_url = f"{base}/{source_name}"
    installers_url = f"{base}/{inst_name}"
    assets: dict[str, str] = {}
    if isinstance(release, dict):
        for row in release.get("assets") or []:
            if not isinstance(row, dict):
                continue
            name = str(row.get("name") or "")
            url = str(row.get("browser_download_url") or "")
            if name and url:
                assets[name] = url
        if source_name in assets:
            source_url = assets[source_name]
        if inst_name in assets:
            installers_url = assets[inst_name]
    return {
        "source_tarball": source_url,
        "installers_tarball": installers_url,
        "source_tarball_name": source_name,
        "installers_tarball_name": inst_name,
        "install_script": "install-all.sh",
        "install_command": f"tar -xzf {source_name} && cd nexus-shield-{ver} && sudo ./install-all.sh",
        "tristate_installer_url": TRISTATE_URL,
    }


def _github_latest() -> dict[str, Any]:
    """Pick highest version across releases/latest, tags, and main branch."""
    candidates: list[dict[str, Any]] = []
    latest_release: dict[str, Any] | None = None

    rel = _fetch_json(f"https://api.github.com/repos/{REPO}/releases/latest")
    if isinstance(rel, dict) and rel.get("tag_name"):
        latest_release = rel
        ver = str(rel.get("tag_name", "")).lstrip("v")
        tag_name = str(rel.get("tag_name") or f"v{ver}")
        row = {
            "latest": ver,
            "tag_name": tag_name,
            "release_url": rel.get("html_url") or f"https://github.com/{REPO}/releases/latest",
            "release_notes": (rel.get("body") or "").strip()[:1200],
            "published_at": rel.get("published_at"),
            "source": "releases/latest",
        }
        row.update(_installer_assets(ver, tag_name, rel))
        candidates.append(row)

    tags = _fetch_json(f"https://api.github.com/repos/{REPO}/tags?per_page=12")
    if isinstance(tags, list):
        for row in tags:
            tag_name = str(row.get("name") or "")
            ver = tag_name.lstrip("v")
            if ver and re.match(r"^\d+\.\d+", ver):
                row = {
                    "latest": ver,
                    "tag_name": tag_name,
                    "release_url": f"https://github.com/{REPO}/releases/tag/{tag_name}",
                    "release_notes": "",
                    "published_at": None,
                    "source": "tags",
                }
                row.update(_installer_assets(ver, tag_name, None))
                candidates.append(row)
                break

    text = ""
    try:
        with urllib.request.urlopen(
            urllib.request.Request(
                f"https://raw.githubusercontent.com/{REPO}/main/lib/nexus-common.sh",
                headers={"User-Agent": "NEXUS-Shield-Update-Checker"},
            ),
            timeout=10,
        ) as resp:
            text = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError):
        text = ""
    if text:
        m = re.search(r'NEXUS_VERSION="([^"]+)"', text)
        if m:
            candidates.append({
                "latest": m.group(1),
                "release_url": f"https://github.com/{REPO}",
                "release_notes": "",
                "published_at": None,
                "source": "main/nexus-common.sh",
            })

    if not candidates:
        return {
            "latest": None,
            "release_url": f"https://github.com/{REPO}/releases/latest",
            "release_notes": "",
            "published_at": None,
            "source": "none",
        }

    best = max(candidates, key=lambda c: _parse_version(str(c.get("latest") or "0")))
    out = {
        "latest": best["latest"],
        "tag_name": best.get("tag_name") or f"v{best['latest']}",
        "release_url": best["release_url"],
        "release_notes": best.get("release_notes") or "",
        "published_at": best.get("published_at"),
        "source": best["source"],
    }
    if best.get("source_tarball"):
        out.update({
            "source_tarball": best["source_tarball"],
            "installers_tarball": best.get("installers_tarball"),
            "source_tarball_name": best.get("source_tarball_name"),
            "installers_tarball_name": best.get("installers_tarball_name"),
            "install_script": best.get("install_script") or "install-all.sh",
            "install_command": best.get("install_command"),
            "tristate_installer_url": best.get("tristate_installer_url") or TRISTATE_URL,
        })
    elif latest_release and best.get("source") == "releases/latest":
        out.update(_installer_assets(str(best["latest"]), str(out["tag_name"]), latest_release))
    else:
        ver = str(best["latest"])
        out.update(_installer_assets(ver, str(out["tag_name"]), None))
    return out


def _lock_status() -> dict[str, Any]:
    lock_py = INSTALL / "lib" / "nexus-update-lock.py"
    if not lock_py.is_file():
        return {"locked": False}
    import subprocess
    proc = subprocess.run(
        [sys.executable, str(lock_py), "status"],
        capture_output=True,
        text=True,
        timeout=10,
        env={**os.environ, "NEXUS_STATE_DIR": str(STATE), "NEXUS_INSTALL_ROOT": str(INSTALL)},
    )
    try:
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {"locked": False}


def _nxf_check(force: bool = False) -> dict[str, Any] | None:
    nxf_py = INSTALL / "lib" / "nxf.py"
    if not nxf_py.is_file():
        return None
    import subprocess

    args = [sys.executable, str(nxf_py), "check"]
    if force:
        args.append("--force")
    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=20,
            env={**os.environ, "NEXUS_STATE_DIR": str(STATE), "NEXUS_INSTALL_ROOT": str(INSTALL)},
        )
        doc = json.loads(proc.stdout or "{}")
        return doc if doc.get("ok") else None
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        return None


def check_update(force: bool = False) -> dict[str, Any]:
    current = _read_local_version()
    cached: dict[str, Any] | None = None
    if CACHE.is_file() and not force:
        try:
            cached = json.loads(CACHE.read_text(encoding="utf-8"))
            age = time.time() - float(cached.get("cached_epoch") or 0)
            if age < CACHE_TTL_SEC and cached.get("current") == current:
                return cached
        except (OSError, json.JSONDecodeError, ValueError):
            cached = None

    nxf = _nxf_check(force=force)
    if nxf and nxf.get("latest"):
        lock = _lock_status()
        nxf["update_lock"] = lock
        nxf["update_in_progress"] = bool(lock.get("locked"))
        if lock.get("locked"):
            nxf["update_available"] = False
            nxf["label"] = lock.get("message") or "Update in progress"
        elif nxf.get("update_available") and nxf.get("catalog_url"):
            nxf["apply_via"] = "incremental"
        try:
            CACHE.parent.mkdir(parents=True, exist_ok=True)
            tmp = CACHE.with_suffix(".tmp")
            tmp.write_text(json.dumps(nxf, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            tmp.replace(CACHE)
        except OSError:
            pass
        return nxf

    gh = _github_latest()
    latest = gh.get("latest") or current
    cur_t = _parse_version(current)
    lat_t = _parse_version(str(latest))
    update_available = lat_t > cur_t
    doc: dict[str, Any] = {
        "ok": True,
        "current": current,
        "previous": current,
        "latest": latest,
        "update_available": update_available,
        "update_mode": UPDATE_MODE,
        "release_url": gh.get("release_url"),
        "release_notes": gh.get("release_notes") or "",
        "published_at": gh.get("published_at"),
        "github_repo": REPO,
        "source": gh.get("source"),
        "tag_name": gh.get("tag_name"),
        "source_tarball": gh.get("source_tarball"),
        "installers_tarball": gh.get("installers_tarball"),
        "install_script": gh.get("install_script") or "install-all.sh",
        "install_command": gh.get("install_command"),
        "tristate_installer_url": gh.get("tristate_installer_url") or TRISTATE_URL,
        "apply_via": "release_tarball" if UPDATE_MODE == "release" else "git_tree",
        "checked_at": _now(),
        "cached_epoch": time.time(),
    }
    if update_available:
        doc["previous"] = current
        doc["label"] = f"{current} → {latest}"
    else:
        doc["label"] = f"v{current}"

    lock = _lock_status()
    doc["update_lock"] = lock
    doc["update_in_progress"] = bool(lock.get("locked"))
    if lock.get("locked"):
        doc["update_available"] = False
        doc["label"] = lock.get("message") or "Update in progress"

    try:
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        tmp = CACHE.with_suffix(".tmp")
        tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(CACHE)
    except OSError:
        pass
    return doc


def main() -> int:
    force = "--force" in sys.argv
    doc = check_update(force=force)
    print(json.dumps(doc, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())