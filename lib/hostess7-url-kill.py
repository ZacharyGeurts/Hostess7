#!/usr/bin/env python3
"""URL kill — dangerous URLs be gone. Strip, block, never control."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
DOCTRINE = INSTALL / "data" / "hostess7-url-kill-doctrine.json"
ANNOYANCE = INSTALL / "data" / "annoyance-complaints.tsv"
X_PURGE = INSTALL / "data" / "hostess7-x-brand-purge-doctrine.json"


def _resolve_state() -> Path:
    for cand in (
        os.environ.get("NEXUS_FIELD_DRIVE_STATE", "").strip(),
        os.environ.get("NEXUS_STATE_DIR", "").strip(),
    ):
        if cand:
            p = Path(cand)
            if p.is_dir():
                return p
    for p in (
        INSTALL / ".nexus-field-drive" / "nexus-field" / "state",
        INSTALL / ".nexus-state",
    ):
        if p.is_dir():
            return p
    return INSTALL / ".nexus-state"


STATE = _resolve_state()
PANEL = STATE / "hostess7-url-kill-panel.json"
REGISTRY = STATE / "hostess7-url-kill-registry.json"
LEDGER = STATE / "hostess7-url-kill-ledger.jsonl"
BLOCKLIST = STATE / "adblock" / "domains-gone.txt"
URL_RE = re.compile(r"https?://[^\s\"'<>)\]]+", re.I)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _append_ledger(row: dict[str, Any]) -> None:
    try:
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": _now(), **row}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {})


def _host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower().strip()
    except Exception:
        return ""


def _steel_plate_hosts() -> frozenset[str] | None:
    py = INSTALL / "lib" / "field-url-heuristics-steel.py"
    if not py.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("url_steel", py)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "plate_gone_hosts"):
            return mod.plate_gone_hosts()
    except Exception:
        pass
    return None


def gone_hosts() -> frozenset[str]:
    steel = _steel_plate_hosts()
    if steel:
        return steel
    doc = doctrine()
    hosts = {str(h).lower() for h in doc.get("gone_hosts") or []}
    xp = _load(X_PURGE, {})
    for row in xp.get("dangerous_blow") or []:
        if str(row.get("action") or "") in ("block", "drop_lane", "unwrap_kill"):
            h = str(row.get("host") or "").lower()
            if h:
                hosts.add(h)
    if ANNOYANCE.is_file():
        for line in ANNOYANCE.read_text(encoding="utf-8", errors="replace").splitlines()[1:]:
            parts = line.split("\t")
            if len(parts) < 4:
                continue
            dom, cat, score_s = parts[0].lower(), parts[1], parts[2]
            try:
                score = int(score_s)
            except ValueError:
                score = 0
            if score >= 8 or cat in ("lockout", "popup", "popunder"):
                hosts.add(dom)
    return frozenset(hosts)


def _gone_patterns() -> list[re.Pattern[str]]:
    out: list[re.Pattern[str]] = []
    for pat in doctrine().get("gone_patterns") or []:
        try:
            out.append(re.compile(pat, re.I))
        except re.error:
            continue
    return out


def is_gone(url: str) -> dict[str, Any]:
    """Fail-closed — dangerous URL is gone (steel plate authoritative when melded)."""
    py = INSTALL / "lib" / "field-url-heuristics-steel.py"
    if py.is_file():
        try:
            spec = importlib.util.spec_from_file_location("url_steel_gate", py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "gate_url") and _load(STATE / "field-url-heuristics-steel-plate.json", {}).get("steel_plated"):
                    return mod.gate_url(url)
        except Exception:
            pass
    u = str(url or "").strip()
    if not u:
        return {"ok": True, "gone": False, "url": u}
    h = _host(u)
    if not h:
        return {"ok": False, "gone": True, "error": "bad_url", "url": u}
    allow = {str(a).lower() for a in doctrine().get("canonical_allow") or []}
    if h in allow or any(h.endswith("." + a) for a in allow):
        return {"ok": True, "gone": False, "url": u, "host": h, "allowed": True}
    if h in gone_hosts():
        return {"ok": False, "gone": True, "url": u, "host": h, "reason": "gone_host"}
    for pat in _gone_patterns():
        if pat.search(u):
            return {"ok": False, "gone": True, "url": u, "host": h, "reason": "gone_pattern"}
    return {"ok": True, "gone": False, "url": u, "host": h}


def gate_url(url: str) -> dict[str, Any]:
    v = is_gone(url)
    if v.get("gone"):
        _append_ledger({"event": "block", **v})
    return v


def _strip_urls_in_text(text: str) -> tuple[str, list[str]]:
    marker = str(doctrine().get("gone_marker") or "[gone]")
    killed: list[str] = []

    def repl(m: re.Match[str]) -> str:
        url = m.group(0)
        if is_gone(url).get("gone"):
            killed.append(url)
            return marker
        return url

    return URL_RE.sub(repl, text or ""), killed


def _purge_obj(obj: Any) -> tuple[Any, list[str]]:
    killed: list[str] = []
    if isinstance(obj, str):
        new, k = _strip_urls_in_text(obj)
        killed.extend(k)
        return new, killed
    if isinstance(obj, list):
        out: list[Any] = []
        for item in obj:
            fixed, k = _purge_obj(item)
            killed.extend(k)
            out.append(fixed)
        return out, killed
    if isinstance(obj, dict):
        out_d: dict[str, Any] = {}
        for key, val in obj.items():
            if key in ("url", "href", "link", "destination", "location", "canonical_url") and isinstance(val, str):
                if is_gone(val).get("gone"):
                    killed.append(val)
                    continue
            fixed, k = _purge_obj(val)
            killed.extend(k)
            out_d[key] = fixed
        return out_d, killed
    return obj, killed


def write_blocklist() -> dict[str, Any]:
    hosts = sorted(gone_hosts())
    BLOCKLIST.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"||{h}^" for h in hosts]
    BLOCKLIST.write_text("\n".join(lines) + "\n", encoding="utf-8")
    legacy = STATE / "adblock" / "domains-block.txt"
    try:
        existing: set[str] = set()
        if legacy.is_file():
            for line in legacy.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    existing.add(line)
        for line in lines:
            existing.add(line)
        legacy.write_text("\n".join(sorted(existing)) + "\n", encoding="utf-8")
    except OSError:
        pass
    return {"ok": True, "hosts": len(hosts), "blocklist": str(BLOCKLIST)}


def purge_caches() -> dict[str, Any]:
    paths = [
        STATE / "operator-x-comments-cache.json",
        STATE / "operator-google-youtube-cache.json",
        STATE / "operator-tco-kill-cache.json",
        STATE / "operator-whole-internet-cache.json",
        STATE / "hostess7-censorship-exposure-panel.json",
    ]
    total_killed: list[str] = []
    files: list[str] = []
    for path in paths:
        if not path.is_file():
            continue
        doc = _load(path, {})
        if not doc:
            continue
        fixed, killed = _purge_obj(doc)
        if killed:
            _save(path, fixed if isinstance(fixed, dict) else {"data": fixed})
            total_killed.extend(killed)
            files.append(str(path))
    return {"ok": True, "files": files, "urls_gone": len(total_killed), "samples": total_killed[:16]}


def kill_all() -> dict[str, Any]:
    block = write_blocklist()
    purge = purge_caches()
    tco: dict[str, Any] = {"skipped": True}
    py = INSTALL / "lib" / "hostess7-tco-kill.py"
    if py.is_file():
        try:
            spec = importlib.util.spec_from_file_location("tco_kill", py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "open_and_kill"):
                    tco = mod.open_and_kill()
        except Exception as exc:
            tco = {"ok": False, "error": str(exc)[:120]}
    out = {
        "ok": True,
        "schema": "hostess7-url-kill/v1",
        "updated": _now(),
        "motto": doctrine().get("motto"),
        "gone_not_control": True,
        "gone_hosts": len(gone_hosts()),
        "blocklist": block,
        "purge": purge,
        "tco": {"tco_unwrapped": tco.get("tco_unwrapped")},
        "api": doctrine().get("api") or "/api/operator-url-kill",
    }
    _save(PANEL, out)
    _save(REGISTRY, {"updated": _now(), "hosts": sorted(gone_hosts()), "gone": True})
    _append_ledger({"event": "kill_all", "urls_gone": purge.get("urls_gone"), "hosts": out["gone_hosts"]})
    return out


def panel_json() -> dict[str, Any]:
    cached = _load(PANEL, {})
    if cached.get("schema"):
        return cached
    return {
        "ok": True,
        "schema": "hostess7-url-kill-panel/v1",
        "gone_hosts": len(gone_hosts()),
        "pending": "run kill",
        "motto": doctrine().get("motto"),
        "api": "/api/operator-url-kill",
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("kill", "gone", "run", "purge"):
        print(json.dumps(kill_all(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "check" and len(sys.argv) > 2:
        print(json.dumps(gate_url(" ".join(sys.argv[2:])), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("json", "panel", "status"):
        print(json.dumps(panel_json(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "hosts":
        print(json.dumps({"hosts": sorted(gone_hosts())}, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "hostess7-url-kill.py [kill|check URL|json|hosts]",
        "motto": doctrine().get("motto"),
    }, ensure_ascii=False, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())