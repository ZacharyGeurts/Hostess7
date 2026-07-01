#!/usr/bin/env pythong
"""Noti — sovereign notifier. Mirrored IRC rooms, address change alerts, immutable ledger."""
from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(_LIB.parent)))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", str(INSTALL / ".nexus-state")))
DOCTRINE = INSTALL / "data" / "noti-doctrine.json"
PANEL = STATE / "noti-panel.json"
ROOMS = STATE / "noti-rooms.json"
PENDING = STATE / "noti-pending.json"
LEDGER = STATE / "noti-ledger.jsonl"
ADDRESS_STATE = STATE / "noti-address-state.json"

_SOVEREIGN_CLOCK_MOD = None


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        import importlib.util

        py = Path(__file__).resolve().parent / "sovereign-clock.py"
        spec = importlib.util.spec_from_file_location("sovereign_clock_noti", py)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            _SOVEREIGN_CLOCK_MOD = mod
    if _SOVEREIGN_CLOCK_MOD and hasattr(_SOVEREIGN_CLOCK_MOD, "utc_z"):
        try:
            return _SOVEREIGN_CLOCK_MOD.utc_z()
        except Exception:
            pass
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_ts(ts: str) -> datetime:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)


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


def _doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {"policy": {}})


def _ledger_hash(prev: str, row: str) -> str:
    return hashlib.sha256(f"{prev}\n{row}".encode("utf-8")).hexdigest()[:32]


def _append_ledger(event: str, **fields: Any) -> dict[str, Any]:
    """Immutable append-only log — every Noti action witnessed."""
    prev = ""
    if LEDGER.is_file():
        try:
            last = LEDGER.read_text(encoding="utf-8").strip().splitlines()[-1]
            prev = json.loads(last).get("chain", "")
        except (OSError, json.JSONDecodeError, IndexError):
            prev = ""
    row = {
        "schema": "noti-ledger/v1",
        "ts": _now(),
        "event": event,
        **fields,
    }
    body = json.dumps(row, ensure_ascii=False, sort_keys=True)
    row["chain"] = _ledger_hash(prev, body)
    row["prev_chain"] = prev or None
    try:
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass
    return row


def _operator() -> dict[str, Any]:
    op_py = INSTALL / "lib" / "operator-default.py"
    if not op_py.is_file():
        return {"display_name": "Operator", "address": ""}
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("operator_default_noti", op_py)
        if not spec or not spec.loader:
            return {"display_name": "Operator", "address": ""}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "operator_doc"):
            return mod.operator_doc()
        if hasattr(mod, "load_operator"):
            return mod.load_operator()
    except Exception:
        pass
    return {"display_name": "Operator", "address": ""}


def verify_address_real(address: str) -> dict[str, Any]:
    """Basic real-address gate — street + region, not placeholder."""
    addr = (address or "").strip()
    if len(addr) < 12:
        return {"ok": False, "error": "address_too_short", "real": False}
    low = addr.lower()
    if any(p in low for p in ("example", "test@", "0.0.0.0", "localhost", "n/a", "unknown")):
        return {"ok": False, "error": "placeholder_forbidden", "real": False}
    has_digit = bool(re.search(r"\d", addr))
    has_alpha = bool(re.search(r"[A-Za-z]{3,}", addr))
    has_sep = bool(re.search(r"[,.\-]", addr))
    real = has_digit and has_alpha and has_sep
    return {"ok": real, "real": real, "address_preview": addr[:80]}


def _address_state() -> dict[str, Any]:
    doc = _load(ADDRESS_STATE, {})
    op = _operator()
    if not doc.get("current_address"):
        doc["current_address"] = op.get("address") or ""
        doc["verified"] = verify_address_real(doc["current_address"]).get("real", False)
        doc.setdefault("updated", _now())
        _save(ADDRESS_STATE, doc)
    return doc


