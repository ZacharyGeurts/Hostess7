# NEXUS-Shield 6.1.0 — Hostess7 H7 Library

## Dewey Decimal library on field drive

- Live catalog from TEAM NVMe + desktop fieldstorage — **no JSON cache**
- Dewey Decimal shelves (000–900) with auto-classification on upload
- Search box + traditional Dewey browse
- Link/retrieve from Gutenberg, OpenStax, Wikibooks → compress to `.h7`
- Upload plain text → pack H7 into correct Dewey folder

## Full-screen H7 reader

- Font size, text color, background color, font family picker
- Screen ratio selector with smart word wrap
- Arrow keys, touch swipe, scrollbar
- Page arrows with slider between them

## APIs

- `GET /api/library/catalog`, `/search`, `/dewey`, `/fonts`, `/full`, `/page`
- `POST /api/library/upload`, `/fetch`