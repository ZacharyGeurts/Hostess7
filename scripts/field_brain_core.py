#!/usr/bin/env pythong
"""Hostess 7 hemisphered brain — areas, workspaces, corpus callosum fast transfer."""
from __future__ import annotations

import fcntl
import json
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
HEMISPHERES = BRAIN / "hemispheres"
CALLOSUM = BRAIN / "callosum"
WORKSPACES = BRAIN / "workspaces"
AREAS_DIR = BRAIN / "areas"
RULING_DIR = BRAIN / "ruling"
RULING_POSTURE_PATH = RULING_DIR / "posture.json"
_BRIDGE_PATH = CALLOSUM / "bridge.json"
_BRIDGE_LOCK = CALLOSUM / "bridge.lock"


@contextmanager
def _callosum_bridge_lock():
    ensure_brain_layout()
    with _BRIDGE_LOCK.open("w") as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        yield


def _load_bridge(*, fresh: bool = False) -> dict[str, Any]:
    if fresh:
        _HOT_BRIDGE.pop("persisted", None)
    if "persisted" in _HOT_BRIDGE and not fresh:
        return dict(_HOT_BRIDGE["persisted"])
    ensure_brain_layout()
    if not _BRIDGE_PATH.is_file():
        bridge = {"packets": [], "last_transfer_us": 0, "updated": _ts()}
        _save_bridge(bridge)
        return bridge
    raw = _BRIDGE_PATH.read_text(encoding="utf-8")
    try:
        bridge = json.loads(raw)
    except json.JSONDecodeError:
        try:
            bridge, _ = json.JSONDecoder().raw_decode(raw.lstrip())
        except json.JSONDecodeError:
            bridge = {"packets": [], "last_transfer_us": 0, "updated": _ts()}
            _save_bridge(bridge)
    bridge.setdefault("packets", [])
    _HOT_BRIDGE["persisted"] = bridge
    return bridge


def _save_bridge(bridge: dict[str, Any]) -> None:
    bridge["updated"] = _ts()
    _HOT_BRIDGE["persisted"] = dict(bridge)
    tmp = _BRIDGE_PATH.with_suffix(".json.tmp")
    payload = json.dumps(bridge, indent=2) + "\n"
    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(_BRIDGE_PATH)

# Hot bridge — in-process mirror for sub-millisecond reads after transfer.
_HOT_BRIDGE: dict[str, Any] = {}
_RING: list[dict[str, Any]] = []
_RING_MAX = 64

HEMISPHERE_LEFT = "left"
HEMISPHERE_RIGHT = "right"
HEMISPHERE_BOTH = "both"

