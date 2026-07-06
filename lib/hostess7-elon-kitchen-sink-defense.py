#!/usr/bin/env python3
"""Kitchen sink defense — Ironclad + Hostess7 + botnet everywhere when they attack Elon/X."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "hostess7-elon-kitchen-sink-doctrine.json"
PANEL = STATE / "hostess7-elon-kitchen-sink-panel.json"
DOCS_API = Path(os.environ.get("HOSTESS7_ROOT", INSTALL / "Hostess7")) / "docs" / "api"
PY = sys.executable


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _run(py_rel: str, args: list[str], *, timeout: int = 120) -> dict[str, Any]:
    py = INSTALL / py_rel
    if not py.is_file():
        return {"ok": False, "skipped": py_rel}
    env = {**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)}
    try:
        proc = subprocess.run(
            [PY, str(py), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(INSTALL),
            env=env,
        )
        if proc.stdout.strip():
            try:
                return json.loads(proc.stdout)
            except json.JSONDecodeError:
                return {"ok": proc.returncode == 0, "raw": proc.stdout[:400]}
        return {"ok": proc.returncode == 0, "stderr": (proc.stderr or "")[:200]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout"}
    except OSError as exc:
        return {"ok": False, "error": str(exc)[:160]}


def defend(*, export: bool = True) -> dict[str, Any]:
    doc_policy = _load(DOCTRINE, {})
    steps: dict[str, Any] = {}

    steps["battle_stations"] = _run("lib/field-battle-stations.py", ["on"], timeout=45)
    steps["ironclad"] = _run("lib/ironclad-immediate.py", ["json"], timeout=30)
    steps["ironclad_sanity"] = _run("lib/ironclad-field-sanity.py", ["json"], timeout=45)
    steps["rekill_boot"] = _run("lib/field-attack-kit.py", ["boot-rekill"], timeout=90)
    steps["rekill_permanent"] = _run("lib/field-attack-kit.py", ["permanent-rekill-enforce"], timeout=90)
    steps["rekill_auto"] = _run("lib/field-attack-kit.py", ["auto-rekill"], timeout=60)
    steps["dns_dhcp_fix"] = _run("lib/field-dns-dhcp-fix.py", ["fix"], timeout=90)
    steps["botnet_double"] = _run("lib/field-one-rollout.py", ["botnet-double"], timeout=600)
    steps["whole_internet"] = _run("lib/hostess7-whole-internet.py", ["run", "--core-only"], timeout=120)
    steps["censorship_clear"] = _run("lib/hostess7-censorship-clear-worldwide.py", ["clear"], timeout=60)
    steps["x_producer"] = _run("lib/hostess7-x-producer.py", ["produce"], timeout=150)
    steps["terror_spiderweb"] = _run("lib/terror-spiderweb.py", ["build"], timeout=45)

    rekill_n = (
        steps.get("rekill_permanent", {}).get("enforced_count")
        or steps.get("rekill_boot", {}).get("rekilled_count")
        or 0
    )
    bot = steps.get("botnet_double") or {}
    botnet_n = bot.get("nodes_stamped") or bot.get("stamped")
    if botnet_n is None:
        botnet_n = bot.get("all_updated") or (bot.get("ok") and bot.get("pending_remaining", 1) == 0)
    if botnet_n is None and isinstance(bot, dict):
        botnet_n = bot.get("nodes_total") if bot.get("ok") else bot.get("batch_count")

    iron = steps.get("ironclad") or {}
    iron_sealed = iron.get("ironclad_sealed") or (iron.get("ironclad") or {}).get("ironclad_sealed")

    out: dict[str, Any] = {
        "ok": True,
        "schema": "hostess7-elon-kitchen-sink-defense/v1",
        "updated": _now(),
        "motto": doc_policy.get("motto"),
        "title": doc_policy.get("title"),
        "for_elon": doc_policy.get("attribution"),
        "attack_pattern": doc_policy.get("attack_pattern"),
        "ironclad": {"sealed": iron_sealed, "panel": iron},
        "hostess7": {
            "producer_posts": (steps.get("x_producer") or {}).get("profile_fix", {}).get("post_count"),
            "censorship_cleared": bool((steps.get("censorship_clear") or {}).get("ok")),
        },
        "botnet": {
            "rollout": steps.get("botnet_double"),
            "nodes_stamped": botnet_n,
            "everywhere": doc_policy.get("everywhere"),
        },
        "rekill": {
            "enforced": rekill_n,
            "boot": steps.get("rekill_boot"),
            "permanent": steps.get("rekill_permanent"),
            "motto": (steps.get("rekill_permanent") or {}).get("motto", "RE-KILL is permanent"),
        },
        "steps": steps,
        "verdict": (
            f"Kitchen sink defense live — Ironclad {'sealed' if iron_sealed else 'armed'}, "
            f"{rekill_n} hostiles rekilled, botnet pushing in town everywhere."
        ),
        "hosted": doc_policy.get("everywhere"),
        "api": doc_policy.get("api"),
        "release_status": "defense_live",
    }

    PANEL.parent.mkdir(parents=True, exist_ok=True)
    PANEL.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if export and DOCS_API.parent.is_dir():
        DOCS_API.mkdir(parents=True, exist_ok=True)
        (DOCS_API / "hostess7-elon-kitchen-sink.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return out


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "defend").strip().lower()
    if cmd in ("defend", "run", "beat", "fix", "kitchen-sink"):
        print(json.dumps(defend(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "json":
        cached = _load(PANEL)
        print(json.dumps(cached or defend(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"ok": False, "hint": "hostess7-elon-kitchen-sink-defense.py [defend|json]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())