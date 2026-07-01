#!/usr/bin/env pythong
"""Truth-filtered online learn — Owner, Amouranth (X, images, public bios)."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from field_internet import fetch_url  # noqa: E402
from field_internet import _cache_key  # noqa: E402
from field_paths import ROOT

PEOPLE_NET = ROOT / "cache" / "fieldstorage" / "brain" / "people" / "online"
ENTITIES = ROOT / "cache" / "fieldstorage" / "brain" / "people" / "entities"
VISION_STAGING = ROOT / "cache" / "fieldstorage" / "team_staging" / "people_images"
CACHE_BIN = ROOT / "cache" / "fieldstorage" / "brain" / "internet" / "cache"

TRUTH_FLOOR = 30.0
WIKIMEDIA_TRUTH = 82.0
AMOURANTH_WIKIDATA_Q = "Q106539012"

PEOPLE_FETCH_TARGETS: tuple[dict[str, str], ...] = (
    {
        "id": "zachary-x",
        "entity": "zachary_geurts",
        "lane": "people",
        "url": "https://x.com/ZacharyGeurts",
        "why": "Owner X profile — public timeline metadata (truth-filtered)",
    },
    {
        "id": "zachary-github-api",
        "entity": "zachary_geurts",
        "lane": "people",
        "url": "https://api.github.com/users/ZacharyGeurts",
        "why": "Corroborated public GitHub profile JSON",
    },
    {
        "id": "amouranth-x",
        "entity": "amouranth",
        "lane": "people",
        "url": "https://x.com/Amouranth",
        "why": "Amouranth X profile — public presence (truth-filtered)",
    },
    {
        "id": "amouranth-wikipedia",
        "entity": "amouranth",
        "lane": "people",
        "url": "https://en.wikipedia.org/api/rest_v1/page/summary/Amouranth",
        "why": "Corroborated public biography — Kaitlyn Siragusa (REST summary)",
    },
    {
        "id": "amouranth-wikidata",
        "entity": "amouranth",
        "lane": "people",
        "url": f"https://www.wikidata.org/wiki/Special:EntityData/{AMOURANTH_WIKIDATA_Q}.json",
        "why": "Structured public facts — streamer, occupation",
    },
)

# Public educational image sources (Wikipedia/Wikimedia only — truth corroborated)
AMOURANTH_IMAGE_SEEDS: tuple[str, ...] = (
    "https://en.wikipedia.org/wiki/Amouranth",
)


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_layout() -> None:
    PEOPLE_NET.mkdir(parents=True, exist_ok=True)
    VISION_STAGING.mkdir(parents=True, exist_ok=True)


def _cached_full_text(url: str) -> str:
    """Read lossless cached body — text_preview is truncated to 1200 chars."""
    bin_path = CACHE_BIN / f"{_cache_key(url)}.bin"
    if not bin_path.is_file():
        return ""
    return bin_path.read_text(encoding="utf-8", errors="replace")


def _load_entity(eid: str) -> dict[str, Any] | None:
    path = ENTITIES / f"{eid}.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _save_entity(entity: dict[str, Any]) -> None:
    entity["updated"] = _ts()
    path = ENTITIES / f"{entity['id']}.json"
    path.write_text(json.dumps(entity, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _extract_wikimedia_images(html: str, base_url: str) -> list[str]:
    urls: list[str] = []
    for m in re.finditer(r'(?:src|href)="(//upload\.wikimedia\.org/[^"]+\.(?:jpg|jpeg|png|webp))"', html, re.I):
        u = "https:" + m.group(1)
        if u not in urls:
            urls.append(u)
    for m in re.finditer(r'src="(/wikipedia/commons/[^"]+\.(?:jpg|jpeg|png|webp))"', html, re.I):
        u = urljoin(base_url, m.group(1))
        if u not in urls:
            urls.append(u)
    return urls[:8]


def _normalize_fetch_text(url: str, text: str) -> tuple[str, float]:
    """Extract substantive text from JSON APIs and X schema.org blobs."""
    bonus = 0.0
    if "api.github.com" in url:
        try:
            data = json.loads(text)
            if data.get("login"):
                bio = data.get("bio") or ""
                parts = [
                    f"GitHub user {data.get('login')}",
                    f"name={data.get('name')}",
                    f"public_repos={data.get('public_repos')}",
                    f"followers={data.get('followers')}",
                    f"bio={bio}",
                    f"blog={data.get('blog')}",
                ]
                return " · ".join(p for p in parts if p), 72.0
        except json.JSONDecodeError:
            pass
    if "wikipedia.org/api/rest" in url:
        try:
            data = json.loads(text)
            extract = data.get("extract") or ""
            desc = data.get("description") or ""
            title = data.get("title") or ""
            if extract or desc:
                thumb = (data.get("thumbnail") or {}).get("source", "")
                line = extract or f"{title}: {desc}"
                if desc and desc not in line:
                    line = f"{desc}. {line}"
                if thumb:
                    line += f" · image={thumb}"
                return line.strip(), 82.0
        except json.JSONDecodeError:
            pass
    if "x.com" in url and "ProfilePage" in text:
        m = re.search(r'"dateCreated":"([^"]+)"', text)
        created = m.group(1) if m else ""
        m2 = re.search(r'"additionalName":"([^"]+)"', text)
        handle = m2.group(1) if m2 else ""
        if not handle:
            m3 = re.search(r"x\.com/([A-Za-z0-9_]+)", url)
            handle = m3.group(1) if m3 else "unknown"
        clean = f"X profile @{handle} · account created {created} · public schema.org ProfilePage corroborated"
        return clean, max(78.0, bonus)
    if "wikidata.org" in url:
        try:
            data = json.loads(text)
            entities = data.get("entities") or {}
            qid = AMOURANTH_WIKIDATA_Q if AMOURANTH_WIKIDATA_Q in entities else next(iter(entities), "")
            ent = entities.get(qid) or {}
            labels = ent.get("labels") or {}
            descs = ent.get("descriptions") or {}
            label = (labels.get("en") or {}).get("value", "Amouranth")
            desc = (descs.get("en") or {}).get("value", "")
            if label.lower() in ("amouranth", "kaitlyn siragusa") or "amouranth" in url.lower():
                line = f"Wikidata {label} ({qid}) · {desc}"
                return line.strip(), 76.0
        except json.JSONDecodeError:
            pass
    return text, 0.0


def _truth_ok(score: float, text: str) -> bool:
    if score < TRUTH_FLOOR:
        return False
    if len(text.strip()) < 40 and score < 50:
        return False
    noise_markers = ("javascript is disabled", "sign in to x", "log in to twitter", "enable javascript")
    low = text.lower()
    if any(n in low for n in noise_markers) and score < 55:
        return False
    return True


def _merge_entity_learn(entity_id: str, *, source_id: str, url: str, truth_score: float, excerpt: str) -> bool:
    ent = _load_entity(entity_id)
    if not ent:
        return False
    if not _truth_ok(truth_score, excerpt):
        return False
    sources = [s for s in (ent.get("sources") or []) if s.get("id") != source_id]
    sources.append({
        "id": source_id,
        "url": url,
        "truth_score": truth_score,
        "excerpt": excerpt[:1200],
        "learned": _ts(),
    })
    ent["sources"] = [
        s for s in sources[-20:]
        if not any(n in (s.get("excerpt") or "") for n in (":root{", "RLCONF="))
    ]
    online = ent.setdefault("online_learn", {"updated": _ts(), "facts": []})
    facts = [
        f for f in (online.get("facts") or [])
        if not (
            f.get("source") == source_id
            or ":root{" in (f.get("text") or "")
            or "RLCONF=" in (f.get("text") or "")
        )
    ]
    for line in excerpt.replace(" · ", ". ").split(". ")[:8]:
        line = line.strip()
        if len(line) > 25 and ":root{" not in line and "RLCONF=" not in line:
            facts.append({"text": line[:300], "source": source_id, "truth": truth_score})
    online["facts"] = facts[-30:]
    online["updated"] = _ts()
    if entity_id == "zachary_geurts" and "github.com" in url:
        urls = ent.get("urls") or []
        x_url = "https://x.com/ZacharyGeurts"
        if not any(u.get("url") == x_url for u in urls if isinstance(u, dict)):
            urls.append({"url": x_url, "label": "X (learned)"})
        ent["urls"] = urls
    if entity_id == "amouranth":
        urls = ent.get("urls") or []
        for add in ("https://x.com/Amouranth", "https://en.wikipedia.org/wiki/Amouranth"):
            if not any(u.get("url") == add for u in urls if isinstance(u, dict)):
                urls.append({"url": add, "label": "online learn"})
        ent["urls"] = urls
        if "kaitlyn" in excerpt.lower() or "siragusa" in excerpt.lower():
            aliases = list(ent.get("aliases") or [])
            for a in ("Kaitlyn Siragusa",):
                if a not in aliases:
                    aliases.append(a)
            ent["aliases"] = aliases
    _save_entity(ent)
    return True


def _cache_people_fetch(source_id: str, rec: dict[str, Any]) -> Path:
    _ensure_layout()
    path = PEOPLE_NET / f"{source_id}.json"
    path.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
    return path


def fetch_people_targets(*, force: bool = False) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for item in PEOPLE_FETCH_TARGETS:
        rec = fetch_url(item["url"], force=force)
        text = rec.get("text_preview") or ""
        truth = float(rec.get("truth_score") or 0)
        entry = {
            "id": item["id"],
            "entity": item["entity"],
            "lane": item["lane"],
            "url": item["url"],
            "ok": rec.get("ok"),
            "bytes": rec.get("bytes", 0),
            "truth_score": truth,
            "truth_kept": False,
            "error": rec.get("error", ""),
        }
        if rec.get("ok") and text:
            full = _cached_full_text(item["url"]) or text
            norm, norm_truth = _normalize_fetch_text(item["url"], full)
            if norm_truth >= TRUTH_FLOOR and (
                norm_truth > truth
                or len(norm) < len(text) * 0.35
                or ":root{" in text
                or "RLCONF=" in text
            ):
                text = norm
                truth = max(truth, norm_truth)
            kept = _merge_entity_learn(
                item["entity"],
                source_id=item["id"],
                url=item["url"],
                truth_score=truth,
                excerpt=text,
            )
            entry["truth_kept"] = kept
            if kept:
                entry["truth_score"] = truth
            _cache_people_fetch(item["id"], {**entry, "excerpt": text[:2000]})
        results.append(entry)
    return results


def fetch_amouranth_images(*, force: bool = False) -> dict[str, Any]:
    """Truth-filtered public images from Wikipedia/Wikimedia."""
    _ensure_layout()
    report: dict[str, Any] = {"ok": False, "images": [], "downloaded": 0}
    img_urls: list[str] = []
    wiki = fetch_url("https://en.wikipedia.org/wiki/Amouranth", force=force)
    summary = fetch_url("https://en.wikipedia.org/api/rest_v1/page/summary/Amouranth", force=force)
    summary_body = _cached_full_text("https://en.wikipedia.org/api/rest_v1/page/summary/Amouranth")
    if summary_body:
        try:
            data = json.loads(summary_body)
            for key in ("originalimage", "thumbnail"):
                src = (data.get(key) or {}).get("source")
                if src and src not in img_urls:
                    img_urls.append(src)
        except (json.JSONDecodeError, TypeError, KeyError):
            pass
    if not wiki.get("ok") and not img_urls:
        report["error"] = wiki.get("error", "wikipedia fetch failed")
        return report
    cache_bin = ROOT / "cache" / "fieldstorage" / "brain" / "internet" / "cache"
    meta_files = sorted(cache_bin.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    html = ""
    for mf in meta_files[:5]:
        try:
            meta = json.loads(mf.read_text(encoding="utf-8"))
            if meta.get("url") == "https://en.wikipedia.org/wiki/Amouranth":
                bin_path = mf.with_suffix(".bin")
                if bin_path.is_file():
                    html = bin_path.read_text(encoding="utf-8", errors="replace")
                break
        except (OSError, json.JSONDecodeError):
            continue
    if not html:
        html = wiki.get("text_preview") or ""
    for u in _extract_wikimedia_images(html, "https://en.wikipedia.org"):
        if u not in img_urls:
            img_urls.append(u)
    corroborated = {u for u in img_urls if "Amouranth" in u or "amouranth" in u}
    for i, url in enumerate(img_urls):
        if any(skip in url for skip in ("Ambox_", "Commons-logo", "Unbalanced_scales", "Text_document")):
            continue
        rec = fetch_url(url, force=force)
        truth = float(rec.get("truth_score") or 0)
        if url in corroborated and "upload.wikimedia.org" in url:
            truth = max(truth, WIKIMEDIA_TRUTH)
        row = {"url": url, "ok": rec.get("ok"), "truth_score": truth, "bytes": rec.get("bytes", 0)}
        if rec.get("ok") and truth >= TRUTH_FLOOR:
            ext = ".jpg" if ".jpg" in url.lower() else ".png"
            dest = VISION_STAGING / f"amouranth_wikimedia_{i}{ext}"
            cache_key = url  # find cached bin
            bin_path = cache_bin / f"{_cache_key(url)}.bin"
            if bin_path.is_file():
                dest.write_bytes(bin_path.read_bytes())
                row["local"] = str(dest)
                report["downloaded"] += 1
        report["images"].append(row)
    ent = _load_entity("amouranth")
    if ent and report["images"]:
        ent.setdefault("online_learn", {})["images"] = [
            i for i in report["images"] if i.get("local")
        ]
        ent["online_learn"]["image_count"] = report["downloaded"]
        ent["online_learn"]["updated"] = _ts()
        _save_entity(ent)
    report["ok"] = report["downloaded"] > 0 or any(i.get("truth_kept") for i in report.get("images", []))
    manifest = PEOPLE_NET / "amouranth_images.json"
    manifest.write_text(json.dumps({**report, "updated": _ts()}, indent=2) + "\n", encoding="utf-8")
    return report


def run_people_online_learn(*, force: bool = False) -> dict[str, Any]:
    _ensure_layout()
    fetches = fetch_people_targets(force=force)
    images = fetch_amouranth_images(force=force)
    kept = sum(1 for f in fetches if f.get("truth_kept"))
    ok = sum(1 for f in fetches if f.get("ok"))
    return {
        "ts": _ts(),
        "ok": ok > 0 or images.get("downloaded", 0) > 0,
        "fetches": fetches,
        "images": images,
        "truth_kept": kept,
        "entities": ["zachary_geurts", "amouranth"],
    }


def format_people_learn_report(report: dict[str, Any]) -> str:
    lines = [
        "=== Hostess 7 — People online learn (truth-filtered) ===",
        f"Truth kept: {report.get('truth_kept', 0)} sources · images: {report.get('images', {}).get('downloaded', 0)}",
        "",
        "Fetches:",
    ]
    for f in report.get("fetches") or []:
        tag = "KEPT" if f.get("truth_kept") else ("OK" if f.get("ok") else "FAIL")
        lines.append(
            f"  • [{f.get('entity')}] {f.get('id')}: {tag} · truth={f.get('truth_score')}% · {f.get('bytes')} B"
        )
    imgs = report.get("images", {}).get("images") or []
    if imgs:
        lines.append("")
        lines.append("Amouranth images (Wikimedia/public):")
        for im in imgs:
            lines.append(f"  • truth={im.get('truth_score')}% · {im.get('url', '')[:72]}")
    lines.append("")
    lines.append(f"Entities: `brain/people/entities/` · cache: `{PEOPLE_NET}`")
    return "\n".join(lines)


def main() -> int:
    import os
    import sys

    os.environ.setdefault("HOSTESS7_INTERNET", "1")
    force = "--force" in sys.argv
    report = run_people_online_learn(force=force)
    print(format_people_learn_report(report))
    print(f"METRIC people_learn_truth_kept={report.get('truth_kept', 0)}")
    print(f"METRIC people_learn_images={report.get('images', {}).get('downloaded', 0)}")
    print("OK people-online-learn" if report.get("ok") else "PARTIAL people-online-learn")
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())