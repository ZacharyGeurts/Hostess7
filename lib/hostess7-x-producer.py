#!/usr/bin/env python3
"""X Producer — repair profile censorship, flatten intruders, export hardened front page."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "hostess7-x-producer-doctrine.json"
PANEL = STATE / "hostess7-x-producer-panel.json"
DOCS = Path(os.environ.get("HOSTESS7_ROOT", INSTALL / "Hostess7")) / "docs"
DOCS_API = DOCS / "api"
DOCS_DATA = DOCS / "data"
HANDLE = os.environ.get("OPERATOR_X_HANDLE", "ZacharyGeurts")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _run_py(name: str, args: list[str], *, timeout: int = 120) -> dict[str, Any]:
    py = INSTALL / "lib" / name
    if not py.is_file():
        return {"ok": False, "skipped": name}
    import subprocess
    proc = subprocess.run(
        [sys.executable, str(py), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(INSTALL),
        env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
    )
    if not proc.stdout.strip():
        return {"ok": proc.returncode == 0, "stderr": (proc.stderr or "")[:200]}
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"ok": proc.returncode == 0, "raw": proc.stdout[:300]}


def produce(*, export: bool = True) -> dict[str, Any]:
    doc_policy = _load(DOCTRINE, {})
    profile = _run_py("hostess7-x-profile-fix.py", ["repair"], timeout=120)
    sso = _run_py("hostess7-x-sso-fix.py", ["repair"], timeout=45)
    intruders = _run_py("field-attack-kit.py", ["auto-rekill"], timeout=60)

    feed = {
        "schema": "hostess7-x-producer-feed/v1",
        "updated": _now(),
        "operator": HANDLE,
        "tweet_count": (profile.get("censorship") or {}).get("tweet_count_truth"),
        "post_count": profile.get("post_count", 0),
        "posts": profile.get("posts") or [],
        "censorship": profile.get("censorship"),
        "producer_url": doc_policy.get("hosted", {}).get("producer"),
    }

    out: dict[str, Any] = {
        "ok": True,
        "schema": "hostess7-x-producer/v1",
        "updated": _now(),
        "motto": doc_policy.get("motto"),
        "title": doc_policy.get("title"),
        "for_musk": doc_policy.get("for_musk"),
        "operator": HANDLE,
        "producer_mode": "beta",
        "grok_beta": True,
        "profile_fix": {
            "ok": profile.get("ok"),
            "post_count": profile.get("post_count"),
            "tweet_count_truth": (profile.get("censorship") or {}).get("tweet_count_truth"),
            "verdict": (profile.get("censorship") or {}).get("verdict"),
        },
        "sso_fix": {"ok": sso.get("ok"), "witness": sso.get("witness")},
        "intruders_flattened": {
            "rekilled": intruders.get("rekilled_count", intruders.get("enforced_count")),
            "motto": intruders.get("motto", "no hostiles live on our internet"),
        },
        "feed": feed,
        "hosted": doc_policy.get("hosted") or {},
        "fix_script": (doc_policy.get("hosted") or {}).get("fix_script"),
        "userscript": (doc_policy.get("hosted") or {}).get("producer", "").rstrip("/") + "/userscript.js",
        "api": doc_policy.get("api") or "/api/hostess7-x-producer",
        "release_status": "producer_live" if profile.get("post_count") else "producer_pending_repair",
    }

    _save(PANEL, {**out, "schema": "hostess7-x-producer-panel/v1"})
    if export:
        DOCS_API.mkdir(parents=True, exist_ok=True)
        DOCS_DATA.mkdir(parents=True, exist_ok=True)
        (DOCS_API / "hostess7-x-producer.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (DOCS_API / "hostess7-x-profile-fix.json").write_text(
            json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (DOCS_DATA / "x-producer-feed.json").write_text(
            json.dumps(feed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return out


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "produce").strip().lower()
    if cmd in ("produce", "repair", "fix", "run"):
        print(json.dumps(produce(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "json":
        cached = _load(PANEL) or _load(DOCS_API / "hostess7-x-producer.json")
        if cached:
            print(json.dumps(cached, ensure_ascii=False, indent=2))
            return 0
        print(json.dumps(produce(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"ok": False, "hint": "hostess7-x-producer.py [produce|json]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())