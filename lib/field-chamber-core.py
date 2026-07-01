#!/usr/bin/env pythong
"""Shared chamber utilities — paths, JSON I/O, truth gate, module loader, audio backend."""
from __future__ import annotations

import importlib.util
import json
import math
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(_LIB.parent)))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", str(INSTALL / ".nexus-state")))
_MOD_CACHE: dict[str, Any] = {}


def ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def save_atomic(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def mod(name: str, rel: str, *, lib: Path | None = None) -> Any | None:
    py = (lib or _LIB) / rel
    key = f"{name}:{py}"
    if key in _MOD_CACHE:
        return _MOD_CACHE[key]
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, py)
    if not spec or not spec.loader:
        return None
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    _MOD_CACHE[key] = m
    return m


def truth_gate() -> dict[str, Any]:
    gate = mod("fcc_truth", "field-io-packet.py")
    if gate and hasattr(gate, "truth_gate"):
        return gate.truth_gate()
    return {"schema": "field-io-truth-gate/v1", "pass_ok": True, "skipped": True}


def ironclad_integrity() -> dict[str, Any]:
    ic = mod("fcc_ironclad", "ironclad-plate.py")
    if ic and hasattr(ic, "verify_integrity"):
        try:
            return ic.verify_integrity()
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
    return {"ok": False, "skipped": True}


