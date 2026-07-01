#!/usr/bin/env pythong
"""NEXUS Trust Strike Engine — pinpoint wire-point strikes with dossier-backed certainty.

Resolves the ACTUAL end wire endpoint (LAN MAC device or remote C2 host identity),
shields consumer/insecure browsing collateral (CDN edges, porn-on-HTTP viewers),
and fail-closes until malware evidence + wire confirmation reach certainty thresholds.
Friendly-guard remains immutable and runs first.
"""
from __future__ import annotations

import ipaddress
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
HOSTILE_TSV = STATE / "field-hostile.tsv"
CORPUS_CACHE = STATE / "trust-strike-corpus.json"
SUMMARY_CACHE = STATE / "trust-strike-summary.json"
CORPUS_CACHE_TTL_SEC = 120
DOSSIER_FILE = os.environ.get("NEXUS_TARGET_DOSSIER_FILE", "nexus-target-dossiers.jsonl")

STRIKE_AUTO_MIN = 0.99
STRIKE_MANUAL_MIN = 0.85
STRIKE_REKILL_MIN = 0.85
AUTO_MIN_SIGNALS = 2
AUTO_MIN_SIGNAL_WEIGHT = 0.12
WIRE_CERTAINTY_MIN = 0.99

HOSTILE_VECTORS = frozenset({
    "HOSTILE", "FIREWALL_BLOCK", "THREAT", "MALWARE", "C2", "BOTNET", "INTRUSION",
})
HARM_VERDICTS = frozenset({"HARM_CANDIDATE", "BLOCK_RECOMMENDED", "SUSPICIOUS"})
FRIENDLY_VERDICTS = frozenset({"USER_OK", "EPHEMERAL"})
CDN_IP_CLASSES = frozenset({"stream_cdn", "search_cdn"})
CONSUMER_PORTS = frozenset({80, 443, 8080, 8443, 853})

BROWSER_PROCS = frozenset({
    "fieldfox", "field-queen", "queen-browser",
    "firefox", "chrome", "chromium", "brave", "brave-browser", "vivaldi", "opera",
    "msedge", "waterfox", "librewolf", "floorp", "thorium", "google-chrome", "google-chrome-stable",
})
MEDIA_PROCS = BROWSER_PROCS | frozenset({
    "vlc", "mpv", "totem", "spotify", "discord", "obs", "ffmpeg", "youtube", "celluloid", "streamlink",
})
CONSUMER_PROCS = MEDIA_PROCS | frozenset({
    "thunderbird", "betterbird", "evolution", "geary", "mailspring", "kmail", "slack", "zoom", "teams",
})

CDN_ORG_RE = re.compile(
    r"(cloudflare|akamai|fastly|amazon|google|microsoft|facebook|meta|apple|"
    r"netflix|cloudfront|edgecast|limelight|stackpath|cdn77|bunny|cachefly|github)",
    re.I,
)
ADULT_CONTENT_RE = re.compile(
    r"(porn|xxx|adult|onlyfans|chaturbate|xhamster|pornhub|redtube|youporn|"
    r"cam4|livejasmin|brazzers|xvideos|xnxx|stripchat|myfreecams)",
    re.I,
)
CAMPAIGN_PATTERNS: list[tuple[str, re.Pattern[str], float]] = [
    ("cobalt_strike", re.compile(r"cobalt[\s_-]?strike|\bcs[\s_-]?beacon\b", re.I), 0.32),
    ("asyncrat", re.compile(r"async[\s_-]?rat|asyncrat", re.I), 0.30),
    ("havoc", re.compile(r"\bhavoc\b", re.I), 0.28),
    ("remcos", re.compile(r"\bremcos\b", re.I), 0.28),
    ("adaptix", re.compile(r"adaptix[\s_-]?c2|adaptixc2", re.I), 0.30),
    ("mythic", re.compile(r"\bmythic\b", re.I), 0.26),
    ("threatfox", re.compile(r"threatfox|abuse\.ch", re.I), 0.18),
    ("rat_generic", re.compile(r"\brat\b|remote[\s_-]?access[\s_-]?trojan", re.I), 0.22),
]