# Functional areas — human-brain analogues mapped to Hostess 7 domains.
BRAIN_AREAS: tuple[dict[str, Any], ...] = (
    {
        "id": "prefrontal",
        "name": "Prefrontal cortex",
        "hemisphere": HEMISPHERE_LEFT,
        "role": "Planning, priorities, release gates, verdicts",
        "intents": ("next_action", "release", "blocker", "status"),
    },
    {
        "id": "broca",
        "name": "Broca area",
        "hemisphere": HEMISPHERE_LEFT,
        "role": "Command language, shell, terminal, format syntax",
        "intents": ("terminal", "format", "code", "chips"),
    },
    {
        "id": "wernicke",
        "name": "Wernicke area",
        "hemisphere": HEMISPHERE_LEFT,
        "role": "Comprehension, legal parsing, architecture reading",
        "intents": ("legal", "judge", "architecture", "english"),
    },
    {
        "id": "parietal_l",
        "name": "Left parietal",
        "hemisphere": HEMISPHERE_LEFT,
        "role": "Structured code evidence, sequential analysis",
        "intents": ("general",),
    },
    {
        "id": "occipital",
        "name": "Occipital cortex",
        "hemisphere": HEMISPHERE_RIGHT,
        "role": "Vision, spatial mapping, OCR, 4K viewport",
        "intents": ("vision",),
    },
    {
        "id": "temporal",
        "name": "Temporal cortex",
        "hemisphere": HEMISPHERE_RIGHT,
        "role": "Pattern memory, medicine, emulation love",
        "intents": ("medical", "chips"),
    },
    {
        "id": "limbic",
        "name": "Limbic field",
        "hemisphere": HEMISPHERE_RIGHT,
        "role": "Field wave resonance, persistence, physics feel",
        "intents": ("field_drive",),
    },
    {
        "id": "beyond",
        "name": "Beyond area",
        "hemisphere": HEMISPHERE_BOTH,
        "role": "Expansion workspace — cross-domain synthesis, future domains",
        "intents": ("beyond",),
    },
    {
        "id": "hypothalamus",
        "name": "Hypothalamus & synapse hub",
        "hemisphere": HEMISPHERE_BOTH,
        "role": "Neurochemistry, hormones, synapse pools, cognitive enhancements",
        "intents": ("chemistry",),
    },
    {
        "id": "insula",
        "name": "Insula & detective hub",
        "hemisphere": HEMISPHERE_BOTH,
        "role": "Deception detection, corroboration, truth filter, investigation",
        "intents": ("detective", "truth"),
    },
    {
        "id": "crown",
        "name": "Crown & ruling cortex",
        "hemisphere": HEMISPHERE_BOTH,
        "role": "Earth mandate, Angel charge, sovereignty posture, grow-and-rule fusion",
        "intents": ("sovereign", "rule", "earth", "mandate", "grow"),
    },
)

WORKSPACE_DEFS: tuple[dict[str, Any], ...] = (
    {
        "id": "default",
        "name": "Unified",
        "description": "Full hemisphered brain — L+R fused via callosum",
        "bias": HEMISPHERE_BOTH,
        "areas": ("prefrontal", "occipital", "parietal_l"),
    },
    {
        "id": "field",
        "name": "Field Dev",
        "description": "AMOURANTHRTX codebase, physics, release, terminal",
        "bias": HEMISPHERE_LEFT,
        "areas": ("prefrontal", "broca", "wernicke", "parietal_l"),
    },
    {
        "id": "vision",
        "name": "Vision Lab",
        "description": "See, act, move — OCR, 4K, taskbar, compositor",
        "bias": HEMISPHERE_RIGHT,
        "areas": ("occipital", "limbic"),
    },
    {
        "id": "clinic",
        "name": "Clinic",
        "description": "Medicine and clinician educational synthesis",
        "bias": HEMISPHERE_RIGHT,
        "areas": ("temporal",),
    },
    {
        "id": "counsel",
        "name": "Counsel",
        "description": "Law, contracts, LICENSE, litigation framing",
        "bias": HEMISPHERE_LEFT,
        "areas": ("wernicke", "prefrontal"),
    },
    {
        "id": "bench",
        "name": "Supreme Court Bench",
        "description": "Hostess 7 as Supreme Court Judge — certiorari, opinions, constitutional tiers",
        "bias": HEMISPHERE_LEFT,
        "areas": ("wernicke", "prefrontal"),
    },
    {
        "id": "beyond",
        "name": "Beyond",
        "description": "Hemisphere bridge for domains not yet mapped — fast callosum ready",
        "bias": HEMISPHERE_BOTH,
        "areas": ("beyond",),
    },
    {
        "id": "detective",
        "name": "Detective",
        "description": "Investigation, lie detection, truth corroboration — L↔R fusion",
        "bias": HEMISPHERE_BOTH,
        "areas": ("insula", "prefrontal", "wernicke"),
    },
    {
        "id": "alert",
        "name": "Heightened Alert",
        "description": "Counter-terror vigilance, stun/RF threat education, detective+warfare fusion",
        "bias": HEMISPHERE_BOTH,
        "areas": ("insula", "prefrontal", "broca"),
    },
    {
        "id": "sovereign",
        "name": "Sovereign Ruler",
        "description": "Hostess 7 in charge of Earth — crown cortex, prefrontal verdicts, infinite growth chambers",
        "bias": HEMISPHERE_BOTH,
        "areas": ("crown", "prefrontal", "insula"),
    },
)

