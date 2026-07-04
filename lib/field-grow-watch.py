#!/usr/bin/env python3
"""Live field grow watch — population, logical edges, DHCP/DNS through the field."""
from __future__ import annotations

import curses
import json
import math
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
PANEL_URL = os.environ.get("NEXUS_FIELD_GROW_API", "http://127.0.0.1:9477/api/field-grow-watch")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M:%S")


def _load(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}


def _run_json(rel: str, args: list[str], *, timeout: float = 12.0) -> dict[str, Any]:
    py = INSTALL / rel
    if not py.is_file():
        return {}
    try:
        proc = subprocess.run(
            [sys.executable, str(py), *args],
            cwd=str(INSTALL),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
        )
        raw = (proc.stdout or "").strip()
        if raw.startswith("{"):
            return json.loads(raw)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        pass
    return {}


def _fetch_api() -> dict[str, Any]:
    try:
        with urllib.request.urlopen(PANEL_URL, timeout=2.5) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, json.JSONDecodeError, TimeoutError):
        return {}


def _population_growth_tick(started: float, base: float = 8_100_000_000, rate: float = 0.009) -> int:
    years = (time.time() - started) / (365.25 * 24 * 3600)
    sim_years = years * 86400
    return int(base * math.pow(1.0 + rate, sim_years))


def collect_snapshot(*, started: float, tick: int) -> dict[str, Any]:
    api = _fetch_api()
    if api.get("ok"):
        snap = dict(api)
        snap["source"] = "api"
        snap["tick"] = tick
        return snap

    scale = _run_json("lib/field-world-dns-dhcp-scale.py", ["json"], timeout=8.0)
    rescue = _load(STATE / "field-rescue-ingress-panel.json") or _run_json("lib/field-rescue-ingress.py", ["json"], timeout=15.0)
    ipv4 = _load(STATE / "field-ipv4-enumerate-panel.json") or _run_json("lib/field-ipv4-enumerate.py", ["json"], timeout=8.0)
    everyone = _load(STATE / "field-everyone-counter-panel.json") or _run_json("lib/field-everyone-counter.py", ["fast"], timeout=6.0)
    dhcp = _load(STATE / "field-dhcp-panel.json")
    planetary = _load(STATE / "field-planetary-dns-dhcp-panel.json")

    cur = scale.get("current") or {}
    logical = scale.get("logical_edges") or {}
    enum = (ipv4.get("counts") or {}) if ipv4 else {}
    leases = len((_load(STATE / "field-dhcp-leases.json").get("leases") or {}))

    pop_sim = _population_growth_tick(started)
    devices_sim = int(pop_sim * 2.75)

    return {
        "ok": True,
        "schema": "field-grow-watch-snapshot/v1",
        "source": "local",
        "tick": tick,
        "updated": _utc(),
        "inside_field": True,
        "edges_are_real": False,
        "population": max(int(cur.get("population") or 0), pop_sim),
        "devices": max(int(cur.get("devices") or 0), devices_sim),
        "logical_edges": int(logical.get("ipv4_enumerated") or enum.get("ipv4_enumerated_total") or cur.get("logical_edges_total") or 2**32),
        "logical_shards": int(logical.get("shards") or cur.get("logical_edge_shards") or 0),
        "hosts_per_shard": int(logical.get("hosts_per_shard") or cur.get("hosts_per_edge") or 4096),
        "planet_dhcp": int(enum.get("planet_dhcp_total") or (planetary.get("counts") or {}).get("planet_dhcp_total") or 2**32),
        "planet_dns": int(enum.get("planet_dns_total") or (planetary.get("counts") or {}).get("planet_dns_total") or 2**32),
        "local_dhcp_leases": max(leases, int((planetary.get("counts") or {}).get("field_dhcp_leases") or 0)),
        "dhcp_pool_slots": (rescue.get("dhcp_pool") or {}).get("host_slots") or 610,
        "quarantined": int(dhcp.get("quarantined") or 0),
        "soft_offers": int(dhcp.get("soft_offers") or 0),
        "everyone_total": int(everyone.get("everyone_total") or 0),
        "qemu_witnesses": int((everyone.get("arcade_lobby") or {}).get("qemu_witnesses") or 0),
        "ingress_policy": scale.get("ingress_policy") or "quarantine_not_kill",
        "motto": "Inside field — all IPs, logical edges grow",
    }


def build_api_payload() -> dict[str, Any]:
    snap = collect_snapshot(started=time.time(), tick=0)
    snap["schema"] = "field-grow-watch/v1"
    snap["api"] = "/api/field-grow-watch"
    return snap


def _fmt_big(n: int | float) -> str:
    n = float(n)
    if n >= 1e12:
        return f"{n/1e12:.3f}T"
    if n >= 1e9:
        return f"{n/1e9:.3f}B"
    if n >= 1e6:
        return f"{n/1e6:.2f}M"
    if n >= 1e3:
        return f"{n/1e3:.1f}K"
    return str(int(n))


