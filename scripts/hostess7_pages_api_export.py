#!/usr/bin/env pythong
"""Export GitHub brain API snapshots for Pages — never touches sovereign brain."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
API = DOCS / "api"
sys.path.insert(0, str(ROOT / "src"))

from hostess7.github_brain import ask_mirror, status_mirror  # noqa: E402


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write(name: str, doc: Any) -> Path:
    API.mkdir(parents=True, exist_ok=True)
    out = API / name
    out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return out


def _export_health() -> dict[str, Any]:
    return {
        "ok": True,
        "service": "Hostess7-GitHub-Brain",
        "owner": "ZacharyGeurts",
        "pages": True,
        "lane": "github-mirror",
        "mode": "github-brain-mirror",
        "writes_to_sovereign": False,
    }


def _export_status() -> dict[str, Any]:
    st = status_mirror()
    st["exported"] = _ts()
    return st


def _export_brain() -> dict[str, Any]:
    manifest_path = DOCS / "github-brain" / "manifest.json"
    if manifest_path.is_file():
        doc = json.loads(manifest_path.read_text(encoding="utf-8"))
        doc["pages"] = True
        return doc
    return {"ok": True, "schema": "hostess7-github-brain/v1", "lane": "github-mirror", "pages": True}


def _export_status_full() -> dict[str, Any]:
    st = _export_status()
    mirror_path = DOCS / "github-brain" / "mirror.json"
    if mirror_path.is_file():
        st["mirror"] = json.loads(mirror_path.read_text(encoding="utf-8"))
    st["sovereign_note"] = "Loopback ./Hostess7.sh boot uses sovereign brain — not modified by Pages chat."
    return st


def _export_search_index(name: str, static_name: str, q: str) -> dict[str, Any]:
    """Read-only index from published github-brain corpus domains."""
    corpus_path = DOCS / "github-brain" / "corpus.json"
    if not corpus_path.is_file():
        return {"ok": True, "query": q, "hits": [], "lane": "github-mirror"}
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    tokens = [t for t in q.lower().split() if len(t) > 2]
    hits = []
    for c in corpus.get("chunks") or []:
        if c.get("domain") != name and name not in (c.get("tags") or []):
            continue
        hay = f"{c.get('title', '')} {c.get('text', '')}".lower()
        if any(t in hay for t in tokens):
            hits.append({"title": c.get("title"), "source": c.get("source"), "excerpt": c.get("text", "")[:240]})
    return {"ok": True, "query": q, "hits": hits[:24], "lane": "github-mirror", "exported": _ts()}


def _export_ask_seeds() -> dict[str, Any]:
    seeds = (
        "What do you want first?",
        "KILROY field stack boot order",
        "truth floor and neural guardian",
        "hearing and speech for Hostess7",
        "English grammar training",
        "github brain isolation policy",
    )
    answers = []
    for q in seeds:
        res = ask_mirror(q)
        answers.append({"query": q, "text": res.get("text", ""), "ok": res.get("ok"), "lane": "github-mirror"})
    return {"ok": True, "schema": "hostess7-github-ask-seeds/v1", "lane": "github-mirror", "answers": answers, "exported": _ts()}


def export_all(*, full: bool = True) -> dict[str, Any]:
    os.environ.setdefault("HOSTESS7_ROOT", str(ROOT))
    files: list[str] = []
    files.append(_write("health.json", _export_health()).name)
    files.append(_write("status.json", _export_status()).name)
    files.append(_write("brain.json", _export_brain()).name)
    files.append(_write("status-full.json", _export_status_full()).name)
    if full:
        files.append(_write("hearing-index.json", _export_search_index("hearing", "hearing", "hearing listen speak")).name)
        files.append(_write("world-index.json", _export_search_index("world", "world", "bible law nature")).name)
        files.append(_write("library-index.json", _export_search_index("library", "library", "children algebra")).name)
        files.append(_write("videogames-index.json", _export_search_index("videogames", "videogames", "mario zelda")).name)
        files.append(_write("ask-seeds.json", _export_ask_seeds()).name)
    total = sum((API / f).stat().st_size for f in files if (API / f).is_file())
    return {"ok": True, "lane": "github-mirror", "api_dir": str(API), "files": files, "bytes": total, "exported": _ts()}


def main() -> int:
    full = "--lite" not in sys.argv
    doc = export_all(full=full)
    print(json.dumps(doc, indent=2))
    print(f"METRIC pages_api_export={len(doc.get('files', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())