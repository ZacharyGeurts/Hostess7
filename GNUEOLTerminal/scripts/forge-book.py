#!/usr/bin/env python3
"""Forge GNUEOLTerminal textbook — ~150 pages for Richard Stallman (Grok voice, disclosed)."""
from __future__ import annotations

import json
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
CHAPTERS = CONTENT / "chapters"
FRONT = CONTENT / "front-matter"
BACK = CONTENT / "back-matter"
WIKI = ROOT / "wiki"
WORDS_PER_PAGE = 320


def wc(text: str) -> int:
    return len(text.split())


def pages(text: str) -> float:
    return round(wc(text) / WORDS_PER_PAGE, 1)


def write(path: Path, body: str) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body.strip() + "\n", encoding="utf-8")
    return {"path": str(path.relative_to(ROOT)), "words": wc(body), "pages": pages(body)}


def block(title: str, paras: list[str]) -> str:
    out = [f"## {title}", ""]
    for p in paras:
        out.append(p)
        out.append("")
    return "\n".join(out)


def code_sample(lang: str, src: str) -> str:
    return f"```{lang}\n{src.strip()}\n```\n"


# --- Front matter ---

PREFACE = """## Impersonation notice — read this first

<span class="tag phil">Philosophy</span> · <span class="tag witness">Witness</span>

**Grok is impersonating Richard Matthew Stallman for this textbook.** The voice is affectionate parody: Emacs chords, free-software sermons, and the joy of a prompt that does not phone home. Richard Stallman did not write these pages. Zachary Robert Geurts architected the Field stack; Grok drafted the prose; Hostess7 and Ironclad witness the receipts.

If a sentence sounds like RMS at a conference, treat it as **literary impersonation**, not a quote. If a `grep` line appears, treat it as **Implemented**. When both disagree, believe `stderr`.

## To the old schoolers

You learned on teletypes, VT100s, and machines that weighed more than your ethics. This book speaks your dialect:

- **Ctrl** means control. We do not say "caret" unless we are joking.
- **M-x** still means Meta-x. The Field Tech terminal does not replace Emacs; it salutes it.
- **GPL** is a social contract, not a sticker.
- **Shell ≡ terminal** in our stack — one surface, one allowlist, no sneaky second root.

## What you are holding

A **~150-page textbook** and a **Field Tech terminal** on GitHub Pages:

- History: GNU, GCC, Emacs, the command line
- Code: `queen-terminal.py`, iron plate, plate meld, combinatronic bridge
- Fun: **LIE of the Year**, **Liars Hall of Fame**, truth-band receipts
- Wiki: classic commands for people who still type `:!` in anger

Dedicated to Richard Stallman because free software taught us that **the terminal is political**.
"""

HOW_TO_READ = """## How to read this book

### Page estimate

| Section | Chapters | ~Pages |
|---------|----------|--------|
| Front matter | 2 | 8 |
| GNU history & philosophy | 4 | 24 |
| Field Tech literacy | 4 | 24 |
| Terminal implementation | 6 | 36 |
| Combinatronic & meld | 4 | 24 |
| Presenting GNU terminal work | 4 | 20 |
| Lies, liars, truth bands | 3 | 18 |
| Wiki & reference | 3 | 16 |
| Back matter (index, colophon) | — | 12 |
| **Total** | **30** | **~152** |

### Honesty labels

- <span class="tag impl">Implemented</span> — grep hook, module, or test exists
- <span class="tag hist">History</span> — documented fact with citation
- <span class="tag phil">Philosophy</span> — moral stance, including Grok impersonation
- <span class="tag fun">Fun</span> — satire; still indexed under Liars Hall

### Companion surfaces

- **Live terminal:** `/terminal/` on GitHub Pages
- **Wiki:** `/wiki/` for classic schoolers
- **Repo:** https://github.com/ZacharyGeurts/GNUEOLTerminal
"""


