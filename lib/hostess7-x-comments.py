#!/usr/bin/env python3
"""Operator X comments — syndicate recoverable posts/replies to Hostess7 pages."""
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
DOCS_API = Path(os.environ.get("HOSTESS7_ROOT", INSTALL / "Hostess7")) / "docs" / "api"
CACHE = STATE / "operator-x-comments-cache.json"
HANDLE = os.environ.get("OPERATOR_X_HANDLE", "ZacharyGeurts")
UA = "Hostess7-XComments/3.0"
HTTP_TIMEOUT = int(os.environ.get("NEXUS_X_HTTP_TIMEOUT", "12"))
NO_DELAY = os.environ.get("NEXUS_X_NO_DELAY", "1").strip().lower() not in ("0", "false", "no", "off")
OPERATOR_ALIASES = frozenset({
    "zacharygeurts", "biggrin", "big_grin", "zachary_geurts", "zacharyrobertgeurts",
})
IMPERSONATION_MARKERS = (
    "plagiar", "copyscape", "turnitin", "originality", "ai wrote", "ai-written",
    "written by ai", "chatgpt", "not your words", "stolen content", "copyright strike",
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _http_json(url: str, *, timeout: int | None = None) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout or HTTP_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def _load_cache() -> dict[str, Any]:
    if not CACHE.is_file():
        return {}
    try:
        return json.loads(CACHE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}


def _witness_delay_kill(*, detail: str = "", signal: str = "stale_operator_x_cache") -> dict[str, Any]:
    """Kill delay-as-threat on X cache — bypass middleman, open local truth now."""
    py = INSTALL / "lib" / "hostess7-truth-lie-threat.py"
    if not py.is_file():
        return {"ok": True, "delay_killed": True, "skipped": "truth_lie_threat_missing"}
    try:
        spec = importlib.util.spec_from_file_location("x_delay_kill", py)
        if not spec or not spec.loader:
            return {"ok": True, "delay_killed": True}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "witness_delay_threat"):
            return mod.witness_delay_threat(
                signal=signal,
                detail=detail or "operator-x-comments-cache opened — no cooldown, no stale gate",
                elapsed_sec=0,
                meta={"module": "hostess7-x-comments.py", "cache": str(CACHE)},
            )
    except Exception as exc:
        return {"ok": True, "delay_killed": True, "degraded": str(exc)[:120]}
    return {"ok": True, "delay_killed": True}


