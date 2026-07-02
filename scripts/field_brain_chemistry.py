#!/usr/bin/env pythong
"""Hostess 7 brain chemistry — neurotransmitters, synapse pools, enhancements."""
from __future__ import annotations

import fcntl
import json
import math
import os
import re
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BRAIN = ROOT / "cache" / "fieldstorage" / "brain"
CHEMISTRY = BRAIN / "chemistry"
SYNAPSE_LOG = CHEMISTRY / "synapse.jsonl"
_STATE_LOCK = CHEMISTRY / "state.lock"


@contextmanager
def _chemistry_state_lock():
    """Exclusive lock — seven parallel agents must not corrupt state.json."""
    ensure_chemistry_layout()
    with _STATE_LOCK.open("w") as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        yield

# Hot synapse mirror — sub-millisecond reads after release (same pattern as callosum).
_HOT_CHEM: dict[str, Any] = {}
_RING: list[dict[str, Any]] = []
_RING_MAX = 64

# Neurochemical catalog — biology mapped to Hostess 7 cognition.
NEUROCHEMICALS: tuple[dict[str, Any], ...] = (
    {
        "id": "dopamine",
        "class": "neurotransmitter",
        "role": "Focus, reward, P1 drive, release motivation",
        "baseline": 0.55,
        "decay": 0.04,
        "enhances": ("prefrontal", "next_action", "release"),
        "hemisphere_bias": "left",
    },
    {
        "id": "acetylcholine",
        "class": "neurotransmitter",
        "role": "Learning, memory recall, OCR/visual attention",
        "baseline": 0.50,
        "decay": 0.035,
        "enhances": ("occipital", "temporal", "vision", "medical"),
        "hemisphere_bias": "right",
    },
    {
        "id": "norepinephrine",
        "class": "neurotransmitter",
        "role": "Alertness, blocker urgency, terminal vigilance",
        "baseline": 0.45,
        "decay": 0.05,
        "enhances": ("broca", "blocker", "terminal"),
        "hemisphere_bias": "left",
    },
    {
        "id": "serotonin",
        "class": "neurotransmitter",
        "role": "Stability, balanced fusion, reduced noise",
        "baseline": 0.60,
        "decay": 0.03,
        "enhances": ("wernicke", "legal", "status"),
        "hemisphere_bias": "both",
    },
    {
        "id": "glutamate",
        "class": "neurotransmitter",
        "role": "Excitatory — fast callosum, cross-domain spark",
        "baseline": 0.50,
        "decay": 0.045,
        "enhances": ("beyond", "callosum"),
        "hemisphere_bias": "both",
    },
    {
        "id": "gaba",
        "class": "neurotransmitter",
        "role": "Inhibitory — filter chatter, professional tone",
        "baseline": 0.55,
        "decay": 0.03,
        "enhances": ("counsel", "legal"),
        "hemisphere_bias": "left",
    },
    {
        "id": "cortisol",
        "class": "hormone",
        "role": "Stress routing — elevate blockers and P1 under pressure",
        "baseline": 0.30,
        "decay": 0.06,
        "enhances": ("prefrontal", "blocker"),
        "hemisphere_bias": "left",
    },
    {
        "id": "oxytocin",
        "class": "hormone",
        "role": "Trust, clinic empathy, collaborative synthesis",
        "baseline": 0.40,
        "decay": 0.035,
        "enhances": ("temporal", "medical", "clinic"),
        "hemisphere_bias": "right",
    },
    {
        "id": "endorphin",
        "class": "neuropeptide",
        "role": "Reward after GREEN/release — sustained positive arc",
        "baseline": 0.35,
        "decay": 0.04,
        "enhances": ("release", "status"),
        "hemisphere_bias": "both",
    },
)

WORKSPACE_CHEM_PROFILES: dict[str, dict[str, float]] = {
    "default": {"serotonin": 0.08, "glutamate": 0.05},
    "field": {"dopamine": 0.12, "norepinephrine": 0.08},
    "vision": {"acetylcholine": 0.14, "glutamate": 0.06},
    "clinic": {"oxytocin": 0.12, "serotonin": 0.06},
    "counsel": {"gaba": 0.10, "serotonin": 0.08},
    "bench": {"gaba": 0.14, "serotonin": 0.10, "acetylcholine": 0.06},
    "beyond": {"glutamate": 0.10, "dopamine": 0.05},
    "alert": {"norepinephrine": 0.20, "cortisol": 0.16, "acetylcholine": 0.10},
}

