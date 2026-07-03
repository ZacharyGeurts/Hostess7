#!/usr/bin/env python3
"""NEXUS Field Clipboard Wire — hardware-secured copy/paste, all chords, all editor souls."""
from __future__ import annotations

import base64
import glob
import hashlib
import json
import mimetypes
import os
import re
import struct
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hardware_wire_registry import WIRE_ALLOWED
from proc_threat_match import proc_hits_any

try:
    from field_programming_filetypes import clipboard_mimes, media_discern, media_status, mime_for_path
except ImportError:
    import importlib.util

    _ft_path = Path(__file__).resolve().parent / "field-programming-filetypes.py"
    _ft_spec = importlib.util.spec_from_file_location("field_programming_filetypes", _ft_path)
    _ft_mod = importlib.util.module_from_spec(_ft_spec) if _ft_spec and _ft_spec.loader else None
    if _ft_mod and _ft_spec and _ft_spec.loader:
        _ft_spec.loader.exec_module(_ft_mod)
        clipboard_mimes = _ft_mod.clipboard_mimes
        media_discern = _ft_mod.media_discern
        media_status = _ft_mod.media_status
        mime_for_path = _ft_mod.mime_for_path
    else:
        def clipboard_mimes() -> list[str]:
            return []

        def media_discern(path: str = "", *, mime: str = "") -> dict[str, Any]:
            return {"ok": False}

        def media_status() -> dict[str, Any]:
            return {"ok": False}

        def mime_for_path(path: str, *, clipboard: bool = True) -> str:
            return mimetypes.guess_type(path)[0] or "application/octet-stream"

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
SG_ROOT = Path(os.environ.get("GROK16_SG_ROOT", os.environ.get("SG_ROOT", INSTALL.parent.parent)))
DOCTRINE = INSTALL / "data" / "field-clipboard-doctrine.json"
PANEL_JSON = STATE / "field-clipboard-wire.json"
SCHEME_JSON = STATE / "field-clipboard-scheme.json"
HISTORY_JSON = STATE / "field-clipboard-history.json"
MEDIA_DIR = STATE / "field-clipboard-media"
MEDIA_INDEX = STATE / "field-clipboard-media-index.json"
ALERTS = STATE / "field-clipboard-alerts.jsonl"
_DATA_URL_RE = re.compile(r"^data:([^;,]+)?(?:;base64)?,(.*)$", re.DOTALL)