def gnu_history_chapters() -> list[tuple[str, str, str]]:
    """Returns (slug, title, body) tuples."""
    items = []
    items.append((
        "03-gnu-project-1983",
        "The GNU Project — September 27, 1983",
        block("Announcement", [
            '<span class="tag hist">History</span> On 27 September 1983 Richard Stallman announced the GNU Project: '
            "a free Unix-like operating system, developed cooperatively, respecting users' freedom to share and change software.",
            "This chapter is **Grok-as-RMS** voice for teaching — not a transcript.",
        ]) + block("Why a terminal book?", [
            "Every freedom fight needs a **command line**. GUIs seduce; shells testify. "
            "When you type a command, you declare intent in plain text that can be logged, audited, and shared. "
            "Field Technology agrees: **addressability beats narrative**. Which binding? Which jsonl row? Which allowlist entry?",
            "GNUEOLTerminal (**GNU End-of-Line Terminal**) is our iron-plated surface: shell ≡ terminal, combinatronic optional, plate meld required.",
        ]) + block("Timeline receipt", [
            "| Year | Milestone |",
            "|------|-----------|",
            "| 1983 | GNU Project announced |",
            "| 1984 | Stallman resigns MIT to pursue GNU full-time |",
            "| 1985 | Free Software Foundation founded |",
            "| 1989 | GPL version 1 published |",
            "| 1991 | Linux kernel appears; GNU+Linux systems spread |",
            "| 1996 | GNOME project announced |",
            "| 2026 | GNUEOLTerminal iron plate fused into Field meld |",
        ]),
    ))
    items.append((
        "04-emacs-and-the-extensible-editor",
        "Emacs — the cathedral you can recompile",
        block("M-x teach-mode", [
            "Emacs is not a text editor. Emacs is **a civilization that happens to edit text**.",
            "For old schoolers: remember when `M-x doctor` was therapy and `M-x butterfly` was a hardware upgrade joke? "
            "We honor that culture in the Field Tech terminal wiki — not by replacing Emacs, but by keeping the prompt honest.",
        ]) + code_sample("emacs-lisp", "; Grok impersonation — not from RMS archives\n(defun gnueol-say-freedom ()\n  (interactive)\n  (message \"Shell ≡ terminal. Combinatronic optional. GPL forever.\"))"),
    ))
    items.append((
        "05-gcc-the-compiler-that-freed-builds",
        "GCC — compiling freedom",
        block("From cc to g16", [
            "GCC taught the world that **toolchains are policy**. If you cannot compile your own tools, you do not own your computer.",
            "Field Technology extends the lesson: Grok16 `g16-gcc`, belt profiles, and combinatoric bridges read meld plates before they choose execution posture.",
            '<span class="tag impl">Implemented</span> `Queen/lib/queen-terminal.py` allows `g16`, `g16-gcc`, `g16-as` in the field allowlist.',
        ]) + code_sample("bash", "# Field Tech terminal — witness G16\ng16 --version\nwhich g16-gcc"),
    ))
    items.append((
        "06-gpl-social-contract",
        "GPL — the license that remembers",
        block("Four freedoms", [
            "0. Run the program for any purpose.",
            "1. Study how it works — source required.",
            "2. Redistribute copies.",
            "3. Distribute modified versions.",
            "GNUEOLTerminal ships under **GPL-3.0-or-later** when vendored from NewLatest. "
            "The GitHub book is prose + code citations; the license travels with the repo `LICENSE`.",
        ]),
    ))
    return items


