#!/usr/bin/env pythong
"""Safe signal touch policy — silent unless music, normal traffic, or animals."""
from __future__ import annotations

import os
import re
from typing import Any

TOUCH_MOTTO = (
    "A human should never feel a touch if it is a safe signal. "
    "Music, normal car traffic, animals, and Train are different."
)

FELT_SAFE_TOUCHES = frozenset({"music", "traffic", "animal", "train"})

MUSIC_CLIENT_PROCS = frozenset({
    "vlc", "mpv", "totem", "spotify", "obs", "ffmpeg", "streamlink",
    "rhythmbox", "audacious", "clementine", "amarok", "deadbeef",
})
BROWSER_PROCS = frozenset({
    "fieldfox", "field-queen", "queen-browser",
    "firefox", "chrome", "chromium", "brave", "brave-browser", "vivaldi", "opera",
    "msedge", "waterfox", "librewolf", "floorp", "thorium",
    "google-chrome", "google-chrome-stable",
})
TRAFFIC_PROC_RE = re.compile(
    r"maps|waze|uber|lyft|tesla|android[\s._-]?auto|carplay|navigation|tomtom|here[\s._-]?wego",
    re.I,
)
TRAFFIC_HOST_HINTS = frozenset({
    "maps.google.com", "www.google.com", "waze.com", "uber.com", "lyft.com",
    "openstreetmap.org", "mapbox.com", "here.com",
})
ANIMAL_PROC_RE = re.compile(
    r"tractive|whistle|fi\.pet|petcube|findmy|tile|airtag|petcoach|pawtrack",
    re.I,
)
ANIMAL_TEXT_RE = re.compile(
    r"\b(pet|dog|cat|puppy|kitten|collar|tracker|animal|wildlife|deer|bird|squirrel|raccoon)\b",
    re.I,
)
VEHICLE_TEXT_RE = re.compile(
    r"\b(car|cars|truck|vehicle|traffic|highway|commute|automobile|suv|sedan|road|driveway)\b",
    re.I,
)
TRAIN_PROC_RE = re.compile(
    r"train|rail|amtrak|metra|subway|transit|locomotive|commuter",
    re.I,
)
TRAIN_TEXT_RE = re.compile(
    r"\b(train|rail|railroad|amtrak|metra|subway|transit|locomotive|commuter)\b",
    re.I,
)
HOSTILE_MOBILE_ROLES = frozenset({
    "evil_twin", "rogue", "hostile", "unpermitted", "pollution", "adversary",
})


def _is_music_safe(scores: dict[str, int], proc: str, ip_class: str) -> bool:
    media = int(scores.get("media_stream", 0))
    if media < 6:
        return False
    proc_l = (proc or "").lower()
    if proc_l in MUSIC_CLIENT_PROCS:
        return True
    if proc_l in BROWSER_PROCS and ip_class in ("stream_cdn", "search_cdn"):
        return True
    return media >= 8


def _is_traffic_safe(proc: str, host: str, text: str = "") -> bool:
    proc_l = (proc or "").lower()
    host_l = (host or "").lower()
    blob = f"{proc_l} {host_l} {text}".lower()
    if TRAFFIC_PROC_RE.search(proc_l):
        return True
    if any(h in host_l for h in TRAFFIC_HOST_HINTS):
        return True
    if "maps" in host_l and proc_l in BROWSER_PROCS:
        return True
    return bool(VEHICLE_TEXT_RE.search(blob) and "hostile" not in blob and "rogue" not in blob)


def _is_train_safe(proc: str, host: str, text: str = "") -> bool:
    blob = f"{proc or ''} {host or ''} {text}"
    if TRAIN_PROC_RE.search(proc or ""):
        return True
    return bool(TRAIN_TEXT_RE.search(blob))


def _is_animal_safe(proc: str, host: str, text: str = "", lifeform: str = "") -> bool:
    if lifeform == "pet":
        return True
    blob = f"{proc or ''} {host or ''} {text}"
    if ANIMAL_PROC_RE.search(proc or ""):
        return True
    return bool(ANIMAL_TEXT_RE.search(blob))


def felt_safe_kind(
    *,
    scores: dict[str, int] | None = None,
    proc: str = "",
    ip_class: str = "",
    host: str = "",
    text: str = "",
    lifeform: str = "",
) -> str | None:
    scores = scores or {}
    if _is_music_safe(scores, proc, ip_class):
        return "music"
    if _is_traffic_safe(proc, host, text):
        return "traffic"
    if _is_animal_safe(proc, host, text, lifeform):
        return "animal"
    if _is_train_safe(proc, host, text):
        return "train"
    return None