C2_PORTS = frozenset({3004, 3005, 4444, 4443, 5555, 6006, 6606, 7001, 7002, 8808, 9002, 9003, 1337, 31337})
STRONG_WIRE_MARKERS = frozenset({"tls_subject", "ptr_hostname", "banner", "mac_oui"})

import importlib.util

_fg_spec = importlib.util.spec_from_file_location("friendly_guard", INSTALL / "lib" / "friendly-guard.py")
_fg = importlib.util.module_from_spec(_fg_spec)
assert _fg_spec and _fg_spec.loader
_fg_spec.loader.exec_module(_fg)
refuse_kill = _fg.refuse_kill

_hi_spec = importlib.util.spec_from_file_location("host_identity", INSTALL / "lib" / "host-identity.py")
_hi = importlib.util.module_from_spec(_hi_spec)
assert _hi_spec and _hi_spec.loader
_hi_spec.loader.exec_module(_hi)
load_archived_dossier = _hi.load_archived_dossier
extract_identity_fingerprint = _hi.extract_identity_fingerprint


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



def _norm(s: Any) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip().lower())


def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _is_private_ip(ip: str) -> bool:
    if not ip:
        return True
    try:
        addr = ipaddress.ip_address(ip.split("%")[0])
        return addr.is_private or addr.is_loopback or addr.is_link_local
    except ValueError:
        return True


def _proc_base(point: dict[str, Any]) -> str:
    mon = point.get("monitor") if isinstance(point.get("monitor"), dict) else {}
    proc = (
        point.get("our_process")
        or mon.get("process")
        or point.get("process")
        or ""
    )
    return str(proc).lower().split("/")[-1]


def _is_consumer_process(point: dict[str, Any]) -> bool:
    base = _proc_base(point)
    return base in CONSUMER_PROCS


def _ip_class(point: dict[str, Any]) -> str:
    mon = point.get("monitor") if isinstance(point.get("monitor"), dict) else {}
    return str(mon.get("ip_class") or point.get("ip_class") or "")


def _dossier_paths() -> list[Path]:
    hostess7 = Path(os.environ.get("HOSTESS7_ROOT", str(INSTALL / "Hostess7")))
    team_field = Path(os.environ.get("HOSTESS7_TEAM_FIELD", "/media/default/HOSTESS7_TEAM/fieldstorage"))
    return [
        hostess7 / "cache" / "fieldstorage" / "brain" / "security" / DOSSIER_FILE,
        team_field / "brain" / "security" / DOSSIER_FILE,
        STATE / "field-storage" / DOSSIER_FILE,
    ]


def _disabled_ips() -> set[str]:
    ips: set[str] = set()
    if not HOSTILE_TSV.is_file():
        return ips
    try:
        for line in HOSTILE_TSV.read_text(encoding="utf-8", errors="replace").splitlines()[1:]:
            parts = line.split("\t")
            if len(parts) >= 2 and parts[1]:
                ips.add(parts[1].strip())
    except OSError:
        pass
    return ips


def _path_readable(path: Path) -> bool:
    try:
        return path.is_file()
    except OSError:
        return False


def _iter_archived_dossiers() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in _dossier_paths():
        if not _path_readable(path):
            continue
        try:
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if row.get("kind") != "nexus_target_dossier":
                    continue
                dossier = row.get("dossier") if isinstance(row.get("dossier"), dict) else row
                ip = str(row.get("ip") or dossier.get("ip") or "")
                if ip:
                    rows.append({"ip": ip, "ts": row.get("ts", ""), "dossier": dossier})
        except OSError:
            continue
    return rows


