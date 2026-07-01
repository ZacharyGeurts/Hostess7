#!/usr/bin/env python3
"""Sync GitHub profile README, favorites manifest, and releases pages from live API data."""
from __future__ import annotations

import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

OWNER = "ZacharyGeurts"
PAGES_BASE = f"https://{OWNER.lower()}.github.io"
ROOT = Path(__file__).resolve().parents[1]
SG = ROOT.parent
FAVORITES_PATH = ROOT / "docs" / "github-favorites.json"
PROFILE_README = ROOT / "profile" / "README.md"
PROFILE_DOCS = ROOT / "profile" / "docs"
RELEASES_CSS = PROFILE_DOCS / "releases.css"

# Pin board order (16 public repos)
PIN_ORDER = [
    "AmmoOS", "Grok16", "KILROY", "ZNetwork",
    "AmmoCode", "Field_Primer", "Field_Research", "Final_Eye",
    "World_Redata", "AMOURANTHRTX", "OBS-FieldVoiceFilter", "Kill-Grok-Orphans",
    "memes", "retrotool", "Poop", "ZacharyGeurts",
]

TAGS = {
    "AmmoOS": "field OS",
    "Grok16": "G16 compiler",
    "KILROY": "Field boot",
    "ZNetwork": "smart relayer",
    "AmmoCode": "compiler GUI",
    "Field_Primer": "field primer",
    "Field_Research": "combinatorics manual",
    "Final_Eye": "vision stack",
    "World_Redata": "WRDT1 redata",
    "AMOURANTHRTX": "Field Die",
    "OBS-FieldVoiceFilter": "OBS plugin",
    "Kill-Grok-Orphans": "Grok watchdog",
    "memes": "vision feed",
    "retrotool": "retro tooling",
    "Poop": "misc",
    "ZacharyGeurts": "profile hub",
}

BADGE_VERSIONS = {
    "AmmoOS": "2.0.0-beta4",
    "Grok16": "5.2.0",
    "KILROY": "1.1.0 Sanctuary",
    "ZNetwork": "absorbed-in-KILROY",
    "AmmoCode": "6.0.0-Stack",
}

# GitHub repo name → on-disk tree under SG (AmmoOS ships from NewLatest).
REPO_LOCAL_ROOT: dict[str, str] = {
    "AmmoOS": "NewLatest",
}


def repo_local_dir(repo: str) -> Path:
    return SG / REPO_LOCAL_ROOT.get(repo, repo)