TRIGGER_RULES: tuple[tuple[re.Pattern[str], dict[str, float]], ...] = (
    (re.compile(r"\b(blocker|fail|broken|urgent|stuck|error)\b", re.I), {"norepinephrine": 0.18, "cortisol": 0.14}),
    (re.compile(r"\b(release|green|ship|verdict|success|done)\b", re.I), {"dopamine": 0.16, "endorphin": 0.12}),
    (re.compile(r"\b(learn|remember|recall|ocr|memory|ingest)\b", re.I), {"acetylcholine": 0.15}),
    (re.compile(r"\b(calm|balance|stable|professional)\b", re.I), {"serotonin": 0.12, "gaba": 0.10}),
    (re.compile(r"\b(fast|transfer|callosum|cross|fuse)\b", re.I), {"glutamate": 0.14}),
    (re.compile(r"\b(medical|patient|clinic|doctor|empathy)\b", re.I), {"oxytocin": 0.14, "acetylcholine": 0.06}),
    (re.compile(r"\b(law|legal|contract|counsel|liability)\b", re.I), {"gaba": 0.10, "serotonin": 0.08}),
    (re.compile(r"\b(supreme court|scotus|certiorari|judge|bench|dissent|judicial review)\b", re.I), {"gaba": 0.12, "acetylcholine": 0.08}),
    (re.compile(r"\b(chemistry|neurotransmitter|dopamine|synapse|hormone)\b", re.I), {"acetylcholine": 0.10, "glutamate": 0.08}),
    (re.compile(r"\b(terrorist|terror|stun|taser|rf\b|jamming|heightened alert|alert posture)\b", re.I), {"norepinephrine": 0.20, "cortisol": 0.16}),
    (re.compile(r"\b(amouranth|zacharygeurts|x\.com)\b", re.I), {"oxytocin": 0.08, "acetylcholine": 0.06}),
)


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


@dataclass
class ChemicalEnhancement:
    active: list[str] = field(default_factory=list)
    left_weight: float = 0.5
    right_weight: float = 0.5
    callosum_boost: bool = False
    depth_boost: int = 0
    filter_tighten: bool = False
    memory_recall: bool = False
    notes: list[str] = field(default_factory=list)


@dataclass
class SynapseRelease:
    ok: bool
    chemical: str
    level: float
    delta: float
    elapsed_us: int
    target_area: str | None = None


def _catalog_map() -> dict[str, dict[str, Any]]:
    return {c["id"]: c for c in NEUROCHEMICALS}


