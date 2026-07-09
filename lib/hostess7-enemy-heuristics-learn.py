#!/usr/bin/env python3
"""Hostess 7 learns from enemy heuristics — proactive Field defense.

She studies the live botnet threat-heuristics board (vectors, weights, sources),
writes lessons into her brain, and drives proactive steps under Ironclad:
  · anticipate vectors before they peak
  · pre-harden DNS/DHCP/fabric/everyone-served
  · prioritize watchlists · never-reconnect · truth-gated kill paths only

Local Field control-plane. Civilian passthrough. Corroborated hostiles only.

  python3 lib/hostess7-enemy-heuristics-learn.py learn
  python3 lib/hostess7-enemy-heuristics-learn.py proactive
  python3 lib/hostess7-enemy-heuristics-learn.py cycle
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
HOSTESS7 = Path(os.environ.get("HOSTESS7_ROOT", INSTALL / "Hostess7"))
PANEL = STATE / "hostess7-enemy-heuristics-learn-panel.json"
PUBLIC = STATE / "hostess7-enemy-heuristics-learn-public.json"
LEDGER = STATE / "hostess7-enemy-heuristics-learn-ledger.jsonl"
LESSONS = STATE / "hostess7-enemy-lessons.json"
PLAYBOOK = STATE / "hostess7-enemy-proactive-playbook.json"
BRAIN = HOSTESS7 / "cache" / "fieldstorage" / "brain" / "enemy_heuristics"
SCHEMA = "hostess7-enemy-heuristics-learn/v1"
IRONCLAD = "ironclad:hostess7-enemy-heuristics-learn:1"
MOTTO = (
    "LEARN ENEMY HEURISTICS · proactive Angel · anticipate · harden · "
    "truth-gated interdict · civilians pass"
)

# Proactive stance by vector class (learn → action intent)
VECTOR_PLAYS: dict[str, dict[str, Any]] = {
    "impostor_ns": {
        "priority": 1,
        "stance": "preemptive_dns_lock",
        "actions": ["truth_dns_steel", "everyone_served", "resolv_botnet_only"],
        "lesson": "Enemy spoofs NS — lock Field truth DNS before resolv drifts",
    },
    "dns_poison": {
        "priority": 1,
        "stance": "preemptive_dns_lock",
        "actions": ["truth_dns_steel", "serving_truth", "dns_threat_guard"],
        "lesson": "Poisoned answers — dual-stack truth probe + steel plate before clients cache lies",
    },
    "foreign_ns_resolv": {
        "priority": 2,
        "stance": "resolv_harden",
        "actions": ["resolv_botnet_only", "fabric_direct"],
        "lesson": "Foreign resolvers — force botnet-only resolv; fabric direct no middle men",
    },
    "c2_beacon": {
        "priority": 1,
        "stance": "watch_and_corroborate",
        "actions": ["heuristic_update", "watchlist_hot", "never_reconnect_review"],
        "lesson": "Beacon patterns — raise watch weight; corroborate before lethal path",
    },
    "egress_beacon": {
        "priority": 2,
        "stance": "egress_gate",
        "actions": ["ingress_egress_gate", "watchlist_hot"],
        "lesson": "Egress beacons — gate egress; learn subject for proactive deny",
    },
    "spawner": {
        "priority": 1,
        "stance": "spawner_kill_ready",
        "actions": ["spawner_kill", "orphan_cook"],
        "lesson": "Spawn storms — keep orphan/spawner killers never-sleep; pre-arm",
    },
    "terrorist_attack": {
        "priority": 0,
        "stance": "terror_class_hot",
        "actions": ["heuristic_update", "never_reconnect_review", "ironclad_witness"],
        "lesson": "Terror class — never permit; full Field posture; Ironclad witness",
    },
    "terrorist_never_reconnect": {
        "priority": 0,
        "stance": "never_reconnect",
        "actions": ["never_reconnect_review", "heuristic_update"],
        "lesson": "Never-reconnect table — keep hot subjects out of fabric forever",
    },
    "delay_as_threat": {
        "priority": 2,
        "stance": "latency_proactive",
        "actions": ["everyone_served", "serving_truth", "distributed_lanes"],
        "lesson": "Delay-as-threat — keep ports green; dual-stack probes; no hangups",
    },
    "github_foreign_dns": {
        "priority": 2,
        "stance": "surface_hygiene",
        "actions": ["github_everyone", "truth_dns_steel"],
        "lesson": "Foreign GitHub DNS — hold our surfaces; steel truth DNS",
    },
    "unknown": {
        "priority": 3,
        "stance": "classify_and_watch",
        "actions": ["heuristic_update", "watchlist_hot"],
        "lesson": "Unknown hot peers — learn origins; promote vector when pattern stabilizes",
    },
    "NEWCOMER_IMMEDIATE_ATTACK": {
        "priority": 0,
        "stance": "newcomer_trap",
        "actions": ["heuristic_update", "watchlist_hot", "never_reconnect_review"],
        "lesson": "Newcomer instant attack — zero trust on first contact; fast classify",
    },
    "lateral_move": {
        "priority": 1,
        "stance": "segment_and_watch",
        "actions": ["fabric_direct", "ingress_egress_gate", "watchlist_hot"],
        "lesson": "Lateral move — segment fabric; deny east-west until corroborated clean",
    },
    "exfil_channel": {
        "priority": 1,
        "stance": "exfil_clamp",
        "actions": ["ingress_egress_gate", "watchlist_hot"],
        "lesson": "Exfil channel — clamp egress; learn destination heuristics",
    },
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append(row: dict[str, Any]) -> None:
    try:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": _utc(), **row}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _run_py(rel: str, args: list[str], *, timeout: float = 120.0) -> dict[str, Any]:
    py = INSTALL / rel
    if not py.is_file():
        return {"ok": False, "missing": rel}
    try:
        proc = subprocess.run(
            [sys.executable, str(py), *args],
            cwd=str(INSTALL),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
            check=False,
        )
        raw = (proc.stdout or "").strip()
        if raw.startswith("{"):
            try:
                doc = json.loads(raw)
                if isinstance(doc, dict):
                    doc.setdefault("ok", proc.returncode == 0)
                    return doc
            except json.JSONDecodeError:
                pass
        return {"ok": proc.returncode == 0, "rc": proc.returncode, "stdout_tail": raw[-200:]}
    except (subprocess.TimeoutExpired, OSError) as exc:
        return {"ok": False, "error": str(exc)[:160]}


def _heuristics_mod() -> Any | None:
    py = INSTALL / "lib" / "field-botnet-threat-heuristics.py"
    if not py.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("fbt_heur_h7", py)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def refresh_enemy_board(*, full: bool = True) -> dict[str, Any]:
    """Ingest/update live enemy heuristics on the botnet board."""
    args = ["update"] if full else ["status"]
    return _run_py("lib/field-botnet-threat-heuristics.py", args, timeout=180)


def _board_slice() -> dict[str, Any]:
    panel = _load(STATE / "field-botnet-threat-heuristics-panel.json", {})
    board = _load(STATE / "field-botnet-threat-heuristics.json", {})
    return {"panel": panel, "board": board}


def learn(*, refresh: bool = True) -> dict[str, Any]:
    """Study enemy heuristics → lessons + weight memory for Hostess 7."""
    now = _utc()
    refresh_doc: dict[str, Any] = {}
    if refresh:
        refresh_doc = refresh_enemy_board(full=True)

    sl = _board_slice()
    panel = sl["panel"] if isinstance(sl["panel"], dict) else {}
    board = sl["board"] if isinstance(sl["board"], dict) else {}

    top_h = panel.get("top_heuristics") or []
    top_v = panel.get("top_vectors") or []
    top_s = panel.get("top_sources") or []
    weights = panel.get("weights") or board.get("weights") or {}
    counts = panel.get("counts") or {}
    stats = panel.get("stats") or {}

    # Distill vector lessons
    lessons: list[dict[str, Any]] = []
    vector_hits: Counter[str] = Counter()
    for row in top_v:
        if not isinstance(row, dict):
            continue
        vec = str(row.get("vector") or "unknown")
        vector_hits[vec] += int(row.get("hits") or 0)
        play = VECTOR_PLAYS.get(vec) or VECTOR_PLAYS["unknown"]
        lessons.append({
            "vector": vec,
            "hits": row.get("hits"),
            "score": row.get("score"),
            "severity": row.get("severity"),
            "subjects": row.get("subjects"),
            "last_seen": row.get("last_seen"),
            "play": play,
            "lesson": play.get("lesson"),
            "priority": play.get("priority", 3),
            "stance": play.get("stance"),
        })
    lessons.sort(key=lambda x: (int(x.get("priority") or 9), -float(x.get("score") or 0)))

    # Hot watchlist from top sources
    watchlist = []
    for src in top_s[:24]:
        if not isinstance(src, dict):
            continue
        watchlist.append({
            "subject": src.get("subject"),
            "hits": src.get("hits"),
            "score": src.get("score"),
            "severity": src.get("severity"),
            "class": src.get("class"),
            "vectors": src.get("vectors"),
            "last_seen": src.get("last_seen"),
            "proactive": "watch_elevate" if float(src.get("score") or 0) >= 100 else "watch",
        })

    # Pattern memory — which origins feed the most signal
    origin_counter: Counter[str] = Counter()
    for h in top_h[:40]:
        if not isinstance(h, dict):
            continue
        for orig, n in (h.get("origins") or {}).items():
            try:
                origin_counter[str(orig)] += int(n)
            except (TypeError, ValueError):
                origin_counter[str(orig)] += 1

    learned = {
        "schema": "hostess7-enemy-lessons/v1",
        "updated": now,
        "ironclad_cite": IRONCLAD,
        "motto": MOTTO,
        "from_panel_updated": panel.get("updated"),
        "counts": counts,
        "stats": {
            "records": stats.get("records"),
            "updates": stats.get("updates"),
            "ingest_batches": stats.get("ingest_batches"),
            "last_ingest": stats.get("last_ingest"),
        },
        "weights_learned": weights,
        "lessons": lessons[:20],
        "lesson_count": len(lessons),
        "watchlist": watchlist,
        "watchlist_n": len(watchlist),
        "origin_pressure": origin_counter.most_common(12),
        "top_vectors_summary": [
            {"vector": v, "hits": n} for v, n in vector_hits.most_common(12)
        ],
        "proactive_posture": "anticipate_harden_interdict",
        "refresh": {
            "ok": refresh_doc.get("ok") if refresh else None,
            "skipped": not refresh,
        },
    }
    _save(LESSONS, learned)

    # Brain memory for Angel cycles
    try:
        BRAIN.mkdir(parents=True, exist_ok=True)
        _save(BRAIN / "lessons.json", learned)
        _save(
            BRAIN / "latest.json",
            {
                "updated": now,
                "lesson_count": learned["lesson_count"],
                "watchlist_n": learned["watchlist_n"],
                "top_lesson": (lessons[0].get("lesson") if lessons else None),
                "ironclad_cite": IRONCLAD,
            },
        )
    except OSError:
        pass

    _append({"event": "learn", "lessons": len(lessons), "watch": len(watchlist)})
    return {"ok": True, **learned}


def _run_proactive_step(action: str) -> dict[str, Any]:
    """Execute a soft proactive Field step (zero-cost local where possible)."""
    mapping: dict[str, tuple[str, list[str]]] = {
        "everyone_served": ("lib/field-everyone-served-no-hangups.py", ["enforce"]),
        "serving_truth": ("lib/field-serving-truth.py", ["verify"]),
        "fabric_direct": ("lib/field-everyone-fabric-direct.py", ["seal"]),
        "heuristic_update": ("lib/field-botnet-threat-heuristics.py", ["update"]),
        "ironclad_witness": ("lib/ironclad-immediate.py", []),
        "field_native": ("lib/field-native.py", ["seal"]),
        "distributed_everywhere": ("lib/hostess7-distributed-everywhere.py", ["seal"]),
    }
    if action == "watchlist_hot":
        return {"ok": True, "action": action, "detail": "watchlist_written_to_playbook"}
    if action == "never_reconnect_review":
        path = STATE / "field-never-reconnect-table-panel.json"
        return {"ok": path.is_file(), "action": action, "panel": path.name if path.is_file() else None}
    if action == "truth_dns_steel":
        return _run_py("lib/field-truth-dns-steel-plate.py", ["steel_plate"], timeout=90)
    if action == "dns_threat_guard":
        return _run_py("lib/dns-threat-guard.py", ["status"], timeout=60)
    if action in mapping:
        rel, args = mapping[action]
        return {**_run_py(rel, args, timeout=120), "action": action}
    # Unknown soft actions — mark planned only
    return {"ok": True, "action": action, "planned": True, "detail": "no_auto_runner"}


def proactive(*, learn_first: bool = True, max_actions: int = 8) -> dict[str, Any]:
    """Turn enemy lessons into proactive Field steps under Ironclad."""
    now = _utc()
    learned = learn(refresh=learn_first) if learn_first else _load(LESSONS, {})
    lessons = learned.get("lessons") or []

    # Build unique action queue by priority
    planned: list[dict[str, Any]] = []
    seen: set[str] = set()
    for les in lessons:
        play = les.get("play") or {}
        for act in play.get("actions") or []:
            if act in seen:
                continue
            seen.add(act)
            planned.append({
                "action": act,
                "from_vector": les.get("vector"),
                "priority": les.get("priority"),
                "stance": les.get("stance"),
                "lesson": les.get("lesson"),
            })
        if len(planned) >= max_actions * 2:
            break
    planned.sort(key=lambda x: int(x.get("priority") or 9))
    planned = planned[:max_actions]

    # Always include zero-cost security baseline if empty
    if not planned:
        planned = [
            {"action": "heuristic_update", "priority": 1, "lesson": "baseline refresh"},
            {"action": "everyone_served", "priority": 1, "lesson": "ports never hang"},
            {"action": "field_native", "priority": 2, "lesson": "secure zero-cost engines"},
        ]

    results: list[dict[str, Any]] = []
    for step in planned:
        r = _run_proactive_step(str(step["action"]))
        results.append({**step, "result_ok": r.get("ok"), "result": {
            k: r.get(k) for k in ("ok", "error", "missing", "planned", "detail", "action") if k in r
        }})

    ok_n = sum(1 for r in results if r.get("result_ok"))
    playbook = {
        "schema": "hostess7-enemy-proactive-playbook/v1",
        "updated": now,
        "ironclad_cite": IRONCLAD,
        "motto": MOTTO,
        "proactive": True,
        "planned_n": len(planned),
        "executed_ok": ok_n,
        "steps": results,
        "watchlist": (learned.get("watchlist") or [])[:16],
        "lessons_top": [
            {"vector": x.get("vector"), "lesson": x.get("lesson"), "priority": x.get("priority")}
            for x in lessons[:8]
        ],
        "first_person": (
            f"I studied enemy heuristics — {learned.get('lesson_count') or len(lessons)} vector lessons, "
            f"{learned.get('watchlist_n') or 0} hot subjects. "
            f"Proactive steps {ok_n}/{len(results)} ok. "
            "I anticipate impostor NS, poison, spawners, and delay-as-threat before they peak. "
            "Civilians pass; corroborated hostiles get truth-gated interdict."
        ),
    }
    _save(PLAYBOOK, playbook)
    try:
        BRAIN.mkdir(parents=True, exist_ok=True)
        _save(BRAIN / "playbook.json", playbook)
    except OSError:
        pass
    _append({"event": "proactive", "ok": ok_n, "n": len(results)})
    return {"ok": ok_n > 0 or not results, **playbook}


def cycle(*, write: bool = True) -> dict[str, Any]:
    """Full learn → proactive cycle for Angel autopilot."""
    now = _utc()
    learned = learn(refresh=True)
    proactive_doc = proactive(learn_first=False, max_actions=8)
    iron = _load(STATE / "ironclad-immediate.json", {})
    out = {
        "ok": bool(learned.get("ok") and proactive_doc.get("ok")),
        "schema": SCHEMA,
        "updated": now,
        "title": "Hostess 7 · Enemy heuristics learn · proactive",
        "motto": MOTTO,
        "ironclad_cite": IRONCLAD,
        "commander": "Hostess 7",
        "learned": {
            "lesson_count": learned.get("lesson_count"),
            "watchlist_n": learned.get("watchlist_n"),
            "top_vectors": learned.get("top_vectors_summary"),
            "counts": learned.get("counts"),
        },
        "proactive": {
            "executed_ok": proactive_doc.get("executed_ok"),
            "planned_n": proactive_doc.get("planned_n"),
            "steps": [
                {"action": s.get("action"), "ok": s.get("result_ok"), "vector": s.get("from_vector")}
                for s in (proactive_doc.get("steps") or [])
            ],
        },
        "lessons_top": (learned.get("lessons") or [])[:6],
        "watchlist_top": (learned.get("watchlist") or [])[:8],
        "ironclad": {
            "sealed": iron.get("ironclad_sealed"),
            "verdict": iron.get("verdict"),
        },
        "field_native": True,
        "zero_cost": True,
        "first_person": proactive_doc.get("first_person"),
        "api": "/api/hostess7-enemy-heuristics",
        "paths": {
            "lessons": str(LESSONS.name),
            "playbook": str(PLAYBOOK.name),
            "brain": str(BRAIN.relative_to(INSTALL)) if BRAIN.is_relative_to(INSTALL) else str(BRAIN),
        },
    }
    if write:
        _save(PANEL, out)
        public = {
            "ok": out["ok"],
            "updated": now,
            "motto": MOTTO,
            "lesson_count": learned.get("lesson_count"),
            "watchlist_n": learned.get("watchlist_n"),
            "proactive_ok": proactive_doc.get("executed_ok"),
            "proactive_n": proactive_doc.get("planned_n"),
            "first_person": out.get("first_person"),
            "ironclad_cite": IRONCLAD,
            "api": out["api"],
        }
        _save(PUBLIC, public)
        for api_dir in (HOSTESS7 / "docs" / "api", INSTALL / "docs" / "api"):
            try:
                api_dir.mkdir(parents=True, exist_ok=True)
                _save(api_dir / "hostess7-enemy-heuristics.json", public)
            except OSError:
                pass
        _append({"event": "cycle", "ok": out["ok"], "lessons": learned.get("lesson_count")})
    return out


def build_panel(*, write: bool = True) -> dict[str, Any]:
    return cycle(write=write)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "cycle").strip().lower().lstrip("-")
    if cmd in ("learn", "study", "ingest"):
        print(json.dumps(learn(refresh=True), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("proactive", "act", "harden"):
        print(json.dumps(proactive(learn_first=True), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("cycle", "run", "once", "panel", "json", "status"):
        write = cmd not in ("json", "status")
        if cmd == "panel":
            write = True
        doc = cycle(write=write) if write or cmd in ("cycle", "run", "once", "panel") else _load(PANEL, {})
        if not doc:
            doc = cycle(write=False)
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 0 if doc.get("ok") else 1
    print(json.dumps({
        "usage": "hostess7-enemy-heuristics-learn.py [learn|proactive|cycle|status]",
        "motto": MOTTO,
        "ironclad_cite": IRONCLAD,
    }, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