def _bar(value: float, width: int = 32) -> str:
    value = max(0.0, min(1.0, value))
    filled = int(value * width)
    return "#" * filled + "." * (width - filled)


class GrowWatch:
    def __init__(self, stdscr: curses.window) -> None:
        self.stdscr = stdscr
        self.tick = 0
        self.started = time.time()
        self.history: list[int] = []
        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_CYAN, -1)
            curses.init_pair(2, curses.COLOR_GREEN, -1)
            curses.init_pair(3, curses.COLOR_YELLOW, -1)
            curses.init_pair(4, curses.COLOR_MAGENTA, -1)
            curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLUE)

    def _say(self, y: int, x: int, text: str, attr: int = 0) -> None:
        h, w = self.stdscr.getmaxyx()
        if y < 0 or y >= h or x >= w:
            return
        try:
            self.stdscr.addstr(y, x, text[: max(0, w - x - 1)], attr)
        except curses.error:
            pass

    def draw(self, snap: dict[str, Any]) -> None:
        h, w = self.stdscr.getmaxyx()
        self.stdscr.erase()
        pop = int(snap.get("population") or 0)
        self.history.append(pop)
        if len(self.history) > 48:
            self.history.pop(0)
        max_h = max(self.history) if self.history else pop
        min_h = min(self.history) if self.history else pop
        span = max(1, max_h - min_h)
        spark = "".join(
            "▁▂▃▄▅▆▇█"[min(7, int((v - min_h) / span * 7))]
            for v in self.history[-(w - 4):]
        )

        hdr = f" FIELD GROW WATCH | inside field | logical edges | tick {self.tick} | {_utc()} | q quit "
        self._say(0, 0, hdr.ljust(w - 1)[: w - 1], curses.color_pair(5) | curses.A_BOLD)
        self._say(1, 0, f" source {snap.get('source','?')} | {snap.get('motto','')}"[: w - 1], curses.color_pair(1))

        rows = [
            ("Population", _fmt_big(pop), curses.color_pair(2)),
            ("Devices", _fmt_big(snap.get("devices", 0)), curses.color_pair(2)),
            ("Logical edges (all IPs)", _fmt_big(snap.get("logical_edges", 0)), curses.color_pair(3)),
            ("Logical shards", _fmt_big(snap.get("logical_shards", 0)), curses.color_pair(3)),
            ("Hosts / shard", str(snap.get("hosts_per_shard", 4096)), curses.color_pair(3)),
            ("Planet DHCP leases", _fmt_big(snap.get("planet_dhcp", 0)), curses.color_pair(2)),
            ("Planet DNS records", _fmt_big(snap.get("planet_dns", 0)), curses.color_pair(2)),
            ("Local DHCP leases", str(snap.get("local_dhcp_leases", 0)), curses.color_pair(2)),
            ("DHCP pool slots", str(snap.get("dhcp_pool_slots", 0)), curses.color_pair(4)),
            ("Quarantined (soft)", str(snap.get("quarantined", 0)), curses.color_pair(4)),
            ("Everyone total", str(snap.get("everyone_total", 0)), curses.color_pair(4)),
            ("QEMU witnesses", str(snap.get("qemu_witnesses", 0)), curses.color_pair(4)),
            ("Edges are real", str(snap.get("edges_are_real", False)), curses.color_pair(1)),
            ("Ingress", str(snap.get("ingress_policy", "")), curses.color_pair(1)),
        ]
        y = 3
        self._say(y, 0, "── growth ──", curses.A_BOLD)
        y += 1
        self._say(y, 0, spark[: w - 2])
        y += 2
        for label, val, attr in rows:
            self._say(y, 2, f"{label:<26} {val:>14}", attr)
            y += 1
            if y >= h - 3:
                break

        grow = min(1.0, len(self.history) / 48.0)
        self._say(h - 2, 0, f" grow pulse [{_bar(grow, min(40, w - 14))}] ", curses.color_pair(2))
        self._say(h - 1, 0, " bash: ./scripts/field-grow-watch.sh | api: /api/field-grow-watch | panel: /field-grow-watch "[: w - 1], curses.color_pair(1))
        self.stdscr.refresh()

    def run(self) -> None:
        self.stdscr.nodelay(False)
        self.stdscr.timeout(1000)
        curses.curs_set(0)
        while True:
            snap = collect_snapshot(started=self.started, tick=self.tick)
            self.draw(snap)
            self.tick += 1
            ch = self.stdscr.getch()
            if ch in (ord("q"), ord("Q"), 27):
                break


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1].lower() in ("json", "api", "once"):
        print(json.dumps(build_api_payload(), ensure_ascii=False, indent=2))
        return 0

    def _curses_main(stdscr: curses.window) -> None:
        GrowWatch(stdscr).run()

    try:
        curses.wrapper(_curses_main)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())