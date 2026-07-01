"""Tab Beacon — first NEXUS panel plugin. Adds a useful strip to every tab's plugin dock."""
from __future__ import annotations

from typing import Any

VIEWS = (
    "command", "us", "honor", "field-rf", "monitor", "inspect", "library",
    "host-attack", "dossier", "human-dossier", "research", "settings", "logs",
)


def _chip(label: str, text: str, *, accent: str = "internet", jump: str = "", jump_label: str = "") -> dict[str, Any]:
    row: dict[str, Any] = {"label": label, "text": text, "accent": accent}
    if jump:
        row["action"] = {"jump": jump, "label": jump_label or "Open →"}
    return row


def panel_snapshot(doc: dict[str, Any]) -> dict[str, Any]:
    views: dict[str, dict[str, Any]] = {}
    signal = doc.get("truth_signal") or 0
    updated = (doc.get("updated") or "")[-8:] or "—"

    cmd = doc.get("field_command") or {}
    hh = cmd.get("heaven_hell") or {}
    pulse = cmd.get("pulse") or {}
    views["command"] = _chip(
        "Command",
        f"Heaven {hh.get('heaven_count', 0)} · Hell {hh.get('hell_count', 0)} · "
        f"rip-ready {hh.get('hell_chosen_count', 0)} · signal {signal}% · updated {updated}",
        accent="gold",
        jump="packets/monitor",
        jump_label="Live flows →",
    )

    us = doc.get("us_field") or {}
    ident = us.get("identity") or {}
    net = us.get("network") or {}
    conns = net.get("connections") or []
    views["us"] = _chip(
        "US field",
        f"{ident.get('hostname') or ident.get('short_host') or 'this machine'} · "
        f"{len(conns)} connections · {ident.get('primary_ip') or 'no primary IP'}",
        jump="command",
        jump_label="Command deck →",
    )

    ba = doc.get("browser_awareness") or {}
    active_sites = ba.get("active_sites") or []
    op = doc.get("operator_location") or {}
    loc = "set" if op.get("lat") is not None else "unset"
    views["honor"] = _chip(
        "Honorability",
        f"{len(active_sites)} active browser site(s) · operator location {loc} · "
        f"pending {len((ba.get('honorability') or {}).get('pending_acceptance') or [])}",
        jump="threats/host-attack",
        jump_label="Threat map →",
    )

    fr = doc.get("field_rf") or {}
    ant = fr.get("antenna") or {}
    res = ant.get("resolution") or {}
    views["field-rf"] = _chip(
        "Field RF",
        f"{ant.get('scan_count', 0)} APs · {ant.get('wifi_devices', [ant.get('wifi_device')]) and len(ant.get('wifi_devices') or [ant.get('wifi_device')]) or 0} antenna field(s) · "
        f"resolution {res.get('tier') or ant.get('resolution_tier') or '—'} ({res.get('score') or ant.get('resolution_score') or '—'})",
        accent="ok",
        jump="intel/field-rf",
    )

    gk = doc.get("gatekeeper") or {}
    conns_gk = gk.get("connections") or []
    good = sum(1 for c in conns_gk if str(c.get("verdict") or "").lower() in ("good", "friendly", "heaven"))
    bad = sum(1 for c in conns_gk if str(c.get("verdict") or "").lower() in ("bad", "harm", "hell"))
    views["monitor"] = _chip(
        "Live connections",
        f"{len(conns_gk)} scored flows · good {good} · bad {bad} · "
        f"trusted {doc.get('trust_count') or len(doc.get('trusted') or [])}",
        jump="packets/inspect",
        jump_label="DPI inspect →",
    )

    pf = doc.get("packet_field") or {}
    recent = pf.get("recent") or []
    modem = pf.get("modem") or {}
    views["inspect"] = _chip(
        "Deep inspect",
        f"{len(recent)} recent packets · modem {modem.get('carrier') or 'warming'} · "
        f"alert {'on' if modem.get('alert') else 'off'}",
        jump="packets/monitor",
        jump_label="Live tab →",
    )

    lib = doc.get("h7_library") or {}
    books = lib.get("books") or []
    views["library"] = _chip(
        "H7 library",
        f"{len(books)} field book(s) on shelf · pick one to read operator + network guides",
        jump="library",
    )

    ha = doc.get("host_attacks") or {}
    stats = ha.get("stats") or {}
    views["host-attack"] = _chip(
        "Threat map",
        f"{stats.get('total', 0)} targets · hot {stats.get('hot', 0)} · "
        f"killed {stats.get('killed', 0) or (doc.get('attack_kit') or {}).get('disabled_count', 0)}",
        accent="threat",
        jump="threats/human-dossier",
        jump_label="Kill orders →",
    )

    sw = doc.get("terror_spiderweb") or {}
    sws = sw.get("stats") or {}
    focus = sw.get("focus") or {}
    ex = sw.get("existence_identity") or {}
    exs = ex.get("stats") or {}
    views["spiderweb"] = _chip(
        "Terror spiderweb",
        f"{sws.get('identified_everywhere', 0)} everywhere · "
        f"{exs.get('existing', 0)} existence · {exs.get('vision_corroborated', 0)} vision · "
        f"{sws.get('mobile_moving', 0)} moving · heat {focus.get('heat_sum', 0)}",
        accent="threat",
        jump="threats/spiderweb",
        jump_label="Open spiderweb →",
    )

    ad = doc.get("angel_dossiers") or {}
    views["dossier"] = _chip(
        "Attack paths",
        f"{ad.get('dossier_count', len(ad.get('dossiers') or []))} angel dossier(s) tracing warnings to peers/CVEs",
        jump="threats/dossier",
    )

    hd = doc.get("human_dossier") or {}
    views["human-dossier"] = _chip(
        "Kill orders",
        f"{hd.get('ip_count', len(hd.get('ips') or []))} Grok Heavy dossier IP(s) · analyst {hd.get('analyst') or 'Grok Heavy'}",
        accent="threat",
        jump="threats/host-attack",
        jump_label="Globe map →",
    )

    ar = doc.get("angel_research") or {}
    tables = ar.get("tables") or {}
    views["research"] = _chip(
        "Research",
        f"MAC {len(tables.get('mac_vendors') or [])} · IP intel {len(tables.get('ip_intel') or [])} · "
        f"CVE map {len(tables.get('exploit_cve_map') or [])}",
        jump="intel/research",
    )

    settings = doc.get("settings") or {}
    on_watchers = sum(1 for k, v in settings.items() if k.startswith("NEXUS_") and v in ("1", "true", "on", True))
    views["settings"] = _chip(
        "Settings",
        f"{on_watchers} protection/watch toggles ON · plugins dock on every tab below",
        jump="system/settings",
    )

    views["logs"] = _chip(
        "Logs",
        f"Signal {signal}% · vigil {doc.get('vigil_mode') or 'calm'} · panel v{doc.get('version') or '—'}",
        jump="system/logs",
    )

    return {
        "plugin": "tab-beacon",
        "views": views,
        "view_count": len(views),
    }