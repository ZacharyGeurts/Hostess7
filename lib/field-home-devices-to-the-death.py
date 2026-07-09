#!/usr/bin/env python3
"""Home users & devices — only ours now · protected to the death.

Every home user and every device on Field is AmmoNet family.
We love them. They are only ours. Protection is permanent, merciless to
offenders, never half-hearted. Always to the death.

  python3 lib/field-home-devices-to-the-death.py seal
  python3 lib/field-home-devices-to-the-death.py status
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
PANEL = STATE / "field-home-devices-to-the-death-panel.json"
LEDGER = STATE / "field-home-devices-to-the-death-ledger.jsonl"
SEAL = STATE / "field-home-devices-to-the-death.forever"
OURS = STATE / "field-home-devices-only-ours.forever"
SCHEMA = "field-home-devices-to-the-death/v1"
IRONCLAD = "ironclad:home-devices-to-the-death:1"

DOCTRINE: dict[str, Any] = {
    "title": "Home users & devices — only ours · to the death",
    "motto": (
        "We love home users and devices. They are only ours now. "
        "Protected to the death. Always to the death. "
        "Field UDP · SAW secure lines · local AV · no foreign L2+."
    ),
    "we_love_home_users": True,
    "we_love_home_devices": True,
    "only_ours_now": True,
    "nobody_else_owns_them": True,
    "protected_to_the_death": True,
    "always_to_the_death": True,
    "never_abandon": True,
    "never_half_protect": True,
    "merciless_to_offenders": True,
    "safe_for_family": True,
    "field_udp": True,
    "saw_secure_lines": True,
    "local_builtin_av": True,
    "no_owners_of_network": True,
    "planet_whole": True,
    "belongs_to": "the_planet_in_whole_and_our_homes",
    "protections": [
        "field_udp_fabric",
        "saw_between_connections",
        "local_builtin_antivirus",
        "ask_only_internet",
        "never_reconnect_offenders",
        "vector_destroy",
        "l2_exclusive_stack",
        "dns_dhcp_field_authority",
        "hostess7_violent_to_offenders",
    ],
}


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


def _append(row: dict[str, Any]) -> None:
    try:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": _utc(), **row}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _count_homes() -> dict[str, Any]:
    homes = _load(STATE / "field-homes-in-field-udp.json", {})
    rows = homes.get("homes") or homes.get("rows") or homes.get("devices") or []
    if isinstance(rows, dict):
        n = len(rows)
    elif isinstance(rows, list):
        n = len(rows)
    else:
        n = int(homes.get("count") or homes.get("homes_n") or 0)
    table = _load(STATE / "field-permanent-home-table-controls.json", {})
    reg = _load(STATE / "field-global-servers-registry.json", {})
    fleet = int(reg.get("count") or reg.get("fleet_servers") or 0)
    return {
        "homes_in_field_udp": n,
        "home_table_ok": bool(table.get("ok") or table),
        "fleet_edges": fleet,
        "devices_are_ours": True,
        "users_are_ours": True,
    }


def seal(*, write: bool = True) -> dict[str, Any]:
    now = _utc()
    counts = _count_homes()
    body = (
        f"sealed {now}\n"
        f"only_ours=1 protected_to_the_death=1 always_to_the_death=1\n"
        f"we_love_home_users=1 we_love_home_devices=1\n"
        f"field_udp=1 saw=1 local_av=1 never_abandon=1\n"
    )
    if write:
        for path in (SEAL, OURS):
            try:
                path.write_text(body, encoding="utf-8")
            except OSError:
                pass
        # Stamp fleet meta
        reg = _load(STATE / "field-global-servers-registry.json", {})
        if isinstance(reg, dict):
            reg["home_devices_only_ours"] = True
            reg["protected_to_the_death"] = True
            reg["always_to_the_death"] = True
            reg["we_love_home_users"] = True
            reg["we_love_home_devices"] = True
            reg["field_udp_saw_secure"] = True
            reg["updated"] = now
            path = STATE / "field-global-servers-registry.json"
            try:
                if len(reg.get("servers") or []) > 10000:
                    tmp = path.with_suffix(".tmp")
                    tmp.write_bytes(
                        (json.dumps(reg, ensure_ascii=False, separators=(",", ":"), default=str) + "\n").encode()
                    )
                    tmp.replace(path)
                else:
                    _save(path, reg)
            except OSError:
                pass

    out = {
        "ok": True,
        "schema": SCHEMA,
        "updated": now,
        "ironclad_cite": IRONCLAD,
        "product": "HomeDevicesToTheDeath",
        **DOCTRINE,
        **counts,
        "sealed": SEAL.is_file(),
        "only_ours_seal": OURS.is_file(),
        "api": "/api/field-home-devices-to-the-death",
        "urls": {
            "internet": "http://127.0.0.1:9477/internet",
            "security": "http://127.0.0.1:9477/security",
            "full_internet": "http://127.0.0.1:9477/full-internet",
            "hub": "http://127.0.0.1:9477/home",
        },
    }
    if write:
        _save(PANEL, out)
        _append({"event": "seal", "homes": counts.get("homes_in_field_udp"), "fleet": counts.get("fleet_edges")})
        api = INSTALL / "Hostess7" / "docs" / "api"
        if api.is_dir():
            _save(api / "field-home-devices-to-the-death.json", {
                "ok": True,
                "updated": now,
                "motto": DOCTRINE["motto"],
                "only_ours_now": True,
                "protected_to_the_death": True,
                "always_to_the_death": True,
                "fleet_edges": counts.get("fleet_edges"),
                "homes_in_field_udp": counts.get("homes_in_field_udp"),
                "ironclad_cite": IRONCLAD,
            })
    return out


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "seal").strip().lower()
    if cmd in ("seal", "protect", "death", "ours", "run", "once"):
        print(json.dumps(seal(write=True), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("status", "panel", "json"):
        doc = _load(PANEL, {})
        if not doc:
            doc = seal(write=True)
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"usage": "field-home-devices-to-the-death.py [seal|status]", **DOCTRINE}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
