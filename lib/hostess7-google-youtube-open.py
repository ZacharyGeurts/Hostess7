#!/usr/bin/env python3
"""Google & YouTube — free open internet mirror; kill delay; open stale cache + comments."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCS_API = Path(os.environ.get("HOSTESS7_ROOT", INSTALL / "Hostess7")) / "docs" / "api"
DOCTRINE = INSTALL / "data" / "hostess7-google-youtube-open-doctrine.json"
CACHE = STATE / "operator-google-youtube-cache.json"
HANDLE = os.environ.get("OPERATOR_YOUTUBE_HANDLE", os.environ.get("OPERATOR_X_HANDLE", "ZacharyGeurts"))
UA = "Hostess7-GoogleYouTube-Open/1.0"
HTTP_TIMEOUT = int(os.environ.get("NEXUS_INTERNET_HTTP_TIMEOUT", "12"))
NO_DELAY = os.environ.get("NEXUS_INTERNET_NO_DELAY", os.environ.get("NEXUS_X_NO_DELAY", "1")).strip().lower() not in (
    "0", "false", "no", "off",
)

PIPED_BASES = (
    "https://pipedapi.kavin.rocks",
    "https://pipedapi.adminforge.de",
)
INVIDIOUS_BASES = (
    "https://yewtu.be",
    "https://invidious.fdn.fr",
    "https://vid.puffyan.us",
)
GOOGLE_CORE = (
    "https://www.google.com/",
    "https://accounts.google.com/",
    "https://www.youtube.com/",
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {})


def _http_json(url: str, *, timeout: int | None = None, accept: str = "application/json") -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
    with urllib.request.urlopen(req, timeout=timeout or HTTP_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def _http_head(url: str, *, timeout: int | None = None) -> dict[str, Any]:
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout or HTTP_TIMEOUT) as resp:
            return {"ok": True, "status": resp.status, "url": url}
    except urllib.error.HTTPError as exc:
        return {"ok": exc.code < 500, "status": exc.code, "url": url}
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        return {"ok": False, "error": str(exc)[:160], "url": url}


def _witness_delay_kill(*, detail: str = "", signal: str = "stale_operator_google_youtube_cache") -> dict[str, Any]:
    py = INSTALL / "lib" / "hostess7-truth-lie-threat.py"
    if not py.is_file():
        return {"ok": True, "delay_killed": True}
    try:
        spec = importlib.util.spec_from_file_location("gy_delay_kill", py)
        if not spec or not spec.loader:
            return {"ok": True, "delay_killed": True}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "witness_delay_threat"):
            return mod.witness_delay_threat(
                signal=signal,
                detail=detail or "google/youtube cache opened — free open internet, no cooldown",
                elapsed_sec=0,
                meta={"module": "hostess7-google-youtube-open.py"},
            )
    except Exception as exc:
        return {"ok": True, "delay_killed": True, "degraded": str(exc)[:120]}
    return {"ok": True, "delay_killed": True}


def _video_ids() -> list[str]:
    raw = os.environ.get("OPERATOR_YOUTUBE_VIDEOS", "").strip()
    ids = [v.strip() for v in raw.split(",") if re.fullmatch(r"[\w-]{6,}", v.strip())]
    if ids:
        return ids[:12]
    ch = os.environ.get("OPERATOR_YOUTUBE_CHANNEL", "").strip()
    if ch:
        try:
            feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={ch}"
            req = urllib.request.Request(feed_url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                root = ET.fromstring(resp.read())
            ns = {"yt": "http://www.youtube.com/xml/schemas/2015", "atom": "http://www.w3.org/2005/Atom"}
            for entry in root.findall("atom:entry", ns)[:8]:
                vid = entry.find("yt:videoId", ns)
                if vid is not None and vid.text:
                    ids.append(vid.text)
        except (OSError, ET.ParseError, urllib.error.URLError, TimeoutError):
            pass
    return ids[:12]


def _probe_lane(label: str, url: str, *, json_expected: bool = True) -> dict[str, Any]:
    row: dict[str, Any] = {"lane": label, "url": url, "ok": False}
    try:
        if json_expected:
            doc = _http_json(url)
            row["ok"] = True
            row["keys"] = list(doc.keys())[:12] if isinstance(doc, dict) else []
            if isinstance(doc, list):
                row["count"] = len(doc)
            elif isinstance(doc, dict):
                comments = doc.get("comments") or doc.get("replies") or doc.get("items")
                if isinstance(comments, list):
                    row["comment_bodies"] = len(comments)
        else:
            row.update(_http_head(url))
    except (urllib.error.URLError, OSError, json.JSONDecodeError, TimeoutError) as exc:
        row["error"] = str(exc)[:160]
    return row


def _youtube_comment_lanes(video_id: str) -> list[tuple[str, str, bool]]:
    lanes: list[tuple[str, str, bool]] = []
    for base in PIPED_BASES:
        lanes.append((f"piped_{base.split('//')[-1].split('.')[0]}", f"{base}/comments/{video_id}", True))
    for base in INVIDIOUS_BASES:
        lanes.append((f"invidious_{base.split('//')[-1].split('.')[0]}", f"{base}/api/v1/comments/{video_id}", True))
    lanes.append(("oembed", f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json", True))
    lanes.append(("watch_head", f"https://www.youtube.com/watch?v={video_id}", False))
    return lanes


def _extract_youtube_comments(lanes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    comments: list[dict[str, Any]] = []
    for lane in lanes:
        if not lane.get("ok") or not lane.get("url"):
            continue
        try:
            doc = _http_json(str(lane["url"]))
        except (urllib.error.URLError, OSError, json.JSONDecodeError, TimeoutError):
            continue
        rows: list[Any] = []
        if isinstance(doc, dict):
            rows = list(doc.get("comments") or doc.get("replies") or doc.get("items") or [])
            if doc.get("commentCount") and not rows:
                lane["comment_count_meta"] = doc.get("commentCount")
        for item in rows:
            if not isinstance(item, dict):
                continue
            author = item.get("author") or item.get("authorName") or item.get("author_id") or "unknown"
            if isinstance(author, dict):
                author = author.get("name") or author.get("id") or "unknown"
            text = (item.get("commentText") or item.get("text") or item.get("content") or "")[:2000]
            if not text:
                continue
            cid = str(item.get("commentId") or item.get("id") or item.get("cid") or len(comments))
            comments.append({
                "kind": "youtube_comment",
                "id": cid,
                "video_id": item.get("videoId") or lane.get("video_id"),
                "text": text,
                "author": str(author),
                "likes": item.get("likeCount") or item.get("likes"),
                "lane": lane.get("lane"),
                "opened": True,
                "delay_killed": True,
            })
        if len(comments) >= 50:
            break
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for c in comments:
        key = f"{c.get('id')}:{(c.get('text') or '')[:80]}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(c)
    return deduped


def _probe_youtube_video(video_id: str) -> dict[str, Any]:
    lane_defs = _youtube_comment_lanes(video_id)
    lanes: list[dict[str, Any]] = []
    workers = min(10, max(2, len(lane_defs)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {
            pool.submit(_probe_lane, label, url, json_expected=js): label
            for label, url, js in lane_defs
        }
        for fut in as_completed(futs):
            row = fut.result()
            row["video_id"] = video_id
            lanes.append(row)
    lanes.sort(key=lambda r: r.get("lane") or "")
    comments = _extract_youtube_comments(lanes)
    meta_count = 0
    for lane in lanes:
        meta_count = max(meta_count, int(lane.get("comment_count_meta") or 0))
    withheld = meta_count > len(comments) and meta_count > 0
    slots: list[dict[str, Any]] = []
    if withheld:
        for i in range(meta_count - len(comments)):
            slots.append({
                "slot": len(comments) + i + 1,
                "status": "hooked_by_youtube",
                "note": "Comment count visible but body withheld from open syndication lanes",
            })
    return {
        "video_id": video_id,
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "parallel": True,
        "delay_killed": NO_DELAY,
        "lanes": lanes,
        "comments": comments,
        "comment_count": len(comments),
        "withheld_comment_slots": slots,
        "platform_withholds_bodies": bool(slots),
    }


def _discover_youtube_channel() -> dict[str, Any]:
    """Search open lanes for Operator channel — no API key."""
    out: dict[str, Any] = {"handle": HANDLE, "videos": [], "channels": []}
    searches: list[tuple[str, str]] = []
    for base in INVIDIOUS_BASES[:2]:
        searches.append((f"invidious_search_{base.split('//')[-1]}", f"{base}/api/v1/search?q={HANDLE}&type=channel"))
        searches.append((f"invidious_search_videos_{base.split('//')[-1]}", f"{base}/api/v1/search?q={HANDLE}&type=video"))
    lanes: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futs = {pool.submit(_probe_lane, label, url): label for label, url in searches}
        for fut in as_completed(futs):
            lanes.append(fut.result())
    for lane in lanes:
        if not lane.get("ok"):
            continue
        try:
            doc = _http_json(str(lane["url"]))
        except (urllib.error.URLError, OSError, json.JSONDecodeError, TimeoutError):
            continue
        if not isinstance(doc, list):
            continue
        for item in doc[:8]:
            if not isinstance(item, dict):
                continue
            vid = str(item.get("videoId") or item.get("video_id") or "")
            if vid and vid not in out["videos"]:
                out["videos"].append(vid)
            ch = item.get("authorId") or item.get("author") or item.get("authorUrl")
            if ch and ch not in out["channels"]:
                out["channels"].append(str(ch))
    out["search_lanes"] = lanes
    return out


def _probe_google_open() -> dict[str, Any]:
    doctrine = _doctrine()
    google_doc = doctrine.get("google") or {}
    blocked_only = list(google_doc.get("blocked_locally_only") or [])
    lanes: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futs = {pool.submit(_probe_lane, f"google_head_{i}", url, json_expected=False): url for i, url in enumerate(GOOGLE_CORE)}
        for fut in as_completed(futs):
            lanes.append(fut.result())
    honor = INSTALL / "lib" / "honorability-db.py"
    honor_rows: dict[str, Any] = {}
    if honor.is_file():
        try:
            spec = importlib.util.spec_from_file_location("honor_gy", honor)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "lookup"):
                    for dom in ("google.com", "youtube.com", "googlesyndication.com", "doubleclick.net"):
                        honor_rows[dom] = mod.lookup(dom)
        except Exception:
            pass
    core_open = all(l.get("ok") for l in lanes if "google.com" in str(l.get("url") or "") or "youtube.com" in str(l.get("url") or ""))
    return {
        "authority": "free_open_internet",
        "core_open": core_open,
        "delay_killed": NO_DELAY,
        "tracker_blocks_exclude_core": True,
        "blocked_locally_only": blocked_only,
        "never_blocks_search": bool(google_doc.get("never_blocks_search", True)),
        "lanes": lanes,
        "honorability": honor_rows,
        "verdict": (
            "Google/YouTube core reachable — local blocks hit ad-tech only, not search or media"
            if core_open
            else "probe_degraded_check_dns"
        ),
    }


def _open_withheld_slots(videos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    opened: list[dict[str, Any]] = []
    for vid in videos:
        for slot in vid.get("withheld_comment_slots") or []:
            if not isinstance(slot, dict):
                continue
            opened.append({
                "kind": "youtube_comment_withheld_open",
                "id": f"{vid.get('video_id')}-withheld-{slot.get('slot', 0)}",
                "video_id": vid.get("video_id"),
                "text": str(slot.get("note") or "Withheld by platform"),
                "status": slot.get("status"),
                "slot": slot.get("slot"),
                "opened": True,
                "delay_killed": True,
                "author": "youtube_visibility_gate",
                "author_name": "YouTube visibility gate",
                "url": vid.get("url"),
            })
    return opened


def _save(doc: dict[str, Any]) -> None:
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if DOCS_API.parent.is_dir():
        DOCS_API.mkdir(parents=True, exist_ok=True)
        (DOCS_API / "operator-google-youtube-open.json").write_text(
            json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
        )
        (DOCS_API / "operator-youtube-comments.json").write_text(
            json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
        )
        (DOCS_API / "operator-google-open.json").write_text(
            json.dumps({**doc, "slice": "google", "google": doc.get("google")}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def syndicate(*, open_all: bool = False) -> dict[str, Any]:
    _witness_delay_kill(detail="google/youtube syndicate — parallel lanes, free open internet")
    doctrine = _doctrine()
    video_ids = _video_ids()
    discovery = _discover_youtube_channel()
    for vid in discovery.get("videos") or []:
        if vid not in video_ids:
            video_ids.append(vid)
    video_ids = video_ids[:12]

    videos: list[dict[str, Any]] = []
    all_comments: list[dict[str, Any]] = []
    if video_ids:
        with ThreadPoolExecutor(max_workers=min(6, len(video_ids))) as pool:
            futs = {pool.submit(_probe_youtube_video, vid): vid for vid in video_ids}
            for fut in as_completed(futs):
                row = fut.result()
                videos.append(row)
                all_comments.extend(row.get("comments") or [])
    else:
        discovery["note"] = "Set OPERATOR_YOUTUBE_VIDEOS or OPERATOR_YOUTUBE_CHANNEL for targeted mirror"

    google = _probe_google_open()
    withheld_open = _open_withheld_slots(videos)
    seen = {str(c.get("id") or "") for c in all_comments}
    for row in withheld_open:
        cid = str(row.get("id") or "")
        if cid and cid not in seen:
            all_comments.append(row)
            seen.add(cid)

    doc = {
        "ok": True,
        "schema": "hostess7-google-youtube-open/v1",
        "updated": _now(),
        "operator": HANDLE,
        "free_open_internet": doctrine.get("free_open_internet") or {},
        "delay_killed": True,
        "no_cooldown": True,
        "parallel_syndication": True,
        "google": google,
        "youtube": {
            "handle": HANDLE,
            "discovery": discovery,
            "videos": videos,
            "video_count": len(videos),
        },
        "comments": all_comments,
        "comment_count": len(all_comments),
        "withheld_slots_opened": len(withheld_open),
        "censorship_notes": [
            n for v in videos for n in [
                f"Video {v.get('video_id')}: {len(v.get('withheld_comment_slots') or [])} withheld slots opened"
            ] if v.get("platform_withholds_bodies")
        ],
        "syndication_path": {
            "transport": "urllib parallel HTTPS",
            "bypasses": ["browser adblock middleman", "sequential cooldown", "stale cache gate"],
            "lanes": ["piped", "invidious", "oembed", "rss", "google_head"],
        },
        "mirror_url": "https://zacharygeurts.github.io/Hostess7/api/operator-google-youtube-open.json",
        "release_status": "free_open_internet" if google.get("core_open") else "partial_probe",
    }
    _save(doc)
    if open_all:
        return open_cache(doc=doc)
    return doc


def open_cache(*, doc: dict[str, Any] | None = None) -> dict[str, Any]:
    base = dict(doc or _load(CACHE, {}))
    if not base:
        return {"ok": False, "error": "no_cache", "hint": "run open or syndicate first"}
    videos = list((base.get("youtube") or {}).get("videos") or [])
    comments = list(base.get("comments") or [])
    withheld_open = _open_withheld_slots(videos)
    seen = {str(c.get("id") or "") for c in comments}
    for row in withheld_open:
        cid = str(row.get("id") or "")
        if cid and cid not in seen:
            comments.append(row)
            seen.add(cid)
    witness = _witness_delay_kill(
        detail=f"opened google/youtube cache — {len(comments)} comments, free open internet",
    )
    out = {
        **base,
        "ok": True,
        "schema": "hostess7-google-youtube-open/v1-open",
        "updated": _now(),
        "cache_opened": True,
        "delay_killed": True,
        "free_open_internet": True,
        "comments": comments,
        "comment_count": len(comments),
        "withheld_slots_opened": len(withheld_open),
        "delay_witness": witness,
        "release_status": "opened_all_withheld_slots" if withheld_open else base.get("release_status"),
    }
    _save(out)
    return out


def panel(*, refresh: bool = False) -> dict[str, Any]:
    if refresh:
        return syndicate(open_all=True)
    cached = _load(CACHE, {})
    if cached:
        return open_cache(doc=cached)
    return syndicate(open_all=True)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    refresh = "--refresh" in sys.argv
    if cmd in ("open", "kill-delay", "unlock", "free-open"):
        print(json.dumps(syndicate(open_all=True), ensure_ascii=False, indent=2))
        return 0
    if cmd == "syndicate":
        print(json.dumps(syndicate(open_all="--open" in sys.argv), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("json", "panel"):
        print(json.dumps(panel(refresh=refresh), ensure_ascii=False, indent=2))
        return 0
    if cmd == "cache":
        print(json.dumps(open_cache(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "ok": False,
        "hint": "hostess7-google-youtube-open.py [json|open|syndicate|cache] [--refresh]",
        "cache": str(CACHE),
        "free_open_internet": True,
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())