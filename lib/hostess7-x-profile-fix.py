#!/usr/bin/env python3
"""X profile censorship fix — @ZacharyGeurts shows 'hasn't posted' with 6855 tweets. Rip it."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "hostess7-x-profile-fix-doctrine.json"
PANEL = STATE / "hostess7-x-profile-fix-panel.json"
CACHE = STATE / "hostess7-x-profile-fix-cache.json"
X_COMMENTS_CACHE = STATE / "operator-x-comments-cache.json"
DOCS_API = Path(os.environ.get("HOSTESS7_ROOT", INSTALL / "Hostess7")) / "docs" / "api"
HANDLE = os.environ.get("OPERATOR_X_HANDLE", "ZacharyGeurts")
UA = "Hostess7-XProfileFix/1.0 (+https://zacharygeurts.github.io/Hostess7/x-profile/)"
TIMEOUT = int(os.environ.get("NEXUS_X_HTTP_TIMEOUT", "16"))
MAX_POSTS = int(os.environ.get("HOSTESS7_X_PROFILE_MAX", "40") or "40")

LIE_RE = re.compile(r"hasn.t posted", re.I)
TWEET_COUNT_RE = re.compile(r"tweets:(\d+)", re.I)
STATUS_ID_RE = re.compile(r"/status/(\d{15,22})")


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


def _probe_profile_html() -> dict[str, Any]:
    url = f"https://x.com/{HANDLE}"
    row: dict[str, Any] = {"lane": "x_profile_html", "url": url, "ok": False}
    status, body, _ = _http(url, accept="text/html")
    row["http_status"] = status
    if status < 200 or status >= 300 or not body:
        row["error"] = body[:160] if body else "fetch_failed"
        return row
    row["ok"] = True
    row["bytes"] = len(body)
    row["shows_hasnt_posted_lie"] = bool(LIE_RE.search(body))
    ids = list(dict.fromkeys(STATUS_ID_RE.findall(body)))
    row["status_ids_in_html"] = len(ids)
    row["timeline_empty_in_html"] = len(ids) == 0
    m = TWEET_COUNT_RE.search(body)
    row["tweet_count_in_payload"] = int(m.group(1)) if m else None
    row["censorship_barrier"] = bool(
        row["shows_hasnt_posted_lie"]
        and row["timeline_empty_in_html"]
        and (row.get("tweet_count_in_payload") or 0) > 0
    )
    if row["censorship_barrier"]:
        row["barrier"] = "logged_out_profile_timeline_empty"
        row["verdict"] = (
            f"X lies: shows 'hasn't posted' while payload reports "
            f"{row['tweet_count_in_payload']} tweets and zero timeline IDs"
        )
    return row


def _probe_user_meta() -> dict[str, Any]:
    lanes: list[dict[str, Any]] = []
    for label, url in (
        ("fxtwitter_user", f"https://api.fxtwitter.com/{HANDLE}"),
        ("vxtwitter_user", f"https://api.vxtwitter.com/{HANDLE}"),
    ):
        row: dict[str, Any] = {"lane": label, "url": url, "ok": False}
        try:
            doc = _http_json(url)
            row["ok"] = True
            user = doc.get("user") or doc
            row["tweet_count"] = user.get("tweets") or user.get("tweet_count") or user.get("statuses_count")
            row["followers"] = user.get("followers") or user.get("followers_count")
            row["name"] = user.get("name")
            row["verified"] = (user.get("verification") or {}).get("verified") if isinstance(user.get("verification"), dict) else user.get("verified")
        except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError, TimeoutError, OSError) as exc:
            row["error"] = str(exc)[:160]
        lanes.append(row)
    best = next((l for l in lanes if l.get("ok")), lanes[0] if lanes else {})
    return {"lanes": lanes, "tweet_count": best.get("tweet_count"), "ok": any(l.get("ok") for l in lanes)}


def _nitter_rss_urls() -> list[str]:
    doc = doctrine()
    seeds = [f"https://nitter.net/{HANDLE}/rss"]
    for lane in doc.get("timeline_lanes") or []:
        u = str(lane.get("url") or "")
        if "nitter" in u and "{handle}" in u:
            seeds.append(u.replace("{handle}", HANDLE))
    # dedupe preserve order
    out: list[str] = []
    seen: set[str] = set()
    for u in seeds:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def _fetch_nitter_rss() -> dict[str, Any]:
    out: dict[str, Any] = {"lane": "nitter_rss", "ok": False, "posts": [], "tweet_ids": []}
    for url in _nitter_rss_urls():
        row: dict[str, Any] = {"url": url, "ok": False}
        status, body, _ = _http(url, accept="application/rss+xml,*/*")
        row["http_status"] = status
        if status != 200 or not body.strip():
            row["error"] = body[:120] if body else "empty"
            out.setdefault("attempts", []).append(row)
            continue
        ids = list(dict.fromkeys(re.findall(rf"/{HANDLE}/status/(\d+)", body, re.I)))
        titles = re.findall(r"<title><!\[CDATA\[(.*?)\]\]></title>", body, re.S)
        posts: list[dict[str, Any]] = []
        for i, tid in enumerate(ids):
            text = titles[i + 1] if i + 1 < len(titles) else (titles[i] if i < len(titles) else "")
            posts.append({
                "id": tid,
                "text": text[:2000],
                "url": f"https://x.com/{HANDLE}/status/{tid}",
                "source": "nitter_rss",
                "rss_url": url,
            })
        row["ok"] = True
        row["id_count"] = len(ids)
        out["attempts"] = out.get("attempts", []) + [row]
        if len(ids) > len(out.get("tweet_ids") or []):
            out["ok"] = True
            out["tweet_ids"] = ids
            out["posts"] = posts
            out["rss_url"] = url
        if out["ok"]:
            break
    return out


def _syndicate_tweet(tid: str) -> dict[str, Any]:
    row: dict[str, Any] = {"id": tid, "ok": False}
    for label, url in (
        ("fxtwitter", f"https://api.fxtwitter.com/{HANDLE}/status/{tid}"),
        ("vxtwitter", f"https://api.vxtwitter.com/{HANDLE}/status/{tid}"),
    ):
        try:
            doc = _http_json(url)
            tw = doc.get("tweet") or doc
            if not isinstance(tw, dict):
                continue
            row.update({
                "ok": True,
                "lane": label,
                "text": (tw.get("text") or "")[:2000],
                "created_at": tw.get("created_at") or tw.get("date"),
                "url": tw.get("url") or f"https://x.com/{HANDLE}/status/{tid}",
                "author": (tw.get("author") or {}).get("screen_name") or HANDLE,
                "author_name": (tw.get("author") or {}).get("name") or "BIG GRIN",
                "replies": tw.get("replies"),
                "likes": tw.get("likes"),
                "views": tw.get("views"),
                "media": tw.get("media"),
            })
            return row
        except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError, TimeoutError, OSError):
            continue
    row["error"] = "syndication_failed"
    return row


def _probe_syndication_timeline() -> dict[str, Any]:
    url = (
        f"https://syndication.twitter.com/srv/timeline-profile/screen-name/{HANDLE}"
        "?showReplies=false&showHeader=true&maxHeight=1200"
    )
    row: dict[str, Any] = {"lane": "syndication_profile", "url": url, "ok": False}
    status, body, _ = _http(url, accept="application/json")
    row["http_status"] = status
    if status == 429:
        row["barrier"] = "rate_limit"
        row["censorship_barrier"] = True
        return row
    if status < 200 or status >= 300:
        row["error"] = body[:160]
        return row
    try:
        doc = json.loads(body)
        tl = doc.get("timeline") or []
        row["ok"] = True
        row["timeline_entries"] = len(tl) if isinstance(tl, list) else 0
        if isinstance(tl, list):
            row["tweet_ids"] = [
                str(t.get("tweet_id") or t.get("id") or "") for t in tl if isinstance(t, dict)
            ]
    except json.JSONDecodeError:
        row["error"] = "invalid_json"
    return row


def _merge_into_x_comments(profile_doc: dict[str, Any]) -> dict[str, Any]:
    py = INSTALL / "lib" / "hostess7-x-comments.py"
    if not py.is_file():
        return {"ok": False, "skipped": "x_comments_missing"}
    try:
        spec = importlib.util.spec_from_file_location("x_comments_merge", py)
        if not spec or not spec.loader:
            return {"ok": False, "skipped": "load_failed"}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        ids = [str(p.get("id") or "") for p in profile_doc.get("posts") or [] if p.get("id")]
        if hasattr(mod, "syndicate"):
            merged = mod.syndicate(tweet_ids=ids, open_all=True)
            return {"ok": True, "merged": True, "post_count": merged.get("post_count"), "ids": len(ids)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:160]}
    return {"ok": False, "skipped": "syndicate_missing"}


def repair(*, export: bool = True) -> dict[str, Any]:
    doc_policy = doctrine()
    html_probe = _probe_profile_html()
    user_meta = _probe_user_meta()
    syndication = _probe_syndication_timeline()
    rss = _fetch_nitter_rss()

    tweet_ids: list[str] = list(rss.get("tweet_ids") or [])
    if syndication.get("tweet_ids"):
        for tid in syndication["tweet_ids"]:
            if tid and tid not in tweet_ids:
                tweet_ids.append(tid)

    # appearance seed
    appearance = INSTALL / "data" / "hostess7-operator-appearance.json"
    if appearance.is_file():
        try:
            ref = json.loads(appearance.read_text(encoding="utf-8")).get("x_reference") or {}
            url = str(ref.get("url") or "")
            if "/status/" in url:
                seed = url.rstrip("/").split("/status/")[-1].split("?")[0]
                if seed.isdigit() and seed not in tweet_ids:
                    tweet_ids.insert(0, seed)
        except (OSError, json.JSONDecodeError):
            pass

    tweet_ids = tweet_ids[:MAX_POSTS]
    posts: list[dict[str, Any]] = []
    rss_by_id = {str(p.get("id") or ""): p for p in rss.get("posts") or []}

    workers = min(12, max(2, len(tweet_ids) or 2))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(_syndicate_tweet, tid): tid for tid in tweet_ids}
        for fut in as_completed(futs):
            row = fut.result()
            tid = str(row.get("id") or "")
            if not row.get("ok"):
                seed = rss_by_id.get(tid) or {}
                if seed.get("text"):
                    posts.append({
                        "kind": "post",
                        "id": tid,
                        "text": seed.get("text"),
                        "url": seed.get("url") or f"https://x.com/{HANDLE}/status/{tid}",
                        "author": HANDLE,
                        "author_name": "BIG GRIN",
                        "source": "nitter_rss_fallback",
                        "verified_operator": True,
                    })
                continue
            posts.append({
                "kind": "post",
                "id": tid,
                "text": row.get("text") or "",
                "created_at": row.get("created_at"),
                "url": row.get("url"),
                "author": row.get("author") or HANDLE,
                "author_name": row.get("author_name") or "BIG GRIN",
                "replies": row.get("replies"),
                "likes": row.get("likes"),
                "views": row.get("views"),
                "source": row.get("lane") or "syndication",
                "verified_operator": True,
            })

    posts.sort(key=lambda p: int(p.get("id") or "0"), reverse=True)
    tweet_count = (
        html_probe.get("tweet_count_in_payload")
        or user_meta.get("tweet_count")
        or (rss.get("posts") and len(rss.get("posts") or []))
        or 0
    )
    censored = bool(html_probe.get("censorship_barrier"))
    barriers: list[dict[str, Any]] = []
    if censored:
        barriers.append({
            "id": "logged_out_profile_timeline_empty",
            "actor": "X Corp",
            "lie": "hasn't posted",
            "truth_tweet_count": tweet_count,
            "mirrored_posts": len(posts),
            "revealed": True,
        })
    if syndication.get("barrier") == "rate_limit":
        barriers.append({
            "id": "syndication_rate_limit",
            "actor": "X Corp",
            "http_status": 429,
            "revealed": True,
        })

    out: dict[str, Any] = {
        "ok": True,
        "schema": "hostess7-x-profile-fix/v1",
        "updated": _now(),
        "motto": doc_policy.get("motto"),
        "title": doc_policy.get("title"),
        "operator": HANDLE,
        "profile_url": doc_policy.get("profile_url") or f"https://x.com/{HANDLE}",
        "censorship": {
            "detected": censored,
            "lie_text": "hasn't posted",
            "tweet_count_truth": tweet_count,
            "timeline_ids_in_x_html": html_probe.get("status_ids_in_html"),
            "barriers": barriers,
            "verdict": (
                f"X censored @{HANDLE} profile — shows empty timeline while {tweet_count} posts exist. "
                f"Mirrored {len(posts)} posts to sovereign cache."
                if censored
                else f"Profile reachable — mirrored {len(posts)} posts"
            ),
        },
        "probes": {
            "profile_html": html_probe,
            "user_meta": user_meta,
            "syndication_timeline": syndication,
            "nitter_rss": {k: v for k, v in rss.items() if k != "posts"},
        },
        "posts": posts,
        "post_count": len(posts),
        "tweet_ids_seeded": len(tweet_ids),
        "hosted": doc_policy.get("hosted") or {},
        "mirror_url": f"https://zacharygeurts.github.io/Hostess7/x-profile/",
        "api": doc_policy.get("api") or "/api/hostess7-x-profile-fix",
        "release_status": "profile_timeline_ripped" if posts else "barrier_revealed_no_posts",
    }

    merge = _merge_into_x_comments(out)
    out["x_comments_merge"] = merge

    _save(CACHE, out)
    panel_doc = {**out, "schema": "hostess7-x-profile-fix-panel/v1", "witness": {"ok": True, "detail": out["censorship"]["verdict"]}}
    _save(PANEL, panel_doc)

    if export and DOCS_API.parent.is_dir():
        DOCS_API.mkdir(parents=True, exist_ok=True)
        (DOCS_API / "hostess7-x-profile-fix.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    return out


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "repair").strip().lower()
    if cmd in ("repair", "rip", "fix", "clear"):
        print(json.dumps(repair(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "json":
        cached = _load(CACHE) or _load(PANEL)
        if cached:
            print(json.dumps(cached, ensure_ascii=False, indent=2))
            return 0
        print(json.dumps(repair(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "explain":
        print(json.dumps({
            "ok": True,
            "doctrine": doctrine(),
            "usage": "hostess7-x-profile-fix.py [repair|json|explain]",
            "hosted": "https://zacharygeurts.github.io/Hostess7/x-profile/",
        }, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"ok": False, "hint": "hostess7-x-profile-fix.py [repair|json|explain]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())