#!/usr/bin/env pythong
"""NEXUS Field Clipboard Wire — hardware-secured copy/paste, all chords, all editor souls."""
from __future__ import annotations

import glob
import json
import os
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

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
SG_ROOT = Path(os.environ.get("GROK16_SG_ROOT", os.environ.get("SG_ROOT", INSTALL.parent.parent)))
DOCTRINE = INSTALL / "data" / "field-clipboard-doctrine.json"
PANEL_JSON = STATE / "field-clipboard-wire.json"
SCHEME_JSON = STATE / "field-clipboard-scheme.json"
HISTORY_JSON = STATE / "field-clipboard-history.json"
ALERTS = STATE / "field-clipboard-alerts.jsonl"

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


def _push_history(text: str, *, action: str = "copy") -> dict[str, Any]:
    if not _policy().get("historic_ring", True):
        return {"ok": False, "skipped": "historic_ring_disabled"}
    if not text or not str(text).strip():
        return {"ok": False, "skipped": "empty"}
    doc = _load_history()
    entries: list[dict[str, Any]] = list(doc.get("entries") or [])
    preview = str(text)[: _historic_preview_len()]
    entry = {
        "ts": _now(),
        "action": action,
        "preview": preview,
        "length": len(str(text)),
        "secured": True,
    }
    if entries and entries[0].get("preview") == preview and entries[0].get("length") == entry["length"]:
        return {"ok": True, "deduped": True, "count": len(entries)}
    entries.insert(0, entry)
    entries = entries[: _historic_max()]
    doc["entries"] = entries
    doc["cursor"] = 0
    _save_history(doc)
    vault = _run_sclip("copy", str(text))
    return {"ok": True, "count": len(entries), "vault": vault.get("ok", False)}


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


def _active_scheme() -> str:
    env = os.environ.get("NEXUS_CLIPBOARD_SCHEME", "").strip()
    if env:
        return env
    saved = _load(SCHEME_JSON, {})
    if saved.get("scheme"):
        return str(saved["scheme"])
    return str((_doctrine().get("policy") or {}).get("default_scheme") or "standard")


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
    }
    _save(PANEL_JSON, doc)
    return doc


def panel_json() -> dict[str, Any]:
    if PANEL_JSON.is_file():
        doc = _load(PANEL_JSON, {})
        if doc.get("schema") == "field-clipboard-wire/v1":
            return doc
    return enforce(kill=False)


def set_scheme(scheme: str) -> dict[str, Any]:
    schemes = (_doctrine().get("schemes") or {})
    if scheme not in schemes:
        return {"ok": False, "error": "unknown_scheme", "scheme": scheme, "known": sorted(schemes.keys())}
    _save(SCHEME_JSON, {"scheme": scheme, "updated": _now()})
    return {"ok": True, "scheme": scheme, "bindings": len(_resolve_scheme_bindings(scheme))}


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
    return {"ok": False, "error": "unknown_action", "action": name}


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
    if cmd == "listen":
        once = "--once" in sys.argv[2:]
        return _evdev_listen(once=once)
    print(json.dumps({
        "error": "usage: field-clipboard-wire.py [json|enforce|scan|scheme|bindings|action|listen]",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())