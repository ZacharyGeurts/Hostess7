#!/usr/bin/env pythong
"""Field stack layer posture — NEXUS C2 → ZNetwork → Queen CANVAS → Queen → AmmoOS. Hardware no-break."""
from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(ROOT)))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
DOCTRINE = INSTALL / "data" / "field-stack-layer-doctrine.json"
LOOPBACK = os.environ.get("NEXUS_LOOPBACK", "127.0.0.1")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def _port_open(host: str, port: int, timeout: float = 0.35) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _http_ok(url: str, timeout: float = 1.2) -> bool:
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except (urllib.error.URLError, OSError, ValueError):
        return False


def _import_posture(script: str, argv: list[str]) -> dict[str, Any]:
    candidates = [
        INSTALL / script,
        ROOT / script,
        (ROOT.parent / script).resolve(),
        (ROOT.parent / "Queen" / "lib" / Path(script).name),
        (ROOT.parent / "NewLatest" / "Queen" / "lib" / Path(script).name),
    ]
    path = next((p.resolve() for p in candidates if p.is_file()), None)
    if path is None:
        return {"ok": False, "skipped": True}
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(f"stack_{path.stem}", str(path))
        if not spec or not spec.loader:
            return {"ok": False, "skipped": True}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "posture"):
            prev = os.environ.get("FIELD_STACK_LAYER_POSTURE")
            os.environ["FIELD_STACK_LAYER_POSTURE"] = "1"
            try:
                out = mod.posture()
            finally:
                if prev is None:
                    os.environ.pop("FIELD_STACK_LAYER_POSTURE", None)
                else:
                    os.environ["FIELD_STACK_LAYER_POSTURE"] = prev
            if isinstance(out, dict):
                return out
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": False, "skipped": True}


def _layer_status(layer: dict[str, Any]) -> dict[str, Any]:
    lid = layer.get("id", "")
    host = LOOPBACK
    out: dict[str, Any] = {
        "id": lid,
        "label": layer.get("label", lid),
        "role": layer.get("role", ""),
        "ok": False,
    }

    if lid == "hardware":
        hw = _import_posture("lib/hardware-wire.py", ["json"])
        guard = (DOCTRINE_DOC.get("hardware_guard") or {}) if DOCTRINE_DOC else {}
        out["ok"] = guard.get("no_breaks", True) and guard.get("own_drivers", True)
        out["no_breaks"] = guard.get("no_breaks", True)
        out["never_harm_os"] = guard.get("never_harm_os", True)
        out["hardware_wire"] = hw.get("ok", hw.get("running", False))
        return out

    if lid == "nexus_c2":
        port = int(layer.get("port") or 9477)
        out["port"] = port
        out["panel_up"] = _port_open(host, port)
        out["field_up"] = _http_ok(f"http://{host}:{port}/field")
        out["command_up"] = _http_ok(f"http://{host}:{port}/command")
        out["ok"] = out["panel_up"] and (out["field_up"] or out["command_up"])
        return out

    if lid == "kilroy":
        core = _load(STATE / "kilroy-core.json", {})
        net = _load(STATE / "kilroy-net-lane.json", {})
        out["pc_core"] = core.get("role") == "pc_core" or bool(core)
        out["znetwork_absorbed"] = core.get("znetwork_absorbed", True)
        out["network_lane"] = bool(net.get("active")) or core.get("network_lane", 0) == 1
        out["loopback"] = core.get("loopback_authority", LOOPBACK)
        out["panel_url"] = core.get("nexus_c2_panel")
        out["ok"] = out["pc_core"] or out["network_lane"] or _http_ok(f"http://{host}:9477/field")
        return out

    if lid == "znetwork":
        zn = _load(STATE / "znetwork-status.json", {})
        rel = _load(STATE / "znetwork-relayer.json", {})
        op = _load(STATE / "znetwork-operator.json", {})
        pipe = int(zn.get("internet_pipe_percent") or rel.get("internet_pipe_percent") or 0)
        target = int(layer.get("internet_pipe_percent_target") or 100)
        relayer = rel.get("enabled") is True or rel.get("active") is True or os.environ.get("ZNETWORK_RELAYER", "1") != "0"
        running = zn.get("running") is True or op.get("running") is True or relayer
        out["running"] = running
        out["relayer"] = relayer
        out["internet_pipe_percent"] = pipe if pipe else (target if running and relayer else 0)
        out["ok"] = running or relayer
        return out

    if lid == "queen_canvas":
        canvas: dict[str, Any] = {"ok": False, "skipped": True}
        for script in (
            "Queen/lib/queen-canvas-renderer.py",
            "../Queen/lib/queen-canvas-renderer.py",
            "../NewLatest/Queen/lib/queen-canvas-renderer.py",
        ):
            canvas = _import_posture(script, ["json"])
            if not canvas.get("skipped"):
                break
        out["technology"] = "AMOURANTHRTX"
        out["is_gui"] = False
        out["default_canvas"] = canvas.get("default_canvas", "CANVAS")
        out["desktop_comp_shader"] = canvas.get("desktop_comp_shader", False)
        out["os_shaders_ok"] = all(
            s.get("exists") for s in (canvas.get("os_shaders") or []) if isinstance(s, dict)
        ) if canvas.get("os_shaders") else False
        out["engines_present"] = canvas.get("engines_present", False)
        out["canvas_posture"] = canvas
        out["ok"] = canvas.get("ok", False) or canvas.get("amouranthrtx_present", False)
        return out

    if lid == "queen":
        port = int(layer.get("port") or 9481)
        shell = str(layer.get("shell") or "/world/browser.html")
        out["port"] = port
        out["shell_up"] = _http_ok(f"http://{host}:{port}{shell}")
        out["guide_up"] = _http_ok(f"http://{host}:{port}/world/queen-browser-guide.html")
        gates = INSTALL / "data" / "field-queen-gates-seed.json"
        out["gates_sealed"] = gates.is_file()
        out["ok"] = out["shell_up"] and out["gates_sealed"]
        out["standalone"] = layer.get("role") == "standalone_secure_browser" or not (layer.get("contains") or [])
        out["contains_ammoos"] = "ammoos" in (layer.get("contains") or [])
        return out

    if lid == "ammoos":
        out["tier"] = layer.get("tier") or "sovereign_core"
        out["fused_with"] = layer.get("fused_with") or ["nexus_c2", "kilroy"]
        out["loopback"] = layer.get("loopback") or LOOPBACK
        out["host_desktop"] = _http_ok(f"http://{out['loopback']}:9477/field")
        out["view"] = _http_ok(f"http://{out['loopback']}:9481/world/view.html")
        out["ok"] = out["host_desktop"]
        return out

    if lid == "ammoos_blocks":
        blocks = _load(STATE / "field-ammoos-blocks-panel.json", {})
        stack_meld = _load(STATE / "field-sovereign-stack-meld-panel.json", {})
        out["parent"] = layer.get("parent") or "ammoos"
        out["block_count"] = blocks.get("block_count")
        out["stack_held"] = bool(blocks.get("stack_held"))
        out["chips_held"] = bool((blocks.get("chips_block") or {}).get("held"))
        out["thermal_safe"] = blocks.get("thermal_safe", True)
        out["no_interloper"] = bool(layer.get("tier") == "ammoos_blocks")
        out["ok"] = out["stack_held"] or bool(blocks.get("ok")) or bool(stack_meld.get("ok"))
        return out

    return out


