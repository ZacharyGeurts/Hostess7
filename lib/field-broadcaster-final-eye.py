#!/usr/bin/env pythong
"""Broadcaster ↔ Final_Eye — camera + display driver (MJPEG ingress, silent capture)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))


def _final_eye_root() -> Path:
    try:
        if str(INSTALL / "lib") not in sys.path:
            sys.path.insert(0, str(INSTALL / "lib"))
        from sg_paths import final_eye_root as _fer
        return _fer()
    except Exception:
        env = os.environ.get("FINAL_EYE_ROOT", "").strip()
        if env and Path(env).is_dir():
            return Path(env)
        for cand in (INSTALL / "Final_Eye", SG / "NewLatest" / "Final_Eye", SG / "Final_Eye"):
            if (cand / "zocr.py").is_file():
                return cand
        return INSTALL / "Final_Eye"


def final_eye_port() -> int:
    try:
        return int(os.environ.get("FINAL_EYE_PORT", os.environ.get("ZOCR_PORT", "9479")))
    except ValueError:
        return 9479


def final_eye_base_url() -> str:
    host = os.environ.get("FINAL_EYE_HOST", "127.0.0.1").strip() or "127.0.0.1"
    return f"http://{host}:{final_eye_port()}"


def mjpeg_url(*, profile: str = "watch", prefer: str = "auto") -> str:
    return f"{final_eye_base_url()}/api/stream/mjpeg?profile={profile}&prefer={prefer}"


def preview_url() -> str:
    return f"{final_eye_base_url()}/live"


def _http_json(method: str, path: str, body: dict[str, Any] | None = None, *, timeout: float = 6.0) -> dict[str, Any]:
    url = f"{final_eye_base_url()}{path}"
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw) if raw.strip().startswith("{") else {"ok": True, "raw": raw[:500]}
    except urllib.error.HTTPError as exc:
        try:
            raw = exc.read().decode("utf-8", errors="replace")
            doc = json.loads(raw) if raw.strip().startswith("{") else {"error": raw[:300]}
        except (OSError, json.JSONDecodeError):
            doc = {"error": str(exc)}
        doc["ok"] = False
        doc["http_status"] = exc.code
        return doc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"ok": False, "error": str(exc), "url": url}


def probe_health() -> dict[str, Any]:
    doc = _http_json("GET", "/api/health")
    doc["reachable"] = bool(doc.get("ok", doc.get("service")))
    doc["base_url"] = final_eye_base_url()
    doc["port"] = final_eye_port()
    return doc


def stream_status() -> dict[str, Any]:
    return _http_json("GET", "/api/stream/status")


def ensure_stream(*, profile: str = "watch", prefer: str = "auto") -> dict[str, Any]:
    st = stream_status()
    if st.get("running"):
        return {"ok": True, "already_running": True, "status": st, "mjpeg": mjpeg_url(profile=profile, prefer=prefer)}
    started = _http_json("POST", "/api/stream/start", {"profile": profile, "prefer": prefer}, timeout=12.0)
    return {
        "ok": bool(started.get("ok", started.get("running"))),
        "started": started,
        "mjpeg": mjpeg_url(profile=profile, prefer=prefer),
    }


def ensure_stream_straight(*, profile: str = "watch", prefer: str = "auto") -> dict[str, Any]:
    """Straight-path capture — MJPEG ingress only, no Final_Eye look/OCR in the hot path."""
    out = ensure_stream(profile=profile, prefer=prefer)
    out["mode"] = "straight_path"
    out["look_in_path"] = False
    return out


def _truth_gate() -> dict[str, Any]:
    import importlib.util
    py = Path(__file__).resolve().parent / "field-chamber-core.py"
    spec = importlib.util.spec_from_file_location("fe_fcc", py)
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.truth_gate()
    return {"pass_ok": True, "skipped": True}


def look_and_share_hostess7(*, prefer: str = "auto", label: str = "broadcaster_look") -> dict[str, Any]:
    """Final_Eye look on demand — truth-gated before sharing vision with Hostess 7."""
    gate = _truth_gate()
    if not gate.get("pass_ok"):
        return {"ok": False, "error": "truth_gate_failed", "mode": "look_path", "truth_gate": gate}
    try:
        import importlib.util
        ocr_py = INSTALL / "lib" / "final-eye-ocr-core.py"
        spec = importlib.util.spec_from_file_location("fe_ocr_look", ocr_py)
        if not spec or not spec.loader:
            return {"ok": False, "error": "ocr_core_missing", "mode": "look_path"}
        ocr = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ocr)
        if hasattr(ocr, "ocr_via_hostess7"):
            look = ocr.ocr_via_hostess7({"action": "final_eye", "subaction": "look", "prefer": prefer, "label": label})
        elif hasattr(ocr, "final_eye_look"):
            look = ocr.final_eye_look(prefer=prefer, label=label)
        else:
            look = {"ok": False, "error": "look_unavailable"}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "mode": "look_path"}
    if not look.get("ok"):
        return {"ok": False, "mode": "look_path", "look": look, "truth_gate": gate}
    excerpt = str(look.get("text") or look.get("ocr") or look.get("summary") or look.get("label") or label)[:2000]
    share: dict[str, Any] = {"shared": False, "consumer": "Hostess7"}
    try:
        growth_py = INSTALL / "lib" / "hostess7-growth.py"
        spec = importlib.util.spec_from_file_location("fe_h7_growth", growth_py)
        if spec and spec.loader:
            growth = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(growth)
            if hasattr(growth, "record_learning"):
                share = growth.record_learning(
                    "final_eye_vision_share",
                    excerpt or f"Final_Eye look: {label}",
                    source="final_eye",
                    meta={"look": {k: look.get(k) for k in ("ok", "label", "prefer", "engine") if k in look}, "broadcaster": True},
                    truth_gate=True,
                )
                share = {"shared": bool(share.get("ok")), "consumer": "Hostess7", "growth": share}
    except Exception as exc:
        share = {"shared": False, "consumer": "Hostess7", "error": str(exc)}
    return {"ok": True, "mode": "look_path", "look": look, "hostess7": share, "truth_gate": gate}


def _capture_backends() -> dict[str, Any]:
    root = _final_eye_root()
    if not (root / "zocr_capture.py").is_file():
        return {}
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("zocr_cap_bc", root / "zocr_capture.py")
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "capture_backends"):
                return mod.capture_backends()
    except Exception:
        pass
    return {}


def camera_driver() -> dict[str, Any]:
    health = probe_health()
    return {
        "role": "camera_driver",
        "primary": True,
        "product": "Final_Eye",
        "profile": "watch",
        "mjpeg": mjpeg_url(profile="watch"),
        "preview": preview_url(),
        "reachable": health.get("reachable"),
        "ffmpeg_input": ["-f", "mpjpeg", "-re", "-i", mjpeg_url(profile="watch")],
        "source_kind": "final_eye",
    }


def display_driver() -> dict[str, Any]:
    """Final_Eye is our display — silent framebuffer ingress via MJPEG watch stream."""
    health = probe_health()
    backends = _capture_backends()
    return {
        "role": "display_driver",
        "primary": True,
        "product": "Final_Eye",
        "profile": "watch",
        "mjpeg": mjpeg_url(profile="watch"),
        "preview": preview_url(),
        "reachable": health.get("reachable"),
        "silent_capture": True,
        "backends": backends,
        "ffmpeg_input": ["-f", "mpjpeg", "-re", "-i", mjpeg_url(profile="watch")],
        "source_kind": "final_eye_display",
        "replaces": "x11grab",
    }


def eye_probe() -> dict[str, Any]:
    health = probe_health()
    return {
        "ok": bool(health.get("reachable")),
        "reachable": health.get("reachable"),
        "port": final_eye_port(),
        "base_url": final_eye_base_url(),
        "mode": "straight_path",
        "health": health,
    }


def _canvas_wire() -> dict[str, Any]:
    import importlib.util
    bridge_py = INSTALL / "lib" / "field-final-eye-canvas-bridge.py"
    if not bridge_py.is_file():
        return {"ok": False, "error": "canvas_bridge_missing"}
    try:
        spec = importlib.util.spec_from_file_location("fe_canvas", bridge_py)
        if not spec or not spec.loader:
            return {"ok": False}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "canvas_probe"):
            return mod.canvas_probe()
        if hasattr(mod, "feed_descriptor"):
            return {"ok": True, "feed": mod.feed_descriptor()}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": False}


def vision_posture() -> dict[str, Any]:
    root = _final_eye_root()
    health = probe_health()
    st = stream_status() if health.get("reachable") else {}
    cam = camera_driver()
    disp = display_driver()
    canvas = _canvas_wire()
    eye_threat: dict[str, Any] = {}
    try:
        import importlib.util
        py = INSTALL / "lib" / "field-eye-threat-chamber.py"
        if py.is_file():
            spec = importlib.util.spec_from_file_location("fe_threat", py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "threat_catalog"):
                    eye_threat = mod.threat_catalog()
    except Exception:
        pass
    return {
        "schema": "field-broadcaster-final-eye/v2",
        "ok": True,
        "product": "Final_Eye",
        "routing": {
            "default": "straight_path",
            "straight_path": "MJPEG capture → CANVAS/stream — no look in hot path",
            "look_path": "On-demand look — truth-gated share with Hostess 7",
        },
        "mode": (canvas.get("link") or {}).get("mode") or (canvas.get("mode")) or "straight_path",
        "look_on_demand": True,
        "hostess7_share_on_look": True,
        "truth_before_permanency": True,
        "final_eye_root": str(root),
        "port": final_eye_port(),
        "base_url": final_eye_base_url(),
        "reachable": health.get("reachable"),
        "health": health,
        "stream": st,
        "camera": cam,
        "display": disp,
        "canvas_wire": canvas,
        "canvas_connected": bool(canvas.get("connected")),
        "mjpeg": mjpeg_url(),
        "preview": preview_url(),
        "cameras": list_cameras(),
        "displays": list_displays(),
        "eye_threats": {
            "count": eye_threat.get("count", 0),
            "catalog_schema": eye_threat.get("schema"),
            "hostess7_report": True,
        },
    }


def _capture_mod() -> Any | None:
    try:
        import importlib.util
        cap_py = INSTALL / "lib" / "field-broadcaster-capture.py"
        if not cap_py.is_file():
            return None
        spec = importlib.util.spec_from_file_location("fe_cap", cap_py)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    except Exception:
        pass
    return None


def list_displays() -> list[dict[str, Any]]:
    """Final_Eye primary display — capturable desktops from secure enumeration."""
    displays: list[dict[str, Any]] = [
        {
            "id": "final_eye_display",
            "name": "Final_Eye · sovereign display",
            "kind": "final_eye_display",
            "driver": "Final_Eye",
            "primary": True,
            "mjpeg": mjpeg_url(profile="watch"),
            "preview": preview_url(),
        }
    ]
    cap = _capture_mod()
    if cap and hasattr(cap, "enumerate_monitors"):
        for mon in cap.enumerate_monitors():
            displays.append({
                "id": mon.get("id"),
                "name": mon.get("name") or f"Desktop · {mon.get('id')}",
                "kind": "desktop_capture",
                "driver": "secure_capture",
                "capturable": True,
                "primary": bool(mon.get("primary")),
                "backend": mon.get("backend"),
            })
    return displays[:12]


def list_cameras() -> list[dict[str, Any]]:
    cams: list[dict[str, Any]] = [
        {
            "id": "final_eye",
            "name": "Final_Eye · sovereign vision",
            "kind": "final_eye",
            "driver": "Final_Eye",
            "primary": True,
            "mjpeg": mjpeg_url(profile="watch"),
            "port": final_eye_port(),
        }
    ]
    try:
        proc = subprocess.run(["v4l2-ctl", "--list-devices"], capture_output=True, text=True, timeout=6)
        dev = ""
        for line in (proc.stdout or "").splitlines():
            if line.strip() and not line.startswith("\t") and not line.startswith(" "):
                dev = line.strip().rstrip(":")
            elif "/dev/video" in line:
                cams.append({
                    "id": line.strip(),
                    "name": f"{dev or 'Camera'} ({line.strip()})",
                    "kind": "camera",
                    "driver": "v4l2",
                    "primary": False,
                })
    except (OSError, subprocess.TimeoutExpired):
        pass
    return cams[:12]


def resolve_video_source(source: dict[str, Any] | None = None) -> dict[str, Any]:
    """Pick primary video source for ffmpeg — Final_Eye display/camera default."""
    src = dict(source or {})
    kind = str(src.get("kind") or "final_eye_display")
    if kind == "desktop_capture":
        return src
    if kind in ("display", "final_eye_display") and not src.get("legacy_x11"):
        ensure_stream(profile=str(src.get("profile") or "watch"))
        return {"kind": "final_eye_display", "profile": src.get("profile") or "watch", "prefer": src.get("prefer") or "auto"}
    if kind in ("final_eye", "camera") and src.get("driver") != "v4l2":
        ensure_stream(profile=str(src.get("profile") or "watch"))
        return {"kind": "final_eye", "profile": src.get("profile") or "watch", "prefer": src.get("prefer") or "auto"}
    return src


def ffmpeg_video_input(source: dict[str, Any] | None = None) -> list[str]:
    src = resolve_video_source(source)
    kind = str(src.get("kind") or "final_eye_display")
    if kind == "desktop_capture" or src.get("driver") == "secure_capture":
        cap = _capture_mod()
        if cap and hasattr(cap, "ffmpeg_video_input"):
            return cap.ffmpeg_video_input(src)
        raise ValueError("desktop_capture_unavailable")
    if kind in ("final_eye", "final_eye_display") or src.get("id") in ("final_eye", "final_eye_display"):
        profile = str(src.get("profile") or "watch")
        prefer = str(src.get("prefer") or "auto")
        return ["-f", "mpjpeg", "-re", "-i", mjpeg_url(profile=profile, prefer=prefer)]
    if kind == "display" and src.get("legacy_x11"):
        return ["-f", "x11grab", "-framerate", "30", "-i", str(src.get("device") or ":0.0")]
    if kind == "camera":
        dev = str(src.get("device") or src.get("id") or "/dev/video0")
        if not dev.startswith("/dev/video"):
            raise ValueError("invalid_camera_device")
        return ["-f", "v4l2", "-input_format", "mjpeg", "-i", dev]
    return ["-f", "mpjpeg", "-re", "-i", mjpeg_url()]


def posture() -> dict[str, Any]:
    return vision_posture()


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "status", "driver", "vision"):
        print(json.dumps(vision_posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "ensure":
        print(json.dumps(ensure_stream(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("straight", "straight-path", "straight_path"):
        print(json.dumps(ensure_stream_straight(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("look", "look-share", "look_share"):
        print(json.dumps(look_and_share_hostess7(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "cameras":
        print(json.dumps({"ok": True, "cameras": list_cameras()}, ensure_ascii=False, indent=2))
        return 0
    if cmd == "displays":
        print(json.dumps({"ok": True, "displays": list_displays()}, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"usage": "field-broadcaster-final-eye.py [json|vision|ensure|cameras|displays]"}, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())