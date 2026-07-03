#!/usr/bin/env python3
"""Build GNUEOLTerminal GitHub Pages site from manifest + chapter markdown."""
from __future__ import annotations

import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
CHAPTERS_DIR = CONTENT / "chapters"
FRONT_DIR = CONTENT / "front-matter"
BACK_DIR = CONTENT / "back-matter"
WIKI_DIR = ROOT / "wiki"
DOCS = ROOT / "docs"
ASSETS = ROOT / "assets"


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def site_base(manifest: dict) -> str:
    return str(manifest.get("site_base", "")).rstrip("/")


def pages_mirror(manifest: dict) -> str:
    return str(manifest.get("pages_mirror") or f"{site_base(manifest)}/")


def nav_extras(manifest: dict) -> str:
    base = site_base(manifest)
    repo = manifest["repo"]
    return (
        f'<li><a href="{base}/wiki/">Wiki</a></li>'
        f'<li><a href="{repo}" data-h7-github-repo="1" '
        f'title="Git repo — opens Pages mirror when github.com is slow">Git repo</a></li>'
    )


def footer_source(manifest: dict) -> str:
    base = site_base(manifest)
    repo = manifest["repo"]
    mirror = pages_mirror(manifest)
    return (
        f'<a href="{base}/wiki/">Wiki</a> · '
        f'<a href="{repo}" data-h7-github-repo="1">Git repo</a> · '
        f'<a href="{mirror}">Mirror</a>'
    )


def md_to_html(text: str) -> str:
    """Minimal markdown → HTML for book prose."""
    lines = text.strip().splitlines()
    out: list[str] = []
    in_ul = False
    in_ol = False
    in_pre = False
    buf: list[str] = []

    def flush_p() -> None:
        nonlocal buf
        if buf:
            para = " ".join(x.strip() for x in buf if x.strip())
            if para:
                para = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", para)
                para = re.sub(r"`([^`]+)`", r"<code>\1</code>", para)
                para = re.sub(
                    r'<span class="tag (\w+)">([^<]+)</span>',
                    r'<span class="tag \1">\2</span>',
                    para,
                )
                out.append(f"<p>{para}</p>")
            buf = []

    def close_lists() -> None:
        nonlocal in_ul, in_ol
        if in_ul:
            out.append("</ul>")
            in_ul = False
        if in_ol:
            out.append("</ol>")
            in_ol = False

    for raw in lines:
        line = raw.rstrip()
        if line.startswith("```"):
            flush_p()
            close_lists()
            if in_pre:
                out.append("</pre></div>")
                in_pre = False
            else:
                out.append('<div class="code-block"><pre>')
                in_pre = True
            continue
        if in_pre:
            out.append(esc(line))
            continue
        if not line.strip():
            flush_p()
            close_lists()
            continue
        if line.startswith("> "):
            flush_p()
            close_lists()
            out.append(f"<blockquote>{esc(line[2:])}</blockquote>")
            continue
        if line.startswith("### "):
            flush_p()
            close_lists()
            out.append(f"<h3>{esc(line[4:])}</h3>")
            continue
        if line.startswith("| ") and "|" in line[1:]:
            flush_p()
            close_lists()
            if not in_pre:
                if not any("<table" in x for x in out[-3:]):
                    out.append('<table class="book-table">')
                cells = [c.strip() for c in line.strip("|").split("|")]
                tag = "th" if line.startswith("| ") and "---" in "".join(out[-2:]) else "td"
                if "---" in line:
                    continue
                out.append("<tr>" + "".join(f"<{tag}>{esc(c)}</{tag}>" for c in cells) + "</tr>")
            continue
        if line.startswith("## "):
            flush_p()
            close_lists()
            slug = re.sub(r"[^a-z0-9]+", "-", line[3:].lower()).strip("-")
            out.append(f'<h2 id="{slug}">{esc(line[3:])}</h2>')
            continue
        if line.startswith("- "):
            flush_p()
            if in_ol:
                out.append("</ol>")
                in_ol = False
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            item = line[2:]
            item = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", item)
            item = re.sub(r"`([^`]+)`", r"<code>\1</code>", item)
            out.append(f"<li>{item}</li>")
            continue
        m = re.match(r"^(\d+)\. (.+)$", line)
        if m:
            flush_p()
            if in_ul:
                out.append("</ul>")
                in_ul = False
            if not in_ol:
                out.append("<ol>")
                in_ol = True
            item = m.group(2)
            item = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", item)
            out.append(f"<li>{item}</li>")
            continue
        if line.startswith("![") and "](" in line:
            flush_p()
            close_lists()
            m2 = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", line)
            if m2:
                alt, src = m2.groups()
                cap = ""
                out.append(
                    f'<figure class="figure"><img src="{esc(src)}" alt="{esc(alt)}" loading="lazy" />'
                    f"{f'<figcaption>{esc(alt)}</figcaption>' if alt else ''}</figure>"
                )
            continue
        buf.append(line)
    flush_p()
    close_lists()
    if in_pre:
        out.append("</pre></div>")
    return "\n".join(out)