DOCTRINE_DOC: dict[str, Any] = {}


def posture() -> dict[str, Any]:
    global DOCTRINE_DOC
    for path in (DOCTRINE, ROOT / "data" / "field-stack-layer-doctrine.json"):
        if path.is_file():
            DOCTRINE_DOC = _load(path, {})
            break

    layers_in = DOCTRINE_DOC.get("layers_bottom_up") or []
    layers_out: list[dict[str, Any]] = []
    for layer in layers_in:
        layers_out.append(_layer_status(layer))

    all_ok = all(l.get("ok") for l in layers_out if l.get("id") != "hardware") if layers_out else False
    hw = next((l for l in layers_out if l.get("id") == "hardware"), {})
    hardware_safe = hw.get("no_breaks", True) and hw.get("never_harm_os", True)

    sov_doc = _load(INSTALL / "data" / "field-sovereign-stack-meld-doctrine.json", {})
    stack_meld = _load(STATE / "field-sovereign-stack-meld-panel.json", {})
    tier_order = sov_doc.get("tier_order") or [
        "hardware",
        "sovereign_core",
        "ammoos_blocks",
        "queen_shell",
    ]
    visible_layers = [l for l in layers_out if not (l.get("id") == "znetwork")]
    return {
        "schema": "field-stack-layer/v1",
        "ok": all_ok and hardware_safe,
        "ts": _now(),
        "motto": DOCTRINE_DOC.get("motto", ""),
        "statement": DOCTRINE_DOC.get("statement", ""),
        "hardware_safe": hardware_safe,
        "sovereign_core_fused": ["nexus_c2", "kilroy", "ammoos"],
        "queen_shell_outer_only": True,
        "stack_tight": bool(stack_meld.get("stack_tight")),
        "sovereign_stack_sealed": bool(stack_meld.get("sealed")),
        "sovereign_gaps": stack_meld.get("gaps") or [],
        "layer_order": tier_order,
        "layers": visible_layers,
        "defense_chain": DOCTRINE_DOC.get("defense_chain") or [],
        "loopback_authority": LOOPBACK,
        "sovereign_stack_meld": stack_meld.get("schema"),
    }


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "posture", "status"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    print("usage: field-stack-layer.py [json]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())