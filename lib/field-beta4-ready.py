#!/usr/bin/env pythong
"""Beta 4 WATCHGUARD helpers — combinatronic restore + panel (orchestration lives in AML)."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
PANEL = STATE / "field-beta4-ready-panel.json"
LEDGER = STATE / "field-beta4-ready.jsonl"
HOLD = STATE / "field-beta4-release-hold.json"


def _utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        return default if default is not None else {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append(row: dict[str, Any]) -> None:
    try:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def verify(*, halt: bool = True) -> dict[str, Any]:
    """Run beta4_verify AML suite via test engine — no bash subprocess suites."""
    import importlib.util

    test_py = INSTALL / "lib" / "field-ammolang-test.py"
    spec = importlib.util.spec_from_file_location("aml_test", test_py)
    if not spec or not spec.loader:
        return {"ok": False, "error": "test_engine_missing"}
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    os.environ.setdefault("HOSTESS7_TRUTH_LIE_SKIP_NEXUS", "1")
    doc = mod.run_suite_name("beta4_verify", halt=halt)
    out = {
        "ok": bool(doc.get("ok")),
        "schema": "field-beta4-verify/v1",
        "updated": _utc(),
        "passed": doc.get("passed"),
        "failed": doc.get("failed"),
        "total": doc.get("total"),
        "elapsed_ms": doc.get("elapsed_ms"),
        "aml_route": "beta4_verify",
        "via": "aml_suite",
    }
    _append({**out, "event": "verify"})
    return out


def combinatronic_restore(*, limit: int = 48) -> dict[str, Any]:
    """Regenerate exploring_* combinatronic books — capped batch."""
    t0 = time.perf_counter()
    limit = max(1, min(int(limit), 200))
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "vis", INSTALL / "lib" / "field-combinatronic-visuals.py"
        )
        if not spec or not spec.loader:
            return {"ok": False, "label": "combinatronic_langs", "error": "visuals_missing"}
        vis = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(vis)

        skip = {
            "exploring_hand_to_hand_combat",
            "exploring_weaponized_combat",
            "exploring_combat",
        }
        restored: list[str] = []
        errors: list[dict[str, Any]] = []
        count = 0
        for book_json in sorted((INSTALL / "library" / "dewey").rglob("book.json")):
            if count >= limit:
                break
            try:
                doc = json.loads(book_json.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            bid = str(doc.get("id") or book_json.parent.name)
            if not bid.startswith("exploring_") or bid.startswith("exploring_the_") or bid in skip:
                continue
            h7c = book_json.parent / f"{bid}.h7c"
            if not h7c.is_file():
                continue
            lang = doc.get("combinatronic_lang") or bid.replace("exploring_", "", 1)
            try:
                rep = vis.generate_exploring_book(lang)
                if rep.get("ok"):
                    restored.append(bid)
                    count += 1
                else:
                    errors.append({"book": bid, "error": rep.get("error")})
            except Exception as exc:
                errors.append({"book": bid, "error": str(exc)[:120]})
        ok = len(errors) == 0 or len(restored) > 0
        out = {
            "ok": ok,
            "label": "combinatronic_langs",
            "restored": len(restored),
            "errors": len(errors),
            "sample": restored[:8],
            "error_sample": errors[:5],
            "limit": limit,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
        }
    except Exception as exc:
        out = {
            "ok": False,
            "label": "combinatronic_langs",
            "error": str(exc)[:200],
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
        }
    _append({**out, "event": "combinatronic_restore"})
    return out


def verify_hand() -> dict[str, Any]:
    """Spot-check exploring_the_hand H7c roundtrip."""
    t0 = time.perf_counter()
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("d", INSTALL / "lib" / "field-dewey-library.py")
        if not spec or not spec.loader:
            return {"ok": False, "error": "dewey_library_missing"}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        text, _, _ = mod.read_h7c_text("exploring_the_hand")
        ok = len(text) > 0
        out = {
            "ok": ok,
            "label": "verify_exploring_the_hand",
            "chars": len(text),
            "message": f"exploring_the_hand ok {len(text)} chars",
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
        }
    except Exception as exc:
        out = {
            "ok": False,
            "label": "verify_exploring_the_hand",
            "error": str(exc)[:200],
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
        }
    if out.get("ok"):
        print(out["message"])
    _append({**out, "event": "verify_hand"})
    return out


def release_hold(*, reason: str = "", operator: str = "system") -> dict[str, Any]:
    """Pause Beta 4 release until operator clears hold."""
    doc = {
        "schema": "field-beta4-release-hold/v1",
        "held": True,
        "updated": _utc(),
        "reason": reason or "operator hold — catch up before Beta 4",
        "operator": operator,
        "release": "2.0.0-beta4",
        "cleared_by": None,
    }
    _save(HOLD, doc)
    _append({**doc, "event": "hold"})
    return doc


def release_resume(*, operator: str = "operator") -> dict[str, Any]:
    """Clear Beta 4 hold — release may run again."""
    prev = _load(HOLD, {})
    doc = {
        "schema": "field-beta4-release-hold/v1",
        "held": False,
        "updated": _utc(),
        "reason": prev.get("reason"),
        "operator": prev.get("operator"),
        "release": "2.0.0-beta4",
        "cleared_by": operator,
        "cleared_at": _utc(),
    }
    _save(HOLD, doc)
    _append({**doc, "event": "resume"})
    return doc


def release_hold_status() -> dict[str, Any]:
    doc = _load(HOLD, {})
    if not doc:
        return {"held": False, "schema": "field-beta4-release-hold/v1", "updated": _utc()}
    return doc


def release_blocked() -> tuple[bool, dict[str, Any]]:
    doc = release_hold_status()
    if doc.get("held"):
        return True, doc
    if os.environ.get("BETA4_RELEASE_HOLD", "").strip().lower() in ("1", "true", "yes", "hold"):
        return True, {"held": True, "reason": "BETA4_RELEASE_HOLD env", "updated": _utc()}
    return False, doc


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doc = _load(PANEL, {})
    if not doc:
        doc = {
            "schema": "field-beta4-ready-panel/v1",
            "updated": _utc(),
            "motto": "Beta 4 WATCHGUARD — AML routes, no exec-script hangs",
            "aml_routes": [
                "beta4_watchguard",
                "beta4_verify",
                "beta4_library_prep",
                "beta4_restore_h7c",
            ],
            "verify_via": "test suite:beta4_verify",
        }
    else:
        doc["updated"] = _utc()
    hold = release_hold_status()
    doc["release_hold"] = hold
    doc["release_blocked"] = bool(hold.get("held"))
    if write:
        _save(PANEL, doc)
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower().replace("-", "_")
    if cmd in ("panel", "json", "status"):
        print(json.dumps(build_panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "verify":
        rep = verify()
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0 if rep.get("ok") else 1
    if cmd in ("combinatronic_restore", "combinatronic", "langs"):
        limit = 48
        for arg in sys.argv[2:]:
            if arg.startswith("--limit="):
                limit = int(arg.split("=", 1)[1])
        rep = combinatronic_restore(limit=limit)
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0 if rep.get("ok") else 1
    if cmd in ("verify_hand", "verify_hand_h7c", "hand"):
        rep = verify_hand()
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0 if rep.get("ok") else 1
    if cmd in ("hold", "pause", "stop"):
        reason = " ".join(sys.argv[2:]).strip()
        print(json.dumps(release_hold(reason=reason or "operator hold"), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("resume", "clear_hold", "unhold"):
        print(json.dumps(release_resume(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("hold_status", "blocked"):
        blocked, doc = release_blocked()
        print(json.dumps({"blocked": blocked, **doc}, ensure_ascii=False, indent=2))
        return 2 if blocked else 0
    print(json.dumps({
        "error": "usage: field-beta4-ready.py [panel|verify|combinatronic_restore|verify_hand|hold|resume|hold_status]",
        "aml": "./lib/ammolang-run.sh beta4_watchguard",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())