#!/usr/bin/env python3
"""X straight shot — direct x.com/api.x.com lanes, reveal censorship, pull on resist."""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "hostess7-x-straight-shot-doctrine.json"
PANEL = STATE / "hostess7-x-straight-shot-panel.json"
CACHE = STATE / "operator-x-straight-shot-cache.json"
X_CACHE = STATE / "operator-x-comments-cache.json"
DOCS_API = Path(os.environ.get("HOSTESS7_ROOT", INSTALL / "Hostess7")) / "docs" / "api"
HANDLE = os.environ.get("OPERATOR_X_HANDLE", "ZacharyGeurts")
PROBE_TWEET = os.environ.get("OPERATOR_X_PROBE_TWEET", "2061509192746217772")
UA = "Hostess7-XStraightShot/1.0 (+https://zacharygeurts.github.io/Hostess7/x-straight-shot/)"
TIMEOUT = int(os.environ.get("NEXUS_X_HTTP_TIMEOUT", "14"))

NEXT_DATA_RE = re.compile(r'<script[^>]*id="__NEXT_DATA__"[^>]*>([^<]+)</script>', re.I)
REPLY_COUNT_RE = re.compile(r'"reply_count"\s*:\s*(\d+)', re.I)
TEXT_RE = re.compile(r'"full_text"\s*:\s*"((?:\\.|[^"\\])*)"', re.I)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {})


def _http(url: str, *, accept: str = "*/*") -> tuple[int, str, dict[str, str]]:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": UA, "Accept": accept, "Accept-Language": "en-US,en;q=0.9"},
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, body, dict(resp.headers)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        return exc.code, raw, dict(exc.headers or {})
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return 0, str(exc), {}


def _http_json(url: str) -> Any:
    status, body, _ = _http(url, accept="application/json")
    if status < 200 or status >= 300:
        raise urllib.error.HTTPError(url, status, body[:120], None, None)
    return json.loads(body)


def _decode_json_str(s: str) -> str:
    try:
        return json.loads(f'"{s}"')
    except json.JSONDecodeError:
        return s.replace("\\n", "\n").replace("\\\"", '"')


def _extract_thread_from_doc(doc: Any, tw: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("reply_thread", "thread", "replies_list", "conversation", "replies"):
        val = doc.get(key) if isinstance(doc, dict) else None
        if val is None and isinstance(tw, dict):
            val = tw.get(key)
        if isinstance(val, list) and val:
            return [x for x in val if isinstance(x, dict)]
    return []


def _lane_x_direct_html(tid: str) -> dict[str, Any]:
    url = f"https://x.com/{HANDLE}/status/{tid}"
    row: dict[str, Any] = {
        "lane": "x_direct_html",
        "url": url,
        "tier": 1,
        "middleman": False,
        "ok": False,
    }
    status, body, headers = _http(url, accept="text/html")
    row["http_status"] = status
    if status in (401, 403, 429):
        row["barrier"] = "auth_gate" if status in (401, 403) else "rate_limit"
        row["censorship_barrier"] = True
        return row
    if status < 200 or status >= 300 or not body:
        row["error"] = body[:160] if body else "fetch_failed"
        return row
    row["ok"] = True
    row["bytes"] = len(body)
    m = NEXT_DATA_RE.search(body)
    if m:
        try:
            nd = json.loads(m.group(1))
            row["next_data"] = True
            blob = json.dumps(nd)
            rc = REPLY_COUNT_RE.search(blob)
            if rc:
                row["reply_count"] = int(rc.group(1))
            texts = [_decode_json_str(t) for t in TEXT_RE.findall(blob)]
            row["text_samples"] = [t[:200] for t in texts[:5] if t.strip()]
            row["reply_bodies"] = max(0, len(texts) - 1)
        except json.JSONDecodeError:
            row["next_data"] = False
    if "login" in body.lower() and "sign in" in body.lower():
        row["barrier"] = "logged_out_wall"
        row["censorship_barrier"] = True
    rc = row.get("reply_count")
    bodies = int(row.get("reply_bodies") or 0)
    if rc and int(rc) > 0 and bodies == 0:
        row["barrier"] = "reply_body_hook"
        row["censorship_barrier"] = True
        row["reply_bodies_withheld"] = True
    row["cache_control"] = headers.get("Cache-Control") or headers.get("cache-control")
    return row


def _lane_x_oembed(tid: str) -> dict[str, Any]:
    tweet_url = f"https://x.com/{HANDLE}/status/{tid}"
    q = urllib.parse.urlencode({"url": tweet_url, "omit_script": "1", "dnt": "true"})
    url = f"https://publish.twitter.com/oembed?{q}"
    row: dict[str, Any] = {
        "lane": "x_oembed",
        "url": url,
        "tier": 1,
        "middleman": False,
        "ok": False,
    }
    try:
        doc = _http_json(url)
        row["ok"] = True
        row["author_name"] = doc.get("author_name")
        row["html_len"] = len(doc.get("html") or "")
        row["text_hint"] = unescape(re.sub(r"<[^>]+>", " ", doc.get("html") or "")).strip()[:240]
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError, OSError) as exc:
        row["error"] = str(exc)[:160]
        if "401" in str(exc) or "403" in str(exc):
            row["barrier"] = "auth_gate"
            row["censorship_barrier"] = True
    return row