def build_hostile_corpus(*, refresh: bool = False) -> dict[str, Any]:
    """Learn hostile markers from archived KILL dossiers and registry."""
    import time

    if not refresh and CORPUS_CACHE.is_file():
        try:
            cached = json.loads(CORPUS_CACHE.read_text(encoding="utf-8"))
            age = time.time() - float(cached.get("_cached_ts") or 0)
            if age < CORPUS_CACHE_TTL_SEC and cached.get("hostile_ips") is not None:
                return cached
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass

    asns: set[str] = set()
    orgs: set[str] = set()
    campaigns: set[str] = set()
    fingerprints: list[dict[str, Any]] = []
    ips: set[str] = set()

    for row in _iter_archived_dossiers():
        ip = row["ip"]
        ips.add(ip)
        dossier = row["dossier"]
        geo = dossier.get("geo") or {}
        asn = _norm(dossier.get("asn") or geo.get("asn"))
        org = _norm(dossier.get("org") or geo.get("org"))
        if asn:
            asns.add(asn)
        if org:
            orgs.add(org)
        for field in (dossier.get("vector"), dossier.get("reason"), dossier.get("detail")):
            text = str(field or "")
            for name, pat, _ in CAMPAIGN_PATTERNS:
                if pat.search(text):
                    campaigns.add(name)
        fp = dossier.get("identity_fingerprint")
        if isinstance(fp, dict) and fp.get("identity_hash"):
            fingerprints.append(fp)
        else:
            fingerprints.append(extract_identity_fingerprint({**dossier, "ip": ip}))

    disabled = _disabled_ips()
    ips.update(disabled)
    dossier_rows = _iter_archived_dossiers()

    doc = {
        "updated": _now(),
        "dossier_count": len(dossier_rows),
        "registry_count": len(disabled),
        "hostile_ips": sorted(ips),
        "asns": sorted(asns),
        "orgs": sorted(orgs),
        "campaigns": sorted(campaigns),
        "fingerprints": fingerprints,
        "_cached_ts": time.time(),
    }
    try:
        CORPUS_CACHE.parent.mkdir(parents=True, exist_ok=True)
        tmp = CORPUS_CACHE.with_suffix(".tmp")
        tmp.write_text(json.dumps(doc, ensure_ascii=False) + "\n", encoding="utf-8")
        tmp.replace(CORPUS_CACHE)
    except OSError:
        pass
    return doc


def _text_blob(point: dict[str, Any]) -> str:
    parts = [
        point.get("vector"),
        point.get("detail"),
        point.get("verdict"),
        point.get("process"),
        point.get("org"),
        point.get("asn"),
        point.get("reason"),
        point.get("ptr_hostname"),
        point.get("target_tls_subject"),
        point.get("hostname"),
    ]
    dos = point.get("dossier")
    if isinstance(dos, dict):
        parts.extend([dos.get("vector"), dos.get("summary"), dos.get("detail")])
    return " ".join(str(p) for p in parts if p)


def _campaign_hits(blob: str) -> list[str]:
    return [name for name, pat, _ in CAMPAIGN_PATTERNS if pat.search(blob)]


def _monitor_harm(point: dict[str, Any]) -> int:
    mon = point.get("monitor")
    if not isinstance(mon, dict):
        return 0
    try:
        return int(mon.get("harm_total") or 0)
    except (TypeError, ValueError):
        return 0


def _ports_seen(point: dict[str, Any]) -> set[int]:
    ports: set[int] = set()
    for raw in point.get("target_ports") or []:
        try:
            ports.add(int(raw))
        except (TypeError, ValueError):
            pass
    mon = point.get("monitor")
    if isinstance(mon, dict):
        try:
            ports.add(int(mon.get("remote_port") or 0))
        except (TypeError, ValueError):
            pass
    for sess in point.get("monitor_sessions") or []:
        if isinstance(sess, dict):
            try:
                ports.add(int(sess.get("remote_port") or 0))
            except (TypeError, ValueError):
                pass
    return {p for p in ports if p > 0}


def _dpi_correlation(ip: str) -> dict[str, Any] | None:
    path = STATE / "packet-field.json"
    doc = _load_json(path, {})
    alerts = doc.get("dpi_alerts") or doc.get("alerts") or []
    if not isinstance(alerts, list):
        return None
    for alert in alerts:
        if not isinstance(alert, dict):
            continue
        if str(alert.get("remote_ip") or alert.get("ip") or "") == ip:
            conf = float(alert.get("confidence") or 0)
            if conf >= 0.92:
                return alert
    return None


def _identity_markers(point: dict[str, Any]) -> dict[str, str]:
    fp = point.get("identity_fingerprint")
    if isinstance(fp, dict) and fp.get("markers"):
        return {k: v for k, v in fp["markers"].items() if v}
    markers: dict[str, str] = {}
    for key, src in (
        ("ptr_hostname", point.get("ptr_hostname")),
        ("tls_subject", point.get("target_tls_subject")),
        ("banner", point.get("target_banner")),
        ("mac_oui", point.get("mac_oui")),
        ("asn", point.get("asn")),
        ("org", point.get("org")),
    ):
        val = _norm(src)
        if val:
            markers[key] = val
    return markers