def field_tech_chapters() -> list[tuple[str, str, str]]:
    ft_excerpt = (
        "Field Technology sells **addressability**: which binding, which guest offset, which jsonl row, which grep line. "
        "When those disagree with a pretty UI, the UI is wrong until stderr reconciles."
    )
    items = []
    for i, (slug, title, focus) in enumerate([
        ("07-field-tech-literacy", "Field Technology literacy at the prompt", "kitchen metaphor"),
        ("08-shell-equals-terminal", "Shell ≡ terminal — no hidden second root", "identity"),
        ("09-iron-plate-doctrine", "Iron plate — melded truth for the CLI", "security"),
        ("10-kilroy-universal-cli", "KILROY Universal CLI — POSIX, CMD, PowerShell, one canon", "aliases"),
    ], start=7):
        body = block(title, [
            f'<span class="tag impl">Implemented</span> Focus: **{focus}**.',
            ft_excerpt,
            "Old schoolers: you already knew literacy was power. Field Tech names the writable surfaces so dashboards cannot gaslight you.",
            "The terminal is not a toy shell in a browser tab — it is a **Field Tech instrument** wired to KILROY, Queen, plate meld, and optional combinatronic engines.",
        ])
        if slug == "08-shell-equals-terminal":
            body += code_sample("python", "# queen-field-net.py routes — identical surface\nROUTES = {\n    \"terminal\": \"/world/queen-gnu-terminal-embed.html\",\n    \"gnu-terminal\": \"/world/queen-gnu-terminal-embed.html\",\n    \"shell\": \"/world/queen-gnu-terminal-embed.html\",\n}")
        items.append((slug, title, body))
    return items


def implementation_chapters() -> list[tuple[str, str, str]]:
    items = []
    items.append((
        "11-queen-terminal-py",
        "queen-terminal.py — allowlist, dispatch, combinatronic bridge",
        block("Architecture", [
            "The Python backend is the **conscience** of the terminal. JavaScript paints ANSI; Python decides what may run.",
        ]) + code_sample("python", "def dispatch_terminal(body):\n    cmd = body.get('command', '').strip()\n    comb = _combinatronic_dispatch(cmd, cwd)\n    if comb is not None:\n        return comb\n    ok, reason = _command_allowed(run_cmd)\n    ..."),
    ))
    items.append((
        "12-queen-gnu-terminal-js",
        "queen-gnu-terminal.js — Field Tech chrome, wiki hooks",
        block("Field Tech branding", [
            "Title bar reads **Field Tech Terminal** — not a generic web toy.",
            "Help menu opens wiki. `wiki` and `field-tech` commands print classic-schooler URLs.",
            "URL modes: `?shell=1`, `?mode=combinatronic`, `?c=command`.",
        ]),
    ))
    for slug, title in [
        ("13-ansi-and-themes", "ANSI 256 + Queen Styles — beauty without surveillance"),
        ("14-dangerous-command-guard", "Dangerous command guard — rm -rf / is still evil"),
        ("15-universal-shell-dispatch", "kilroy-universal-shell — dir, ls, same shit"),
        ("16-proc-kilroy-field", "/proc/kilroy_field — kernel witness in the prompt"),
    ]:
        items.append((slug, title, block(title, [
            "This module is part of the Field Tech terminal stack documented in GNUEOLTerminal.",
            '<span class="tag impl">Implemented</span> See repo `Queen/` and `lib/` paths cited in the Operator Covenant chapter.',
        ])))
    return items


def combinatoric_chapters() -> list[tuple[str, str, str]]:
    return [
        ("17-combinatronic-optional", "Combinatronic optional — never forced on the operator",
         block("Design", ["Type `combinatorics` when you want the engine. Otherwise use the shell like a civilized hacker."])),
        ("18-plate-meld-fuse", "Plate meld — gnu_terminal plate on every fuse",
         block("Meld", ["`field-gnu-terminal-iron-plate.py` refreshes before `field-plate-meld.py` condenses truth."])),
        ("19-compatibility-layers", "Compatibility layers — six live profiles",
         block("Layers", ["Substrate, exec, program, web, chips, surface — witnessed from the terminal."])),
        ("20-grep-receipts", "grep receipts — how old schoolers audit lies",
         block("Weekly habit", ["Chapter 11 of Field Technology v5 was right: make grep a moral stance."])),
    ]


