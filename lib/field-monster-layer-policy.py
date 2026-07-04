#!/usr/bin/env python3
"""Monster layer policy — launches above KILROY must run through AmmoLang boundary."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STACK = INSTALL / "data" / "field-stack-layer-doctrine.json"

# Stack order ≤2 = at or below KILROY PC core (hardware, nexus_c2, kilroy)
KILROY_MAX_ORDER = 2
ABOVE_KILROY_IDS = frozenset({
    "ammoos", "ammoos-desktop", "queen", "queen-browser", "userland",
    "os-software", "broadcaster", "ammonet", "panels",
})
KILROY_IDS = frozenset({"kilroy", "nexus_c2", "nexus-c2", "dns-kilroy-lane", "hardware"})


def _load_stack() -> dict[str, Any]:
    try:
        return json.loads(STACK.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def layer_order(layer_id: str) -> int:
    doc = _load_stack()
    lid = str(layer_id or "").strip().lower().replace("-", "_")
    for row in doc.get("layers_bottom_up") or []:
        if str(row.get("id") or "").lower().replace("-", "_") == lid:
            return int(row.get("order") or 99)
    screen = (doc.get("screen_layers") or {}).get("layers") or {}
    for key, spec in screen.items():
        if not isinstance(spec, dict):
            continue
        if str(spec.get("id") or "").lower().replace("-", "_") == lid:
            try:
                return int(key)
            except (TypeError, ValueError):
                pass
    return 99


def infer_layer(*, label: str = "", cmd: list[str] | None = None) -> dict[str, Any]:
    blob = f"{label} {' '.join(cmd or [])}".lower()
    lid = "userland"
    if any(x in blob for x in ("kilroy-core", "kilroy_core", "znetwork-field", "field-dns", "threat-panel")):
        lid = "kilroy"
    elif any(x in blob for x in ("nexus-c2", "nexus_c2", "command/", "connection-gatekeeper")):
        lid = "nexus_c2"
    elif any(x in blob for x in ("queen-world", "queen-browser", "queen/", "9481")):
        lid = "queen"
    elif any(x in blob for x in ("field-host-desktop", "ammoos", "field-desktop", "9477/field")):
        lid = "ammoos"
    elif any(x in blob for x in ("field-broadcaster", "ammonet", "obs-field")):
        lid = "os-software"
    order = layer_order(lid)
    return {"layer_id": lid, "order": order, "above_kilroy": order > KILROY_MAX_ORDER}


def needs_ammolang(*, label: str = "", cmd: list[str] | None = None) -> bool:
    if os.environ.get("MONSTER_SKIP_AML", "").strip() in ("1", "true", "yes"):
        return False
    if os.environ.get("AML_BOUNDARY_ACTIVE", "").strip() in ("1", "true", "yes"):
        return False
    lbl = str(label or "").lower()
    if lbl.startswith("ammolang:") and any(x in lbl for x in ("tasks", "list", "assist")):
        return False
    argv = [str(a) for a in (cmd or [])]
    if any("field-ammolang-build.py" in a for a in argv):
        tail = {str(a).lower() for a in argv}
        if tail & {"tasks", "list", "assist"}:
            return False
    info = infer_layer(label=label, cmd=cmd)
    if info["layer_id"] in KILROY_IDS:
        return False
    return bool(info["above_kilroy"])


def ammolang_wrap(label: str, cmd: list[str]) -> list[str]:
    """Rewrite argv to ammolang-run.sh exec — monster label preserved."""
    aml = INSTALL / "lib" / "ammolang-run.sh"
    target = f"monster:{label or 'launch'}"
    if cmd and str(cmd[0]).endswith(".py"):
        rel = cmd[0]
        try:
            rel = str(Path(cmd[0]).resolve().relative_to(INSTALL))
        except ValueError:
            pass
        target = f"py:{rel}"
    elif cmd and ("/scripts/" in cmd[0] or cmd[0].endswith(".sh")):
        try:
            rel = str(Path(cmd[0]).resolve().relative_to(INSTALL))
            target = f"script:{rel}"
        except ValueError:
            target = f"script:{Path(cmd[0]).name}"
    return ["bash", str(aml), "exec", target, "--", *cmd]


def main() -> int:
    args = sys.argv[1:]
    cmd = "needs_ammolang"
    label = os.environ.get("MONSTER_LABEL", "")
    rest: list[str] = []
    i = 0
    while i < len(args):
        if args[i] == "needs_ammolang":
            i += 1
            continue
        if args[i] == "--label" and i + 1 < len(args):
            label = args[i + 1]
            i += 2
            continue
        if args[i] == "--":
            rest = args[i + 1 :]
            break
        rest.append(args[i])
        i += 1
    info = infer_layer(label=label, cmd=rest)
    out = {
        "ok": True,
        "schema": "field-monster-layer-policy/v1",
        "needs_ammolang": needs_ammolang(label=label, cmd=rest),
        "kilroy_max_order": KILROY_MAX_ORDER,
        "ammolang_run": str(INSTALL / "lib" / "ammolang-run.sh"),
        **info,
    }
    if rest and out["needs_ammolang"]:
        out["wrapped_argv"] = ammolang_wrap(label, rest)
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())