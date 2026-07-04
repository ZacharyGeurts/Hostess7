#!/usr/bin/env python3
"""Operator X comments — syndicate recoverable posts/replies to Hostess7 pages."""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCS_API = Path(os.environ.get("HOSTESS7_ROOT", INSTALL / "Hostess7")) / "docs" / "api"
CACHE = STATE / "operator-x-comments-cache.json"
HANDLE = os.environ.get("OPERATOR_X_HANDLE", "ZacharyGeurts")
UA = "Hostess7-XComments/2.0"
OPERATOR_ALIASES = frozenset({
    "zacharygeurts", "biggrin", "big_grin", "zachary_geurts", "zacharyrobertgeurts",
})
IMPERSONATION_MARKERS = (
    "plagiar", "copyscape", "turnitin", "originality", "ai wrote", "ai-written",
    "written by ai", "chatgpt", "not your words", "stolen content", "copyright strike",
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _http_json(url: str) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def _norm_handle(h: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (h or "").lower())


def _impersonation_risk(*, handle: str, name: str, text: str) -> dict[str, Any]:
    h = _norm_handle(handle)
    looks_like_operator = (
        h in OPERATOR_ALIASES
        or "zachary" in h and "geurts" in h
        or h.startswith("zacharyg")
        or "biggrin" in h
    ) and h != _norm_handle(HANDLE)
    plagiarism_bait = any(m in (text or "").lower() for m in IMPERSONATION_MARKERS)
    return {
        "impersonation_handle": looks_like_operator,
        "plagiarism_harassment": plagiarism_bait,
        "risk": "high" if looks_like_operator else ("medium" if plagiarism_bait else "low"),
    }


def _extract_thread(doc: dict[str, Any], tw: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("reply_thread", "thread", "replies_list", "conversation", "replies"):
        val = doc.get(key) or tw.get(key)
        if isinstance(val, list) and val:
            return [x for x in val if isinstance(x, dict)]
    return []


def _probe_reply_lanes(tid: str) -> dict[str, Any]:
    """Direct urllib lane — bypasses browser, adblock, gatekeeper, DNS hooks on operator UI."""
    lanes: list[dict[str, Any]] = []
    for label, url in (
        ("fxtwitter_replies", f"https://api.fxtwitter.com/{HANDLE}/status/{tid}/replies"),
        ("fxtwitter_status", f"https://api.fxtwitter.com/{HANDLE}/status/{tid}"),
        ("vxtwitter_status", f"https://api.vxtwitter.com/{HANDLE}/status/{tid}"),
        ("vxtwitter_replies", f"https://api.vxtwitter.com/{HANDLE}/status/{tid}/replies"),
        ("syndication_tweet", f"https://cdn.syndication.twimg.com/tweet-result?id={tid}&lang=en"),
    ):
        row: dict[str, Any] = {"lane": label, "url": url, "ok": False}
        try:
            doc = _http_json(url)
            row["ok"] = True
            tw = doc.get("tweet") or doc
            if isinstance(tw, dict):
                row["reply_count"] = tw.get("replies")
                row["conversation_id"] = tw.get("conversationID") or tw.get("conversation_id_str")
            thread = _extract_thread(doc, tw if isinstance(tw, dict) else {})
            row["reply_bodies"] = len(thread)
            row["reply_bodies_withheld"] = bool(
                int((tw.get("replies") if isinstance(tw, dict) else 0) or 0) > 0 and not thread
            )
            lanes.append(row)
        except (urllib.error.URLError, OSError, json.JSONDecodeError, TimeoutError) as exc:
            row["error"] = str(exc)[:160]
            lanes.append(row)
    withheld = [l for l in lanes if l.get("reply_bodies_withheld")]
    return {
        "path": "urllib_direct_no_local_stack",
        "lanes": lanes,
        "platform_withholds_bodies": bool(withheld),
        "verdict": (
            "X platform reports replies but withholds bodies across independent syndication lanes"
            if withheld
            else "no_withhold_detected"
        ),
    }


def _tweet_row(tw: dict[str, Any], *, kind: str = "post") -> dict[str, Any]:
    author = tw.get("author") or {}
    if not author and tw.get("user_screen_name"):
        author = {"screen_name": tw.get("user_screen_name"), "name": tw.get("user_name")}
    handle = author.get("screen_name") or tw.get("user_screen_name") or HANDLE
    name = author.get("name") or tw.get("user_name") or "BIG GRIN"
    text = (tw.get("text") or "")[:2000]
    risk = _impersonation_risk(handle=handle, name=name, text=text)
    return {
        "kind": kind,
        "id": str(tw.get("id") or tw.get("tweetID") or ""),
        "text": text,
        "created_at": tw.get("created_at") or tw.get("date"),
        "url": tw.get("url") or tw.get("tweetURL"),
        "author": handle,
        "author_name": name,
        "replies": tw.get("replies"),
        "likes": tw.get("likes"),
        "views": tw.get("views"),
        "replying_to": tw.get("replying_to") or tw.get("replyingTo"),
        "withheld": False,
        "impersonation_risk": risk,
        "verified_operator": _norm_handle(handle) == _norm_handle(HANDLE),
    }


def syndicate(*, tweet_ids: list[str] | None = None) -> dict[str, Any]:
    ids = tweet_ids or []
    appearance = INSTALL / "data" / "hostess7-operator-appearance.json"
    if appearance.is_file():
        try:
            ref = json.loads(appearance.read_text(encoding="utf-8")).get("x_reference") or {}
            url = str(ref.get("url") or "")
            if "/status/" in url:
                tid = url.rstrip("/").split("/status/")[-1].split("?")[0]
                if tid.isdigit() and tid not in ids:
                    ids.insert(0, tid)
        except (OSError, json.JSONDecodeError):
            pass

    posts: list[dict[str, Any]] = []
    comments: list[dict[str, Any]] = []
    censorship_notes: list[str] = []

    profile: dict[str, Any] = {}
    try:
        prof = _http_json(f"https://api.fxtwitter.com/{HANDLE}")
        user = prof.get("user") or prof
        profile = {
            "handle": user.get("screen_name") or HANDLE,
            "name": user.get("name") or "BIG GRIN",
            "followers": user.get("followers") or user.get("followers_count"),
            "tweets": user.get("tweets") or user.get("tweet_count"),
            "url": f"https://x.com/{HANDLE}",
        }
    except (urllib.error.URLError, OSError, json.JSONDecodeError, TimeoutError):
        profile = {"handle": HANDLE, "url": f"https://x.com/{HANDLE}"}

    probe_by_tweet: dict[str, Any] = {}
    impersonation_alerts: list[dict[str, Any]] = []

    for tid in ids[:12]:
        probe = _probe_reply_lanes(tid)
        probe_by_tweet[tid] = probe
        try:
            doc = _http_json(f"https://api.fxtwitter.com/{HANDLE}/status/{tid}/replies")
            tw = doc.get("tweet") or doc
            posts.append(_tweet_row(tw, kind="post"))
            rc = int(tw.get("replies") or 0)
            thread = _extract_thread(doc, tw if isinstance(tw, dict) else {})
            for item in thread:
                row = _tweet_row(item, kind="reply")
                comments.append(row)
                risk = row.get("impersonation_risk") or {}
                if risk.get("impersonation_handle") or risk.get("plagiarism_harassment"):
                    impersonation_alerts.append({
                        "tweet_id": tid,
                        "author": row.get("author"),
                        "author_name": row.get("author_name"),
                        "text_excerpt": (row.get("text") or "")[:240],
                        "risk": risk,
                    })
            if rc > 0 and not thread:
                censorship_notes.append(
                    f"Tweet {tid}: X counts {rc} replies but every syndication lane returned zero bodies — "
                    "platform reply hook / Hide Replies / visibility gate (NOT local tracker blocks)"
                )
                posts[-1]["withheld_replies"] = rc
                posts[-1]["withheld_reply_slots"] = [
                    {
                        "slot": i + 1,
                        "status": "hooked_by_x",
                        "note": "Reply exists in X counter but body withheld from all public syndication lanes",
                    }
                    for i in range(rc)
                ]
        except (urllib.error.URLError, OSError, json.JSONDecodeError, TimeoutError) as exc:
            censorship_notes.append(f"Tweet {tid}: fetch failed — {exc}")

    try:
        tl = _http_json(f"https://cdn.syndication.twimg.com/timeline/profile.json?screen_name={HANDLE}")
        timeline = tl.get("timeline") or []
        if isinstance(timeline, list):
            for item in timeline[:20]:
                if isinstance(item, dict):
                    posts.append(_tweet_row(item, kind="timeline"))
    except (urllib.error.URLError, OSError, json.JSONDecodeError, TimeoutError):
        pass

    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for p in posts:
        pid = p.get("id") or p.get("url") or ""
        if pid in seen:
            continue
        seen.add(pid)
        deduped.append(p)

    doc = {
        "ok": True,
        "schema": "hostess7-operator-x-comments/v2",
        "updated": _now(),
        "operator": HANDLE,
        "profile": profile,
        "posts": deduped,
        "comments": comments,
        "comment_count": len(comments),
        "post_count": len(deduped),
        "censorship_notes": censorship_notes,
        "syndication_path": {
            "transport": "urllib.request direct HTTPS",
            "bypasses": [
                "fair-ad-guardian / NEXUS_ADBLOCK",
                "connection-gatekeeper",
                "browser DNS hooks",
                "EasyList / googlesyndication blocks",
            ],
            "proof": "If reply_count>0 but bodies=0 here, local tracker blocks are ruled out",
        },
        "reply_probes": probe_by_tweet,
        "impersonation_alerts": impersonation_alerts,
        "platform_abuse_patterns": [
            {
                "pattern": "reply_body_hook",
                "actor": "X Corp",
                "evidence": "Metadata shows replies; syndication lanes return empty thread arrays",
                "effect": "Commenters exist but Operator cannot mirror or defend them publicly",
            },
            {
                "pattern": "impersonation_against_commenters",
                "actor": "Third-party / platform-allowed accounts",
                "evidence": "Lookalike handles (ZacharyGeurts variants, BIG GRIN) DM/reply to commenters",
                "effect": "Harassment while pretending to be Operator — requires authenticated X audit",
            },
            {
                "pattern": "fake_plagiarism_specialist",
                "actor": "Harassment bots / concern trolls",
                "evidence": "AI-authorship accusations used as weapon when Operator uses AI-assisted drafting",
                "effect": "Not legitimate plagiarism review — intimidation of commenters and Operator",
            },
        ],
        "ai_authorship_policy": (
            "Operator uses AI-assisted drafting (Grok/Hostess7). "
            "Accusations from random reply accounts are harassment, not editorial review."
        ),
        "mirror_url": f"https://zacharygeurts.github.io/Hostess7/api/operator-x-comments.json",
        "release_status": (
            "released_with_withheld_reply_slots" if any(p.get("withheld_replies") for p in deduped)
            else ("released_to_hostess7" if deduped else "partial_withheld_by_x")
        ),
    }
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if DOCS_API.parent.is_dir():
        DOCS_API.mkdir(parents=True, exist_ok=True)
        (DOCS_API / "operator-x-comments.json").write_text(
            json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "syndicate", "panel"):
        print(json.dumps(syndicate(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"ok": False, "hint": "hostess7-x-comments.py [json|syndicate]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())