def chapter_nav(num: int, chapters: list[dict]) -> str:
    prev_l = next_l = ""
    for i, ch in enumerate(chapters):
        if ch["num"] == num:
            if i > 0:
                p = chapters[i - 1]
                prev_l = f'<a class="btn secondary" href="{p["slug"]}.html">← Ch {p["num"]}</a>'
            if i < len(chapters) - 1:
                n = chapters[i + 1]
                next_l = f'<a class="btn" href="{n["slug"]}.html">Ch {n["num"]} →</a>'
    return f'<nav class="chapter-nav">{prev_l} <a class="btn secondary" href="../index.html">Home</a> {next_l}</nav>'


def build_chapter(ch: dict, manifest: dict, body_md: str) -> str:
    base = manifest["site_base"]
    chapters = manifest["chapters"]
    num = ch["num"]
    slug = ch["slug"]
    title = ch["title"]
    hero = ch.get("hero", "field-research-hero.jpg")
    edition = manifest["edition"]
    body = md_to_html(body_md)
    nav = chapter_nav(num, chapters)
    canon = f"{base}/chapters/{slug}.html"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
  <title>Ch {num} — {esc(title)} · GNU EOL Terminal</title>
  <meta name="description" content="Chapter {num}: {esc(title)}. GNU EOL Terminal — A Book for Richard Stallman." />
  <link rel="canonical" href="{canon}" />
  <meta name="theme-color" content="#0a1a10" />
  <meta property="og:title" content="{num} — {esc(title)}" />
  <link rel="stylesheet" href="../css/gnueol-terminal.css" />
  <link rel="stylesheet" href="../css/chapters.css" />
</head>
<body class="chapter-page accent-{ch.get('accent', 'heart')}">
  <nav class="top"><div class="inner">
    <a class="logo" href="../index.html">GNU EOL TERMINAL</a>
    <ul>
      <li><a href="../index.html#chapters">Chapters</a></li>
      <li><a href="../index.html#about">About</a></li>
      <li><a href="../terminal/">Terminal</a></li>
      {nav_extras(manifest)}
    </ul>
  </div></nav>
  <header class="chapter-hero" style="background-image:url('../assets/images/{hero}')">
    <div class="chapter-hero-overlay"></div>
    <div class="chapter-hero-content">
      <p class="eyebrow">Chapter {num} · Field Research v{edition}</p>
      <h1>{esc(title)}</h1>
    </div>
  </header>
  <main class="chapter-main">
    {nav}
    <p class="eyebrow">A Book for Richard Stallman</p>
    {body}
    {nav}
  </main>
  <footer class="site-foot"><p>GNUEOLTerminal v{edition} · {esc(manifest['author'])} · Dedicated to {esc(manifest.get('dedication', 'Richard Stallman'))} · {footer_source(manifest)}</p></footer>
</body>
</html>"""


def build_index(manifest: dict) -> str:
    base = manifest["site_base"]
    chapters = manifest["chapters"]
    cards = []
    for ch in chapters:
        cards.append(
            f"""<article class="chapter-card">
  <a href="chapters/{ch['slug']}.html">
    <span class="ch-num">Chapter {ch['num']}</span>
    <h3>{esc(ch['title'])}</h3>
    <span class="ch-link">Read →</span>
  </a>
