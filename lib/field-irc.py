#!/usr/bin/env python3
"""Field IRC — global chat rooms on Hostess7 Noti fair ban + Ironclad + truth-lie witness."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import signal
import socket
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
METROS = INSTALL / "data" / "world-global-metros.json"
NOTI_DOCTRINE = INSTALL / "data" / "noti-doctrine.json"
IRC_DOCTRINE = INSTALL / "data" / "field-irc-doctrine.json"
PANEL = STATE / "field-irc-panel.json"
BANS = STATE / "field-irc-ban-panel.json"
USERNAMES = STATE / "field-irc-usernames.json"
LEDGER = STATE / "field-irc-ledger.jsonl"
SCHEMA = "field-irc/v1"
BAN_HOURS = 24
OWNER_NAME = "Zachary Geurts"
OWNER_IDS = frozenset({"zacharygeurts", "zachary-geurts", "zachary geurts"})

GLOBAL_ROOMS = (
    "fleet-2500",
    "mesh-global",
    "sovereign",
    "grok-racks",
    "field-irc",
    "iron-warning",
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append_ledger(row: dict[str, Any]) -> None:
    try:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": _utc(), **row}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _mod(rel: str, name: str) -> Any | None:
    py = INSTALL / rel
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _noti_core() -> Any | None:
    """Always load lib/noti.py — Hostess7 bridge delegates but does not define rooms."""
    return _mod("lib/noti.py", "noti_core")


def _noti_bridge() -> Any | None:
    """Hostess7 Noti bridge for relay/dispatch when available."""
    return _mod("lib/hostess7-noti.py", "h7_noti_bridge")


def _birth_location(*, person: str, device_id: str = "", metro_id: str = "", region_id: str = "") -> dict[str, Any]:
    host = socket.gethostname().split(".")[0]
    since = _utc()
    dev_reg = _load(STATE / "field-device-registry.json", {})
    devices = list(dev_reg.get("devices") or [])
    matched: dict[str, Any] | None = None
    did = (device_id or person or host).strip().lower()
    for dev in devices:
        if not isinstance(dev, dict):
            continue
        keys = {
            str(dev.get("id") or "").lower(),
            str(dev.get("hostname") or "").lower(),
            str(dev.get("mac") or "").lower(),
        }
        if did and did in keys:
            matched = dev
            break
    if matched:
        since = str(matched.get("first_seen") or matched.get("last_seen") or matched.get("last_timestamp") or since)
        metro_id = metro_id or str(matched.get("metro_id") or matched.get("region") or "")
        region_id = region_id or str(matched.get("region_id") or matched.get("region") or "")

    fleet_reg = _load(STATE / "field-global-servers-registry.json", {})
    if not metro_id and fleet_reg.get("servers"):
        row = fleet_reg["servers"][hash(person) % len(fleet_reg["servers"])]
        if isinstance(row, dict):
            metro_id = str(row.get("metro_id") or "")
            region_id = region_id or str(row.get("region_id") or "")

    birth_place = metro_id or region_id or host or "sovereign-local"
    blob = f"{birth_place}|{since}|{host}|{person}"
    fingerprint = hashlib.sha256(blob.encode()).hexdigest()[:20]
    return {
        "birth_place": birth_place,
        "metro_id": metro_id or None,
        "region_id": region_id or None,
        "hostname": host,
        "since": since,
        "person": person,
        "device_id": device_id or did or host,
        "fingerprint": fingerprint,
    }


def _ban_doc() -> dict[str, Any]:
    doc = _load(BANS, {"schema": "field-irc-ban/v1", "bans": {}, "devices_seen": {}})
    doc.setdefault("bans", {})
    doc.setdefault("devices_seen", {})
    return doc


def _ban_active(fingerprint: str) -> dict[str, Any] | None:
    doc = _ban_doc()
    row = doc.get("bans", {}).get(fingerprint)
    if not isinstance(row, dict):
        return None
    exp = str(row.get("expires") or "")
    try:
        until = datetime.fromisoformat(exp.replace("Z", "+00:00"))
        if datetime.now(timezone.utc) < until:
            return row
    except ValueError:
        pass
    return None


def _circumvention_check(birth: dict[str, Any]) -> dict[str, Any]:
    fp = str(birth.get("fingerprint") or "")
    did = str(birth.get("device_id") or "")
    doc = _ban_doc()
    seen = doc.setdefault("devices_seen", {})
    prior = seen.get(fp)
    if isinstance(prior, dict) and prior.get("device_id") and prior["device_id"] != did:
        active = _ban_active(fp)
        if active:
            return {
                "ok": False,
                "circumvention": True,
                "error": "birth_location_ban_no_alt_device",
                "detail": "Alternate device blocked — birth location and since are known.",
                "birth": birth,
                "ban": active,
            }
    seen[fp] = {"device_id": did, "since": birth.get("since"), "updated": _utc()}
    _save(BANS, doc)
    active = _ban_active(fp)
    if active:
        return {
            "ok": False,
            "banned": True,
            "error": "pid_ban_active",
            "detail": active.get("reason") or "Iron warning — 24h fair ban",
            "expires": active.get("expires"),
            "birth": birth,
        }
    return {"ok": True, "birth": birth}


def _pid_ban(*, birth: dict[str, Any], reason: str, pid: int | None = None) -> dict[str, Any]:
    policy = (_load(NOTI_DOCTRINE, {}).get("policy") or {})
    hours = int(policy.get("red_circle_hours") or BAN_HOURS)
    now = datetime.now(timezone.utc)
    expires = (now + timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
    fp = str(birth.get("fingerprint") or "")
    me = os.getpid()
    target = int(pid or me)
    killed = False
    if target and target != me:
        try:
            os.kill(target, signal.SIGTERM)
            killed = True
        except OSError:
            pass
    doc = _ban_doc()
    doc["bans"][fp] = {
        "fingerprint": fp,
        "birth_place": birth.get("birth_place"),
        "since": birth.get("since"),
        "device_id": birth.get("device_id"),
        "person": birth.get("person"),
        "reason": reason[:300],
        "pid": target,
        "killed": killed,
        "expires": expires,
        "fair_ban_hours": hours,
        "issued": _utc(),
        "authority": "hostess7_noti+ironclad",
    }
    _save(BANS, doc)
    _append_ledger({"event": "iron_warning_pid_ban", "fingerprint": fp, "reason": reason[:200], "expires": expires})
    return {"ok": True, "banned": True, "expires": expires, "fingerprint": fp, "pid": target, "killed": killed}


def _h7_noti_assist() -> dict[str, Any]:
    h7 = _mod("lib/hostess7-noti.py", "h7_noti")
    if h7 and hasattr(h7, "build_panel"):
        try:
            return {"ok": True, "lane": "hostess7_noti", "panel": h7.build_panel(write=False)}
        except (TypeError, ValueError, OSError) as exc:
            return {"ok": False, "lane": "hostess7_noti", "error": str(exc)[:160]}
    noti = _mod("lib/noti.py", "noti_core")
    if noti and hasattr(noti, "build_panel"):
        return {"ok": True, "lane": "noti", "panel": noti.build_panel(write=False)}
    return {"ok": False, "error": "hostess7_noti_missing"}


def _ironclad_assist() -> dict[str, Any]:
    ic = _mod("lib/ironclad-field-sanity.py", "iron_sanity")
    if ic and hasattr(ic, "build_panel"):
        try:
            return {"ok": True, "lane": "ironclad_field_sanity", "panel": ic.build_panel(write=False, body={})}
        except (TypeError, ValueError, OSError) as exc:
            return {"ok": False, "lane": "ironclad", "error": str(exc)[:160]}
    return {"ok": False, "error": "ironclad_missing"}


def _truth_assist() -> dict[str, Any]:
    tlt = _mod("lib/hostess7-truth-lie-threat.py", "h7_tlt")
    if tlt and hasattr(tlt, "build_panel"):
        try:
            return {"ok": True, "lane": "hostess7_truth_lie", "panel": tlt.build_panel(write=True)}
        except (TypeError, ValueError, OSError) as exc:
            return {"ok": False, "lane": "hostess7_truth_lie", "error": str(exc)[:160]}
    return {"ok": False, "error": "truth_lie_missing"}


def _plate_meld_gate() -> dict[str, Any]:
    meld = _mod("lib/field-plate-meld.py", "plate_meld_gate")
    if meld and hasattr(meld, "read_meld"):
        doc = meld.read_meld()
        ok = bool(doc.get("ok", True)) or bool(doc.get("generation"))
        return {
            "ok": ok,
            "generation": doc.get("generation"),
            "steel_plated": doc.get("steel_plated"),
            "fail_closed": doc.get("fail_closed", True),
        }
    cached = _load(STATE / "field-plate-meld.json", {})
    return {
        "ok": bool(cached.get("generation") or cached.get("ok")),
        "generation": cached.get("generation"),
        "cached": True,
    }


def ban_assist() -> dict[str, Any]:
    """Ask Hostess7 Noti + Ironclad + truth-lie for fair ban design counsel."""
    h7 = _h7_noti_assist()
    ic = _ironclad_assist()
    tlt = _truth_assist()
    doctrine = _load(NOTI_DOCTRINE, {})
    return {
        "ok": True,
        "schema": "field-irc-ban-assist/v1",
        "updated": _utc(),
        "motto": "Hostess7 Noti fair ban · Ironclad warning · birth location — no circumvention",
        "fair_ban": {
            "red_circle_hours": (doctrine.get("policy") or {}).get("red_circle_hours", 24),
            "deny_anytime_in_red_window": (doctrine.get("policy") or {}).get("deny_anytime_in_red_window", True),
            "immutable_ledger": True,
            "no_moderators": True,
            "birth_location_bind": True,
        },
        "assist": {
            "hostess7_noti": h7,
            "ironclad": ic,
            "truth_lie_threat": tlt,
        },
        "authority": doctrine.get("hostess7_authority"),
    }


def _normalize_nick(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip().lower())


def _is_owner(name: str) -> bool:
    return _normalize_nick(name) in OWNER_IDS or _normalize_nick(name) == _normalize_nick(OWNER_NAME)


def _username_doc() -> dict[str, Any]:
    cached = _load(USERNAMES, {})
    if cached.get("reserved"):
        return cached
    doctrine = _load(IRC_DOCTRINE, {})
    reserved = (doctrine.get("reserved_usernames") or {}).get("names") or {}
    return {
        "schema": "field-irc-usernames/v1",
        "owner": OWNER_NAME,
        "owner_ids": sorted(OWNER_IDS),
        "reserved": reserved,
    }


def _reserved_alias_map() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    doc = _username_doc()
    for canonical, meta in (doc.get("reserved") or {}).items():
        if not isinstance(meta, dict):
            continue
        row = {**meta, "canonical": canonical, "owner": meta.get("registered_to") or doc.get("owner") or OWNER_NAME}
        out[_normalize_nick(canonical)] = row
        for alias in meta.get("aliases") or []:
            out[_normalize_nick(str(alias))] = row
    return out


def _username_gate(person: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Grok watches; speaks only when Zachary Geurts asks as Grok. Big Grin is owner-only."""
    body = body or {}
    nick = _normalize_nick(person)
    actor = _normalize_nick(str(body.get("actor") or body.get("owner_actor") or person))
    aliases = _reserved_alias_map()

    if nick in aliases:
        row = aliases[nick]
        canonical = str(row.get("canonical") or person)
        if canonical.lower() == "grok":
            if body.get("grok_watch") or body.get("watch_only"):
                return {"ok": True, "mode": "grok_watch", "person": "Grok"}
            if body.get("as_grok") or body.get("invoke_grok"):
                if not (_is_owner(actor) or _is_owner(str(body.get("authorized_by") or ""))):
                    return {
                        "ok": False,
                        "error": "grok_reserved",
                        "detail": "Grok may only speak when Zachary Geurts asks as Grok.",
                    }
                return {"ok": True, "mode": "grok_speak", "person": "Grok"}
            return {
                "ok": False,
                "error": "grok_watch_only",
                "detail": "Grok watches world chat; cannot interact unless Zachary Geurts asks as Grok.",
                "hint": "Use actor=Zachary Geurts with as_grok:true to invoke.",
            }
        if canonical.lower() in ("big grin",):
            if not (_is_owner(actor) or _is_owner(person)):
                return {
                    "ok": False,
                    "error": "big_grin_reserved",
                    "detail": "Big Grin is registered to Zachary Geurts in Hostess7.",
                }
            return {"ok": True, "mode": "owner_speak", "person": "Big Grin"}
    for alias, row in aliases.items():
        if nick == alias and not _is_owner(actor) and not _is_owner(person):
            return {
                "ok": False,
                "error": "username_reserved",
                "detail": f"{row.get('canonical')} is registered to {row.get('owner')}.",
            }
    return {"ok": True, "mode": "normal", "person": person}


