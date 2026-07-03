#!/usr/bin/env python3
"""Operator X comments — syndicate recoverable posts/replies to Hostess7 pages."""
from __future__ import annotations

import json
import os
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
UA = "Hostess7-XComments/1.0"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _http_json(url: str) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def _tweet_row(tw: dict[str, Any], *, kind: str = "post") -> dict[str, Any]:
    author = tw.get("author") or {}
    if not author and tw.get("user_screen_name"):
        author = {"screen_name": tw.get("user_screen_name"), "name": tw.get("user_name")}
    return {
        "kind": kind,
        "id": str(tw.get("id") or tw.get("tweetID") or ""),
        "text": (tw.get("text") or "")[:2000],
        "created_at": tw.get("created_at") or tw.get("date"),
        "url": tw.get("url") or tw.get("tweetURL"),
        "author": author.get("screen_name") or HANDLE,
        "author_name": author.get("name") or "BIG GRIN",
        "replies": tw.get("replies"),
        "likes": tw.get("likes"),
        "views": tw.get("views"),
        "replying_to": tw.get("replying_to") or tw.get("replyingTo"),
        "withheld": False,
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

    for tid in ids[:12]:
        try:
            doc = _http_json(f"https://api.fxtwitter.com/{HANDLE}/status/{tid}/replies")
            tw = doc.get("tweet") or doc
            posts.append(_tweet_row(tw, kind="post"))
            rc = int(tw.get("replies") or 0)
            thread = doc.get("reply_thread") or doc.get("thread") or []
            if isinstance(thread, list):
                for item in thread:
                    if isinstance(item, dict):
                        comments.append(_tweet_row(item, kind="reply"))
            if rc > 0 and not thread:
                censorship_notes.append(
                    f"Tweet {tid}: X reports {rc} replies but syndication withheld reply bodies — platform-side suppression"
                )
                posts[-1]["withheld_replies"] = rc
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
        "schema": "hostess7-operator-x-comments/v1",
        "updated": _now(),
        "operator": HANDLE,
        "profile": profile,
        "posts": deduped,
        "comments": comments,
        "comment_count": len(comments),
        "post_count": len(deduped),
        "censorship_notes": censorship_notes,
        "mirror_url": f"https://zacharygeurts.github.io/Hostess7/api/operator-x-comments.json",
        "release_status": "released_to_hostess7" if deduped else "partial_withheld_by_x",
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