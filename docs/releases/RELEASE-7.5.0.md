# NEXUS-Shield 7.5.0 — World's Best Dewey Library · Field Drive Tie-In

## Library (Hostess 7)

- **World's Best Dewey Library** — full GitHub folder tree under `library/dewey/` with `shelf.json`, `book.json`, and README per shelf/book
- **War studies shelf** — expanded `data/war-books-seed.json` (Clausewitz, Grant, Mahan, WWI/WWII, Civil War, etc.); `ascertain_war_books()` studies field drive
- **Hot-swappable catalog profiles** — Hostess 7, Library of Congress, British Library, OCLC WorldCat (`data/library-profiles.json`); panel dropdown + `/api/library/profiles`
- **TEAM fieldstorage tie-in** (`/media/default/HOSTESS7_TEAM/fieldstorage`):
  - **Library tab:** virtual brain corpora (12) + H7 books in `textbooks/dewey/{class}/`
  - **US · Home tracking lists:** manifest catalog, k12 staging, war seed — not mixed into library shelves
  - `./scripts/organize-h7-dewey.sh` moves flat `.h7` into Dewey library places
  - Path resolve: cache paths → TEAM NVMe when present
- **Panel** — war sub-shelves (355, 940.53, 973.7…), profile switcher, field drive inventory in sync bar

## Scripts

- `./scripts/sync-dewey-github.sh` — rebuild catalog + GitHub Dewey tree
- `pythong lib/h7-field-drive-tie.py inventory` — field drive asset report

Install: `sudo ./stealth_install.sh`  
Panel: https://127.0.0.1:9477/field