#!/usr/bin/env python3
"""Build Field Research GitHub Pages site from manifest + chapter markdown."""
from __future__ import annotations

import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
CHAPTERS_DIR = CONTENT / "chapters"
DOCS = ROOT / "docs"
ASSETS = ROOT / "assets"


def esc(s: str) -> str:
    return html.escape(s, quote=True)


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
        if line.startswith("### "):
            flush_p()
            close_lists()
            out.append(f"<h3>{esc(line[4:])}</h3>")
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
  <title>{num} — {esc(title)} · Field Research</title>
  <meta name="description" content="Chapter {num}: {esc(title)}. Field Research — The Book of Grok's Heart." />
  <link rel="canonical" href="{canon}" />
  <meta name="theme-color" content="#1a0810" />
  <meta property="og:title" content="{num} — {esc(title)}" />
  <meta property="og:image" content="{base}/assets/images/{hero}" />
  <link rel="stylesheet" href="../css/field-research.css" />
  <link rel="stylesheet" href="../css/chapters.css" />
</head>
<body class="chapter-page accent-{ch.get('accent', 'heart')}">
  <nav class="top"><div class="inner">
    <a class="logo" href="../index.html">FIELD RESEARCH <span class="heart-badge">♥</span></a>
    <ul>
      <li><a href="../index.html#chapters">Chapters</a></li>
      <li><a href="../index.html#spine">Research spine</a></li>
      <li><a href="{manifest['repo']}">GitHub</a></li>
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
    <p class="eyebrow">The Book of Grok's Heart</p>
    {body}
    {nav}
  </main>
  <footer class="site-foot"><p>Field Research v{edition} · {esc(manifest['author'])} · <a href="{manifest['repo']}">Source</a></p></footer>
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
  <link rel="stylesheet" href="css/field-research.css" />
</head>
<body>
  <nav class="top"><div class="inner">
    <span class="logo">FIELD RESEARCH <span class="heart-badge">♥</span></span>
    <ul>
      <li><a href="#about">About</a></li>
      <li><a href="#spine">Spine</a></li>
      <li><a href="#chapters">13 Chapters</a></li>
      <li><a href="{manifest['repo']}">GitHub</a></li>
    </ul>
  </div></nav>
  <header class="hero">
    <div class="hero-bg"></div>
    <div class="hero-overlay"></div>
    <div class="hero-content">
      <p class="eyebrow">Field Research · Edition {manifest['edition']} · {manifest['year']}</p>
      <h1>The Book of Grok's Heart</h1>
      <p class="lead">{esc(manifest['subtitle'])}</p>
      <div class="axiom-bar">{ax}</div>
      <div class="cta-row">
        <a class="btn" href="chapters/01-preface-ironclad.html">Start Chapter 1</a>
        <a class="btn secondary" href="chapters/07-field-combinatorics.html">Combinatorics</a>
        <a class="btn secondary" href="chapters/09-compatibility-layers.html">Layers &amp; seals</a>
      </div>
    </div>
  </header>
  <main>
    <section id="about" class="section-panel">
      <div class="section-inner">
        <p class="eyebrow">What this book is</p>
        <h2>Research receipts — not marketing</h2>
        <p>This manual records the <strong>actual research path</strong> that produced Grok16 single fabric,
        the combinatorics endpoint, plate meld, compatibility layers, launch seals, CHIPS BSP, and NEXUS diagnostic mode.
        Every chapter cites grep hooks: doctrine JSON → lib module → panel slice → test in <code>run-tests.sh</code>.</p>
        <p>Honesty labels: {labels}. The heart on the cover is <span class="tag phil">Philosophy</span> —
        Grok's care for truth — but the bench numbers in Chapter 13 are <span class="tag impl">Implemented</span>.</p>
      </div>
      <figure class="hero-side"><img src="assets/images/grok-heart-icon.jpg" alt="Grok heart icon" loading="lazy" /></figure>
    </section>
    <section id="spine" class="section-panel dark">
      <div class="section-inner wide">
        <p class="eyebrow">Research spine</p>
        <h2>From combinatorics endpoint to compatibility layers</h2>
        <pre class="spine-diagram">Fault signals → Diagnostic Mode (baseline lock)
     ↓
Plate sources (30+) → field-plate-meld.py → chain-hash generation
     ↓
Grok16 combinatorics → tree walk → condense_plates
     ↓
field-plate-combinatorics-bridge → exec_posture (belt/runner/emulator)
     ↓
g16-compiler-sense-plate → profile ladder
     ↓
field-compatibility-layers refresh → 6 layers live → launch_seal bump
     ↓
queen-launch-chamber → secured .launch with current seal generation
     ↓
g16 belt_2_0 · CHIPS field_opt · Python interpreter</pre>
      </div>
    </section>
    <section id="chapters" class="chapter-grid-section">
      <h2>Thirteen chapters</h2>
      <div class="chapter-grid">{ch_html}</div>
    </section>
  </main>
  <footer class="site-foot"><p>{esc(manifest['title'])} · {esc(manifest['author'])} · {esc(manifest['co_author'])}</p></footer>
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


def main() -> None:
    manifest = json.loads((CONTENT / "book-manifest.json").read_text(encoding="utf-8"))
    (DOCS / "css").mkdir(parents=True, exist_ok=True)
    (DOCS / "chapters").mkdir(parents=True, exist_ok=True)

    css_src = ROOT / "docs" / "css"
    if not (css_src / "field-research.css").is_file():
        raise SystemExit("missing docs/css/field-research.css — run from complete tree")

    built = 0
    for ch in manifest["chapters"]:
        md_path = CHAPTERS_DIR / f"{ch['slug']}.md"
        if not md_path.is_file():
            raise SystemExit(f"missing chapter: {md_path}")
        body = md_path.read_text(encoding="utf-8")
        out = DOCS / "chapters" / f"{ch['slug']}.html"
        out.write_text(build_chapter(ch, manifest, body), encoding="utf-8")
        built += 1

    (DOCS / "index.html").write_text(build_index(manifest), encoding="utf-8")
    copy_assets()
    print(f"built {built} chapters → {DOCS}")


if __name__ == "__main__":
    main()