def gh_json(path: str) -> Any:
    proc = subprocess.run(
        ["gh", "api", path],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
    return json.loads(proc.stdout or "null")


def pages_live(url: str) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=8) as resp:
            return 200 <= resp.status < 400
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def human_size(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KiB"
    if n < 1024 * 1024 * 1024:
        return f"{n / (1024 * 1024):.2f} MiB"
    return f"{n / (1024 * 1024 * 1024):.2f} GiB"


def md_escape(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def icon_row(links: dict[str, str | None]) -> str:
    icons = [
        ("pages", "📄", "GitHub Pages"),
        ("releases_page", "📦", "Releases page — SHA-256"),
        ("wiki", "📖", "Wiki"),
        ("releases", "🏷️", "GitHub Releases"),
        ("repo", "💻", "Repository"),
        ("issues", "🐛", "Issues"),
    ]
    parts: list[str] = []
    for key, glyph, label in icons:
        url = links.get(key)
        if not url:
            continue
        tip = f"{label}"
        if key == "releases" and links.get("latest_tag"):
            tip += f" — {links['latest_tag']}"
        parts.append(f'<a href="{url}" title="{tip}">{glyph}</a>')
    if not parts:
        return ""
    return "<br/>" + " ".join(parts)


def pin_block(repo: str, meta: dict[str, Any]) -> str:
    name = meta["name"]
    tag = meta.get("tag") or TAGS.get(repo, "")
    pin_url = meta.get("pin_url") or meta["repo_url"]
    ver = meta.get("latest_tag") or BADGE_VERSIONS.get(repo, "")
    ver_line = f" · `{ver}`" if ver else ""
    links = {
        "pages": meta.get("pages_url"),
        "releases_page": meta.get("releases_page") if meta.get("latest_release") else None,
        "wiki": meta.get("wiki_url") if meta.get("has_wiki") else None,
        "releases": meta.get("releases_url"),
        "repo": meta["repo_url"],
        "issues": meta.get("issues_url"),
        "latest_tag": meta.get("latest_tag"),
    }
    return (
        f"**★ [{name}]({pin_url})**  \n"
        f"{tag}{ver_line}\n"
        f"{icon_row(links)}"
    )


def fetch_repo_meta(repo: str) -> dict[str, Any]:
    doc = gh_json(f"repos/{OWNER}/{repo}")
    pages_url = f"{PAGES_BASE}/{repo}/"
    local_docs = (SG / repo / "docs").is_dir()
    if repo == OWNER:
        local_docs = local_docs or (ROOT / "profile" / "docs").is_dir()
    has_pages = pages_live(pages_url) or local_docs
    pin_url = pages_url if has_pages else doc["html_url"]
    releases_page = f"{pages_url}releases.html" if has_pages else None
    meta: dict[str, Any] = {
        "name": repo,
        "repo": repo,
        "tag": TAGS.get(repo, doc.get("description") or repo),
        "repo_url": doc["html_url"],
        "pin_url": pin_url,
        "pages_url": pages_url if has_pages else None,
        "releases_page": releases_page,
        "wiki_url": f"{doc['html_url']}/wiki",
        "releases_url": f"{doc['html_url']}/releases",
        "issues_url": f"{doc['html_url']}/issues",
        "has_wiki": bool(doc.get("has_wiki")),
        "description": doc.get("description") or "",
        "default_branch": (doc.get("default_branch") or "main"),
    }
    try:
        rel = gh_json(f"repos/{OWNER}/{repo}/releases/latest")
        meta["latest_release"] = {
            "tag": rel.get("tag_name"),
            "name": rel.get("name"),
            "published": rel.get("published_at"),
            "url": rel.get("html_url"),
            "assets": [
                {
                    "name": a.get("name"),
                    "size": a.get("size"),
                    "size_human": human_size(int(a.get("size") or 0)),
                    "digest": (a.get("digest") or "").replace("sha256:", ""),
                    "sha256": (a.get("digest") or "").replace("sha256:", ""),
                    "download_count": a.get("download_count"),
                    "url": a.get("browser_download_url"),
                    "content_type": a.get("content_type"),
                }
                for a in (rel.get("assets") or [])
            ],
        }
        meta["latest_tag"] = rel.get("tag_name")
    except RuntimeError:
        meta["latest_release"] = None
        meta["latest_tag"] = None
    return meta


def build_favorites(metas: list[dict[str, Any]]) -> dict[str, Any]:
    favorites = []
    for m in metas:
        fav: dict[str, Any] = {
            "star": True,
            "name": m["name"],
            "repo": m["repo"],
            "tag": m["tag"],
            "url": m["repo_url"],
            "pin_url": m["pin_url"],
        }
        if m.get("pages_url"):
            fav["pages"] = m["pages_url"]
        if m.get("releases_page") and m.get("latest_release"):
            fav["releases_page"] = m["releases_page"]
        if m.get("has_wiki"):
            fav["wiki"] = m["wiki_url"]
        fav["releases"] = m["releases_url"]
        fav["issues"] = m["issues_url"]
        if m.get("latest_tag"):
            fav["latest_tag"] = m["latest_tag"]
        if m.get("latest_release"):
            fav["latest_release"] = m["latest_release"]
        favorites.append(fav)
    return {
        "schema": "github-favorites/v2",
        "owner": OWNER,
        "title": "Favorites",
        "subtitle": "16 public repos — page-first pins, release SHA manifest.",
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "unlimited": False,
        "pin_count": len(favorites),
        "native_pin_max": 6,
        "pages_base": PAGES_BASE,
        "favorites": favorites,
    }


def profile_readme(metas: list[dict[str, Any]]) -> str:
    by_name = {m["name"]: m for m in metas}
    cols = [PIN_ORDER[i : i + 4] for i in range(0, 16, 4)]
    table_rows = ["<tr>"]
    for col in cols:
        table_rows.append('<td width="25%" valign="top">\n\n')
        blocks = [pin_block(r, by_name[r]) for r in col if r in by_name]
        table_rows.append("\n\n<br/>\n\n".join(blocks))
        table_rows.append("\n\n</td>")
    table_rows.append("</tr>")
    table_body = "".join(table_rows)

    badges = "\n".join(
        f'[![{name}](https://img.shields.io/badge/{name.replace("-", "--")}-{ver}-38bdf8?style=for-the-badge)]({by_name[name]["pin_url"]})'
        for name, ver in [
            ("AmmoOS", "1.9.9h"),
            ("Grok16", "5.0.1"),
            ("KILROY", "1.0.0--Taco"),
            ("ZNetwork", "2.1.0--Stack"),
        ]
        if name in by_name
    )

    return f"""<div align="center">

# ZacharyGeurts

**Field operator · AmmoOS · Grok16 · KILROY · ZNetwork**

{badges}

</div>

## Code first

```bash
git clone https://github.com/{OWNER}/AmmoOS.git
cd AmmoOS && sudo ./install-all.sh
# Browser → http://127.0.0.1:9477/field
```

```bash
export SG_ROOT=/path/to/SG
cd "$SG_ROOT/NewLatest" && ./nexus.sh
```

---

## ★ Pinned — 16 / 16 public repos

> Pins link to **GitHub Pages** when live; icons below: 📄 Pages · 📖 Wiki · 🏷 Releases · 💻 Repo · 🐛 Issues

<table>
{table_body}
</table>

### Icon legend

| Icon | Surface |
|------|---------|
| 📄 | [GitHub Pages]({PAGES_BASE}/) manual / docs |
| 📦 | Releases page on Pages — full asset table + **SHA-256** |
| 📖 | Repository wiki |
| 🏷️ | GitHub Releases — tags and downloads |
| 💻 | Source repository |
| 🐛 | Issues |

### Live surfaces (loopback)

| Surface | URL |
|---------|-----|
| AmmoOS C2 | `http://127.0.0.1:9477/field` |
| Field command | `http://127.0.0.1:9477/command` |
| Queen Browser | `http://127.0.0.1:9481/world/browser.html` |
| AmmoCode Stack | `http://127.0.0.1:9555/` |

---

## Footprint

- **Profile hub:** [{PAGES_BASE}/ZacharyGeurts/]({PAGES_BASE}/ZacharyGeurts/)
- **X:** [@{OWNER}](https://x.com/{OWNER})
- **Favorites manifest:** `docs/github-favorites.json` (v2 — release SHA)

*Field is THE thing.*
"""


def releases_css() -> str:
    return """/* SG stack — release asset tables */
:root {
  --bg: #0a0c12;
  --panel: #141820;
  --text: #e8edf7;
  --dim: #7c8aa3;
  --edge: rgba(148, 163, 184, 0.18);
  --accent: #38bdf8;
  --mono: "JetBrains Mono", Consolas, monospace;
}
* { box-sizing: border-box; }
body {
  margin: 0 auto;
  max-width: 1100px;
  padding: 1.5rem;
  background: var(--bg);
  color: var(--text);
  font: 15px/1.55 system-ui, sans-serif;
}
a { color: var(--accent); }
h1 { font-size: 1.6rem; }
.meta { color: var(--dim); font-size: 0.92rem; }
table {
  width: 100%;
  border-collapse: collapse;
  margin: 1rem 0 2rem;
  font-size: 0.88rem;
}
th, td {
  border: 1px solid var(--edge);
  padding: 0.45rem 0.6rem;
  text-align: left;
  vertical-align: top;
}
th { background: var(--panel); }
.sha { font-family: var(--mono); font-size: 0.75rem; word-break: break-all; }
.num { text-align: right; white-space: nowrap; }
nav { margin-bottom: 1.5rem; }
nav a { margin-right: 0.75rem; }
"""


def releases_html(repo: str, meta: dict[str, Any], all_releases: list[dict[str, Any]] | None = None) -> str:
    rel = meta.get("latest_release")
    pages = meta.get("pages_url") or f"{PAGES_BASE}/{repo}/"
    rels = all_releases or ([rel] if rel else [])
    sections: list[str] = []
    for r in rels:
        if not r:
            continue
        tag = r.get("tag") or r.get("tag_name") or "?"
        name = r.get("name") or tag
        published = (r.get("published") or r.get("published_at") or "")[:10]
        url = r.get("url") or r.get("html_url") or meta["releases_url"]
        rows = []
        for a in r.get("assets") or []:
            sha = a.get("sha256") or a.get("digest", "").replace("sha256:", "")
            rows.append(
                f"<tr>"
                f"<td><a href=\"{a.get('url', '#')}\">{a.get('name', '')}</a></td>"
                f"<td class=\"num\">{a.get('size_human') or human_size(int(a.get('size') or 0))}</td>"
                f"<td class=\"sha\"><code>{sha or '—'}</code></td>"
                f"<td class=\"num\">{a.get('download_count', 0)}</td>"
                f"</tr>"
            )
        asset_table = ""
        if rows:
            asset_table = (
                "<table><thead><tr>"
                "<th>File</th><th>Size</th><th>SHA-256</th><th>↓</th>"
                "</tr></thead><tbody>"
                + "\n".join(rows)
                + "</tbody></table>"
            )
        else:
            asset_table = "<p><em>No release assets — source-only tag.</em></p>"
        sections.append(
            f"<section id=\"{tag}\">"
            f"<h2>{name}</h2>"
            f"<p class=\"meta\">Tag <code>{tag}</code> · published {published} · "
            f"<a href=\"{url}\">GitHub release</a></p>"
            f"{asset_table}"
            f"</section>"
        )
    body = "\n".join(sections) if sections else "<p><em>No releases published yet.</em></p>"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{repo} — Releases</title>
  <meta name="description" content="{repo} release assets — SHA-256 checksums, sizes, downloads." />
  <link rel="stylesheet" href="releases.css" />
  <link rel="canonical" href="{pages}releases.html" />
</head>
<body>
  <nav>
    <a href="index.html">Home</a>
    <a href="{meta['repo_url']}">GitHub</a>
    <a href="{meta['releases_url']}">Releases</a>
    <a href="{meta.get('wiki_url', '#')}">Wiki</a>
  </nav>
  <h1>{repo} — Releases</h1>
  <p class="meta">Auto-synced from GitHub API · verify downloads with SHA-256 below.</p>
  {body}
  <footer class="meta">
    <a href="{pages}">Pages</a> ·
    <a href="https://github.com/{OWNER}/{repo}">Repository</a> ·
    <a href="https://github.com/{OWNER}">@{OWNER}</a>
  </footer>
</body>
</html>
"""


def profile_hub_html(metas: list[dict[str, Any]]) -> str:
    cards = []
    for m in metas:
        if m["name"] == "ZacharyGeurts":
            continue
        icons = icon_row({
            "pages": m.get("pages_url"),
            "wiki": m.get("wiki_url") if m.get("has_wiki") else None,
            "releases": m.get("releases_url"),
            "repo": m["repo_url"],
            "issues": m.get("issues_url"),
            "latest_tag": m.get("latest_tag"),
        }).replace("<br/>", "")
        ver = f" <code>{m['latest_tag']}</code>" if m.get("latest_tag") else ""
        cards.append(
            f'<article class="card">'
            f'<h3><a href="{m["pin_url"]}">{m["name"]}</a></h3>'
            f'<p>{m["tag"]}{ver}</p>'
            f'<p class="icons">{icons}</p>'
            f'</article>'
        )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>@{OWNER} — Profile hub</title>
  <meta name="description" content="16 public repos — pages, wiki, releases with SHA-256." />
  <link rel="stylesheet" href="releases.css" />
  <style>
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 1rem; }}
    .card {{ border: 1px solid var(--edge); border-radius: 10px; padding: 1rem; background: var(--panel); }}
    .card h3 {{ margin: 0 0 0.35rem; font-size: 1.05rem; }}
    .icons a {{ margin-right: 0.35rem; text-decoration: none; font-size: 1.1rem; }}
  </style>
</head>
<body>
  <h1>@{OWNER}</h1>
  <p class="meta">Field operator hub — pins link to Pages first. Icons: 📄 Pages · 📖 Wiki · 🏷 Releases · 💻 Repo · 🐛 Issues</p>
  <nav>
    <a href="https://github.com/{OWNER}/{OWNER}">Profile README</a>
    <a href="{PAGES_BASE}/AmmoOS/">AmmoOS</a>
    <a href="{PAGES_BASE}/Grok16/">Grok16</a>
    <a href="{PAGES_BASE}/Field_Primer/">Field Primer</a>
  </nav>
  <div class="grid">
    {"".join(cards)}
  </div>
</body>
</html>
"""


def fetch_all_releases(repo: str, limit: int = 5) -> list[dict[str, Any]]:
    try:
        rels = gh_json(f"repos/{OWNER}/{repo}/releases?per_page={limit}")
    except RuntimeError:
        return []
    out = []
    for rel in rels:
        out.append({
            "tag": rel.get("tag_name"),
            "name": rel.get("name"),
            "published": rel.get("published_at"),
            "url": rel.get("html_url"),
            "assets": [
                {
                    "name": a.get("name"),
                    "size": a.get("size"),
                    "size_human": human_size(int(a.get("size") or 0)),
                    "digest": (a.get("digest") or "").replace("sha256:", ""),
                    "sha256": (a.get("digest") or "").replace("sha256:", ""),
                    "download_count": a.get("download_count"),
                    "url": a.get("browser_download_url"),
                }
                for a in (rel.get("assets") or [])
            ],
        })
    return out


def write_repo_index(repo: str, meta: dict[str, Any]) -> Path | None:
    """Minimal docs hub when repo has releases but no index.html yet."""
    local = repo_local_dir(repo) / "docs"
    idx = local / "index.html"
    if idx.is_file():
        return None
    if not meta.get("latest_release"):
        return None
    tag = meta.get("latest_tag") or ""
    local.mkdir(parents=True, exist_ok=True)
    idx.write_text(
        f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{repo}</title>
  <link rel="stylesheet" href="releases.css" />
</head>
<body>
  <h1>{repo}</h1>
  <p class="meta">Latest <code>{tag}</code> · field stack project</p>
  <nav>
    <a href="releases.html">Releases — SHA-256</a>
    <a href="{meta['repo_url']}">GitHub</a>
    <a href="{meta['releases_url']}">GitHub Releases</a>
    <a href="https://github.com/{OWNER}">@{OWNER}</a>
  </nav>
</body>
</html>
""",
        encoding="utf-8",
    )
    return idx


def write_repo_releases(repo: str, meta: dict[str, Any]) -> Path | None:
    local = repo_local_dir(repo) / "docs"
    if not local.is_dir():
        local.mkdir(parents=True, exist_ok=True)
    if not meta.get("latest_release") and not repo_local_dir(repo).is_dir():
        return None
    all_rels = fetch_all_releases(repo, limit=8) if meta.get("latest_release") else []
    css_path = local / "releases.css"
    if not css_path.is_file():
        css_path.write_text(releases_css(), encoding="utf-8")
    out = local / "releases.html"
    out.write_text(releases_html(repo, meta, all_rels), encoding="utf-8")
    return out


def main() -> int:
    print(f"sync GitHub profile — {OWNER}")
    metas = []
    for repo in PIN_ORDER:
        try:
            m = fetch_repo_meta(repo)
            metas.append(m)
            n_assets = len((m.get("latest_release") or {}).get("assets") or [])
            print(f"  {repo}: pin→{m['pin_url']} tag={m.get('latest_tag')} assets={n_assets}")
        except Exception as exc:
            print(f"  WARN {repo}: {exc}", file=sys.stderr)

    fav = build_favorites(metas)
    FAVORITES_PATH.parent.mkdir(parents=True, exist_ok=True)
    FAVORITES_PATH.write_text(json.dumps(fav, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {FAVORITES_PATH}")

    PROFILE_README.parent.mkdir(parents=True, exist_ok=True)
    PROFILE_README.write_text(profile_readme(metas), encoding="utf-8")
    print(f"wrote {PROFILE_README}")

    PROFILE_DOCS.mkdir(parents=True, exist_ok=True)
    RELEASES_CSS.write_text(releases_css(), encoding="utf-8")
    (PROFILE_DOCS / "index.html").write_text(profile_hub_html(metas), encoding="utf-8")
    print(f"wrote {PROFILE_DOCS}/index.html")

    for m in metas:
        if m.get("latest_release"):
            write_repo_index(m["name"], m)
            p = write_repo_releases(m["name"], m)
            if p:
                print(f"  releases → {p}")

    # Mirror profile README to AmmoOS (NewLatest) profile path
    ammo_profile = repo_local_dir("AmmoOS") / "profile" / "README.md"
    ammo_profile.parent.mkdir(parents=True, exist_ok=True)
    ammo_profile.write_text(PROFILE_README.read_text(encoding="utf-8"), encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())