def touch_fields(
    human_touch: str,
    *,
    safe_signal: bool | None = None,
) -> dict[str, Any]:
    felt = human_touch in FELT_SAFE_TOUCHES
    safe = safe_signal if safe_signal is not None else human_touch != "alert"
    return {
        "human_touch": human_touch,
        "safe_signal": safe,
        "music_signal": human_touch == "music",
        "traffic_signal": human_touch == "traffic",
        "animal_signal": human_touch == "animal",
        "train_signal": human_touch == "train",
        "touch_silent": human_touch == "none",
        "touch_motto": TOUCH_MOTTO,
    }


def connection_touch(
    verdict: str,
    trust_rank: int,
    scores: dict[str, int],
    soul_side: str,
    kill_ok: bool,
    proc: str,
    ip_class: str,
    *,
    host: str = "",
    min_accept_trust_rank: int = 2,
) -> dict[str, Any]:
    felt = felt_safe_kind(scores=scores, proc=proc, ip_class=ip_class, host=host)
    safe = (
        not kill_ok
        and verdict in ("USER_OK", "EPHEMERAL", "MONITOR")
        and trust_rank <= min_accept_trust_rank
        and soul_side in ("heaven", "limbo")
    )
    if kill_ok or verdict in ("HARM_CANDIDATE", "SUSPICIOUS") or soul_side == "hell":
        return touch_fields("alert", safe_signal=False)
    if safe and felt:
        return touch_fields(felt, safe_signal=True)
    if safe:
        return touch_fields("none", safe_signal=True)
    return touch_fields("alert", safe_signal=False)


def lifeform_touch(lifeform: str) -> str:
    if lifeform == "pet":
        return "animal"
    return "none"


def field_entity_touch(
    *,
    kind: str = "",
    role: str = "",
    label: str = "",
    moving: bool = False,
    hostile: bool = False,
    lifeform: str = "",
) -> dict[str, Any]:
    if hostile or role in HOSTILE_MOBILE_ROLES or kind in ("terror", "hostile"):
        return touch_fields("alert", safe_signal=False)
    text = f"{kind} {role} {label}"
    if lifeform == "pet" or _is_animal_safe("", "", text):
        return touch_fields("animal", safe_signal=True)
    if _is_train_safe("", "", text):
        return touch_fields("train", safe_signal=True)
    if moving and (
        kind in ("mobile", "cellphone", "vehicle", "car")
        or role in ("operator", "wifi_active", "lan_mobile", "mobile_hotspot")
        or _is_traffic_safe("", "", text)
    ):
        return touch_fields("traffic", safe_signal=True)
    if kind in ("home", "neighbor", "internet") and not hostile:
        return touch_fields("none", safe_signal=True)
    if moving:
        return touch_fields("traffic", safe_signal=True)
    return touch_fields("none", safe_signal=True)


def discern_stress_terror(
    *,
    text: str = "",
    source: str = "operator",
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify stress/terror — block external direction and illegal recreational shoot."""
    try:
        import importlib.util
        from pathlib import Path

        install = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
        script = install / "lib" / "field-stress-terror-discern.py"
        if not script.is_file():
            return {"ok": False, "error": "discern_unavailable"}
        spec = importlib.util.spec_from_file_location("field_stress_terror_discern", script)
        if not spec or not spec.loader:
            return {"ok": False, "error": "discern_unavailable"}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.discern({"text": text, "source": source, "evidence": evidence or {}})
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:120]}


def aggregate_counts(rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {t: 0 for t in ("none", "music", "traffic", "animal", "train", "alert")}
    for row in rows:
        touch = str(row.get("human_touch") or "none")
        counts[touch] = counts.get(touch, 0) + 1
    return {
        "motto": TOUCH_MOTTO,
        "silent_count": counts.get("none", 0),
        "music_count": counts.get("music", 0),
        "traffic_count": counts.get("traffic", 0),
        "animal_count": counts.get("animal", 0),
        "train_count": counts.get("train", 0),
        "alert_count": counts.get("alert", 0),
        "felt_safe_count": (
            counts.get("music", 0) + counts.get("traffic", 0)
            + counts.get("animal", 0) + counts.get("train", 0)
        ),
    }