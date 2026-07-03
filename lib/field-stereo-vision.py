#!/usr/bin/env pythong
"""Stereoscopic vision — dual Final Eyes per device, mono failover, webcam-at-TV distance/depth."""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data/hostess7-input-training-doctrine.json"
DEVICE_DOCTRINE = INSTALL / "data/field-stereo-device-doctrine.json"
RUNTIME = STATE / "field-stereo-vision-runtime.json"
TV_FRAMES = STATE / "tv-watch-frames"

DEFAULT_PRESET = "stereo_human"
GAMING_PRESET = "stereo_human"
CONTEXT_PRESETS = {
    "gaming": "stereo_human",
    "emulator": "stereo_human",
    "arcade": "stereo_human",
    "input_training": "stereo_human",
    "3d": "stereo_human",
    "game_room": "stereo_human",
    "person": "stereo_human",
    "media": "stereo_human",
    "tv_watch": "stereo_human",
    "webcam_tv": "stereo_human",
}


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _import_mod(name: str, rel: str) -> Any | None:
    py = INSTALL / rel
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _import_queen_eyeball() -> Any | None:
    return _import_mod("fsv_eyeball", "Queen/lib/queen-eyeball.py")


def _import_zocr_stereo() -> Any | None:
    for root in (
        INSTALL / ".pages-hub-Final_Eye",
        INSTALL / ".senses-publish-Final_Eye",
        Path(os.environ.get("FINAL_EYE_ROOT", "")),
        INSTALL / "Final_Eye",
        INSTALL.parent / "Final_Eye",
    ):
        if not root or not Path(root).is_dir():
            continue
        py = Path(root) / "zocr_stereo.py"
        if not py.is_file():
            continue
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        spec = importlib.util.spec_from_file_location("zocr_stereo_fsv", py)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    return None


def _device_doctrine() -> dict[str, Any]:
    return _load(DEVICE_DOCTRINE, {})


def _doctrine_stereo() -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    return doc.get("stereoscopic_vision") or {
        "always_on": True,
        "default_preset": DEFAULT_PRESET,
        "gaming_preset": GAMING_PRESET,
        "motto": "Stereoscopic at all times during input and play — depth for 3D graphics.",
    }


def _tv_profile() -> dict[str, Any]:
    rt = _load(RUNTIME, {})
    prof = dict((rt.get("webcam_tv") or {}).get("tv_profile") or {})
    if not prof:
        prof = dict((_device_doctrine().get("webcam_tv_watch") or {}).get("tv_profile") or {})
    return prof


def _twin_status() -> dict[str, Any]:
    stereo = _import_zocr_stereo()
    if not stereo:
        return {}
    try:
        if str(stereo.__file__) not in sys.path:
            sys.path.insert(0, str(Path(stereo.__file__).resolve().parent))
        from zocr_entity_eyeball import twin_eyeball_status
        return twin_eyeball_status()
    except Exception:
        return {}