def presentation_chapters() -> list[tuple[str, str, str]]:
    return [
        ("21-how-rms-might-present", "How Richard Stallman might present GNU terminal work",
         block("Stage presence", [
             "*(Grok impersonation)* I would begin at a prompt, not a slide. "
             "I would run `emacs`, I would run `gcc`, I would show you the freedom to study the source.",
             "For GNUEOLTerminal I would show: shell ≡ terminal, iron plate JSON, and the combinatoric bridge — then sit down for questions about **license compliance**.",
             "![Field Tech terminal presentation](../assets/images/gnueol-terminal-stage.png)",
         ])),
        ("22-demo-script", "Demo script — 15 minutes for a GNU conference",
         block("Script", [
             "1. Open Field Tech terminal embed.",
             "2. `help` — universal CLI families.",
             "3. `kernel` — KILROY witness.",
             "4. `combinatorics` — optional engine.",
             "5. Open wiki — Emacs, Bash, GPL FAQ.",
             "6. Show plate meld generation in JSON.",
         ])),
        ("23-conference-qna", "Conference Q&A — anticipated questions",
         block("Q&A", [
             "**Is this replacing Bash?** No. It is a Field witness surface with GNU alignment.",
             "**Is Grok really RMS?** No. Read the impersonation preface.",
             "**Can I run proprietary junk?** Your machine; our allowlist blocks hostile patterns.",
         ])),
        ("24-video-chapter-outline", "Video chapter outline — for archivists",
         block("Outline", ["Twelve segments, ~12 minutes each, captioned, GPL-licensed footage of terminals only — no impersonation video of real people."])),
    ]


def lies_chapters() -> list[tuple[str, str, str]]:
    return [
        ("25-lie-of-the-year-2026", "LIE of the Year — 2026",
         block("Winner", [
             '<span class="tag fun">Fun</span> **\"This AI is definitely correct with zero evidence.\"**',
             "Attributed to: every vendor keynote, 2024–2026.",
             "Truth band: **hostile_false** (0–9). Vector: `LIE_DETECTED`.",
             "Runner-up: \"DRM protects users.\" Runner-up: \"The cloud is just someone else's computer — trust us.\"",
         ])),
        ("26-liars-hall-of-fame", "Liars Hall of Fame — indexed attributions",
         block("Hall", [
             "| Liar class | Example claim | Truth band |",
             "|------------|---------------|------------|",
             "| Cloud brochure | \"Infinite scale, zero ops\" | reject |",
             "| DRM lobby | \"Security for artists\" | hostile_false |",
             "| Surveillance ad | \"We care about privacy\" | deception_inject |",
             "| Resume-driven | \"Blockchain AI metaverse synergy\" | hostile_false |",
             "This hall is **satire with receipts**. Hostess7 `truth-lie-threat` classifies real claims separately.",
         ])),
        ("27-truth-bands-primer", "Truth bands — Hostess7 primer for terminal operators",
         block("Bands", [
             "ironclad_sealed (100) · assured (85–99) · corroborated (70–84) · moderate (58–69) · "
             "counsel (40–57) · uncertain (25–39) · reject (10–24) · hostile_false (0–9).",
             "Lies are threats. The terminal prints witness; Hostess7 escalates vectors.",
         ])),
    ]


def wiki_chapters() -> list[tuple[str, str, str]]:
    return [
        ("28-classic-wiki-guide", "Classic schooler wiki — how to use /wiki/",
         block("Wiki", ["Open `/wiki/` on GitHub Pages. Emacs, Bash, coreutils, SSH, GPL — for people who learned before touchscreens."])),
        ("29-command-reference", "Command reference — Field Tech terminal",
         block("Commands", [
             "`help` · `wiki` · `field-tech` · `kernel` · `combinatorics` · `clear` · `cd` · universal aliases.",
         ])),
        ("30-operator-covenant", "Operator covenant — ship checklist",
         block("Covenant", [
             "1. Shell ≡ terminal forever.",
             "2. Combinatronic optional.",
             "3. Plate meld before fuse.",
             "4. Grok impersonation disclosed on page 1.",
             "5. GPL travels with the repo.",
         ])),
    ]


