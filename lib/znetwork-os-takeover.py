#!/usr/bin/env python3
"""ZNetwork bottom-up OS takeover — replace native managers without dropping the live link."""
from __future__ import annotations

import json
import os
import platform
import subprocess
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
LEDGER = STATE / "znetwork-takeover.jsonl"
ROLLBACK = STATE / "znetwork-takeover-rollback.json"
SCHEMA = "znetwork-os-takeover/v1"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _log(row: dict[str, Any]) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"ts": _now(), **row}, ensure_ascii=False) + "\n")


def _run(cmd: list[str], *, timeout: int = 12, sudo: bool = False) -> tuple[int, str, str]:
    full = (["sudo", "-n", *cmd] if sudo else cmd)
    try:
        proc = subprocess.run(full, capture_output=True, text=True, timeout=timeout)
        return proc.returncode, proc.stdout or "", proc.stderr or ""
    except (subprocess.SubprocessError, OSError) as exc:
        return 1, "", str(exc)


def _capture(cmd: list[str], *, sudo: bool = False) -> str:
    rc, out, _ = _run(cmd, sudo=sudo)
    return out.strip() if rc == 0 else ""


def _iface_operstate(iface: str) -> str:
    p = Path(f"/sys/class/net/{iface}/operstate")
    try:
        return p.read_text(encoding="utf-8").strip().lower()
    except OSError:
        return "unknown"


def _iface_ipv4(iface: str) -> str:
    out = _capture(["ip", "-4", "-o", "addr", "show", "dev", iface])
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 4 and parts[2] == "inet":
            return parts[3].split("/", 1)[0]
    return ""


def _default_iface() -> str:
    out = _capture(["ip", "-4", "route", "show", "default"])
    if not out:
        return ""
    parts = out.split()
    return parts[parts.index("dev") + 1] if "dev" in parts else ""


def _link_healthy(iface: str, baseline: dict[str, Any]) -> bool:
    if not iface:
        return False
    state = _iface_operstate(iface)
    if state not in ("up", "unknown"):
        return False
    ipv4 = _iface_ipv4(iface)
    if baseline.get("ipv4") and ipv4 and ipv4 != baseline["ipv4"]:
        return False
    if baseline.get("ipv4") and not ipv4:
        return False
    return True


def _save_rollback(doc: dict[str, Any]) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    ROLLBACK.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _takeover_linux(snapshot: dict[str, Any]) -> dict[str, Any]:
    conn = snapshot.get("connection") or snapshot
    iface = str(conn.get("iface") or _default_iface()).strip()
    if not iface:
        return {"ok": False, "error": "no_primary_iface"}

    baseline = {
        "iface": iface,
        "ipv4": str(conn.get("ipv4") or _iface_ipv4(iface)),
        "gateway": str(conn.get("gateway") or ""),
        "operstate": _iface_operstate(iface),
    }
    steps: list[dict[str, Any]] = []

    def step(name: str, ok: bool, detail: str) -> None:
        steps.append({"step": name, "ok": ok, "detail": detail[:300]})
        _log({"event": "takeover_step", "iface": iface, "step": name, "ok": ok, "detail": detail[:300]})

    if not _link_healthy(iface, baseline):
        return {"ok": False, "error": "link_not_healthy_before_handoff", "baseline": baseline, "steps": steps}

    step("mirror_baseline", True, json.dumps(baseline))

    # Handoff: unmanaged keeps L3 — never `link down` / `con down` on primary.
    rc, out, err = _run(["nmcli", "dev", "set", iface, "managed", "no"], sudo=True)
    step("primary_unmanaged", rc == 0, err or out or "managed_no")

    # Drop every other active connection — primary iface untouched.
    listing = _capture(["nmcli", "-t", "-f", "NAME,DEVICE", "connection", "show", "--active"], sudo=True)
    for line in listing.splitlines():
        if ":" not in line:
            continue
        name, device = line.split(":", 1)
        name, device = name.strip(), device.strip()
        if not name or device == iface:
            continue
        rc, out, err = _run(["nmcli", "connection", "down", name], sudo=True)
        step(f"drop_other_con:{name}", rc == 0, err or out or device)

    devs = _capture(["nmcli", "-t", "-f", "DEVICE", "dev", "status"], sudo=True)
    for dev in devs.splitlines():
        dev = dev.strip()
        if not dev or dev == iface or dev == "lo":
            continue
        rc, out, err = _run(["nmcli", "dev", "set", dev, "managed", "no"], sudo=True)
        step(f"other_unmanaged:{dev}", rc == 0, err or out or dev)
        rc, out, err = _run(["nmcli", "dev", "disconnect", dev], sudo=True)
        if rc == 0:
            step(f"disconnect_other_dev:{dev}", True, dev)

    # Short stability window — abort mask if link would appear down.
    stable = True
    for _ in range(6):
        time.sleep(0.5)
        if not _link_healthy(iface, baseline):
            stable = False
            break
    step("stability_probe", stable, f"ipv4={_iface_ipv4(iface)} operstate={_iface_operstate(iface)}")

    if not stable:
        return {
            "ok": False,
            "error": "link_unstable_abort_mask",
            "iface": iface,
            "baseline": baseline,
            "steps": steps,
        }

    backend = str((snapshot.get("backend") or {}).get("id") or "networkmanager")
    if backend == "networkmanager" or _capture(["systemctl", "is-active", "NetworkManager"], sudo=True) == "active":
        _run(["systemctl", "stop", "NetworkManager"], sudo=True)
        rc, out, err = _run(["systemctl", "mask", "NetworkManager"], sudo=True)
        step("mask_networkmanager", rc == 0, err or out or "masked")
    if _capture(["systemctl", "is-active", "systemd-networkd"], sudo=True) == "active":
        _run(["systemctl", "stop", "systemd-networkd"], sudo=True)
        rc, out, err = _run(["systemctl", "mask", "systemd-networkd"], sudo=True)
        step("mask_systemd_networkd", rc == 0, err or out or "masked")

    if not _link_healthy(iface, baseline):
        return {"ok": False, "error": "link_lost_after_mask", "iface": iface, "steps": steps}

    rollback = {
        "schema": "znetwork-takeover-rollback/v1",
        "iface": iface,
        "baseline": baseline,
        "linux_unmask": ["NetworkManager", "systemd-networkd"],
        "nm_managed_yes": iface,
        "created": _now(),
    }
    _save_rollback(rollback)

    return {
        "ok": True,
        "schema": SCHEMA,
        "os": "linux",
        "iface": iface,
        "link_preserved": True,
        "appears_connected": True,
        "baseline": baseline,
        "final_ipv4": _iface_ipv4(iface),
        "policy_owner": "znetwork",
        "steps": steps,
        "rollback": str(ROLLBACK),
    }


