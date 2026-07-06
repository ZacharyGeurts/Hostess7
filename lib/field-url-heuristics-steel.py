#!/usr/bin/env python3
"""URL heuristics — derive from field data, steel plate, meld into server."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
DOCTRINE = INSTALL / "data" / "field-url-heuristics-doctrine.json"
ANNOYANCE = INSTALL / "data" / "annoyance-complaints.tsv"
HONOR = INSTALL / "data" / "honorability-seed.json"
X_PURGE = INSTALL / "data" / "hostess7-x-brand-purge-doctrine.json"
URL_KILL_DOC = INSTALL / "data" / "hostess7-url-kill-doctrine.json"
TCO_DOC = INSTALL / "data" / "hostess7-tco-kill-doctrine.json"
TRUTH_DOC = INSTALL / "data" / "hostess7-truth-lie-threat-doctrine.json"


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
PLATE = STATE / "field-url-heuristics-steel-plate.json"
PANEL = STATE / "field-url-heuristics-panel.json"
LEDGER = STATE / "field-url-heuristics-ledger.jsonl"
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
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append_ledger(row: dict[str, Any]) -> None:
    try:
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": _now(), **row}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _fingerprint(path: Path) -> str:
    if not path.is_file():
        return "missing"
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    except OSError:
        return "error"


def doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {})


def _host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower().strip()
    except Exception:
        return ""


def derive_heuristics() -> dict[str, Any]:
    """Build heuristics + why from every witnessed data source."""
    doc = doctrine()
    thr = doc.get("thresholds") or {}
    annoy_min = int(thr.get("annoyance_gone_min") or 8)
    honor_gone_max = int(thr.get("honor_gone_max_stars") or 1)
    honor_allow_min = int(thr.get("honor_allow_min_stars") or 5)

    rules: list[dict[str, Any]] = []
    gone_hosts: set[str] = set()
    allow_hosts: set[str] = set()
    patterns: list[dict[str, Any]] = []
    sources_fp: dict[str, str] = {}

    for rel in doc.get("derive_from") or []:
        p = INSTALL / rel if not str(rel).startswith("state/") else STATE / str(rel).replace("state/", "")
        sources_fp[str(rel)] = _fingerprint(p)

    if ANNOYANCE.is_file():
        for line in ANNOYANCE.read_text(encoding="utf-8", errors="replace").splitlines()[1:]:
            parts = line.split("\t")
            if len(parts) < 4:
                continue
            dom, cat, score_s, reason = parts[0].lower(), parts[1], parts[2], parts[3]
            try:
                score = int(score_s)
            except ValueError:
                score = 0
            if score >= annoy_min or cat in ("lockout", "popup", "popunder"):
                gone_hosts.add(dom)
                rules.append({
                    "id": f"annoyance_{dom.replace('.', '_')}",
                    "action": "gone",
                    "host": dom,
                    "category": cat,
                    "complaint_score": score,
                    "confidence": min(0.99, 0.7 + score * 0.03),
                    "sources": ["annoyance-complaints.tsv"],
                    "why": f"Complaint score {score}/10 — {reason}",
                })

    honor_doc = _load(HONOR, {"entries": []})
    for entry in honor_doc.get("entries") or []:
        dom = str(entry.get("domain") or "").lower()
        if not dom:
            continue
        stars = int(entry.get("stars") or 3)
        note = str(entry.get("note") or "")
        cat = str(entry.get("category") or "")
        if stars <= honor_gone_max:
            gone_hosts.add(dom)
            rules.append({
                "id": f"honor_gone_{dom.replace('.', '_')}",
                "action": "gone",
                "host": dom,
                "honor_stars": stars,
                "category": cat,
                "confidence": 0.95,
                "sources": ["honorability-seed.json"],
                "why": f"Honor {stars}★ — {note or 'dangerous legacy'}",
            })
        elif stars >= honor_allow_min:
            allow_hosts.add(dom)
            rules.append({
                "id": f"honor_allow_{dom.replace('.', '_')}",
                "action": "allow",
                "host": dom,
                "honor_stars": stars,
                "category": cat,
                "confidence": 0.92,
                "sources": ["honorability-seed.json"],
                "why": f"Honor {stars}★ operator lane — {note}",
            })

    xp = _load(X_PURGE, {})
    for row in xp.get("dangerous_blow") or []:
        host = str(row.get("host") or "").lower()
        action = str(row.get("action") or "gone")
        if not host:
            continue
        if action in ("block", "drop_lane", "unwrap_kill"):
            gone_hosts.add(host)
            rules.append({
                "id": f"x_purge_{host.replace('.', '_')}",
                "action": "gone" if action != "unwrap_kill" else "unwrap_kill",
                "host": host,
                "confidence": 0.96,
                "sources": ["hostess7-x-brand-purge-doctrine.json"],
                "why": str(row.get("reason") or "X brand purge — dangerous"),
            })
        elif action == "redirect_canonical":
            rules.append({
                "id": f"x_legacy_{host.replace('.', '_')}",
                "action": "redirect",
                "host": host,
                "canonical": "x.com",
                "confidence": 0.88,
                "sources": ["hostess7-x-brand-purge-doctrine.json"],
                "why": str(row.get("reason") or "Legacy redirect — X canonical"),
            })

    uk = _load(URL_KILL_DOC, {})
    for host in uk.get("gone_hosts") or []:
        h = str(host).lower()
        gone_hosts.add(h)
    for pat in uk.get("gone_patterns") or []:
        patterns.append({
            "pattern": pat,
            "action": "gone",
            "sources": ["hostess7-url-kill-doctrine.json"],
            "why": "Doctrine pattern — dangerous URL shape",
        })

    for host in _load(TCO_DOC, {}).get("hosts") or ["t.co"]:
        h = str(host).lower()
        gone_hosts.add(h)
        rules.append({
            "id": "tco_delay_threat",
            "action": "unwrap_kill",
            "host": h,
            "confidence": 0.97,
            "sources": ["hostess7-tco-kill-doctrine.json", "truth-lie-threat"],
            "why": "Click tracker middleman — delay-as-threat; unwrap then gone",
        })

    delay_sigs = (_load(TRUTH_DOC, {}).get("delay_as_threat") or {}).get("signals") or []
    for sig in delay_sigs:
        if "t_co" in str(sig) or "tco" in str(sig):
            patterns.append({
                "pattern": r"://t\.co/",
                "action": "unwrap_kill",
                "signal": sig,
                "why": "Witnessed delay-as-threat signal",
            })

    ledger_path = STATE / "hostess7-url-kill-ledger.jsonl"
    if ledger_path.is_file():
        try:
            for line in ledger_path.read_text(encoding="utf-8", errors="replace").splitlines()[-200:]:
                row = json.loads(line)
                url = str(row.get("url") or "")
                if row.get("gone") and url:
                    h = _host(url)
                    if h:
                        gone_hosts.add(h)
        except (json.JSONDecodeError, OSError):
            pass

    for host in uk.get("canonical_allow") or []:
        allow_hosts.add(str(host).lower())

    pipe_pat = r"curl\s+[^\s|]+\s*\|\s*(ba)?sh"
    patterns.append({
        "pattern": pipe_pat,
        "action": "gone",
        "why": "Pipe-to-shell — queen-root-sovereign CRITICAL pattern",
        "sources": ["queen-root-sovereign", "field-ai-root-api-guard"],
    })

    seen_ids: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for r in rules:
        rid = str(r.get("id") or "")
        if rid in seen_ids:
            continue
        seen_ids.add(rid)
        deduped.append(r)

    why_meld = doc.get("why_meld") or {}
    return {
        "schema": "field-url-heuristics-derived/v1",
        "updated": _now(),
        "rules": deduped,
        "gone_hosts": sorted(gone_hosts),
        "allow_hosts": sorted(allow_hosts),
        "patterns": patterns,
        "counts": {
            "rules": len(deduped),
            "gone_hosts": len(gone_hosts),
            "allow_hosts": len(allow_hosts),
            "patterns": len(patterns),
        },
        "source_fingerprints": sources_fp,
        "why_meld": why_meld,
        "thresholds": thr,
    }


def steel_plate(*, derived: dict[str, Any] | None = None) -> dict[str, Any]:
    """Hash and seal heuristics — immutable server plate."""
    body = dict(derived or derive_heuristics())
    pre = {k: v for k, v in body.items() if k not in ("chain_hash", "generation", "steel_plated")}
    chain = hashlib.sha256(json.dumps(pre, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    prev = _load(PLATE, {})
    gen = int(prev.get("generation") or 0) + 1
    plate = {
        **body,
        "schema": (doctrine().get("steel_plate") or {}).get("schema") or "field-url-heuristics-steel/v1",
        "steel_plated": True,
        "generation": gen,
        "chain_hash": chain,
        "prev_chain_hash": prev.get("chain_hash"),
        "ironclad_citation": (doctrine().get("steel_plate") or {}).get("ironclad_citation"),
        "motto": doctrine().get("motto"),
        "fail_closed": True,
        "gone_not_control": True,
    }
    _save(PLATE, plate)
    _save(PANEL, {
        "ok": True,
        "schema": "field-url-heuristics-panel/v1",
        "updated": _now(),
        "generation": gen,
        "chain_hash": chain,
        "counts": plate.get("counts"),
        "why_summary": (plate.get("why_meld") or {}).get("summary"),
        "api": doctrine().get("api"),
    })
    _append_ledger({"event": "steel_plate", "generation": gen, "chain_hash": chain})
    return plate


def read_plate() -> dict[str, Any]:
    doc = _load(PLATE, {})
    if doc.get("steel_plated"):
        return doc
    return steel_plate()


def plate_gone_hosts() -> frozenset[str]:
    return frozenset(str(h).lower() for h in read_plate().get("gone_hosts") or [])


def plate_allow_hosts() -> frozenset[str]:
    return frozenset(str(h).lower() for h in read_plate().get("allow_hosts") or [])


def plate_patterns() -> list[re.Pattern[str]]:
    out: list[re.Pattern[str]] = []
    for row in read_plate().get("patterns") or []:
        pat = str(row.get("pattern") or "")
        if not pat:
            continue
        try:
            out.append(re.compile(pat, re.I))
        except re.error:
            continue
    return out


def gate_url(url: str) -> dict[str, Any]:
    """Fail-closed gate — melded steel plate is authoritative."""
    u = str(url or "").strip()
    h = _host(u)
    if not u or not h:
        return {"ok": False, "gone": True, "error": "bad_url", "steel_plated": True}
    allow = plate_allow_hosts()
    if h in allow or any(h.endswith("." + a) for a in allow):
        return {"ok": True, "gone": False, "url": u, "host": h, "allowed": True, "steel_plated": True}
    if h in plate_gone_hosts():
        return {"ok": False, "gone": True, "url": u, "host": h, "reason": "steel_plate_gone_host", "steel_plated": True}
    for pat in plate_patterns():
        if pat.search(u):
            return {"ok": False, "gone": True, "url": u, "host": h, "reason": "steel_plate_pattern", "steel_plated": True}
    return {"ok": True, "gone": False, "url": u, "host": h, "steel_plated": True}


def _sync_url_kill_blocklist() -> dict[str, Any]:
    py = INSTALL / "lib" / "hostess7-url-kill.py"
    if not py.is_file():
        return {"skipped": "url_kill_missing"}
    try:
        spec = importlib.util.spec_from_file_location("url_kill_sync", py)
        if not spec or not spec.loader:
            return {"skipped": "load"}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "write_blocklist"):
            hosts = sorted(plate_gone_hosts())
            return mod.write_blocklist() if hosts else {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:160]}
    return {"skipped": "write_blocklist"}


def _meld_plate_cycle() -> dict[str, Any]:
    py = INSTALL / "lib" / "field-plate-meld.py"
    if not py.is_file():
        return {"skipped": "plate_meld_missing"}
    env = {**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)}
    try:
        proc = subprocess.run(
            [sys.executable, str(py), "fuse"],
            capture_output=True,
            text=True,
            timeout=90,
            env=env,
        )
        try:
            out = json.loads(proc.stdout or "{}")
        except json.JSONDecodeError:
            out = {"ok": proc.returncode == 0, "raw": (proc.stdout or proc.stderr or "")[:300]}
        return {"ok": proc.returncode == 0, "fuse": out}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": str(exc)[:160]}


def meld_into_server() -> dict[str, Any]:
    """Derive → steel plate → blocklist → plate meld fuse — one server truth."""
    derived = derive_heuristics()
    plate = steel_plate(derived=derived)
    block = _sync_url_kill_blocklist()
    meld = _meld_plate_cycle()
    url_kill: dict[str, Any] = {"skipped": True}
    kill_py = INSTALL / "lib" / "hostess7-url-kill.py"
    if kill_py.is_file():
        try:
            proc = subprocess.run(
                [sys.executable, str(kill_py), "kill"],
                capture_output=True,
                text=True,
                timeout=60,
                env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
            )
            url_kill = json.loads(proc.stdout or "{}")
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
            pass
    out = {
        "ok": True,
        "schema": "field-url-heuristics-meld/v1",
        "updated": _now(),
        "steel_plated": True,
        "generation": plate.get("generation"),
        "chain_hash": plate.get("chain_hash"),
        "counts": plate.get("counts"),
        "why_summary": (plate.get("why_meld") or {}).get("summary"),
        "why_reasons": (plate.get("why_meld") or {}).get("reasons"),
        "blocklist": block,
        "plate_meld": meld,
        "url_kill": {"urls_gone": (url_kill.get("purge") or {}).get("urls_gone")},
        "api": doctrine().get("api"),
    }
    _append_ledger({"event": "meld_into_server", "chain_hash": plate.get("chain_hash")})
    return out


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("derive", "heuristics"):
        print(json.dumps(derive_heuristics(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("steel", "steel-plate", "plate"):
        print(json.dumps(steel_plate(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("meld", "run", "fuse-server"):
        print(json.dumps(meld_into_server(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "why":
        print(json.dumps(doctrine().get("why_meld") or {}, ensure_ascii=False, indent=2))
        return 0
    if cmd == "gate" and len(sys.argv) > 2:
        print(json.dumps(gate_url(" ".join(sys.argv[2:])), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("json", "panel", "status"):
        doc = _load(PANEL, {})
        if not doc.get("schema"):
            doc = {"ok": True, "pending": "meld", "why": "run meld"}
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "field-url-heuristics-steel.py [derive|steel|meld|why|gate URL|json]",
        "motto": doctrine().get("motto"),
    }, ensure_ascii=False, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())