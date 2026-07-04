#!/usr/bin/env python3
"""Field HDMI Audio Driver — binds NVIDIA/AMD HDMI through PipeWire pro-audio profile.

When HDMI ports report unavailable (no EDID / monitor_present=0), WirePlumber leaves
the card on profile \"off\" and only exposes auto_null. This driver forces pro-audio,
selects the best HDMI ALSA device, sets the default sink, and moves streams off dummy.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("fcc", _LIB / "field-chamber-core.py")
fcc = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(fcc)

STATE = fcc.STATE
ROUTE_PATH = STATE / "field-hdmi-audio.json"
PANEL_PATH = STATE / "field-hdmi-audio-panel.json"

# ALSA playback device id → human label (NVIDIA HDA typical layout)
HDMI_ALSA_DEVICES: dict[str, str] = {
    "3": "HDMI 0",
    "7": "HDMI 1",
    "8": "HDMI 2",
    "9": "HDMI 3",
}

DUMMY_PATTERNS = ("auto_null", "null", "dummy")


def _run(cmd: list[str], *, timeout: float = 10.0) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return proc.returncode, ((proc.stdout or "") + (proc.stderr or "")).strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)


def _is_dummy(name: str) -> bool:
    low = name.lower()
    return any(p in low for p in DUMMY_PATTERNS)


def _card_from_sink(sink_name: str) -> str:
    m = re.match(r"alsa_output\.(alsa_card\.[^.]+(?:\.[^.]+)*)\.", sink_name)
    if m:
        return m.group(1)
    m = re.match(r"alsa_output\.(pci-[^.]+(?:\.[^.]+)*)\.", sink_name)
    if m:
        return f"alsa_card.{m.group(1)}"
    return ""


def _hdmi_cards() -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    code, out = _run(["pactl", "list", "cards"])
    if code == 0:
        blocks = re.split(r"^Card #\d+", out, flags=re.MULTILINE)
        for block in blocks[1:]:
            name_m = re.search(r"Name:\s*(.+)", block)
            if not name_m:
                continue
            name = name_m.group(1).strip()
            blob = block.lower()
            if (
                "nvidia" not in blob
                and "hdmi" not in blob
                and "displayport" not in blob
                and not re.search(r"output:hdmi", block)
                and "pro-audio" not in blob
            ):
                continue
            active_m = re.search(r"Active Profile:\s*(.+)", block)
            cards.append({
                "name": name,
                "active_profile": active_m.group(1).strip() if active_m else "",
                "pro_audio_available": "pro-audio:" in block and "available: yes" in block.split("pro-audio:")[-1][:80],
                "hdmi_profiles": len(re.findall(r"output:hdmi", block)),
            })
    if cards:
        return cards
    for sink in _pro_hdmi_sinks():
        card_name = _card_from_sink(str(sink.get("name") or ""))
        if card_name and not any(c["name"] == card_name for c in cards):
            cards.append({
                "name": card_name,
                "active_profile": "pro-audio",
                "pro_audio_available": True,
                "hdmi_profiles": 0,
                "inferred_from_sink": True,
            })
    return cards


def _eld_hdmi_present(card_id: str = "0") -> dict[str, bool]:
    """Map ALSA device suffix → monitor_present from ELD."""
    present: dict[str, bool] = {k: False for k in HDMI_ALSA_DEVICES}
    eld_dir = Path(f"/proc/asound/card{card_id}")
    if not eld_dir.is_dir():
        return present
    for eld in sorted(eld_dir.glob("eld#*")):
        try:
            text = eld.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        dev_m = re.search(r"codec_dev_id(\d+)", text)
        mon_m = re.search(r"monitor_present(\d+)", text)
        if not dev_m or not mon_m:
            continue
        if mon_m.group(1) != "1":
            continue
        # ELD index does not map 1:1 to ALSA device; correlate via aplay -l
        pass
    code, out = _run(["aplay", "-l"])
    if code != 0:
        return present
    for line in out.splitlines():
        m = re.match(rf"card {re.escape(card_id)}:.*device (\d+): HDMI (\d+)", line)
        if m:
            dev_id, hdmi_idx = m.group(1), m.group(2)
            eld_path = eld_dir / f"eld#0.{hdmi_idx}"
            if eld_path.is_file():
                text = eld_path.read_text(encoding="utf-8", errors="replace")
                mon = re.search(r"monitor_present(\d+)", text)
                present[dev_id] = bool(mon and mon.group(1) == "1")
    return present


def _pro_hdmi_sinks() -> list[dict[str, Any]]:
    sinks: list[dict[str, Any]] = []
    for row in fcc.parse_pactl_short("sink"):
        name = str(row.get("name") or "")
        if _is_dummy(name):
            continue
        m = re.search(r"\.pro-output-(\d+)$", name)
        if not m:
            if "hdmi" in name.lower() or "nvidia" in name.lower():
                sinks.append({**row, "alsa_device": "", "hdmi_label": row.get("description", name)})
            continue
        dev_id = m.group(1)
        sinks.append({
            **row,
            "alsa_device": dev_id,
            "hdmi_label": HDMI_ALSA_DEVICES.get(dev_id, f"HDMI ALSA {dev_id}"),
            "kind": "hdmi",
        })
    return sinks


def _activate_card(card_name: str) -> dict[str, Any]:
    code, detail = _run(["pactl", "set-card-profile", card_name, "pro-audio"])
    return {"ok": code == 0, "card": card_name, "profile": "pro-audio", "detail": detail[:200]}


def _pick_sink(*, prefer_device: str = "") -> dict[str, Any] | None:
    sinks = _pro_hdmi_sinks()
    if not sinks:
        return None
    if prefer_device:
        hit = next((s for s in sinks if s.get("alsa_device") == prefer_device), None)
        if hit:
            return hit
        hit = next((s for s in sinks if prefer_device in s.get("name", "")), None)
        if hit:
            return hit
    eld = _eld_hdmi_present("0")
    for dev_id in ("3", "7", "8", "9"):
        if eld.get(dev_id):
            hit = next((s for s in sinks if s.get("alsa_device") == dev_id), None)
            if hit:
                return hit
    return next((s for s in sinks if s.get("alsa_device") == "3"), sinks[0])


def _move_streams(target_sink: str) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    code, out = _run(["pactl", "list", "sink-inputs", "short"])
    if code != 0:
        return steps
    dummy_indices: set[str] = set()
    code2, sinks_out = _run(["pactl", "list", "sinks", "short"])
    if code2 == 0:
        for sline in sinks_out.splitlines():
            sp = sline.split("\t")
            if len(sp) >= 2 and _is_dummy(sp[1]):
                dummy_indices.add(sp[0])
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        idx, cur_sink = parts[0], parts[1]
        if dummy_indices and cur_sink not in dummy_indices:
            continue
        app = parts[3] if len(parts) > 3 else ""
        mc, md = _run(["pactl", "move-sink-input", idx, target_sink])
        steps.append({"input": idx, "app": app, "ok": mc == 0, "detail": md[:80]})
    return steps


def probe() -> dict[str, Any]:
    default_sink = fcc.default_device("sink")
    cards = _hdmi_cards()
    sinks = _pro_hdmi_sinks()
    eld = _eld_hdmi_present("0")
    preferred = _pick_sink()
    return {
        "ok": True,
        "schema": "field-hdmi-audio-probe/v1",
        "updated": fcc.ts(),
        "default_sink": default_sink,
        "default_is_dummy": _is_dummy(default_sink),
        "hdmi_cards": cards,
        "hdmi_sinks": sinks,
        "eld_monitor_present": eld,
        "preferred_sink": preferred,
        "alsa_hdmi_map": HDMI_ALSA_DEVICES,
        "driver": "field-hdmi-audio-driver/v1",
    }


def bind(*, sink_name: str = "", hdmi_device: str = "", force: bool = False) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    sinks = _pro_hdmi_sinks()
    cards = _hdmi_cards()
    card = cards[0]["name"] if cards else ""
    if not sinks and card and cards[0].get("active_profile") != "pro-audio":
        act = _activate_card(card)
        steps.append({"op": "set-card-profile", **act})
        if not act["ok"] and not force:
            return {"ok": False, "error": "profile_activate_failed", "steps": steps, "probe": probe()}
        sinks = _pro_hdmi_sinks()
    elif not sinks and card:
        act = _activate_card(card)
        steps.append({"op": "set-card-profile", **act})
        sinks = _pro_hdmi_sinks()
    if not sinks and not card:
        return {"ok": False, "error": "no_hdmi_card", "probe": probe()}

    target = None
    if sink_name:
        target = next((s for s in sinks if s.get("name") == sink_name), None)
    if not target:
        target = _pick_sink(prefer_device=hdmi_device)

    if not target:
        return {"ok": False, "error": "no_hdmi_sink", "steps": steps, "probe": probe()}

    name = str(target["name"])
    for op, args in (
        ("set-default-sink", ["pactl", "set-default-sink", name]),
        ("unmute", ["pactl", "set-sink-mute", name, "0"]),
        ("volume", ["pactl", "set-sink-volume", name, "100%"]),
    ):
        code, detail = _run(args)
        steps.append({"op": op, "target": name, "ok": code == 0, "detail": detail[:120]})

    moved = _move_streams(name)
    if moved:
        steps.append({"op": "move-streams", "count": len(moved), "streams": moved})

    route = {
        "schema": "field-hdmi-audio-route/v1",
        "updated": fcc.ts(),
        "bound": True,
        "card": card,
        "profile": "pro-audio",
        "sink_name": name,
        "hdmi_label": target.get("hdmi_label"),
        "alsa_device": target.get("alsa_device"),
        "monitor_source": f"{name}.monitor",
        "steps": steps,
    }
    fcc.save_atomic(ROUTE_PATH, route)

    dac_settings = STATE / "field-audio-dac-settings.json"
    saved = fcc.load(dac_settings, {})
    saved["output_device"] = name
    saved["output_muted"] = False
    fcc.save_atomic(dac_settings, saved)

    settings = STATE / "field-audio-settings.json"
    s2 = fcc.load(settings, {})
    s2["default_sink"] = name
    s2["sink_muted"] = False
    fcc.save_atomic(settings, s2)

    return {
        "ok": True,
        "schema": "field-hdmi-audio-bind/v1",
        "bound": True,
        "sink_name": name,
        "hdmi_label": target.get("hdmi_label"),
        "route": route,
        "probe": probe(),
    }


def posture() -> dict[str, Any]:
    route = fcc.load(ROUTE_PATH, {})
    p = probe()
    doc = {
        "ok": True,
        "schema": "field-hdmi-audio-panel/v1",
        "updated": fcc.ts(),
        "bound": bool(route.get("bound")),
        "route": route,
        "probe": p,
        "routes": {
            "bind": "/api/field-hdmi-audio/bind",
            "auto": "/api/field-hdmi-audio/auto",
            "probe": "/api/field-hdmi-audio/probe",
        },
        "posture": (
            f"HDMI audio — {'bound' if route.get('bound') else 'standby'} · "
            f"{route.get('hdmi_label') or p.get('preferred_sink', {}).get('hdmi_label') or 'no sink'}"
        ),
    }
    fcc.save_atomic(PANEL_PATH, doc)
    return doc


def install_session_service() -> dict[str, Any]:
    home = Path.home()
    unit_dir = home / ".config" / "systemd" / "user"
    unit_dir.mkdir(parents=True, exist_ok=True)
    root = fcc.INSTALL
    py = sys.executable
    script = _LIB / "field-hdmi-audio-driver.py"
    unit = f"""[Unit]
