#!/usr/bin/env pythong
"""Hostess 7 ↔ Noti bridge — she speaks alerts, witnesses rooms, truth-gates address changes."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(_LIB.parent)))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", str(INSTALL / ".nexus-state")))
HOSTESS7 = Path(os.environ.get("HOSTESS7_ROOT", str(INSTALL / "Hostess7")))
DOCTRINE = INSTALL / "data" / "noti-doctrine.json"
PANEL = STATE / "hostess7-noti-panel.json"
INBOX = HOSTESS7 / "cache" / "fieldstorage" / "brain" / "superintel" / "agents7" / "inbox.jsonl"


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


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _noti_mod():
    py = INSTALL / "lib" / "noti.py"
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location("noti_core", py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _append_inbox(row: dict[str, Any]) -> None:
    try:
        INBOX.parent.mkdir(parents=True, exist_ok=True)
        with INBOX.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _speak(text: str) -> bool:
    vpy = INSTALL / "lib" / "hostess7-voice.py"
    if not vpy.is_file():
        return False
    try:
        proc = subprocess.run(
            [sys.executable, str(vpy), "speak", text[:420]],
            capture_output=True,
            text=True,
            timeout=120,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
        )
        doc = json.loads(proc.stdout or "{}")
        return bool(doc.get("ok"))
    except (json.JSONDecodeError, subprocess.TimeoutExpired, OSError):
        return False


def relay_event(event: str, *, message: str, noti_id: str | None = None, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    """Hostess 7 witnesses Noti — inbox + optional sovereign voice."""
    doctrine = _load(DOCTRINE, {})
    spoken = False
    voice_line = message
    if event in ("address_reset_requested", "alert_ingested", "notification_pending"):
        voice_line = (
            f"Noti alert — {message}. "
            "Red circle stays by the clock for twenty-four hours. You may accept or deny."
        )
        spoken = _speak(voice_line)
    _append_inbox({
        "schema": "hostess7-noti/v1",
        "event": event,
        "noti_id": noti_id,
        "message": message,
        "spoken": spoken,
        "meta": meta or {},
    })
    return {
        "ok": True,
        "event": event,
        "spoken": spoken,
        "voice_line": voice_line if spoken else None,
        "hostess7_authority": doctrine.get("hostess7_authority"),
    }


def bridge_field_io_notify(notify_doc: dict[str, Any]) -> dict[str, Any]:
    """When field-io-packet signals ready — surface through Noti + Hostess7 voice."""
    mod = _noti_mod()
    if not mod:
        return {"ok": False, "error": "noti_missing"}
    latest = notify_doc.get("latest") or {}
    if not notify_doc.get("notify"):
        return {"ok": True, "skipped": True, "reason": "no_notify"}
    msg = (
        f"Field packet ready — {latest.get('verb') or 'output'}. "
        "Pull when you want; I will not await."
    )
    out = mod.ingest_alert(kind="field_io_packet", message=msg, source="field-io-packet", speak=False)
    relay = relay_event("alert_ingested", message=msg, noti_id=out.get("noti_id"), meta=latest)
    return {"ok": True, "noti": out, "hostess7": relay}


def handle_address_reset(new_address: str, *, person: str = "operator") -> dict[str, Any]:
    mod = _noti_mod()
    if not mod:
        return {"ok": False, "error": "noti_missing"}
    out = mod.request_address_reset(new_address, person=person)
    if out.get("ok"):
        relay = relay_event(
            "address_reset_requested",
            message=f"Address change proposed for {person}. Accept on desktop after forty-eight hour cooldown.",
            noti_id=out.get("noti_id"),
        )
        out["hostess7"] = relay
    return out


def ensure_person_rooms() -> dict[str, Any]:
    """Seed one mirrored room per known person in people registry."""
    mod = _noti_mod()
    if not mod:
        return {"ok": False, "error": "noti_missing"}
    created = 0
    people_py = HOSTESS7 / "scripts" / "field_people_registry.py"
    names: list[str] = ["ZacharyGeurts", "Hostess7"]
    if people_py.is_file():
        try:
            spec = importlib.util.spec_from_file_location("people_reg_noti", people_py)
            if spec and spec.loader:
                pm = importlib.util.module_from_spec(spec)
                sys.path.insert(0, str(people_py.parent))
                spec.loader.exec_module(pm)
                if hasattr(pm, "ensure_registry"):
                    pm.ensure_registry(seed=False)
                if hasattr(pm, "list_entities"):
                    for ent in pm.list_entities() or []:
                        n = str(ent.get("name") or ent.get("id") or "")
                        if n:
                            names.append(n)
        except Exception:
            pass
    seen: set[str] = set()
    for name in names:
        key = name.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        r = mod.person_room(key)
        if r.get("created"):
            created += 1
    panel = mod.build_panel(write=True)
    return {"ok": True, "rooms_seeded": len(seen), "rooms_created": created, "panel": panel}


def build_panel(*, write: bool = True) -> dict[str, Any]:
    mod = _noti_mod()
    noti_panel = mod.build_panel(write=False) if mod else {}
    tb = noti_panel.get("taskbar") or {}
    sysc = {}
    sc_py = INSTALL / "lib" / "hostess7-system-control.py"
    if sc_py.is_file():
        try:
            spec = importlib.util.spec_from_file_location("h7_sysc_noti", sc_py)
            if spec and spec.loader:
                sm = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(sm)
                if hasattr(sm, "commander_slice"):
                    sysc = sm.commander_slice()
        except Exception:
            pass
    doc = {
        "schema": "hostess7-noti-panel/v1",
        "updated": noti_panel.get("updated"),
        "motto": _load(DOCTRINE, {}).get("motto"),
        "tie": "Hostess 7 speaks Noti · Angel commands system · truth-gates address · witnesses mirrored rooms",
        "system_control": sysc,
        "noti": noti_panel,
        "taskbar": tb,
        "voice_on_alert": True,
        "inbox": str(INBOX),
    }
    if write:
        _save(PANEL, doc)
    return doc


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")
    mod = _noti_mod()
    if not mod:
        return {"ok": False, "error": "noti_missing"}
    if action in ("status", "json", "panel"):
        return {"ok": True, **build_panel(write=action == "panel")}
    if action == "seed_rooms":
        return ensure_person_rooms()
    if action == "address_reset":
        return handle_address_reset(
            str(body.get("new_address") or body.get("address") or ""),
            person=str(body.get("person") or "operator"),
        )
    if action == "field_io":
        return bridge_field_io_notify(body.get("notify") or body)
    if action == "relay":
        return relay_event(
            str(body.get("event") or "alert"),
            message=str(body.get("message") or ""),
            noti_id=body.get("noti_id"),
            meta=body.get("meta") if isinstance(body.get("meta"), dict) else None,
        )
    if action in ("accept", "deny", "create_room", "join_room", "post", "list_rooms", "ingest", "taskbar"):
        out = mod.dispatch(body)
        if out.get("ok") and action == "ingest":
            relay_event("alert_ingested", message=str(body.get("message") or ""), noti_id=out.get("noti_id"))
        if out.get("ok") and action == "address_reset":
            relay_event("address_reset_requested", message="Address reset queued", noti_id=out.get("noti_id"))
        return out
    return mod.dispatch(body)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}, ensure_ascii=False))
            return 1
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    if cmd == "json":
        print(json.dumps(build_panel(write=False), ensure_ascii=False))
        return 0
    if cmd == "seed":
        print(json.dumps(ensure_person_rooms(), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: hostess7-noti.py [json|seed|dispatch]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())