def _takeover_stub(os_name: str, snapshot: dict[str, Any]) -> dict[str, Any]:
    conn = snapshot.get("connection") or snapshot
    return {
        "ok": True,
        "schema": SCHEMA,
        "os": os_name,
        "iface": conn.get("iface", ""),
        "link_preserved": True,
        "appears_connected": True,
        "skipped": True,
        "reason": f"{os_name}_policy_record_only",
        "policy_owner": "znetwork",
        "steps": [{"step": "mirror_policy", "ok": True, "detail": "Bottom-up plan recorded; native mask deferred on this OS"}],
    }


def _smart_inside_active() -> bool:
    return os.environ.get("ZNETWORK_SMART_INSIDE", "1") != "0"


def takeover(*, snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    if snapshot is None:
        snapshot = {}
    if _smart_inside_active():
        conn = snapshot.get("connection") or snapshot
        rep = {
            "ok": True,
            "schema": SCHEMA,
            "os": platform.system().lower(),
            "iface": conn.get("iface", ""),
            "link_preserved": True,
            "appears_connected": True,
            "skipped": True,
            "smart_inside": True,
            "coexist_os": True,
            "native_mask_deferred": True,
            "reason": "smart_inside_passthrough",
            "policy_owner": "znetwork",
            "steps": [
                {
                    "step": "smart_inside_policy_owner",
                    "ok": True,
                    "detail": "OS L3 preserved — ZNetwork owns advisory policy only",
                }
            ],
        }
        _log({"event": "takeover_deferred", **{k: rep.get(k) for k in ("ok", "os", "iface", "reason")}})
        return rep
    system = platform.system().lower()
    if system == "linux":
        rep = _takeover_linux(snapshot)
    elif system == "windows":
        rep = _takeover_stub("windows", snapshot)
    elif system == "darwin":
        rep = _takeover_stub("darwin", snapshot)
    else:
        rep = _takeover_stub(system or "unknown", snapshot)
    _log({"event": "takeover_complete", **{k: rep.get(k) for k in ("ok", "os", "iface", "error")}})
    return rep


def rollback_old_takeover() -> dict[str, Any]:
    """Restore native network manager if a prior destructive handoff masked it."""
    if not ROLLBACK.is_file():
        return {"ok": True, "skipped": True, "reason": "no_rollback_state"}
    try:
        doc = json.loads(ROLLBACK.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": str(exc)}
    steps: list[dict[str, Any]] = []
    iface = str(doc.get("iface") or doc.get("nm_managed_yes") or "").strip()
    for unit in doc.get("linux_unmask") or ["NetworkManager", "systemd-networkd"]:
        rc, out, err = _run(["systemctl", "unmask", str(unit)], sudo=True)
        steps.append({"step": f"unmask_{unit}", "ok": rc == 0, "detail": (err or out or "")[:200]})
        _run(["systemctl", "start", str(unit)], sudo=True)
        steps.append({"step": f"start_{unit}", "ok": True, "detail": str(unit)})
    if iface and platform.system().lower() == "linux":
        rc, out, err = _run(["nmcli", "dev", "set", iface, "managed", "yes"], sudo=True)
        steps.append({"step": "primary_managed_yes", "ok": rc == 0, "detail": (err or out or iface)[:200]})
    try:
        archived = ROLLBACK.with_suffix(".rolled-back.json")
        ROLLBACK.replace(archived)
    except OSError:
        pass
    rep = {
        "ok": True,
        "schema": "znetwork-takeover-rollback/v1",
        "iface": iface,
        "steps": steps,
        "restored_at": _now(),
    }
    _log({"event": "rollback_old_takeover", **{k: rep.get(k) for k in ("ok", "iface")}})
    return rep


def posture() -> dict[str, Any]:
    rb = None
    if ROLLBACK.is_file():
        try:
            rb = json.loads(ROLLBACK.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            rb = None
    return {"schema": SCHEMA, "ok": True, "rollback": rb, "ledger": str(LEDGER)}


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "rollback":
        result = rollback_old_takeover()
    elif cmd == "takeover":
        snap: dict[str, Any] = {}
        if len(sys.argv) > 2:
            try:
                snap = json.loads(sys.argv[2])
            except json.JSONDecodeError:
                pass
        result = takeover(snapshot=snap)
    else:
        result = posture()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())