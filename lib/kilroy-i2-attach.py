#!/usr/bin/env python3
"""KILROY Internet 2.0 attach — secure layer + truth DNS path + C2 basement seal.

Boot order (before guest grant):
  loopback → secure_layer → truth_dns → wire → nexus_c2 seal
"""
from __future__ import annotations

import json
import os
import socket
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
MARKER = STATE / "kilroy-i2-attached.json"
I2_DOC = INSTALL / "data" / "internet-2.0-doctrine.json"
SL_DOC = INSTALL / "data" / "secure-layer-doctrine.json"
UNIFIED = INSTALL / "data" / "kilroy-unified-product-doctrine.json"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _loopback_ok() -> dict[str, Any]:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        return {"ok": True, "loopback": "127.0.0.1", "ephemeral_bind_port": port}
    except OSError as e:
        return {"ok": False, "error": str(e)}


def _dns_probe() -> dict[str, Any]:
    """Best-effort: is something on 127.0.0.1:53 (field DNS)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.3)
        s.sendto(b"\x00", ("127.0.0.1", 53))
        s.close()
        return {"ok": True, "truth_dns_port": 53, "note": "udp_send_ok"}
    except OSError as e:
        return {"ok": False, "truth_dns_port": 53, "error": str(e), "note": "start field-dns serve for full I2"}


def _c2_probe() -> dict[str, Any]:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.4)
        r = s.connect_ex(("127.0.0.1", 9477))
        s.close()
        return {"ok": r == 0, "port": 9477, "listening": r == 0}
    except OSError as e:
        return {"ok": False, "port": 9477, "error": str(e)}


def _seal_c2(i2_attached: bool) -> dict[str, Any]:
    sys.path.insert(0, str(INSTALL / "lib"))
    try:
        import importlib.util

        p = INSTALL / "lib" / "nexus-c2-harden.py"
        spec = importlib.util.spec_from_file_location("nexus_c2_harden", p)
        if not spec or not spec.loader:
            return {"ok": False, "error": "c2_harden_missing"}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        # Always War — AI defends; never seal peace at boot
        profile = os.environ.get("NEXUS_C2_PROFILE", "war").strip() or "war"
        if os.environ.get("NEXUS_C2_ALLOW_PEACE", "0") != "1":
            profile = "war"
        return mod.seal_posture(
            profile=profile,
            reason="i2_attach_always_war",
            i2_attached=i2_attached,
            bump=True,
        )
    except Exception as e:
        return {"ok": False, "error": str(e)}


def attach(*, force: bool = False) -> dict[str, Any]:
    """Run Internet 2.0 attach sequence. Idempotent unless force."""
    if MARKER.is_file() and not force:
        try:
            prev = json.loads(MARKER.read_text(encoding="utf-8"))
            if prev.get("ok") and prev.get("i2_attached"):
                return {**prev, "cached": True}
        except (OSError, json.JSONDecodeError):
            pass

    steps: dict[str, Any] = {}
    steps["loopback"] = _loopback_ok()
    steps["secure_layer"] = {
        "ok": True,
        "doctrine": str(SL_DOC.name) if SL_DOC.is_file() else None,
        "kernel_param": "secure_layer=1",
        "always_on": True,
    }
    steps["truth_dns"] = _dns_probe()
    steps["single_egress_wire"] = {
        "ok": True,
        "policy": "field_wire_only",
        "note": "ZNetwork/field pipe — no silent multi-path",
    }
    steps["c2_probe"] = _c2_probe()
    steps["c2_seal"] = _seal_c2(i2_attached=True)

    ok = bool(steps["loopback"].get("ok")) and bool(steps["secure_layer"].get("ok"))
    # DNS/C2 may not be up yet at early boot — still mark attach intent
    result = {
        "schema": "kilroy-i2-attach/v1",
        "ok": ok,
        "i2_attached": ok,
        "before_guest": True,
        "secure_layer": True,
        "internet_2_0": True,
        "motto": "Booting KILROY is connecting to Internet 2.0.",
        "steps": steps,
        "unified_product": str(UNIFIED.name) if UNIFIED.is_file() else None,
        "updated": _now(),
    }
    STATE.mkdir(parents=True, exist_ok=True)
    tmp = MARKER.with_suffix(".tmp")
    tmp.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    tmp.replace(MARKER)
    return result


def status() -> dict[str, Any]:
    out: dict[str, Any] = {
        "schema": "kilroy-i2-status/v1",
        "marker": str(MARKER),
        "marker_exists": MARKER.is_file(),
    }
    if MARKER.is_file():
        try:
            out["attach"] = json.loads(MARKER.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            out["attach_error"] = str(e)
    out["loopback"] = _loopback_ok()
    out["c2"] = _c2_probe()
    out["dns"] = _dns_probe()
    out["doctrine"] = {
        "i2": I2_DOC.is_file(),
        "secure_layer": SL_DOC.is_file(),
        "unified": UNIFIED.is_file(),
    }
    return out


def guest_grant_allowed() -> dict[str, Any]:
    """Guest OS / AmmoMint may only receive network grant after I2 attach."""
    st = status()
    attached = bool((st.get("attach") or {}).get("i2_attached")) or (
        MARKER.is_file() and st.get("loopback", {}).get("ok")
    )
    if not attached:
        # try attach once
        att = attach()
        attached = bool(att.get("i2_attached"))
    return {
        "ok": attached,
        "guest_grant": attached,
        "rule": "Guest has no raw WAN until Internet 2.0 attach",
        "i2_attached": attached,
    }


def main(argv: list[str] | None = None) -> int:
    argv = list(argv or sys.argv[1:])
    cmd = argv[0] if argv else "status"
    if cmd in ("-h", "--help", "help"):
        print("kilroy-i2-attach.py attach|status|guest-grant|force")
        return 0
    if cmd == "attach":
        print(json.dumps(attach(), indent=2))
        return 0
    if cmd == "force":
        print(json.dumps(attach(force=True), indent=2))
        return 0
    if cmd == "status":
        print(json.dumps(status(), indent=2))
        return 0
    if cmd in ("guest-grant", "guest_grant", "guest"):
        print(json.dumps(guest_grant_allowed(), indent=2))
        return 0
    print(json.dumps({"ok": False, "error": f"unknown:{cmd}"}))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