Description=Field HDMI Audio Driver (NVIDIA pro-audio bind)
After=pipewire.service pipewire-pulse.service wireplumber.service
PartOf=graphical-session.target

[Service]
Type=oneshot
RemainAfterExit=yes
Environment=NEXUS_INSTALL_ROOT={root}
Environment=NEXUS_STATE_DIR={STATE}
ExecStart={py} {script} auto
ExecStartPost=/bin/sleep 2
ExecStartPost={py} {script} auto

[Install]
WantedBy=graphical-session.target
"""
    unit_path = unit_dir / "field-hdmi-audio.service"
    unit_path.write_text(unit, encoding="utf-8")
    steps: list[dict[str, Any]] = [{"op": "write-unit", "path": str(unit_path), "ok": True}]
    for cmd in (
        ["systemctl", "--user", "daemon-reload"],
        ["systemctl", "--user", "enable", "field-hdmi-audio.service"],
    ):
        code, detail = _run(cmd)
        steps.append({"op": " ".join(cmd[2:]), "ok": code == 0, "detail": detail[:120]})
    return {"ok": True, "unit": str(unit_path), "steps": steps}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "status", "posture"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "probe":
        print(json.dumps(probe(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("bind", "auto"):
        sink = ""
        hdmi_dev = ""
        force = "--force" in sys.argv
        for arg in sys.argv[2:]:
            if arg.startswith("--hdmi="):
                hdmi_dev = arg.split("=", 1)[1]
            elif not arg.startswith("--"):
                sink = arg
        print(json.dumps(bind(sink_name=sink, hdmi_device=hdmi_dev, force=force or cmd == "auto"), ensure_ascii=False, indent=2))
        return 0
    if cmd == "install":
        print(json.dumps(install_session_service(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: field-hdmi-audio-driver.py [json|probe|bind|auto|install]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())