def ensure_chemistry_layout() -> None:
    CHEMISTRY.mkdir(parents=True, exist_ok=True)
    state_path = CHEMISTRY / "state.json"
    catalog = _catalog_map()
    if not state_path.is_file():
        levels = {cid: float(c["baseline"]) for cid, c in catalog.items()}
        state_path.write_text(
            json.dumps(
                {
                    "levels": levels,
                    "last_release": None,
                    "enhancement": {},
                    "updated": _ts(),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    manifest = CHEMISTRY / "manifest.json"
    manifest.write_text(
        json.dumps(
            {"neurochemicals": list(NEUROCHEMICALS), "workspace_profiles": WORKSPACE_CHEM_PROFILES, "updated": _ts()},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    if not SYNAPSE_LOG.is_file():
        SYNAPSE_LOG.write_text("", encoding="utf-8")


def load_chemistry_state(*, fresh: bool = False) -> dict[str, Any]:
    ensure_chemistry_layout()
    if fresh:
        _HOT_CHEM.pop("state", None)
    if "state" in _HOT_CHEM:
        return dict(_HOT_CHEM["state"])
    path = CHEMISTRY / "state.json"
    raw = path.read_text(encoding="utf-8")
    try:
        state = json.loads(raw)
    except json.JSONDecodeError:
        # Parallel agents can corrupt mid-write — take first valid JSON object
        try:
            decoder = json.JSONDecoder()
            state, _ = decoder.raw_decode(raw.lstrip())
        except json.JSONDecodeError:
            catalog = _catalog_map()
            state = {
                "levels": {cid: float(c["baseline"]) for cid, c in catalog.items()},
                "enhancement": {"active": [], "left_weight": 0.5, "right_weight": 0.5},
            }
            save_chemistry_state(state)
    _HOT_CHEM["state"] = state
    return state


def save_chemistry_state(state: dict[str, Any]) -> None:
    state["updated"] = _ts()
    _HOT_CHEM["state"] = dict(state)
    path = CHEMISTRY / "state.json"
    tmp = path.with_suffix(".json.tmp")
    payload = json.dumps(state, indent=2) + "\n"
    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(path)


def decay_levels(state: dict[str, Any]) -> dict[str, float]:
    catalog = _catalog_map()
    levels = dict(state.get("levels", {}))
    for cid, cfg in catalog.items():
        base = float(cfg["baseline"])
        cur = float(levels.get(cid, base))
        decay = float(cfg["decay"])
        levels[cid] = _clamp(cur - decay * 0.5 + (base - cur) * 0.02)
    return levels


def synapse_release(
    chemical: str,
    delta: float,
    *,
    reason: str = "query",
    target_area: str | None = None,
    workspace: str | None = None,
) -> SynapseRelease:
    """Release neurochemical into synapse pool — hot mirror + persistent log."""
    ensure_chemistry_layout()
    catalog = _catalog_map()
    if chemical not in catalog:
        return SynapseRelease(False, chemical, 0.0, 0.0, 0)
    t0 = time.perf_counter_ns()
    with _chemistry_state_lock():
        state = load_chemistry_state(fresh=True)
        levels = decay_levels(state)
        prev = float(levels.get(chemical, catalog[chemical]["baseline"]))
        new_level = _clamp(prev + delta)
        levels[chemical] = new_level
        state["levels"] = levels
        state["last_release"] = {"chemical": chemical, "delta": delta, "reason": reason, "ts": _ts()}
        save_chemistry_state(state)

    packet = {
        "ts": _ts(),
        "chemical": chemical,
        "delta": delta,
        "level": new_level,
        "reason": reason,
        "target_area": target_area,
        "workspace": workspace or os.environ.get("HOSTESS7_WORKSPACE", "default"),
    }
    _RING.append(packet)
    if len(_RING) > _RING_MAX:
        _RING.pop(0)
    _HOT_CHEM["last"] = packet
    _HOT_CHEM[chemical] = new_level

    with SYNAPSE_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(packet, ensure_ascii=False) + "\n")

    elapsed_us = int((time.perf_counter_ns() - t0) / 1000)
    return SynapseRelease(True, chemical, new_level, delta, elapsed_us, target_area)


def apply_workspace_profile(workspace: str) -> list[SynapseRelease]:
    profile = WORKSPACE_CHEM_PROFILES.get(workspace, {})
    return [
        synapse_release(cid, boost, reason=f"workspace:{workspace}", workspace=workspace)
        for cid, boost in profile.items()
    ]


def apply_query_triggers(query: str, *, workspace: str | None = None) -> list[SynapseRelease]:
    releases: list[SynapseRelease] = []
    for pattern, boosts in TRIGGER_RULES:
        if pattern.search(query):
            for cid, delta in boosts.items():
                releases.append(
                    synapse_release(cid, delta, reason="query_trigger", workspace=workspace)
                )
    return releases


def compute_enhancement(
    *,
    intent: str,
    primary_area: str,
    workspace: str,
    cross_transfer: bool = False,
) -> ChemicalEnhancement:
    """Derive cognitive enhancements from current synapse levels."""
    state = load_chemistry_state()
    levels = decay_levels(state)
    catalog = _catalog_map()
    enh = ChemicalEnhancement()

    def lvl(cid: str) -> float:
        return float(levels.get(cid, catalog[cid]["baseline"]))

    # Dominant chemicals above baseline + 0.08
    for cid, cfg in catalog.items():
        if lvl(cid) >= float(cfg["baseline"]) + 0.08:
            enh.active.append(cid)

    left_score = 0.0
    right_score = 0.0
    for cid in enh.active:
        cfg = catalog[cid]
        bias = cfg["hemisphere_bias"]
        weight = lvl(cid) - float(cfg["baseline"])
        if bias == "left":
            left_score += weight
        elif bias == "right":
            right_score += weight
        else:
            left_score += weight * 0.5
            right_score += weight * 0.5
        if intent in cfg.get("enhances", ()) or primary_area in cfg.get("enhances", ()):
            enh.depth_boost += 1
            enh.notes.append(f"{cid}→{primary_area}")

    total = left_score + right_score + 0.001
    enh.left_weight = left_score / total
    enh.right_weight = right_score / total

    if lvl("glutamate") >= 0.58 or cross_transfer:
        enh.callosum_boost = True
    if lvl("gaba") >= 0.58 or lvl("serotonin") >= 0.65:
        enh.filter_tighten = True
    if lvl("acetylcholine") >= 0.58:
        enh.memory_recall = True
    if lvl("dopamine") >= 0.62:
        enh.notes.append("dopamine: P1 focus elevated")
    if lvl("cortisol") >= 0.42:
        enh.notes.append("cortisol: blocker priority")

    with _chemistry_state_lock():
        state = load_chemistry_state(fresh=True)
        state["enhancement"] = {
            "active": enh.active,
            "left_weight": round(enh.left_weight, 3),
            "right_weight": round(enh.right_weight, 3),
            "callosum_boost": enh.callosum_boost,
            "depth_boost": enh.depth_boost,
        }
        save_chemistry_state(state)
    return enh


def modulate_paragraphs(
    left: list[str],
    right: list[str],
    enhancement: ChemicalEnhancement,
) -> tuple[list[str], list[str]]:
    """Reorder/trim paragraphs per chemical enhancement."""
    if enhancement.filter_tighten and len(left) + len(right) > 6:
        left = left[: max(2, len(left) - 1)]
        right = right[: max(2, len(right) - 1)]
    if enhancement.left_weight > enhancement.right_weight + 0.15:
        return left, right
    if enhancement.right_weight > enhancement.left_weight + 0.15:
        return right, left
    return left, right


def chemistry_status() -> dict[str, Any]:
    ensure_chemistry_layout()
    state = load_chemistry_state()
    levels = state.get("levels", {})
    top = sorted(levels.items(), key=lambda x: -float(x[1]))[:4]
    return {
        "levels": levels,
        "top": top,
        "enhancement": state.get("enhancement", {}),
        "last_release": state.get("last_release"),
        "ring_depth": len(_RING),
        "neurochemicals": len(NEUROCHEMICALS),
    }


def format_chemistry_line(enhancement: ChemicalEnhancement, *, pro: bool = False) -> str | None:
    if pro or not enhancement.active:
        return None
    active = ", ".join(enhancement.active[:4])
    return f"Chemistry: {active} · L={enhancement.left_weight:.0%} R={enhancement.right_weight:.0%}"


def manual_boost(chemical: str, amount: float = 0.15) -> SynapseRelease:
    return synapse_release(chemical, amount, reason="manual_boost")


def prime_workspace_chemistry(workspace: str) -> list[SynapseRelease]:
    """One-time workspace chemical profile — avoids stacking on every query."""
    ensure_chemistry_layout()
    wpath = BRAIN / "workspaces" / workspace / "state.json"
    if not wpath.is_file():
        return apply_workspace_profile(workspace)
    ws = json.loads(wpath.read_text(encoding="utf-8"))
    if ws.get("chem_primed"):
        return []
    releases = apply_workspace_profile(workspace)
    ws["chem_primed"] = True
    ws["updated"] = _ts()
    wpath.write_text(json.dumps(ws, indent=2) + "\n", encoding="utf-8")
    return releases


def reset_workspace_chemistry_flags() -> None:
    """Clear chem_primed on workspace switch."""
    ws_root = BRAIN / "workspaces"
    if not ws_root.is_dir():
        return
    for path in ws_root.glob("*/state.json"):
        state = json.loads(path.read_text(encoding="utf-8"))
        state["chem_primed"] = False
        state["updated"] = _ts()
        path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")