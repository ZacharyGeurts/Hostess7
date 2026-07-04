#!/usr/bin/env python3
"""Forge full GNU Technical manual wiki from field-technology-v5.txt + Field stack extensions."""
from __future__ import annotations

import re
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WIKI = ROOT / "wiki"
INSTALL = ROOT.parent
FIELD_TECH = INSTALL / "Textbook" / "field-technology-v5.txt"
PRESERVE_WIKI = frozenset({"eol-terminal-full-manual.md"})


def _slug(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:72] or "chapter"


def _write(path: Path, body: str) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body.rstrip() + "\n", encoding="utf-8")
    words = len(body.split())
    return {"path": str(path.relative_to(ROOT)), "words": words}


def _parse_field_technology() -> list[tuple[str, str, str]]:
    if not FIELD_TECH.is_file():
        return []
    raw = FIELD_TECH.read_text(encoding="utf-8", errors="replace")
    parts = re.split(r"^=== Chapter (\d+) ===\s*", raw, flags=re.M)
    chapters: list[tuple[str, str, str]] = []
    i = 1
    while i + 1 < len(parts):
        num = parts[i].zfill(2)
        body = parts[i + 1].strip()
        title_line = next((ln.strip() for ln in body.splitlines() if ln.strip()), f"Chapter {num}")
        title_line = re.sub(r"^Chapter \d+\s*·\s*", "", title_line)
        slug = f"ft-ch{num}-{_slug(title_line)}"
        chapters.append((slug, f"Ch {num} · {title_line}", body))
        i += 2
    return chapters


def _extension_pages() -> list[tuple[str, str, str]]:
    return [
        (
            "gnu-technical-manual",
            "GNU Technical Manual",
            textwrap.dedent("""
            # GNU Technical Manual

            **GNUEOLTerminal** — the last terminal software the world will ever need.
            Themeable, extensible, tight paneling, every option GNU ran on — beat with nicer widgets.

            ## Live surfaces

            - [Field GNU Terminal](https://zacharygeurts.github.io/GNUEOLTerminal/terminal/) — RTX panels · code preview · iron plate
            - [AmmoOS desktop](https://zacharygeurts.github.io/Hostess7/desktop/) — Layer −1 · Archival Warehouse wallpaper
            - Panel loopback: `http://127.0.0.1:9477/field-gnu-terminal-embed.html`

            ## Command families

            ```text
            help · wiki · field-tech · modules · load-module · mspaint · truth · combinatorics
            clear · cd · kernel · discern · mem
            ```

            ## Wiki map

            - **Field Technology** — chapters `ft-ch01` … `ft-ch22` (full primer)
            - **Classic schooler** — emacs · bash · coreutils · ssh · gpl
            - **Production** — [RTX panels](rtx-panels.md) · [entropy grade](entropy-grade.md) · [sovereign time](sovereign-time.md)
            - **DOS 4.0** — [modules](dos40-modules.md) · MSPaint · EDIT · GW-BASIC lane

            Shell ≡ terminal. Combinatronic optional. Plate meld never lies.
            """).strip(),
        ),
        (
            "rtx-panels",
            "RTX Panels",
            textwrap.dedent("""
            # RTX Panels — entropy-grade production

            Field GNU Terminal ships **tight paneling**: tab strip, code-preview sidebar, scroll track,
            theme engine, mini-browser proxy, ANSI 256 + truecolor via Ellie nav parser.

            ## RTX lane

            - `queen_rtx` profile when RTX permit gates open (Grok16 / AMOURANTHRTX)
            - CPU `field_opt` path when no RTX — same widgets, gated tools hidden
            - Iron plate JSON: `field-gnu-terminal-iron-plate-doctrine.json`

            ## Widgets (production)

            | Widget | Role |
            |--------|------|
            | Tab strip | Multi-session · split ≤4 |
            | Code preview | Live source beside stderr |
            | Scroll thumb | Touch + drag track |
            | Theme picker | AmmoOS C2 themes API |
            | Mini browser | `/browse/view` proxy |
            | Status bar | cwd · kernel · cli family |

            ## Entropy grade

            Every dispatch witnesses thermo + truth bands. Slow API paths log sovereign slowdown threats.
            See [entropy grade](entropy-grade.md).
            """).strip(),
        ),
        (
            "entropy-grade",
            "Entropy Grade Production",
            textwrap.dedent("""
            # Entropy Grade Production

            **Entropy grade** means: stderr, jsonl, sovereign time, and panel latency agree — or the UI is wrong.

            ## Witness stack

            1. `GET/POST /api/sovereign-time` — linear clock · slowdown ≥800ms = threat
            2. `FieldSovereignBus.fetch` — wraps every panel API with stamp + confirm
            3. Ironclad truth — `truth` command in GNU Terminal
            4. THERMO lines — fabric + packet field correlation (Field Technology Ch 5–7)

            ## Operator habit

            ```bash
            grep THERMO ~/.nexus-state/*.jsonl | tail
            curl -s http://127.0.0.1:9477/api/sovereign-time | jq .derived_utc
            ```

            Production panels: Hostess7 Pages · panel :9477 · Queen :9481.
            """).strip(),
        ),
        (
            "sovereign-time",
            "Sovereign Time",
            textwrap.dedent("""
            # Sovereign Time — single API everywhere

            Time is linear. Temperature does not adjust the timer. Slowdowns are threats.

            ## API

            - `GET /api/sovereign-time` — status + stamp policy
            - `POST /api/sovereign-time` — `{ "action": "...", "elapsed_ms": N }` → threat witness

            ## Client

            `field-sovereign-bus.js` on AmmoOS desktop, MSPaint, clipboard flyout chip.

            Confirm gate when `confirm_required` — grandma gets plain English; emacs users get stderr.
            """).strip(),
        ),
        (
            "dos40-modules",
            "MS-DOS 4.0 Modules",
            textwrap.dedent("""
            # MS-DOS 4.0 Module Host

            GNU Terminal loads extras like COMMAND.COM lineage:

            ```text
            modules
            load-module mspaint
            load-module edit
            mspaint
            mem
            ```

            | Module | Surface |
            |--------|---------|
            | MSPaint | `/mspaint` — PCX · clipboard |
            | EDIT | GNU Terminal embed |
            | GW-BASIC | coming soon · CHIPS lane |
            | MEM | truth witness · memory diagnostic |

            Right-click desktop → **Load DOS 4.0 module…**
            """).strip(),
        ),
        (
            "widgets-and-paneling",
            "Widgets & Tight Paneling",
            textwrap.dedent("""
            # Widgets & Tight Paneling

            Everything GNU ran on — options restored with modern widgets:

            - **Clipboard flyout** — Ctrl+Alt+Space · scheme grid · sovereign chip · media vault
            - **Archival Warehouse** — Layer −1 wallpaper · caution stripes · forklift
            - **Start flyout** — classic raised Start · OS theme swatches
            - **C2 task manager** — bullet rescue · CAD chords
            - **AmmoNet display rail** — Layer 0 monitor

            No dead space. Emacs veterans get chord labels; everyone else gets plain names.
            """).strip(),
        ),
        (
            "emacs",
            "Emacs",
            "# Emacs\n\n`C-x C-c` exits. `M-x` is still the cathedral door.\n\nClipboard flyout lists **emacs** scheme: `C-y` yank · `M-w` kill-ring.\n\nGNUEOLTerminal does not replace Emacs — it salutes it.\n",
        ),
        (
            "bash",
            "Bash",
            "# Bash\n\nGNU Bourne-Again SHell. Field Terminal accepts `bash -c` including combinatronic invocations.\n\n```bash\nhelp\nwiki\ncombinatorics\nload-module mspaint\n```\n",
        ),
        (
            "coreutils",
            "GNU Coreutils",
            "# Coreutils\n\n`ls`, `cat`, `grep`, `find` — allowed in field terminal allowlist.\n",
        ),
        (
            "ssh",
            "SSH",
            "# SSH\n\nSecure shell — pinned host keys in `Hostess7/data/github-known-hosts.json`.\n",
        ),
        (
            "gpl",
            "GPL FAQ",
            "# GPL FAQ\n\nFour freedoms. Copyleft. Source offers. Read [gnu.org/copyleft](https://www.gnu.org/copyleft/gpl.html).\n\nGNUEOLTerminal ships **GPL-3.0-or-later** when vendored from NewLatest.\n",
        ),
        (
            "field-tech",
            "Field Tech Commands",
            "# Field Tech Terminal\n\nShell ≡ terminal. Iron plate. Plate meld. Wiki: you are here.\n\nLive: [terminal/](../terminal/)\n\n```text\nwiki · field-tech · truth · modules · mspaint\n```\n",
        ),
    ]


