#!/usr/bin/env pythong
"""AmmoOS Software Update Manager — GitHub tracking, safe in-place updates."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parent.parent))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE_PATH = INSTALL / "data" / "ammoos-update-doctrine.json"
CACHE = STATE / "ammoos-update-check.json"
SCHEMA = "ammoos-update/v1"
CACHE_TTL = int(os.environ.get("AMMOOS_UPDATE_CACHE_TTL", "3600"))
PRIMARY_REPO = os.environ.get("AMMOOS_GITHUB_REPO", "ZacharyGeurts/AmmoOS")
UPDATE_MODE = os.environ.get("AMMOOS_UPDATE_MODE", os.environ.get("NEXUS_UPDATE_MODE", "git_tree")).strip().lower() or "git_tree"


def _now() -> str:
    try:
        import importlib.util

        p = Path(__file__).resolve().parent / "sovereign-clock.py"
        spec = importlib.util.spec_from_file_location("sovereign_clock", p)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.utc_z()
    except Exception:
        pass
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write_json_atomic(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def load_doctrine() -> dict[str, Any]:
    doc = _read_json(DOCTRINE_PATH, {})
    if not doc:
        doc = {
            "schema": "ammoos-update-doctrine/v1",
            "primary_repo": {"github": PRIMARY_REPO},
            "getting_started": "Clone AmmoOS from GitHub and run install-all.sh.",
        }
    return doc


def _parse_version(text: str) -> tuple[int, ...]:
    m = re.search(r"(\d+(?:\.\d+)*)", text or "")
    if not m:
        return (0,)
    parts: list[int] = []
    for seg in m.group(1).split("."):
        try:
            parts.append(int(re.match(r"^\d+", seg).group(0)))  # type: ignore[union-attr]
        except (ValueError, AttributeError):
            parts.append(0)
    return tuple(parts) if parts else (0,)


def _sg_root() -> Path:
    env = os.environ.get("SG_ROOT", "").strip()
    if env:
        return Path(env)
    if (INSTALL.parent / "NewLatest").is_dir():
        return INSTALL.parent
    return INSTALL.parent


def resolve_source_root() -> Path:
    """Git/install tree used for in-place updates."""
    candidates = [
        INSTALL,
        INSTALL.parent,
        _sg_root() / "NewLatest",
        _sg_root(),
    ]
    seen: set[str] = set()
    for base in candidates:
        s = str(base.resolve())
        if s in seen:
            continue
        seen.add(s)
        if (base / "data" / "ammoos-version.json").is_file():
            if (base / "nexus.sh").is_file() or (base / "install-all.sh").is_file():
                return base.resolve()
        if (base / ".git").is_dir() and (base / "install-all.sh").is_file():
            return base.resolve()
        if (base / ".git").is_dir() and (base / "nexus.sh").is_file():
            return base.resolve()
    return INSTALL.resolve()


def _read_local_version(root: Path | None = None) -> str:
    base = root or INSTALL
    ver_doc = base / "data" / "ammoos-version.json"
    if ver_doc.is_file():
        doc = _read_json(ver_doc, {})
        if doc.get("version"):
            return str(doc["version"])
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("nexus_version", base / "lib" / "nexus_version.py")
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.read_version(str(base))
    except Exception:
        pass
    return os.environ.get("NEXUS_VERSION", "unknown")


def _github_transport():
    try:
        import importlib.util

        path = INSTALL / "lib" / "field-github-mcp-transport.py"
        if not path.is_file():
            return None
        spec = importlib.util.spec_from_file_location("github_mcp_transport", path)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _fetch_json(url: str, timeout: int = 12) -> dict[str, Any] | list[Any] | None:
    m = re.search(r"https://api\.github\.com/repos/([^/]+/[^/]+)/(.+)", url)
    transport = _github_transport()
    if m and transport and transport.resolve_transport() != "tcp":
        repo, tail = m.group(1), m.group(2)
        if tail == "releases/latest":
            out = transport.repo_latest_release(repo)
            if out.get("ok"):
                return {
                    "tag_name": out.get("tag_name"),
                    "html_url": out.get("release_url"),
                    "body": out.get("release_notes"),
                    "published_at": out.get("published_at"),
                }
        api = transport.gh_api(f"repos/{repo}/{tail}")
        if api.get("ok"):
            return api.get("data")
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "AmmoOS-Update-Manager",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError, OSError):
        return None


def _fetch_text(url: str, timeout: int = 12) -> str:
    m = re.search(r"https://raw\.githubusercontent\.com/([^/]+/[^/]+)/([^/]+)/(.+)", url)
    transport = _github_transport()
    if m and transport and transport.resolve_transport() != "tcp":
        out = transport.repo_file_text(m.group(1), m.group(3), ref=m.group(2))
        if out.get("ok"):
            return str(out.get("text") or "")
    req = urllib.request.Request(url, headers={"User-Agent": "AmmoOS-Update-Manager"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError):
        return ""


def _installer_assets(version: str, tag_name: str, release: dict[str, Any] | None, repo: str) -> dict[str, str]:
    ver = version.lstrip("v")
    tag = tag_name if tag_name.startswith("v") else f"v{ver}"
    doctrine = load_doctrine()
    primary = doctrine.get("primary_repo") or {}
    source_name = str(
        primary.get("release_archive")
        or primary.get("release_tarball")
        or "ammoos-{version}-source.h7e"
    ).format(version=ver)
    inst_name = str(primary.get("installers_tarball") or "ammoos-{version}-installers.tar.gz").format(version=ver)
    base = f"https://github.com/{repo}/releases/download/{tag}"
    source_url = f"{base}/{source_name}"
    installers_url = f"{base}/{inst_name}"
    if isinstance(release, dict):
        for row in release.get("assets") or []:
            if not isinstance(row, dict):
                continue
            name = str(row.get("name") or "")
            url = str(row.get("browser_download_url") or "")
            if name == source_name and url:
                source_url = url
            if name == inst_name and url:
                installers_url = url
    return {
        "source_tarball": source_url,
        "installers_tarball": installers_url,
        "source_tarball_name": source_name,
        "installers_tarball_name": inst_name,
    }


def _github_latest(repo: str) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    latest_release: dict[str, Any] | None = None

    rel = _fetch_json(f"https://api.github.com/repos/{repo}/releases/latest")
    if isinstance(rel, dict) and rel.get("tag_name"):
        latest_release = rel
        ver = str(rel.get("tag_name", "")).lstrip("v")
        tag_name = str(rel.get("tag_name") or f"v{ver}")
        row = {
            "latest": ver,
            "tag_name": tag_name,
            "release_url": rel.get("html_url") or f"https://github.com/{repo}/releases/latest",
            "release_notes": (rel.get("body") or "").strip()[:2000],
            "published_at": rel.get("published_at"),
            "source": "releases/latest",
        }
        row.update(_installer_assets(ver, tag_name, rel, repo))
        candidates.append(row)

    tags = _fetch_json(f"https://api.github.com/repos/{repo}/tags?per_page=12")
    if isinstance(tags, list):
        for row in tags:
            tag_name = str(row.get("name") or "")
            ver = tag_name.lstrip("v")
            if ver and re.match(r"^\d+\.\d+", ver):
                item = {
                    "latest": ver,
                    "tag_name": tag_name,
                    "release_url": f"https://github.com/{repo}/releases/tag/{tag_name}",
                    "release_notes": "",
                    "published_at": None,
                    "source": "tags",
                }
                item.update(_installer_assets(ver, tag_name, None, repo))
                candidates.append(item)
                break

    for branch, path in (("main", "data/ammoos-version.json"), ("main", "lib/nexus-common.sh")):
        text = _fetch_text(f"https://raw.githubusercontent.com/{repo}/{branch}/{path}")
        if not text:
            continue
        ver = None
        if path.endswith(".json"):
            try:
                ver = json.loads(text).get("version")
            except json.JSONDecodeError:
                ver = None
        else:
            m = re.search(r'NEXUS_VERSION="([^"]+)"', text)
            ver = m.group(1) if m else None
        if ver:
            candidates.append({
                "latest": str(ver),
                "tag_name": f"v{ver}",
                "release_url": f"https://github.com/{repo}",
                "release_notes": "",
                "published_at": None,
                "source": f"{branch}/{path}",
            })
            break

    if not candidates:
        return {
            "latest": None,
            "release_url": f"https://github.com/{repo}/releases/latest",
            "release_notes": "",
            "source": "none",
        }

    best = max(candidates, key=lambda c: _parse_version(str(c.get("latest") or "0")))
    out = dict(best)
    if latest_release and not out.get("source_tarball"):
        out.update(_installer_assets(str(out["latest"]), str(out.get("tag_name") or ""), latest_release, repo))
    elif not out.get("source_tarball"):
        out.update(_installer_assets(str(out["latest"]), str(out.get("tag_name") or ""), None, repo))
    return out


def _lock_status() -> dict[str, Any]:
    lock_py = INSTALL / "lib" / "nexus-update-lock.py"
    if not lock_py.is_file():
        return {"locked": False}
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


def _resolve_local_repo_path(spec: dict[str, Any]) -> Path | None:
    sg = _sg_root()
    paths = list(spec.get("local_paths") or [])
    if spec.get("id") == "ammoos":
        paths = [".", "NewLatest"]
    for rel in paths:
        for base in (INSTALL, sg, INSTALL.parent):
            p = (base / rel).resolve()
            if p.is_dir() and ((p / ".git").is_dir() or spec.get("bundled")):
                return p
    return None


def check_component(spec: dict[str, Any], *, force: bool = False) -> dict[str, Any]:
    repo = str(spec.get("github") or "")
    comp_id = str(spec.get("id") or repo)
    local_path = _resolve_local_repo_path(spec)
    local_version = _read_local_version(local_path) if local_path and comp_id == "ammoos" else None
    if local_path and comp_id != "ammoos":
        local_version = local_version or "bundled"
    if not local_path and spec.get("optional"):
        return {
            "id": comp_id,
            "name": spec.get("name") or comp_id,
            "github": repo,
            "present": False,
            "optional": True,
            "status": "not_installed",
        }
    gh = _github_latest(repo) if repo else {}
    remote = gh.get("latest")
    cur = local_version or _read_local_version()
    update_available = bool(remote and _parse_version(str(remote)) > _parse_version(str(cur)))
    return {
        "id": comp_id,
        "name": spec.get("name") or comp_id,
        "github": repo,
        "present": bool(local_path),
        "local_path": str(local_path) if local_path else None,
        "local_version": cur,
        "remote_version": remote,
        "update_available": update_available,
        "release_url": gh.get("release_url"),
        "optional": bool(spec.get("optional")),
        "legacy": bool(spec.get("legacy")),
        "status": "update_available" if update_available else ("current" if remote else "unknown"),
    }


def check_components(*, force: bool = False) -> list[dict[str, Any]]:
    doctrine = load_doctrine()
    rows = [check_component({"id": "ammoos", **(doctrine.get("primary_repo") or {})}, force=force)]
    for spec in doctrine.get("stack_repos") or []:
        if isinstance(spec, dict):
            rows.append(check_component(spec, force=force))
    return rows


def preflight(*, target: str = "", previous: str = "") -> dict[str, Any]:
    doctrine = load_doctrine()
    safety = doctrine.get("safety") or {}
    pre = safety.get("preflight") or {}
    issues: list[dict[str, str]] = []
    ok = True

    lock = _lock_status()
    if lock.get("locked"):
        ok = False
        issues.append({"kind": "lock", "message": lock.get("message") or "Update already in progress"})

    root = resolve_source_root()
    free_mb = shutil.disk_usage(root).free // (1024 * 1024)
    min_mb = int(pre.get("disk_free_mb_min") or 512)
    if free_mb < min_mb:
        ok = False
        issues.append({"kind": "disk", "message": f"Low disk space: {free_mb} MB free (need {min_mb} MB)"})

    if pre.get("block_dirty_git") and (root / ".git").is_dir():
        proc = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if (proc.stdout or "").strip():
            ok = False
            issues.append({"kind": "git", "message": "Git working tree has uncommitted changes"})

    if not (root / "nexus.sh").is_file() and not (root / "install-all.sh").is_file():
        ok = False
        issues.append({"kind": "tree", "message": f"Invalid source tree: {root}"})

    apply_sh = INSTALL / "lib" / "nexus-update-apply.sh"
    if not apply_sh.is_file():
        ok = False
        issues.append({"kind": "apply", "message": "nexus-update-apply.sh missing"})

    return {
        "ok": ok,
        "schema": SCHEMA,
        "preflight_ok": ok,
        "issues": issues,
        "source_root": str(root),
        "disk_free_mb": free_mb,
        "target": target,
        "previous": previous,
        "never_harm_os": pre.get("never_harm_os", True),
        "checked_at": _now(),
    }


def check_update(*, force: bool = False) -> dict[str, Any]:
    current = _read_local_version()
    if CACHE.is_file() and not force:
        try:
            cached = json.loads(CACHE.read_text(encoding="utf-8"))
            age = time.time() - float(cached.get("cached_epoch") or 0)
            if age < CACHE_TTL and cached.get("current") == current and cached.get("schema") == SCHEMA:
                lock = _lock_status()
                cached["update_lock"] = lock
                cached["update_in_progress"] = bool(lock.get("locked"))
                if lock.get("locked"):
                    cached["update_available"] = False
                    cached["label"] = lock.get("message") or "Update in progress"
                return cached
        except (OSError, json.JSONDecodeError, ValueError):
            pass

    doctrine = load_doctrine()
    repo = str((doctrine.get("primary_repo") or {}).get("github") or PRIMARY_REPO)
    gh = _github_latest(repo)
    latest = gh.get("latest") or current
    cur_t = _parse_version(current)
    lat_t = _parse_version(str(latest))
    update_available = lat_t > cur_t
    mode = UPDATE_MODE
    if os.environ.get("NEXUS_FIELD_STANDALONE", "0") == "1" and (INSTALL / ".git").is_dir():
        mode = os.environ.get("AMMOOS_UPDATE_MODE", "git_tree")

    doc: dict[str, Any] = {
        "ok": True,
        "schema": SCHEMA,
        "product": "AmmoOS",
        "current": current,
        "previous": current,
        "latest": latest,
        "update_available": update_available,
        "update_mode": mode,
        "apply_via": "git_tree" if mode != "release" else "release_tarball",
        "release_url": gh.get("release_url"),
        "release_notes": gh.get("release_notes") or "",
        "published_at": gh.get("published_at"),
        "github_repo": repo,
        "source": gh.get("source"),
        "tag_name": gh.get("tag_name"),
        "source_tarball": gh.get("source_tarball"),
        "installers_tarball": gh.get("installers_tarball"),
        "source_tarball_name": gh.get("source_tarball_name"),
        "install_script": (doctrine.get("primary_repo") or {}).get("install_script") or "install-all.sh",
        "source_root": str(resolve_source_root()),
        "components": check_components(force=force),
        "preflight": preflight(target=str(latest), previous=current),
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

    _write_json_atomic(CACHE, doc)
    marker = STATE / "update-previous-version.json"
    if update_available and not marker.is_file():
        _write_json_atomic(marker, {"previous": current, "recorded_at": _now()})

    return doc


def post_update_hooks() -> dict[str, Any]:
    results: dict[str, Any] = {"ok": True, "steps": []}
    host_py = INSTALL / "lib" / "nexus-host-desktop-install.py"
    if host_py.is_file():
        proc = subprocess.run(
            [sys.executable, str(host_py), "run"],
            capture_output=True,
            text=True,
            timeout=120,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
        )
        results["steps"].append({"id": "host_desktop", "ok": proc.returncode == 0})
    vest_py = INSTALL / "lib" / "nexus-vestigial-cleanup.py"
    if vest_py.is_file():
        proc = subprocess.run(
            [sys.executable, str(vest_py), "run"],
            capture_output=True,
            text=True,
            timeout=60,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
        )
        results["steps"].append({"id": "vestigial_cleanup", "ok": proc.returncode == 0})
    return results


def tail_log(lines: int = 80) -> dict[str, Any]:
    log_path = STATE / "update-apply.log"
    if not log_path.is_file():
        return {"ok": True, "lines": [], "path": str(log_path)}
    try:
        text = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        return {"ok": True, "path": str(log_path), "lines": text[-max(1, lines) :]}
    except OSError as exc:
        return {"ok": False, "error": str(exc)}


def doctrine_payload() -> dict[str, Any]:
    doc = load_doctrine()
    doc["ok"] = True
    doc["schema"] = doc.get("schema") or "ammoos-update-doctrine/v1"
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "check").strip().lower()
    force = "--force" in sys.argv

    if cmd in ("check", "status", "json"):
        print(json.dumps(check_update(force=force), ensure_ascii=False, indent=2))
        return 0
    if cmd == "doctrine":
        print(json.dumps(doctrine_payload(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "source-root":
        root = resolve_source_root()
        print(json.dumps({"ok": True, "source_root": str(root), "install_root": str(INSTALL)}, ensure_ascii=False, indent=2))
        return 0
    if cmd == "components":
        print(json.dumps({"ok": True, "components": check_components(force=force)}, ensure_ascii=False, indent=2))
        return 0
    if cmd == "preflight":
        upd = check_update(force=force)
        pf = preflight(target=str(upd.get("latest") or ""), previous=str(upd.get("current") or ""))
        print(json.dumps(pf, ensure_ascii=False, indent=2))
        return 0
    if cmd == "post-update":
        print(json.dumps(post_update_hooks(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "log":
        n = 80
        for arg in sys.argv[2:]:
            if arg.startswith("--lines="):
                n = int(arg.split("=", 1)[1])
        print(json.dumps(tail_log(n), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "error": "usage",
        "cmds": ["check", "doctrine", "source-root", "components", "preflight", "post-update", "log"],
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())