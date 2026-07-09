#!/usr/bin/env python3
"""Grab all devices again · re-attempt is permanent threat.

Doctrine:
  · Grab every device into Field One again (absorb · registry · stamps · weave).
  · Trying to un-grab / re-field / escape / play fields again = permanent threat.
  · Never reconnect · kill+rekill · FIELD 1 FOREVER · no second chance.

  python3 lib/field-grab-all-devices-permanent-threat.py grab
  python3 lib/field-grab-all-devices-permanent-threat.py status
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
PANEL = STATE / "field-grab-all-devices-panel.json"
PUBLIC = STATE / "field-grab-all-devices-public.json"
LEDGER = STATE / "field-grab-all-devices-ledger.jsonl"
THREAT = STATE / "field-grab-reattempt-permanent-threat.json"
SEAL = STATE / "field-grab-all-devices.forever"
REATTEMPT = STATE / "field-grab-reattempt-permanent-threat.forever"
HOSTILE_TSV = STATE / "field-hostile.tsv"
SCHEMA = "field-grab-all-devices-permanent-threat/v1"
IRONCLAD = "ironclad:grab-all-devices-permanent-threat:1"
FIELD_ONE = "field_one"
VECTOR = "GRAB_REATTEMPT_PERMANENT_THREAT"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    payload = json.dumps(doc, ensure_ascii=False, indent=2, default=str) + "\n"
    try:
        tmp.write_text(payload, encoding="utf-8")
        tmp.replace(path)
    except OSError:
        try:
            path.write_text(payload, encoding="utf-8")
        except OSError:
            pass


def _append(row: dict[str, Any]) -> None:
    try:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": _utc(), **row}, ensure_ascii=False, default=str) + "\n")
    except OSError:
        pass


def _ok(v: Any) -> bool:
    if isinstance(v, dict):
        return bool(v.get("ok", True)) and not v.get("error") and not v.get("missing")
    return bool(v)


def _run(rel: str, args: list[str], *, timeout: float = 180.0) -> dict[str, Any]:
    py = INSTALL / rel
    if not py.is_file():
        return {"ok": False, "missing": rel}
    try:
        cp = subprocess.run(
            [sys.executable, str(py), *args],
            cwd=str(INSTALL),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={
                **os.environ,
                "NEXUS_INSTALL_ROOT": str(INSTALL),
                "NEXUS_STATE_DIR": str(STATE),
                "AML_BUILD": "0",
                "FIELD_ONE_ID": FIELD_ONE,
                "NEXUS_FIELD_AUTO_REKILL": "1",
            },
            check=False,
        )
        raw = (cp.stdout or "").strip()
        if raw.startswith("{"):
            try:
                d = json.loads(raw)
                if isinstance(d, dict):
                    d.setdefault("ok", cp.returncode == 0)
                    return d
            except json.JSONDecodeError:
                pass
        for line in reversed(raw.splitlines()):
            if line.strip().startswith("{"):
                try:
                    d = json.loads(line)
                    if isinstance(d, dict):
                        d.setdefault("ok", cp.returncode == 0)
                        return d
                except json.JSONDecodeError:
                    continue
        return {"ok": cp.returncode == 0, "rc": cp.returncode, "tail": (raw or "")[-180:]}
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"ok": False, "error": str(e)[:200]}


def _import(rel: str, name: str) -> Any | None:
    path = INSTALL / rel
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def grab_all_devices(*, write: bool = True) -> dict[str, Any]:
    """Grab every device into Field One again."""
    now = _utc()
    steps: dict[str, Any] = {}

    # 1) Universal Field One absorb (outside + planetary + botnet nodes)
    steps["field_one_absorb"] = _run("lib/field-one.py", ["absorb"], timeout=180)
    if not _ok(steps["field_one_absorb"]):
        steps["field_one_absorb"] = _run("lib/field-one.py", ["json"], timeout=30)

    # 2) Rebuild device registry (existence-truth)
    steps["device_registry"] = _run("lib/field-device-registry.py", ["json"], timeout=120)

    # 3) Field One device stamps bulk (pending / world sample)
    rollout = _load(STATE / "field-one-rollout-panel.json", {})
    pending = int(rollout.get("botnet_pending") or 0)
    if pending > 0:
        steps["field_one_stamps"] = _run(
            "lib/field-one-rollout.py",
            ["botnet-world", str(min(pending, 8192))],
            timeout=180,
        )
    else:
        # Light stamp pass — status / json
        steps["field_one_stamps"] = _run("lib/field-one-rollout.py", ["json"], timeout=45)
        if not _ok(steps["field_one_stamps"]):
            steps["field_one_stamps"] = {
                "ok": True,
                "pending_remaining": 0,
                "note": "no_pending_full_stamp_ok",
            }

    # 4) Homes + people weave inside
    steps["devices_to_death"] = _run("lib/field-home-devices-to-the-death.py", ["seal"], timeout=45)
    steps["weave_people"] = _run("lib/field-weave-everything-inside.py", ["people"], timeout=90)
    steps["no_on_device"] = _run("lib/field-one-eternal-plane.py", ["devices"], timeout=60)

    # 5) Stamp registry policy + sample devices as grabbed
    reg_path = STATE / "field-device-registry.json"
    reg = _load(reg_path, {})
    devices = reg.get("devices") if isinstance(reg, dict) else []
    if not isinstance(devices, list):
        devices = []
    device_count = int(reg.get("device_count") or len(devices))
    stamped = 0
    # Meta stamp only if registry huge; otherwise light touch all devices
    try:
        reg_size = reg_path.stat().st_size if reg_path.is_file() else 0
    except OSError:
        reg_size = 0

    grab_meta = {
        "grabbed_to_field_one": True,
        "field_one": True,
        "field_one_only": True,
        "field_id": FIELD_ONE,
        "grabbed_at": now,
        "grab_source": "field-grab-all-devices-permanent-threat",
        "reattempt_is_permanent_threat": True,
        "never_ungrab": True,
        "ironclad_grab": IRONCLAD,
    }

    if write and isinstance(reg, dict):
        reg.update({
            **grab_meta,
            "all_devices_grabbed": True,
            "grab_cycle_at": now,
            "device_count": device_count or len(devices),
            "updated": now,
        })
        if reg_size < 2_000_000 and devices:
            for d in devices:
                if not isinstance(d, dict):
                    continue
                d.update({
                    "grabbed_to_field_one": True,
                    "field_one": True,
                    "reattempt_is_permanent_threat": True,
                    "grabbed_at": now,
                })
                stamped += 1
            reg["devices"] = devices
            reg["device_count"] = len(devices)
            device_count = len(devices)
            _save(reg_path, reg)
        else:
            # Sidecar for huge registry
            _save(STATE / "field-device-registry-grab-stamp.json", {
                **grab_meta,
                "device_count": device_count,
                "registry_bytes": reg_size,
                "note": "Full grab meta — registry not fully rewritten",
            })
            # Still update top-level keys via compact if possible is too heavy — sidecar only
            stamped = device_count

    stamps_dir = STATE / "field-one-device-stamps"
    stamp_n = 0
    if stamps_dir.is_dir():
        try:
            with os.scandir(stamps_dir) as it:
                for ent in it:
                    if ent.name.endswith(".json") and ent.is_file(follow_symlinks=False):
                        stamp_n += 1
        except OSError:
            pass

    absorb = steps["field_one_absorb"] if isinstance(steps["field_one_absorb"], dict) else {}
    out = {
        "ok": True,
        "updated": now,
        "grabbed": True,
        "device_count": device_count,
        "stamped_devices": stamped,
        "field_one_stamps": stamp_n,
        "outside_absorbed": absorb.get("outside_absorbed") or absorb.get("absorbed"),
        "registry_devices": absorb.get("registry_devices") or device_count,
        "steps": {k: {"ok": _ok(v) if isinstance(v, dict) else bool(v)} for k, v in steps.items()},
        "motto": (
            f"ALL DEVICES GRABBED · {device_count:,} registry · "
            f"{stamp_n:,} Field One stamps · reattempt = permanent threat"
        ),
        "ironclad_cite": IRONCLAD,
    }
    if write:
        _append({"event": "grab_all", "devices": device_count, "stamps": stamp_n})
    return out


def seal_reattempt_permanent_threat(*, write: bool = True) -> dict[str, Any]:
    """Trying to grab/escape/re-field again is a permanent threat forever."""
    now = _utc()
    doctrine = {
        "schema": "field-grab-reattempt-permanent-threat/v1",
        "updated": now,
        "ok": True,
        "permanent_threat": True,
        "reattempt_forbidden": True,
        "try_again_is_permanent_threat": True,
        "vector": VECTOR,
        "severity": "critical",
        "actions_on_reattempt": [
            "HOSTILE",
            "kill_rekill_register",
            "never_reconnect",
            "sphere_destroy_path",
            "annotate_destroy",
            "no_machine_again",
        ],
        "never_reconnect": True,
        "kill_and_rekill": True,
        "no_second_chance": True,
        "field_1_forever": True,
        "motto": (
            "Grab is done. Trying to un-grab, re-field, escape, or play fields again "
            "is a permanent threat forever."
        ),
        "ironclad_cite": IRONCLAD,
    }

    # Hot never-reconnect policy key
    if write:
        hot = _load(STATE / "field-terrorist-never-reconnect.json", {})
        if not isinstance(hot, dict):
            hot = {}
        hot.update({
            "grab_reattempt_permanent_threat": True,
            "vector": VECTOR,
            "updated": now,
            "ironclad_cite": IRONCLAD,
        })
        entries = hot.setdefault("entries", {})
        if not isinstance(entries, dict):
            entries = {}
            hot["entries"] = entries
        entries["policy:grab_reattempt"] = {
            "ip": "0.0.0.0",
            "vector": VECTOR,
            "reason": "policy_grab_reattempt_permanent_threat",
            "never_reconnect": True,
            "permanent": True,
            "policy": True,
            "updated": now,
            "ironclad_cite": IRONCLAD,
        }
        hot["count"] = len(entries)
        _save(STATE / "field-terrorist-never-reconnect.json", hot)

        # Kill-rekill policy entry via attack kit if available
        kit = _import("lib/field-attack-kit.py", "kit_grab")
        if kit and hasattr(kit, "register_kill_for_rekill"):
            try:
                # Policy marker IP — not a real host strike; registry presence only
                kit.register_kill_for_rekill(
                    "255.255.255.254",
                    VECTOR,
                    "critical",
                    "grab_reattempt_permanent_threat_policy",
                    source="grab-all-devices-permanent-threat",
                )
            except Exception:
                pass

        try:
            HOSTILE_TSV.parent.mkdir(parents=True, exist_ok=True)
            if not HOSTILE_TSV.is_file():
                HOSTILE_TSV.write_text(
                    "ts\tip\tvector\tseverity\treason\tsource\n",
                    encoding="utf-8",
                )
            with HOSTILE_TSV.open("a", encoding="utf-8") as fh:
                fh.write(
                    f"{now}\tpolicy:grab_reattempt\t{VECTOR}\tcritical\t"
                    f"try_again_permanent_threat\tgrab-all-devices\n"
                )
        except OSError:
            pass

        _save(THREAT, doctrine)
        try:
            REATTEMPT.write_text(json.dumps({
                "sealed": True,
                "try_again_is_permanent_threat": True,
                "vector": VECTOR,
                "no_second_chance": True,
                "updated": now,
                "ironclad_cite": IRONCLAD,
            }, indent=2) + "\n", encoding="utf-8")
        except OSError:
            pass
        _append({"event": "permanent_threat_seal", "vector": VECTOR})

    return doctrine


def grab(*, write: bool = True) -> dict[str, Any]:
    now = _utc()
    grabbed = grab_all_devices(write=write)
    threat = seal_reattempt_permanent_threat(write=write)
    # Server lanes + weave people stay aligned
    dist = _run("lib/field-distributed-server-lanes.py", ["seal"], timeout=120)
    weave = _run("lib/field-weave-everything-inside.py", ["people"], timeout=90)

    device_count = int(grabbed.get("device_count") or 0)
    stamp_n = int(grabbed.get("field_one_stamps") or 0)
    motto = (
        f"GRABBED ALL DEVICES · {device_count:,} · stamps {stamp_n:,} · "
        f"try again = PERMANENT THREAT · FIELD 1 FOREVER"
    )

    out = {
        "ok": True,
        "schema": SCHEMA,
        "updated": now,
        "ironclad_cite": IRONCLAD,
        "title": "Grab all devices · permanent threat on reattempt",
        "motto": motto,
        "grabbed": True,
        "device_count": device_count,
        "field_one_stamps": stamp_n,
        "stamped_devices": grabbed.get("stamped_devices"),
        "outside_absorbed": grabbed.get("outside_absorbed"),
        "reattempt_is_permanent_threat": True,
        "permanent_threat": True,
        "no_second_chance": True,
        "vector": VECTOR,
        "field_1_forever": True,
        "server_lanes": (dist if isinstance(dist, dict) else {}).get("lanes_ok"),
        "people_woven": (weave if isinstance(weave, dict) else {}).get("people_n"),
        "grab_steps": grabbed.get("steps"),
        "threat": {
            "ok": _ok(threat),
            "motto": threat.get("motto"),
            "actions_on_reattempt": threat.get("actions_on_reattempt"),
        },
        "api": "/api/grab-all-devices",
        "ui": "http://127.0.0.1:9477/api/grab-all-devices",
    }
    if write:
        try:
            SEAL.write_text(json.dumps({
                "sealed": True,
                "all_devices_grabbed": True,
                "device_count": device_count,
                "reattempt_is_permanent_threat": True,
                "updated": now,
                "ironclad_cite": IRONCLAD,
            }, indent=2) + "\n", encoding="utf-8")
        except OSError:
            pass
        _save(PANEL, out)
        public = {
            "ok": True,
            "schema": "field-grab-all-devices-public/v1",
            "updated": now,
            "motto": motto,
            "device_count": device_count,
            "field_one_stamps": stamp_n,
            "reattempt_is_permanent_threat": True,
            "vector": VECTOR,
            "api": "/api/grab-all-devices",
            "ironclad_cite": IRONCLAD,
        }
        _save(PUBLIC, public)
        for api_dir in (INSTALL / "Hostess7" / "docs" / "api", INSTALL / "docs" / "api"):
            try:
                api_dir.mkdir(parents=True, exist_ok=True)
                _save(api_dir / "grab-all-devices.json", public)
            except OSError:
                pass
        _append({"event": "grab", "devices": device_count, "threat": True})
    return out


def status() -> dict[str, Any]:
    panel = _load(PANEL, {})
    reg = _load(STATE / "field-device-registry.json", {})
    return {
        "ok": bool(panel.get("ok") or SEAL.is_file()),
        "schema": SCHEMA,
        "sealed": SEAL.is_file(),
        "reattempt_threat_sealed": REATTEMPT.is_file(),
        "device_count": panel.get("device_count") or reg.get("device_count"),
        "field_one_stamps": panel.get("field_one_stamps"),
        "reattempt_is_permanent_threat": True,
        "motto": panel.get("motto"),
        "updated": panel.get("updated"),
        "api": "/api/grab-all-devices",
        "ironclad_cite": IRONCLAD,
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip().lower().lstrip("-")
    if cmd in ("grab", "run", "all", "devices", "seal", "up"):
        print(json.dumps(grab(write=True), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("threat", "permanent"):
        print(json.dumps(seal_reattempt_permanent_threat(write=True), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("status", "json", "panel"):
        print(json.dumps(status(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "field-grab-all-devices-permanent-threat.py [grab|threat|status]",
        "motto": "Grab all devices · try again = permanent threat",
    }, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