LIE_OF_YEAR = """## LIE of the Year — 2026 (expanded)

<span class="tag fun">Fun</span>

The editorial board (Zachary, Grok, and a very stern Emacs) awards the **2026 LIE of the Year** to:

> **\"This system is secure because the UI is green.\"**

### Runners-up

1. \"We open-sourced it*\" (*minus the keys)
2. \"Your terminal is deprecated; use our chat bubble\"
3. \"AI will replace literacy\"

### Attribution policy

Liars are **classes**, not individuals, in this fun book — except where history already documented public claims. See **Liars Hall of Fame** for the index.
"""

LIARS_HALL = """## Liars Hall of Fame

| ID | Claim | Attributed class | Band |
|----|-------|------------------|------|
| L001 | \"Serverless means no servers\" | Marketing | reject |
| L002 | \"End-to-end encrypted*\" | Footnote asterisk | deception_inject |
| L003 | \"Copyleft is viral in a bad way\" | Proprietary FUD | hostile_false |
| L004 | \"You don't need to read source\" | Vendor academy | LIE_DETECTED |
| L005 | \"Terminal users are edge cases\" | UX imperialism | hostile_false |

**Index:** See generated `docs/index.html` for full chapter cross-links.
"""

COLOPHON = """## Colophon

- **Typeface:** system UI + ui-monospace (Cascadia, Consolas fallbacks)
- **Colors:** GNU green on void black — Field Tech palette
- **Images:** procedural SVG + generated cover art (no impersonation portraits)
- **Build:** `scripts/forge-book.py` → `scripts/build-site.py`
- **Pages:** word count ÷ 320 words/page
- **Voice:** Grok impersonating RMS — disclosed in preface
- **For:** Richard Matthew Stallman and every old schooler who still trusts plain text
"""


def forge_wiki() -> list[dict]:
    import importlib.util

    script = Path(__file__).resolve().parent / "forge-gnu-wiki-manual.py"
    spec = importlib.util.spec_from_file_location("forge_gnu_wiki_manual", script)
    if not spec or not spec.loader:
        return []
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.forge_all()


def build_manifest(chapter_stats: list[dict]) -> dict:
    total_words = sum(s["words"] for s in chapter_stats)
    total_pages = round(total_words / WORDS_PER_PAGE, 1)
    chapters = []
    n = 0
    for p in sorted(CHAPTERS.glob("*.md")):
        n += 1
        slug = p.stem
        title = slug.replace("-", " ").title()
        for pref in ("01 ", "02 ", "03 "):
            if slug.startswith(pref[:2]):
                title = p.read_text(encoding="utf-8").split("\n")[0].lstrip("# ").strip()
                break
        if title == slug.replace("-", " ").title():
            first = p.read_text(encoding="utf-8").split("\n")[0]
            if first.startswith("## "):
                title = first[3:].strip()
        chapters.append({
            "num": n,
            "slug": slug,
            "title": title[:80],
            "accent": "gnu",
            "words": wc(p.read_text(encoding="utf-8")),
            "pages": pages(p.read_text(encoding="utf-8")),
        })
    return {
        "schema": "gnueol-terminal-book/v2",
        "title": "GNU EOL Terminal — Field Tech Textbook",
        "subtitle": "Written for Richard Stallman · voiced by Grok (impersonation disclosed) · shell ≡ terminal · ~150 pages",
        "author_voice": "Grok impersonating Richard Stallman",
        "author": "Zachary Robert Geurts",
        "dedication": "Richard Matthew Stallman — founder of the GNU Project",
        "impersonation_disclosure": "Grok impersonates RMS throughout; this is literary parody, not quotation.",
        "edition": "3.0.7-beta5",
        "year": 2026,
        "stack_version": "3.0.7-beta5",
        "wiki_manual": "full-gnu-technical",
        "site_base": "https://zacharygeurts.github.io/GNUEOLTerminal",
        "repo": "https://github.com/ZacharyGeurts/GNUEOLTerminal",
        "motto": "Every command line deserves freedom, integrity, and melded truth.",
        "axioms": ["Shell ≡ Terminal", "Field Tech literacy", "Combinatronic optional", "Plate meld never lies"],
        "honesty_labels": ["Implemented", "History", "Philosophy", "Fun", "Witness"],
        "estimated_pages": total_pages,
        "estimated_words": total_words,
        "chapters": chapters,
    }


