#!/usr/bin/env python3
"""AmmoOS GitHub incorporate — pull best upstream, merge with local canonical, publish-ready posture."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "ammoos-incorporate-doctrine.json"
PANEL = STATE / "ammoos-incorporate-panel.json"
PRIMARY = os.environ.get("AMMOOS_GITHUB_REPO", "ZacharyGeurts/AmmoOS")
HOSTESS7 = os.environ.get("HOSTESS7_GITHUB_REPO", "ZacharyGeurts/Hostess7")

# Upstream paths we always prefer when local lacks them (WATCHGUARD / beta4+ gifts).
UPSTREAM_ONLY = [
    "lib/field-root-status.py",
    "lib/field-watch-dhcp.py",
    "panel/field-root-status.html",
    "panel/field-watch-dhcp.html",
    "panel/assets/field-root-status.js",
    "panel/assets/field-root-status.css",
    "panel/assets/field-watch-dhcp.js",
    "panel/assets/field-watch-dhcp.css",
    "scripts/field-root-status.sh",
    "scripts/field-watch-dhcp.sh",
    "scripts/fix-dns-dhcp-everywhere.sh",
    "scripts/truth-dns-serve.sh",
    "panel/assets/big-grin-pwnership/hero.jpg",
    "panel/assets/big-grin-pwnership/look-pwnership-badge.jpg",
    "wiki/H7-Updater.md",
]

# Local canonical wins — never overwrite with older AmmoOS publish tree.
LOCAL_CANONICAL = [
    "data/ammoos-version.json",
    "data/field-stack-boot-doctrine.json",
    "data/field-host-desktop-doctrine.json",
    "data/field-irc-doctrine.json",
    "data/field-battle-stations-doctrine.json",
    "lib/field-stack-boot.py",
    "lib/field-irc.py",
    "lib/field-irc-bsp.py",
    "panel/field-irc-chat-embed.html",
    "panel/assets/field-host-desktop.js",
    "panel/assets/field-gnu-terminal.js",
    "panel/assets/field-gnu-terminal.css",
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


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


def _local_version() -> str:
    doc = _load(INSTALL / "data" / "ammoos-version.json", {})
    return str(doc.get("version") or "unknown")


def _gh_clone(repo: str, dest: Path) -> dict[str, Any]:
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    dest.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        ["gh", "repo", "clone", repo, str(dest), "--", "--depth=1"],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    return {"ok": proc.returncode == 0, "repo": repo, "path": str(dest), "stderr": (proc.stderr or "")[:300]}


def _git_pull_hostess7() -> dict[str, Any]:
    if not (INSTALL / ".git").is_dir():
        return {"ok": False, "skipped": True, "reason": "not_a_git_tree"}
    proc = subprocess.run(
        ["git", "pull", "origin", "main", "--no-rebase"],
        cwd=str(INSTALL),
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    return {
        "ok": proc.returncode == 0,
        "stdout": (proc.stdout or "")[-400:],
        "stderr": (proc.stderr or "")[-400:],
    }


def incorporate_upstream(*, write: bool = True) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    paths = list(dict.fromkeys(UPSTREAM_ONLY + list(doctrine.get("upstream_paths") or [])))
    local_only = set(LOCAL_CANONICAL + list(doctrine.get("local_canonical") or []))

    steps: list[dict[str, Any]] = []
    steps.append({"step": "hostess7_pull", **_git_pull_hostess7()})

    tmp = Path(tempfile.mkdtemp(prefix="ammoos-incorp-"))
    clone = _gh_clone(PRIMARY, tmp / "AmmoOS")
    steps.append({"step": "clone_ammoos", **clone})
    merged: list[str] = []
    skipped: list[str] = []
    if clone.get("ok"):
        src_root = tmp / "AmmoOS"
        for rel in paths:
            if rel in local_only:
                skipped.append(rel)
                continue
            src = src_root / rel
            dst = INSTALL / rel
            if not src.is_file():
                continue
            if dst.is_file():
                skipped.append(rel)
                continue
            if write:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
            merged.append(rel)

    local_ver = _local_version()
    out = {
        "ok": True,
        "schema": "ammoos-incorporate/v1",
        "updated": _utc(),
        "local_version": local_ver,
        "primary_repo": PRIMARY,
        "hostess7_repo": HOSTESS7,
        "merged_from_upstream": merged,
        "skipped": skipped,
        "local_canonical_count": len(local_only),
        "steps": steps,
        "motto": "Best of GitHub incorporated — local canonical wins on stack, IRC, desktop.",
        "api": "/api/ammoos-incorporate",
    }
    if write:
        _save(PANEL, out)
    shutil.rmtree(tmp, ignore_errors=True)
    return out


def posture() -> dict[str, Any]:
    cached = _load(PANEL, {})
    if cached.get("schema"):
        return cached
    return incorporate_upstream(write=False)


def doctrine_json() -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    if not doc:
        doc = {
            "schema": "ammoos-incorporate-doctrine/v1",
            "upstream_paths": UPSTREAM_ONLY,
            "local_canonical": LOCAL_CANONICAL,
            "primary_repo": PRIMARY,
            "hostess7_repo": HOSTESS7,
        }
    return doc


def apply(body: dict[str, Any] | None = None) -> dict[str, Any]:
    body = body or {}
    if body.get("pull_hostess7", True):
        _git_pull_hostess7()
    return incorporate_upstream(write=bool(body.get("write", True)))


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}, ensure_ascii=False))
            return 1
        action = str(body.get("action") or "apply").strip().lower()
        if action in ("apply", "incorporate", "run"):
            print(json.dumps(apply(body), ensure_ascii=False, indent=2))
            return 0
        if action in ("status", "json", "posture"):
            print(json.dumps(posture(), ensure_ascii=False, indent=2))
            return 0
        if action == "doctrine":
            print(json.dumps(doctrine_json(), ensure_ascii=False, indent=2))
            return 0
        print(json.dumps({"ok": False, "error": "unknown_action"}, ensure_ascii=False))
        return 1
    if cmd in ("apply", "incorporate", "run"):
        print(json.dumps(apply(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "doctrine":
        print(json.dumps(doctrine_json(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps(posture(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())