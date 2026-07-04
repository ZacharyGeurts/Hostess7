#!/usr/bin/env pythong
"""Remove internet restrictions — foreign blocks off; open access worldwide."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-internet-unrestrict-doctrine.json"
PANEL = STATE / "field-internet-unrestrict-panel.json"

RESTRICT_COMMENTS = (
    "nexus-dns-local",
    "nexus-dns-local-v6",
    "nexus-dns-local-dot",
    "nexus-foreign-dhcp-threat",
    "nexus-foreign-dns-offer-threat",
    "nexus-foreign-dns-offer-threat-tcp",
)


def _utc() -> str:
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


def internet_unrestricted() -> bool:
    if os.environ.get("NEXUS_FIELD_INTERNET_UNRESTRICT", "1").strip().lower() in ("0", "false", "no", "off"):
        return False
    doctrine = _load(DOCTRINE, {})
    return bool((doctrine.get("policy") or {}).get("internet_open", True))


def foreign_block_enabled() -> bool:
    if internet_unrestricted():
        return False
    return os.environ.get("NEXUS_FIELD_DNS_FOREIGN_BLOCK", "0").strip().lower() in ("1", "true", "yes", "on")


def foreign_threat_block_enabled() -> bool:
    if internet_unrestricted():
        return False
    return os.environ.get("NEXUS_FIELD_FOREIGN_DNS_DHCP_THREAT", "0").strip().lower() in ("1", "true", "yes", "on")


def _nft_delete_by_comment(table: str, chain: str, comment: str) -> int:
    removed = 0
    try:
        proc = subprocess.run(
            ["nft", "-a", "list", "chain", "inet", table, chain],
            capture_output=True,
            text=True,
            timeout=4,
            errors="replace",
        )
        if proc.returncode != 0:
            return 0
        for line in (proc.stdout or "").splitlines():
            if comment not in line:
                continue
            m = re.search(r"# handle (\d+)", line)
            if not m:
                continue
            handle = m.group(1)
            del_proc = subprocess.run(
                ["nft", "delete", "rule", "inet", table, chain, "handle", handle],
                capture_output=True,
                timeout=3,
                errors="replace",
            )
            if del_proc.returncode == 0:
                removed += 1
    except (OSError, subprocess.TimeoutExpired):
        pass
    return removed


def remove_nft_restrictions() -> dict[str, Any]:
    table = os.environ.get("NEXUS_FIREWALL_TABLE", "nexus")
    removed: list[dict[str, Any]] = []
    for comment in RESTRICT_COMMENTS:
        for chain in ("input", "output"):
            count = _nft_delete_by_comment(table, chain, comment)
            if count:
                removed.append({"chain": chain, "comment": comment, "rules_removed": count})
    return {"ok": True, "table": table, "removed": removed, "rules_removed": sum(r["rules_removed"] for r in removed)}


def apply(*, remove_nft: bool = True) -> dict[str, Any]:
    actions: list[dict[str, Any]] = []
    if remove_nft:
        nft = remove_nft_restrictions()
        actions.append({"step": "remove_nft_restrictions", **nft})

    script = INSTALL / "lib" / "field-dns.sh"
    if script.is_file():
        try:
            subprocess.run(
                [
                    "bash", "-c",
                    f'export AML_BUILD=0 NEXUS_INSTALL_ROOT="{INSTALL}" NEXUS_STATE_DIR="{STATE}" '
                    f'NEXUS_FIELD_INTERNET_UNRESTRICT=1 NEXUS_FIELD_DNS_FOREIGN_BLOCK=0 '
                    f'NEXUS_FIELD_FOREIGN_DNS_DHCP_THREAT=0; '
                    f'source "{script}" && nexus_field_internet_unrestrict',
                ],
                capture_output=True,
                timeout=12,
                errors="replace",
            )
            actions.append({"step": "field_dns_unrestrict"})
        except (OSError, subprocess.TimeoutExpired):
            actions.append({"step": "field_dns_unrestrict", "error": "timeout"})

    panel = build_panel(write=True)
    panel["apply"] = {"actions": actions, "internet_open": True}
    _save(PANEL, panel)
    return panel


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    open_net = internet_unrestricted()
    doc = {
        "ok": True,
        "schema": "field-internet-unrestrict/v1",
        "updated": _utc(),
        "title": doctrine.get("title"),
        "motto": doctrine.get("motto"),
        "boss": doctrine.get("boss", "hostess7"),
        "internet_open": open_net,
        "foreign_resolver_block": foreign_block_enabled(),
        "foreign_dns_dhcp_threat_block": foreign_threat_block_enabled(),
        "restrictions_removed": open_net,
        "it_just_works": True,
        "policy": doctrine.get("policy") or {},
        "api": doctrine.get("api", "/api/field-internet-unrestrict"),
    }
    if write:
        _save(PANEL, doc)
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(build_panel(write=cmd == "panel"), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("apply", "remove", "unrestrict", "run"):
        print(json.dumps(apply(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "remove-nft":
        print(json.dumps(remove_nft_restrictions(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"usage": "field-internet-unrestrict.py [json|panel|apply|remove-nft]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())