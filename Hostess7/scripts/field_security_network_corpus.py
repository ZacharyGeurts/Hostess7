#!/usr/bin/env pythong
"""Computer, network, and security expertise — NEXUS-Shield aligned."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CORPUS_CACHE = ROOT / "cache" / "fieldstorage" / "brain" / "security" / "corpus.json"
CORPUS_VERSION = 3

SECURITY_MARKERS = re.compile(
    r"\b(security|cyber|network|firewall|tls|https|nftables|dpi|packet|tamper|"
    r"owasp|stride|zero trust|ids|ips|ssh|dns|tcp|ip|vlan|segmentation|"
    r"nexus|nexus-shield|malware|phishing|injection|xss|csrf|encryption|"
    r"incident response|siem|vulnerability|hardening)\b",
    re.I,
)

SECURITY_DOMAINS: tuple[dict[str, str | tuple[str, ...]], ...] = (
    {
        "id": "computer_fundamentals",
        "title": "Computer systems fundamentals",
        "tags": ("cpu", "memory", "process", "kernel", "filesystem", "syscall", "driver"),
        "body": (
            "Processes isolate address spaces; the kernel mediates syscalls (open, read, write, fork, exec). "
            "Memory: stack, heap, mmap, page tables, ASLR, NX bit. Storage: block devices, journaling, permissions "
            "(owner/group/other, ACLs). Hostess7 runs on Linux — understand systemd units, cgroups, capabilities, "
            "and why ProtectSystem=strict matters for daemons."
        ),
    },
    {
        "id": "network_stack",
        "title": "Network stack — TCP/IP and DNS",
        "tags": ("tcp", "udp", "ip", "dns", "dhcp", "arp", "routing", "socket", "port"),
        "body": (
            "Layers: link (Ethernet/Wi-Fi), network (IP), transport (TCP/UDP), application (HTTP/TLS/DNS). "
            "TCP: three-way handshake, sequence/ack, congestion control, ESTABLISHED/LISTEN states (ss/netstat). "
            "DNS: resolver chain, caching, poisoning risk — verify with multiple resolvers. "
            "ARP maps IP→MAC on LAN; spoofing enables MITM. IPv6 dual-stack — don't forget ICMPv6 ND."
        ),
    },
    {
        "id": "tls_https",
        "title": "TLS and HTTPS",
        "tags": ("tls", "https", "certificate", "openssl", "handshake", "cipher", "sni"),
        "body": (
            "TLS 1.2+ provides confidentiality and integrity on the wire. Handshake: cipher suite, cert chain, "
            "key exchange, finished verify. Self-signed certs OK for localhost panels (NEXUS threat panel 9477). "
            "Production: Let's Encrypt or org CA, HSTS, no mixed content. "
            "Hostess7 GitHub Pages: HTTPS by default; demo UI must not embed secrets or call insecure APIs."
        ),
    },
    {
        "id": "firewall_nftables",
        "title": "Firewall policy — nftables / zero trust",
        "tags": ("firewall", "nftables", "ufw", "iptables", "drop", "allow", "segmentation"),
        "body": (
            "Default-deny inbound; allow established, loopback, required services. "
            "NEXUS-Shield firewall-sentinel: disables UFW, owns inet nexus table, blocks threat IPs and bad ports, "
            "restricts threat panel 9477 to localhost. "
            "Zero trust: verify every connection, micro-segment, log denies, auto-block on DPI correlation."
        ),
    },
    {
        "id": "dpi_threats",
        "title": "Deep packet inspection and threat vectors",
        "tags": ("dpi", "packet", "injection", "arp", "beacon", "c2", "mitm", "listener"),
        "body": (
            "Packet oracle: ss snapshots, ARP tables, DNS hash, tcpdump samples, raw socket scan. "
            "Threat vectors: PACKET_INJECTION, ARP_SPOOF, DNS_POISON, MITM_LISTENER, EGRESS_BEACON, "
            "LISTENER_SURGE, TLS_DOWNGRADE, C2_CORRELATION — 94% noise / 6% truth filter. "
            "Correlate with firewall auto-block; publish to HTTPS threat panel."
        ),
    },
    {
        "id": "appsec",
        "title": "Application security — OWASP and supply chain",
        "tags": ("owasp", "injection", "xss", "csrf", "auth", "sbom", "dependency"),
        "body": (
            "OWASP Top 10: broken access control, cryptographic failures, injection, insecure design, "
            "misconfiguration, vulnerable components, auth failures, integrity failures, logging, SSRF. "
            "Sanitize all user input in web UIs (GitHub Pages demo). Pin dependencies; verify checksums on ingest. "
            "NEXUS self-defense: signed MANIFEST.sha256, refuse tampered module loads."
        ),
    },
    {
        "id": "nexus_shield",
        "title": "NEXUS-Shield architecture (Hostess7 operator)",
        "tags": ("nexus", "nexus-shield", "seal", "tamper", "vigil", "hostess7"),
        "body": (
            "Mint field checkout: nexus-field-early.service (ZNetwork + C2 before login) then "
            "nexus-genius.service running NewLatest/lib/nexus-daemon.sh — must be chmod +x. "
            "State: .nexus-field-drive/nexus-field/state. Panel HTTP :9477/field, Queen :9481. "
            "Modules: network-lockdown, packet-oracle, firewall-sentinel (nftables), seal-vault, "
            "tamper-guard, field-attack-kit (autokill/RE-KILL), pest-arsenal. "
            "Kill tech doctrine: anchor in KILROY Field Die kernel substrate — nothing below. "
            "Setup: bash NewLatest/scripts/field-mint-boot-ready.sh. "
            "Hostess7: ./Hostess7.sh nexus status · ./Hostess7.sh stack-learn · ./Hostess7.sh stack status."
        ),
    },
    {
        "id": "field_stack_boot",
        "title": "SG Field Stack boot order",
        "tags": ("kilroy", "boot", "znetwork", "underlay", "f9", "field-drive"),
        "body": (
            "Boot: kilroy_kernel → unified_device_field → znetwork → underlay → nexus_c2 → guest_os. "
            "F9 after login: nexus_c2, kilroy, znetwork, ammoos. Field mirror: .nexus-field-drive "
            "(publish via field-drive-system.py). Grandma-safe: GRUB untouched until Tristate commit. "
            "Full corpus: ./Hostess7.sh stack-learn · doctrine: data/field-stack-doctrine.json."
        ),
    },
    {
        "id": "incident_response",
        "title": "Incident response and logging",
        "tags": ("incident", "siem", "forensics", "contain", "recover", "postmortem"),
        "body": (
            "Detect → analyze → contain → eradicate → recover → lessons learned. "
            "Preserve logs (/var/log/nexus-alerts.log, journalctl -u nexus-genius). "
            "Document timeline, indicators, blast radius. "
            "Hostess7 online: truth-filter before acting on fetched intel."
        ),
    },
    {
        "id": "online_security",
        "title": "Secure online operation (GitHub Pages + Codespaces)",
        "tags": ("github", "pages", "codespaces", "csp", "sanitize", "demo", "secrets"),
        "body": (
            "GitHub Pages: static demo only — no API keys, no sudo, no raw shell from browser. "
            "Content-Security-Policy, X-Frame-Options, sanitize chat input, HTTPS-only fetch. "
            "Full brain: Codespaces or local with fieldstorage on TEAM drive. Internet gate: HOSTESS7_INTERNET=1 with truth filter. "
            "Never commit secrets; use environment variables in Codespaces secrets."
        ),
    },
)

FREE_SECURITY_BOOKS: tuple[dict[str, str], ...] = (
    {"id": "gutenberg_art_of_war", "title": "The Art of War", "category": "security"},
    {"id": "gutenberg_babbage_economy", "title": "On the Economy of Machinery", "category": "security"},
)


def is_security_query(query: str) -> bool:
    return bool(SECURITY_MARKERS.search(query))


def _tokens(query: str) -> list[str]:
    return [t for t in re.split(r"\W+", query.lower()) if len(t) > 2]


def search_security(query: str, *, limit: int = 6) -> list[dict[str, Any]]:
    toks = _tokens(query)
    q = query.lower()
    scored: list[tuple[int, dict[str, Any]]] = []
    for d in SECURITY_DOMAINS:
        tags = " ".join(d.get("tags") or []).lower()
        body = str(d.get("body", "")).lower()
        title = str(d.get("title", "")).lower()
        blob = f"{title} {tags} {body[:600]}"
        score = sum(5 if t in tags else 2 if t in blob else 0 for t in toks)
        if "nexus" in q and d.get("id") == "nexus_shield":
            score += 20
        if "github" in q or "pages" in q:
            if d.get("id") == "online_security":
                score += 15
        if score > 0:
            scored.append((score, dict(d)))
    scored.sort(key=lambda x: -x[0])
    return [d for _, d in scored[:limit]]


def ensure_corpus() -> Path:
    CORPUS_CACHE.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "version": CORPUS_VERSION,
        "domains": [dict(d) for d in SECURITY_DOMAINS],
        "books": list(FREE_SECURITY_BOOKS),
        "training": ("computer", "network", "security", "nexus-shield", "online"),
    }
    CORPUS_CACHE.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return CORPUS_CACHE


def synthesize_security_paragraphs(query: str) -> list[str]:
    ensure_corpus()
    hits = search_security(query, limit=6)
    if not hits:
        hits = search_security("network security nexus firewall tls", limit=4)
    paras = ["Hostess 7 — computer, network, and security expertise (NEXUS-Shield aligned)."]
    for h in hits:
        paras.append(f"{h.get('title', 'Security')}: {h.get('body', '')}")
    paras.append(
        "Operator: ./Hostess7.sh nexus status · ./Hostess7.sh security-learn · "
        "truth-filter all online fetches (94% noise / 6% truth)."
    )
    return paras


def corpus_stats() -> dict[str, Any]:
    ensure_corpus()
    return {"version": CORPUS_VERSION, "total": len(SECURITY_DOMAINS), "books": len(FREE_SECURITY_BOOKS)}