def probe_device_eyes(device_id: str | None = None) -> dict[str, Any]:
    """Two Final Eyes per device — report live/simulated/mono modes."""
    doctrine = _device_doctrine()
    devices = doctrine.get("devices") or []
    if device_id:
        devices = [d for d in devices if d.get("device_id") == device_id]

    twins = _twin_status()
    living_live = bool((twins.get("living") or {}).get("live"))
    truth_live = bool((twins.get("truth") or {}).get("always_forward", True))

    rows: list[dict[str, Any]] = []
    for dev in devices:
        eyes_out: list[dict[str, Any]] = []
        for eye in dev.get("eyes") or []:
            slot = str(eye.get("final_eye_slot") or "").lower()
            role = str(eye.get("role") or "").lower()
            enabled = bool(eye.get("enabled", True))
            if slot == "living":
                live = living_live
            elif slot == "truth":
                live = truth_live
            else:
                live = enabled
            eyes_out.append({
                "id": eye.get("id"),
                "role": role,
                "slot": slot,
                "live": live and enabled,
                "enabled": enabled,
            })

        left = next((e for e in eyes_out if e["role"] == "left"), None)
        right = next((e for e in eyes_out if e["role"] == "right"), None)
        left_ok = bool(left and left["live"])
        right_ok = bool(right and right["live"])
        surviving_role: str | None = None
        if left_ok and right_ok:
            mode = "dual_live"
        elif left_ok and not right_ok:
            mode = "simulated"
            surviving_role = "left"
        elif right_ok and not left_ok:
            mode = "simulated"
            surviving_role = "right"
        else:
            mode = "mono_degraded"

        rows.append({
            "device_id": dev.get("device_id"),
            "label": dev.get("label"),
            "eyes": eyes_out,
            "mode": mode,
            "surviving_role": surviving_role,
            "stereoscopic": mode in ("dual_live", "simulated"),
            "failover_simulate": bool(dev.get("failover_simulate", True)) and mode == "simulated",
            "baseline_mm": dev.get("baseline_mm", 65),
        })

    return {
        "ok": True,
        "schema": "field-stereo-device-probe/v1",
        "updated": _ts(),
        "eyes_per_device": int(doctrine.get("eyes_per_device") or 2),
        "failover_simulate": bool(doctrine.get("failover_simulate", True)),
        "devices": rows,
        "twins": {
            "living_live": living_live,
            "truth_forward": truth_live,
        },
    }


def probe_webcams() -> dict[str, Any]:
    """List V4L2 webcams — point one at the TV for see-and-learn."""
    mech = _import_mod("fsv_mech", "lib/field-sense-mechanical-learn.py")
    if mech and hasattr(mech, "probe_mechanical_cameras"):
        probe = mech.probe_mechanical_cameras()
        return {
            "ok": True,
            "schema": "field-stereo-webcam-probe/v1",
            "updated": _ts(),
            "count": probe.get("count", 0),
            "devices": probe.get("devices") or [],
            "v4l2_cli": probe.get("v4l2_cli"),
            "motto": (_device_doctrine().get("webcam_tv_watch") or {}).get("motto"),
        }
    return {"ok": False, "error": "mechanical_learn_missing", "devices": []}