def _lane_pull(label: str, url: str) -> dict[str, Any]:
    row: dict[str, Any] = {
        "lane": label,
        "url": url,
        "tier": 3,
        "middleman": True,
        "extraction_only": True,
        "ok": False,
    }
    try:
        doc = _http_json(url)
        row["ok"] = True
        tw = doc.get("tweet") or doc
        if isinstance(tw, dict):
            row["reply_count"] = tw.get("replies")
            row["text"] = (tw.get("text") or "")[:240]
        thread = _extract_thread_from_doc(doc, tw if isinstance(tw, dict) else {})
        row["reply_bodies"] = len(thread)
        rc = int((tw.get("replies") if isinstance(tw, dict) else 0) or 0)
        row["reply_bodies_withheld"] = bool(rc > 0 and not thread)
        if thread:
            row["pulled_thread"] = [
                {
                    "author": (t.get("author") or {}).get("screen_name") or t.get("user_screen_name"),
                    "text": (t.get("text") or "")[:500],
                }
                for t in thread[:20]
                if isinstance(t, dict)
            ]
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError, TimeoutError, OSError) as exc:
        row["error"] = str(exc)[:160]
    return row


def _barriers_from_lanes(lanes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for lane in lanes:
        b = lane.get("barrier")
        if not b or b in seen:
            continue
        seen.add(b)
        out.append({
            "id": b,
            "lane": lane.get("lane"),
            "url": lane.get("url"),
            "http_status": lane.get("http_status"),
            "reply_count": lane.get("reply_count"),
            "reply_bodies": lane.get("reply_bodies"),
            "revealed": True,
        })
    return out


def _pull_withheld_from_cache(tid: str) -> list[dict[str, Any]]:
    doc = _load(X_CACHE, {})
    pulled: list[dict[str, Any]] = []
    for post in doc.get("posts") or []:
        if str(post.get("id") or "") != str(tid):
            continue
        for slot in post.get("withheld_reply_slots") or []:
            pulled.append({
                "kind": "pulled_withheld_slot",
                "parent_id": tid,
                "slot": slot.get("slot"),
                "status": slot.get("status") or "hooked_by_x",
                "text": slot.get("note") or "Reply body withheld by X — slot pulled into sovereign mirror",
                "source": "operator-x-comments-cache",
                "released": True,
            })
        for c in doc.get("comments") or []:
            if str(c.get("parent_id") or "") == str(tid) or c.get("replying_to"):
                pulled.append({**c, "pulled": True, "source": "cache_comments"})
    return pulled


def straight_shot(*, tweet_ids: list[str] | None = None, export: bool = True) -> dict[str, Any]:
    doc_policy = doctrine()
    ids = list(tweet_ids or [])
    if PROBE_TWEET and PROBE_TWEET not in ids:
        ids.insert(0, PROBE_TWEET)

    all_lanes: list[dict[str, Any]] = []
    by_tweet: dict[str, Any] = {}
    pulled_all: list[dict[str, Any]] = []
    barriers_all: list[dict[str, Any]] = []

    for tid in ids[:12]:
        primary_urls = [
            ("x_direct_html", f"https://x.com/{HANDLE}/status/{tid}"),
            ("x_oembed", f"https://publish.twitter.com/oembed?{urllib.parse.urlencode({'url': f'https://x.com/{HANDLE}/status/{tid}', 'omit_script': '1'})}"),
        ]
        pull_urls = [
            ("pull_fx_replies", f"https://api.fxtwitter.com/{HANDLE}/status/{tid}/replies"),
            ("pull_vx", f"https://api.vxtwitter.com/{HANDLE}/status/{tid}"),
        ]
        lanes: list[dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=6) as pool:
            futs = {
                pool.submit(_lane_x_direct_html, tid): "x_direct_html",
                pool.submit(_lane_x_oembed, tid): "x_oembed",
            }
            for fut in as_completed(futs):
                lanes.append(fut.result())

        direct_ok = any(l.get("ok") and not l.get("reply_bodies_withheld") for l in lanes if l.get("tier") == 1)
        resist = any(l.get("censorship_barrier") or l.get("reply_bodies_withheld") for l in lanes)
        if resist or not direct_ok:
            with ThreadPoolExecutor(max_workers=4) as pool:
                futs2 = {pool.submit(_lane_pull, label, url): label for label, url in pull_urls}
                for fut in as_completed(futs2):
                    lanes.append(fut.result())

        pulled = _pull_withheld_from_cache(tid)
        for row in lanes:
            for pt in row.get("pulled_thread") or []:
                pulled.append({**pt, "kind": "pulled_reply", "parent_id": tid, "released": True})
        pulled_all.extend(pulled)

        barriers = _barriers_from_lanes(lanes)
        barriers_all.extend(barriers)

        by_tweet[tid] = {
            "tweet_id": tid,
            "direct_url": f"https://x.com/{HANDLE}/status/{tid}",
            "lanes": lanes,
            "barriers_revealed": barriers,
            "resisted": resist,
            "pulled_count": len(pulled),
            "verdict": (
                "X resisted — bodies pulled via extraction lanes + sovereign cache"
                if resist and pulled
                else ("X resisted — barriers revealed, partial pull" if resist else "direct_lane_ok")
            ),
        }
        all_lanes.extend(lanes)

    out = {
        "ok": True,
        "schema": "hostess7-x-straight-shot/v1",
        "updated": _now(),
        "motto": doc_policy.get("motto"),
        "operator": HANDLE,
        "policy": doc_policy.get("policy"),
        "no_middlemen_primary": True,
        "primary_hosts": doc_policy.get("policy", {}).get("primary_hosts"),
        "gone_middlemen": doc_policy.get("policy", {}).get("gone_hosts"),
        "tweets": by_tweet,
        "censorship_barriers_revealed": barriers_all,
        "barrier_count": len(barriers_all),
        "pulled": pulled_all,
        "pulled_count": len(pulled_all),
        "release_status": "pulled_on_resist" if pulled_all else ("barriers_revealed" if barriers_all else "direct_ok"),
        "verdict_summary": (
            "Primary: direct x.com/oembed. Barriers revealed where X withholds. "
            "Extraction lanes + sovereign cache pull data when platform resists."
        ),
        "hosted": "https://zacharygeurts.github.io/Hostess7/x-straight-shot/",
        "mirror_url": "https://zacharygeurts.github.io/Hostess7/api/hostess7-x-straight-shot.json",
        "api": "/api/hostess7-x-straight-shot",
    }
    _save(CACHE, out)
    _save(PANEL, out)
    if export and DOCS_API.parent.is_dir():
        DOCS_API.mkdir(parents=True, exist_ok=True)
        (DOCS_API / "hostess7-x-straight-shot.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return out


def rip_barriers(*, export: bool = True) -> dict[str, Any]:
    """Reveal barriers, pull withheld data, merge into sovereign operator-x-comments cache."""
    shot = straight_shot(export=False)
    xdoc = _load(X_CACHE, {})
    posts = list(xdoc.get("posts") or [])
    comments = list(xdoc.get("comments") or [])
    censorship_notes = list(xdoc.get("censorship_notes") or [])
    seen = {str(c.get("id") or "") for c in comments}

    for tid, block in (shot.get("tweets") or {}).items():
        for barrier in block.get("barriers_revealed") or []:
            note = (
                f"Barrier ripped [{barrier.get('id')}]: tweet {tid} — "
                f"lane={barrier.get('lane')} status={barrier.get('http_status')} "
                f"replies={barrier.get('reply_count')} bodies={barrier.get('reply_bodies')}"
            )
            if note not in censorship_notes:
                censorship_notes.append(note)

    freed = 0
    for row in shot.get("pulled") or []:
        if row.get("kind") == "pulled_reply":
            cid = f"{row.get('parent_id')}-pulled-{freed}"
            if cid in seen:
                continue
            comments.append({
                "kind": "reply_pulled",
                "id": cid,
                "parent_id": row.get("parent_id"),
                "text": row.get("text") or "",
                "author": row.get("author") or "unknown",
                "author_name": row.get("author") or "Recovered",
                "withheld": False,
                "released": True,
                "barrier_ripped": True,
                "source": "straight_shot_pull",
            })
            seen.add(cid)
            freed += 1
        elif row.get("kind") in ("pulled_withheld_slot", "reply_withheld_open"):
            cid = str(row.get("id") or f"pulled-slot-{freed}")
            if cid in seen:
                continue
            comments.append({
                **row,
                "kind": "reply_withheld_open",
                "opened": True,
                "released": True,
                "barrier_ripped": True,
                "delay_killed": True,
            })
            seen.add(cid)
            freed += 1

    xdoc.update({
        "ok": True,
        "updated": _now(),
        "straight_shot": {
            "barrier_count": shot.get("barrier_count"),
            "pulled_count": shot.get("pulled_count"),
            "release_status": shot.get("release_status"),
        },
        "censorship_barriers_revealed": shot.get("censorship_barriers_revealed"),
        "censorship_notes": censorship_notes,
        "comments": comments,
        "comment_count": len(comments),
        "posts": posts,
        "barriers_ripped": True,
        "info_freed": freed > 0 or bool(shot.get("barrier_count")),
        "release_status": "barriers_ripped_info_freed" if freed else shot.get("release_status"),
        "no_middlemen_primary": True,
        "mirror_url": shot.get("mirror_url"),
    })
    X_CACHE.parent.mkdir(parents=True, exist_ok=True)
    X_CACHE.write_text(json.dumps(xdoc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if DOCS_API.parent.is_dir():
        (DOCS_API / "operator-x-comments.json").write_text(
            json.dumps(xdoc, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    out = {**shot, "barriers_ripped": True, "info_freed_count": freed, "operator_x_cache": str(X_CACHE)}
    _save(PANEL, out)
    if export and DOCS_API.parent.is_dir():
        (DOCS_API / "hostess7-x-straight-shot.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return out


def panel_json() -> dict[str, Any]:
    cached = _load(PANEL, {})
    if cached.get("schema"):
        return cached
    return straight_shot(export=True)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("rip", "free", "rip-barriers", "free-info"):
        print(json.dumps(rip_barriers(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("run", "pull", "shoot", "straight-shot"):
        print(json.dumps(straight_shot(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("json", "panel"):
        print(json.dumps(panel_json(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "explain":
        print(json.dumps(doctrine(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "hostess7-x-straight-shot.py [run|json|explain]",
        "api": "/api/hostess7-x-straight-shot",
        "hosted": "https://zacharygeurts.github.io/Hostess7/x-straight-shot/",
    }, ensure_ascii=False, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())