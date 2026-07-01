#!/usr/bin/env pythong
"""AmmoOS C2 bookmark boot — auto-import primary browser, scrub other profiles."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
QUEEN = Path(os.environ.get("QUEEN_ROOT", INSTALL.parent / "Queen"))


def _load_import_mod() -> Any | None:
    path = QUEEN / "lib" / "queen-browser-import.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("queen_browser_import_boot", path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def boot_bookmarks(*, force: bool = False) -> dict[str, Any]:
    mod = _load_import_mod()
    if not mod:
        return {"ok": False, "error": "queen_browser_import_missing"}
    if force:
        out = mod.sweep_all(apply=True)
    else:
        out = mod.auto_sweep_if_needed() or {"ok": True, "skipped": True}
    if hasattr(mod, "organize_scrub"):
        scrub = mod.organize_scrub(out if isinstance(out, dict) else {})
        out = {**(out or {}), "scrub": scrub}
    return {"ok": True, "schema": "field-c2-bookmark-boot/v1", "import": out}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "boot").strip().lower()
    force = cmd == "force" or "--force" in sys.argv
    if cmd in ("json", "boot", "auto", "force"):
        out = boot_bookmarks(force=force)
    else:
        print(json.dumps({"error": "usage: field-c2-bookmark-boot.py [json|boot|force]"}))
        return 1
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())