def _consumer_collateral(point: dict[str, Any], blob: str) -> tuple[bool, str]:
    """Shield innocent viewers on shared CDN / insecure HTTP — not the wire endpoint."""
    if _campaign_hits(blob):
        return False, ""
    verdict = str(point.get("verdict") or (point.get("monitor") or {}).get("verdict") or "")
    if verdict in FRIENDLY_VERDICTS:
        return True, "consumer_intentional_traffic"

    consumer = _is_consumer_process(point)
    ip_class = _ip_class(point)
    ports = _ports_seen(point)
    harm = _monitor_harm(point)
    mon = point.get("monitor") if isinstance(point.get("monitor"), dict) else {}
    axes = mon.get("axis_scores") or {}

    if consumer and ip_class in CDN_IP_CLASSES:
        if ports <= CONSUMER_PORTS or not ports:
            return True, "consumer_cdn_edge_not_wire_endpoint"

    if consumer and (80 in ports or str(mon.get("remote_port")) in ("80", "8080")):
        if harm < 14 and not _campaign_hits(blob):
            return True, "insecure_http_viewer_not_c2"

    if ADULT_CONTENT_RE.search(blob) and consumer and harm < 16:
        return True, "adult_content_viewer_not_malware_host"

    try:
        user_browser = int(axes.get("user_browser") or 0)
        media_stream = int(axes.get("media_stream") or 0)
        stream_theft = int(axes.get("stream_theft_risk") or 0)
    except (TypeError, ValueError):
        user_browser = media_stream = stream_theft = 0

    if consumer and user_browser >= 7 and media_stream >= 6 and stream_theft <= 3 and harm < 12:
        return True, "browser_media_stream_collateral"

    if CDN_ORG_RE.search(_norm(point.get("org"))) and consumer and harm < 12:
        return True, "shared_cdn_collateral"

    return False, ""