def register_reserved_usernames() -> dict[str, Any]:
    """Reserve Grok + Big Grin for Zachary Geurts — Hostess7 people + local registry."""
    doctrine = _load(IRC_DOCTRINE, {})
    reserved_cfg = doctrine.get("reserved_usernames") or {}
    names = reserved_cfg.get("names") or {
        "Grok": {"aliases": ["grok"], "mode": "watch_only", "registered_to": OWNER_NAME},
        "Big Grin": {"aliases": ["big grin", "big-grin", "biggrin"], "mode": "owner_only", "registered_to": OWNER_NAME},
    }
    doc = {
        "schema": "field-irc-usernames/v1",
        "updated": _utc(),
        "owner": OWNER_NAME,
        "owner_ids": sorted(OWNER_IDS),
        "hostess7_authority": "Hostess7 people registry",
        "reserved": names,
    }
    _save(USERNAMES, doc)

    h7_entities: list[dict[str, Any]] = []
    people_py = INSTALL / "Hostess7" / "scripts" / "field_people_registry.py"
    clone_py = INSTALL / ".hostess7-github-clone" / "Hostess7" / "scripts" / "field_people_registry.py"
    target_py = people_py if people_py.is_file() else clone_py
    if target_py.is_file():
        try:
            spec = importlib.util.spec_from_file_location("people_reg_irc", target_py)
            if spec and spec.loader:
                pm = importlib.util.module_from_spec(spec)
                sys.path.insert(0, str(target_py.parent))
                spec.loader.exec_module(pm)
                if hasattr(pm, "ensure_registry"):
                    pm.ensure_registry(seed=True)
                if hasattr(pm, "new_entity"):
                    owner = pm.new_entity(
                        OWNER_NAME,
                        tags=["owner", "founder", "goodguy"],
                        aliases=["ZacharyGeurts", "Zachary Geurts"],
                        respect_level=100,
                    )
                    h7_entities.append({"id": owner.get("id"), "name": owner.get("name"), "role": "owner"})
                    grok = pm.new_entity(
                        "Grok",
                        tags=["owner", "reserved_username", "watch_only"],
                        aliases=["grok"],
                        bio="Reserved to Zachary Geurts — watches world chat; speaks only when asked as Grok.",
                        respect_level=95,
                    )
                    if hasattr(pm, "add_tag"):
                        pm.add_tag(grok.get("id"), "registered_to_zacharygeurts")
                    h7_entities.append({"id": grok.get("id"), "name": "Grok", "role": "reserved"})
                    grin = pm.new_entity(
                        "Big Grin",
                        tags=["owner", "reserved_username"],
                        aliases=["big-grin", "biggrin", "BIG GRIN"],
                        bio="Reserved to Zachary Geurts — Hostess7 Big Grin identity.",
                        respect_level=95,
                    )
                    if hasattr(pm, "add_tag"):
                        pm.add_tag(grin.get("id"), "registered_to_zacharygeurts")
                    h7_entities.append({"id": grin.get("id"), "name": "Big Grin", "role": "reserved"})
        except (ImportError, OSError, TypeError, ValueError, KeyError):
            pass

    h7 = _noti_bridge()
    if h7 and hasattr(h7, "relay_event"):
        h7.relay_event(
            "irc_usernames_registered",
            message="Grok and Big Grin reserved to Zachary Geurts — Grok watches unless asked.",
        )
    return {"ok": True, "usernames": doc, "hostess7_entities": h7_entities}


