#!/usr/bin/env pythong
"""GitHub brain — read-only mirror for Pages. Never writes to sovereign brain."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hostess7 import __version__
from hostess7.h7_io import read_json as h7_read_json
from hostess7.paths import hostess7_root

SCHEMA = "hostess7-github-brain/v1"
SOVEREIGN_STORAGE = "cache/fieldstorage"
GITHUB_BRAIN_CACHE = "cache/github-brain"
GITHUB_BRAIN_DOCS = "docs/github-brain"

BLOCKED_DATA = frozenset({"github-known-hosts.json"})
SENSITIVE_RE = re.compile(
    r"(ssh-rsa|BEGIN OPENSSH|pin_sha256|HOSTESS7_SUDO|password\s*[:=]|"
    r"superintel/agents7|MITM|known_hosts)",
    re.I,
)
GITHUB_RAW = "https://raw.githubusercontent.com/ZacharyGeurts/Hostess7/main/"
BRAIN_GLOBS = (
    "superintel/**/*.json",
    "chemistry/**/*.json",
    "people/**/*.json",
    "areas/**/*.json",
    "workspaces/default/**/*.json",
    "legal/**/*.json",
    "medical/**/*.json",
    "warfare/**/*.json",
    "english/**/*.json",
)
MAX_MIRROR_BYTES = 40 * 1024 * 1024


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def github_brain_cache() -> Path:
    p = hostess7_root() / GITHUB_BRAIN_CACHE
    p.mkdir(parents=True, exist_ok=True)
    (p / "fieldstorage").mkdir(exist_ok=True)
    (p / "sessions").mkdir(exist_ok=True)
    os.environ["HOSTESS7_GITHUB_BRAIN"] = "1"
    os.environ.setdefault("HOSTESS7_GITHUB_BRAIN_DIR", str(p))
    return p


def github_brain_docs() -> Path:
    p = hostess7_root() / GITHUB_BRAIN_DOCS
    p.mkdir(parents=True, exist_ok=True)
    return p


def sovereign_storage() -> Path:
    return hostess7_root() / SOVEREIGN_STORAGE


def is_github_brain_mode() -> bool:
    return os.environ.get("HOSTESS7_GITHUB_BRAIN", "0") in ("1", "true", "yes")


def activate_github_brain_env() -> dict[str, str]:
    """Redirect brain I/O to sandbox — call before subprocess ask in mirror context."""
    cache = github_brain_cache()
    env = {
        **os.environ,
        "HOSTESS7_GITHUB_BRAIN": "1",
        "HOSTESS7_GITHUB_BRAIN_DIR": str(cache),
        "HOSTESS7_BRAIN_STATE": str(cache / "state"),
        "NEXUS_STATE_DIR": str(cache / "state"),
    }
    os.environ.update(env)
    return env


def _safe(text: str) -> str:
    if SENSITIVE_RE.search(text):
        return ""
    return text.strip()


def _chunk(cid: str, domain: str, title: str, text: str, source: str, tags: list[str] | None = None) -> dict[str, Any] | None:
    body = _safe(text)
    if not body or len(body) < 8:
        return None
    return {
        "id": cid,
        "domain": domain,
        "title": title,
        "text": body[:12000],
        "source": source,
        "tags": tags or [],
        "lane": "github-mirror",
    }


def mirror_sovereign_snapshot() -> dict[str, Any]:
    """Copy sovereign brain JSON → github-brain cache (read-only snapshot)."""
    src = sovereign_storage() / "brain"
    dst = github_brain_cache() / "fieldstorage" / "brain"
    copied = 0
    if src.is_dir():
        if dst.exists():
            shutil.rmtree(dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst, dirs_exist_ok=True)
        copied = len(list(dst.rglob("*.json")))
    meta = {
        "schema": SCHEMA,
        "lane": "github-mirror",
        "sovereign_read_only": True,
        "mirrored_at": _ts(),
        "json_files": copied,
        "note": "Public GitHub chatter never writes here after publish — sovereign brain untouched.",
    }
    (github_brain_cache() / "mirror.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return meta


def build_corpus(*, include_repo_files: bool = True) -> dict[str, Any]:
    """Build searchable corpus for Pages — sourced from mirror + public repo files."""
    import runpy

    root = hostess7_root()
    mirror = mirror_sovereign_snapshot()
    chunks: list[dict[str, Any]] = []
    github_files: list[dict[str, str]] = []

    chunks.append(
        _chunk(
            "github-brain-policy",
            "policy",
            "GitHub brain isolation",
            (
                "This is the GitHub brain — a read-only mirror of Hostess 7 doctrine and corpus. "
                "It answers the same way but lives in docs/github-brain on Pages. "
                "Public chat never writes to cache/fieldstorage/brain, brain/state, or superintel. "
                "Sovereign brain stays on loopback after ./Hostess7.sh boot."
            ),
            "hostess7/github_brain",
            ["policy", "isolation"],
        )
    )

    if include_repo_files:
        data_out = root / "docs" / "data"
        data_out.mkdir(parents=True, exist_ok=True)
        for p in sorted((root / "data").glob("*.json")):
            if p.name in BLOCKED_DATA:
                continue
            shutil.copy2(p, data_out / p.name)
            github_files.append({"path": f"data/{p.name}", "domain": p.stem})
            try:
                doc = h7_read_json(p)
                flat = json.dumps(doc)[:8000]
                c = _chunk(f"data-{p.stem}", p.stem, p.stem, flat, f"data/{p.name}", ["data"])
                if c:
                    chunks.append(c)
            except (OSError, json.JSONDecodeError):
                pass

        wants_py = root / "scripts" / "field_hostess_wants.py"
        if wants_py.is_file():
            g = runpy.run_path(str(wants_py))
            wants = g.get("HOSTESS_WANTS") or {}
            for p in wants.get("priorities") or []:
                c = _chunk(
                    f"wants-{p.get('rank')}",
                    "wants",
                    p.get("want", ""),
                    f"{p.get('want')}. {p.get('detail', '')}",
                    "scripts/field_hostess_wants.py",
                    ["wants"],
                )
                if c:
                    chunks.append(c)

    mirror_brain = github_brain_cache() / "fieldstorage" / "brain"
    used = 0
    if mirror_brain.is_dir():
        for pattern in BRAIN_GLOBS:
            for path in sorted(mirror_brain.glob(pattern)):
                if used >= MAX_MIRROR_BYTES:
                    break
                try:
                    raw = path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                if SENSITIVE_RE.search(raw):
                    continue
                if len(raw) > 200_000:
                    raw = raw[:200_000]
                used += len(raw)
                rel = path.relative_to(github_brain_cache() / "fieldstorage").as_posix()
                domain = path.parts[path.parts.index("brain") + 1] if "brain" in path.parts else "brain"
                cid = f"mirror-{path.stem}-{hashlib.md5(rel.encode()).hexdigest()[:10]}"
                c = _chunk(cid, domain, path.stem, raw, rel, ["mirror", domain])
                if c:
                    chunks.append(c)

    seen: set[str] = set()
    unique = []
    for c in chunks:
        if c and c["id"] not in seen:
            seen.add(c["id"])
            unique.append(c)

    corpus = {
        "schema": "hostess7-github-corpus/v1",
        "lane": "github-mirror",
        "version": __version__,
        "updated": _ts(),
        "chunk_count": len(unique),
        "mirror": mirror,
        "github_raw": GITHUB_RAW,
        "chunks": unique,
    }
    manifest = {
        "schema": SCHEMA,
        "lane": "github-mirror",
        "identity": "Hostess7-GitHub",
        "sovereign_identity": "Hostess7",
        "version": __version__,
        "mode": "github-brain-mirror",
        "updated": _ts(),
        "read_only": True,
        "writes_to_sovereign": False,
        "posture": "war-ready",
        "war_ready": True,
        "demo": False,
        "brain": True,
        "pages_url": "https://zacharygeurts.github.io/Hostess7/",
        "repo": "https://github.com/ZacharyGeurts/Hostess7",
        "codespaces": "https://github.com/codespaces/new?hide_repo_select=true&repo=ZacharyGeurts/Hostess7",
        "corpus": "/github-brain/corpus.json",
        "mirror": "/github-brain/mirror.json",
        "github_files": github_files,
        "api": {
            "ask": "/api/ask",
            "status": "/api/status",
            "brain": "/api/brain",
        },
        "loopback_upgrade": "./Hostess7.sh boot",
    }

    docs = github_brain_docs()
    legacy = root / "docs" / "brain"
    if legacy.is_dir():
        shutil.rmtree(legacy)
    (docs / "corpus.json").write_text(json.dumps(corpus, indent=2) + "\n", encoding="utf-8")
    (docs / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    shutil.copy2(github_brain_cache() / "mirror.json", docs / "mirror.json")

    return {"ok": True, "chunks": len(unique), "mirror": mirror, "docs": str(docs)}


def ask_mirror(query: str, *, chunks: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Search github-brain corpus only — no sovereign writes."""
    q = _safe(query)
    if not q:
        return {"ok": False, "error": "empty query", "lane": "github-mirror"}
    if chunks is None:
        corpus_path = github_brain_docs() / "corpus.json"
        if corpus_path.is_file():
            chunks = json.loads(corpus_path.read_text(encoding="utf-8")).get("chunks") or []
        else:
            chunks = []

    tokens = [t for t in re.split(r"[^a-z0-9]+", q.lower()) if len(t) > 2]
    ranked: list[tuple[int, dict[str, Any]]] = []
    for c in chunks:
        hay = f"{c.get('title', '')} {c.get('text', '')}".lower()
        score = sum(3 if len(t) > 5 else 1 for t in tokens if t in hay)
        if score:
            ranked.append((score, c))
    ranked.sort(key=lambda x: -x[0])
    hits = [c for _, c in ranked[:4]]

    if not hits:
        text = (
            "I'm the GitHub brain mirror — same doctrine, isolated from sovereign storage. "
            "Try: wants, KILROY, truth floor, boot. Full agents on loopback after ./Hostess7.sh boot."
        )
    else:
        lines = [f"You asked: {q}", ""]
        for h in hits:
            excerpt = h["text"][:520] + ("…" if len(h["text"]) > 520 else "")
            lines.append(f"• {h['title']}")
            lines.append(excerpt)
            lines.append("")
        lines.append("Lane: github-mirror (sovereign brain not touched)")
        text = "\n".join(lines).strip()

    return {
        "ok": True,
        "text": text,
        "query": q,
        "route": "github-mirror",
        "lane": "github-mirror",
        "hits": [{"id": h["id"], "title": h["title"], "source": h["source"]} for h in hits],
    }


def status_mirror() -> dict[str, Any]:
    docs = github_brain_docs()
    corpus_path = docs / "corpus.json"
    chunk_count = 0
    if corpus_path.is_file():
        chunk_count = json.loads(corpus_path.read_text(encoding="utf-8")).get("chunk_count", 0)
    return {
        "ok": True,
        "name": "Hostess 7 GitHub Brain",
        "version": __version__,
        "mode": "github-brain-mirror",
        "lane": "github-mirror",
        "brain": True,
        "sovereign_brain": False,
        "writes_to_sovereign": False,
        "read_only": True,
        "chunk_count": chunk_count,
        "posture": "war-ready",
        "war_ready": True,
        "demo": False,
        "pages": True,
        "upgrade": "./Hostess7.sh boot",
    }