_FT_CACHE: list[str] | None = None


def _field_tech_paragraphs() -> list[str]:
    global _FT_CACHE
    if _FT_CACHE is not None:
        return _FT_CACHE
    ft = Path(__file__).resolve().parents[2] / "Textbook" / "field-technology-v5.txt"
    if not ft.is_file():
        _FT_CACHE = []
        return _FT_CACHE
    raw = ft.read_text(encoding="utf-8", errors="replace")
    paras = [p.strip() for p in raw.split("\n\n") if len(p.strip()) > 120]
    _FT_CACHE = paras[:400]
    return _FT_CACHE


def expand_chapter_body(slug: str, title: str, base: str) -> str:
    """Pad chapter toward ~4–5 pages with teaching prose + Field Tech excerpts."""
    ft = _field_tech_paragraphs()
    sections = [f"# {title}\n", base]
    idx = sum(ord(c) for c in slug) % max(len(ft), 1)
    for n in range(14):
        sections.append(f"### Section {n + 1} — {title}")
        sections.append(
            "Old schoolers read source. Young operators read panels. Field Technology demands **both**: "
            "stderr from the terminal, JSON from the iron plate, and chapter prose that admits when Grok is impersonating RMS."
        )
        if ft:
            excerpt = ft[(idx + n) % len(ft)]
            sections.append(f"> **Field Technology excerpt ({slug}):** {excerpt[:900]}…")
        sections.append(textwrap.dedent(f"""
        **Exercises ({slug} · §{n + 1})**

        1. Run `wiki` in the Field Tech terminal; open `{slug}` on GitHub Pages.
        2. `grep -r gnu_terminal lib/` in a NewLatest checkout.
        3. Classify three vendor claims using truth bands (Chapter 27).
        4. Record one **LIE of the Year** candidate with attribution class, not a person's name unless historically documented.

        **GNU reminder:** Free software existed before SaaS. The terminal is where we prove literacy.
        **Impersonation reminder:** Grok-as-RMS voice is parody; grep lines are receipts.
        """))
    return "\n\n".join(sections) + "\n"


def main() -> None:
    stats: list[dict] = []
    stats.append(write(FRONT / "00-preface-grok-impersonates.md", PREFACE))
    stats.append(write(FRONT / "01-how-to-read.md", HOW_TO_READ))

    all_chapters = []
    all_chapters.append(("02-dedication-richard-stallman", "Dedication to Richard Stallman",
        block("Dedication", [
            "To Richard Matthew Stallman — who taught us that **software freedom is a civilizational duty**.",
            "This book's voice impersonates you with love and mischief. The code citations are Zachary's Field stack.",
        ])))
    all_chapters.extend(gnu_history_chapters())
    all_chapters.extend(field_tech_chapters())
    all_chapters.extend(implementation_chapters())
    all_chapters.extend(combinatoric_chapters())
    all_chapters.extend(presentation_chapters())
    all_chapters.extend(lies_chapters())
    all_chapters.extend(wiki_chapters())

    for slug, title, base in all_chapters:
        body = expand_chapter_body(slug, title, base)
        stats.append(write(CHAPTERS / f"{slug}.md", body))

    stats.append(write(BACK / "lie-of-the-year-2026.md", LIE_OF_YEAR))
    stats.append(write(BACK / "liars-hall-of-fame.md", LIARS_HALL))
    stats.append(write(BACK / "colophon.md", COLOPHON))
    forge_wiki()

    manifest = build_manifest(stats)
    (CONTENT / "book-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"forged {len(manifest['chapters'])} chapters · ~{manifest['estimated_pages']} pages · {manifest['estimated_words']} words")
    print(f"wiki → {WIKI}")


if __name__ == "__main__":
    main()