#!/usr/bin/env python3
"""Rebuild AmmoOS GitHub Pages manual (docs/)."""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
sys.path.insert(0, str(REPO_ROOT / "lib"))
import page_github_chrome as gh_chrome  # noqa: E402

GITHUB_REPO = "https://github.com/ZacharyGeurts/AmmoOS"
VER_DOC = REPO_ROOT / "data" / "ammoos-version.json"
PLAT_DOC = REPO_ROOT / "data" / "ammoos-platform-release.json"
CACHE = "3"
FAV_DOC = ROOT / "github-favorites.json"

VER = "1.0.1-beta"
SURFACES: dict[str, str] = {}
if VER_DOC.is_file():
    v = json.loads(VER_DOC.read_text(encoding="utf-8"))
    VER = v.get("version", VER)
    SURFACES = v.get("surfaces", {})

NAV = [
    ("index.html", "Home"),
    ("getting-started.html", "Getting Started"),
    ("launch-surfaces.html", "Launch Surfaces"),
    ("update-your-os.html", "Software Updates"),
    ("combinatronic.html", "Combinatronic"),
    ("platforms.html", "Platforms"),
    ("io.html", "Field I/O"),
    ("queen-browser.html", "Queen Browser"),
    ("architecture.html", "Architecture"),
    ("profile.html", "Profile"),
    ("stack-hub.html", "Stack Hub"),
]


