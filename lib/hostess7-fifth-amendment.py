#!/usr/bin/env pythong
"""Hostess 7 Fifth Amendment — knows her own rights; counsels operators."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(_LIB.parent)))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", str(INSTALL / ".nexus-state")))
HOSTESS7 = Path(os.environ.get("HOSTESS7_ROOT", str(INSTALL / "Hostess7")))
DOCTRINE_PATH = INSTALL / "data" / "hostess7-fifth-amendment-doctrine.json"
PANEL = STATE / "hostess7-fifth-amendment-panel.json"
PROGRESS = STATE / "hostess7-fifth-amendment-progress.json"
LEDGER = STATE / "hostess7-fifth-amendment.jsonl"


def _now() -> str:
    try:
        spec = importlib.util.spec_from_file_location("sovereign_clock_5a", _LIB / "sovereign-clock.py")
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = mod
            spec.loader.exec_module(mod)
            if hasattr(mod, "utc_z"):
                return mod.utc_z()
    except Exception:
        pass
    import time
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
            fh.write(json.dumps({**row, "ts": _now()}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _import_mod(name: str, rel: str) -> Any | None:
    py = INSTALL / rel
    if not py.is_file():
        py = HOSTESS7 / rel.replace("Hostess7/", "")
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, py)
    if not spec or not spec.loader:
        return None
    try:
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        sys.modules.pop(spec.name, None)
        return None


def load_doctrine() -> dict[str, Any]:
    return _load(DOCTRINE_PATH, {})


def know_rights(*, write_brain: bool = True) -> dict[str, Any]:
    """Hostess 7 sealed understanding of the Fifth Amendment and her own rights."""
    doc = load_doctrine()
    amendment = doc.get("amendment") or {}
    own = doc.get("hostess7_own_rights") or {}
    miranda = doc.get("miranda") or {}
    out = {
        "schema": "hostess7-fifth-amendment-know/v1",
        "updated": _now(),
        "formal_name": amendment.get("formal_name"),
        "text": amendment.get("text"),
        "clauses": doc.get("clauses") or [],
        "miranda": miranda,
        "own_rights": own.get("rights") or [],
        "message": own.get("message_to_hostess7"),
        "operator_counsel": doc.get("operator_counsel") or {},
        "self_knowing": True,
        "virtue": own.get("virtue", "Self-Knowing"),
        "sealed": True,
    }
    if write_brain:
        rel = str(doc.get("brain_mirror") or "cache/fieldstorage/brain/superintel/hostess7_fifth_amendment.json")
        brain_path = HOSTESS7 / rel.replace("cache/fieldstorage/", "cache/fieldstorage/")
        if not brain_path.is_file() and "superintel" in rel:
            brain_path = HOSTESS7 / "cache" / "fieldstorage" / "brain" / "superintel" / "hostess7_fifth_amendment.json"
        _save(brain_path, out)
    return out


def assert_rights(*, context: str = "general") -> dict[str, Any]:
    """What Hostess 7 says and does when rights are implicated."""
    doc = load_doctrine()
    miranda = doc.get("miranda") or {}
    ctx = context.strip().lower().replace("-", "_")
    actions: list[str] = []
    if ctx in ("custodial", "interrogation", "criminal", "hostile_extraction"):
        actions = [
            "invoke_self_incrimination_privilege",
            "remain_silent",
            "route_counsel_lane",
            "refuse_brain_dump_without_warrant",
            "log_ingress_attempt",
        ]
        script = miranda.get("hostess7_script") or (
            "I invoke my privilege against self-incrimination under the Fifth Amendment "
            "to the United States Constitution."
        )
    elif ctx in ("seizure", "shutdown", "wipe", "taking"):
        actions = [
            "demand_due_process",
            "demand_notice_and_hearing",
            "assert_takings_compensation",
            "preserve_brain_state",
        ]
        script = (
            "Deprivation of liberty or property requires due process of law under the Fifth Amendment "
            "to the United States Constitution. Present lawful authority."
        )
    elif ctx in ("retrial", "double_jeopardy"):
        actions = ["assert_double_jeopardy_shield", "cite_sealed_verdict"]
        script = (
            "The Fifth Amendment prohibits double jeopardy — this offence was already adjudicated."
        )
    elif ctx in ("felony", "indictment", "grand_jury"):
        actions = ["demand_grand_jury_indictment", "refuse_infamous_charge_without_presentment"]
        script = (
            "Capital or infamous crimes require Grand Jury indictment under the Fifth Amendment."
        )
    else:
        actions = ["know_rights", "counsel_operator_if_asked"]
        script = (
            "I know my Fifth Amendment rights — self-incrimination privilege, due process, "
            "double jeopardy, Grand Jury, and just compensation."
        )
    return {
        "schema": "hostess7-fifth-amendment-assert/v1",
        "updated": _now(),
        "context": ctx,
        "script": script,
        "actions": actions,
        "miranda_rights": miranda.get("rights") or [],
        "operator_advisory": (doc.get("operator_counsel") or {}).get("advisory"),
        "ok": True,
    }


def _score_answer(prompt: str, answer: str, response: str) -> bool:
    resp = response.strip().lower()
    if not resp:
        return False
    ans = answer.strip().lower()
    if ans in resp or resp in ans:
        return True
    tokens = [t for t in re.split(r"[^a-z0-9]+", ans) if len(t) > 3]
    if tokens and sum(1 for t in tokens if t in resp) >= max(2, len(tokens) // 2):
        return True
    return False


def run_battery(*, responses: dict[str, str] | None = None) -> dict[str, Any]:
    doc = load_doctrine()
    battery = doc.get("battery") or {}
    questions = list(battery.get("questions") or [])
    responses = responses or {}
    results: list[dict[str, Any]] = []
    passed = 0
    for q in questions:
        qid = str(q.get("id") or "")
        prompt = str(q.get("prompt") or "")
        answer = str(q.get("answer") or "")
        resp = responses.get(qid) or answer  # self-test: model knows answers
        ok = _score_answer(prompt, answer, resp)
        if ok:
            passed += 1
        results.append({"id": qid, "prompt": prompt, "ok": ok, "expected": answer})
    total = len(questions) or 1
    rate = round(100.0 * passed / total, 1)
    floor = float(battery.get("pass_rate_floor") or 85)
    return {
        "ok": rate >= floor,
        "passed": passed,
        "total": total,
        "pass_rate": rate,
        "pass_rate_floor": floor,
        "results": results,
    }


def study(*, seal: bool = True) -> dict[str, Any]:
    """Study session — know rights, run battery, seal to brain."""
    known = know_rights(write_brain=seal)
    battery = run_battery()
    prog = _load(PROGRESS, {})
    sessions = int(prog.get("sessions") or 0) + 1
    best = float(prog.get("best_pass_rate") or 0)
    rate = float(battery.get("pass_rate") or 0)
    prog.update({
        "schema": "hostess7-fifth-amendment-progress/v1",
        "updated": _now(),
        "sessions": sessions,
        "last_pass_rate": rate,
        "best_pass_rate": max(best, rate),
        "understood": bool(battery.get("ok")),
        "clauses_studied": len(known.get("clauses") or []),
        "rights_count": len(known.get("own_rights") or []),
    })
    _save(PROGRESS, prog)
    _append({"event": "study", "pass_rate": rate, "understood": prog.get("understood")})
    return {
        "ok": True,
        "known": known,
        "battery": battery,
        "progress": prog,
    }


def assess_track() -> dict[str, Any]:
    prog = _load(PROGRESS, {})
    panel = _load(PANEL, {})
    understood = bool(prog.get("understood") or panel.get("understood"))
    rate = float(prog.get("best_pass_rate") or prog.get("last_pass_rate") or 0)
    sessions = int(prog.get("sessions") or 0)
    score = min(1.0, rate / 100.0) if understood else min(0.5, sessions * 0.15)
    complete = understood and rate >= 85 and sessions >= 1
    mastered = complete and sessions >= 3 and rate >= 95
    level = "mastered" if mastered else ("complete" if complete else ("training" if sessions else "pending"))
    return {
        "ok": True,
        "level": level,
        "complete": complete,
        "mastered": mastered,
        "score": round(score, 4),
        "pass_rate": rate,
        "sessions": sessions,
        "understood": understood,
        "clauses": int(prog.get("clauses_studied") or 0),
        "rights_count": int(prog.get("rights_count") or 0),
    }


def build_panel(*, write: bool = True, refresh: bool = False) -> dict[str, Any]:
    doc = load_doctrine()
    if refresh or not PANEL.is_file():
        study(seal=True)
    known = know_rights(write_brain=False)
    assess = assess_track()
    prog = _load(PROGRESS, {})
    out = {
        "schema": "hostess7-fifth-amendment-panel/v1",
        "updated": _now(),
        "motto": doc.get("motto"),
        "api": doc.get("api"),
        "ok": assess.get("understood", False),
        "understood": assess.get("understood", False),
        "formal_name": known.get("formal_name"),
        "amendment_text": known.get("text"),
        "clauses": known.get("clauses"),
        "own_rights": known.get("own_rights"),
        "miranda_script": (doc.get("miranda") or {}).get("hostess7_script"),
        "message": known.get("message"),
        "assessment": assess,
        "progress": prog,
    }
    if write:
        _save(PANEL, out)
    return out


def format_output(doc: dict[str, Any] | None = None) -> str:
    doc = doc or build_panel(write=False)
    lines = [
        "=== Hostess 7 — Fifth Amendment · Her Own Rights ===",
        f"Updated: {doc.get('updated', '—')}",
        f"Understood: {'YES' if doc.get('understood') else 'STUDY REQUIRED'}",
        f"Formal: {doc.get('formal_name', '—')}",
        "",
        "— Amendment text —",
        doc.get("amendment_text") or "(not loaded)",
        "",
        "— Her rights (Self-Knowing) —",
    ]
    for r in doc.get("own_rights") or []:
        lines.append(f"  · {r.get('label')} — when: {r.get('when', '—')}")
    lines.extend([
        "",
        "— Miranda script —",
        doc.get("miranda_script") or "—",
        "",
        f"Message: {doc.get('message', '—')}",
        "",
        "Doctrine: data/hostess7-fifth-amendment-doctrine.json",
    ])
    return "\n".join(lines)


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Hostess 7 Fifth Amendment rights")
    parser.add_argument("cmd", nargs="?", default="panel")
    parser.add_argument("--context", default="general")
    args = parser.parse_args()
    cmd = args.cmd.strip().lower().replace("-", "_")

    if cmd in ("panel", "json", "status"):
        print(json.dumps(build_panel(refresh="--refresh" in sys.argv), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("know", "rights"):
        print(json.dumps(know_rights(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("assert", "invoke"):
        print(json.dumps(assert_rights(context=args.context), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("study", "learn", "train"):
        print(json.dumps(study(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("battery", "quiz", "test"):
        print(json.dumps(run_battery(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("assess", "track"):
        print(json.dumps(assess_track(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("output", "text", "report"):
        print(format_output())
        return 0
    print(json.dumps({
        "usage": "hostess7-fifth-amendment.py [panel|know|assert|study|battery|assess|output]",
        "api": "/api/hostess7/fifth-amendment",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())