def resolve_wire_point(point: dict[str, Any], corpus: dict[str, Any]) -> dict[str, Any]:
    """Pinpoint the ACTUAL end wire endpoint — LAN device or direct remote C2 host."""
    ip = str(point.get("ip") or "")
    private = _is_private_ip(ip)
    markers = _identity_markers(point)
    blob = _text_blob(point)
    campaigns = _campaign_hits(blob)
    ports = _ports_seen(point)
    consumer = _is_consumer_process(point)
    ip_class = _ip_class(point)
    archived = load_archived_dossier(ip)
    registry_hit = ip in corpus.get("hostile_ips", [])

    wire: dict[str, Any] = {
        "ip": ip,
        "scope": "unknown",
        "confirmed": False,
        "certainty": 0.0,
        "evidence": [],
        "label": "",
        "lan_device": private,
    }

    if registry_hit and archived:
        wire.update({
            "scope": "registry_locked",
            "confirmed": True,
            "certainty": 1.0,
            "evidence": ["prior_kill_archived_dossier"],
            "label": f"Registry-locked wire point {ip}",
        })
        return wire

    if private:
        mac = str(point.get("mac") or "")
        oui = str(point.get("mac_oui") or markers.get("mac_oui") or "")
        vendor = str(point.get("mac_vendor") or "")
        evidence: list[str] = []
        if mac and oui:
            evidence.append(f"lan_mac:{oui}")
        if vendor:
            evidence.append(f"lan_vendor:{vendor[:32]}")
        if campaigns:
            evidence.append("lan_malware_campaign")
        if mac and oui and (campaigns or _monitor_harm(point) >= 14):
            wire.update({
                "scope": "lan_device",
                "confirmed": True,
                "certainty": 0.99 if campaigns else 0.92,
                "evidence": evidence,
                "label": f"LAN wire device {ip} · {vendor or oui}",
            })
        elif mac and oui:
            wire.update({
                "scope": "lan_device",
                "confirmed": False,
                "certainty": 0.45,
                "evidence": evidence,
                "label": f"LAN neighbor {ip} — needs malware corroboration",
            })
        else:
            wire.update({
                "scope": "lan_unresolved",
                "confirmed": False,
                "certainty": 0.0,
                "evidence": [],
                "label": f"LAN {ip} — no MAC/neighbor wire lock",
            })
        return wire

    if consumer and ip_class in CDN_IP_CLASSES:
        wire.update({
            "scope": "cdn_edge",
            "confirmed": False,
            "certainty": 0.0,
            "evidence": ["shared_cdn_not_endpoint"],
            "label": "CDN edge — not the actual hostile wire host",
        })
        return wire

    strong = [k for k in STRONG_WIRE_MARKERS if markers.get(k)]
    evidence = [f"marker:{k}" for k in strong]
    c2_hits = sorted(ports & C2_PORTS)

    if c2_hits and not consumer:
        evidence.append(f"c2_port_daemon:{','.join(str(p) for p in c2_hits[:3])}")
    if campaigns:
        evidence.append(f"campaign:{campaigns[0]}")

    dpi = _dpi_correlation(ip)
    if dpi and not consumer:
        evidence.append(f"dpi_c2:{dpi.get('confidence')}")

    hosting = ip_class in ("classified_remote", "hosting", "identified_org", "cloud_aws", "cloud_azure")
    if hosting and not CDN_ORG_RE.search(_norm(point.get("org"))):
        evidence.append("direct_hosting_peer")

    certainty = 0.0
    confirmed = False
    if len(strong) >= 2 and not consumer:
        certainty = 0.99
        confirmed = True
    elif campaigns and (len(strong) >= 1 or c2_hits) and not consumer:
        certainty = 0.99
        confirmed = True
    elif dpi and campaigns and not consumer:
        certainty = 0.99
        confirmed = True
    elif registry_hit and campaigns:
        certainty = 0.99
        confirmed = True
    elif c2_hits and not consumer and hosting and len(strong) >= 1:
        certainty = 0.95
        confirmed = True
    elif campaigns and not consumer and hosting:
        certainty = 0.92
        confirmed = True
    elif len(strong) == 1 and not consumer and not ip_class in CDN_IP_CLASSES:
        certainty = 0.72
        confirmed = False

    scope = "remote_endpoint" if confirmed else "remote_unconfirmed"
    label = f"Wire host {ip}"
    if markers.get("ptr_hostname"):
        label = f"Wire host {markers['ptr_hostname'][:48]}"
    elif markers.get("tls_subject"):
        label = f"Wire TLS {markers['tls_subject'][:48]}"

    wire.update({
        "scope": scope,
        "confirmed": confirmed,
        "certainty": round(certainty, 3),
        "evidence": evidence[:8],
        "label": label,
    })
    return wire


def _malware_evidence(signals: list[dict[str, Any]], campaigns: list[str], point: dict[str, Any]) -> bool:
    sig_ids = {s["id"] for s in signals}
    if campaigns:
        return True
    if "prior_kill_registry" in sig_ids or "archived_dossier_strong" in sig_ids:
        return True
    if "dpi_high_alert" in sig_ids:
        return True
    if "c2_ports" in sig_ids and not _is_consumer_process(point):
        return True
    if "beacon_axis" in sig_ids and _monitor_harm(point) >= 14 and not _is_consumer_process(point):
        return True
    return False