def request_address_reset(new_address: str, *, person: str = "operator") -> dict[str, Any]:
    """48-hour cooldown before address reset takes effect."""
    policy = (_doctrine().get("policy") or {})
    hours = int(policy.get("address_reset_hours") or 48)
    check = verify_address_real(new_address)
    if not check.get("real"):
        _append_ledger("address_reset_denied", person=person, reason=check.get("error"))
        return {"ok": False, **check}

    st = _address_state()
    now = datetime.now(timezone.utc)
    cooldown_until = (now + timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    noti_id = f"noti_{uuid.uuid4().hex[:12]}"
    pending = _load(PENDING, {"items": []})
    item = {
        "id": noti_id,
        "kind": "address_change",
        "person": person,
        "old_address": st.get("current_address"),
        "new_address": new_address.strip(),
        "status": "pending_accept",
        "created": _now(),
        "cooldown_until": cooldown_until,
        "red_until": (now + timedelta(hours=int(policy.get("red_circle_hours") or 24))).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "desktop_accept_required": True,
    }
    pending.setdefault("items", []).append(item)
    _save(PENDING, pending)
    st["pending_reset"] = item
    st["cooldown_until"] = cooldown_until
    _save(ADDRESS_STATE, st)
    _append_ledger(
        "address_reset_requested",
        noti_id=noti_id,
        person=person,
        new_address_preview=new_address[:80],
        cooldown_hours=hours,
    )
    return {"ok": True, "noti_id": noti_id, "item": item, "cooldown_hours": hours}


def _find_pending(noti_id: str) -> dict[str, Any] | None:
    pending = _load(PENDING, {"items": []})
    for it in pending.get("items") or []:
        if str(it.get("id")) == noti_id:
            return it
    return None


def accept_notification(noti_id: str, *, actor: str = "operator") -> dict[str, Any]:
    item = _find_pending(noti_id)
    if not item:
        return {"ok": False, "error": "not_found"}
    if item.get("status") not in ("pending_accept", "pending"):
        return {"ok": False, "error": "not_pending", "status": item.get("status")}

    now = datetime.now(timezone.utc)
    cooldown = _parse_ts(str(item.get("cooldown_until") or ""))
    if now < cooldown:
        return {
            "ok": False,
            "error": "cooldown_active",
            "cooldown_until": item.get("cooldown_until"),
        }

    st = _address_state()
    st["current_address"] = item.get("new_address")
    st["verified"] = True
    st["accepted_at"] = _now()
    st.pop("pending_reset", None)
    st.pop("cooldown_until", None)
    _save(ADDRESS_STATE, st)

    pending = _load(PENDING, {"items": []})
    for it in pending.get("items") or []:
        if str(it.get("id")) == noti_id:
            it["status"] = "accepted"
            it["accepted_at"] = _now()
            it["accepted_by"] = actor
    _save(PENDING, pending)
    _append_ledger("notification_accepted", noti_id=noti_id, actor=actor, kind=item.get("kind"))
    return {"ok": True, "noti_id": noti_id, "address": st.get("current_address")}


def deny_notification(noti_id: str, *, actor: str = "operator") -> dict[str, Any]:
    """Deny anytime during the 24h red window."""
    item = _find_pending(noti_id)
    if not item:
        return {"ok": False, "error": "not_found"}
    if item.get("status") in ("accepted", "denied", "expired"):
        return {"ok": False, "error": "already_resolved", "status": item.get("status")}

    pending = _load(PENDING, {"items": []})
    for it in pending.get("items") or []:
        if str(it.get("id")) == noti_id:
            it["status"] = "denied"
            it["denied_at"] = _now()
            it["denied_by"] = actor
    _save(PENDING, pending)

    st = _address_state()
    st.pop("pending_reset", None)
    st.pop("cooldown_until", None)
    _save(ADDRESS_STATE, st)
    _append_ledger("notification_denied", noti_id=noti_id, actor=actor, kind=item.get("kind"))
    return {"ok": True, "noti_id": noti_id, "denied": True}


def taskbar_state() -> dict[str, Any]:
    """Red unbreakable circle by clock for 24h when address change pending; else green."""
    policy = (_doctrine().get("policy") or {})
    pending = _load(PENDING, {"items": []})
    now = datetime.now(timezone.utc)
    red_items: list[dict[str, Any]] = []
    for it in pending.get("items") or []:
        if it.get("status") not in ("pending_accept", "pending"):
            continue
        red_until = _parse_ts(str(it.get("red_until") or it.get("created") or ""))
        if red_until.tzinfo is None:
            red_until = red_until.replace(tzinfo=timezone.utc)
        if now <= red_until + timedelta(hours=int(policy.get("red_circle_hours") or 24)):
            red_items.append(it)

    state = "red_circle" if red_items else "green"
    return {
        "schema": "noti-taskbar/v1",
        "state": state,
        "icon": "noti",
        "unbreakable": bool(red_items),
        "position": "by_clock",
        "pending_count": len(red_items),
        "pending_ids": [it.get("id") for it in red_items],
        "updated": _now(),
    }


def _rooms_doc() -> dict[str, Any]:
    doc = _load(ROOMS, {"schema": "noti-rooms/v1", "rooms": []})
    doc.setdefault("rooms", [])
    return doc


def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or f"room-{uuid.uuid4().hex[:8]}"


def create_room(name: str, *, owner: str) -> dict[str, Any]:
    """IRC-like room — no mods; owner creates, anyone with real address may join."""
    doc = _rooms_doc()
    rid = _slug(name)
    for r in doc["rooms"]:
        if r.get("id") == rid:
            return {"ok": True, "room": r, "created": False}
    room = {
        "id": rid,
        "name": name.strip(),
        "owner": owner,
        "members": [owner],
        "messages": [],
        "mirrored": True,
        "no_moderators": True,
        "created": _now(),
    }
    doc["rooms"].append(room)
    _save(ROOMS, doc)
    _append_ledger("room_created", room_id=rid, owner=owner, name=name[:80])
    return {"ok": True, "room": room, "created": True}


def person_room(person: str) -> dict[str, Any]:
    """One mirrored room per person by default."""
    name = f"@{person}"
    return create_room(name, owner=person)


def join_room(room_id: str, *, person: str, address: str = "") -> dict[str, Any]:
    addr = address or _address_state().get("current_address") or ""
    check = verify_address_real(addr)
    if not check.get("real"):
        _append_ledger("room_join_denied", room_id=room_id, person=person, reason="address_not_real")
        return {"ok": False, "error": "address_not_real", **check}
    doc = _rooms_doc()
    for r in doc["rooms"]:
        if r.get("id") == room_id:
            if person not in (r.get("members") or []):
                r.setdefault("members", []).append(person)
                _save(ROOMS, doc)
                _append_ledger("room_joined", room_id=room_id, person=person)
            return {"ok": True, "room": r}
    return {"ok": False, "error": "room_not_found"}


def post_message(room_id: str, *, person: str, text: str) -> dict[str, Any]:
    doc = _rooms_doc()
    msg = {"ts": _now(), "from": person, "text": (text or "")[:2000]}
    for r in doc["rooms"]:
        if r.get("id") == room_id:
            if person not in (r.get("members") or []):
                return {"ok": False, "error": "not_member"}
            r.setdefault("messages", []).append(msg)
            if len(r["messages"]) > 500:
                r["messages"] = r["messages"][-500:]
            _save(ROOMS, doc)
            _append_ledger("room_message", room_id=room_id, person=person, preview=text[:120])
            return {"ok": True, "message": msg, "room_id": room_id}
    return {"ok": False, "error": "room_not_found"}


def list_rooms() -> dict[str, Any]:
    doc = _rooms_doc()
    return {
        "ok": True,
        "rooms": [
            {
                "id": r.get("id"),
                "name": r.get("name"),
                "owner": r.get("owner"),
                "members": len(r.get("members") or []),
                "messages": len(r.get("messages") or []),
            }
            for r in doc.get("rooms") or []
        ],
    }


def ingest_alert(
    *,
    kind: str,
    message: str,
    source: str = "field",
    speak: bool = False,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """External systems (field-io-packet, Hostess7) push into Noti."""
    noti_id = f"noti_{uuid.uuid4().hex[:12]}"
    policy = (_doctrine().get("policy") or {})
    now = datetime.now(timezone.utc)
    item = {
        "id": noti_id,
        "kind": kind,
        "message": message[:500],
        "source": source,
        "status": "pending_accept",
        "created": _now(),
        "red_until": (now + timedelta(hours=int(policy.get("red_circle_hours") or 24))).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "meta": meta or {},
    }
    pending = _load(PENDING, {"items": []})
    pending.setdefault("items", []).append(item)
    _save(PENDING, pending)
    row = _append_ledger("alert_ingested", noti_id=noti_id, kind=kind, source=source)
    out = {"ok": True, "noti_id": noti_id, "item": item, "ledger": row.get("chain")}
    if speak:
        try:
            import subprocess
            import sys

            vpy = INSTALL / "lib" / "hostess7-voice.py"
            if vpy.is_file():
                subprocess.Popen(
                    [sys.executable, str(vpy), "speak", message[:420]],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
                )
        except OSError:
            pass
    return out


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doctrine = _doctrine()
    addr = _address_state()
    tb = taskbar_state()
    pending = _load(PENDING, {"items": []})
    open_items = [
        it for it in (pending.get("items") or [])
        if it.get("status") in ("pending_accept", "pending")
    ]
    doc = {
        "schema": "noti-panel/v1",
        "updated": _now(),
        "motto": doctrine.get("motto"),
        "hostess7_authority": doctrine.get("hostess7_authority"),
        "taskbar": tb,
        "address": {
            "current": addr.get("current_address"),
            "verified": addr.get("verified"),
            "cooldown_until": addr.get("cooldown_until"),
        },
        "pending_count": len(open_items),
        "pending": open_items[:12],
        "rooms": list_rooms().get("rooms") or [],
        "ledger_path": str(LEDGER),
        "policy": doctrine.get("policy"),
    }
    if write:
        _save(PANEL, doc)
    return doc


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")
    if action in ("status", "json", "panel"):
        return {"ok": True, **build_panel(write=action == "panel")}
    if action == "taskbar":
        return {"ok": True, **taskbar_state()}
    if action == "accept":
        return accept_notification(str(body.get("id") or body.get("noti_id") or ""), actor=str(body.get("actor") or "operator"))
    if action == "deny":
        return deny_notification(str(body.get("id") or body.get("noti_id") or ""), actor=str(body.get("actor") or "operator"))
    if action == "address_reset":
        return request_address_reset(
            str(body.get("new_address") or body.get("address") or ""),
            person=str(body.get("person") or "operator"),
        )
    if action == "create_room":
        return create_room(str(body.get("name") or ""), owner=str(body.get("owner") or body.get("person") or "operator"))
    if action == "person_room":
        return person_room(str(body.get("person") or body.get("owner") or "operator"))
    if action == "join_room":
        return join_room(
            str(body.get("room_id") or body.get("room") or ""),
            person=str(body.get("person") or "operator"),
            address=str(body.get("address") or ""),
        )
    if action == "post":
        return post_message(
            str(body.get("room_id") or body.get("room") or ""),
            person=str(body.get("person") or "operator"),
            text=str(body.get("text") or body.get("message") or ""),
        )
    if action == "list_rooms":
        return list_rooms()
    if action == "ingest":
        return ingest_alert(
            kind=str(body.get("kind") or "alert"),
            message=str(body.get("message") or ""),
            source=str(body.get("source") or "dispatch"),
            speak=bool(body.get("speak")),
            meta=body.get("meta") if isinstance(body.get("meta"), dict) else None,
        )
    return {"ok": False, "error": "unknown_action", "actions": [
        "panel", "taskbar", "accept", "deny", "address_reset", "create_room",
        "person_room", "join_room", "post", "list_rooms", "ingest",
    ]}


def main() -> int:
    import sys

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
    if cmd == "taskbar":
        print(json.dumps(taskbar_state(), ensure_ascii=False))
        return 0
    if cmd == "ledger" and len(sys.argv) > 2:
        tail = int(sys.argv[2]) if sys.argv[2].isdigit() else 20
        rows = []
        if LEDGER.is_file():
            for line in LEDGER.read_text(encoding="utf-8").strip().splitlines()[-tail:]:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        print(json.dumps({"ok": True, "rows": rows}, ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: noti.py [json|taskbar|ledger N|dispatch]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())