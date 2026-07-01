#!/usr/bin/env pythong
"""AmmoOS Broadcaster — Final_Eye vision chamber, all codecs, all platforms."""
from __future__ import annotations

import importlib.util
import json
import mimetypes
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_RECORDING_SAFE = re.compile(r"^[A-Za-z0-9._-]+\.(mkv|mp4|webm|mov|flv)$", re.I)

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))
FIELD = Path(os.environ.get("BROADCASTER_FIELD_ROOT", os.environ.get("OBS_FIELD_ROOT", SG / "OBS-Field")))
DOCTRINE = FIELD / "data" / "field-broadcaster-doctrine.json"
OBS_DOCTRINE = FIELD / "data" / "field-obs-doctrine.json"
AUDIO_DOCTRINE = INSTALL / "data" / "field-broadcaster-audio-doctrine.json"
PANEL = STATE / "field-broadcaster-panel.json"
PORTABLE = STATE / "field-broadcaster-portable"
SETTINGS = STATE / "field-broadcaster-settings.json"
RECORDINGS = PORTABLE / "recordings"


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


def _save_atomic(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _legacy_obs() -> bool:
    return os.environ.get("FIELD_BROADCASTER_LEGACY_OBS", "0") in ("1", "true", "yes")


def _chamber_mod() -> Any | None:
    path = INSTALL / "lib" / "field-broadcaster-chamber.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("field_broadcaster_chamber", path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _studio_mod() -> Any | None:
    path = INSTALL / "lib" / "field-broadcaster-studio.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("field_broadcaster_studio", path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _obs_core() -> Any:
    path = INSTALL / "lib" / "field-obs-engine.py"
    spec = importlib.util.spec_from_file_location("field_obs_engine", path)
    if not spec or not spec.loader:
        raise ImportError("field-obs.py missing")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _audio_mod() -> Any | None:
    path = INSTALL / "lib" / "field-broadcaster-audio.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("field_broadcaster_audio", path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _doctrine() -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    if not doc:
        doc = _load(OBS_DOCTRINE, {})
    return doc


def _posterity_bridge() -> dict[str, Any]:
    try:
        bridge_py = INSTALL / "lib" / "obs-threat-posterity-bridge.py"
        spec = importlib.util.spec_from_file_location("broadcaster_posterity", bridge_py)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            out = mod.panel_json()
            if isinstance(out, dict):
                out["product"] = "Broadcaster"
            return out
    except Exception:
        pass
    return _load(STATE / "obs-threat-posterity-panel.json", {})


def _with_broadcaster_env() -> dict[str, str]:
    return {
        **os.environ,
        "OBS_FIELD_ROOT": str(FIELD),
        "BROADCASTER_FIELD_ROOT": str(FIELD),
        "NEXUS_STATE_DIR": str(STATE),
        "FIELD_OBS_PORTABLE_DIR": str(PORTABLE),
        "FIELD_BROADCASTER_PORTABLE_DIR": str(PORTABLE),
    }


def ui_posture(**kwargs: Any) -> dict[str, Any]:
    obs = _obs_core()
    os.environ.update(_with_broadcaster_env())
    return obs.ui_posture(**kwargs)


def launch(*, record: bool = False, virtualcam: bool = False, studio: bool = False, go_live: bool = False) -> dict[str, Any]:
    if not _legacy_obs():
        st = _studio_mod()
        if st:
            if record:
                return {**st.start_record(), "product": "Broadcaster", "engine": "studio"}
            if go_live:
                return {**st.go_live(), "product": "Broadcaster", "engine": "studio"}
            return {"ok": True, "product": "Broadcaster", "engine": "studio", "panel": st.posture()}
    obs = _obs_core()
    os.environ.update(_with_broadcaster_env())
    out = obs.launch(record=record or go_live, virtualcam=virtualcam, studio=studio)
    if isinstance(out, dict):
        out["product"] = "Broadcaster"
        out["go_live"] = go_live or record
        out["engine"] = "obs_legacy"
    return out


def save_settings(patch: dict[str, Any]) -> dict[str, Any]:
    doctrine = _doctrine()
    allowed = {
        "ui_scale_pct", "rtx_reduce", "tier_override", "studio_mode_default",
        "echo_cancel", "noise_gate", "static_filter", "input_gain_db", "output_gain_db",
        "simple_mode",
    }
    saved = _load(SETTINGS, {})
    audio_patch = {}
    for key, val in patch.items():
        if key in allowed:
            saved[key] = val
        if key in ("echo_cancel", "noise_gate", "static_filter", "input_gain_db", "output_gain_db"):
            audio_patch[key] = val
    _save_atomic(SETTINGS, saved)
    obs = _obs_core()
    obs_patch = {k: v for k, v in patch.items() if k in ("ui_scale_pct", "rtx_reduce", "tier_override", "studio_mode_default")}
    if obs_patch:
        obs.save_settings(obs_patch)
    audio = _audio_mod()
    if audio and audio_patch and hasattr(audio, "save_settings"):
        audio.save_settings(audio_patch, apply=bool(patch.get("apply_audio")))
    return posture()


def clear_filters() -> dict[str, Any]:
    """Strip Broadcaster audio filters — passthrough OBS, no chain on launch."""
    audio = _audio_mod()
    audio_out: dict[str, Any] = {}
    if audio and hasattr(audio, "clear_chain"):
        audio_out = audio.clear_chain()
    saved = _load(SETTINGS, {})
    for key in ("echo_cancel", "noise_gate", "static_filter"):
        saved[key] = False
    saved["input_gain_db"] = 0
    saved["output_gain_db"] = 0
    _save_atomic(SETTINGS, saved)
    return {**posture(), "cleared": True, "audio": audio_out}


def _recording_roots() -> list[Path]:
    roots: list[Path] = []
    for raw in (RECORDINGS, STATE / "field-obs-portable" / "recordings"):
        try:
            r = raw.resolve()
            if r.is_dir() and r not in roots:
                roots.append(r)
        except OSError:
            pass
    return roots


def resolve_recording(name: str) -> dict[str, Any] | None:
    """Safe local recording resolve — basename only, no path traversal."""
    base = str(name or "").strip()
    if not base or not _RECORDING_SAFE.match(base):
        return None
    for root in _recording_roots():
        try:
            path = (root / base).resolve()
            if not str(path).startswith(str(root) + os.sep) and path != root:
                continue
            if path.is_file():
                mime, _ = mimetypes.guess_type(path.name)
                return {
                    "name": path.name,
                    "path": path,
                    "bytes": path.stat().st_size,
                    "mime": mime or "video/x-matroska",
                    "legacy": root.name == "recordings" and "obs-portable" in str(root),
                    "playback_url": f"/api/field-broadcaster/playback?name={path.name}",
                }
        except OSError:
            continue
    return None


def read_recording_range(path: Path, start: int, end: int) -> bytes:
    with path.open("rb") as fh:
        fh.seek(start)
        return fh.read(end - start + 1)


def parse_range_header(range_hdr: str, size: int) -> tuple[int, int] | None:
    m = re.match(r"bytes=(\d+)-(\d*)", range_hdr.strip())
    if not m:
        return None
    start = int(m.group(1))
    end = int(m.group(2)) if m.group(2) else size - 1
    end = min(end, size - 1)
    if start > end or start < 0:
        return None
    return start, end


def list_recordings() -> list[dict[str, Any]]:
    RECORDINGS.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for root in _recording_roots():
        for p in sorted(root.glob("*"), key=lambda x: x.stat().st_mtime, reverse=True):
            if not p.is_file() or p.name in seen:
                continue
            item = resolve_recording(p.name)
            if item:
                seen.add(p.name)
                out.append({
                    "name": item["name"],
                    "bytes": item["bytes"],
                    "mime": item["mime"],
                    "legacy": item.get("legacy"),
                    "playback_url": item["playback_url"],
                })
    out.sort(key=lambda r: r.get("bytes", 0), reverse=True)
    return out[:24]


def us_broadcaster_slice() -> dict[str, Any]:
    full = posture()
    engine = full.get("engine") or {}
    audio = full.get("audio") or {}
    threat = (full.get("scene_guard") or {}).get("threat_summary") or {}
    return {
        "schema": "us-broadcaster-field/v1",
        "updated": full.get("ts"),
        "motto": full.get("motto"),
        "product": "Broadcaster",
        "running": engine.get("running"),
        "plugin_installed": engine.get("plugin_installed"),
        "g16_ready": full.get("g16", {}).get("ok"),
        "encoder": full.get("encoder"),
        "audio_echo_cancel": (audio.get("settings") or {}).get("echo_cancel"),
        "audio_noise_gate": (audio.get("settings") or {}).get("noise_gate"),
        "threat_rows": threat.get("rows", 0),
        "jump": "field-broadcaster",
    }


def studio_dispatch(body: dict[str, Any]) -> dict[str, Any]:
    st = _studio_mod()
    if st and hasattr(st, "dispatch"):
        return st.dispatch(body)
    return {"ok": False, "error": "studio_missing"}


def posture() -> dict[str, Any]:
    doctrine = _doctrine()
    if not _legacy_obs():
        chamber = _chamber_mod()
        if chamber and hasattr(chamber, "build_panel"):
            doc = chamber.build_panel(write=True)
            doc["ts"] = _now()
            doc["product"] = "Broadcaster"
            doc["recordings"] = list_recordings()
            doc["settings"] = _load(SETTINGS, {"simple_mode": False})
            audio = _audio_mod()
            doc["audio"] = doc.get("audio") or (audio.posture() if audio and hasattr(audio, "posture") else {})
            _save_atomic(PANEL, doc)
            return doc
        st = _studio_mod()
        if st and hasattr(st, "posture"):
            studio_panel = st.posture()
            audio = _audio_mod()
            audio_snap = audio.posture() if audio and hasattr(audio, "posture") else {}
            saved = _load(SETTINGS, {"simple_mode": False})
            doc = {
                "schema": "field-broadcaster/v2",
                "ts": _now(),
                "ok": True,
                "product": "Broadcaster",
                "motto": "AmmoOS Broadcaster — Final_Eye display+camera, all codecs, Kick-first platforms.",
                "engine": {"backend": "chamber", "legacy_obs": False},
                "studio": studio_panel,
                "scenes": studio_panel.get("scenes"),
                "scene_count": studio_panel.get("scene_count"),
                "active_scene": studio_panel.get("active_scene"),
                "devices": studio_panel.get("devices"),
                "streaming": studio_panel.get("streaming"),
                "recording": studio_panel.get("recording"),
                "platform": studio_panel.get("platform"),
                "codecs": studio_panel.get("codecs"),
                "canvas_wire": studio_panel.get("canvas_wire"),
                "threat": studio_panel.get("threat"),
                "combinatorics": studio_panel.get("combinatorics"),
                "audio": audio_snap,
                "settings": saved,
                "recordings": list_recordings(),
                "routes": {"panel": "/field-broadcaster", "api": "/api/field-broadcaster", "chamber": "/api/field-broadcaster/chamber"},
                "posture": f"Broadcaster — {studio_panel.get('scene_count', 0)} scenes · {'LIVE' if studio_panel.get('streaming') else 'ready'}",
            }
            _save_atomic(PANEL, doc)
            return doc
    os.environ.update(_with_broadcaster_env())
    obs = _obs_core()
    obs_base = obs.posture()
    audio = _audio_mod()
    audio_snap = audio.posture() if audio and hasattr(audio, "posture") else {}
    posterity = _posterity_bridge()
    saved = _load(SETTINGS, {"simple_mode": True})
    capture = doctrine.get("capture") or {}
    engine_block = obs_base.get("obs") or {}
    threat = engine_block.get("threat_summary") or (posterity.get("threat_ledger") or {}).get("summary") or {}
    streaming = bool(engine_block.get("running"))
    scenes = 1 if engine_block.get("stack") else 0

    doc = {
        "schema": "field-broadcaster/v1",
        "ts": _now(),
        "ok": bool(obs_base.get("ok")),
        "product": doctrine.get("product") or "Broadcaster",
        "legacy_product": doctrine.get("legacy_product"),
        "motto": doctrine.get("motto"),
        "policy": doctrine.get("policy"),
        "gui": doctrine.get("gui") or {},
        "binary": obs_base.get("binary"),
        "platform": obs_base.get("platform"),
        "g16": obs_base.get("g16"),
        "ui": obs_base.get("ui"),
        "encoder": obs_base.get("encoder"),
        "portable": str(PORTABLE),
        "recordings_dir": str(RECORDINGS),
        "profile": capture.get("default_profile", "Broadcaster"),
        "collection": capture.get("default_collection", "NEXUS-C2"),
        "recordings": list_recordings(),
        "settings": saved,
        "audio": audio_snap,
        "engine": {
            "backend": (doctrine.get("engine") or {}).get("backend", "obs-studio"),
            "running": engine_block.get("running"),
            "plugin_installed": engine_block.get("field_plugin_installed"),
            "filters": engine_block.get("filters") or [],
            "scene_guard": (doctrine.get("engine") or {}).get("scene_guard_filter"),
        },
        "scene_guard": {
            "stack": engine_block.get("stack"),
            "security": engine_block.get("security") or posterity.get("security"),
            "posterity": engine_block.get("posterity") or posterity.get("posterity"),
            "threat_summary": threat,
        },
        "streaming": streaming,
        "scenes": scenes,
        "routes": {
            "panel": "/field-broadcaster",
            "api": "/api/field-broadcaster",
            "audio": "/api/field-broadcaster/audio",
            "legacy_panel": "/field-obs",
        },
        "posture": (
            f"Broadcaster — {'LIVE' if streaming else 'ready'} · "
            f"audio {audio_snap.get('backend', {}).get('name', 'chain')} · "
            f"encoder {obs_base.get('encoder', 'x264')}"
        ),
    }
    _save_atomic(PANEL, doc)
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "status", "posture"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("launch", "go-live", "golive"):
        print(json.dumps(launch(go_live=cmd != "launch"), ensure_ascii=False, indent=2))
        return 0
    if cmd == "record":
        print(json.dumps(launch(record=True), ensure_ascii=False, indent=2))
        return 0
    if cmd == "virtualcam":
        print(json.dumps(launch(virtualcam=True), ensure_ascii=False, indent=2))
        return 0
    if cmd == "studio":
        print(json.dumps(launch(studio=True), ensure_ascii=False, indent=2))
        return 0
    if cmd == "settings" and len(sys.argv) > 2:
        try:
            patch = json.loads(sys.argv[2])
        except json.JSONDecodeError:
            patch = {}
        print(json.dumps(save_settings(patch), ensure_ascii=False, indent=2))
        return 0
    if cmd == "us":
        print(json.dumps(us_broadcaster_slice(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("clear-filters", "clear_filters", "passthrough"):
        print(json.dumps(clear_filters(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "audio":
        audio = _audio_mod()
        if not audio:
            print(json.dumps({"ok": False, "error": "audio_module_missing"}))
            return 1
        sub = (sys.argv[2] if len(sys.argv) > 2 else "json").strip().lower()
        if sub == "apply":
            print(json.dumps(audio.apply_chain(), ensure_ascii=False, indent=2))
            return 0
        if sub in ("clear", "clear-filters", "passthrough"):
            print(json.dumps(audio.clear_chain(), ensure_ascii=False, indent=2))
            return 0
        print(json.dumps(audio.posture(), ensure_ascii=False, indent=2))
        return 0
    print(
        "usage: field-broadcaster.py [json|launch|go-live|record|virtualcam|studio|us|audio|settings JSON]",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())