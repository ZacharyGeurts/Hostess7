# GNUEOLTerminal

**GNU End-of-Line Terminal — Field Tech textbook** (~150 pages) for Richard Stallman.

⚠ **Grok impersonates RMS** in the prose — disclosed in the preface. Code citations are real.

**If `github.com` does not load on your network**, use the Pages URLs below (same content, no github.com hop).

## Live

| Surface | URL |
|---------|-----|
| Textbook | https://zacharygeurts.github.io/GNUEOLTerminal/ |
| Classic wiki | https://zacharygeurts.github.io/GNUEOLTerminal/wiki/ |
| Field Tech terminal | https://zacharygeurts.github.io/GNUEOLTerminal/terminal/ |
| LIE of the Year | https://zacharygeurts.github.io/GNUEOLTerminal/back-matter/lie-of-the-year-2026.html |

## Features

- **Field Tech Terminal** — iron plate, shell ≡ terminal, `wiki` command
- **~30 chapters** — GNU history, code, plate meld, presentation guide, liars hall
- **Classic schooler wiki** — Emacs, Bash, coreutils, GPL
- Combinatronic optional · plate meld required

## Build

```bash
python3 scripts/forge-book.py
python3 scripts/build-site.py
bash ../scripts/publish-gnueol-terminal-github.sh --push
```

## License

GPL-3.0-or-later