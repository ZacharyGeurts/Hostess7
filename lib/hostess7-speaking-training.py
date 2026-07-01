#!/usr/bin/env pythong
"""Speaking training — Exploring Speaking books → Final Mouth FCC-safe spoken word."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SG = Path(os.environ.get("SG_ROOT", str(INSTALL.parent.parent)))
QUEEN = Path(os.environ.get("QUEEN_ROOT", SG / "NewLatest" / "Queen"))
FINAL_MOUTH = Path(os.environ.get("FINAL_MOUTH_ROOT", SG / "NewLatest" / "Final_Mouth"))
DOCTRINE = INSTALL / "data" / "hostess7-speaking-training-doctrine.json"
PANEL = STATE / "hostess7-speaking-training-panel.json"
SPEAKING_SHELF = INSTALL / "library" / "dewey" / "400-education"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


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


def _mouthball(body: dict[str, Any]) -> dict[str, Any]:
    path = QUEEN / "lib" / "queen-mouthball.py"
    if not path.is_file():
        return {"ok": False, "error": "mouthball_missing"}
    env = os.environ.copy()
    py = [str(QUEEN / "lib"), str(FINAL_MOUTH)]
    env["PYTHONPATH"] = os.pathsep.join(py + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
    try:
        proc = subprocess.run(
            [sys.executable, str(path), "dispatch"],
            input=json.dumps(body, ensure_ascii=False),
            capture_output=True,
            text=True,
            timeout=90,
            env=env,
            cwd=str(QUEEN),
        )
        return json.loads(proc.stdout or "{}")
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        return {"ok": False, "error": str(exc)}


def _mouth_neural(body: dict[str, Any]) -> dict[str, Any]:
    path = FINAL_MOUTH / "zocr_neural_assist.py"
    if not path.is_file():
        return {"ok": False, "error": "mouth_neural_missing"}
    try:
        proc = subprocess.run(
            [sys.executable, str(path), "dispatch"],
            input=json.dumps(body, ensure_ascii=False),
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(FINAL_MOUTH),
        )
        return json.loads(proc.stdout or "{}")
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        return {"ok": False, "error": str(exc)}


def _read_speaking_book(iso6393: str) -> str:
    book_id = f"exploring_speaking_{iso6393}"
    h7c = SPEAKING_SHELF / book_id / f"{book_id}.h7c"
    if h7c.is_file():
        h7c_py = INSTALL / "lib" / "field-h7c-compression.py"
        try:
            spec = importlib.util.spec_from_file_location("h7c_sp", h7c_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                _, text, _ = mod.decompress_h7c(h7c.read_bytes())
                if text:
                    return text
        except Exception:
            pass
    bridge = INSTALL / "lib" / "h7-library-bridge.py"
    if bridge.is_file():
        try:
            spec = importlib.util.spec_from_file_location("h7_bridge_sp", bridge)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                full = mod.read_full(book_id)
                if full.get("ok"):
                    return str(full.get("text") or "")
        except Exception:
            pass
    return ""


def _extract_lemma(text: str) -> dict[str, str]:
    for line in text.splitlines():
        if line.startswith("|") and "Lemma" not in line and "---" not in line:
            cols = [c.strip() for c in line.strip("|").split("|")]
            if len(cols) >= 4 and cols[0] and cols[0] not in ("—", "(pending)"):
                return {
                    "lemma": cols[0],
                    "ipa": cols[1] if len(cols) > 1 else "",
                    "gloss": cols[3] if len(cols) > 3 else "",
                }
    m = re.search(r'"lemma":\s*"([^"]+)"', text)
    if m:
        return {"lemma": m.group(1), "ipa": "", "gloss": ""}
    return {"lemma": "hello", "ipa": "/həˈloʊ/", "gloss": "greeting"}


def _presume_guard(action_id: str, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> dict[str, Any]:
    pg = INSTALL / "lib" / "hostess7-presume.py"
    if not pg.is_file():
        return fn(*args, **kwargs)
    try:
        spec = importlib.util.spec_from_file_location("h7_presume_sp", pg)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "guard_action"):
                return mod.guard_action(action_id, fn, *args, label=action_id, **kwargs)
    except Exception:
        pass
    return fn(*args, **kwargs)


def run_lesson(
    lesson_id: str,
    *,
    iso6393: str = "eng",
    audience: str = "human",
) -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    text = _read_speaking_book(iso6393)
    lemma = _extract_lemma(text) if text else {"lemma": "hello", "ipa": "/həˈloʊ/", "gloss": "greeting"}
    utterance = f"{lemma['lemma']} — {lemma['ipa']} — {lemma['gloss']}".strip(" —")

    if lesson_id == "phonetics_read":
        sample = f"Reading IPA from Exploring Speaking {iso6393}: {lemma['ipa']}"
        prep = _mouth_neural({"action": "train", "lesson": "speaking_phonetics", "thought": sample})
        ok = prep.get("ok", False)
    elif lesson_id == "lemma_speak":
        spoken = _mouthball({
            "action": "speak",
            "text": utterance,
            "mode": "speaking",
            "audience": audience,
        })
        ok = spoken.get("ok", False)
        prep = {"utterance": utterance, "mouth": spoken}
    elif lesson_id == "human_spoken_word":
        spoken = _mouthball({
            "action": "speak",
            "text": utterance,
            "mode": "speaking",
            "audience": "human",
        })
        fcc = spoken.get("fcc_clamp") or {}
        ok = spoken.get("ok") and bool(fcc.get("spoken_word_first", True))
        prep = {"mouth": spoken, "fcc_clamp": fcc}
    elif lesson_id == "animal_call":
        spoken = _mouthball({
            "action": "speak",
            "text": "Good companion — steady call.",
            "mode": "animal",
            "audience": "animal_dog",
        })
        ok = spoken.get("ok", False)
        prep = {"mouth": spoken, "audience": "animal_dog"}
    elif lesson_id == "hieroglyph_translit":
        sample = "nfr — /ˈnaːfir/ — good / beautiful" if iso6393 == "egy" else utterance
        spoken = _mouthball({"action": "speak", "text": sample, "mode": "speaking", "audience": "human"})
        ok = spoken.get("ok", False)
        prep = {"translit": sample, "mouth": spoken}
    elif lesson_id == "thought_voice_speak":
        thought = f"I will speak {lemma['lemma']} with truth gate and Ironclad grounding."
        prep = _mouth_neural({"action": "prepare", "thought": thought, "mode": "speaking"})
        spoken = _mouthball({
            "action": "speak",
            "text": str(prep.get("utterance") or utterance),
            "mode": "speaking",
            "audience": audience,
        })
        ok = prep.get("ok") and spoken.get("ok")
        prep = {"prepare": prep, "mouth": spoken}
    else:
        prep = _mouth_neural({"action": "train", "lesson": lesson_id, "thought": utterance})
        ok = prep.get("ok", False)

    return {
        "ok": ok,
        "lesson_id": lesson_id,
        "iso6393": iso6393,
        "audience": audience,
        "lemma": lemma,
        "prepare_or_mouth": prep,
    }


def _run_speaking_training_body(
    *,
    iso6393: str = "eng",
    audience: str = "human",
) -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    lessons = doc.get("lessons") or []
    steps: list[dict[str, Any]] = []
    passed = 0
    for lesson in lessons:
        lid = str(lesson.get("id") or "")
        rep = run_lesson(lid, iso6393=iso6393, audience=audience)
        if rep.get("ok"):
            passed += 1
        steps.append({
            "id": lid,
            "label": lesson.get("label", lid),
            "ok": rep.get("ok"),
            "lemma": rep.get("lemma"),
        })
        _mouth_neural({"action": "train", "lesson": f"speaking_{lid}", "thought": str(rep.get("lemma"))})

    total = len(lessons) or 1
    rate = passed / total
    threshold = float(doc.get("pass_threshold") or 0.75)
    complete = rate >= threshold
    panel = {
        "schema": "hostess7-speaking-training-panel/v1",
        "updated": _now(),
        "iso6393": iso6393,
        "audience": audience,
        "passed": passed,
        "total": total,
        "pass_rate": round(rate * 100, 1),
        "complete": complete,
        "level": "fluent" if complete and passed == total else "training" if passed else "pending",
        "steps": steps,
        "final_mouth_mode": doc.get("default_mode", "speaking"),
        "fcc_acoustic": doc.get("final_mouth", {}).get("fcc_acoustic"),
        "motto": doc.get("motto"),
    }
    _save(PANEL, panel)
    ca = INSTALL / "lib" / "hostess7-change-awareness.py"
    if ca.is_file():
        try:
            spec = importlib.util.spec_from_file_location("h7_ca_sp", ca)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "witness_change"):
                    mod.witness_change(
                        source="speaking_training",
                        label=f"speaking_training_{iso6393}",
                        detail=f"level={panel.get('level')} passed={passed}/{total}",
                        meta={"iso6393": iso6393, "complete": complete},
                    )
        except Exception:
            pass

    return {"ok": complete, **panel}


def run_speaking_training(
    *,
    iso6393: str = "eng",
    audience: str = "human",
) -> dict[str, Any]:
    aid = f"speaking_training_{iso6393}"
    guarded = _presume_guard(
        aid,
        _run_speaking_training_body,
        iso6393=iso6393,
        audience=audience,
    )
    if guarded.get("schema") == "hostess7-presume-guard/v1":
        result = guarded.get("result") or {}
        result["presume_guard"] = {
            "action_id": aid,
            "uninterruptable": guarded.get("uninterruptable"),
            "elapsed_us": guarded.get("elapsed_us"),
        }
        return result
    return guarded


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Hostess 7 speaking training")
    ap.add_argument("cmd", nargs="?", default="train", choices=["train", "lesson", "json"])
    ap.add_argument("--code", default="eng")
    ap.add_argument("--audience", default="human")
    ap.add_argument("--lesson", default="lemma_speak")
    args = ap.parse_args()
    if args.cmd == "lesson":
        rep = run_lesson(args.lesson, iso6393=args.code, audience=args.audience)
    else:
        rep = run_speaking_training(iso6393=args.code, audience=args.audience)
    print(json.dumps(rep, ensure_ascii=False, indent=2))
    return 0 if rep.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())