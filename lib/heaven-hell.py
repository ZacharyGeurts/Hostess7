#!/usr/bin/env pythong
"""NEXUS Heaven / Hell — we know Heaven from Hell.

Heaven: permitted flows, operator trust, zero friendly fire.
Hell: harm chosen — no mercy, forever block, rip it up.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
DOCTRINE_PATH = INSTALL / "data" / "heaven-hell-doctrine.json"
INTENT = STATE / "connection-intent.json"
HOSTILE = STATE / "field-hostile.tsv"
OUT_JSON = STATE / "heaven-hell.json"
RIP_LOG = STATE / "heaven-hell-rip.jsonl"

_DEFAULT_MOTTO = (
    "We know Heaven from Hell. To those who chose Hell, we also choose it for them. "
    "No mercy. No friendly fire. God Bless."
)
_DEFAULT_TAGLINE = "Heaven passes at zero cost. Hell gets ripped — block forever, eradicate, strike."
_DEFAULT_KNOW = (
    "Know that nothing is unseen and nothing is fully secure. "
    "We can't hide all the rocks, so send Hell to Hell."
)


def _doctrine() -> dict[str, Any]:
    try:
        doc = json.loads(DOCTRINE_PATH.read_text(encoding="utf-8"))
        return doc if isinstance(doc, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _motto() -> str:
    return str(_doctrine().get("heaven_hell_motto") or _DEFAULT_MOTTO)


def _tagline() -> str:
    return str(_doctrine().get("tagline") or _DEFAULT_TAGLINE)


def _know_doctrine() -> str:
    return str(_doctrine().get("motto") or _DEFAULT_KNOW)


MOTTO = _motto()
TAGLINE = _tagline()
KNOW_DOCTRINE = _know_doctrine()

HEAVEN_VERDICTS = frozenset({"USER_OK", "EPHEMERAL", "MONITOR"})
HELL_VERDICTS = frozenset({"HARM_CANDIDATE", "SUSPICIOUS"})

_fg = None


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



def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _friendly_guard():
    global _fg
    if _fg is not None:
        return _fg
    import importlib.util

    spec = importlib.util.spec_from_file_location("friendly_guard", INSTALL / "lib" / "friendly-guard.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    _fg = mod
    return mod


def classify_row(row: dict[str, Any]) -> tuple[str, bool]:
    """Return (soul_side, hell_chosen). soul_side: heaven | hell | limbo."""
    verdict = str(row.get("verdict") or "")
    trust_rank = int(row.get("trust_rank") or 5)
    scores = row.get("scores") or {}
    if int(scores.get("operator_auth") or 0) >= 10:
        return "heaven", False
    if trust_rank <= 2 and verdict in HEAVEN_VERDICTS:
        return "heaven", False
    if row.get("hell_chosen"):
        return "hell", True
    if row.get("kill_eligible") or verdict == "HARM_CANDIDATE":
        return "hell", True
    if verdict in HELL_VERDICTS and int(scores.get("process_trust") or 0) <= 3:
        return "hell", bool(row.get("kill_eligible"))
    return "limbo", False


def heaven_protected(ip: str, row: dict[str, Any] | None = None) -> tuple[bool, str]:
    """No friendly fire — refuse rip when Heaven-side."""
    fg = _friendly_guard()
    monitor = {
        "verdict": (row or {}).get("verdict") or "MONITOR",
        "trust_rank": (row or {}).get("trust_rank", 2),
        "process": (row or {}).get("process") or "",
        "axis_scores": (row or {}).get("scores") or {},
    }
    refuse, reason = fg.refuse_kill(ip, monitor)
    if refuse:
        return True, f"heaven_protected:{reason}"
    soul, _ = classify_row(row or {})
    if soul == "heaven":
        return True, "heaven_protected:soul_side"
    return False, "hell_eligible"


def build_status(panel: dict[str, Any] | None = None) -> dict[str, Any]:
    panel = panel or _load_json(STATE / "threat-panel.json", {})
    gk = panel.get("gatekeeper") or {}
    conns = gk.get("connections") or []
    heaven_rows: list[dict[str, Any]] = []
    hell_rows: list[dict[str, Any]] = []
    limbo = 0
    for c in conns:
        side, hell = classify_row(c)
        slim = {
            "ip": c.get("remote_ip"),
            "port": c.get("remote_port"),
            "process": c.get("process"),
            "verdict": c.get("verdict"),
            "hell_chosen": hell,
        }
        if side == "heaven":
            heaven_rows.append(slim)
        elif side == "hell":
            hell_rows.append(slim)
        else:
            limbo += 1
    hostile = 0
    if HOSTILE.is_file():
        try:
            hostile = max(0, sum(1 for _ in HOSTILE.read_text(encoding="utf-8").splitlines()) - 1)
        except OSError:
            pass
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "hostility_priority", INSTALL / "lib" / "hostility-priority.py",
        )
        hp = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(hp)
        hell_rows = hp.sort_hell_first(hell_rows)
    except Exception:
        pass

    doc = _doctrine()
    return {
        "updated": _now(),
        "motto": _motto(),
        "tagline": _tagline(),
        "know_doctrine": _know_doctrine(),
        "send_hell": str(doc.get("send_hell") or "Send Hell to Hell — hostility first, rip ready, no mercy."),
        "visibility": doc.get("visibility") or {},
        "no_mercy": True,
        "no_friendly_fire": True,
        "hostility_priority": "hell_first",
        "heaven": {
            "count": len(heaven_rows),
            "label": "Heaven",
            "flows": heaven_rows[:16],
        },
        "hell": {
            "count": len(hell_rows),
            "label": "Hell",
            "chosen": sum(1 for r in hell_rows if r.get("hell_chosen")),
            "flows": hell_rows[:16],
        },
        "limbo_count": limbo,
        "hostile_registry": hostile,
        "rip_ready": len([r for r in hell_rows if r.get("hell_chosen")]),
    }


def rip_hell(doc: dict[str, Any] | None = None) -> dict[str, Any]:
    """No mercy execution for Hell-chosen only. Heaven never touched."""
    doc = doc if doc is not None else _load_json(INTENT, {})
    import subprocess

    lethal_py = INSTALL / "lib" / "lethal-enforcement.py"
    if lethal_py.is_file():
        proc = subprocess.run(
            ["pythong", str(lethal_py), "cycle"],
            env={**os.environ, "NEXUS_STATE_DIR": str(STATE), "NEXUS_INSTALL_ROOT": str(INSTALL)},
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if proc.stdout.strip():
            try:
                cycle = json.loads(proc.stdout)
                if cycle.get("executed_count", 0) > 0:
                    out = {
                        "ok": True,
                        "updated": _now(),
                        "motto": MOTTO,
                        "ripped_count": cycle.get("executed_count", 0),
                        "spared_heaven": cycle.get("spared_heaven", []),
                        "lethal_cycle": cycle,
                        "no_friendly_fire": True,
                    }
                    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                    return out
            except json.JSONDecodeError:
                pass

    ripped: list[dict[str, Any]] = []
    spared: list[dict[str, Any]] = []
    for row in doc.get("connections") or []:
        side, hell = classify_row(row)
        if side == "heaven" or not hell:
            continue
        ip = str(row.get("remote_ip") or "").strip()
        if not ip:
            continue
        protected, reason = heaven_protected(ip, row)
        if protected:
            spared.append({"ip": ip, "reason": reason})
            continue
        pid = str(row.get("pid") or "0")
        kill_reason = str(row.get("kill_reason") or "hell_chosen")
        entry: dict[str, Any] = {"ip": ip, "hell_chosen": True, "reason": kill_reason, "ok": False}
        pest = INSTALL / "lib" / "pest-arsenal.sh"
        if pest.is_file() and pid.isdigit() and int(pid) > 0:
            subprocess.run(
                ["bash", "-c", f"source '{pest}'; nexus_pest_eradicate '{ip}' '{pid}' 'HELL_CHOSEN' ''"],
                env={**os.environ, "NEXUS_STATE_DIR": str(STATE), "NEXUS_INSTALL_ROOT": str(INSTALL)},
                timeout=12,
                check=False,
            )
            entry["eradicated"] = True
        fw = INSTALL / "lib" / "firewall-sentinel.sh"
        if fw.is_file():
            subprocess.run(
                [
                    "bash",
                    "-c",
                    (
                        f"source '{INSTALL}/lib/nexus-common.sh'; source '{fw}'; "
                        f"nexus_firewall_block_ip_forever out '{ip}' 'heaven_hell:no_mercy' || true; "
                        f"nexus_firewall_block_ip_forever in '{ip}' 'heaven_hell:no_mercy' || true"
                    ),
                ],
                env={**os.environ, "NEXUS_STATE_DIR": str(STATE), "NEXUS_INSTALL_ROOT": str(INSTALL)},
                timeout=12,
                check=False,
            )
            entry["forever_block"] = True
        kit = INSTALL / "lib" / "field-attack-kit.py"
        if kit.is_file():
            subprocess.run(
                [
                    "pythong",
                    str(kit),
                    "kill",
                    ip,
                    "HELL_CHOSEN",
                    "critical",
                    f"heaven_hell:rip:{kill_reason}",
                ],
                env={**os.environ, "NEXUS_STATE_DIR": str(STATE), "NEXUS_INSTALL_ROOT": str(INSTALL)},
                timeout=25,
                check=False,
            )
            entry["strike"] = True
        entry["ok"] = True
        ripped.append(entry)
        try:
            with RIP_LOG.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({"ts": _now(), **entry}, ensure_ascii=False) + "\n")
        except OSError:
            pass

    out = {
        "ok": True,
        "updated": _now(),
        "motto": MOTTO,
        "ripped": ripped,
        "ripped_count": len(ripped),
        "spared_heaven": spared,
        "no_friendly_fire": True,
    }
    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: heaven-hell.py [status|rip|json]", file=sys.stderr)
        return 1
    cmd = sys.argv[1]
    if cmd == "rip":
        json.dump(rip_hell(), sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0
    if cmd in ("status", "json"):
        json.dump(build_status(), sys.stdout, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0
    print("usage: heaven-hell.py [status|rip|json]", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())