def grok_watch(*, room_id: str, text: str, person: str = "Grok") -> dict[str, Any]:
    """Grok observes world chat — ledger only, no room post."""
    _append_ledger({
        "event": "grok_watch",
        "room_id": room_id,
        "person": person,
        "text": (text or "")[:500],
        "mode": "watch_only",
    })
    return {
        "ok": True,
        "mode": "grok_watch",
        "watched": True,
        "room_id": room_id,
        "detail": "Grok is watching — no interaction unless Zachary Geurts asks as Grok.",
    }


def _bsp() -> Any | None:
    return _mod("lib/field-irc-bsp.py", "irc_bsp")


def _irc_iron_trigger(lie: dict[str, Any]) -> bool:
    """Iron warning only on real threats — counsel-band chat stays open."""
    klass = str(lie.get("class") or "")
    if klass in ("lie", "quarantine", "delay_threat", "hostile"):
        return True
    if lie.get("quarantine"):
        return True
    try:
        lie_score = float(lie.get("lie_score") or 0)
    except (TypeError, ValueError):
        lie_score = 0.0
    return lie_score >= 60.0


def _witness_message(text: str, *, person: str, source: str = "field_irc") -> dict[str, Any]:
    tlt = _mod("lib/hostess7-truth-lie-threat.py", "h7_tlt_w")
    if not tlt:
        return {"ok": True, "skipped": True, "reason": "truth_lie_missing"}
    if hasattr(tlt, "classify_lie"):
        lie = tlt.classify_lie(text)
        if _irc_iron_trigger(lie):
            if hasattr(tlt, "witness_claim"):
                tlt.witness_claim(text, source=source, party=person, record_threat=True)
            return {"ok": False, "iron_warning": True, "lie": lie, "reason": lie.get("class") or "lie_threat"}
        if hasattr(tlt, "witness_claim"):
            return {"ok": True, "witness": tlt.witness_claim(text, source=source, party=person, record_threat=False)}
    if hasattr(tlt, "witness_claim"):
        return {"ok": True, "witness": tlt.witness_claim(text, source=source, party=person, record_threat=False)}
    return {"ok": True, "skipped": True}


