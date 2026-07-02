#!/usr/bin/env pythong
"""Hostess7 memes corpus — ZacharyGeurts/memes GitHub image library for image talk."""
from __future__ import annotations

import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from field_paths import ROOT

MEMES_REPO = "https://github.com/ZacharyGeurts/memes"
MEMES_API = "https://api.github.com/repos/ZacharyGeurts/memes"
RAW_BASE = "https://raw.githubusercontent.com/ZacharyGeurts/memes/main"

BRAIN_MEMES = ROOT / "cache" / "fieldstorage" / "brain" / "memes"
MANIFEST = BRAIN_MEMES / "manifest.json"
INDEX = BRAIN_MEMES / "search_index.jsonl"
CACHE = BRAIN_MEMES / "images"
CORPUS_VERSION = 1

IMAGE_EXTS = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"})
MAX_DOWNLOAD = int(os.environ.get("HOSTESS7_MEMES_MAX", "48"))
MAX_BYTES = int(os.environ.get("HOSTESS7_MEMES_MAX_BYTES", str(4 * 1024 * 1024)))


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _api_get(url: str) -> Any:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Hostess7-SuperIntelligence/1.0",
            "Accept": "application/vnd.github+json",
        },
    )
    with urllib.request.urlopen(req, timeout=30, context=ssl.create_default_context()) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _download(url: str, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "Hostess7-SuperIntelligence/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=60, context=ssl.create_default_context()) as resp:
            data = resp.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                return False
            dest.write_bytes(data)
        return dest.is_file() and dest.stat().st_size > 0
    except (urllib.error.URLError, OSError):
        return False


def _walk_github_tree(path: str = "") -> Iterator[dict[str, Any]]:
    """Breadth-first walk of repo tree via GitHub API."""
    queue = [path]
    seen = 0
    while queue and seen < 800:
        current = queue.pop(0)
        url = f"{MEMES_API}/contents/{current}" if current else f"{MEMES_API}/contents"
        try:
            entries = _api_get(url)
        except (urllib.error.URLError, OSError, json.JSONDecodeError):
            continue
        if not isinstance(entries, list):
            continue
        for entry in entries:
            seen += 1
            if entry.get("type") == "file":
                yield entry
            elif entry.get("type") == "dir":
                queue.append(entry.get("path", ""))


def ingest_memes(*, max_files: int | None = None) -> dict[str, Any]:
    """Index + download images from github.com/ZacharyGeurts/memes."""
    os.environ.setdefault("HOSTESS7_INTERNET", "1")
    BRAIN_MEMES.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)

    limit = max_files or MAX_DOWNLOAD
    files: list[dict[str, Any]] = []
    downloaded = 0

    readme_text = ""
    try:
        readme = _api_get(f"{MEMES_API}/readme")
        if readme.get("download_url"):
            req = urllib.request.Request(readme["download_url"], headers={"User-Agent": "Hostess7/1.0"})
            with urllib.request.urlopen(req, timeout=20, context=ssl.create_default_context()) as r:
                readme_text = r.read(8000).decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError):
        pass

    for entry in _walk_github_tree():
        name = entry.get("name", "")
        ext = Path(name).suffix.lower()
        if ext not in IMAGE_EXTS:
            continue
        rel = entry.get("path", name)
        dl = entry.get("download_url") or f"{RAW_BASE}/{rel}"
        local = CACHE / rel.replace("/", "__")
        ok = False
        if not local.is_file():
            ok = _download(dl, local)
        else:
            ok = True
        if ok:
            downloaded += 1
        files.append({
            "path": rel,
            "name": name,
            "local": str(local.relative_to(ROOT)),
            "bytes": local.stat().st_size if local.is_file() else 0,
            "downloaded": ok,
            "url": dl,
        })
        if len(files) >= limit:
            break

    manifest = {
        "version": CORPUS_VERSION,
        "updated": _ts(),
        "repo": MEMES_REPO,
        "owner": "ZacharyGeurts",
        "readme_excerpt": readme_text[:1200],
        "file_count": len(files),
        "downloaded": sum(1 for f in files if f.get("downloaded")),
        "files": files,
        "talk_hint": "Hostess7 shows memes as ASCII graphics in the talk window — ask about tarot, BigGrin, stamp.",
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    with INDEX.open("w", encoding="utf-8") as f:
        for item in files:
            f.write(json.dumps({
                "path": item["path"],
                "name": item["name"],
                "local": item["local"],
                "folder": str(Path(item["path"]).parent),
            }) + "\n")

    return manifest


def load_manifest() -> dict[str, Any]:
    if not MANIFEST.is_file():
        return {}
    try:
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def ensure_corpus(*, seed_if_missing: bool = True) -> dict[str, Any]:
    man = load_manifest()
    if man.get("file_count", 0) > 0:
        return man
    if seed_if_missing and os.environ.get("HOSTESS7_INTERNET", "0") in ("1", "true", "on"):
        return ingest_memes(max_files=24)
    return man


def search_memes(query: str, *, limit: int = 5) -> list[dict[str, Any]]:
    man = load_manifest()
    files = man.get("files") or []
    if not files:
        return []
    tokens = [t for t in re.split(r"\W+", query.lower()) if len(t) > 2]
    scored: list[tuple[int, dict]] = []
    for item in files:
        blob = f"{item.get('path','')} {item.get('name','')}".lower()
        score = sum(3 if t in blob else 0 for t in tokens)
        if not tokens and item.get("downloaded"):
            score = 1
        if score > 0:
            scored.append((score, item))
    scored.sort(key=lambda x: -x[0])
    return [it for _, it in scored[:limit]]


def synthesize_memes_paragraphs(query: str) -> list[str]:
    man = load_manifest()
    if not man:
        return [
            "Memes corpus empty — run `./Hostess7.sh memes-ingest seed` or `./Hostess7.sh on` with internet.",
            f"Source: {MEMES_REPO}",
        ]
    hits = search_memes(query, limit=4)
    lines = [
        f"ZacharyGeurts/memes — {man.get('file_count', 0)} images indexed, "
        f"{man.get('downloaded', 0)} cached locally.",
        man.get("readme_excerpt", "")[:400],
    ]
    if hits:
        names = ", ".join(h["name"] for h in hits[:4])
        lines.append(f"Matched: {names}. I render these as ASCII art in the talk window.")
    else:
        lines.append("Folders: tarot, BigGrin, Commentary, DEMONS, GrokBuild, …")
    lines.append("Talk with images: ask about a meme name, `/image <file>`, or `/gfx memes`.")
    return lines


def graphics_for_memes_query(query: str) -> list[str]:
    from field_image_talk import image_to_ascii  # noqa: WPS433

    ensure_corpus(seed_if_missing=False)
    hits = search_memes(query, limit=2)
    if not hits:
        man = load_manifest()
        hits = (man.get("files") or [])[:1]
    gfx: list[str] = []
    for item in hits:
        local = ROOT / item.get("local", "")
        if local.is_file():
            gfx.extend(image_to_ascii(local, max_width=68, max_height=14))
            gfx.append(f"--- {item.get('path')} ---")
    return gfx


def format_status() -> str:
    man = load_manifest()
    if not man:
        return f"Memes corpus: empty. Run: ./Hostess7.sh memes-ingest seed ({MEMES_REPO})"
    return (
        f"Memes: {man.get('downloaded', 0)}/{man.get('file_count', 0)} images · "
        f"{MEMES_REPO} · updated {man.get('updated', '?')}"
    )


def show_image(query: str) -> int:
    ensure_corpus(seed_if_missing=True)
    for para in synthesize_memes_paragraphs(query):
        print(para)
    print(format_status())
    for line in graphics_for_memes_query(query):
        print(f"GFX:{line}")
    print("OK memes-show")
    return 0


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd in ("seed", "ingest", "bulk"):
        os.environ["HOSTESS7_INTERNET"] = "1"
        man = ingest_memes()
        print(format_status())
        print(f"METRIC memes_files={man.get('file_count', 0)}")
        print(f"METRIC memes_downloaded={man.get('downloaded', 0)}")
        print("OK memes-ingest")
        return 0
    if cmd in ("show", "image") and len(sys.argv) >= 3:
        return show_image(" ".join(sys.argv[2:]))
    if cmd in ("show", "image"):
        return show_image("stamp")
    ensure_corpus()
    print(format_status())
    print("OK memes-status")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())