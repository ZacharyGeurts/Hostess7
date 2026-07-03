#!/usr/bin/env python3
"""Build alphabetized stacked folder manifest for H7updater from live GitHub API."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

OWNER = "ZacharyGeurts"
PAGES = f"https://{OWNER.lower()}.github.io"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "h7updater-stack-index.json"

# Stacked layers (z) — lower = deeper in field stack
STACK: list[dict[str, Any]] = [
    {"id": "hostess7", "name": "Hostess7", "layer_z": -4, "role": "brain_supreme", "version_file": "Hostess7/VERSION.md", "pages": "Hostess7", "primary": True},
    {"id": "nexus-shield", "name": "NEXUS-Shield", "layer_z": -3, "role": "command_security", "optional": True, "legacy": True},
    {"id": "kilroy", "name": "KILROY", "layer_z": -2, "role": "field_boot", "pages": "KILROY"},
    {"id": "ammoos", "name": "AmmoOS", "layer_z": -1, "role": "field_os", "version_file": "data/ammoos-version.json", "pages": "AmmoOS", "update_primary": True},
    {"id": "h7updater", "name": "H7updater", "layer_z": 0, "role": "official_updates", "version_file": "data/h7updater-version.json", "pages": "H7updater"},
    {"id": "queen", "name": "Queen", "layer_z": 1, "role": "browser_shell", "pages": "Queen", "bundled": True},
    {"id": "grok16", "name": "Grok16", "layer_z": 1, "role": "compiler", "pages": "Grok16", "bundled": True},
    {"id": "znetwork", "name": "ZNetwork", "layer_z": 1, "role": "smart_relayer", "pages": "ZNetwork"},
    {"id": "ammocode", "name": "AmmoCode", "layer_z": 2, "role": "compiler_gui", "pages": "AmmoCode", "optional": True},
    {"id": "final_ear", "name": "Final_Ear", "layer_z": 2, "role": "sense_audio", "pages": "Final_Ear"},
    {"id": "final_eye", "name": "Final_Eye", "layer_z": 2, "role": "sense_vision", "pages": "Final_Eye"},
    {"id": "final_mouth", "name": "Final_Mouth", "layer_z": 2, "role": "sense_speech", "pages": "Final_Mouth"},
    {"id": "field_primer", "name": "Field_Primer", "layer_z": 3, "role": "primer", "pages": "Field_Primer"},
    {"id": "field_research", "name": "Field_Research", "layer_z": 3, "role": "research", "pages": "Field_Research"},
    {"id": "world_redata", "name": "World_Redata", "layer_z": 3, "role": "redata", "pages": "World_Redata"},
    {"id": "amouranthrtx", "name": "AMOURANTHRTX", "layer_z": 3, "role": "field_die", "pages": "AMOURANTHRTX"},
    {"id": "obs_fieldvoicefilter", "name": "OBS-FieldVoiceFilter", "layer_z": 3, "role": "obs_plugin", "pages": "OBS-FieldVoiceFilter"},
    {"id": "kill_grok_orphans", "name": "Kill-Grok-Orphans", "layer_z": 3, "role": "grok_watchdog", "pages": "Kill-Grok-Orphans"},
]


def gh_json(path: str) -> Any:
    proc = subprocess.run(
        ["gh", "api", path],
        capture_output=True,
        text=True,
        timeout=90,
    )
    if proc.returncode != 0:
        return None
    return json.loads(proc.stdout or "null")


def letter_bucket(name: str) -> str:
    ch = (name[0] if name else "?").upper()
    return ch if ch.isalpha() else "#"


def build_folder_tree(entries: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    tree: dict[str, list[dict[str, Any]]] = {}
    for e in sorted(entries, key=lambda x: x["name"].lower()):
        bucket = letter_bucket(e["name"])
        tree.setdefault(bucket, []).append(e)
    return dict(sorted(tree.items()))


def enrich(entry: dict[str, Any]) -> dict[str, Any]:
    repo = entry["name"]
    doc = gh_json(f"repos/{OWNER}/{repo}") or {}
    rel = gh_json(f"repos/{OWNER}/{repo}/releases/latest") or {}
    pages_slug = entry.get("pages") or repo
    out: dict[str, Any] = {
        "id": entry["id"],
        "name": repo,
        "github": f"{OWNER}/{repo}",
        "branch": doc.get("default_branch") or "main",
        "layer_z": entry.get("layer_z", 0),
        "role": entry.get("role", ""),
        "sovereign": True,
        "folder": f"stack/{letter_bucket(repo)}/{repo}",
        "repo_url": doc.get("html_url") or f"https://github.com/{OWNER}/{repo}",
        "pages_url": f"{PAGES}/{pages_slug}/" if entry.get("pages") else None,
        "releases_url": f"https://github.com/{OWNER}/{repo}/releases",
        "optional": bool(entry.get("optional")),
        "bundled": bool(entry.get("bundled")),
        "legacy": bool(entry.get("legacy")),
        "primary": bool(entry.get("primary")),
        "update_primary": bool(entry.get("update_primary")),
    }
    if entry.get("version_file"):
        out["version_file"] = entry["version_file"]
        out["version_raw_url"] = (
            f"https://raw.githubusercontent.com/{OWNER}/{repo}/"
            f"{out['branch']}/{entry['version_file']}"
        )
    if rel:
        out["latest_release"] = {
            "tag": rel.get("tag_name"),
            "name": rel.get("name"),
            "published": rel.get("published_at"),
            "url": rel.get("html_url"),
        }
    return out


def main() -> int:
    entries = [enrich(e) for e in STACK]
    manifest = {
        "schema": "h7updater-stack-index/v1",
        "title": "H7 Updater — alphabetized stacked folder index",
        "motto": "Layer stack × A–Z folders — Grok and warehouse read the same manifest.",
        "owner": OWNER,
        "sovereign_only_write": True,
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pages_base": PAGES,
        "stack_order": "layer_z ascending, then name A–Z within bucket",
        "folder_doctrine": {
            "pattern": "stack/{LETTER}/{RepoName}",
            "letter_rule": "first character uppercase A–Z, else #",
            "stack_rule": "layer_z: -4 brain → 0 warehouse → 3 satellites"
        },
        "entries": entries,
        "folder_tree": build_folder_tree(entries),
        "update_lane": {
            "primary_repo": "ZacharyGeurts/AmmoOS",
            "brain_repo": "ZacharyGeurts/Hostess7",
            "updater_repo": "ZacharyGeurts/H7updater",
            "manifest_self": "data/h7updater-stack-index.json",
            "oauth_doctrine": "data/h7updater-oauth-doctrine.json"
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({len(entries)} entries, {len(manifest['folder_tree'])} letter buckets)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())