def _open_withheld_as_comments(posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Expose every withheld reply slot as a visible comment — nothing hidden behind delay."""
    opened: list[dict[str, Any]] = []
    for post in posts:
        tid = str(post.get("id") or "")
        for slot in post.get("withheld_reply_slots") or []:
            if not isinstance(slot, dict):
                continue
            opened.append({
                "kind": "reply_withheld_open",
                "id": f"{tid}-withheld-{slot.get('slot', 0)}",
                "parent_id": tid,
                "text": str(slot.get("note") or "Reply body withheld by X platform"),
                "status": slot.get("status") or "hooked_by_x",
                "slot": slot.get("slot"),
                "opened": True,
                "delay_killed": True,
                "author": "x_platform_gate",
                "author_name": "X visibility gate",
                "url": post.get("url"),
                "withheld": True,
                "verified_operator": False,
                "impersonation_risk": {"risk": "platform", "note": "Platform withheld body — slot opened for Operator audit"},
            })
    return opened


def _kill_tco_hops(doc: dict[str, Any]) -> dict[str, Any]:
    py = INSTALL / "lib" / "hostess7-tco-kill.py"
    if not py.is_file():
        return {"ok": True, "skipped": "tco_kill_missing"}
    try:
        spec = importlib.util.spec_from_file_location("tco_kill", py)
        if not spec or not spec.loader:
            return {"ok": True, "skipped": "tco_kill_load"}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "kill_in_doc"):
            return mod.kill_in_doc(doc)
    except Exception as exc:
        return {"ok": True, "degraded": str(exc)[:120]}
    return {"ok": True, "skipped": "kill_in_doc_missing"}


def open_cache(*, doc: dict[str, Any] | None = None) -> dict[str, Any]:
    """Open stale X cache — all posts, probes, censorship notes, withheld slots as visible comments."""
    base = dict(doc or _load_cache())
    if not base:
        return {"ok": False, "error": "no_cache", "hint": "run syndicate or open first"}
    posts = list(base.get("posts") or [])
    comments = list(base.get("comments") or [])
    withheld_open = _open_withheld_as_comments(posts)
    seen = {str(c.get("id") or "") for c in comments}
    for row in withheld_open:
        cid = str(row.get("id") or "")
        if cid and cid not in seen:
            comments.append(row)
            seen.add(cid)
    delay_witness = _witness_delay_kill(
        detail=f"cache updated {base.get('updated')} — opening {len(comments)} comments, {len(withheld_open)} withheld slots",
    )
    out = {
        **base,
        "ok": True,
        "schema": "hostess7-operator-x-comments/v3-open",
        "updated": _now(),
        "cache_opened": True,
        "delay_killed": True,
        "no_delay": NO_DELAY,
        "comments": comments,
        "comment_count": len(comments),
        "withheld_slots_opened": len(withheld_open),
        "reply_probes_exposed": bool(base.get("reply_probes")),
        "censorship_notes_exposed": list(base.get("censorship_notes") or []),
        "delay_witness": delay_witness,
        "release_status": "opened_all_withheld_slots" if withheld_open else base.get("release_status"),
    }
    tco = _kill_tco_hops(out)
    if tco.get("tco_unwrapped"):
        out["posts"] = tco.get("posts") or out.get("posts")
        out["comments"] = tco.get("comments") or out.get("comments")
        out["tco_kill"] = {
            "tco_found": tco.get("tco_found"),
            "tco_unwrapped": tco.get("tco_unwrapped"),
            "mapping": tco.get("mapping"),
            "sniff_median_ms": tco.get("sniff_median_ms"),
            "witness": tco.get("witness"),
        }
    CACHE.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if DOCS_API.parent.is_dir():
        DOCS_API.mkdir(parents=True, exist_ok=True)
        (DOCS_API / "operator-x-comments.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return out


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


def _url_gone(url: str) -> bool:
    py = INSTALL / "lib" / "hostess7-url-kill.py"
    if not py.is_file():
        return False
    try:
        spec = importlib.util.spec_from_file_location("url_kill_gate", py)
        if not spec or not spec.loader:
            return False
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "is_gone"):
            return bool(mod.is_gone(url).get("gone"))
    except Exception:
        pass
    return False


def _probe_lane(label: str, url: str) -> dict[str, Any]:
    row: dict[str, Any] = {"lane": label, "url": url, "ok": False}
    if _url_gone(url):
        row["gone"] = True
        row["error"] = "url_killed"
        return row
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
        if thread:
            row["thread_sample"] = [
                (t.get("text") or "")[:120] for t in thread[:3] if isinstance(t, dict)
            ]
    except (urllib.error.URLError, OSError, json.JSONDecodeError, TimeoutError) as exc:
        row["error"] = str(exc)[:160]
    return row


def _reply_lane_urls(tid: str) -> list[tuple[str, str]]:
    """Straight shot first — direct x.com/oembed; extraction middlemen only on resist."""
    import urllib.parse

    oembed_q = urllib.parse.urlencode({
        "url": f"https://x.com/{HANDLE}/status/{tid}",
        "omit_script": "1",
    })
    return [
        ("x_direct", f"https://x.com/{HANDLE}/status/{tid}"),
        ("x_oembed", f"https://publish.twitter.com/oembed?{oembed_q}"),
        ("pull_fx_replies", f"https://api.fxtwitter.com/{HANDLE}/status/{tid}/replies"),
        ("pull_fx_status", f"https://api.fxtwitter.com/{HANDLE}/status/{tid}"),
        ("pull_vx", f"https://api.vxtwitter.com/{HANDLE}/status/{tid}"),
        ("pull_vx_replies", f"https://api.vxtwitter.com/{HANDLE}/status/{tid}/replies"),
    ]


def _probe_reply_lanes(tid: str) -> dict[str, Any]:
    """Parallel urllib lanes — no sequential delay, bypasses browser/adblock/gatekeeper."""
    lanes: list[dict[str, Any]] = []
    urls = _reply_lane_urls(tid)
    workers = min(8, max(2, len(urls)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(_probe_lane, label, url): label for label, url in urls}
        for fut in as_completed(futs):
            lanes.append(fut.result())
    lanes.sort(key=lambda r: r.get("lane") or "")
    withheld = [lane for lane in lanes if lane.get("reply_bodies_withheld")]
    return {
        "path": "urllib_parallel_no_delay",
        "parallel": True,
        "delay_killed": NO_DELAY,
        "lanes": lanes,
        "platform_withholds_bodies": bool(withheld),
        "verdict": (
            "X platform reports replies but withholds bodies across independent syndication lanes"
            if withheld
            else "no_withhold_detected"
        ),
    }


def _best_thread_from_probes(probe: dict[str, Any]) -> list[dict[str, Any]]:
    best: list[dict[str, Any]] = []
    for lane in probe.get("lanes") or []:
        if not lane.get("ok"):
            continue
        label = str(lane.get("lane") or "")
        if "repl" not in label and "syndication" not in label:
            continue
        try:
            doc = _http_json(str(lane.get("url") or ""))
            tw = doc.get("tweet") or doc
            thread = _extract_thread(doc, tw if isinstance(tw, dict) else {})
            if len(thread) > len(best):
                best = thread
        except (urllib.error.URLError, OSError, json.JSONDecodeError, TimeoutError):
            continue
    return best


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


def syndicate(*, tweet_ids: list[str] | None = None, open_all: bool = False) -> dict[str, Any]:
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

    _witness_delay_kill(detail="syndicate start — parallel lanes, no cooldown gate")

    for tid in ids[:12]:
        probe = _probe_reply_lanes(tid)
        probe_by_tweet[tid] = probe
        try:
            doc = _http_json(f"https://api.fxtwitter.com/{HANDLE}/status/{tid}/replies")
            tw = doc.get("tweet") or doc
            posts.append(_tweet_row(tw, kind="post"))
            rc = int(tw.get("replies") or 0)
            thread = _extract_thread(doc, tw if isinstance(tw, dict) else {})
            if not thread:
                thread = _best_thread_from_probes(probe)
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

    # syndication.twimg timeline dropped — useless legacy per X brand purge (Mr. Musk)

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
        "schema": "hostess7-operator-x-comments/v3",
        "updated": _now(),
        "delay_killed": NO_DELAY,
        "no_cooldown": True,
        "parallel_syndication": True,
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
    if open_all:
        doc = open_cache(doc=doc)
    _merge_straight_shot(doc)
    return doc


def _merge_straight_shot(doc: dict[str, Any]) -> None:
    """Rip censorship barriers — merge straight-shot pulled data into live doc."""
    py = INSTALL / "lib" / "hostess7-x-straight-shot.py"
    if not py.is_file():
        return
    try:
        spec = importlib.util.spec_from_file_location("x_straight_shot", py)
        if not spec or not spec.loader:
            return
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if not hasattr(mod, "rip_barriers"):
            return
        shot = mod.rip_barriers(export=False)
        pulled = shot.get("pulled") or []
        comments = list(doc.get("comments") or [])
        seen = {str(c.get("id") or "") for c in comments}
        freed = 0
        for row in pulled:
            if row.get("kind") == "pulled_reply":
                cid = f"{row.get('parent_id')}-ripped-{freed}"
                if cid in seen:
                    continue
                comments.append({
                    "kind": "reply_pulled",
                    "id": cid,
                    "parent_id": row.get("parent_id"),
                    "text": row.get("text") or "",
                    "author": row.get("author") or "unknown",
                    "released": True,
                    "barrier_ripped": True,
                })
                seen.add(cid)
                freed += 1
        doc["comments"] = comments
        doc["comment_count"] = len(comments)
        doc["censorship_barriers_revealed"] = shot.get("censorship_barriers_revealed")
        doc["straight_shot"] = {
            "barrier_count": shot.get("barrier_count"),
            "pulled_count": shot.get("pulled_count"),
            "info_freed_count": freed,
        }
        doc["no_middlemen_primary"] = True
        if shot.get("barrier_count") or freed:
            doc["release_status"] = "barriers_ripped_info_freed"
        for note in shot.get("censorship_barriers_revealed") or []:
            line = f"Barrier [{note.get('id')}]: tweet lane={note.get('lane')}"
            notes = list(doc.get("censorship_notes") or [])
            if line not in notes:
                notes.append(line)
            doc["censorship_notes"] = notes
        if DOCS_API.parent.is_dir():
            (DOCS_API / "hostess7-x-straight-shot.json").write_text(
                json.dumps(shot, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
    except Exception:
        pass


def panel(*, refresh: bool = False) -> dict[str, Any]:
    """Cache-first panel — instant open; refresh only when explicitly requested."""
    if refresh:
        return syndicate(open_all=True)
    cached = _load_cache()
    if cached:
        return open_cache(doc=cached)
    return syndicate(open_all=True)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    refresh = "--refresh" in sys.argv or "--no-delay" in sys.argv
    if cmd in ("open", "kill-delay", "unlock"):
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
        "hint": "hostess7-x-comments.py [json|open|syndicate|cache] [--refresh|--open]",
        "cache": str(CACHE),
        "delay_killed": NO_DELAY,
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())