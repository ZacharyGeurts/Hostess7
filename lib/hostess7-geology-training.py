#!/usr/bin/env pythong
"""Geology training — plate tectonics, earth materials, Gutenberg textbook."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
DOCTRINE = INSTALL / "data" / "hostess7-geology-doctrine.json"
BATTERY = INSTALL / "data" / "hostess7-geology-battery.json"
RUNTIME = STATE / "hostess7-geology-runtime.json"
PANEL = STATE / "hostess7-geology-panel.json"

_SOVEREIGN_CLOCK_MOD = None


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


def _h7s_read_json(path: Path, default: Any = None) -> Any:
    fs_py = INSTALL / "lib" / "field-h7s-fs.py"
    if path.suffix.lower() == ".json" and fs_py.is_file():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("_h7s_fs_io", fs_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "read_json"):
                    return mod.read_json(path, default=default)
        except Exception:
            pass
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}

def _load(path: Path, default: Any = None) -> Any:
    return _h7s_read_json(path, default=default)


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def textbook_info() -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    tb = doc.get("textbook") or {}
    return {
        "ok": True,
        "domain": "geology",
        "textbook_id": tb.get("id", "gutenberg_textbook_geology"),
        "title": tb.get("title", "Text-Book of Geology"),
        "url": tb.get("url"),
        "license": tb.get("license", "Public Domain"),
    }


def help_query(query: str, *, audience: str = "ai") -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    topics = doc.get("topics") or {}
    q = query.lower()
    hits = [k for k, v in topics.items() if any(t in q for t in (v.get("keywords") or []))]
    return {
        "ok": True,
        "domain": "geology",
        "training": "geology",
        "query": query,
        "audience": audience,
        "topics": hits or list(topics.keys())[:3],
        "summary": (
            "Geology covers plate tectonics — convergent boundaries subduct lithosphere, "
            "divergent boundaries spread ocean crust, and transform boundaries slide past."
        ),
    }


def corroborate_claim(claim: str = "") -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    return {
        "ok": True,
        "domain": "geology",
        "claim": claim,
        "ironclad_ref": doc.get("ironclad_ref"),
        "verified": bool(claim),
    }


def train_session(*, rounds: int = 8) -> dict[str, Any]:
    n = max(1, min(int(rounds), 500))
    rt = _load(RUNTIME, {"schema": "hostess7-geology-runtime/v1", "proficiency": 0.0})
    prof = min(1.0, float(rt.get("proficiency") or 0) + 0.02 * n)
    rt["proficiency"] = round(prof, 4)
    rt["session_rounds"] = int(rt.get("session_rounds") or 0) + n
    rt["updated"] = _now()
    _save(RUNTIME, rt)
    return {"ok": True, "rounds": n, "proficiency": prof, "domain": "geology"}


def build_panel() -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    rt = _load(RUNTIME, {})
    return {
        "schema": "hostess7-geology/v1",
        "updated": _now(),
        "domain": "geology",
        "motto": doc.get("motto"),
        "textbook": textbook_info(),
        "proficiency": rt.get("proficiency", 0.0),
        "training_mode": "geology",
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        panel = build_panel()
        _save(PANEL, panel)
        print(json.dumps(panel, ensure_ascii=False))
        return 0
    if cmd == "textbook":
        print(json.dumps(textbook_info(), ensure_ascii=False))
        return 0
    if cmd == "help":
        query = sys.argv[2] if len(sys.argv) > 2 else ""
        audience = "human" if "--human" in sys.argv else "ai"
        print(json.dumps(help_query(query, audience=audience), ensure_ascii=False))
        return 0
    if cmd == "corroborate":
        claim = sys.argv[2] if len(sys.argv) > 2 else ""
        print(json.dumps(corroborate_claim(claim), ensure_ascii=False))
        return 0
    if cmd in ("train", "session"):
        rounds = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 8
        print(json.dumps(train_session(rounds=rounds), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: hostess7-geology-training.py [json|textbook|help|corroborate|train]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())