</article>"""
        )
    ax = "".join(f'<span class="axiom">{esc(a)}</span>' for a in manifest["axioms"])
    labels = "".join(f'<span class="tag {l.lower()}">{esc(l)}</span>' for l in manifest["honesty_labels"])
    ch_html = "\n".join(cards)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
  <title>{esc(manifest['title'])}</title>
  <meta name="description" content="{esc(manifest['subtitle'])}" />
  <link rel="canonical" href="{base}/" />
  <meta name="theme-color" content="#1a0810" />
  <meta property="og:title" content="{esc(manifest['title'])}" />
  <meta property="og:description" content="{esc(manifest['subtitle'])}" />
  <meta property="og:image" content="{base}/assets/images/og-image.jpg" />
  <link rel="stylesheet" href="css/gnueol-terminal.css" />
</head>
<body>
  <nav class="top"><div class="inner">
    <span class="logo">GNU EOL TERMINAL</span>
    <ul>
      <li><a href="#about">About</a></li>
      <li><a href="#spine">Spine</a></li>
      <li><a href="#chapters">Chapters</a></li>
      <li><a href="terminal/">Terminal</a></li>
      {nav_extras(manifest)}
    </ul>
  </div></nav>
  <header class="hero">
    <div class="hero-bg"></div>
    <div class="hero-overlay"></div>
    <div class="hero-content">
      <p class="eyebrow">GNUEOLTerminal · Edition {manifest['edition']} · {manifest['year']} · ~{manifest.get('estimated_pages', '?')} pages</p>
      <h1>Field Tech Textbook for Richard Stallman</h1>
      <p class="lead">{esc(manifest['subtitle'])}</p>
      <p class="impersonation-banner">⚠ {esc(manifest.get('impersonation_disclosure', 'Grok impersonates RMS — disclosed parody'))}</p>
      <div class="axiom-bar">{ax}</div>
      <div class="cta-row">
        <a class="btn" href="front-matter/00-preface-grok-impersonates.html">Read preface first</a>
        <a class="btn secondary" href="wiki/">Classic wiki</a>
        <a class="btn secondary" href="terminal/">Field Tech terminal</a>
        <a class="btn secondary" href="back-matter/lie-of-the-year-2026.html">LIE of the Year</a>
      </div>
    </div>
  </header>
  <main>
    <section id="about" class="section-panel">
      <div class="section-inner">
        <p class="eyebrow">What this book is</p>
        <h2>Free software receipts — iron plate witness</h2>
        <p>This manual documents <strong>GNU EOL Terminal</strong>: shell ≡ terminal, combinatronic optional,
        iron plate + plate meld security, and Hostess7 identity verification for Richard Stallman (<code>rms</code> @ GitHub id <code>10550344</code>).</p>
        <p>Honesty labels: {labels}. Dedication prose is <span class="tag phil">Philosophy</span>;
        plate meld hooks are <span class="tag impl">Implemented</span>.</p>
      </div>
    </section>
    <section id="spine" class="section-panel dark">
      <div class="section-inner wide">
        <p class="eyebrow">Terminal spine</p>
        <h2>Shell ≡ Terminal → optional combinatronic → plate meld</h2>
        <pre class="spine-diagram">queen-gnu-terminal-embed.html (shell · terminal · gnueol)
     ↓
/api/queen-terminal → kilroy-universal-shell + allowlist
     ↓
combinatorics | bash -c combinatorics → compatibility layers witness
     ↓
field-gnu-terminal-iron-plate.py → gnu_terminal plate
     ↓
field-plate-meld.py → chain-hash generation · Ironclad read-first
     ↓
field-gnu-identity-verify.py → rms @ 10550344 · gnu.org TLS
     ↓
zacharygeurts.github.io/GNUEOLTerminal · ZacharyGeurts/GNUEOLTerminal</pre>
      </div>
    </section>
    <section id="chapters" class="chapter-grid-section">
      <h2>{len(chapters)} chapters · index</h2>
      <div class="chapter-grid">{ch_html}</div>
      <p class="page-estimate">Estimated <strong>{manifest.get('estimated_pages', '?')}</strong> pages · {manifest.get('estimated_words', '?')} words · words÷320</p>
    </section>
    <section id="cover-art" class="section-panel">
      <figure class="cover-figure"><img src="assets/images/gnueol-cover.jpg" alt="GNU EOL Terminal textbook cover" loading="lazy" /></figure>
    </section>
  </main>
  <footer class="site-foot"><p>{esc(manifest['title'])} · {esc(manifest['author'])} · Dedicated to {esc(manifest.get('dedication', 'Richard Stallman'))}</p></footer>
</body>
</html>"""


