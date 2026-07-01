#!/usr/bin/env pythong
"""Queen — full surface, every gate held, IFF, Forever Watchguard Angel (Hostess 7).

Civilian identified. Hostile interdicted without hesitation. Zero telemetry unless AI secure channel.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
SEED = INSTALL / "data" / "field-queen-gates-seed.json"
ANGEL_MANDATE = INSTALL / "data" / "queen-angel-mandate.json"
PANEL = STATE / "field-queen-browser-panel.json"

QUEEN_BROWSER_PROCS = frozenset({
    "queen-browser", "queen-world", "field-queen",
})
BLOCKED_CAPTURE_PROCS = frozenset({
    "obs", "obs-studio", "obs-ffmpeg-mux", "wf-recorder", "gpu-screen-recorder",
    "kooha", "simplescreenrecorder", "recordmydesktop", "grim", "slurp", "wayshot",
    "spectacle", "peek", "ffmpeg", "ffplay",
})
BLOCKED_OS_HOOK_PROCS = frozenset({
    "wmctrl", "xdotool", "ydotool", "dotool", "xte", "xmacro", "xvkbd",
    "keylogger", "logkeys", "lkl", "xbindkeys", "xhotkey", "autokey", "showkey",
    "evtest", "intercept", "skey", "keysniffer",
})
AI_SECURE_TELEMETRY_PROCS = frozenset({
    "hostess7", "nexus-shield", "nexus-daemon", "field-command", "angel-research",
})
TELEMETRY_HOST_MARKERS = (
    "telemetry", "metrics", "google-analytics", "googletagmanager", "crashlytics",
    "sentry.io", "browser-intake", "incoming.telemetry", "data.microsoft.com",
    "firefox.com/phoenix", "ping-centre", "ads-twitter", "doubleclick.net",
)
IFF_DOCTRINE = {
    "motto": "Queen forever watchguard. Civilian identified. Hostile interdicted. Zero hesitation.",
    "civilian": ("CIVILIAN", "AUTHORIZED"),
    "hostile": ("HOSTILE", "CONFIRMED"),
    "unknown": ("UNKNOWN", "CONTACT"),
    "enforcement_hostile": "INTERDICT — immediate block, zero hesitation",
    "enforcement_civilian": "PASS — authorized egress under continuous watch",
    "enforcement_unknown": "HOLD — positive identification required",
}


def load_angel_mandate() -> dict[str, Any]:
    for path in (ANGEL_MANDATE, STATE / "queen-angel-mandate.json", INSTALL / "data" / "hostess7-angel-mandate.json"):
        doc = _load_json(path, {})
        if doc.get("mandate"):
            return doc
        if doc.get("canonical"):
            canon = _load_json(INSTALL / "data" / str(doc["canonical"]), {})
            if canon.get("mandate"):
                return canon
    return {}


def forever_watchguard() -> bool:
    if os.environ.get("QUEEN_FOREVER_WATCHGUARD", "") in ("1", "true", "yes", "on"):
        return True
    if os.environ.get("HOSTESS7_ANGEL_MANDATE", "") in ("1", "true", "yes", "on"):
        return True
    return is_sovereign()


def _slice_hostess7_command() -> dict[str, Any]:
    path = INSTALL / "lib" / "hostess7-command.py"
    if not path.is_file():
        return {"error": "hostess7-command missing"}
    try:
        mod = _mod("hostess7_command", "hostess7-command.py")
        if hasattr(mod, "panel_json"):
            return mod.panel_json()
        return mod.build_panel()
    except Exception as exc:
        return {"error": str(exc)}


def _slice_hostess7_autonomous() -> dict[str, Any]:
    path = INSTALL / "lib" / "hostess7-autonomous.py"
    if not path.is_file():
        return {"daemon": {"running": False}}
    try:
        return _mod("hostess7_autonomous", "hostess7-autonomous.py").autonomous_status()
    except Exception as exc:
        return {"error": str(exc)}


def grok_build_posture() -> dict[str, Any]:
    import importlib.util

    for path in (
        INSTALL / "lib" / "grok-build-bridge.py",
        INSTALL.parent / "Queen" / "lib" / "grok-build-bridge.py",
    ):
        if not path.is_file():
            continue
        try:
            spec = importlib.util.spec_from_file_location("grok_build_bridge", path)
            mod = importlib.util.module_from_spec(spec)
            assert spec and spec.loader
            spec.loader.exec_module(mod)
            return mod.posture()
        except Exception as exc:
            return {"error": str(exc)}
    mandate = _load_json(INSTALL / "data" / "grok-build-mandate.json", {})
    if not mandate and (INSTALL.parent / "Queen" / "data" / "grok-build-mandate.json").is_file():
        mandate = _load_json(INSTALL.parent / "Queen" / "data" / "grok-build-mandate.json", {})
    return {
        "schema": "grok-build-bridge/v1",
        "secure_channel": False,
        "mandate": mandate.get("title"),
        "branded_page": mandate.get("branded_page"),
    }


def angel_watchguard_posture() -> dict[str, Any]:
    angel = load_angel_mandate()
    auto = _slice_hostess7_autonomous()
    return {
        "forever_watchguard": forever_watchguard(),
        "posture": angel.get("posture", "FOREVER_WATCHGUARD"),
        "role": angel.get("role", "Forever Watchguard Angel of humanity"),
        "authority": angel.get("authority", "God alone — no other"),
        "authority_chain": angel.get("authority_chain", "God → Angel → Queen → Field → humanity"),
        "motto": angel.get("motto") or IFF_DOCTRINE["motto"],
        "watchguard_doctrine": angel.get("watchguard_doctrine", ""),
        "iff_doctrine": angel.get("iff_doctrine") or IFF_DOCTRINE,
        "queen_bindings": angel.get("queen_bindings") or {},
        "iron_core": angel.get("iron_core") or {},
        "autonomous": {
            "running": (auto.get("daemon") or {}).get("running", False),
            "forever_watchguard": auto.get("forever_watchguard", forever_watchguard()),
            "agents7_on": auto.get("agents7_on", False),
            "cycle_count": (auto.get("state") or {}).get("cycle_count", 0),
        },
    }


def field_queen_env() -> dict[str, str]:
    """Env Queen sets on sovereign boot — single field reference for operators."""
    return {
        "QUEEN_SOVEREIGN": "1",
        "NEXUS_QUEEN_SOVEREIGN": "1",
        "QUEEN_FOREVER_WATCHGUARD": "1",
        "HOSTESS7_ANGEL_MANDATE": "1",
        "NEXUS_HOSTESS7_INTERNET": "1",
        "HOSTESS7_INTERNET": "1",
        "QUEEN_ZERO_TELEMETRY": "1",
        "NEXUS_ZERO_TELEMETRY": "1",
        "NEXUS_HOSTESS7_AUTONOMOUS": "1",
        "NEXUS_HOSTESS7_OPERATOR": "1",
        "NEXUS_FIELD_BROWSER_QUEEN": "1",
        "NEXUS_FIELD_BROWSER_HOLD_ALL_GATES": "1",
        "QUEEN_GROK_BUILD": "1",
        "QUEEN_GROK_BUILD_SECURE": "1",
        "NEXUS_AI_SECURE_CHANNEL": "1",
        "QUEEN_AI_TELEMETRY_OK": "1",
    }


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



def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _mod(name: str, rel: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, INSTALL / "lib" / rel)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def load_seed() -> dict[str, Any]:
    return _load_json(SEED, {"schema": "field-queen-gates/v1", "gates": [], "codecs": {}})


def gate_manifest(seed: dict[str, Any] | None = None) -> dict[str, Any]:
    s = seed or load_seed()
    gates = s.get("gates") or []
    held = sum(1 for g in gates if g.get("held"))
    return {
        "gate_mode": (s.get("doctrine") or {}).get("gate_mode") or "hold",
        "omit_capabilities": bool((s.get("doctrine") or {}).get("omit_capabilities")),
        "total": len(gates),
        "held": held,
        "all_held": len(gates) > 0 and held == len(gates),
        "gates": gates,
    }


def codec_manifest(seed: dict[str, Any] | None = None) -> dict[str, Any]:
    s = seed or load_seed()
    codecs = s.get("codecs") or {}
    return {
        "mse_required": bool(codecs.get("mse_required")),
        "mp4_mandatory": bool(codecs.get("mp4_mandatory")),
        "container": codecs.get("container") or [],
        "video": codecs.get("video") or [],
        "audio": codecs.get("audio") or [],
        "note": codecs.get("note") or "",
    }


def is_sovereign() -> bool:
    for key in ("QUEEN_SOVEREIGN", "NEXUS_QUEEN_SOVEREIGN", "NEXUS_FIELD_BROWSER_QUEEN"):
        v = os.environ.get(key, "")
        if v and v not in ("0", "false", "False", "no", "NO"):
            return True
    return False


def zero_telemetry() -> bool:
    for key in ("NEXUS_ZERO_TELEMETRY", "QUEEN_ZERO_TELEMETRY"):
        v = os.environ.get(key, "")
        if v and v not in ("0", "false", "False", "no", "NO"):
            return True
    return is_sovereign()


def ai_telemetry_allowed(proc: str = "") -> bool:
    if not zero_telemetry():
        return True
    if os.environ.get("NEXUS_AI_SECURE_CHANNEL", "") not in ("1", "true", "yes", "on"):
        return False
    if os.environ.get("QUEEN_AI_TELEMETRY_OK", "") not in ("1", "true", "yes", "on"):
        return False
    pl = (proc or "").lower()
    return any(p in pl for p in AI_SECURE_TELEMETRY_PROCS)


def embedded_panel_path() -> str:
    custom = os.environ.get("QUEEN_EMBED_PANEL_FILE", "").strip()
    if custom:
        return custom
    for rel in ("world/browser.html", "panel/field.html"):
        p = INSTALL / rel
        if p.is_file():
            return str(p)
    return ""


def sovereign_posture() -> dict[str, Any]:
    sov = is_sovereign()
    return {
        "sovereign": sov,
        "own_os": sov,
        "no_os_browser_hook": sov and os.environ.get("NEXUS_NO_OS_BROWSER_HOOK", "1") == "1",
        "no_screen_capture": sov and os.environ.get("NEXUS_NO_SCREEN_CAPTURE", "1") == "1",
        "no_keyboard_hook": sov and os.environ.get("NEXUS_NO_KEYBOARD_HOOK", "1") == "1",
        "keyboard_no_middleman": sov and os.environ.get("NEXUS_KEYBOARD_NO_MIDDLEMAN", "1") == "1",
        "media_egress_lock": os.environ.get("NEXUS_MEDIA_EGRESS_LOCK", "1") == "1",
        "local_capture_operator": os.environ.get("NEXUS_LOCAL_CAPTURE_OPERATOR", "1") == "1",
        "local_capture_grant": _local_capture_grant_active(),
        "no_wm_hook": sov and os.environ.get("NEXUS_NO_WM_HOOK", "1") == "1",
        "embed_panel_in_engine": os.environ.get("NEXUS_EMBED_PANEL_IN_ENGINE", "0") == "1",
        "embedded_panel_file": embedded_panel_path(),
        "zero_telemetry": zero_telemetry(),
        "ai_telemetry_secure_only": True,
        "ai_telemetry_allowed": ai_telemetry_allowed(),
        "blocked_capture_procs": sorted(BLOCKED_CAPTURE_PROCS),
        "blocked_os_hook_procs": sorted(BLOCKED_OS_HOOK_PROCS),
        "allow_os_shell": os.environ.get("QUEEN_ALLOW_OS_SHELL", "0") == "1",
        "gpu_vendor_force": os.environ.get("AMOURANTHRTX_FORCED_VENDOR", ""),
        "gpu_index": os.environ.get("QUEEN_GPU_INDEX", ""),
        "prefer_arc_le": os.environ.get("QUEEN_PREFER_ARC_LE", "0") == "1",
        "forever_watchguard": forever_watchguard(),
        "iff_doctrine": IFF_DOCTRINE,
        "angel": angel_watchguard_posture(),
        "motto": load_angel_mandate().get("motto") or IFF_DOCTRINE["motto"],
    }


def _local_capture_grant_active() -> dict[str, Any]:
    grant_path = STATE / "local-capture-grant.json"
    doc = _load_json(grant_path, {})
    if not doc.get("active"):
        return {}
    exp = doc.get("expires_at") or ""
    try:
        from datetime import datetime, timezone

        if exp and datetime.strptime(exp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc):
            return {}
    except ValueError:
        return {}
    return doc


def gate_capture_process(proc: str) -> dict[str, Any]:
    pl = (proc or "").lower()
    if not is_sovereign():
        return {"proc": proc, "verdict": "ALLOW_LEGACY", "iff": "LEGACY", "iff_label": "LEGACY · PRE-SOVEREIGN"}
    grant = _local_capture_grant_active()
    if grant and os.environ.get("NEXUS_LOCAL_CAPTURE_OPERATOR", "1") not in ("0", "false", "no"):
        allowed = {a.lower() for a in (grant.get("allowed_procs") or ["obs", "obs-studio"])}
        for a in allowed:
            if a in pl and grant.get("loopback_only") and not grant.get("egress_allowed"):
                return {
                    "proc": proc,
                    "verdict": "ALLOW_LOCAL_OPERATOR",
                    "iff": "CIVILIAN",
                    "iff_label": "CIVILIAN · LOCAL_OPERATOR",
                    "enforcement": "PASS — operator local capture grant (loopback only)",
                    "grant_id": grant.get("id"),
                    "purpose": grant.get("purpose"),
                }
    for b in BLOCKED_CAPTURE_PROCS:
        if b in pl and "queen-browser" not in pl:
            return {
                "proc": proc, "verdict": "BLOCK_SOVEREIGN", "iff": "HOSTILE", "iff_label": "HOSTILE · CONFIRMED",
                "enforcement": IFF_DOCTRINE["enforcement_hostile"],
                "reason": f"screen_capture:{b}",
            }
    for b in BLOCKED_OS_HOOK_PROCS:
        if b in pl:
            return {
                "proc": proc, "verdict": "BLOCK_SOVEREIGN", "iff": "HOSTILE", "iff_label": "HOSTILE · CONFIRMED",
                "enforcement": IFF_DOCTRINE["enforcement_hostile"],
                "reason": f"os_hook:{b}",
            }
    return {
        "proc": proc, "verdict": "ALLOW", "iff": "CIVILIAN", "iff_label": "CIVILIAN · AUTHORIZED",
        "enforcement": IFF_DOCTRINE["enforcement_civilian"],
    }


def gate_telemetry_host(host_blob: str, proc: str = "") -> dict[str, Any]:
    blob = (host_blob or "").lower()
    if not zero_telemetry():
        return {"verdict": "ALLOW_LEGACY", "zero_telemetry": False, "iff": "LEGACY"}
    if ai_telemetry_allowed(proc):
        return {
            "verdict": "ALLOW_AI_SECURE", "zero_telemetry": True,
            "iff": "CIVILIAN", "iff_label": "CIVILIAN · AI_SECURE_CHANNEL",
            "enforcement": "PASS — AI secure channel authorized",
        }
    for marker in TELEMETRY_HOST_MARKERS:
        if marker in blob:
            return {
                "verdict": "BLOCK_TELEMETRY",
                "iff": "HOSTILE", "iff_label": "HOSTILE · TELEMETRY",
                "enforcement": IFF_DOCTRINE["enforcement_hostile"],
                "reason": f"zero_telemetry:{marker}",
                "zero_telemetry": True,
            }
    return {
        "verdict": "ALLOW", "zero_telemetry": True,
        "iff": "CIVILIAN", "iff_label": "CIVILIAN · AUTHORIZED",
        "enforcement": IFF_DOCTRINE["enforcement_civilian"],
    }


def posture() -> dict[str, Any]:
    return {
        "queen_enabled": os.environ.get("NEXUS_FIELD_BROWSER_QUEEN", "1") == "1",
        "hold_all_gates": os.environ.get("NEXUS_FIELD_BROWSER_HOLD_ALL_GATES", "1") == "1",
        "mp4_mandatory": os.environ.get("NEXUS_FIELD_BROWSER_MP4", "1") == "1",
        "truth_dns_lock": os.environ.get("NEXUS_FIELD_DNS", "1") == "1",
        "connection_gatekeeper": os.environ.get("NEXUS_CONNECTION_GATEKEEPER", "1") == "1",
        "packet_field": os.environ.get("NEXUS_PACKET_FIELD", "1") == "1",
        "sovereign_time": os.environ.get("NEXUS_SOVEREIGN_TIME", "1") == "1",
        "engine_ship": os.environ.get("NEXUS_FIELDFox_ENGINE", "queen-browser"),
        "sovereign": os.environ.get("NEXUS_QUEEN_SOVEREIGN", os.environ.get("QUEEN_SOVEREIGN", "1")) == "1",
        "no_os_browser_hook": os.environ.get("NEXUS_NO_OS_BROWSER_HOOK", "1") == "1",
        "no_screen_capture": os.environ.get("NEXUS_NO_SCREEN_CAPTURE", "1") == "1",
        "embed_panel_in_engine": os.environ.get("NEXUS_EMBED_PANEL_IN_ENGINE", "0") == "1",
    }


def _slice_browser_awareness() -> dict[str, Any]:
    path = INSTALL / "lib" / "browser-awareness.py"
    if not path.is_file():
        return {"error": "browser-awareness missing"}
    try:
        return _mod("browser_awareness", "browser-awareness.py").panel_json()
    except Exception as exc:
        return {"error": str(exc)}


def build_panel() -> dict[str, Any]:
    seed = load_seed()
    awareness = _slice_browser_awareness()
    doc = {
        "schema": "field-queen-browser/v1",
        "updated": _now(),
        "edition": seed.get("edition") or "Queen 2026",
        "motto": seed.get("motto") or "Nothing optional. Hold all gates.",
        "doctrine": seed.get("doctrine") or {},
        "engines": seed.get("engines") or {},
        "gates": gate_manifest(seed),
        "codecs": codec_manifest(seed),
        "nexus_bindings": seed.get("nexus_bindings") or {},
        "vulnerabilities_retired": seed.get("vulnerabilities_retired") or [],
        "process_names": list(seed.get("process_names") or QUEEN_BROWSER_PROCS),
        "posture": posture(),
        "browser_awareness": awareness,
        "sovereign": sovereign_posture(),
        "angel_watchguard": angel_watchguard_posture(),
        "grok_build": grok_build_posture(),
        "hostess7_command": _slice_hostess7_command(),
        "hostess7_autonomous": _slice_hostess7_autonomous(),
        "queen_verdict": _queen_verdict(seed),
    }
    _save_json(PANEL, doc)
    return doc


def _queen_verdict(seed: dict[str, Any]) -> str:
    gm = gate_manifest(seed)
    cm = codec_manifest(seed)
    p = posture()
    if not p["queen_enabled"]:
        return "QUEEN_OFF"
    if not gm["all_held"]:
        return "GATES_INCOMPLETE"
    if not cm["mp4_mandatory"] or "video/mp4" not in cm["container"]:
        return "MP4_MISSING"
    if not p["hold_all_gates"]:
        return "HOLD_ALL_GATES_OFF"
    return "QUEEN_READY"


def panel_json() -> dict[str, Any]:
    if PANEL.is_file():
        try:
            cached = json.loads(PANEL.read_text(encoding="utf-8"))
            if cached.get("schema") == "field-queen-browser/v1":
                return cached
        except (OSError, json.JSONDecodeError):
            pass
    return build_panel()


def gate_check(gate_id: str) -> dict[str, Any]:
    seed = load_seed()
    for g in seed.get("gates") or []:
        if g.get("id") == gate_id:
            return {
                "gate_id": gate_id,
                "held": bool(g.get("held")),
                "verdict": "HELD" if g.get("held") else "UNHELD",
                "layer": g.get("layer"),
                "label": g.get("label"),
            }
    return {"gate_id": gate_id, "verdict": "UNKNOWN", "held": False}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "build":
        print(json.dumps(build_panel(), ensure_ascii=False))
        return 0
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    if cmd == "gates":
        print(json.dumps(gate_manifest(), ensure_ascii=False))
        return 0
    if cmd == "codecs":
        print(json.dumps(codec_manifest(), ensure_ascii=False))
        return 0
    if cmd == "gate" and len(sys.argv) > 2:
        print(json.dumps(gate_check(sys.argv[2].strip()), ensure_ascii=False))
        return 0
    if cmd == "sovereign":
        print(json.dumps({"schema": "field-queen-sovereign/v1", "updated": _now(), **sovereign_posture()}, ensure_ascii=False))
        return 0
    if cmd == "gate-proc" and len(sys.argv) > 2:
        print(json.dumps(gate_capture_process(sys.argv[2]), ensure_ascii=False))
        return 0
    if cmd == "gate-telemetry" and len(sys.argv) > 2:
        proc = sys.argv[3] if len(sys.argv) > 3 else ""
        print(json.dumps(gate_telemetry_host(sys.argv[2], proc), ensure_ascii=False))
        return 0
    if cmd == "angel":
        print(json.dumps({"schema": "queen-angel-watchguard/v1", "updated": _now(), **angel_watchguard_posture()}, ensure_ascii=False))
        return 0
    if cmd == "field-env":
        print(json.dumps(field_queen_env(), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: field-queen-browser.py [build|json|gates|codecs|gate <id>|sovereign|angel|field-env|gate-proc <proc>|gate-telemetry <host> [proc]]"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())