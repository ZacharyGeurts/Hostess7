#!/usr/bin/env pythong
"""Truth ID — prioritized human registry. Internet connections tie to people; identity sticks once known.

No census required: field learns humans from live connections, dossiers, gov intel, and operator anchor.
Biological lifeforms (human, pet) get persistent truth_id; merge-only after id_locked.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
REGISTRY_JSON = STATE / "human-registry.json"
REGISTRY_LEDGER = STATE / "human-registry.jsonl"
PANEL_CACHE = STATE / "human-registry-panel.json"
SCHOOLS_USER = STATE / "schools-verified.json"
IPV4_RE = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")
LOCK_THRESHOLD = 0.85

TAG_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("FBI", re.compile(r"\bfbi\b", re.I)),
    ("CIA", re.compile(r"\bcia\b", re.I)),
    ("NSA", re.compile(r"\bnsa\b", re.I)),
    ("DHS", re.compile(r"\bdhs\b|homeland\s+security", re.I)),
    ("Federal", re.compile(r"\bfederal\b|\bu\.?s\.?\s+gov", re.I)),
    ("Deputy", re.compile(r"\bdeputy\b", re.I)),
    ("Sheriff", re.compile(r"\bsheriff\b", re.I)),
    ("Secretary", re.compile(r"\bsecretary\b", re.I)),
    ("Director", re.compile(r"\bdirector\b", re.I)),
    ("Agent", re.compile(r"\bagent\b", re.I)),
    ("Officer", re.compile(r"\bofficer\b", re.I)),
    ("Military", re.compile(r"\bmilitary\b|\barmy\b|\bnavy\b|\busaf\b|\bmarines\b", re.I)),
    ("Veteran", re.compile(r"\bveteran\b", re.I)),
]
PET_RE = re.compile(r"\b(pet|dog|cat|puppy|kitten|collar|tracker)\b", re.I)
BUSINESS_DOMAIN_RE = re.compile(
    r"\.(corp|inc|llc|gov|mil|edu|agency|consulting|solutions|cloud|hosting)\b", re.I,
)
CONSUMER_HOSTS = frozenset({
    "google.com", "youtube.com", "x.com", "twitter.com", "facebook.com", "instagram.com",
    "amazon.com", "netflix.com", "reddit.com", "wikipedia.org", "github.com",
})


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


def _append_ledger(row: dict[str, Any]) -> None:
    try:
        REGISTRY_LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with REGISTRY_LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _merge_value(existing: Any, new: Any) -> Any:
    if new is None:
        return existing
    if isinstance(new, str) and not new.strip():
        return existing
    if isinstance(new, dict):
        base = dict(existing) if isinstance(existing, dict) else {}
        for k, v in new.items():
            if k in base:
                base[k] = _merge_value(base[k], v)
            else:
                base[k] = v
        return base
    if isinstance(new, list):
        old = list(existing) if isinstance(existing, list) else []
        seen = {json.dumps(x, sort_keys=True, default=str) for x in old}
        for item in new:
            key = json.dumps(item, sort_keys=True, default=str)
            if key not in seen:
                old.append(item)
                seen.add(key)
        return old
    return new


def _truth_id(markers: dict[str, Any]) -> str:
    blob = json.dumps(markers, sort_keys=True, default=str).encode("utf-8")
    return "truth_" + hashlib.sha256(blob).hexdigest()[:24]


def _provisional_id(seed: str) -> str:
    return "truth_prov_" + hashlib.sha256(seed.encode()).hexdigest()[:20]


def _load_schools() -> list[dict[str, Any]]:
    user = _load_json(SCHOOLS_USER, {"schools": []})
    seed = _load_json(INSTALL / "data" / "schools-verified-seed.json", {"schools": []})
    by_id: dict[str, dict[str, Any]] = {}
    for row in (seed.get("schools") or []) + (user.get("schools") or []):
        if isinstance(row, dict) and row.get("id"):
            by_id[str(row["id"])] = row
    return list(by_id.values())


def _match_schools(text: str, schools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not text:
        return []
    text_l = text.lower()
    hits: list[dict[str, Any]] = []
    for sch in schools:
        names = [str(sch.get("name") or "")]
        names.extend(str(a) for a in (sch.get("aliases") or []))
        for name in names:
            if name and name.lower() in text_l:
                hits.append({
                    "school_id": sch.get("id"),
                    "school_name": sch.get("name"),
                    "verified": bool(sch.get("verified", True)),
                    "matched_on": name,
                })
                break
    return hits


def _infer_tags(*texts: str) -> list[str]:
    blob = " ".join(t for t in texts if t)
    found: list[str] = []
    for label, pat in TAG_PATTERNS:
        if pat.search(blob):
            found.append(label)
    return list(dict.fromkeys(found))


def _infer_skills(tags: list[str], text: str) -> list[str]:
    seeds = _load_json(INSTALL / "data" / "human-registry-tags.json", {}).get("skill_seeds") or []
    skills: list[str] = []
    text_l = text.lower()
    if any(t in tags for t in ("FBI", "CIA", "NSA", "Federal", "Agent", "Officer")):
        skills.append("intelligence")
    if any(t in tags for t in ("Military", "Veteran")):
        skills.append("field_operations")
    if "security" in text_l or "c2" in text_l or "malware" in text_l:
        skills.append("security")
    if "network" in text_l or "asn" in text_l:
        skills.append("networking")
    for s in seeds:
        if s.lower() in text_l and s not in skills:
            skills.append(s)
    return list(dict.fromkeys(skills))[:12]


def _classify_link(ip: str, host: str, process: str, row: dict[str, Any], adversary_ips: set[str]) -> str:
    if ip in adversary_ips:
        return "adversary"
    host_l = (host or "").lower()
    proc_l = (process or "").lower()
    if row.get("category_hint") == "operator":
        return "personal"
    if BUSINESS_DOMAIN_RE.search(host_l) or host_l.endswith(".gov") or host_l.endswith(".mil"):
        return "business"
    if any(h in host_l for h in CONSUMER_HOSTS) or proc_l in ("firefox", "chrome", "thunderbird", "brave"):
        return "personal"
    if row.get("verdict") in ("HARM_CANDIDATE", "SUSPICIOUS") or row.get("kill_eligible"):
        return "adversary"
    org = str(row.get("asn_org") or row.get("org") or "")
    if any(x in org.lower() for x in ("inc", "corp", "llc", "hosting", "cloud", "datacenter")):
        return "business"
    return "personal"


def _lifeform_from_text(text: str) -> str:
    if PET_RE.search(text):
        return "pet"
    return "human"


def _confidence_score(row: dict[str, Any]) -> float:
    score = 0.25
    if row.get("display_name") and not str(row.get("display_name", "")).startswith("Unknown"):
        score += 0.2
    if row.get("internet_ties"):
        score += min(0.25, len(row["internet_ties"]) * 0.04)
    if row.get("tags"):
        score += min(0.15, len(row["tags"]) * 0.03)
    if row.get("schooling"):
        score += 0.1
    if row.get("gov_intel") or row.get("gov_agency_id"):
        score += 0.15
    if row.get("category_primary") == "operator":
        score = max(score, 0.92)
    if row.get("category_primary") == "adversary" and row.get("associated_malware"):
        score = max(score, 0.88)
    return round(min(1.0, score), 3)


def _blank_human(
    truth_id: str,
    *,
    display_name: str = "Unknown",
    lifeform: str = "human",
    category: str = "unknown",
) -> dict[str, Any]:
    return {
        "truth_id": truth_id,
        "display_name": display_name,
        "lifeform": lifeform,
        "category_primary": category,
        "id_locked": False,
        "confidence": 0.0,
        "tags": [],
        "skills": [],
        "schooling": [],
        "internet_ties": [],
        "business_affiliations": [],
        "personal_markers": [],
        "ip_bindings": [],
        "first_seen": _now(),
        "last_seen": _now(),
        "sightings": 0,
        "truth_attempts": 0,
    }


def _tie_row(
    ip: str,
    link: str,
    source: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row = {
        "ip": ip,
        "link": link,
        "source": source,
        "last_seen": _now(),
    }
    if extra:
        row.update({k: v for k, v in extra.items() if v is not None})
    return row


def _merge_human(prev: dict[str, Any] | None, patch: dict[str, Any]) -> dict[str, Any]:
    if not prev:
        return dict(patch)
    locked = bool(prev.get("id_locked"))
    out = dict(prev)
    sticky = {"truth_id", "id_locked", "first_seen"}
    if locked:
        sticky.add("display_name")
        sticky.add("lifeform")
        sticky.add("category_primary")
    for k, v in patch.items():
        if k in sticky:
            continue
        if k == "internet_ties":
            out[k] = _merge_value(prev.get(k) or [], v or [])
        elif k in ("tags", "skills", "schooling", "business_affiliations", "personal_markers", "ip_bindings"):
            out[k] = _merge_value(prev.get(k) or [], v or [])
        else:
            out[k] = _merge_value(prev.get(k), v)
    out["truth_id"] = prev["truth_id"]
    out["id_locked"] = prev.get("id_locked", False)
    out["first_seen"] = prev.get("first_seen") or patch.get("first_seen")
    out["sightings"] = int(prev.get("sightings") or 0) + 1
    out["last_seen"] = _now()
    out["truth_attempts"] = int(prev.get("truth_attempts") or 0) + 1
    out["confidence"] = _confidence_score(out)
    if not out["id_locked"] and out["confidence"] >= LOCK_THRESHOLD:
        out["id_locked"] = True
        _append_ledger({
            "ts": _now(),
            "event": "truth_id_locked",
            "truth_id": out["truth_id"],
            "display_name": out.get("display_name"),
            "confidence": out["confidence"],
        })
    return out


def _panel_doc() -> dict[str, Any]:
    panel = _load_json(STATE / "threat-panel.json", {})
    if not panel.get("panel_ready"):
        panel = _load_json(PANEL_CACHE, {}) or panel
    return panel


def _harvest_connections(panel: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for conn in (panel.get("gatekeeper") or {}).get("connections") or []:
        if not isinstance(conn, dict):
            continue
        ip = str(conn.get("remote_ip") or "").strip()
        if not ip or not IPV4_RE.match(ip):
            continue
        rows.append({
            "ip": ip,
            "port": conn.get("remote_port"),
            "process": conn.get("process"),
            "host": conn.get("honor_host") or conn.get("site_host") or conn.get("intel_host"),
            "verdict": conn.get("verdict"),
            "kill_eligible": conn.get("kill_eligible"),
            "asn_org": conn.get("asn_org") or conn.get("org"),
            "source": "gatekeeper",
        })
    pf = panel.get("packet_field") or {}
    for pkt in pf.get("connections") or pf.get("recent") or []:
        if not isinstance(pkt, dict):
            continue
        ip = str(pkt.get("dst_ip") or pkt.get("remote_ip") or "").strip()
        if not ip or not IPV4_RE.match(ip):
            continue
        rows.append({
            "ip": ip,
            "port": pkt.get("dst_port") or pkt.get("remote_port"),
            "process": pkt.get("process"),
            "host": pkt.get("dst_host") or pkt.get("host"),
            "source": "packet_field",
        })
    for site in (panel.get("browser_awareness") or {}).get("active_sites") or []:
        if not isinstance(site, dict):
            continue
        host = str(site.get("host") or "").strip()
        if host:
            rows.append({
                "ip": None,
                "host": host,
                "process": site.get("process"),
                "source": "browser_awareness",
                "category_hint": "operator",
            })
    return rows


def build_human_registry(panel: dict[str, Any] | None = None) -> dict[str, Any]:
    panel = panel or _panel_doc()
    prev = _load_json(REGISTRY_JSON, {"humans": {}, "ip_index": {}, "updated": None})
    humans: dict[str, dict[str, Any]] = dict(prev.get("humans") or {})
    ip_index: dict[str, str] = dict(prev.get("ip_index") or {})
    schools = _load_schools()

    adversary_ips = {
        str(r.get("ip")) for r in (panel.get("human_dossier") or {}).get("ips") or []
        if r.get("ip")
    }
    hd_by_ip = {
        str(r.get("ip")): r for r in (panel.get("human_dossier") or {}).get("ips") or [] if r.get("ip")
    }

    # Operator anchor — highest priority, locked
    op = _load_json(STATE / "operator-location.json", {})
    if op.get("lat") is not None:
        op_id = _truth_id({"role": "operator", "label": op.get("label") or "operator"})
        op_human = humans.get(op_id) or _blank_human(
            op_id, display_name=op.get("label") or "Operator", category="operator",
        )
        op_human = _merge_human(op_human, {
            "display_name": op.get("label") or "Operator",
            "lifeform": "human",
            "category_primary": "operator",
            "id_locked": True,
            "confidence": 0.95,
            "personal_markers": [op.get("source") or "operator-location"],
            "tags": list(dict.fromkeys(op_human.get("tags") or [] + ["Operator"])),
        })
        humans[op_id] = op_human

    # Internet connections → humans
    for conn in _harvest_connections(panel):
        ip = conn.get("ip")
        host = str(conn.get("host") or "")
        process = str(conn.get("process") or "")
        link = _classify_link(str(ip or host), host, process, conn, adversary_ips)

        if ip and ip in ip_index and ip_index[ip] in humans:
            tid = ip_index[ip]
        elif ip and ip in hd_by_ip:
            hd = hd_by_ip[ip]
            markers = {"ip": ip, "malware": hd.get("associated_malware"), "role": "adversary"}
            tid = _truth_id(markers) if hd.get("associated_malware") else _provisional_id(f"ip:{ip}")
        elif host and link == "personal" and conn.get("category_hint") == "operator":
            tid = op_id if op.get("lat") is not None else _provisional_id(f"host:{host}")
        elif ip:
            tid = _provisional_id(f"ip:{ip}")
        elif host:
            tid = _provisional_id(f"host:{host}")
        else:
            continue

        h = humans.get(tid) or _blank_human(tid)
        text_blob = " ".join(filter(None, [
            host, process, conn.get("asn_org"), str(hd_by_ip.get(ip or "", {}).get("notes", "")),
        ]))
        tags = _infer_tags(text_blob, str(hd_by_ip.get(ip or "", {}).get("notes", "")))
        schooling = _match_schools(text_blob, schools)
        skills = _infer_skills(tags, text_blob)
        category = "adversary" if link == "adversary" else (
            "operator" if conn.get("category_hint") == "operator" else
            "business_contact" if link == "business" else
            "personal_contact" if link == "personal" else "unknown"
        )
        lifeform = _lifeform_from_text(text_blob)
        display = h.get("display_name") or "Unknown"
        if ip and ip in hd_by_ip:
            hd = hd_by_ip[ip]
            display = f"{hd.get('associated_malware') or 'Threat'} @ {ip}"
            category = "adversary"
        elif host and display == "Unknown":
            display = host
        elif ip and conn.get("asn_org") and display == "Unknown":
            display = f"{conn.get('asn_org')} · {ip}"
        elif ip and display == "Unknown":
            display = f"Remote · {ip}"

        patch: dict[str, Any] = {
            "display_name": display,
            "lifeform": lifeform,
            "category_primary": category,
            "tags": tags,
            "skills": skills,
            "schooling": schooling,
        }
        if ip:
            patch["internet_ties"] = [_tie_row(ip, link, conn.get("source") or "field", {
                "host": host or None,
                "process": process or None,
                "port": conn.get("port"),
                "verdict": conn.get("verdict"),
            })]
            patch["ip_bindings"] = [ip]
            if conn.get("asn_org"):
                patch["business_affiliations"] = [str(conn.get("asn_org"))]
        if host and link == "personal":
            patch["personal_markers"] = [host]
        if ip and ip in hd_by_ip:
            hd = hd_by_ip[ip]
            patch.update({
                "associated_malware": hd.get("associated_malware"),
                "hosting_likelihood": hd.get("hosting_likelihood"),
                "geo": hd.get("geo"),
                "asn_org": hd.get("asn_org"),
                "adversary_dossier": True,
                "notes": hd.get("notes"),
            })
            patch["tags"] = list(dict.fromkeys((patch.get("tags") or []) + ["adversary", "C2"]))

        merged = _merge_human(h, patch)
        humans[tid] = merged
        if ip:
            ip_index[ip] = tid

    # Gov dossiers with names → humans
    gov = _load_json(STATE / "gov-dossiers.json", {"records": {}})
    for rec in (gov.get("records") or {}).values():
        if not isinstance(rec, dict):
            continue
        name = str(rec.get("name") or rec.get("full_name") or "").strip()
        ip = None
        for field in ("ip", "IP", "remote_ip"):
            val = str(rec.get(field) or "").strip()
            if val and IPV4_RE.match(val):
                ip = val
                break
        if not name and not ip:
            continue
        markers = {"name": name or ip, "agency": rec.get("agency_id") or rec.get("agency")}
        tid = _truth_id(markers) if name else _provisional_id(f"gov:{ip}")
        text = json.dumps(rec, default=str)
        tags = _infer_tags(text, str(rec.get("title") or ""), str(rec.get("role") or ""))
        schooling = _match_schools(text, schools)
        h = humans.get(tid) or _blank_human(tid, display_name=name or f"Gov record · {ip}")
        patch = {
            "display_name": name or h.get("display_name"),
            "category_primary": "business_contact",
            "gov_intel": True,
            "gov_agency_id": rec.get("agency_id"),
            "tags": tags,
            "skills": _infer_skills(tags, text),
            "schooling": schooling,
        }
        if ip:
            patch["internet_ties"] = [_tie_row(ip, "business", "gov_dossiers", {"agency": rec.get("agency_id")})]
            patch["ip_bindings"] = [ip]
            ip_index[ip] = tid
        humans[tid] = _merge_human(h, patch)

    # Human dossier IPs without connection this cycle
    for ip, hd in hd_by_ip.items():
        if ip in ip_index:
            continue
        tid = _truth_id({"ip": ip, "malware": hd.get("associated_malware")}) if hd.get("associated_malware") else _provisional_id(f"ip:{ip}")
        text = str(hd.get("notes") or "") + " " + str(hd.get("asn_org") or "")
        h = humans.get(tid) or _blank_human(
            tid,
            display_name=f"{hd.get('associated_malware') or 'Threat'} @ {ip}",
            category="adversary",
        )
        patch = {
            "adversary_dossier": True,
            "associated_malware": hd.get("associated_malware"),
            "asn_org": hd.get("asn_org"),
            "geo": hd.get("geo"),
            "notes": hd.get("notes"),
            "tags": _infer_tags(text) + ["adversary", "C2"],
            "skills": _infer_skills([], text),
            "schooling": _match_schools(text, schools),
            "internet_ties": [_tie_row(ip, "adversary", "human_dossier")],
            "ip_bindings": [ip],
        }
        humans[tid] = _merge_human(h, patch)
        ip_index[ip] = tid

    try:
        touch_mod = importlib.util.spec_from_file_location(
            "safe_signal_touch", INSTALL / "lib" / "safe-signal-touch.py",
        )
        st = importlib.util.module_from_spec(touch_mod)
        assert touch_mod and touch_mod.loader
        touch_mod.loader.exec_module(st)
        for tid, row in humans.items():
            lf = str(row.get("lifeform") or "human")
            touch = st.lifeform_touch(lf)
            if touch == "none" and lf == "human":
                felt = st.felt_safe_kind(
                    text=" ".join(filter(None, [
                        row.get("display_name"), row.get("notes"),
                        " ".join(str(x) for x in (row.get("personal_markers") or [])),
                    ])),
                )
                touch = felt or "none"
            row.update(st.touch_fields(touch, safe_signal=touch != "alert"))
    except Exception:
        pass

    table = sorted(
        humans.values(),
        key=lambda r: (
            0 if r.get("category_primary") == "operator" else 1,
            0 if r.get("id_locked") else 1,
            -float(r.get("confidence") or 0),
            -int(r.get("sightings") or 0),
        ),
    )
    stats = {
        "total": len(table),
        "locked": sum(1 for r in table if r.get("id_locked")),
        "humans": sum(1 for r in table if r.get("lifeform") == "human"),
        "pets": sum(1 for r in table if r.get("lifeform") == "pet"),
        "operator": sum(1 for r in table if r.get("category_primary") == "operator"),
        "adversary": sum(1 for r in table if r.get("category_primary") == "adversary"),
        "business_contact": sum(1 for r in table if r.get("category_primary") == "business_contact"),
        "personal_contact": sum(1 for r in table if r.get("category_primary") == "personal_contact"),
        "with_schooling": sum(1 for r in table if r.get("schooling")),
        "with_tags": sum(1 for r in table if r.get("tags")),
        "internet_ties": sum(len(r.get("internet_ties") or []) for r in table),
    }

    doc = {
        "schema": "human-registry/v1",
        "updated": _now(),
        "motto": "Truth ID — know every human without census. Internet ties to people; identity sticks once known.",
        "tagline": "Prioritized human registry · business & personal links · FBI/CIA/Federal tags · verified schooling.",
        "touch_policy": {
            "motto": (
                "A human should never feel a touch if it is a safe signal. "
                "Music, normal car traffic, and animals are different."
            ),
            "safe_silent": True,
            "felt_safe": ["music", "traffic", "animal"],
        },
        "lock_threshold": LOCK_THRESHOLD,
        "humans": {r["truth_id"]: r for r in table},
        "ip_index": ip_index,
        "table": table,
        "stats": stats,
        "schools_verified": len(schools),
        "categories": ["operator", "personal_contact", "business_contact", "adversary", "pet", "unknown"],
        "link_types": ["personal", "business", "adversary", "infrastructure"],
    }
    _save_json(REGISTRY_JSON, doc)
    return doc


def panel_json() -> dict[str, Any]:
    doc = build_human_registry()
    _save_json(PANEL_CACHE, doc)
    return doc


def resolve_ip(ip: str) -> dict[str, Any] | None:
    doc = _load_json(REGISTRY_JSON, {})
    tid = (doc.get("ip_index") or {}).get(ip)
    if not tid:
        return None
    return (doc.get("humans") or {}).get(tid)


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    if cmd == "build":
        print(json.dumps(build_human_registry(), ensure_ascii=False))
        return 0
    if cmd == "resolve" and len(sys.argv) >= 3:
        hit = resolve_ip(sys.argv[2].strip())
        print(json.dumps(hit or {"ok": False, "ip": sys.argv[2]}, ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: human-registry.py [json|build|resolve IP]"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())