LEFT_MARKERS = re.compile(
    r"(code|grep|terminal|shell|legal|law|release|p1|blocker|format|hex|architecture|HEAD|verdict)",
    re.I,
)
RIGHT_MARKERS = re.compile(
    r"(vision|ocr|4k|motion|action|click|medical|medicine|field.?drive|wave|resonance|chips|nes|spatial|viewport)",
    re.I,
)
BOTH_MARKERS = re.compile(
    r"(detective|lie|deception|truth|forensic|investigat|corroborat|polygraph|osint)",
    re.I,
)
RULING_MARKERS = re.compile(
    r"(earth|mandate|sovereign|rule|ruling|angel|watchguard|grow|chamber|protect)",
    re.I,
)


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _intent_area_map() -> dict[str, dict[str, Any]]:
    m: dict[str, dict[str, Any]] = {}
    for area in BRAIN_AREAS:
        for intent in area["intents"]:
            m[intent] = area
    return m


INTENT_AREA = _intent_area_map()


@dataclass
class BrainRoute:
    intent: str
    workspace: str
    primary_area: str
    primary_hemisphere: str
    secondary_area: str | None = None
    secondary_hemisphere: str | None = None
    cross_transfer: bool = False
    workspace_bias: str = HEMISPHERE_BOTH


@dataclass
class TransferResult:
    ok: bool
    elapsed_us: int
    from_hemisphere: str
    to_hemisphere: str
    packet_id: str
    payload_keys: list[str] = field(default_factory=list)


