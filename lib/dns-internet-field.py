#!/usr/bin/env pythong
"""DNS Internet Field — passive whole-internet registry held in field storage.

WHOLE: every IANA TLD slot + root delegation chain (all timestamps exist at once).
LOCAL NOW: resolver cache + live trace answers merged into field strength.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
SEED = INSTALL / "data" / "dns-internet-tld-seed.json"
OUT_JSON = STATE / "dns-internet-harvest.json"
PANEL_SLICE = STATE / "dns-internet-harvest-panel.json"
DNS_STATE = STATE / "field-dns.json"
CACHE_HINT = STATE / "field-dns-cache-hints.jsonl"


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


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _run(cmd: list[str], timeout: int = 20) -> str:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        return (proc.stdout or "") + (proc.stderr or "")
    except (OSError, subprocess.TimeoutExpired):
        return ""


def _pull_iana_tlds() -> list[str]:
    """Passive pull of global TLD delegation from root (dig +trace)."""
    text = _run(["dig", "+short", "NS", "."])
    tlds: set[str] = set()
    for line in text.splitlines():
        host = line.strip().rstrip(".").lower()
        if not host or "." not in host:
            continue
        label = host.split(".", 1)[0]
        if re.match(r"^[a-z0-9-]{1,63}$", label):
            tlds.add(label)
    if not tlds:
        seed = _load_json(SEED, {})
        tlds.update(str(t).lower().lstrip(".") for t in (seed.get("tlds") or []))
    return sorted(tlds)


def _passive_cache_domains() -> dict[str, dict[str, Any]]:
    """Domains seen by truth resolver — LOCAL NOW layer."""
    seen: dict[str, dict[str, Any]] = {}
    if CACHE_HINT.is_file():
        try:
            for line in CACHE_HINT.read_text(encoding="utf-8", errors="replace").splitlines()[-2000:]:
                if not line.strip():
                    continue
                row = json.loads(line)
                name = str(row.get("qname") or "").lower().rstrip(".")
                if name:
                    seen[name] = row
        except (OSError, json.JSONDecodeError):
            pass
    dns_doc = _load_json(DNS_STATE, {})
    stats = dns_doc.get("stats") or {}
    if int(stats.get("queries") or 0) > 0 and not seen:
        seen["localhost"] = {"qname": "localhost", "strength": 100, "source": "loopback"}
    return seen


def _apex_for_tld(tld: str) -> str:
    return f"nic.{tld}" if tld not in ("arpa", "root") else tld


def _probe_domain(domain: str) -> dict[str, Any]:
    text = _run(["dig", "+short", "+time=3", "+tries=1", "A", domain])
    answers = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.startswith(";")]
    strength = min(100, 20 + len(answers) * 25) if answers else 0
    return {
        "domain": domain,
        "answers": answers[:8],
        "strength": strength,
        "recognized": bool(answers),
        "pulled_at": _now(),
    }


def build_internet_field(*, pull_live: bool = True, probe_limit: int = 48) -> dict[str, Any]:
    seed = _load_json(SEED, {})
    tlds = _pull_iana_tlds()
    cache = _passive_cache_domains()
    entries: list[dict[str, Any]] = []
    recognized = 0
    probed = 0

    for tld in tlds:
        apex = _apex_for_tld(tld)
        slot = {
            "tld": tld,
            "domain": apex,
            "kind": "tld_slot",
            "strength": 0,
            "recognized": False,
            "answers": [],
            "source": "iana_root",
        }
        for dom, meta in cache.items():
            if dom == apex or dom.endswith(f".{tld}"):
                slot["recognized"] = True
                slot["strength"] = max(slot["strength"], int(meta.get("strength") or 60))
                slot["source"] = "local_cache"
                break
        if pull_live and probed < probe_limit and not slot["recognized"]:
            hit = _probe_domain(apex)
            probed += 1
            if hit.get("recognized"):
                slot.update(hit)
                slot["source"] = "live_trace"
        entries.append(slot)
        if slot.get("recognized"):
            recognized += 1

    for dom, meta in cache.items():
        if any(e.get("domain") == dom for e in entries):
            continue
        entries.append({
            "tld": dom.split(".")[-1] if "." in dom else dom,
            "domain": dom,
            "kind": "cached_query",
            "strength": int(meta.get("strength") or 50),
            "recognized": True,
            "answers": meta.get("answers") or [],
            "source": "local_cache",
        })
        recognized += 1

    by_tld: dict[str, list[dict[str, Any]]] = {}
    for e in entries:
        by_tld.setdefault(str(e.get("tld") or ""), []).append(e)

    out = {
        "schema": "dns-internet-harvest/v1",
        "updated": _now(),
        "motto": "WHOLE internet in field storage — every TLD slot. LOCAL NOW merges live resolver cache.",
        "model": {
            "whole": "All IANA TLD delegation slots exist in field at once (passive everywhere).",
            "local_now": "Active resolver cache + trace probes mark recognized strength.",
            "linear_time": "Each pull appends timestamp; full timeline retained in field JSONL.",
        },
        "total_slots": len(entries),
        "tld_count": len(tlds),
        "recognized_slots": recognized,
        "silent_slots": len(entries) - recognized,
        "coverage_pct": round((recognized / len(entries)) * 100.0, 1) if entries else 0.0,
        "entries": entries,
        "by_tld": {k: v for k, v in sorted(by_tld.items())},
        "root_servers": seed.get("root_servers") or _load_json(
            INSTALL / "data" / "dns-legal-rfc-seed.json", {},
        ).get("root_servers") or [],
        "pull": {"live_probes": probed, "pull_live": pull_live},
    }
    _save_json(OUT_JSON, out)
    _save_json(PANEL_SLICE, out)
    return out


def record_query(qname: str, answers: list[str] | None = None) -> None:
    """Append LOCAL NOW observation (called from field-dns on cache write)."""
    try:
        CACHE_HINT.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "ts": _now(),
            "qname": qname.lower().rstrip("."),
            "answers": (answers or [])[:8],
            "strength": min(100, 30 + len(answers or []) * 20),
        }
        with CACHE_HINT.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def panel_json() -> dict[str, Any]:
    doc = _load_json(PANEL_SLICE, {})
    if doc.get("updated"):
        return doc
    return build_internet_field(pull_live=False)


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    if cmd == "build":
        pull = "--no-pull" not in sys.argv
        print(json.dumps(build_internet_field(pull_live=pull), ensure_ascii=False))
        return 0
    if cmd == "pull":
        print(json.dumps(build_internet_field(pull_live=True), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: dns-internet-field.py [json|build|pull]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())