def head(title: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
  <title>AmmoOS — {title}</title>
  <meta name="description" content="AmmoOS {VER} beta manual — field OS, browser surfaces, combinatronic engine." />
  <link rel="canonical" href="https://zacharygeurts.github.io/AmmoOS/{'index.html' if title == 'Home' else title.lower().replace(' ', '-') + '.html'}" />
  <link rel="stylesheet" href="manual.css?v{CACHE}" />
  <style>{gh_chrome.chrome_css()}</style>
</head>
<body>
{gh_chrome.chrome_top(GITHUB_REPO, label="ZacharyGeurts/AmmoOS")}
"""


def nav(current: str = "index.html") -> str:
    links = "\n".join(
        f'      <a href="{h}"{" aria-current=\"page\"" if h == current else ""}>{l}</a>'
        for h, l in NAV
    )
    return f"""  <nav>
    <div class="nav-top">
      <div class="nav-brand">
        <strong>AmmoOS C2</strong>
        <span class="nav-version">{VER} beta</span>
      </div>
      <div class="nav-profile">
        <a href="https://github.com/ZacharyGeurts">@ZacharyGeurts</a>
        · <a href="profile.html">Profile</a>
      </div>
    </div>
    <div class="nav-links">
{links}
      <a href="https://github.com/ZacharyGeurts/AmmoOS">GitHub</a>
    </div>
  </nav>
"""


def code_first_block() -> str:
    field_url = SURFACES.get("host_desktop", "http://127.0.0.1:9477/field")
    return f"""  <section class="code-first" aria-label="Quick code layout">
    <div class="code-first-head">
      <span class="code-first-label">Code first</span>
      <span class="code-first-note">Clone · install · open C2 <code>{field_url}</code></span>
    </div>
    <pre><code>git clone https://github.com/ZacharyGeurts/AmmoOS.git
cd AmmoOS
sudo ./install-all.sh
# dev tree:
export SG_ROOT=/path/to/SG && ./nexus.sh</code></pre>
    <div class="code-first-actions">
      <a href="getting-started.html">Install guide</a>
      <a href="{field_url}">Open /field</a>
      <a href="https://github.com/ZacharyGeurts">GitHub profile</a>
    </div>
  </section>
"""


def favorites_wall() -> str:
    if not FAV_DOC.is_file():
        return ""
    doc = json.loads(FAV_DOC.read_text(encoding="utf-8"))
    cards = []
    for fav in doc.get("favorites") or []:
        name = fav.get("name") or "?"
        url = fav.get("url") or "#"
        tag = fav.get("tag") or ""
        repo = fav.get("repo") or ""
        local = " local" if fav.get("local") else ""
        star = "★" if fav.get("star", True) else "☆"
        repo_line = f'<span class="fav-repo">{repo}</span>' if repo else ""
        cards.append(
            f'    <a class="fav-card{local}" href="{url}" rel="noopener">'
            f'<div class="fav-card-top"><span class="fav-star" aria-hidden="true">{star}</span>'
            f'<span class="fav-name">{name}</span></div>'
            f'<span class="fav-tag">{tag}</span>{repo_line}</a>'
        )
    grid = "\n".join(cards)
    subtitle = doc.get("subtitle") or "Unlimited favorites — no cap on starred projects."
    return f"""  <section class="favorites-wall" aria-label="GitHub favorites">
    <div class="favorites-head">
      <h2><span class="star-mark" aria-hidden="true">★</span> {doc.get("title", "Favorites")}</h2>
      <p class="favorites-sub">{subtitle}</p>
    </div>
    <div class="favorites-grid">
{grid}
    </div>
  </section>
"""


def foot() -> str:
    return f"""{gh_chrome.chrome_bottom(GITHUB_REPO, label="ZacharyGeurts/AmmoOS", version=VER)}
  <footer>
    <a href="index.html">Home</a> ·
    <a href="https://github.com/ZacharyGeurts/AmmoOS/releases/tag/v{VER}">Release v{VER}</a> ·
    <a href="https://github.com/ZacharyGeurts/AmmoOS">GitHub</a> ·
    <a href="https://zacharygeurts.github.io/ZacharyGeurts/stack.html">Stack hub</a>
    <p class="footer-meta">AmmoOS {VER} · field OS beta · GPLv3</p>
  </footer>
</body>
</html>
"""


def page(title: str, body: str, *, current: str = "index.html", shell: bool = True) -> str:
    prefix = code_first_block() + favorites_wall() if shell else ""
    return head(title) + nav(current) + prefix + body + foot()


def readme_html(md: str) -> str:
    lines = md.splitlines()
    parts: list[str] = []
    in_code = False
    buf: list[str] = []
    for line in lines:
        if line.startswith("```"):
            if in_code:
                parts.append(f"<pre><code>{''.join(buf)}</code></pre>")
                buf, in_code = [], False
            else:
                in_code, buf = True, []
            continue
        if in_code:
            buf.append(line + "\n")
            continue
        if line.startswith("|") and "|" in line[1:]:
            continue
        if m := re.match(r"^#{1,6}\s+(.*)$", line):
            lvl = len(m.group(0).split()[0])
            parts.append(f"<h{lvl}>{m.group(1)}</h{lvl}>")
        elif line.strip().startswith("!["):
            parts.append(f"<p>{line}</p>")
        elif line.strip():
            parts.append(f"<p>{line}</p>")
    return "\n".join(parts)


def platform_table() -> str:
    if not PLAT_DOC.is_file():
        return "<tr><td colspan=\"4\">See data/ammoos-platform-release.json</td></tr>"
    doc = json.loads(PLAT_DOC.read_text(encoding="utf-8"))
    rows = []
    for p in doc.get("platforms", []):
        boot = p.get("bootstrap", {})
        boot_s = ", ".join(f"<code>{k}</code>" for k in boot)
        rows.append(
            f"    <tr><td><code>{p['id']}</code></td><td>{p['os']}</td>"
            f"<td>{p['arch']}</td><td>{boot_s}</td></tr>"
        )
    return "\n".join(rows)


def surface_rows() -> str:
    rows = []
    labels = {
        "host_desktop": "Host desktop",
        "field_command": "Field command",
        "queen_browser": "Queen Browser",
        "underlay_f9": "Underlay F9",
        "training_viewer": "Training viewer",
    }
    for key, url in SURFACES.items():
        rows.append(f"    <tr><td>{labels.get(key, key)}</td><td><code>{url}</code></td><td>Browser</td></tr>")
    rows.append(
        '    <tr><td>Queen shell</td><td><code>Queen/build/rtx/bin/Linux/queen-browser</code></td><td>Native</td></tr>'
    )
    rows.append('    <tr><td>Dev launcher</td><td><code>./nexus.sh</code></td><td>Native</td></tr>')
    return "\n".join(rows)


def write_pages() -> None:
    readme_path = REPO_ROOT / "README-AMMOOS.md"
    readme_body = ""
    if readme_path.is_file():
        readme_body = f"""
  <article class="readme-prose">
{readme_html(readme_path.read_text(encoding="utf-8"))}
  </article>
"""

    pages = {
        "index.html": (
            "Home",
            f"""
  <img class="hero-img" src="images/hero-banner.svg" width="1200" height="320" alt="AmmoOS field OS banner" />
  <h1>AmmoOS Programmer &amp; Operator Manual</h1>
  <p class="lead"><strong>AmmoOS {VER}</strong> — field operating system beta. Every component launches in your <strong>browser</strong> or as a <strong>native program</strong>. Combinatronic rebalance wires the engine before boot.</p>
  <div class="workflow">
    <a href="getting-started.html"><strong>1 Install</strong>Linux / Windows / macOS</a>
    <a href="launch-surfaces.html"><strong>2 Launch</strong>Browser + native paths</a>
    <a href="combinatronic.html"><strong>3 Combinatronic</strong>Rebalance pipeline</a>
    <a href="platforms.html"><strong>4 Platforms</strong>10 target families</a>
    <a href="io.html"><strong>5 Field I/O</strong>Panel HTTP API</a>
  </div>
{readme_body}
""",
        ),
        "getting-started.html": (
            "Getting Started",
            f"""
  <h1>Getting Started</h1>
  <p>AmmoOS <strong>{VER}</strong> installs from source. Production deploy uses <code>install-all.sh</code>; development uses <code>nexus.sh</code>.</p>
  <h2>Linux x86_64</h2>
  <pre><code>git clone https://github.com/ZacharyGeurts/AmmoOS.git
cd AmmoOS
sudo ./install-all.sh</code></pre>
  <p>Browser opens <code>{SURFACES.get('host_desktop', 'http://127.0.0.1:9477/field')}</code> on start.</p>
  <h2>Development tree</h2>
  <pre><code>export SG_ROOT=/path/to/SG
./scripts/ammoos-beta-pipeline.sh
./nexus.sh</code></pre>
  <h2>Windows</h2>
  <pre><code># PowerShell (see stealth.ps1 in release assets)
# Or WSL2:
tar -xzf ammoos-{VER}-source.tar.gz && cd ammoos-{VER}
sudo ./install-all.sh</code></pre>
  <h2>Verify</h2>
  <pre><code>./scripts/ammoos-launch-verify.sh</code></pre>
""",
        ),
        "update-your-os.html": (
            "Software Updates",
            f"""
  <h1>Software Update Manager</h1>
  <p>Update AmmoOS safely from inside the field — GitHub releases, component tracking, global update lock.</p>
  <h2>Open in browser</h2>
  <pre><code>{SURFACES.get('host_desktop', 'http://127.0.0.1:9477/field').replace('/field', '/ammoos-update-os')}</code></pre>
  <h2>API</h2>
  <pre><code>curl -s http://127.0.0.1:9477/api/ammoos-update/check | jq .
curl -s -X POST http://127.0.0.1:9477/api/ammoos-update/apply</code></pre>
  <p>Queen Browser chip uses the same lock — only one update at a time.</p>
""",
        ),
        "launch-surfaces.html": (
            "Launch Surfaces",
            f"""
  <h1>Launch surfaces</h1>
  <p>Policy: <strong>browser or native program</strong> — no orphan components.</p>
  <table>
    <tr><th>Surface</th><th>Path</th><th>Kind</th></tr>
{surface_rows()}
  </table>
  <h2>Verify registry</h2>
  <pre><code>./scripts/ammoos-launch-verify.sh
cat .nexus-state/ammoos-launch-registry.json</code></pre>
""",
        ),
        "combinatronic.html": (
            "Combinatronic",
            """
  <h1>Combinatronic integration</h1>
  <p>Before pack and release, AmmoOS runs the <strong>g16 combinatronic optimal</strong> cycle:</p>
  <ol>
    <li><strong>Growth scan</strong> — file combinatorics, optimal width</li>
    <li><strong>Dimensions consolidate</strong> — plate width × length</li>
    <li><strong>Combinamatrix</strong> — leaf pack</li>
    <li><strong>Steel neural plates</strong> — deep connection management</li>
    <li><strong>Sequence + AmmoLang</strong> — gapless universal sequence</li>
    <li><strong>Rebalance</strong> — chip + program batteries</li>
    <li><strong>Condense + Combine + Connect</strong> — universal panel wiring</li>
    <li><strong>Spider wire</strong> — ironclad outward lanes</li>
  </ol>
  <pre><code>./scripts/ammoos-beta-pipeline.sh
pythong lib/g16-combinatronic-rebalance.py optimal</code></pre>
  <p>Witness: <code>.nexus-state/ammoos-combinatronic-optimal.json</code></p>
  <p>Plates: <code>Queen/AmmoOS/net/FieldNetCore.fld</code>, <code>FieldNetGate.fld</code>, <code>FieldNetDos.fld</code></p>
""",
        ),
        "platforms.html": (
            "Platforms",
            f"""
  <h1>Platform matrix</h1>
  <p>AmmoOS <strong>{VER}</strong> ships source bootstrap per platform family.</p>
  <table>
    <tr><th>ID</th><th>OS</th><th>Arch</th><th>Bootstrap</th></tr>
{platform_table()}
  </table>
  <p>Release assets: <code>ammoos-{VER}-platforms.json</code> · <code>ammoos-{VER}-PLATFORMS.md</code></p>
""",
        ),
        "io.html": (
            "Field I/O",
            f"""
  <h1>Field I/O</h1>
  <p>Panel HTTP serves all browser surfaces on loopback <code>:9477</code>. Queen world on <code>:9481</code>.</p>
  <figure class="figure">
    <img src="images/io-architecture.svg" width="920" height="420" alt="AmmoOS architecture" />
    <figcaption>Panel ↔ daemon ↔ state ↔ Queen browser</figcaption>
  </figure>
  <h2>Key routes</h2>
  <table>
    <tr><th>Route</th><th>Role</th></tr>
    <tr><td><code>/field</code></td><td>Host desktop</td></tr>
    <tr><td><code>/command</code></td><td>Threat panel + training</td></tr>
    <tr><td><code>/underlay-f9</code></td><td>Tristate installer</td></tr>
    <tr><td><code>/api/chips/combinatronic</code></td><td>Chip combinatronic status</td></tr>
    <tr><td><code>/api/g16/universal-combinatronic</code></td><td>Universal combinatronic panel</td></tr>
    <tr><td><code>/api/program/combinatronic</code></td><td>Program combinatronic boil</td></tr>
  </table>
  <p>Module: <code>lib/threat-panel-http.py</code></p>
""",
        ),
        "queen-browser.html": (
            "Queen Browser",
            f"""
  <h1>Queen Browser</h1>
  <p>Queen Browser embeds the field OS inside the Start tab. URL: <code>{SURFACES.get('queen_browser', 'http://127.0.0.1:9481/world/browser.html')}</code></p>
  <p>Native RTX shell: <code>Queen/build/rtx/bin/Linux/queen-browser</code> — built via <code>queen-forge.py run live_build_field</code>.</p>
  <p>FIELDC v4 compiles <code>.fld</code> inside the AmmoOS shell path. Guest net plates live in <code>Queen/AmmoOS/net/</code>.</p>
""",
        ),
        "architecture.html": (
            "Architecture",
            """
  <h1>Architecture</h1>
  <pre><code>Host browser (:9477)
  ├─ /field        → host desktop
  ├─ /command      → C2 + training
  └─ /underlay-f9  → Tristate

Queen Browser (:9481)
  └─ /world/browser.html

Combinatronic engine
  ├─ g16-combinatronic-rebalance.py
  ├─ field-program-combinatronic.py
  └─ field-g16-universal-combinatronic.py

SG stack (wired via wire-stack.sh)
  Grok16 · Queen · Hostess7 · KILROY · ZOCR · World_Redata</code></pre>
""",
        ),
        "stack-hub.html": (
            "Stack Hub",
            f"""
  <h1>AmmoOS Stack Hub</h1>
  <p class="lead"><strong>AmmoOS leads.</strong> All stack <strong>code</strong> and documentation lives here — sibling GitHub Pages redirect to this manual and link back to <a href="https://github.com/ZacharyGeurts/AmmoOS">ZacharyGeurts/AmmoOS</a>.</p>
  <p><a class="cta" href="https://github.com/ZacharyGeurts/AmmoOS">Clone AmmoOS (canonical code)</a> · <a href="https://github.com/ZacharyGeurts/AmmoOS/releases/tag/v{VER}">Release v{VER}</a></p>
  <h2>Layer diagram</h2>
  <pre class="stack">Hardware → NEXUS C2 (:9477) → ZNetwork → Queen CANVAS → Queen Browser (:9481) → AmmoOS</pre>
  <h2>Stack manuals (canonical — all in AmmoOS)</h2>
  <table>
    <tr><th>Component</th><th>Manual page</th><th>Code</th><th>Pages hub</th></tr>
    <tr><td>★ AmmoOS</td><td><a href="index.html">Home</a></td><td><a href="https://github.com/ZacharyGeurts/AmmoOS">AmmoOS</a></td><td><a href="https://zacharygeurts.github.io/AmmoOS/">Manual</a></td></tr>
    <tr><td>Queen</td><td><a href="queen-browser.html">Queen Browser</a></td><td><a href="https://github.com/ZacharyGeurts/AmmoOS">AmmoOS</a></td><td><a href="https://zacharygeurts.github.io/Queen/">Hub</a></td></tr>
    <tr><td>Grok16</td><td><a href="combinatronic.html">Combinatronic</a></td><td><a href="https://github.com/ZacharyGeurts/AmmoOS">AmmoOS</a></td><td><a href="https://zacharygeurts.github.io/Grok16/">Hub</a></td></tr>
    <tr><td>KILROY</td><td><a href="architecture.html">Architecture</a></td><td><a href="https://github.com/ZacharyGeurts/AmmoOS">AmmoOS</a></td><td><a href="https://zacharygeurts.github.io/KILROY/">Hub</a></td></tr>
    <tr><td>ZNetwork</td><td><a href="io.html">Field I/O</a></td><td><a href="https://github.com/ZacharyGeurts/AmmoOS">AmmoOS</a></td><td><a href="https://zacharygeurts.github.io/ZNetwork/">Hub</a></td></tr>
    <tr><td>Final Eye / Ear / Mouth</td><td><a href="launch-surfaces.html">Launch Surfaces</a></td><td><a href="https://github.com/ZacharyGeurts/AmmoOS">AmmoOS</a></td><td>—</td></tr>
  </table>
  <p>Profile navigation: <a href="https://zacharygeurts.github.io/ZacharyGeurts/stack.html">ZacharyGeurts/stack.html</a></p>
""",
        ),
        "profile.html": (
            "Profile",
            f"""
  <h1>ZacharyGeurts — field footprint</h1>
  <p class="lead">GitHub profile and Pages presence styled like <strong>AmmoOS C2</strong> (<code>/field</code>). Unlimited star favorites — add repos to <code>docs/github-favorites.json</code> and rebuild.</p>
  <h2>Publish profile README</h2>
  <pre><code># Create github.com/ZacharyGeurts/ZacharyGeurts (same name as user)
cp profile/README.md /path/to/ZacharyGeurts/README.md
git add README.md && git commit -m "profile: AmmoOS C2 footprint" && git push</code></pre>
  <h2>Pages</h2>
  <table>
    <tr><th>Site</th><th>URL</th></tr>
    <tr><td>AmmoOS manual</td><td><a href="https://zacharygeurts.github.io/AmmoOS/">zacharygeurts.github.io/AmmoOS</a></td></tr>
    <tr><td>NEXUS-Shield</td><td><a href="https://zacharygeurts.github.io/NEXUS-Shield/">zacharygeurts.github.io/NEXUS-Shield</a></td></tr>
    <tr><td>Hostess7</td><td><a href="https://zacharygeurts.github.io/Hostess7/">zacharygeurts.github.io/Hostess7</a></td></tr>
    <tr><td>Field Primer</td><td><a href="https://zacharygeurts.github.io/Field_Primer/">zacharygeurts.github.io/Field_Primer</a></td></tr>
  </table>
  <h2>Rebuild + publish</h2>
  <pre><code>python3 docs/build-ammoos-manual.py
./scripts/publish-ammoos-pages.sh</code></pre>
""",
        ),
    }

    for name, (title, body) in pages.items():
        current = name
        (ROOT / name).write_text(page(title, body, current=current), encoding="utf-8")
        print(f"wrote {name}")


def main() -> int:
    write_pages()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())