#!/usr/bin/env pythong
"""Build local Hostess 7 communication profile from https://x.com/ZacharyGeurts — no runtime X calls."""
from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

INSTALL = Path(__file__).resolve().parents[1]
OUT = INSTALL / "data" / "hostess7-communication-profile.json"
AVATAR_OUT = INSTALL / "panel" / "assets" / "hostess7-operator-x-avatar.jpg"
SOURCE_URL = "https://x.com/ZacharyGeurts"
UA = "AmmoOS-Hostess7-CommProfile-Builder/1.0"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fetch(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _download(url: str, dest: Path) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as resp:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(resp.read())
        return dest.is_file() and dest.stat().st_size > 0
    except (urllib.error.URLError, OSError):
        return False


def _extract(html: str) -> dict[str, str]:
    def meta(prop: str) -> str:
        m = re.search(rf'<meta[^>]+property="{re.escape(prop)}"[^>]+content="([^"]*)"', html, re.I)
        if m:
            return m.group(1).strip()
        m = re.search(rf'<meta[^>]+content="([^"]*)"[^>]+property="{re.escape(prop)}"', html, re.I)
        return m.group(1).strip() if m else ""

    title = meta("og:title") or "BIG GRIN (@ZacharyGeurts)"
    desc = meta("og:description") or meta("description") or ""
    image = meta("og:image") or ""

    display = "BIG GRIN"
    if "@" in title:
        display = title.split("@")[0].strip().rstrip("(").strip() or display
    display = re.sub(r"\s+", " ", display)

    bio = desc
    if not bio:
        bio = (
            "God=1D spine of all. Higher D ⊃ (lower +1), never 0. "
            "Thing-within-thing gazes ∞. No edges — air & soup co-arise."
        )

    bio = bio.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")

    return {
        "display_name": display,
        "handle": "ZacharyGeurts",
        "bio": bio,
        "avatar_remote": image,
        "location": "Gladstone, Michigan, USA",
        "website": "https://github.com/ZacharyGeurts",
    }


def build(*, fetch_remote: bool = True) -> dict:
    fields: dict[str, str] = {
        "display_name": "BIG GRIN",
        "handle": "ZacharyGeurts",
        "bio": (
            "God=1D spine of all. Higher D ⊃ (lower +1), never 0. A edgeless. "
            "Thing-within-thing gazes ∞. Reduced: air & soup co-arise, permeate, flavor each other. No edges"
        ),
        "location": "Gladstone, Michigan, USA",
        "website": "https://github.com/ZacharyGeurts",
        "avatar_remote": "https://pbs.twimg.com/profile_images/2066540278018629632/nLv3TkSn_400x400.jpg",
    }
    fetch_ok = False
    if fetch_remote:
        try:
            html = _fetch(SOURCE_URL)
            fields = {**fields, **_extract(html)}
            fetch_ok = True
        except (urllib.error.URLError, OSError, TimeoutError):
            pass

    avatar_local = "/assets/hostess7-operator-x-avatar.jpg"
    avatar_saved = False
    remote = fields.get("avatar_remote") or ""
    if remote:
        avatar_saved = _download(remote, AVATAR_OUT)

    voice = {
        "register": "operator_sovereign",
        "tone": ["direct", "truth-forward", "BIG GRIN warmth", "field-stack fluent"],
        "sign_off": "— Hostess 7 on behalf of BIG GRIN",
        "never_cloud_egress": True,
        "sole_egress": "znetwork_relayer",
        "queen_speaks_out": True,
    }

    doc = {
        "schema": "hostess7-communication-profile/v1",
        "title": "Hostess 7 communication profile — Operator voice (local)",
        "built_at": _now(),
        "source": {
            "platform": "x",
            "url": SOURCE_URL,
            "handle": fields["handle"],
            "fetched_live": fetch_ok,
            "policy": "Build-time ingest only — runtime reads this file, never calls X.",
        },
        "operator": {
            "handle": fields["handle"],
            "display_name": fields["display_name"],
            "bio": fields["bio"],
            "location": fields.get("location") or "",
            "website": fields.get("website") or "https://github.com/ZacharyGeurts",
            "github": "https://github.com/ZacharyGeurts",
            "avatar_local": avatar_local if avatar_saved else "",
            "avatar_remote": remote,
            "posts_note": "Operator posts on X — Hostess 7 mirrors tone locally.",
        },
        "voice": voice,
        "znetwork": {
            "connected": True,
            "module": "lib/hostess7-znetwork-wire.py",
            "egress_owner": "znetwork_relayer",
            "queen_outbound_only": True,
            "loopback_control": "127.0.0.1",
            "api": "/api/hostess7/znetwork",
        },
        "hostess7": {
            "superintelligence": True,
            "communique_schema": "hostess7-ai-communique/v1",
            "truth_floor": 58,
            "primary_transport": "json",
            "outbox": "Hostess7/cache/fieldstorage/brain/superintel/outbox.jsonl",
            "znetwork_ledger": ".nexus-state/hostess7-znetwork-outbox.jsonl",
        },
        "message_templates": {
            "status": "ZNetwork pipe live — Queen speaks out through relayer on behalf of @{handle}.",
            "greeting": "BIG GRIN on the wire. Hostess 7 Super Intelligence connected — all egress local-controlled.",
            "alert": "Field alert for Operator — truth-gated, ZNetwork sole egress.",
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return doc


def main() -> int:
    offline = "--offline" in sys.argv
    doc = build(fetch_remote=not offline)
    print(json.dumps({"ok": True, "path": str(OUT), "handle": doc["operator"]["handle"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())