def score_strike(point: dict[str, Any], corpus: dict[str, Any] | None = None) -> dict[str, Any]:
    """Compute pinpoint strike confidence. Does not check friendly-guard."""
    corpus = corpus or build_hostile_corpus()
    ip = str(point.get("ip") or "")
    blob = _text_blob(point)
    campaigns = _campaign_hits(blob)
    signals: list[dict[str, Any]] = []

    def add(sig_id: str, weight: float, detail: str) -> None:
        if weight <= 0:
            return
        signals.append({"id": sig_id, "weight": round(weight, 3), "detail": detail[:160]})

    wire = resolve_wire_point(point, corpus)
    collateral, collateral_reason = _consumer_collateral(point, blob)

    if wire.get("confirmed"):
        add("wire_point_locked", 0.28, wire.get("label") or "End wire point confirmed")
    elif wire.get("scope") == "cdn_edge":
        add("wire_cdn_edge", 0.0, wire.get("label", ""))

    if ip in corpus.get("hostile_ips", []):
        add("prior_kill_registry", 0.38, "IP in permanent hostile registry")

    archived = load_archived_dossier(ip)
    if archived:
        fp = archived.get("identity_fingerprint") or extract_identity_fingerprint({**archived, "ip": ip})
        mc = int(fp.get("marker_count") or 0)
        if mc >= 4:
            add("archived_dossier_strong", 0.22, f"Archived dossier with {mc} identity markers")
        elif mc >= 2:
            add("archived_dossier", 0.14, f"Archived dossier with {mc} identity markers")

    asn = _norm(point.get("asn"))
    org = _norm(point.get("org"))
    if asn and asn in corpus.get("asns", []):
        add("hostile_asn_corpus", 0.20, f"ASN matches prior KILL corpus: {asn[:48]}")
    if org and org in corpus.get("orgs", []):
        add("hostile_org_corpus", 0.18, f"Org matches prior KILL corpus: {org[:48]}")

    campaign_weights = {n: w for n, _, w in CAMPAIGN_PATTERNS}
    for name in campaigns:
        add(f"campaign_{name}", campaign_weights.get(name, 0.22), f"Campaign marker: {name}")

    verdict = str(point.get("verdict") or (point.get("monitor") or {}).get("verdict") or "")
    if verdict in HARM_VERDICTS and not collateral:
        add("harm_verdict", 0.18, f"Monitor verdict {verdict}")

    harm = _monitor_harm(point)
    if harm >= 18 and not collateral:
        add("harm_critical", 0.16, f"Harm total {harm}")
    elif harm >= 14 and not collateral and not _is_consumer_process(point):
        add("harm_high", 0.10, f"Harm total {harm} · non-consumer process")

    vector = str(point.get("vector") or "").upper()
    if vector in HOSTILE_VECTORS and campaigns:
        add("hostile_vector", 0.10, f"Vector {vector} + campaign")

    try:
        heat = float(point.get("heat") or 0)
    except (TypeError, ValueError):
        heat = 0.0
    if heat >= 0.85 and campaigns:
        add("heat_critical", 0.10, f"Heat {heat:.2f} + campaign")

    ports = _ports_seen(point)
    c2_hits = sorted(ports & C2_PORTS)
    if c2_hits and not _is_consumer_process(point):
        add("c2_ports", 0.24, f"C2-class ports: {','.join(str(p) for p in c2_hits[:4])}")

    mon = point.get("monitor")
    if isinstance(mon, dict) and not collateral:
        axes = mon.get("axis_scores") or {}
        try:
            threat_linked = int(axes.get("threat_linked") or 0)
            beacon = int(axes.get("beacon_pattern") or 0)
        except (TypeError, ValueError):
            threat_linked = beacon = 0
        if threat_linked >= 7 and campaigns:
            add("threat_linked_axis", 0.10, f"threat_linked axis {threat_linked}/10")
        if beacon >= 7 and not _is_consumer_process(point):
            add("beacon_axis", 0.14, f"beacon_pattern axis {beacon}/10")

    dpi = _dpi_correlation(ip)
    if dpi and not _is_consumer_process(point):
        add("dpi_high_alert", 0.28, f"Packet DPI alert conf={dpi.get('confidence')}")

    from_monitor = point.get("source") == "gatekeeper" or point.get("is_monitor_target") or point.get("globe_pin")
    if from_monitor and campaigns:
        add("live_monitor_target", 0.08, "Active monitor + malware campaign")

    penalties: list[dict[str, Any]] = []
    if collateral:
        penalties.append({
            "id": "consumer_collateral",
            "weight": -0.55,
            "detail": collateral_reason or "Consumer/shared CDN collateral — not wire endpoint",
        })
    if wire.get("scope") == "cdn_edge":
        penalties.append({
            "id": "cdn_wire_blocked",
            "weight": -0.45,
            "detail": "CDN edge is not the actual end wire hostile host",
        })
    if not wire.get("confirmed") and ip not in corpus.get("hostile_ips", []):
        penalties.append({
            "id": "wire_unconfirmed",
            "weight": -0.35,
            "detail": wire.get("label") or "End wire point not confirmed",
        })
    if _is_consumer_process(point) and not campaigns:
        penalties.append({
            "id": "consumer_process",
            "weight": -0.30,
            "detail": f"Consumer app {_proc_base(point)} — not a C2 daemon wire point",
        })
    if not from_monitor and harm < 10 and ip not in corpus.get("hostile_ips", []):
        penalties.append({
            "id": "intel_only",
            "weight": -0.15,
            "detail": "Passive intel only — no live monitor session",
        })

    pos_weight = sum(s["weight"] for s in signals)
    neg_weight = sum(abs(p["weight"]) for p in penalties)
    raw_confidence = max(0.0, min(0.99, pos_weight - neg_weight))

    wire_certainty = float(wire.get("certainty") or 0.0)
    pinpoint_confidence = round(min(raw_confidence, wire_certainty if wire.get("confirmed") else raw_confidence * 0.6), 3)

    strong_signals = [s for s in signals if s["weight"] >= AUTO_MIN_SIGNAL_WEIGHT]
    corroborated = len(strong_signals) >= AUTO_MIN_SIGNALS or any(s["weight"] >= 0.25 for s in signals)
    malware = _malware_evidence(signals, campaigns, point)

    strike_certain = (
        wire.get("confirmed")
        and not collateral
        and malware
        and pinpoint_confidence >= WIRE_CERTAINTY_MIN
        and (wire.get("scope") == "registry_locked" or corroborated)
    )

    if strike_certain:
        pinpoint_confidence = 1.0

    strike_ready_auto = strike_certain and pinpoint_confidence >= STRIKE_AUTO_MIN
    strike_ready_manual = (
        wire.get("confirmed")
        and not collateral
        and malware
        and pinpoint_confidence >= STRIKE_MANUAL_MIN
    )
    strike_ready_rekill = wire.get("scope") == "registry_locked" or (
        wire.get("confirmed") and malware and pinpoint_confidence >= STRIKE_REKILL_MIN
    )

    return {
        "ip": ip,
        "strike_confidence": pinpoint_confidence,
        "strike_auto_confidence": pinpoint_confidence if not collateral else 0.0,
        "pinpoint_confidence": pinpoint_confidence,
        "wire_point": wire,
        "consumer_collateral": collateral,
        "consumer_collateral_reason": collateral_reason,
        "malware_evidence": malware,
        "strike_certain": strike_certain,
        "hardware_destroy": strike_certain,
        "strike_mode": "destroy" if strike_certain else "block",
        "strike_ready": strike_ready_auto,
        "strike_ready_manual": strike_ready_manual,
        "strike_ready_rekill": strike_ready_rekill,
        "corroborated": corroborated,
        "signals": signals[:12],
        "penalties": penalties,
        "thresholds": {
            "auto": STRIKE_AUTO_MIN,
            "manual": STRIKE_MANUAL_MIN,
            "rekill": STRIKE_REKILL_MIN,
            "wire_certainty": WIRE_CERTAINTY_MIN,
        },
        "corpus": {
            "dossier_count": corpus.get("dossier_count", 0),
            "registry_count": corpus.get("registry_count", 0),
        },
    }