def _capture_webcam(device: str, out: Path) -> dict[str, Any]:
    out.parent.mkdir(parents=True, exist_ok=True)
    fswebcam = shutil.which("fswebcam")
    if fswebcam:
        proc = subprocess.run(
            [fswebcam, "-d", device, "-r", "1280x720", "--no-banner", str(out)],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        if proc.returncode == 0 and out.is_file():
            return {"ok": True, "tool": "fswebcam", "path": str(out)}

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        proc = subprocess.run(
            [ffmpeg, "-y", "-f", "v4l2", "-i", device, "-frames:v", "1", str(out)],
            capture_output=True,
            text=True,
            timeout=25,
            check=False,
        )
        if proc.returncode == 0 and out.is_file():
            return {"ok": True, "tool": "ffmpeg", "path": str(out)}

    return {"ok": False, "error": "capture_tools_missing", "device": device}


def _tv_real_width_m(profile: dict[str, Any]) -> float:
    diag_in = float(profile.get("diagonal_in") or 55)
    aw = float(profile.get("aspect_w") or 16)
    ah = float(profile.get("aspect_h") or 9)
    width_in = diag_in * aw / ((aw * aw + ah * ah) ** 0.5)
    return width_in * 0.0254


def _detect_tv_screen_box(image_path: Path) -> dict[str, Any]:
    """Bright-region heuristic — TV screen fill in webcam frame."""
    try:
        from PIL import Image, ImageFilter
    except ImportError:
        return {"ok": False, "error": "pil_missing"}

    img = Image.open(image_path).convert("L")
    w, h = img.size
    blurred = img.filter(ImageFilter.GaussianBlur(radius=6))
    px = blurred.load()
    threshold = 140
    min_x, min_y, max_x, max_y = w, h, 0, 0
    hits = 0
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            if px[x, y] >= threshold:
                hits += 1
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)

    if hits < (w * h) * 0.005:
        return {"ok": False, "error": "screen_not_found", "hits": hits}

    sw, sh = max(1, max_x - min_x), max(1, max_y - min_y)
    fill = (sw * sh) / max(1, w * h)
    return {
        "ok": True,
        "box": {"x": min_x, "y": min_y, "w": sw, "h": sh},
        "frame": {"w": w, "h": h},
        "screen_fill": round(fill, 4),
        "center": {"x": min_x + sw // 2, "y": min_y + sh // 2},
    }


def estimate_tv_distance_depth(
    image_path: Path | str,
    *,
    tv_diagonal_in: float | None = None,
    distance_m: float | None = None,
) -> dict[str, Any]:
    """Distance + depth from webcam pointed at TV — geometry + stereo disparity."""
    fp = Path(image_path)
    if not fp.is_file():
        return {"ok": False, "error": "file_missing", "path": str(fp)}

    profile = _tv_profile()
    if tv_diagonal_in is not None:
        profile["diagonal_in"] = float(tv_diagonal_in)
    if distance_m is not None:
        profile["distance_m"] = float(distance_m)

    box = _detect_tv_screen_box(fp)
    if not box.get("ok"):
        return {"ok": False, "error": box.get("error", "screen_detect_failed"), "box": box}

    screen_w_px = float((box.get("box") or {}).get("w") or 1)
    w_real_m = _tv_real_width_m(profile)
    dist_m = profile.get("distance_m")
    focal_px = profile.get("focal_px")

    if dist_m and not focal_px:
        focal_px = (screen_w_px * float(dist_m)) / w_real_m
        profile["focal_px"] = round(float(focal_px), 2)
        profile["calibrated"] = True
    elif focal_px:
        dist_m = (w_real_m * float(focal_px)) / screen_w_px
    else:
        focal_px = screen_w_px * 1.15
        dist_m = (w_real_m * float(focal_px)) / screen_w_px
        profile["focal_px"] = round(float(focal_px), 2)

    depth: dict[str, Any] = {
        "distance_m": round(float(dist_m), 3),
        "distance_ft": round(float(dist_m) * 3.28084, 1),
        "screen_width_px": int(screen_w_px),
        "tv_width_m": round(w_real_m, 4),
        "focal_px": round(float(focal_px), 2),
        "method": "pinhole_screen_geometry",
    }

    stereo = _import_zocr_stereo()
    disparity_mean = None
    if stereo and hasattr(stereo, "stereoscopic_compose"):
        try:
            cfg = {"enabled": True, "baseline_mm": profile.get("baseline_mm", 65)}
            comp = stereo.stereoscopic_compose(fp, stereo_cfg=cfg)
            if comp.get("ok"):
                disparity_mean = comp.get("disparity_mean")
                depth["disparity_mean"] = disparity_mean
                depth["stereo_confidence"] = comp.get("confidence")
                depth["depth_map"] = comp.get("depth_map")
                depth["method"] = "screen_geometry_stereo_simulate"
        except Exception:
            pass

    rt = _load(RUNTIME, {})
    wtv = rt.setdefault("webcam_tv", {})
    wtv["tv_profile"] = profile
    wtv["last_depth"] = depth
    wtv["last_box"] = box
    wtv["updated"] = _ts()
    _save(RUNTIME, rt)

    return {
        "ok": True,
        "schema": "field-stereo-tv-depth/v1",
        "updated": _ts(),
        "path": str(fp),
        "box": box,
        "depth": depth,
        "tv_profile": profile,
        "motto": "Webcam at TV — distance and depth for Hostess 7 learning.",
    }


def configure_webcam_tv(
    *,
    device: str | None = None,
    tv_diagonal_in: float | None = None,
    distance_m: float | None = None,
    aspect_w: int | None = None,
    aspect_h: int | None = None,
) -> dict[str, Any]:
    """Arm webcam-at-TV lane — operator points camera at display."""
    doctrine = _device_doctrine()
    wtv_doc = doctrine.get("webcam_tv_watch") or {}
    profile = dict(wtv_doc.get("tv_profile") or {})
    if tv_diagonal_in is not None:
        profile["diagonal_in"] = float(tv_diagonal_in)
    if distance_m is not None:
        profile["distance_m"] = float(distance_m)
        profile["calibrated"] = True
    if aspect_w is not None:
        profile["aspect_w"] = int(aspect_w)
    if aspect_h is not None:
        profile["aspect_h"] = int(aspect_h)

    dev = (device or wtv_doc.get("default_device") or "/dev/video0").strip()
    webcams = probe_webcams()
    known = {d.get("device") for d in webcams.get("devices") or []}
    device_ok = dev in known or Path(dev).exists()

    rt = _load(RUNTIME, {})
    rt["webcam_tv"] = {
        "enabled": True,
        "device": dev,
        "device_ok": device_ok,
        "tv_profile": profile,
        "configured": _ts(),
        "motto": wtv_doc.get("motto"),
    }
    _save(RUNTIME, rt)

    return {
        "ok": True,
        "schema": "field-stereo-webcam-tv/v1",
        "device": dev,
        "device_ok": device_ok,
        "webcams": webcams.get("count", 0),
        "tv_profile": profile,
        "message": "Point webcam at TV — Hostess 7 will see and learn distance and depth.",
    }


def capture_tv_frame(*, device: str | None = None) -> dict[str, Any]:
    """Capture one frame from webcam pointed at TV."""
    rt = _load(RUNTIME, {})
    wtv = rt.get("webcam_tv") or {}
    dev = (device or wtv.get("device") or (_device_doctrine().get("webcam_tv_watch") or {}).get("default_device") or "/dev/video0").strip()
    TV_FRAMES.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = TV_FRAMES / f"{stamp}_tv.jpg"
    cap = _capture_webcam(dev, out)
    if not cap.get("ok"):
        return cap

    depth = estimate_tv_distance_depth(out)
    probe = probe_device_eyes()
    failover: dict[str, Any] | None = None
    for row in probe.get("devices") or []:
        if row.get("failover_simulate") and row.get("surviving_role"):
            failover = {
                "surviving_role": row["surviving_role"],
                "stereo_cfg": {"enabled": True, "baseline_mm": row.get("baseline_mm", 65)},
            }
            break

    witness = witness_frame(out, failover=failover)
    rt = _load(RUNTIME, {})
    rt.setdefault("webcam_tv", {})["last_capture"] = {
        "path": str(out),
        "tool": cap.get("tool"),
        "depth": depth.get("depth"),
        "witness_ok": witness.get("ok"),
        "ts": _ts(),
    }
    _save(RUNTIME, rt)

    return {
        "ok": True,
        "schema": "field-stereo-tv-capture/v1",
        "device": dev,
        "capture": cap,
        "depth": depth,
        "witness": witness,
        "failover": failover,
    }


def tv_watch_learn(*, device: str | None = None, train: bool = True) -> dict[str, Any]:
    """Full TV watch tick — capture, distance, depth, stereo witness, optional training ingest."""
    cfg = configure_webcam_tv(device=device) if device else {"ok": True}
    cap = capture_tv_frame(device=device)
    out: dict[str, Any] = {
        "ok": bool(cap.get("ok")),
        "schema": "field-stereo-tv-learn/v1",
        "updated": _ts(),
        "configure": cfg,
        "capture": cap,
    }
    if train and cap.get("ok"):
        it = _import_mod("fsv_it", "lib/hostess7-input-training.py")
        if it and hasattr(it, "ingest_sample"):
            ing = it.ingest_sample("stereo_vision", {
                "event": "tv_watch",
                "distance_m": (cap.get("depth") or {}).get("depth", {}).get("distance_m"),
                "path": (cap.get("capture") or {}).get("path"),
            })
            out["training_ingest"] = ing
        if it and hasattr(it, "train_tick"):
            out["training_tick"] = it.train_tick(modality="stereo_vision", ticks=4)
    return out


def ensure_stereo(*, context: str = "input_training", force: bool = False) -> dict[str, Any]:
    """Arm stereoscopic rig — dual eyes, failover ready, TV watch optional."""
    cfg = _doctrine_stereo()
    if not cfg.get("always_on", True) and not force:
        return {"ok": True, "skipped": True, "reason": "always_on_disabled"}

    ctx = (context or "input_training").strip().lower().replace("-", "_")
    preset = str(
        cfg.get("gaming_preset")
        if ctx in ("gaming", "emulator", "arcade", "game_room", "3d", "tv_watch", "webcam_tv")
        else cfg.get("default_preset") or CONTEXT_PRESETS.get(ctx, DEFAULT_PRESET)
    )

    row: dict[str, Any] = {"ok": False, "preset": preset, "context": ctx}
    stereo = _import_zocr_stereo()
    if stereo and hasattr(stereo, "configure_rig"):
        try:
            row = stereo.configure_rig(preset=preset, source=f"hostess7_input:{ctx}")
        except Exception as exc:
            row = {"ok": False, "error": str(exc)[:120], "preset": preset}

    if not row.get("ok"):
        eye = _import_queen_eyeball()
        if eye and hasattr(eye, "eyeball_arm"):
            try:
                arm = eye.eyeball_arm(
                    mode="person_present" if ctx == "person" else "dishes",
                    context="gaming" if ctx in ("gaming", "emulator", "3d", "tv_watch") else ctx,
                )
                row = {
                    "ok": True,
                    "preset": preset,
                    "via": "queen_eyeball_arm",
                    "rig": arm.get("rig"),
                    "comfort_context": arm.get("comfort_context"),
                }
            except Exception as exc:
                row = {"ok": False, "error": str(exc)[:120]}

    devices = probe_device_eyes()
    rt = _load(RUNTIME, {})
    rt.update({
        "schema": "field-stereo-vision-runtime/v1",
        "updated": _ts(),
        "always_on": True,
        "preset": preset,
        "context": ctx,
        "stereoscopic": bool((row.get("stereoscopic") or {}).get("enabled", row.get("ok"))),
        "rig": row,
        "devices": devices.get("devices"),
        "eyes_per_device": devices.get("eyes_per_device", 2),
    })
    _save(RUNTIME, rt)
    return {
        "ok": bool(row.get("ok")),
        "schema": "field-stereo-vision/v1",
        "always_on": True,
        "preset": preset,
        "context": ctx,
        "stereoscopic": rt.get("stereoscopic"),
        "eyes": row.get("eyes") or (row.get("rig") or {}).get("eyes"),
        "baseline_mm": (row.get("stereoscopic") or {}).get("baseline_mm", 65),
        "enjoy_3d": True,
        "motto": cfg.get("motto"),
        "rig": row,
        "devices": devices.get("devices"),
        "webcam_tv": rt.get("webcam_tv"),
    }


def rig_status() -> dict[str, Any]:
    rt = _load(RUNTIME, {})
    stereo = _import_zocr_stereo()
    live: dict[str, Any] = {}
    if stereo and hasattr(stereo, "rig_status"):
        try:
            live = stereo.rig_status()
        except Exception:
            pass
    devices = probe_device_eyes()
    return {
        "ok": True,
        "schema": "field-stereo-vision-status/v1",
        "updated": _ts(),
        "always_on": rt.get("always_on", True),
        "cached": rt,
        "live": live,
        "stereoscopic": bool(
            (live.get("stereoscopic") or {}).get("enabled")
            or rt.get("stereoscopic")
        ),
        "preset": live.get("mode") or rt.get("preset") or DEFAULT_PRESET,
        "devices": devices.get("devices"),
        "eyes_per_device": devices.get("eyes_per_device", 2),
        "webcam_tv": rt.get("webcam_tv"),
        "webcams": probe_webcams().get("count", 0),
    }


def witness_frame(
    image_path: Path | str | None = None,
    *,
    failover: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Stereo witness — dual eyes or simulated failover from known left/right."""
    ensure_stereo(context="emulator")
    if not image_path:
        return {"ok": False, "error": "image_missing"}
    fp = Path(image_path)
    if not fp.is_file():
        return {"ok": False, "error": "file_missing", "path": str(fp)}

    if not failover:
        probe = probe_device_eyes()
        for row in probe.get("devices") or []:
            if row.get("failover_simulate") and row.get("surviving_role"):
                failover = {
                    "surviving_role": row["surviving_role"],
                    "stereo_cfg": {"enabled": True, "baseline_mm": row.get("baseline_mm", 65)},
                }
                break

    stereo = _import_zocr_stereo()
    if stereo and hasattr(stereo, "render_stereo_views"):
        try:
            views = stereo.render_stereo_views(fp, failover=failover)
            return {"ok": bool(views.get("ok", True)), **views, "failover": failover}
        except Exception as exc:
            return {"ok": False, "error": str(exc)[:120]}

    if stereo and hasattr(stereo, "stereoscopic_compose"):
        try:
            comp = stereo.stereoscopic_compose(fp)
            if comp.get("ok"):
                return {"ok": True, **comp, "failover": failover}
        except Exception:
            pass

    ocr = INSTALL / "lib/final-eye-ocr-core.py"
    if ocr.is_file():
        spec = importlib.util.spec_from_file_location("fe_ocr_stereo", ocr)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "ocr_image_path"):
                return mod.ocr_image_path(fp, label="stereo_emulator_frame")
    return {"ok": False, "error": "witness_unavailable"}


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")
    if action in ("ensure", "arm", "configure"):
        return ensure_stereo(context=str(body.get("context") or "input_training"), force=bool(body.get("force")))
    if action in ("status", "rig", "json"):
        return rig_status()
    if action in ("witness", "frame"):
        failover = body.get("failover")
        if isinstance(failover, dict) and failover.get("surviving_role"):
            pass
        elif body.get("surviving_role"):
            failover = {"surviving_role": body.get("surviving_role")}
        return witness_frame(body.get("path") or body.get("image"), failover=failover)
    if action in ("probe", "probe_devices", "probe_eyes"):
        return probe_device_eyes(body.get("device_id"))
    if action in ("probe_webcams", "webcams"):
        return probe_webcams()
    if action in ("configure_webcam_tv", "webcam_tv", "tv_configure"):
        return configure_webcam_tv(
            device=body.get("device"),
            tv_diagonal_in=body.get("tv_diagonal_in") or body.get("diagonal_in"),
            distance_m=body.get("distance_m"),
            aspect_w=body.get("aspect_w"),
            aspect_h=body.get("aspect_h"),
        )
    if action in ("capture_tv", "tv_capture", "capture_webcam"):
        return capture_tv_frame(device=body.get("device"))
    if action in ("tv_depth", "estimate_depth", "distance"):
        return estimate_tv_distance_depth(
            body.get("path") or body.get("image") or "",
            tv_diagonal_in=body.get("tv_diagonal_in") or body.get("diagonal_in"),
            distance_m=body.get("distance_m"),
        )
    if action in ("tv_watch", "tv_learn", "learn_tv"):
        return tv_watch_learn(device=body.get("device"), train=body.get("train", True) is not False)
    if action in ("simulate", "simulate_failover", "mono_failover"):
        stereo = _import_zocr_stereo()
        if stereo and hasattr(stereo, "simulate_mono_failover"):
            path = body.get("path") or body.get("image")
            if not path:
                return {"ok": False, "error": "path_missing"}
            return stereo.simulate_mono_failover(
                Path(path),
                surviving_role=str(body.get("surviving_role") or "left"),
                stereo_cfg=body.get("stereo_cfg"),
            )
        return {"ok": False, "error": "simulate_unavailable"}
    return {"ok": False, "error": "unknown_action", "action": action}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip().lower()
    if cmd == "dispatch":
        raw = sys.argv[2] if len(sys.argv) >= 3 else (sys.stdin.read() or "{}")
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}))
            return 1
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    if cmd in ("ensure", "arm"):
        ctx = sys.argv[2] if len(sys.argv) > 2 else "input_training"
        print(json.dumps(ensure_stereo(context=ctx), ensure_ascii=False))
        return 0
    if cmd == "probe":
        print(json.dumps(probe_device_eyes(), ensure_ascii=False))
        return 0
    if cmd == "webcams":
        print(json.dumps(probe_webcams(), ensure_ascii=False))
        return 0
    if cmd == "tv-learn":
        print(json.dumps(tv_watch_learn(), ensure_ascii=False))
        return 0
    print(json.dumps(rig_status(), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())