def _iron_warn(reason: str, *, birth: dict[str, Any], meta: dict[str, Any] | None = None) -> dict[str, Any]:
    h7 = _mod("lib/hostess7-noti.py", "h7_noti_warn")
    msg = f"Iron warning — {reason[:200]}. Fair 24h PID ban per Hostess7 Noti doctrine."
    out: dict[str, Any] = {"ok": True, "warning": msg}
    if h7 and hasattr(h7, "relay_event"):
        out["hostess7"] = h7.relay_event("iron_warning", message=msg, meta={**(meta or {}), "birth": birth})
    noti = _mod("lib/noti.py", "noti_warn")
    if noti and hasattr(noti, "ingest_alert"):
        out["noti"] = noti.ingest_alert(kind="iron_warning", message=msg, source="field-irc", meta=meta)
    ic = _mod("lib/ironclad-field-sanity.py", "iron_warn")
    if ic and hasattr(ic, "field_sanity_operator"):
        try:
            out["ironclad"] = ic.field_sanity_operator({"claim": reason, "source": "field_irc", "birth": birth})
        except (TypeError, ValueError, OSError):
            pass
    return out


def _ensure_irc_member(room_id: str, person: str) -> dict[str, Any]:
    """Field IRC sovereign join — plate meld + birth bind already gated; skip address proof."""
    rooms_path = STATE / "noti-rooms.json"
    doc = _load(rooms_path, {"schema": "noti-rooms/v1", "rooms": []})
    rid = room_id.strip().lower()
    for room in doc.get("rooms") or []:
        if not isinstance(room, dict) or str(room.get("id") or "").lower() != rid:
            continue
        members = list(room.get("members") or [])
        if person not in members:
            members.append(person)
            room["members"] = members
            _save(rooms_path, doc)
            _append_ledger({"event": "irc_join", "room_id": rid, "person": person})
        return {"ok": True, "room": room}
    return {"ok": False, "error": "room_not_found", "room_id": rid}