def forge_all() -> list[dict]:
    stats: list[dict] = []
    WIKI.mkdir(parents=True, exist_ok=True)

    for slug, title, body in _extension_pages():
        out_path = WIKI / f"{slug}.md"
        if out_path.name in PRESERVE_WIKI and out_path.is_file():
            stats.append({"path": str(out_path.relative_to(ROOT)), "words": len(out_path.read_text().split()), "preserved": True})
            continue
        if not body.startswith("#"):
            body = f"# {title}\n\n{body}"
        stats.append(_write(out_path, body))

    ft_links: list[str] = []
    for slug, title, body in _parse_field_technology():
        md = f"# {title}\n\n{body}\n"
        stats.append(_write(WIKI / f"{slug}.md", md))
        ft_links.append(f"- [{title}]({slug}.md)")

    index_parts = [
        "# GNU Technical Manual — Classic Schooler Wiki",
        "",
        "For Emacs veterans, Bash poets, printf samurai — and grandma who just wants copy/paste to work.",
        "",
        "## Full manual (start here)",
        "",
        "- **[GNU EOL Terminal — Full Operator Manual](eol-terminal-full-manual.md)** — commands · API · iron plate · boot · troubleshooting",
        "",
        "## Quick links",
        "",
        "- [GNU Technical Manual overview](gnu-technical-manual.md)",
        "- [Widgets & tight paneling](widgets-and-paneling.md)",
        "- [RTX panels](rtx-panels.md)",
        "- [Entropy grade production](entropy-grade.md)",
        "- [Sovereign time](sovereign-time.md)",
        "- [MS-DOS 4.0 modules](dos40-modules.md)",
        "",
        "## Classic GNU",
        "",
        "- [Emacs](emacs.md)",
        "- [Bash](bash.md)",
        "- [Coreutils](coreutils.md)",
        "- [SSH](ssh.md)",
        "- [GPL FAQ](gpl.md)",
        "- [Field Tech commands](field-tech.md)",
        "",
        "## Field Technology primer (full manual)",
        "",
    ]
    index_parts.extend(ft_links)
    index_parts.extend([
        "",
        "Built from `Textbook/field-technology-v5.txt` · Hostess7 **3.0.7-beta5** · GNUEOLTerminal.",
        "",
        "Repo: https://github.com/ZacharyGeurts/GNUEOLTerminal",
    ])
    stats.append(_write(WIKI / "index.md", "\n".join(index_parts)))
    return stats


def main() -> int:
    stats = forge_all()
    print(f"forged {len(stats)} wiki pages → {WIKI}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())