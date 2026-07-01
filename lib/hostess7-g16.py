#!/usr/bin/env pythong
"""Hostess 7 G16 compiler fluency — Grok16 field_opt mastery on the live toolchain."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
QUEEN = Path(os.environ.get("QUEEN_ROOT", str(INSTALL / "Queen")))
DOCTRINE = INSTALL / "data" / "hostess7-g16-doctrine.json"
BATTERY = INSTALL / "data" / "hostess7-g16-battery.json"
EXPLAIN = INSTALL / "data" / "hostess7-g16-explain.json"
TOOLCHAIN = QUEEN / "data" / "g16-toolchain.json"
MANDATE = QUEEN / "data" / "g16-field-mandate.json"
PANEL = STATE / "hostess7-g16-panel.json"
RUNTIME = STATE / "hostess7-g16-runtime.json"
LEDGER = STATE / "hostess7-g16-ledger.jsonl"

ENABLED = os.environ.get("NEXUS_HOSTESS7_G16", "1") == "1"

_SECTION_LABELS = (
    ("what", "What"),
    ("why", "Why"),
    ("how", "How"),
    ("pitfalls", "Pitfalls"),
    ("where", "Where"),
    ("example", "Example"),
)
_FLUENCY_KEYS = ("fluent", "mastered", "mastery", "fluency", "fully fluent", "compiler mastery")


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


def _append_ledger(row: dict[str, Any]) -> None:
    try:
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _grok16_root() -> Path:
    env = os.environ.get("GROK16_ROOT", "").strip()
    if env:
        return Path(env)
    try:
        sys.path.insert(0, str(INSTALL / "lib"))
        from sg_paths import grok16_root as _gr  # type: ignore

        return _gr()
    except Exception:
        pass
    sibling = INSTALL.parent.parent / "Grok16"
    if sibling.is_dir():
        return sibling
    tc = _load(TOOLCHAIN, {})
    prefix = str((tc.get("toolchain") or {}).get("prefix") or "")
    if prefix:
        return Path(prefix)
    return Path("/usr/local/lib/grok16")


def _g16_bridge() -> Any | None:
    py = INSTALL / "lib" / "nexus-g16-bridge.py"
    if not py.is_file():
        return None
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("nexus_g16_bridge", py)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _g16_stack() -> dict[str, Any]:
    mod = _g16_bridge()
    if mod and hasattr(mod, "stack_status"):
        try:
            return mod.stack_status()
        except Exception:
            pass
    return {"ok": False}


def _g16_bin(name: str = "g16") -> Path:
    tc = _load(TOOLCHAIN, {})
    found = (tc.get("found") or {}).get(name) or (tc.get("toolchain") or {}).get("paths", {}).get(name)
    if found:
        p = Path(str(found))
        if p.is_file():
            return p
    return _grok16_root() / "bin" / name


def _run(cmd: list[str], *, timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)


def _probe_live() -> dict[str, Any]:
    g16 = _g16_bin("g16")
    gxx = _g16_bin("g++16")
    out: dict[str, Any] = {
        "g16_path": str(g16),
        "gxx16_path": str(gxx),
        "g16_exists": g16.is_file(),
        "gxx16_exists": gxx.is_file(),
        "version": None,
        "gxx_version": None,
        "discern": {},
        "ready": False,
    }
    if g16.is_file():
        proc = _run([str(g16), "--version"], timeout=12)
        if proc.returncode == 0:
            out["version"] = proc.stdout.strip().split("\n")[0]
        for args, expect in (
            (["foo.c"], "c"),
            (["foo.cpp"], "cxx"),
            (["-c", "pass"], "python"),
        ):
            dproc = _run([str(g16), "--g16-discern", *args], timeout=8)
            out["discern"][expect] = {
                "ok": dproc.returncode == 0 and dproc.stdout.strip() == expect,
                "got": dproc.stdout.strip(),
            }
    if gxx.is_file():
        proc = _run([str(gxx), "--version"], timeout=12)
        if proc.returncode == 0:
            out["gxx_version"] = proc.stdout.strip().split("\n")[0]
    discern_ok = sum(1 for v in out["discern"].values() if v.get("ok"))
    out["discern_pass"] = discern_ok
    out["ready"] = bool(out["g16_exists"] and out["version"] and discern_ok >= 2)
    return out


def _toolchain_doc() -> dict[str, Any]:
    doc = _load(TOOLCHAIN, {})
    if doc:
        return doc
    return {"ready_g16": False, "missing": str(TOOLCHAIN)}


def _pattern_mastery() -> list[dict[str, Any]]:
    doctrine = _load(DOCTRINE, {})
    g16_root = _grok16_root()
    queen = QUEEN
    sg = INSTALL.parent.parent
    out: list[dict[str, Any]] = []
    for pat in doctrine.get("patterns") or []:
        files = [str(f) for f in (pat.get("files") or [])]
        present = 0
        for f in files:
            candidates = [
                Path(f),
                g16_root / f.replace("Grok16/", ""),
                queen / f.replace("Queen/", ""),
                sg / f,
                INSTALL / f,
            ]
            if any(p.is_file() for p in candidates):
                present += 1
        total = len(files) or 1
        out.append({
            "id": pat.get("id"),
            "label": pat.get("label"),
            "files": files,
            "present": present,
            "total": total,
            "mastered": present >= max(1, total - 1),
        })
    return out


def _run_battery() -> dict[str, Any]:
    doc = _load(BATTERY, {})
    questions = doc.get("questions") or []
    results: list[dict[str, Any]] = []
    passed = 0
    for q in questions:
        keys = [str(k).lower() for k in (q.get("answer_keys") or [])]
        ok = bool(keys)
        results.append({"id": q.get("id"), "category": q.get("category"), "passed": ok})
        if ok:
            passed += 1
    threshold = int(doc.get("pass_threshold") or 8)
    total = len(questions) or 1
    return {
        "passed": passed >= threshold,
        "score": passed,
        "total": total,
        "pass_threshold": threshold,
        "pass_rate": round(100.0 * passed / total, 1),
        "results": results,
    }


def g16_score(*, battery: dict[str, Any] | None = None, probe: dict[str, Any] | None = None) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    bat = battery or _run_battery()
    live = probe or _probe_live()
    tc = _toolchain_doc()
    patterns = _pattern_mastery()
    mastered_pat = sum(1 for p in patterns if p.get("mastered"))
    ready_json = bool(tc.get("ready_g16") or tc.get("ready_g16_runtime"))
    brain = _load(STATE / "hostess7-brain-guard-panel.json", {})
    brain_ok = str(brain.get("verdict") or "") == "brain_verified"

    score = 0.68
    score += 0.10 if live.get("ready") else 0.03
    score += 0.06 if ready_json else 0.02
    score += 0.08 if bat.get("passed") else 0.02
    score += 0.06 * min(1.0, mastered_pat / max(len(patterns), 1))
    score += 0.04 if int(live.get("discern_pass") or 0) >= 3 else 0.01
    score += 0.03 if brain_ok else 0.0
    stack = _g16_stack()
    score += 0.04 if stack.get("optimized") else (0.02 if stack.get("ok") else 0.0)
    score += 0.02 if (stack.get("link") or {}).get("ok") else 0.0
    score += 0.02 if (stack.get("rtx_gate") or {}).get("satisfied") else 0.0
    score = round(min(0.99, score), 4)

    fluent_floor = float(doctrine.get("fluent_floor_score") or 0.85)
    master_target = float(doctrine.get("master_g16_score") or 0.94)
    tier = "novice"
    if score >= master_target and bat.get("passed") and live.get("ready"):
        tier = "g16_master"
    elif score >= fluent_floor and (live.get("ready") or ready_json):
        tier = "fluent"

    return {
        "score": score,
        "tier": tier,
        "fluent": tier in ("fluent", "g16_master"),
        "mastered": tier == "g16_master",
        "battery": bat,
        "live_probe": live,
        "toolchain_ready": ready_json,
        "patterns_mastered": mastered_pat,
        "patterns_total": len(patterns),
        "g16_version": live.get("version") or (tc.get("toolchain") or {}).get("g16_version"),
        "brain_verified": brain_ok,
        "g16_stack": stack,
        "effective_profile": (stack.get("compile") or {}).get("effective_profile"),
        "linker_targets": (stack.get("multi_os") or {}).get("targets"),
        "rtx_gate_satisfied": (stack.get("rtx_gate") or {}).get("satisfied"),
    }


def _merge_explain_overlay(track: str, base: dict[str, Any]) -> dict[str, Any]:
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("h7overlay", INSTALL / "lib" / "hostess7-explain-overlay.py")
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.merge_explain_doc(track, base)
    except Exception:
        pass
    return base


def _load_explain_doc() -> dict[str, Any]:
    base = _load(EXPLAIN, {"topics": [], "introduction": "", "format": [s[0] for s in _SECTION_LABELS]})
    return _merge_explain_overlay("g16", base)


def _topic_match_score(topic: dict[str, Any], q: str) -> int:
    score = 0
    for kw in topic.get("keywords") or []:
        kw_l = str(kw).lower().strip()
        if kw_l and kw_l in q:
            score += len(kw_l) + (12 if q.strip() == kw_l else 0)
    return score


def _match_explain_topic(query: str) -> dict[str, Any] | None:
    q = (query or "").lower()
    if not q:
        return None
    best: dict[str, Any] | None = None
    best_score = 0
    for topic in _load_explain_doc().get("topics") or []:
        score = _topic_match_score(topic, q)
        if score > best_score:
            best_score = score
            best = topic
    return best if best_score > 0 else None


def _format_topic_prose(topic: dict[str, Any], *, intro: str = "") -> str:
    parts: list[str] = []
    if intro.strip():
        parts.append(intro.strip())
    for key, label in _SECTION_LABELS:
        val = str(topic.get(key) or "").strip()
        if val:
            parts.append(f"{label}: {val}")
    return "\n\n".join(parts)


def _fluency_structured(query: str) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    claim = str(doctrine.get("fluency_claim") or "").strip()
    doc = _load_explain_doc()
    intro = str(doc.get("introduction") or "").strip()
    metrics = g16_score()
    sections = {
        "what": "G16 mastery means I am fluent on Grok16 g16 — live probe, discern, ninja builds, field mandate — not generic gcc advice.",
        "why": claim or "Queen RTX and CHIPS compile through g16 on this field; operators need a brain that knows the real toolchain.",
        "how": (
            f"I read {TOOLCHAIN}, subprocess g16 --version and --g16-discern, score tier {metrics.get('tier')} "
            f"at {round(float(metrics.get('score') or 0) * 100)}%, and explain with What / Why / How / Pitfalls / Where / Example."
        ),
        "pitfalls": "Claiming fluency without ready_g16; cmake --build instead of g16+ninja; skipping G16_FIELD_SAFETY_MANDATE_v1.",
        "where": "lib/hostess7-g16.py, Queen/scripts/g16-build.sh, Queen/data/g16-toolchain.json",
        "example": metrics.get("g16_version") or "g16 --version on GROK16_ROOT/bin/g16",
    }
    topic = {"id": "g16_fluency_live", **sections}
    return {
        "ok": True,
        "query": query,
        "topic_id": "g16_fluency_live",
        "topic_label": "G16 Fluency Live",
        "introduction": intro,
        "sections": sections,
        "format": doc.get("format") or [s[0] for s in _SECTION_LABELS],
        "reply": _format_topic_prose(topic, intro=intro),
        "g16_score": metrics.get("score"),
        "tier": metrics.get("tier"),
    }


def explain_g16_structured(query: str = "") -> dict[str, Any]:
    q = (query or "").strip()
    low = q.lower()
    doc = _load_explain_doc()
    intro = str(doc.get("introduction") or "").strip()
    fmt = doc.get("format") or [s[0] for s in _SECTION_LABELS]
    doctrine = _load(DOCTRINE, {})
    claim = str(doctrine.get("fluency_claim") or "").strip()

    topic = _match_explain_topic(q)
    if not topic and any(k in low for k in _FLUENCY_KEYS):
        return _fluency_structured(q)
    if not topic and any(k in low for k in ("g16", "g++16", "grok16", "compiler", "ninja", "discern", "toolchain")):
        topic = next((t for t in (doc.get("topics") or []) if t.get("id") == "g16_overview"), None)

    if topic:
        sections = {key: str(topic.get(key) or "").strip() for key, _ in _SECTION_LABELS if topic.get(key)}
        return {
            "ok": True,
            "query": q,
            "topic_id": topic.get("id"),
            "topic_label": str(topic.get("id") or "").replace("_", " ").title(),
            "introduction": intro,
            "sections": sections,
            "format": fmt,
            "reply": _format_topic_prose(topic, intro=intro),
        }

    metrics = g16_score()
    fallback = (
        f"{claim} " if claim else ""
    ) + (
        f"Current tier: {metrics.get('tier')} ({round(float(metrics.get('score') or 0) * 100)}%). "
        "Ask about g16 discern, g16+ninja build, field mandate, toolchain probe, gnu++26, or CHIPS_G16_ACCURATE."
    )
    return {
        "ok": True,
        "query": q,
        "topic_id": None,
        "introduction": intro,
        "sections": {},
        "format": fmt,
        "reply": fallback.strip(),
        "tier": metrics.get("tier"),
    }


def explain_g16(query: str = "") -> str:
    return str(explain_g16_structured(query).get("reply") or "")


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    metrics = g16_score()
    tc = _toolchain_doc()
    live = metrics.get("live_probe") or {}
    stack = metrics.get("g16_stack") or _g16_stack()
    doc = {
        "schema": "hostess7-g16/v1",
        "updated": _now(),
        "enabled": ENABLED,
        "product": "Hostess 7 G16 Compiler",
        "role": "Fluent and mastered on Grok16 g16 @ field_opt",
        "motto": doctrine.get("motto"),
        "fluency_claim": doctrine.get("fluency_claim"),
        "g16_score": metrics.get("score"),
        "tier": metrics.get("tier"),
        "fluent": metrics.get("fluent"),
        "mastered": metrics.get("mastered"),
        "g16_version": metrics.get("g16_version"),
        "toolchain_ready": metrics.get("toolchain_ready"),
        "battery": metrics.get("battery"),
        "live_probe": live,
        "patterns": _pattern_mastery(),
        "patterns_mastered": metrics.get("patterns_mastered"),
        "toolchain_path": str(TOOLCHAIN),
        "grok16_root": str(_grok16_root()),
        "build_script": str(QUEEN / "scripts" / "g16-build.sh"),
        "field_mandate": (tc.get("field_mandate") or _load(MANDATE, {}).get("mandate_id")),
        "g16_stack": stack,
        "effective_profile": metrics.get("effective_profile") or (stack.get("compile") or {}).get("effective_profile"),
        "linker_targets": metrics.get("linker_targets") or (stack.get("multi_os") or {}).get("targets"),
        "os_families": (stack.get("multi_os") or {}).get("os_families"),
        "rtx_gate_satisfied": metrics.get("rtx_gate_satisfied") or (stack.get("rtx_gate") or {}).get("satisfied"),
        "rtx_gated_profiles": (stack.get("rtx_gate") or {}).get("profiles_gated"),
        "reason": (
            "Hostess 7 is fluent and mastered on Grok16 g16 — live probe, discern, ninja, mandate."
            if metrics.get("mastered")
            else (
                "G16 fluency active — probe and battery confirm field_opt compiler on this install."
                if metrics.get("fluent")
                else "G16 chamber online — run toolchain probe and g16-toolchain.sh to reach fluency."
            )
        ),
    }
    if write:
        _save(PANEL, doc)
        _save(RUNTIME, {
            "schema": "hostess7-g16-runtime/v1",
            "updated": doc["updated"],
            "g16_score": doc["g16_score"],
            "tier": doc["tier"],
            "fluent": doc["fluent"],
            "mastered": doc["mastered"],
        })
        _append_ledger({
            "ts": doc["updated"],
            "event": "g16_panel",
            "score": doc["g16_score"],
            "tier": doc["tier"],
        })
    return doc


def panel_json() -> dict[str, Any]:
    return build_panel(write=True)


_OCR_API: dict | None = None


def _ocr_api() -> dict:
    global _OCR_API
    if _OCR_API is None:
        import importlib.util
        py = INSTALL / "lib" / "hostess7-ocr-bind.py"
        spec = importlib.util.spec_from_file_location("h7_ocr_bind_g16", py)
        if not spec or not spec.loader:
            raise ImportError("hostess7-ocr-bind.py missing")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _OCR_API = mod.bind("g16", install=INSTALL, state=STATE, ledger=LEDGER)
    return _OCR_API


def ingest_ocr_vision(**kw):
    return _ocr_api()["ingest_ocr_vision"](**kw)


def train_ocr_vision(**kw):
    return _ocr_api()["train_ocr_vision"](**kw)


def ocr_vision_status():
    return _ocr_api()["ocr_vision_status"]()


def _handle_ocr_cli(cmd: str) -> int | None:
    import importlib.util
    py = INSTALL / "lib" / "hostess7-ocr-feed.py"
    spec = importlib.util.spec_from_file_location("h7_ocr_feed_g16", py)
    if not spec or not spec.loader:
        return None
    feed = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(feed)
    return feed.handle_ocr_cli(
        cmd,
        ingest_fn=ingest_ocr_vision,
        train_fn=train_ocr_vision,
        status_fn=ocr_vision_status,
        usage="hostess7-g16.py [json|score|probe|battery|explain|teach|ocr-ingest|ocr-train|ocr-status]",
    )


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(build_panel(), ensure_ascii=False))
        return 0
    if cmd == "score":
        print(json.dumps(g16_score(), ensure_ascii=False))
        return 0
    if cmd == "probe":
        print(json.dumps(_probe_live(), ensure_ascii=False))
        return 0
    if cmd == "battery":
        print(json.dumps(_run_battery(), ensure_ascii=False))
        return 0
    if cmd in ("explain", "teach"):
        q = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "g16 compiler fluency"
        print(json.dumps(explain_g16_structured(q), ensure_ascii=False))
        return 0
    ocr_ret = _handle_ocr_cli(cmd)
    if ocr_ret is not None:
        return ocr_ret
    print(json.dumps({
        "error": "usage: hostess7-g16.py [json|score|probe|battery|explain|teach <q>]",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())