def seed_global_rooms() -> dict[str, Any]:
    noti = _noti_core()
    h7 = _noti_bridge()
    if not noti or not hasattr(noti, "create_room"):
        return {"ok": False, "error": "noti_missing"}
    created = 0
    rooms: list[str] = list(GLOBAL_ROOMS)
    metros = _load(METROS, {}).get("metros") or []
    for metro in metros[:16]:
        if isinstance(metro, dict) and metro.get("id"):
            rooms.append(f"global-{metro['id']}")
    seen: set[str] = set()
    for name in rooms:
        key = name.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        row = noti.create_room(name, owner="field-irc")
        if row.get("created"):
            created += 1
    if h7 and hasattr(h7, "ensure_person_rooms"):
        h7.ensure_person_rooms()
    return {"ok": True, "rooms_target": len(seen), "rooms_created": created, "seeded": sorted(seen)}


def irc_post(
    room_id: str,
    *,
    person: str,
    text: str,
    device_id: str = "",
    pid: int | None = None,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    gate_user = _username_gate(person, body)
    if not gate_user.get("ok"):
        if _normalize_nick(person) == "grok" and gate_user.get("error") == "grok_watch_only":
            return grok_watch(room_id=room_id, text=text)
        return gate_user
    person = str(gate_user.get("person") or person)

    meld = _plate_meld_gate()
    if not meld.get("ok"):
        return {"ok": False, "error": "plate_meld_required", "detail": "Run plate meld before IRC", "meld": meld}
    birth = _birth_location(person=person, device_id=device_id)
    gate = _circumvention_check(birth)
    if not gate.get("ok"):
        if gate.get("circumvention"):
            _iron_warn("circumvention via alternate device", birth=birth, meta=gate)
            ban = _pid_ban(birth=birth, reason="circumvention_birth_location", pid=pid)
            return {**gate, "iron_warning": True, "ban": ban}
        return gate

    witness = _witness_message(text, person=person)
    if witness.get("iron_warning"):
        reason = str((witness.get("lie") or {}).get("class") or "lie_threat")
        warn = _iron_warn(reason, birth=birth, meta=witness)
        ban = _pid_ban(birth=birth, reason=f"iron_warning:{reason}", pid=pid)
        return {
            "ok": False,
            "error": "iron_warning",
            "iron_warning": True,
            "witness": witness,
            "warning": warn,
            "ban": ban,
            "birth": birth,
        }

    noti = _noti_core()
    if not noti or not hasattr(noti, "post_message"):
        return {"ok": False, "error": "noti_missing"}
    joined = _ensure_irc_member(room_id, person)
    if not joined.get("ok"):
        return joined
    posted = noti.post_message(room_id, person=person, text=text)
    bsp_out: dict[str, Any] | None = None
    fanout: dict[str, Any] | None = None
    if posted.get("ok"):
        _append_ledger({"event": "irc_post", "room_id": room_id, "person": person, "birth_fp": birth.get("fingerprint")})
        bsp_mod = _bsp()
        doctrine = _load(IRC_DOCTRINE, {})
        bsp_cfg = doctrine.get("bsp") or {}
        if bsp_mod:
            panel = _load(STATE / "field-irc-bsp-panel.json", {})
            done = panel.get("batches_done") or []
            if not done and hasattr(bsp_mod, "distribute_batch"):
                bsp_out = bsp_mod.distribute_batch(0, dns_dhcp=bool(bsp_cfg.get("distribute_dns_dhcp", True)))
            if bsp_cfg.get("bicomm_racks") and hasattr(bsp_mod, "rack_fanout"):
                fanout = bsp_mod.rack_fanout(text, room_id=room_id, person=person)
    return {
        **posted,
        "witness": witness.get("witness"),
        "birth": birth,
        "fair_ban": _load(NOTI_DOCTRINE, {}).get("policy"),
        "bsp": bsp_out,
        "rack_fanout": fanout,
    }


def irc_status() -> dict[str, Any]:
    h7 = _h7_noti_assist()
    rooms = []
    noti = _noti_core()
    if noti and hasattr(noti, "list_rooms"):
        rooms = (noti.list_rooms() or {}).get("rooms") or []
    global_ids = {r.strip().lower() for r in GLOBAL_ROOMS}
    global_seen = {str(r.get("id") or "").lower() for r in rooms}
    global_ready = sum(1 for gid in global_ids if gid in global_seen)
    bans = _ban_doc()
    active_bans = sum(1 for fp, row in (bans.get("bans") or {}).items() if _ban_active(str(fp)))
    inv = _mod("lib/field-rack-inventory.py", "rack_inv")
    counts: dict[str, Any] = {}
    if inv and hasattr(inv, "inventory"):
        doc = inv.inventory(fast=True, probe=False)
        counts = doc.get("counts") or {}
    return {
        "ok": True,
        "schema": SCHEMA,
        "updated": _utc(),
        "title": "Field IRC",
        "motto": "Global chat · Hostess7 Noti fair ban · Ironclad warning · birth location bind",
        "counts": {
            "all_good": counts.get("all_good") or counts.get("up") or 0,
            "fleet_target": counts.get("fleet_target") or 2500,
            "physical_up": counts.get("physical_up") or 0,
            "rooms": len(rooms),
            "global_rooms_ready": global_ready,
            "global_rooms_target": len(GLOBAL_ROOMS),
            "active_bans": active_bans,
        },
        "rooms": rooms,
        "global_rooms": list(GLOBAL_ROOMS),
        "plate_meld": _plate_meld_gate(),
        "usernames": _username_doc(),
        "bsp": (_bsp().bsp_status() if _bsp() and hasattr(_bsp(), "bsp_status") else {}),
        "assist": ban_assist(),
        "api": "/api/field-irc",
    }


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")
    if action in ("status", "json", "panel"):
        doc = irc_status()
        _save(PANEL, doc)
        return doc
    if action in ("assist", "ban_assist", "counsel"):
        return ban_assist()
    if action in ("seed", "seed_rooms", "bootstrap"):
        return seed_global_rooms()
    if action in ("register_usernames", "reserve_usernames", "register"):
        return register_reserved_usernames()
    if action in ("grok_watch", "watch"):
        return grok_watch(
            room_id=str(body.get("room_id") or body.get("room") or "mesh-global"),
            text=str(body.get("text") or body.get("message") or ""),
        )
    if action in ("bsp_distribute", "bsp_batch", "distribute_bsp"):
        bsp_mod = _bsp()
        if not bsp_mod:
            return {"ok": False, "error": "bsp_missing"}
        if action == "bsp_distribute" or body.get("all"):
            return bsp_mod.distribute_all(dns_dhcp=bool(body.get("dns_dhcp", True)), limit=body.get("limit"))
        return bsp_mod.distribute_batch(
            int(body.get("batch_index") or body.get("batch") or 0),
            dns_dhcp=bool(body.get("dns_dhcp", True)),
            rack_fanout=bool(body.get("rack_fanout")),
            announce=str(body.get("announce") or body.get("text") or ""),
        )
    if action in ("rack_fanout", "fanout_racks"):
        bsp_mod = _bsp()
        if not bsp_mod or not hasattr(bsp_mod, "rack_fanout"):
            return {"ok": False, "error": "bsp_missing"}
        return bsp_mod.rack_fanout(
            str(body.get("text") or body.get("message") or ""),
            room_id=str(body.get("room_id") or body.get("room") or "mesh-global"),
            person=str(body.get("person") or "operator"),
        )
    if action in ("rack_inbound", "inbound_rack"):
        bsp_mod = _bsp()
        if not bsp_mod or not hasattr(bsp_mod, "rack_inbound"):
            return {"ok": False, "error": "bsp_missing"}
        return bsp_mod.rack_inbound(
            rack_id=str(body.get("rack_id") or ""),
            text=str(body.get("text") or body.get("message") or ""),
            person=str(body.get("person") or "rack"),
            room_id=str(body.get("room_id") or body.get("room") or "mesh-global"),
        )
    if action in ("post", "say", "message"):
        return irc_post(
            str(body.get("room_id") or body.get("room") or "fleet-2500"),
            person=str(body.get("person") or body.get("nick") or "operator"),
            text=str(body.get("text") or body.get("message") or ""),
            device_id=str(body.get("device_id") or ""),
            pid=int(body["pid"]) if str(body.get("pid") or "").isdigit() else None,
            body=body,
        )
    if action in ("join", "join_room"):
        h7 = _noti_bridge()
        noti = h7 if h7 and hasattr(h7, "dispatch") else _noti_core()
        if not noti or not hasattr(noti, "dispatch"):
            return {"ok": False, "error": "noti_missing"}
        birth = _birth_location(
            person=str(body.get("person") or "operator"),
            device_id=str(body.get("device_id") or ""),
        )
        gate = _circumvention_check(birth)
        if not gate.get("ok"):
            return gate
        return noti.dispatch({
            "action": "join_room",
            "room_id": str(body.get("room_id") or body.get("room") or ""),
            "person": str(body.get("person") or "operator"),
            "address": str(body.get("address") or ""),
        })
    if action in ("rooms", "list_rooms"):
        noti = _mod("lib/noti.py", "noti_lr")
        if noti and hasattr(noti, "list_rooms"):
            return noti.list_rooms()
        return {"ok": False, "error": "noti_missing"}
    if action in ("history", "messages"):
        rid = str(body.get("room_id") or body.get("room") or "")
        rooms_doc = _load(STATE / "noti-rooms.json", {})
        for room in rooms_doc.get("rooms") or []:
            if isinstance(room, dict) and room.get("id") == rid:
                msgs = list(room.get("messages") or [])
                lim = int(body.get("limit") or 80)
                return {"ok": True, "room_id": rid, "messages": msgs[-lim:]}
        return {"ok": False, "error": "room_not_found"}
    if action in ("bans", "ban_status"):
        doc = _ban_doc()
        active = {fp: row for fp, row in (doc.get("bans") or {}).items() if _ban_active(str(fp))}
        return {"ok": True, "active_bans": active, "count": len(active)}
    return {
        "ok": False,
        "error": "unknown_action",
        "actions": [
            "status", "assist", "seed", "register_usernames", "grok_watch",
            "bsp_distribute", "bsp_batch", "rack_fanout", "rack_inbound",
            "post", "join", "rooms", "history", "bans",
        ],
    }


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
    if cmd in ("json", "status"):
        print(json.dumps(irc_status(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("assist", "ban-assist"):
        print(json.dumps(ban_assist(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("seed", "seed-rooms"):
        print(json.dumps(seed_global_rooms(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"usage": "field-irc.py [json|assist|seed|dispatch]", "api": "/api/field-irc"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())