def gate_strike(
    ip: str,
    point: dict[str, Any] | None = None,
    *,
    mode: str = "manual",
    monitor: dict[str, Any] | None = None,
    force: bool = False,
    corpus: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Full strike gate: friendly-guard first, then pinpoint wire-point certainty."""
    ip = str(ip or "").strip()
    point = dict(point or {})
    point.setdefault("ip", ip)
    if monitor and not point.get("monitor"):
        point["monitor"] = monitor

    refuse, guard_reason = refuse_kill(ip, monitor=point.get("monitor") if isinstance(point.get("monitor"), dict) else monitor)
    score = score_strike(point, corpus=corpus)

    mode = (mode or "manual").lower()
    if mode == "auto":
        ready = score.get("strike_ready")
        min_conf = STRIKE_AUTO_MIN
        used_conf = score.get("pinpoint_confidence")
    elif mode == "rekill":
        ready = score.get("strike_ready_rekill")
        min_conf = STRIKE_REKILL_MIN
        used_conf = score.get("pinpoint_confidence")
    else:
        ready = score.get("strike_ready_manual")
        min_conf = STRIKE_MANUAL_MIN
        used_conf = score.get("pinpoint_confidence")

    collateral = score.get("consumer_collateral")
    allowed = not refuse and not collateral and (ready or force)
    if refuse:
        reason = guard_reason
    elif collateral:
        reason = score.get("consumer_collateral_reason") or "consumer_collateral"
    elif not ready and not force:
        if not score.get("wire_point", {}).get("confirmed"):
            reason = "wire_point_unconfirmed"
        elif not score.get("malware_evidence"):
            reason = "no_malware_evidence"
        else:
            reason = "strike_confidence_low"
    else:
        reason = "strike_authorized" if not force else "operator_force"

    return {
        "ip": ip,
        "allowed": allowed,
        "refuse": not allowed,
        "reason": reason,
        "mode": mode,
        "friendly_refused": refuse,
        "friendly_reason": guard_reason if refuse else "",
        "consumer_collateral": collateral,
        "wire_point": score.get("wire_point"),
        "strike_confidence": used_conf,
        "strike_certain": score.get("strike_certain"),
        "hardware_destroy": score.get("hardware_destroy"),
        "strike_mode": score.get("strike_mode"),
        "certainty": 1.0 if score.get("strike_certain") else used_conf,
        "strike_ready": ready,
        "force": force,
        "min_confidence": min_conf,
        "score": score,
        "engine": "trust-strike-v2-pinpoint",
        "fail_closed": True,
    }


def trust_strike_summary(*, refresh: bool = False) -> dict[str, Any]:
    if not refresh and SUMMARY_CACHE.is_file():
        try:
            cached = json.loads(SUMMARY_CACHE.read_text(encoding="utf-8"))
            if cached.get("engine"):
                return cached
        except (OSError, json.JSONDecodeError):
            pass
    corpus = build_hostile_corpus(refresh=refresh)
    doc = {
        "engine": "trust-strike-v2-pinpoint",
        "updated": corpus.get("updated"),
        "thresholds": {
            "auto": STRIKE_AUTO_MIN,
            "manual": STRIKE_MANUAL_MIN,
            "rekill": STRIKE_REKILL_MIN,
            "wire_certainty": WIRE_CERTAINTY_MIN,
            "auto_min_signals": AUTO_MIN_SIGNALS,
        },
        "corpus": {
            "dossier_count": corpus.get("dossier_count", 0),
            "registry_count": corpus.get("registry_count", 0),
            "asn_patterns": len(corpus.get("asns", [])),
            "org_patterns": len(corpus.get("orgs", [])),
            "campaigns_learned": corpus.get("campaigns", []),
        },
        "motto": "Pinpoint the end wire host — never cook CDN collateral or insecure viewers.",
    }
    try:
        SUMMARY_CACHE.parent.mkdir(parents=True, exist_ok=True)
        tmp = SUMMARY_CACHE.with_suffix(".tmp")
        tmp.write_text(json.dumps(doc, ensure_ascii=False) + "\n", encoding="utf-8")
        tmp.replace(SUMMARY_CACHE)
    except OSError:
        pass
    return doc


def main() -> int:
    import sys

    if len(sys.argv) < 2:
        print("usage: trust-strike-engine.py [summary|score|gate|wire] ...", file=sys.stderr)
        return 2
    cmd = sys.argv[1]
    if cmd in ("summary", "json"):
        json.dump(trust_strike_summary(), sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0
    if cmd == "score" and len(sys.argv) >= 3:
        try:
            point = json.loads(sys.argv[2])
        except json.JSONDecodeError:
            return 2
        json.dump(score_strike(point), sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0
    if cmd == "wire" and len(sys.argv) >= 3:
        try:
            point = json.loads(sys.argv[2])
        except json.JSONDecodeError:
            return 2
        json.dump(resolve_wire_point(point, build_hostile_corpus()), sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0
    if cmd == "gate" and len(sys.argv) >= 3:
        ip = sys.argv[2]
        point = {}
        mode = "manual"
        if len(sys.argv) > 3:
            try:
                point = json.loads(sys.argv[3])
            except json.JSONDecodeError:
                mode = sys.argv[3]
        if len(sys.argv) > 4:
            mode = sys.argv[4]
        json.dump(gate_strike(ip, point, mode=mode), sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())