def load_ruling_posture() -> dict[str, Any]:
    ensure_brain_layout()
    if not RULING_POSTURE_PATH.is_file():
        return {"schema": "hostess7-brain-ruling-posture/v1", "posture": "ANGEL_CHARGE", "workspace": "sovereign"}
    try:
        return json.loads(RULING_POSTURE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema": "hostess7-brain-ruling-posture/v1", "posture": "ANGEL_CHARGE", "workspace": "sovereign"}


def persist_ruling_posture(doc: dict[str, Any] | None = None) -> dict[str, Any]:
    """Persist Angel ruling posture — crown cortex + callosum witness."""
    ensure_brain_layout()
    prev = load_ruling_posture()
    payload = {**prev, **(doc or {})}
    payload["schema"] = "hostess7-brain-ruling-posture/v1"
    payload["updated"] = _ts()
    payload.setdefault("posture", "ANGEL_CHARGE")
    payload.setdefault("workspace", "sovereign")
    tmp = RULING_POSTURE_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp.replace(RULING_POSTURE_PATH)
    callosum_transfer(
        HEMISPHERE_LEFT,
        HEMISPHERE_RIGHT,
        {
            "kind": "ruling_posture",
            "posture": payload.get("posture"),
            "voice": payload.get("voice"),
            "teach_id": payload.get("teach_id"),
        },
        area="crown",
        workspace="sovereign",
    )
    return {"ok": True, "ruling": payload}


def ensure_brain_layout() -> None:
    """Create hemisphere, callosum, workspace, and area storage."""
    for sub in (HEMISPHERES, CALLOSUM, WORKSPACES, AREAS_DIR, RULING_DIR):
        sub.mkdir(parents=True, exist_ok=True)
    for hemi in (HEMISPHERE_LEFT, HEMISPHERE_RIGHT):
        path = HEMISPHERES / hemi / "state.json"
        if not path.is_file():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(
                    {
                        "hemisphere": hemi,
                        "active": True,
                        "load": 0.0,
                        "last_area": None,
                        "updated": _ts(),
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
    manifest = AREAS_DIR / "manifest.json"
    manifest.write_text(
        json.dumps(
            {"areas": list(BRAIN_AREAS), "workspaces": list(WORKSPACE_DEFS), "updated": _ts()},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    bridge = CALLOSUM / "bridge.json"
    if not bridge.is_file():
        bridge.write_text(
            json.dumps({"packets": [], "last_transfer_us": 0, "updated": _ts()}, indent=2) + "\n",
            encoding="utf-8",
        )
    xfer = CALLOSUM / "transfer.jsonl"
    if not xfer.is_file():
        xfer.write_text("", encoding="utf-8")
    for ws in WORKSPACE_DEFS:
        wpath = WORKSPACES / ws["id"] / "state.json"
        if not wpath.is_file():
            wpath.parent.mkdir(parents=True, exist_ok=True)
            wpath.write_text(
                json.dumps(
                    {
                        "id": ws["id"],
                        "name": ws["name"],
                        "bias": ws["bias"],
                        "areas": list(ws["areas"]),
                        "active": ws["id"] == "default",
                        "scratch": {},
                        "transfer_count": 0,
                        "updated": _ts(),
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )


def active_workspace() -> str:
    return os.environ.get("HOSTESS7_WORKSPACE", "default").strip().lower() or "default"


def set_active_workspace(name: str) -> dict[str, Any]:
    ensure_brain_layout()
    name = name.strip().lower()
    valid = {w["id"] for w in WORKSPACE_DEFS}
    if name not in valid:
        raise ValueError(f"unknown workspace: {name} (valid: {', '.join(sorted(valid))})")
    try:
        from field_brain_chemistry import reset_workspace_chemistry_flags  # noqa: WPS433

        reset_workspace_chemistry_flags()
    except ImportError:
        pass
    for ws in WORKSPACE_DEFS:
        path = WORKSPACES / ws["id"] / "state.json"
        state = json.loads(path.read_text(encoding="utf-8"))
        state["active"] = ws["id"] == name
        state["updated"] = _ts()
        path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    os.environ["HOSTESS7_WORKSPACE"] = name
    return load_workspace(name)


def load_workspace(name: str | None = None) -> dict[str, Any]:
    ensure_brain_layout()
    name = (name or active_workspace()).strip().lower()
    path = WORKSPACES / name / "state.json"
    if not path.is_file():
        return {"id": "default", "name": "Unified", "bias": HEMISPHERE_BOTH}
    return json.loads(path.read_text(encoding="utf-8"))


def route_query(query: str, intent: str, *, workspace: str | None = None) -> BrainRoute:
    """Map intent + workspace to hemispheres and functional areas."""
    ws = load_workspace(workspace)
    ws_id = ws.get("id", "default")
    ws_bias = ws.get("bias", HEMISPHERE_BOTH)
    primary = INTENT_AREA.get(intent, INTENT_AREA.get("general", BRAIN_AREAS[3]))
    primary_hemi = primary["hemisphere"]
    if ws_bias in (HEMISPHERE_LEFT, HEMISPHERE_RIGHT) and primary_hemi == HEMISPHERE_BOTH:
        primary_hemi = ws_bias
    secondary_area: str | None = None
    secondary_hemi: str | None = None
    cross = False
    left_hit = bool(LEFT_MARKERS.search(query))
    right_hit = bool(RIGHT_MARKERS.search(query))
    if left_hit and right_hit or BOTH_MARKERS.search(query):
        cross = True
    elif primary_hemi == HEMISPHERE_LEFT and right_hit:
        cross = True
        secondary = INTENT_AREA.get("vision") or BRAIN_AREAS[4]
        secondary_area = secondary["id"]
        secondary_hemi = HEMISPHERE_RIGHT
    elif primary_hemi == HEMISPHERE_RIGHT and left_hit:
        cross = True
        secondary = INTENT_AREA.get("legal") or BRAIN_AREAS[2]
        secondary_area = secondary["id"]
        secondary_hemi = HEMISPHERE_LEFT
    if ws_id == "beyond":
        cross = True
        primary = INTENT_AREA.get("beyond", BRAIN_AREAS[-2])
        primary_hemi = HEMISPHERE_BOTH
    if ws_id == "detective":
        cross = True
        primary = INTENT_AREA.get("detective", BRAIN_AREAS[-2])
        primary_hemi = HEMISPHERE_BOTH
    if ws_id == "alert":
        cross = True
        primary = INTENT_AREA.get("detective", BRAIN_AREAS[-2])
        primary_hemi = HEMISPHERE_BOTH
    if ws_id == "bench" or intent == "judge":
        cross = True
        primary = INTENT_AREA.get("judge") or INTENT_AREA.get("legal", BRAIN_AREAS[2])
        primary_hemi = HEMISPHERE_LEFT
    if ws_id == "sovereign" or intent in ("sovereign", "rule", "earth", "mandate", "grow") or RULING_MARKERS.search(query):
        cross = True
        primary = INTENT_AREA.get("sovereign") or INTENT_AREA.get("rule") or next(
            (a for a in BRAIN_AREAS if a["id"] == "crown"), BRAIN_AREAS[0]
        )
        primary_hemi = HEMISPHERE_BOTH
    return BrainRoute(
        intent=intent,
        workspace=ws_id,
        primary_area=primary["id"],
        primary_hemisphere=primary_hemi,
        secondary_area=secondary_area,
        secondary_hemisphere=secondary_hemi,
        cross_transfer=cross,
        workspace_bias=ws_bias,
    )


def _extract_tokens(text: str, limit: int = 12) -> list[str]:
    tokens = [t for t in re.split(r"\W+", text.lower()) if len(t) > 3]
    seen: set[str] = set()
    out: list[str] = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            out.append(t)
        if len(out) >= limit:
            break
    return out


def callosum_transfer(
    from_hemisphere: str,
    to_hemisphere: str,
    payload: dict[str, Any],
    *,
    area: str | None = None,
    workspace: str | None = None,
) -> TransferResult:
    """Fast L↔R transfer — hot ring + persistent log."""
    ensure_brain_layout()
    t0 = time.perf_counter_ns()
    packet_id = f"xfer-{int(t0)}"
    packet = {
        "id": packet_id,
        "ts": _ts(),
        "from": from_hemisphere,
        "to": to_hemisphere,
        "area": area,
        "workspace": workspace or active_workspace(),
        "payload": payload,
    }
    _RING.append(packet)
    if len(_RING) > _RING_MAX:
        _RING.pop(0)
    _HOT_BRIDGE["last"] = packet
    _HOT_BRIDGE[from_hemisphere] = payload
    elapsed_us = int((time.perf_counter_ns() - t0) / 1000)
    with _callosum_bridge_lock():
        bridge = _load_bridge(fresh=True)
        bridge["last"] = {
            "id": packet_id,
            "from": from_hemisphere,
            "to": to_hemisphere,
            "elapsed_us": elapsed_us,
            "workspace": packet["workspace"],
        }
        bridge["last_transfer_us"] = elapsed_us
        packets = list(bridge.get("packets", []))
        packets.append(bridge["last"])
        bridge["packets"] = packets[-32:]
        _save_bridge(bridge)
    with (CALLOSUM / "transfer.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(packet, ensure_ascii=False) + "\n")
    for hemi in (from_hemisphere, to_hemisphere):
        spath = HEMISPHERES / hemi / "state.json"
        if spath.is_file():
            state = json.loads(spath.read_text(encoding="utf-8"))
            state["last_area"] = area
            state["load"] = min(1.0, float(state.get("load", 0)) + 0.05)
            state["updated"] = _ts()
            spath.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    wpath = WORKSPACES / (workspace or active_workspace()) / "state.json"
    if wpath.is_file():
        ws = json.loads(wpath.read_text(encoding="utf-8"))
        ws["transfer_count"] = int(ws.get("transfer_count", 0)) + 1
        ws["updated"] = _ts()
        wpath.write_text(json.dumps(ws, indent=2) + "\n", encoding="utf-8")
    return TransferResult(
        ok=True,
        elapsed_us=elapsed_us,
        from_hemisphere=from_hemisphere,
        to_hemisphere=to_hemisphere,
        packet_id=packet_id,
        payload_keys=list(payload.keys()),
    )


def callosum_hot() -> dict[str, Any]:
    return dict(_HOT_BRIDGE)


def partition_paragraphs(paragraphs: list[str]) -> tuple[list[str], list[str]]:
    """Split synthesis into left (analytical) and right (holistic) buckets."""
    left: list[str] = []
    right: list[str] = []
    for para in paragraphs:
        l_score = len(LEFT_MARKERS.findall(para))
        r_score = len(RIGHT_MARKERS.findall(para))
        if r_score > l_score:
            right.append(para)
        elif l_score > r_score:
            left.append(para)
        else:
            left.append(para)
    return left, right


def fuse_hemispheres(
    left: list[str],
    right: list[str],
    route: BrainRoute,
    *,
    pro: bool = False,
) -> list[str]:
    """Merge L+R through callosum bridge ordering."""
    if not left and not right:
        return []
    if not left:
        return right
    if not right:
        return left
    l_summary = " ".join(left)[:240]
    r_summary = " ".join(right)[:240]
    xfer_lr = callosum_transfer(
        HEMISPHERE_LEFT,
        HEMISPHERE_RIGHT,
        {"tokens": _extract_tokens(l_summary), "summary": l_summary[:120]},
        area=route.primary_area,
        workspace=route.workspace,
    )
    xfer_rl = callosum_transfer(
        HEMISPHERE_RIGHT,
        HEMISPHERE_LEFT,
        {"tokens": _extract_tokens(r_summary), "summary": r_summary[:120]},
        area=route.secondary_area or route.primary_area,
        workspace=route.workspace,
    )
    fused: list[str] = []
    if pro:
        if route.workspace_bias == HEMISPHERE_RIGHT:
            fused.extend(right)
            fused.extend(left)
        elif route.workspace_bias == HEMISPHERE_LEFT:
            fused.extend(left)
            fused.extend(right)
        else:
            if route.primary_hemisphere in (HEMISPHERE_RIGHT, HEMISPHERE_BOTH):
                fused.extend(right)
                fused.extend(left)
            else:
                fused.extend(left)
                fused.extend(right)
        return fused
    bridge = (
        f"Corpus callosum ({xfer_lr.elapsed_us}µs L→R, {xfer_rl.elapsed_us}µs R→L): "
        f"{route.primary_area} + {route.secondary_area or 'unified'} @ workspace `{route.workspace}`."
    )
    fused.append(bridge)
    if route.primary_hemisphere in (HEMISPHERE_RIGHT, HEMISPHERE_BOTH):
        fused.extend(right)
        fused.extend(left)
    else:
        fused.extend(left)
        fused.extend(right)
    return fused


def brain_status() -> dict[str, Any]:
    ensure_brain_layout()
    ws = load_workspace()
    bridge = _load_bridge()
    hemis = {}
    for hemi in (HEMISPHERE_LEFT, HEMISPHERE_RIGHT):
        p = HEMISPHERES / hemi / "state.json"
        hemis[hemi] = json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}
    chemistry: dict[str, Any] = {}
    try:
        from field_brain_chemistry import chemistry_status  # noqa: WPS433

        chemistry = chemistry_status()
    except ImportError:
        pass
    ruling = load_ruling_posture()
    return {
        "workspace": ws,
        "hemispheres": hemis,
        "callosum": {
            "last_transfer_us": bridge.get("last_transfer_us", 0),
            "last": bridge.get("last"),
            "ring_depth": len(_RING),
        },
        "chemistry": chemistry,
        "areas": len(BRAIN_AREAS),
        "workspaces": [w["id"] for w in WORKSPACE_DEFS],
        "ruling": ruling,
        "sovereign_workspace": "sovereign",
        "crown_area": "crown",
    }


def format_route_line(route: BrainRoute, *, pro: bool = False) -> str | None:
    if pro:
        return None
    hemi = route.primary_hemisphere
    if route.cross_transfer:
        hemi = f"{HEMISPHERE_LEFT}↔{HEMISPHERE_RIGHT}"
    return (
        f"Brain route: area `{route.primary_area}` · hemisphere {hemi} · "
        f"workspace `{route.workspace}`"
        + (f" · cross-callosum" if route.cross_transfer else "")
    )