def save_permanent(
    path: Path,
    doc: dict[str, Any],
    *,
    ironclad: bool = False,
    correlate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    gate = truth_gate()
    if not gate.get("pass_ok"):
        return {"saved": False, "ephemeral": True, "path": str(path), "truth_gate": gate}
    if ironclad:
        iron = ironclad_integrity()
        if not iron.get("ok") and not iron.get("skipped"):
            return {"saved": False, "ephemeral": True, "reason": "ironclad", "ironclad": iron}
    if correlate:
        if correlate.get("required") and not correlate.get("pass_ok"):
            return {"saved": False, "ephemeral": True, "reason": "correlation", "correlation": correlate}
    save_atomic(path, doc)
    return {"saved": True, "path": str(path), "truth_gate": {"pass_ok": True}}


def run(cmd: list[str], *, timeout: float = 8.0) -> tuple[int, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        return proc.returncode, ((proc.stdout or "") + (proc.stderr or "")).strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)


def db_to_linear(db: float) -> float:
    return 10 ** (db / 20.0)


def linear_to_db(linear: float) -> float:
    if linear <= 1e-9:
        return -96.0
    return 20.0 * math.log10(linear)


def detect_backend(*, install: Path | None = None) -> dict[str, Any]:
    root = install or INSTALL
    code, out = run(["pactl", "info"])
    server = ""
    if code == 0:
        for line in out.splitlines():
            if "Server Name:" in line:
                server = line.split(":", 1)[-1].strip()
    pipewire = "pipewire" in server.lower()
    pulse = pipewire or "pulse" in server.lower()
    alsa, _ = run(["aplay", "-l"], timeout=4.0)
    jack, _ = run(["jack_lsp"], timeout=2.0)
    wp, _ = run(["wpctl", "status"], timeout=3.0)
    sdl = sdl_mixer_posture(install=root)
    return {
        "id": "pipewire" if pipewire else ("pulse" if pulse else "alsa"),
        "name": "PipeWire" if pipewire else ("PulseAudio" if pulse else "ALSA"),
        "server_name": server or "unknown",
        "pactl": code == 0,
        "pipewire": pipewire,
        "pulse_compat": pulse,
        "alsa_available": alsa == 0,
        "jack": jack == 0,
        "wpctl": wp == 0,
        "sdl3_mixer": sdl,
    }


def sdl_mixer_posture(*, install: Path | None = None) -> dict[str, Any]:
    root = install or INSTALL
    sg = Path(os.environ.get("SG_ROOT", str(root.parent)))
    candidates = [
        root / "Queen" / "deps" / "sdl3_mixer-src",
        sg / "Queen" / "deps" / "sdl3_mixer-src",
        root.parent / "Queen" / "deps" / "sdl3_mixer-src",
    ]
    found = next((p for p in candidates if p.is_dir()), None)
    return {
        "available": found is not None,
        "path": str(found) if found else "",
        "channels_max": 8,
        "formats": ["pcm_f32", "pcm_s16", "opus", "mp3", "flac"],
        "surround": ["stereo", "5.1", "7.1", "8ch"],
    }


def classify_device(name: str, desc: str) -> str:
    blob = f"{name} {desc}".lower()
    if "monitor" in blob or ".monitor" in name:
        return "monitor"
    if "loopback" in blob:
        return "loopback"
    if "hdmi" in blob or "displayport" in blob:
        return "hdmi"
    if "bluez" in blob or "bluetooth" in blob:
        return "bluetooth"
    if "usb" in blob:
        return "usb"
    if "echo-cancel" in blob or "virtual" in blob or "null" in blob:
        return "virtual"
    return "generic"


def parse_pactl_short(kind: str) -> list[dict[str, Any]]:
    flag = "sinks" if kind == "sink" else "sources"
    code, out = run(["pactl", "list", flag, "short"])
    if code != 0:
        return []
    items: list[dict[str, Any]] = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        name, desc = parts[1], parts[3] if len(parts) > 3 else parts[1]
        if kind == "source" and name.endswith(".monitor"):
            continue
        items.append({
            "index": parts[0],
            "name": name,
            "description": desc,
            "kind": classify_device(name, desc),
            "driver": kind,
        })
    return items


def parse_pactl_detail(kind: str, name: str) -> dict[str, Any]:
    flag = "sinks" if kind == "sink" else "sources"
    code, out = run(["pactl", "list", flag])
    if code != 0:
        return {}
    blocks = re.split(rf"^{kind.capitalize()} #\d+", out, flags=re.MULTILINE)
    headers = re.findall(rf"^{kind.capitalize()} #(\d+)", out, flags=re.MULTILINE)
    for hdr, chunk in zip(headers, blocks[1:], strict=False):
        if f"Name: {name}" not in chunk:
            continue
        detail: dict[str, Any] = {"name": name, "index": hdr, "driver": kind}
        for line in chunk.splitlines():
            if ":" not in line:
                continue
            key, val = line.split(":", 1)
            detail[key.strip().lower().replace(" ", "_")] = val.strip()
        vol = re.search(r"Volume:.*?(\d+)%", chunk)
        if vol:
            detail["volume_percent"] = int(vol.group(1))
        detail["muted"] = "Mute: yes" in chunk
        ch = re.search(r"Channel Map:\s*(.+)", chunk)
        if ch:
            detail["channel_map"] = ch.group(1).strip()
        sr = re.search(r"Sample Specification:\s*(\w+).*?(\d+)\s*Hz", chunk)
        if sr:
            detail["sample_format"] = sr.group(1)
            detail["sample_rate"] = int(sr.group(2))
        return detail
    return {}


def default_device(kind: str) -> str:
    code, out = run(["pactl", f"get-default-{kind}"])
    return out.strip() if code == 0 else ""


def alsa_cards() -> list[dict[str, Any]]:
    code, out = run(["aplay", "-l"])
    if code != 0:
        return []
    cards: list[dict[str, Any]] = []
    for line in out.splitlines():
        m = re.match(r"card (\d+): ([^\s]+) \[(.+)\]", line)
        if m:
            cards.append({"id": m.group(1), "name": m.group(2), "description": m.group(3), "driver": "alsa"})
    capture, cout = run(["arecord", "-l"])
    if capture == 0:
        for line in cout.splitlines():
            m = re.match(r"card (\d+): ([^\s]+) \[(.+)\]", line)
            if m and not any(c["id"] == m.group(1) for c in cards):
                cards.append({"id": m.group(1), "name": m.group(2), "description": m.group(3), "driver": "alsa_capture"})
    return cards


def apply_volume_db(device: str, db: float, *, kind: str = "sink") -> dict[str, Any]:
    if not device:
        return {"ok": False, "error": "missing_device"}
    pct = max(0, min(150, int(round(100 + linear_to_db(db_to_linear(db))))))
    code, out = run(["pactl", f"set-{kind}-volume", device, f"{pct}%"])
    return {"ok": code == 0, "device": device, "target_db": db, "detail": out[:200]}


def enumerate_audio_devices() -> dict[str, Any]:
    sinks = parse_pactl_short("sink")
    sources = parse_pactl_short("source")
    monitors = [s for s in parse_pactl_short("source") if s["name"].endswith(".monitor")]
    return {
        "sinks": sinks,
        "sources": sources,
        "monitors": monitors,
        "loopbacks": [d for d in sinks + sources if d.get("kind") == "loopback"],
        "hdmi": [d for d in sinks if d.get("kind") == "hdmi"],
        "bluetooth": [d for d in sinks + sources if d.get("kind") == "bluetooth"],
        "usb": [d for d in sinks + sources if d.get("kind") == "usb"],
        "virtual": [d for d in sinks + sources if d.get("kind") == "virtual"],
        "alsa_cards": alsa_cards(),
        "default_sink": default_device("sink"),
        "default_source": default_device("source"),
    }