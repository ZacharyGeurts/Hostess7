#!/usr/bin/env pythong
"""SG Field Stack corpus — boot order, KILROY kill substrate, field drive, services, F9.

Hostess 7 teaches operators how the whole device field works: nothing below KILROY,
defensive/offensive kill tech anchored in the secured kernel, grandma-safe underlay.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
NEWLATEST = ROOT.parent
DOCTRINE = ROOT / "data" / "field-stack-doctrine.json"
CORPUS_CACHE = ROOT / "cache" / "fieldstorage" / "brain" / "field_stack" / "corpus.json"
CORPUS_VERSION = 7

STACK_MARKERS = re.compile(
    r"\b(kilroy|field\s*die|boot\s*order|znetwork|underlay|f9|nexus-genius|"
    r"field-early|unified\s*device|field\s*mirror|nexus-field-drive|"
    r"autokill|re-kill|pest-arsenal|attack-kit|syscall|guest\s*os|"
    r"grandma|passthrough|mint\s*boot|field-mint)\b",
    re.I,
)

STACK_DOMAINS: tuple[dict[str, str | tuple[str, ...]], ...] = (
    {
        "id": "kilroy_self_defensive",
        "title": "KILROY self-defensive — always on, guest cannot disable",
        "tags": ("kilroy", "self-defensive", "tamper", "integrity", "security", "field-die"),
        "body": (
            "KILROY Field Die is self-defensive at the syscall boundary — not a userspace service "
            "Mint or Windows can stop. Built-in layers: 4-slot tamper verify (TIME/MEMORY/THERMO/CONTEXT), "
            "NEXUS behavioral guard (amortized), rtx_slots_tamper_action abort on corruption, "
            "consumer-safe syscall whitelist. Telemetry: cat /proc/kilroy_field/security. "
            "This runs continuously without operator updates. Guest malware cannot chmod-away kernel "
            "self-defense — unlike nexus-genius.service which the host admin could stop before "
            "KILROY bzImage is live."
        ),
    },
    {
        "id": "kilroy_update_process",
        "title": "Periodic update process — stack refresh without disabling self-defense",
        "tags": ("update", "build-kilroy", "nexus-update", "ammoos-update", "recompile", "periodic"),
        "body": (
            "Self-defense is always-on; updates are separate periodic lanes. "
            "KILROY kernel (occasional): Field .fld → gen-field-stack.sh → kilroy-become-substrate.sh "
            "→ build-kilroy.sh → grok-mkimage.sh; field-recompile.sh after stack changes; test-all.sh. "
            "NEXUS userspace (as needed): panel /ammoos-update-os, lib/nexus-update-apply.sh with "
            "nexus-update-lock.sh, or bash scripts/field-mint-boot-ready.sh for Mint checkout refresh. "
            "AmmoOS stack: lib/ammoos-update-inplace.py — preflight, lock, apply, never break running field. "
            "Hostess7: ./Hostess7.sh updates advisory · ./Hostess7.sh stack-learn after doctrine changes. "
            "Updates ship improved rules and images — they do not turn off tamper verify during apply."
        ),
    },
    {
        "id": "kilroy_pc_core",
        "title": "KILROY PC core — boots the computer, owns network + defense + offense",
        "tags": ("kilroy", "pc-core", "kernel", "field-die", "syscall", "network", "kill"),
        "body": (
            "KILROY is the new PC core (lib/kilroy-core.sh). It boots the machine and loads guest OS "
            "(Mint, Windows) normally inside the field grant. ZNetwork is absorbed — not a separate "
            "boot layer; lib/znetwork-field.sh remains the network-lane implementation under KILROY. "
            "Total defense (tamper verify, network-lockdown, firewall) and offense (attack-kit, "
            "pest-arsenal, lethal-enforcement, relayer retaliation) anchor in KILROY Field Die. "
            "Today: userspace graft from NewLatest/KILROY until bzImage boots. Guest cannot disable substrate."
        ),
    },
    {
        "id": "boot_order",
        "title": "Boot order — before and after login",
        "tags": ("boot", "order", "early", "systemd", "desktop", "guest"),
        "body": (
            "Cold boot stack: kilroy_kernel → unified_device_field → underlay → guest_os. "
            "NEXUS C2 panel (black/green/pink, :9477) lives inside kilroy_kernel — all-out Field tech monitoring. "
            "systemd: nexus-field-early.service runs scripts/nexus-field-early-boot.sh before display-manager. "
            "nexus-genius.service starts lib/nexus-daemon.sh via lib/kilroy-core.sh publish. "
            "GRUB/Mint/Windows unchanged until Tristate commit. After login: F9 sovereign hook "
            "(lib/field-underlay-hotkey.py) overrides host shortcuts → lib/field-queen-browser-open.py f9 — "
            "order kilroy, ammoos."
        ),
    },
    {
        "id": "unified_device_field",
        "title": "One field — whole device",
        "tags": ("unified", "device", "storage", "ram", "motherboard", "voltage", "fcc"),
        "body": (
            "lib/field-unified-device.py + data/field-unified-device-doctrine.json — single envelope "
            "for drives, RAM, motherboard DMI, voltage rails, FCC wireless, KILROY PC core (network lane), NEXUS C2. "
            "Verdict PARTIAL is normal until kernel proc is live. guest_field_grant: true means any "
            "incumbent OS receives field tech through HostPassthrough ABI. Check: "
            "pythong lib/field-unified-device.py json"
        ),
    },
    {
        "id": "field_drive_mirror",
        "title": "Field drive — host mirror, not nested TEAM",
        "tags": ("field-drive", "mirror", "publish", "team", "hostess7", "defield"),
        "body": (
            "Live field root: NewLatest/.nexus-field-drive (not Hostess7/cache/fieldstorage mirrors "
            "for nexus-field). Publish: pythong lib/field-drive-system.py publish. "
            "lib/field-non-fielded-safety.py blocks nested nexus-field on physical TEAM drive. "
            "Defield first: purge WRDT/redata tails before physical fielding. "
            "Hostess7 TEAM drive (/media/default/HOSTESS7_TEAM) holds operator data; "
            "field mirror stays on checkout until commit. 500× space via field tech on physical "
            "drive after defield + commit — not on host mirror."
        ),
    },
    {
        "id": "kilroy_network_lane",
        "title": "KILROY network lane — ZNetwork absorbed",
        "tags": ("kilroy", "network", "relayer", "fcc", "znetwork-absorbed"),
        "body": (
            "ZNetwork is no longer a separate stack layer. Network truth lives in KILROY PC core: "
            "lib/kilroy-core.sh boards lib/znetwork-field.sh as implementation; marker kilroy-net-lane.json. "
            "Early boot: NEXUS_KILROY_NET=1, ZNETWORK_FAST=1. Kernel path: netlink_field slots 16–19 "
            "on unified field bus. Grandma's browser passes untouched — guest OS loads normally."
        ),
    },
    {
        "id": "queen_ammoos_surfaces",
        "title": "Queen = web browser · AmmoOS = normal desktop",
        "tags": ("queen", "ammoos", "browser", "desktop", "f9", "surfaces"),
        "body": (
            "Queen is the web browser only — http://127.0.0.1:9481/world/browser.html. "
            "AmmoOS is the normal desktop — http://127.0.0.1:9477/field. F9 launches AmmoOS "
            "fullscreen desktop, not Queen as the desktop shell. Queen world stays up as browser "
            "service; operator opens Queen from desktop when needed. Doctrine: data/kilroy-boot-services.json."
        ),
    },
    {
        "id": "kilroy_boot_services_dns_dhcp",
        "title": "KILROY boot services — DNS/DHCP tables pre-configured on kernel boot",
        "tags": ("kilroy", "dns", "dhcp", "boot", "kernel", "services"),
        "body": (
            "On KILROY kernel boot (and userspace graft today), lib/kilroy-boot-services.py boards "
            "from data/kilroy-boot-services.json: verifies DNS tables (dns-multipoint-seed, "
            "dns-admin-seed, dns-legal-rfc-seed, dns-internet-tld-seed), DHCP table "
            "(field-dhcp-seed.json — pool + DNS option 127.0.0.1), connects via "
            "lib/field-local-dns-connect.py when DNS/DHCP daemons are running. "
            "Marker: kilroy-boot-services.json. Wired by lib/kilroy-core.sh on every board/publish."
        ),
    },
    {
        "id": "kilroy_loopback_sovereignty",
        "title": "KILROY is 127.0.0.1 — any computer, zero bother",
        "tags": ("kilroy", "loopback", "127.0.0.1", "security", "storage", "speed"),
        "body": (
            "KILROY becomes loopback authority 127.0.0.1 on any and every computer — without bothering "
            "the incumbent OS. Guest keeps working normally (HostPassthrough). Boons through loopback: "
            "security (NEXUS C2 :9477, field-dns truth resolver, network lockdown), Field Tech speed "
            "(local panel/Queen — no cloud hop), storage space (field-drive mirror .nexus-field-drive). "
            "Module: lib/kilroy-loopback.py · marker kilroy-loopback.json · boarded by lib/kilroy-core.sh. "
            "Doctrine: data/kilroy-loopback-doctrine.json."
        ),
    },
    {
        "id": "kilroy_nexus_c2_panel",
        "title": "NEXUS C2 inside KILROY — black green pink monitoring panel",
        "tags": ("nexus-c2", "panel", "kilroy", "monitoring", "9477", "threat-panel"),
        "body": (
            "NEXUS C2 is not a separate boot layer — it lives inside KILROY PC core (lib/kilroy-core.sh). "
            "Panel: http://127.0.0.1:9477/field · command: /command. Theme black_emerald_rose_2026 "
            "(black, green, tinge of pink). All-out Field tech monitoring via lib/threat-panel.sh and "
            "lib/threat-panel-http.py. Marker: kilroy-nexus-c2.json. Genius daemon publishes via "
            "nexus_kilroy_core_publish — not standalone ZNetwork/C2 layers."
        ),
    },
    {
        "id": "f9_sovereign_hook",
        "title": "F9 sovereign hook — overrides everyone",
        "tags": ("f9", "hotkey", "sovereign", "override", "keyboard", "hook"),
        "body": (
            "F9 built-in overrides everyone because we got the hook. lib/field-underlay-hotkey.py listens "
            "on /dev/input/event* for KEY_F9, stamps f9-sovereign-hook.json, engages "
            "lib/field-keyboard-sovereign.py (host WM shortcuts inhibited), then launches "
            "lib/field-queen-browser-open.py f9. Boot order: kilroy (includes NEXUS C2), ammoos. "
            "Doctrine: data/f9-sovereign-hook-doctrine.json."
        ),
    },
    {
        "id": "underlay_grandma_safe",
        "title": "Underlay — grandma-safe passthrough",
        "tags": ("underlay", "passthrough", "grub", "tristate", "commit", "f9"),
        "body": (
            "lib/field-underlay.sh + field-underlay-doctrine — host stays boss until operator "
            "commits Tristate. Normal GRUB, Mint login, Windows preserved. F9 hotkey: "
            "lib/field-underlay-hotkey.py install (not install-autostart — that blocks on listener). "
            "F9 sovereign override engages when pressed — host shortcuts yield to KILROY. "
            "Drop-panel wall deleted — desktop shell only. Underlay posture: passthrough, not committed."
        ),
    },
    {
        "id": "nexus_genius_services",
        "title": "NEXUS genius layer — systemd health",
        "tags": ("nexus-genius", "nexus-field-early", "daemon", "systemd", "health"),
        "body": (
            "nexus-field-early.service: active (exited) after successful early boot marker "
            "field-underlay-early.json (kilroy_network_lane, kilroy_nexus_c2). "
            "nexus-genius.service: must run executable lib/nexus-daemon.sh (chmod +x required). "
            "Dev checkout skips MANIFEST integrity via nexus_is_dev_install. "
            "first-boot.complete in state dir switches daemon to lighter refresh boot path. "
            "Health: systemctl is-active both units; panel :9477; Queen :9481. "
            "Setup: sudo bash scripts/field-mint-boot-ready.sh (sudo interactive — never in repo)."
        ),
    },
    {
        "id": "kill_tech_modules",
        "title": "Defensive and offensive kill tech — module map",
        "tags": ("autokill", "re-kill", "pest-arsenal", "attack-kit", "lethal", "defensive", "offensive"),
        "body": (
            "Defensive: seal-vault, tamper-guard, network-lockdown, firewall-sentinel, "
            "field-rf-sentinel, friendly-guard, paranoia-mode. Offensive: field-attack-kit.py "
            "(autokill, RE-KILL, NO-KILL), pest-arsenal.sh, lethal-enforcement.py, "
            "kill-codes.py, planetary-observer.py, znetwork-hostile-threat.py. "
            "Owned by KILROY PC core (lib/kilroy-core.sh) via nexus-daemon; syscall plane in Field Die "
            "when bzImage is live so guest malware cannot disable them. "
            "Truth-gated: Hostess7 supreme authority — lethal still truth_gated."
        ),
    },
    {
        "id": "operator_commands",
        "title": "Operator commands — stack router + registry",
        "tags": ("hostess7", "commands", "setup", "health", "operator", "stack"),
        "body": (
            "Canonical router: ./scripts/stack.sh help — wire, start, fast, restart, mint-ready, "
            "pre-reboot, early, kilroy core, kilroy build, aml. Registry: data/field-scripts-registry.json. "
            "Hostess7: ./Hostess7.sh stack-learn · ./Hostess7.sh stack status · ./Hostess7.sh nexus status. "
            "Mint dev: stack.sh mint-ready · stack.sh pre-reboot · lib/ammolang-run.sh mint_pre_reboot. "
            "Prod install: genius_shield.sh (not field-mint-boot-ready). "
            "KILROY kernel: stack.sh kilroy build when bzImage needed."
        ),
    },
    {
        "id": "scripts_registry",
        "title": "Script audit — keep, merge, delete",
        "tags": ("scripts", "registry", "merge", "delete", "canonical"),
        "body": (
            "field-scripts-registry.json maps one canonical path per job. MERGE: aml.sh and ammoos-* "
            "wrappers → lib/ammolang-run.sh only; stealth_install → install-all.sh. "
            "KEEP: field-mint-* (dev), genius_shield (prod), start-field-stack (full), "
            "ammoos-direct-start (fast), wire-stack, integrate-znetwork. "
            "FIXED: znetwork symlinks now point at NewLatest/ZNetwork. "
            "LEGACY (keep until migration done): v10-mission, kilroy-extract, h7-migrate-batch."
        ),
    },
)


def is_stack_query(query: str) -> bool:
    return bool(STACK_MARKERS.search(query))


def _tokens(query: str) -> list[str]:
    return [t for t in re.split(r"\W+", query.lower()) if len(t) > 2]


def search_stack(query: str, *, limit: int = 6) -> list[dict[str, Any]]:
    toks = _tokens(query)
    q = query.lower()
    scored: list[tuple[int, dict[str, Any]]] = []
    for d in STACK_DOMAINS:
        tags = " ".join(d.get("tags") or []).lower()
        body = str(d.get("body", "")).lower()
        title = str(d.get("title", "")).lower()
        blob = f"{title} {tags} {body[:800]}"
        score = sum(5 if t in tags else 2 if t in blob else 0 for t in toks)
        if "kilroy" in q and d.get("id") == "nothing_below_kilroy":
            score += 20
        if "boot" in q and d.get("id") == "boot_order":
            score += 15
        if "f9" in q or "hotkey" in q:
            if d.get("id") in ("underlay_grandma_safe", "boot_order"):
                score += 12
        if score > 0:
            scored.append((score, dict(d)))
    scored.sort(key=lambda x: -x[0])
    return [d for _, d in scored[:limit]]


def load_doctrine() -> dict[str, Any]:
    if DOCTRINE.is_file():
        return json.loads(DOCTRINE.read_text(encoding="utf-8"))
    return {}


def ensure_corpus() -> Path:
    CORPUS_CACHE.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "version": CORPUS_VERSION,
        "doctrine_path": str(DOCTRINE),
        "doctrine": load_doctrine(),
        "domains": [dict(d) for d in STACK_DOMAINS],
        "training": ("kilroy", "boot", "field-drive", "znetwork", "underlay", "nexus", "kill-tech"),
    }
    CORPUS_CACHE.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return CORPUS_CACHE


def synthesize_stack_paragraphs(query: str) -> list[str]:
    ensure_corpus()
    hits = search_stack(query, limit=6)
    if not hits:
        hits = search_stack("kilroy boot order field drive nexus genius", limit=5)
    paras = [
        "Hostess 7 — SG Field Stack (KILROY bottom, kill tech in secured kernel, one field whole device)."
    ]
    for h in hits:
        paras.append(f"{h.get('title', 'Stack')}: {h.get('body', '')}")
    paras.append(
        "Operator: ./Hostess7.sh stack-learn · ./Hostess7.sh stack status · "
        "./Hostess7.sh nexus status · doctrine: Hostess7/data/field-stack-doctrine.json"
    )
    return paras


def corpus_stats() -> dict[str, Any]:
    ensure_corpus()
    return {"version": CORPUS_VERSION, "total": len(STACK_DOMAINS), "doctrine": DOCTRINE.is_file()}


def stack_status_main() -> int:
    """CLI entry for stack status."""
    report = stack_status_report()
    print(report)
    return 0 if "OK field-stack-status" in report else 1


def stack_status_report() -> str:
    """Live posture summary for operator CLI."""
    import os
    import subprocess

    lines = ["=== SG Field Stack (Hostess 7) ==="]
    if DOCTRINE.is_file():
        d = load_doctrine()
        lines.append(f"doctrine: {DOCTRINE}")
        lines.append(f"motto: {d.get('motto', '')}")
        lines.append(f"boot_order: {' → '.join(d.get('boot_order') or [])}")
    nl = NEWLATEST
    state = nl / ".nexus-field-drive" / "nexus-field" / "state"
    lines.append(f"install_root: {nl}")
    lines.append(f"state_dir: {state} ({'present' if state.is_dir() else 'missing'})")
    for unit in ("nexus-field-early.service", "nexus-genius.service"):
        try:
            proc = subprocess.run(
                ["systemctl", "is-active", unit],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            lines.append(f"service: {unit} → {proc.stdout.strip() or proc.stderr.strip()}")
        except (OSError, subprocess.TimeoutExpired):
            lines.append(f"service: {unit} → unknown")
    daemon = nl / "lib" / "nexus-daemon.sh"
    lines.append(f"nexus-daemon.sh: {'executable' if os.access(daemon, os.X_OK) else 'NOT EXECUTABLE — chmod +x'}")
    for url, label in (
        ("http://127.0.0.1:9477/field", "panel"),
        ("http://127.0.0.1:9481/api/status", "queen"),
    ):
        try:
            proc = subprocess.run(
                ["curl", "-sf", url],
                capture_output=True,
                timeout=5,
                check=False,
            )
            lines.append(f"{label}: {'up' if proc.returncode == 0 else 'down'}")
        except (OSError, subprocess.TimeoutExpired):
            lines.append(f"{label}: unknown")
    marker = state / "field-underlay-early.json"
    if marker.is_file():
        lines.append(f"early_marker: {marker}")
    fb = state / "first-boot.complete"
    lines.append(f"first-boot.complete: {'yes' if fb.is_file() else 'no (heavy first boot on genius start)'}")
    lines.append("METRIC field_stack=1")
    lines.append("OK field-stack-status")
    return "\n".join(lines)