EV_KEY = 0x01
KEY_MAP = {
    "a": 30, "b": 48, "c": 46, "d": 32, "e": 18, "f": 33, "g": 34, "h": 35,
    "i": 23, "j": 36, "k": 37, "l": 38, "m": 50, "n": 49, "o": 24, "p": 25,
    "q": 16, "r": 19, "s": 31, "t": 20, "u": 22, "v": 47, "w": 17, "x": 45,
    "y": 21, "z": 44,
    "insert": 110, "delete": 111, "home": 102, "end": 107, "pageup": 104, "pagedown": 109,
}
MOD_MAP = {
    "control": (29, 97),
    "shift": (42, 54),
    "alt": (56, 100),
    "meta": (125, 126),
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



def _enabled() -> bool:
    env = os.environ.get("NEXUS_CLIPBOARD_WIRE", os.environ.get("NEXUS_HARDWARE_WIRE", "1"))
    return env not in ("0", "false", "no", "off")


def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _save(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _doctrine() -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    if doc.get("schema") == "field-clipboard-doctrine/v1":
        return doc
    fallback = Path(__file__).resolve().parent.parent / "data" / "field-clipboard-doctrine.json"
    return _load(fallback, {})


def _secure_script() -> Path | None:
    rel = (_doctrine().get("secure_backend") or {}).get("script") or "memes/Security/secure_clipboard.sh"
    for root in (SG_ROOT, INSTALL.parent.parent, Path("/home/default/Desktop/SG")):
        candidate = root / rel
        if candidate.is_file():
            return candidate
    return None


def _run_sclip(cmd: str, text: str | None = None, *, timeout: int = 12) -> dict[str, Any]:
    script = _secure_script()
    if not script:
        return {"ok": False, "error": "secure_clipboard_missing"}
    argv = ["bash", str(script), cmd]
    try:
        proc = subprocess.run(
            argv,
            input=text,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ},
        )
        return {
            "ok": proc.returncode == 0,
            "cmd": cmd,
            "stdout": (proc.stdout or "").strip(),
            "stderr": (proc.stderr or "").strip(),
            "code": proc.returncode,
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": str(exc), "cmd": cmd}


def _policy() -> dict[str, Any]:
    return (_doctrine().get("policy") or {})


def _historic_max() -> int:
    return int(_policy().get("historic_ring_max") or 32)


def _historic_preview_len() -> int:
    return int(_policy().get("historic_preview_chars") or 48)


def _ghost_mode() -> bool:
    return bool(_policy().get("ghost_mode", True))


def _load_history() -> dict[str, Any]:
    doc = _load(HISTORY_JSON, {})
    if doc.get("schema") != "field-clipboard-history/v1":
        return {"schema": "field-clipboard-history/v1", "entries": [], "cursor": 0}
    return doc


def _save_history(doc: dict[str, Any]) -> None:
    doc["schema"] = "field-clipboard-history/v1"
    doc["updated"] = _now()
    _save(HISTORY_JSON, doc)


def _media_max_bytes() -> int:
    return int(_policy().get("media_max_bytes") or 67_108_864)


def _media_ring_max() -> int:
    return int(_policy().get("media_ring_max") or 12)


def _allowed_mimes() -> set[str]:
    raw = list(_policy().get("media_mimes") or [])
    try:
        raw.extend(clipboard_mimes())
    except Exception:
        pass
    return {str(x).lower() for x in raw if x}


def _kind_from_mime(mime: str) -> str:
    m = mime.lower()
    if m.startswith("image/"):
        return "image"
    if m.startswith("video/"):
        return "video"
    if m.startswith("audio/"):
        return "audio"
    return "file"


def _parse_data_url(data_url: str) -> tuple[str, bytes]:
    m = _DATA_URL_RE.match(str(data_url or "").strip())
    if not m:
        raise ValueError("bad_data_url")
    mime = (m.group(1) or "application/octet-stream").split(";")[0].strip().lower()
    payload = m.group(2) or ""
    if ";base64" in str(data_url).lower():
        return mime, base64.b64decode(payload)
    from urllib.parse import unquote_to_bytes

    return mime, unquote_to_bytes(payload)


def _load_media_index() -> dict[str, Any]:
    doc = _load(MEDIA_INDEX, {})
    if doc.get("schema") != "field-clipboard-media/v1":
        return {"schema": "field-clipboard-media/v1", "active_id": None, "entries": []}
    return doc


def _save_media_index(doc: dict[str, Any]) -> None:
    doc["schema"] = "field-clipboard-media/v1"
    doc["updated"] = _now()
    _save(MEDIA_INDEX, doc)


def _media_path(media_id: str) -> Path:
    safe = re.sub(r"[^a-zA-Z0-9_-]", "", str(media_id))[:64]
    return MEDIA_DIR / f"{safe}.bin"


def _media_preview_b64(data: bytes, mime: str) -> str | None:
    if not mime.startswith("image/"):
        return None
    if len(data) > 2_000_000:
        return None
    return base64.b64encode(data).decode("ascii")


def _push_history_entry(
    *,
    action: str = "copy",
    kind: str = "text",
    preview: str = "",
    length: int = 0,
    media_id: str | None = None,
    mime: str | None = None,
) -> dict[str, Any]:
    if not _policy().get("historic_ring", True):
        return {"ok": False, "skipped": "historic_ring_disabled"}
    doc = _load_history()
    entries: list[dict[str, Any]] = list(doc.get("entries") or [])
    entry = {
        "ts": _now(),
        "action": action,
        "kind": kind,
        "preview": preview[: _historic_preview_len()],
        "length": length,
        "secured": True,
    }
    if media_id:
        entry["media_id"] = media_id
    if mime:
        entry["mime"] = mime
    if entries and entries[0].get("kind") == kind and entries[0].get("media_id") == media_id and entries[0].get("preview") == entry["preview"]:
        return {"ok": True, "deduped": True, "count": len(entries)}
    entries.insert(0, entry)
    entries = entries[: _historic_max()]
    doc["entries"] = entries
    doc["cursor"] = 0
    _save_history(doc)
    return {"ok": True, "count": len(entries)}


def _push_history(text: str, *, action: str = "copy") -> dict[str, Any]:
    if not text or not str(text).strip():
        return {"ok": False, "skipped": "empty"}
    ring = _push_history_entry(action=action, kind="text", preview=str(text), length=len(str(text)))
    vault = _run_sclip("copy", str(text))
    ring["vault"] = vault.get("ok", False)
    return ring


def copy_media_bytes(data: bytes, mime: str, *, name: str = "", action: str = "copy_media") -> dict[str, Any]:
    if not _policy().get("media_vault", True):
        return {"ok": False, "error": "media_vault_disabled"}
    mime = (mime or "application/octet-stream").split(";")[0].strip().lower()
    allowed = _allowed_mimes()
    if name:
        hinted = mime_for_path(name, clipboard=True)
        if hinted and hinted != "application/octet-stream":
            mime = hinted
    if allowed and mime not in allowed and not any(
        mime.startswith(p) for p in ("image/", "video/", "audio/", "application/")
    ):
        guess = mimetypes.guess_type(name or "file.bin")[0]
        if guess:
            mime = guess.lower()
    meta = media_discern(name or f"blob.{mime.split('/')[-1]}", mime=mime)
    if len(data) > _media_max_bytes():
        return {"ok": False, "error": "media_too_large", "max_bytes": _media_max_bytes(), "size": len(data)}
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(data).hexdigest()[:16]
    media_id = digest
    path = _media_path(media_id)
    path.write_bytes(data)
    kind = _kind_from_mime(mime)
    preview = name or f"{kind}:{mime}"
    preview_b64 = _media_preview_b64(data, mime)
    idx = _load_media_index()
    entries = [e for e in list(idx.get("entries") or []) if e.get("id") != media_id]
    entries.insert(
        0,
        {
            "id": media_id,
            "mime": mime,
            "kind": kind,
            "size": len(data),
            "name": name or "",
            "format": meta.get("format") if meta.get("ok") else None,
            "format_label": meta.get("label") if meta.get("ok") else None,
            "family": meta.get("family") if meta.get("ok") else None,
            "variants": meta.get("variants") if meta.get("ok") else [],
            "preview": (meta.get("label") or preview)[: _historic_preview_len()],
            "preview_b64": preview_b64,
            "ts": _now(),
        },
    )
    entries = entries[: _media_ring_max()]
    idx["entries"] = entries
    idx["active_id"] = media_id
    _save_media_index(idx)
    hist = _push_history_entry(
        action=action,
        kind=kind,
        preview=preview,
        length=len(data),
        media_id=media_id,
        mime=mime,
    )
    return {
        "ok": True,
        "action": action,
        "media_id": media_id,
        "mime": mime,
        "kind": kind,
        "size": len(data),
        "media_url": f"/api/field-clipboard/media?id={media_id}",
        "preview_b64": preview_b64,
        "format": meta.get("format") if meta.get("ok") else None,
        "format_label": meta.get("label") if meta.get("ok") else None,
        "family": meta.get("family") if meta.get("ok") else None,
        "variants": meta.get("variants") if meta.get("ok") else [],
        "historic": hist,
        "count": len(entries),
    }


def copy_media_body(body: dict[str, Any]) -> dict[str, Any]:
    mime = str(body.get("mime") or "").strip().lower()
    name = str(body.get("name") or body.get("filename") or "").strip()
    data: bytes | None = None
    if body.get("media_b64"):
        try:
            data = base64.b64decode(str(body.get("media_b64")))
        except (ValueError, TypeError):
            return {"ok": False, "error": "bad_media_b64"}
    elif body.get("data_url"):
        try:
            mime, data = _parse_data_url(str(body.get("data_url")))
        except (ValueError, TypeError):
            return {"ok": False, "error": "bad_data_url"}
    if not data:
        return {"ok": False, "error": "missing_media"}
    if not mime:
        mime = str(body.get("mime") or "application/octet-stream")
    return copy_media_bytes(data, mime, name=name, action=str(body.get("action") or "copy_media"))


def paste_media(*, media_id: str | None = None, index: int = 0) -> dict[str, Any]:
    idx = _load_media_index()
    entries = list(idx.get("entries") or [])
    if not entries:
        return {"ok": False, "error": "media_empty"}
    target_id = media_id
    if not target_id:
        active = idx.get("active_id")
        if active:
            target_id = str(active)
        else:
            i = max(0, min(int(index), len(entries) - 1))
            target_id = str(entries[i].get("id") or "")
    row = next((e for e in entries if e.get("id") == target_id), None)
    if not row:
        return {"ok": False, "error": "media_not_found", "media_id": target_id}
    path = _media_path(str(target_id))
    if not path.is_file():
        return {"ok": False, "error": "media_file_missing", "media_id": target_id}
    data = path.read_bytes()
    mime = str(row.get("mime") or "application/octet-stream")
    idx["active_id"] = target_id
    idx["cursor"] = next((i for i, e in enumerate(entries) if e.get("id") == target_id), 0)
    _save_media_index(idx)
    b64 = base64.b64encode(data).decode("ascii")
    return {
        "ok": True,
        "media_id": target_id,
        "mime": mime,
        "kind": row.get("kind") or _kind_from_mime(mime),
        "size": len(data),
        "name": row.get("name") or "",
        "media_b64": b64,
        "data_url": f"data:{mime};base64,{b64}",
        "media_url": f"/api/field-clipboard/media?id={target_id}",
        "preview_b64": row.get("preview_b64"),
    }


def media_history(*, limit: int = 12) -> dict[str, Any]:
    idx = _load_media_index()
    entries = list(idx.get("entries") or [])[:limit]
    return {
        "ok": True,
        "schema": "field-clipboard-media/v1",
        "active_id": idx.get("active_id"),
        "count": len(entries),
        "entries": [
            {k: v for k, v in e.items() if k != "preview_b64" or len(str(v or "")) < 120_000}
            for e in entries
        ],
    }


def serve_media(media_id: str) -> tuple[int, bytes, str]:
    path = _media_path(media_id)
    if not path.is_file():
        return 404, b"", "text/plain"
    idx = _load_media_index()
    row = next((e for e in (idx.get("entries") or []) if e.get("id") == media_id), None)
    mime = str((row or {}).get("mime") or mimetypes.guess_type(path.name)[0] or "application/octet-stream")
    return 200, path.read_bytes(), mime


def media_clear() -> dict[str, Any]:
    idx = _load_media_index()
    for row in list(idx.get("entries") or []):
        try:
            _media_path(str(row.get("id") or "")).unlink(missing_ok=True)
        except OSError:
            pass
    _save_media_index({"schema": "field-clipboard-media/v1", "active_id": None, "entries": []})
    return {"ok": True, "cleared": True}


def historic_list(*, limit: int = 32) -> dict[str, Any]:
    doc = _load_history()
    entries = list(doc.get("entries") or [])[:limit]
    return {
        "schema": "field-clipboard-history/v1",
        "ok": True,
        "ghost_mode": _ghost_mode(),
        "count": len(entries),
        "entries": entries,
        "cursor": doc.get("cursor", 0),
    }


def historic_paste(index: int = 0) -> dict[str, Any]:
    doc = _load_history()
    entries = list(doc.get("entries") or [])
    if not entries:
        return {"ok": False, "error": "history_empty"}
    idx = max(0, min(int(index), len(entries) - 1))
    doc["cursor"] = idx
    _save_history(doc)
    return _run_sclip("paste")


def _scheme_state() -> dict[str, Any]:
    doc = _load(SCHEME_JSON, {})
    if not isinstance(doc, dict):
        return {}
    return doc


def _active_scheme() -> str:
    env = os.environ.get("NEXUS_CLIPBOARD_SCHEME", "").strip()
    if env:
        return env
    saved = _scheme_state()
    if saved.get("scheme"):
        return str(saved["scheme"])
    return str((_doctrine().get("policy") or {}).get("default_scheme") or "standard")


def _scheme_history() -> list[str]:
    hist = _scheme_state().get("history") or []
    return [str(x) for x in hist if x]


def _push_scheme_history(scheme: str) -> list[str]:
    max_hist = int(_policy().get("scheme_history_max") or 12)
    hist = [h for h in _scheme_history() if h != scheme]
    hist.insert(0, scheme)
    hist = hist[:max_hist]
    doc = _scheme_state()
    doc["scheme"] = scheme
    doc["history"] = hist
    doc["updated"] = _now()
    _save(SCHEME_JSON, doc)
    return hist


def list_schemes() -> dict[str, Any]:
    doctrine = _doctrine()
    schemes = doctrine.get("schemes") or {}
    order = list(_policy().get("flyout_schemes") or [])
    if not order:
        order = [k for k in schemes.keys() if k != "all"] + (["all"] if "all" in schemes else [])
    items: list[dict[str, str]] = []
    seen: set[str] = set()
    for sid in order:
        if sid in schemes and sid not in seen:
            seen.add(sid)
            row = schemes[sid] or {}
            items.append({"id": sid, "label": str(row.get("label") or sid)})
    for sid, row in schemes.items():
        if sid not in seen:
            items.append({"id": sid, "label": str((row or {}).get("label") or sid)})
    active = _active_scheme()
    labels = {x["id"]: x["label"] for x in items}
    history = _scheme_history()
    return {
        "ok": True,
        "schema": "field-clipboard-schemes/v1",
        "active": active,
        "active_label": labels.get(active, active),
        "history": history,
        "history_labels": [labels.get(h, h) for h in history],
        "schemes": items,
        "flyout_chord": str(_policy().get("flyout_chord") or "Control+Alt+Space"),
        "sovereign_on_boot": bool(_policy().get("sovereign_on_boot", True)),
    }


def _parse_chord(chord: str) -> dict[str, Any]:
    parts = [p.strip().lower() for p in chord.split("+") if p.strip()]
    mods: list[str] = []
    key = ""
    for p in parts:
        if p in ("control", "ctrl", "shift", "alt", "meta", "super", "openapple", "solidapple"):
            if p in ("ctrl", "openapple"):
                mods.append("alt" if p == "openapple" else "control")
            elif p == "solidapple":
                mods.append("meta")
            elif p == "super":
                mods.append("meta")
            else:
                mods.append(p)
        else:
            key = p
    return {"mods": sorted(set(mods)), "key": key}


def _resolve_scheme_bindings(scheme_id: str) -> list[dict[str, Any]]:
    doctrine = _doctrine()
    schemes = doctrine.get("schemes") or {}
    if scheme_id == "all":
        union = (schemes.get("all") or {}).get("union_of") or []
        out: list[dict[str, Any]] = []
        seen: set[str] = set()
        for sid in union:
            for row in _resolve_scheme_bindings(str(sid)):
                sig = json.dumps(row, sort_keys=True)
                if sig not in seen:
                    seen.add(sig)
                    out.append(row)
        return out
    scheme = schemes.get(scheme_id) or {}
    if not scheme and scheme_id not in schemes:
        scheme = schemes.get("standard") or {}
    out = []
    for row in scheme.get("bindings") or []:
        parsed = _parse_chord(str(row.get("chord") or ""))
        out.append({**row, "scheme": scheme_id, "parsed": parsed})
    extends = scheme.get("extends")
    if extends:
        out = _resolve_scheme_bindings(str(extends)) + out
    return out


def _chord_match(parsed: dict[str, Any], mods_down: set[str], key_name: str) -> bool:
    want_mods = set(parsed.get("mods") or [])
    key = str(parsed.get("key") or "").lower()
    if key_name.lower() != key:
        return False
    return want_mods == {m for m in mods_down if m in ("control", "shift", "alt", "meta")}


def _proc_comm(pid: str) -> str:
    try:
        return Path(f"/proc/{pid}/comm").read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _proc_cmdline(pid: str) -> str:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
        return raw.replace(b"\0", b" ").decode("utf-8", errors="replace").strip()
    except OSError:
        return ""


def _scan_middlemen() -> list[dict[str, Any]]:
    doctrine = _doctrine()
    middlemen = frozenset(str(x).lower() for x in (doctrine.get("middleman_procs") or []))
    hits: list[dict[str, Any]] = []
    proc_root = Path("/proc")
    if not proc_root.is_dir():
        return hits
    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        pid = entry.name
        comm = _proc_comm(pid)
        cmd = _proc_cmdline(pid)
        if comm in WIRE_ALLOWED:
            continue
        marker = proc_hits_any(middlemen, comm, cmd)
        if marker:
            hits.append({
                "pid": int(pid),
                "comm": comm,
                "marker": marker,
                "class": "clipboard",
                "ts": _now(),
            })
    return hits


def _log_alert(hit: dict[str, Any]) -> None:
    ALERTS.parent.mkdir(parents=True, exist_ok=True)
    with ALERTS.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(hit, ensure_ascii=False) + "\n")


def enforce(*, kill: bool | None = None) -> dict[str, Any]:
    if not _enabled():
        return {"schema": "field-clipboard-wire/v1", "enabled": False}
    if kill is None:
        kill = os.environ.get("NEXUS_CLIPBOARD_WIRE_KILL", "1") == "1" and os.geteuid() == 0
    hits = _scan_middlemen()
    for hit in hits:
        _log_alert(hit)
        if kill:
            try:
                os.kill(int(hit["pid"]), 9)
                hit["killed"] = True
            except (OSError, ValueError):
                hit["killed"] = False
        else:
            hit["killed"] = False
    sclip = _run_sclip("status")
    if not sclip.get("ok"):
        _run_sclip("init")
    _run_sclip("disable-managers")
    scheme = _active_scheme()
    bindings = _resolve_scheme_bindings(scheme)
    doc = {
        "schema": "field-clipboard-wire/v1",
        "updated": _now(),
        "enabled": True,
        "owner": "nexus",
        "scheme": scheme,
        "scheme_count": len((_doctrine().get("schemes") or {})),
        "binding_count": len(bindings),
        "bindings": bindings[:96],
        "middleman_policy": "no_third_party_clipboard_wire",
        "secure_vault": bool(_secure_script()),
        "sclip_status": sclip,
        "hit_count": len(hits),
        "hits": hits[:32],
        "wire_chain": (_doctrine().get("wire_chain") or []),
        "policy": "Clipboard wire secured — RAM vault, TTL wipe, all chords wired",
        "ghost_mode": _ghost_mode(),
        "ghost_visible": bool(_policy().get("ghost_visible", False)),
        "historic_ring": bool(_policy().get("historic_ring", True)),
        "historic_count": len((_load_history().get("entries") or [])),
        "media_vault": bool(_policy().get("media_vault", True)),
        "media_count": len((_load_media_index().get("entries") or [])),
        "media_active_id": _load_media_index().get("active_id"),
        "scheme_history": _scheme_history(),
        "flyout_chord": str(_policy().get("flyout_chord") or "Control+Alt+Space"),
        "sovereign_on_boot": bool(_policy().get("sovereign_on_boot", True)),
    }
    _save(PANEL_JSON, doc)
    return doc


def panel_json() -> dict[str, Any]:
    if PANEL_JSON.is_file():
        doc = _load(PANEL_JSON, {})
        if doc.get("schema") == "field-clipboard-wire/v1":
            midx = _load_media_index()
            doc["media_vault"] = bool(_policy().get("media_vault", True))
            doc["media_count"] = len(midx.get("entries") or [])
            doc["media_active_id"] = midx.get("active_id")
            return doc
    return enforce(kill=False)


def set_scheme(scheme: str) -> dict[str, Any]:
    schemes = (_doctrine().get("schemes") or {})
    if scheme not in schemes:
        return {"ok": False, "error": "unknown_scheme", "scheme": scheme, "known": sorted(schemes.keys())}
    history = _push_scheme_history(scheme)
    panel = enforce(kill=False)
    return {
        "ok": True,
        "scheme": scheme,
        "scheme_history": history,
        "bindings": len(_resolve_scheme_bindings(scheme)),
        "binding_count": panel.get("binding_count"),
        "label": str((schemes.get(scheme) or {}).get("label") or scheme),
    }


def action(name: str, text: str | None = None, *, history_index: int | None = None) -> dict[str, Any]:
    name = name.strip().lower()
    if name in ("copy", "cut"):
        if text is None:
            return {"ok": False, "error": "missing_text"}
        res = _run_sclip("copy", text)
        if res.get("ok") and _policy().get("historic_ring", True):
            ring = _push_history(str(text), action=name)
            res["historic"] = ring
        return res
    if name in ("paste", "yank", "paste_primary"):
        return _run_sclip("paste")
    if name == "paste_clip":
        return _run_sclip("paste-clip")
    if name == "clear":
        hist = _load_history()
        hist["entries"] = []
        _save_history(hist)
        return _run_sclip("clear")
    if name == "break":
        return {"ok": True, "action": "break", "note": "apple2e BREAK — no clipboard side effect"}
    if name in ("kill_region",):
        if text is None:
            return {"ok": False, "error": "missing_text"}
        res = _run_sclip("copy", text)
        if res.get("ok"):
            _push_history(str(text), action="kill_region")
        return res
    if name in ("history", "historic"):
        return historic_list()
    if name in ("history_paste", "historic_paste", "paste_history"):
        return historic_paste(history_index if history_index is not None else 0)
    if name in ("copy_media", "media_copy"):
        return {"ok": False, "error": "use_dispatch_for_media"}
    if name in ("paste_media", "media_paste"):
        return paste_media(index=history_index if history_index is not None else 0)
    if name in ("media_history", "media_list"):
        return media_history()
    if name == "media_clear":
        return media_clear()
    return {"ok": False, "error": "unknown_action", "action": name}


def handle_dispatch(body: dict[str, Any]) -> dict[str, Any]:
    act = str(body.get("action") or "").strip().lower()
    if act in ("copy_media", "media_copy"):
        return copy_media_body(body)
    if act in ("paste_media", "media_paste"):
        media_id = str(body.get("media_id") or "").strip() or None
        index = int(body.get("index") or body.get("history_index") or 0)
        return paste_media(media_id=media_id, index=index)
    if act in ("media_history", "media_list"):
        return media_history(limit=int(body.get("limit") or 12))
    if act == "media_clear":
        return media_clear()
    if act in ("schemes", "list_schemes"):
        return list_schemes()
    if act == "enforce":
        return enforce(kill=False)
    if act in ("history", "historic"):
        return historic_list(limit=int(body.get("limit") or 32))
    if act in ("history_paste", "historic_paste", "paste_history"):
        return historic_paste(int(body.get("index") or body.get("history_index") or 0))
    if body.get("scheme"):
        return set_scheme(str(body.get("scheme")))
    if act in ("panel", "json", "status"):
        return panel_json()
    if act in ("media_index", "media_filetypes", "filetypes"):
        return media_status()
    if act:
        text = body.get("text")
        if text is not None:
            return action(act, str(text), history_index=body.get("history_index"))
        return action(act, None, history_index=body.get("history_index"))
    return panel_json()


def _mod_names_from_mask(mask: int) -> set[str]:
    mods: set[str] = set()
    if mask & 0x01:
        mods.add("shift")
    if mask & 0x04:
        mods.add("control")
    if mask & 0x08:
        mods.add("meta")
    if mask & 0x10:
        mods.add("alt")
    return mods


def _key_name(code: int) -> str:
    for name, val in KEY_MAP.items():
        if val == code:
            return name
    return f"key{code}"


def _evdev_listen(*, once: bool = False) -> int:
    scheme = _active_scheme()
    bindings = _resolve_scheme_bindings(scheme)
    mod_state: set[str] = set()
    try:
        import evdev  # type: ignore
        use_evdev = True
    except ImportError:
        use_evdev = False

    if use_evdev:
        devices = [evdev.InputDevice(p) for p in evdev.list_devices()]
        if not devices:
            use_evdev = False

    fds: dict[int, str] = {}
    if not use_evdev:
        for path in sorted(glob.glob("/dev/input/event*")):
            try:
                fds[os.open(path, os.O_RDONLY | os.O_NONBLOCK)] = path
            except OSError:
                continue

    if not use_evdev and not fds:
        print(json.dumps({"ok": False, "error": "no_input_devices"}))
        return 1

    last_action = 0.0
    debounce = 0.15

    while True:
        if use_evdev:
            for dev in devices:
                try:
                    for event in dev.read():
                        if event.type != EV_KEY:
                            continue
                        code = event.code
                        val = event.value
                        if val == 1:
                            for mod, keys in MOD_MAP.items():
                                if code in keys:
                                    mod_state.add(mod)
                            key = _key_name(code)
                            now = time.monotonic()
                            if now - last_action < debounce:
                                continue
                            for row in bindings:
                                parsed = row.get("parsed") or _parse_chord(str(row.get("chord") or ""))
                                if _chord_match(parsed, mod_state, key):
                                    act = str(row.get("action") or "")
                                    if act == "break":
                                        res = action("break")
                                    else:
                                        res = action(act)
                                    last_action = now
                                    print(json.dumps({"evdev": dev.path, "chord": row.get("chord"), "result": res}))
                        elif val == 0:
                            for mod, keys in MOD_MAP.items():
                                if code in keys:
                                    mod_state.discard(mod)
                except (BlockingIOError, OSError):
                    continue
            time.sleep(0.02)
        else:
            import select as _select
            try:
                readable, _, _ = _select.select(list(fds.keys()), [], [], 0.5)
            except (ValueError, OSError):
                time.sleep(0.5)
                continue
            for fd in readable:
                try:
                    data = os.read(fd, 24)
                except OSError:
                    continue
                if len(data) < 24:
                    continue
                _sec, _usec, ev_type, code, value = struct.unpack("llHHI", data)
                if ev_type != EV_KEY:
                    continue
                if value == 1:
                    for mod, keys in MOD_MAP.items():
                        if code in keys:
                            mod_state.add(mod)
                    key = _key_name(code)
                    now = time.monotonic()
                    if now - last_action < debounce:
                        continue
                    for row in bindings:
                        parsed = row.get("parsed") or _parse_chord(str(row.get("chord") or ""))
                        if _chord_match(parsed, mod_state, key):
                            act = str(row.get("action") or "")
                            res = action(act if act != "break" else "break")
                            last_action = now
                            print(json.dumps({"evdev": fds[fd], "chord": row.get("chord"), "result": res}))
                elif value == 0:
                    for mod, keys in MOD_MAP.items():
                        if code in keys:
                            mod_state.discard(mod)
        if once:
            break
    return 0


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    if cmd == "enforce":
        print(json.dumps(enforce(), ensure_ascii=False))
        return 0
    if cmd == "scan":
        print(json.dumps({"hits": _scan_middlemen()}, ensure_ascii=False))
        return 0
    if cmd == "scheme":
        if len(sys.argv) < 3:
            print(json.dumps({"scheme": _active_scheme(), "bindings": _resolve_scheme_bindings(_active_scheme())}, ensure_ascii=False))
            return 0
        print(json.dumps(set_scheme(sys.argv[2]), ensure_ascii=False))
        return 0
    if cmd == "bindings":
        scheme = sys.argv[2] if len(sys.argv) > 2 else _active_scheme()
        print(json.dumps({"scheme": scheme, "bindings": _resolve_scheme_bindings(scheme)}, ensure_ascii=False))
        return 0
    if cmd == "action":
        act = sys.argv[2] if len(sys.argv) > 2 else ""
        text = sys.stdin.read() if not sys.stdin.isatty() else (sys.argv[3] if len(sys.argv) > 3 else None)
        hist_idx = int(sys.argv[4]) if len(sys.argv) > 4 and str(sys.argv[4]).isdigit() else None
        print(json.dumps(action(act, text, history_index=hist_idx), ensure_ascii=False))
        return 0
    if cmd == "history":
        print(json.dumps(historic_list(), ensure_ascii=False))
        return 0
    if cmd == "history-paste":
        idx = int(sys.argv[2]) if len(sys.argv) > 2 and str(sys.argv[2]).lstrip("-").isdigit() else 0
        print(json.dumps(historic_paste(idx), ensure_ascii=False))
        return 0
    if cmd == "schemes":
        print(json.dumps(list_schemes(), ensure_ascii=False))
        return 0
    if cmd == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}, ensure_ascii=False))
            return 1
        print(json.dumps(handle_dispatch(body if isinstance(body, dict) else {}), ensure_ascii=False))
        return 0
    if cmd == "serve-media":
        media_id = sys.argv[2] if len(sys.argv) > 2 else ""
        code, data, mime = serve_media(media_id)
        print(json.dumps({"ok": code == 200, "code": code, "mime": mime, "size": len(data)}, ensure_ascii=False))
        if code == 200:
            sys.stdout.buffer.write(data)
        return 0 if code == 200 else 1
    if cmd == "media":
        sub = (sys.argv[2] if len(sys.argv) > 2 else "history").strip().lower()
        if sub in ("history", "list"):
            print(json.dumps(media_history(), ensure_ascii=False))
        elif sub == "paste":
            mid = sys.argv[3] if len(sys.argv) > 3 else None
            print(json.dumps(paste_media(media_id=mid), ensure_ascii=False))
        elif sub == "clear":
            print(json.dumps(media_clear(), ensure_ascii=False))
        else:
            print(json.dumps({"error": "usage: field-clipboard-wire.py media [history|paste|clear]"}, ensure_ascii=False))
            return 1
        return 0
    if cmd == "listen":
        once = "--once" in sys.argv[2:]
        return _evdev_listen(once=once)
    print(json.dumps({
        "error": "usage: field-clipboard-wire.py [json|enforce|scan|scheme|schemes|bindings|action|listen]",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())