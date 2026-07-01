# Hostess7 2.0.7 — superseded by 2.0.7e

See **[RELEASE-2.0.7e.md](RELEASE-2.0.7e.md)** for the current release.

**Version:** `2.0.7e` · **Repo:** [ZacharyGeurts/Hostess7](https://github.com/ZacharyGeurts/Hostess7) · **Pages:** [zacharygeurts.github.io/Hostess7](https://zacharygeurts.github.io/Hostess7/)

Hostess 7 is the **main project**. AmmoOS, Grok16, Queen, KILROY, and the rest are **Old Projects**.

## Source at 2.0.7e

- Package `__version__` = `2.0.7e` (single source via `src/hostess7/__init__.py` + `scripts/hostess7-sync-version.py`)
- Boot · brain · API exports · data doctrine JSON aligned
- Old Projects hub at `docs/old-projects.html`

## Quick start

```bash
git clone https://github.com/ZacharyGeurts/Hostess7.git
cd Hostess7
pip install -r requirements.txt
./Hostess7.sh boot
```

## Local Pages build (no publish)

```bash
./Hostess7.sh pages-build
```