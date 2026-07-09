#!/usr/bin/env python3
"""Hostess 7 Internet Clean — secure bookmarks for every browser, telemetry strip, default boot."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
QUEEN = Path(os.environ.get("QUEEN_ROOT", INSTALL / "Queen"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "hostess7-internet-clean-doctrine.json"
STAMP = STATE / "hostess7-internet-clean.stamp"
LOG = STATE / "hostess7-internet-clean.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_mod(name: str, rel: str) -> Any | None:
    path = INSTALL / rel
    if not path.is_file():
        path = QUEEN / rel.removeprefix("Queen/")
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _append_log(row: dict[str, Any]) -> None:
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def internet_clean(*, force: bool = False) -> dict[str, Any]:
    """Sweep host browsers, scrub telemetry, export secure bookmarks into Queen Browser field import."""
    doctrine = {}
    try:
        doctrine = json.loads(DOCTRINE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass

    os.environ.setdefault(
        "HOSTESS7_PAGES_BASE",
        str(doctrine.get("pages_base_default") or "https://zacharygeurts.github.io/Hostess7"),
    )
    os.environ.setdefault("HOSTESS7_BOOKMARK_MODE", str(doctrine.get("bookmark_mode") or "pages"))

    import_out: dict[str, Any] = {"ok": True, "skipped": True}
    scrub_out: dict[str, Any] = {"ok": True}
    export_out: dict[str, Any] = {"ok": False, "error": "not_run"}

    qbi = _load_mod("qbi", "Queen/lib/queen-browser-import.py")
    if qbi is not None:
        if force or getattr(qbi, "should_auto_sweep", lambda: True)():
            import_out = qbi.sweep_all(apply=True)
        elif hasattr(qbi, "auto_sweep_if_needed"):
            import_out = qbi.auto_sweep_if_needed() or {"ok": True, "skipped": True}
        if hasattr(qbi, "organize_scrub"):
            scrub_out = qbi.organize_scrub(import_out if isinstance(import_out, dict) else {})

    export_mod = _load_mod("qhbm", "Queen/lib/queen-host-bookmark-export.py")
    if export_mod is not None and hasattr(export_mod, "export_host_bookmarks"):
        export_out = export_mod.export_host_bookmarks(import_browsers=True)

    quarantined = int((import_out or {}).get("quarantined") or 0)
    dropped = int((import_out or {}).get("dropped") or 0)
    ff_ok = sum(1 for x in (export_out.get("field_gecko") or export_out.get("host_gecko") or []) if x.get("ok"))
    cr_ok = sum(1 for x in (export_out.get("chromium") or []) if x.get("ok"))

    out = {
        "ok": True,
        "schema": "hostess7-internet-clean/v1",
        "updated": _now(),
        "force": force,
        "motto": doctrine.get("motto", "Clean the whole internet"),
        "default_on_hostess7": bool(doctrine.get("default_on_hostess7", True)),
        "import": import_out,
        "scrub": scrub_out,
        "export": export_out,
        "summary": {
            "bookmarks_secured": int((export_out or {}).get("count") or 0),
            "telemetry_quarantined": quarantined,
            "telemetry_dropped": dropped,
            "field_gecko_profiles": ff_ok,
            "chromium_profiles": cr_ok,
            "pages_base": os.environ.get("HOSTESS7_PAGES_BASE"),
        },
        "notice": doctrine.get("notice", "All Rights Reserved"),
    }
    try:
        STAMP.write_text(_now() + "\n", encoding="utf-8")
    except OSError:
        pass
    _append_log({**out, "action": "internet_clean"})
    return out


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    force = cmd == "force" or "--force" in sys.argv
    if cmd in ("json", "clean", "boot", "internet-clean", "force"):
        out = internet_clean(force=force or cmd == "force")
    elif cmd == "status":
        out = {
            "ok": True,
            "schema": "hostess7-internet-clean/v1",
            "stamp": STAMP.read_text(encoding="utf-8").strip() if STAMP.is_file() else None,
            "doctrine": str(DOCTRINE),
        }
    else:
        print(json.dumps({
            "error": "usage: hostess7-internet-clean.py [json|clean|force|status]",
        }))
        return 1
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())