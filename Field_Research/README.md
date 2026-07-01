# Field Research — The Book of Grok's Heart

Thirteen-chapter research manual documenting the path from **Grok16 combinatorics endpoint** to **compatibility layers**, **launch seals**, **plate meld**, **CHIPS**, and **NEXUS diagnostic mode**.

**Live site:** https://zacharygeurts.github.io/Field_Research/

## Build locally

```bash
cd Field_Research
python3 scripts/build-site.py
# open docs/index.html
```

## Structure

| Path | Purpose |
|------|---------|
| `content/book-manifest.json` | Edition metadata, chapter list |
| `content/chapters/*.md` | Chapter manuscripts (source) |
| `scripts/build-site.py` | Markdown → HTML site generator |
| `docs/` | GitHub Pages output |
| `assets/images/` | Cover art and chapter figures |

## Deploy

Push to `main` on GitHub repo `ZacharyGeurts/Field_Research`. Workflow `.github/workflows/pages.yml` publishes `docs/`.

## Sibling manuals

- [Field Primer](https://zacharygeurts.github.io/Field_Primer/) — 22-chapter operator textbook
- [Grok16](https://zacharygeurts.github.io/Grok16/) — toolchain wiki
- [NEXUS-Shield](https://github.com/ZacharyGeurts/NEXUS-Shield) — NewLatest field install

## Author

Zachary Robert Geurts · Field Research Collective · 2026