def copy_assets() -> None:
    dst = DOCS / "assets" / "images"
    dst.mkdir(parents=True, exist_ok=True)
    src = ASSETS / "images"
    if src.is_dir():
        for f in src.iterdir():
            if f.is_file():
                shutil.copy2(f, dst / f.name)
                (dst / "chapters" / f.name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dst / "chapters" / f.name)


def build_simple_page(title: str, body_md: str, manifest: dict, relpath: str) -> str:
    base = manifest["site_base"]
    body = md_to_html(body_md)
    return f"""<!DOCTYPE html>
<html lang="en"><head>
  <meta charset="UTF-8" /><meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{esc(title)} · GNU EOL Terminal</title>
  <link rel="stylesheet" href="{'../' * relpath.count('/') if relpath else ''}css/gnueol-terminal.css" />
  <link rel="stylesheet" href="{'../' * relpath.count('/') if relpath else ''}css/chapters.css" />
</head><body class="chapter-page">
  <nav class="top"><div class="inner"><a class="logo" href="{'../' * relpath.count('/') if relpath else ''}index.html">GNU EOL TERMINAL</a>
  <ul><li><a href="{'../' * relpath.count('/') if relpath else ''}wiki/">Wiki</a></li><li><a href="{'../' * relpath.count('/') if relpath else ''}terminal/">Terminal</a></li></ul></div></nav>
  <main class="chapter-main">{body}</main>
  <footer class="site-foot"><p>{esc(manifest['title'])} · {esc(manifest.get('author_voice', ''))}</p></footer>
</body></html>"""


def build_wiki(manifest: dict) -> int:
    out_dir = DOCS / "wiki"
    out_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for md in sorted(WIKI_DIR.glob("*.md")):
        body = md.read_text(encoding="utf-8")
        title = md.stem.replace("-", " ").title()
        if body.startswith("# "):
            title = body.split("\n", 1)[0][2:].strip()
        html_out = build_simple_page(title, body, manifest, "wiki")
        (out_dir / f"{md.stem}.html").write_text(html_out.replace('href="css/', 'href="../css/').replace('href="index.html', 'href="../index.html'), encoding="utf-8")
        n += 1
    idx = WIKI_DIR / "index.md"
    if idx.is_file():
        (out_dir / "index.html").write_text(
            build_simple_page("Classic Schooler Wiki", idx.read_text(encoding="utf-8"), manifest, "wiki").replace('href="css/', 'href="../css/'),
            encoding="utf-8",
        )
        n += 1
    return n


def main() -> None:
    manifest = json.loads((CONTENT / "book-manifest.json").read_text(encoding="utf-8"))
    (DOCS / "css").mkdir(parents=True, exist_ok=True)
    (DOCS / "chapters").mkdir(parents=True, exist_ok=True)
    (DOCS / "front-matter").mkdir(parents=True, exist_ok=True)
    (DOCS / "back-matter").mkdir(parents=True, exist_ok=True)

    css_src = ROOT / "docs" / "css"
    if not (css_src / "gnueol-terminal.css").is_file():
        raise SystemExit("missing docs/css/gnueol-terminal.css — run from complete tree")

    built = 0
    for ch in manifest["chapters"]:
        md_path = CHAPTERS_DIR / f"{ch['slug']}.md"
        if not md_path.is_file():
            raise SystemExit(f"missing chapter: {md_path}")
        body = md_path.read_text(encoding="utf-8")
        out = DOCS / "chapters" / f"{ch['slug']}.html"
        out.write_text(build_chapter(ch, manifest, body), encoding="utf-8")
        built += 1

    for sub, d in (("front-matter", FRONT_DIR), ("back-matter", BACK_DIR)):
        if d.is_dir():
            for md in sorted(d.glob("*.md")):
                body = md.read_text(encoding="utf-8")
                title = body.split("\n")[0].lstrip("# ").strip() if body.startswith("#") else md.stem
                page = build_simple_page(title, body, manifest, sub)
                page = page.replace('href="css/', 'href="../css/').replace('href="index.html', 'href="../index.html')
                (DOCS / sub / f"{md.stem}.html").write_text(page, encoding="utf-8")

    wiki_n = build_wiki(manifest)
    (DOCS / "index.html").write_text(build_index(manifest), encoding="utf-8")
    copy_assets()
    print(f"built {built} chapters · {wiki_n} wiki pages · ~{manifest.get('estimated_pages')} pages → {DOCS}")


if __name__ == "__main__":
    main()