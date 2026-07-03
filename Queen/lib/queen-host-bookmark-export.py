#!/usr/bin/env python3
"""Export secure bookmarks for every host browser — Firefox · Chrome · Brave · Edge · Chromium.

Raw :9488 / :9477 / :9481 URLs fail when services are down — rewrite through
bookmark-jump (panel ensure) or Queen ?launch= wrapper. Pages URLs work from
any outside browser (Chrome, Edge, Brave, IE via HTML import).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

QUEEN = Path(__file__).resolve().parents[1]
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", QUEEN.parent))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
TREES = QUEEN / "data" / "queen-bookmark-trees.json"
OUT_HTML = STATE / "host-browser-secure-bookmarks.html"
MANIFEST = STATE / "host-browser-bookmark-export.json"

PANEL_PORT = os.environ.get("NEXUS_THREAT_PANEL_PORT", "9477")
QUEEN_PORT = os.environ.get("QUEEN_WORLD_PORT", "9481")
PAGES_BASE = os.environ.get(
    "HOSTESS7_PAGES_BASE",
    "https://zacharygeurts.github.io/Hostess7",
).rstrip("/")
BOOKMARK_MODE = os.environ.get("HOSTESS7_BOOKMARK_MODE", "pages").strip().lower()
HTTPS_SECURE = os.environ.get("HOSTESS7_HTTPS_SECURE", "1") == "1"
_ORPHAN_LOOPBACK_RE = re.compile(r"^http://127\.0\.0\.1:(9477|9481|9488)(/|$)")
_JUMP_IDS = frozenset({
    "h7-training-viewer", "cmd-field", "cmd-deck", "cmd-c2",
    "g16-compiler", "h7-g16-online",
})

CHROMIUM_ROOTS: list[tuple[str, Path]] = [
    ("chrome", Path.home() / ".config" / "google-chrome"),
    ("chromium", Path.home() / ".config" / "chromium"),
    ("brave", Path.home() / ".config" / "BraveSoftware" / "Brave-Browser"),
    ("edge", Path.home() / ".config" / "microsoft-edge"),
    ("vivaldi", Path.home() / ".config" / "vivaldi"),
    ("opera", Path.home() / ".config" / "opera"),
]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_trees() -> list[dict[str, Any]]:
    try:
        doc = json.loads(TREES.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return list(doc.get("trees") or [])


def _walk(nodes: list[dict[str, Any]], acc: list[dict[str, Any]]) -> None:
    for node in nodes:
        if not isinstance(node, dict):
            continue
        if node.get("kind") == "folder":
            _walk(list(node.get("children") or []), acc)
        elif node.get("url"):
            acc.append(node)


def _https_secure_suffix() -> str:
    return "&https=1" if HTTPS_SECURE else ""


def _pages_url(url: str, bm_id: str) -> str:
    u = (url or "").strip()
    if u.startswith("https://") and "127.0.0.1" not in u and bm_id not in _JUMP_IDS:
        return u
    if bm_id in ("g16-compiler", "h7-g16-online") or "/combinatorics" in u or "/g16-build-output" in u:
        jump_id = "h7-g16-online" if "/g16-build-output" in u else "g16-compiler"
        return f"{PAGES_BASE}/bookmark-jump/?id={jump_id}{_https_secure_suffix()}"
    if ":9488" in u or bm_id == "h7-training-viewer":
        return f"{PAGES_BASE}/bookmark-jump/?id=h7-training-viewer{_https_secure_suffix()}"
    if ":9477" in u:
        tail = u.replace(f"http://127.0.0.1:{PANEL_PORT}", "").split("#")[0].rstrip("/") or "/"
        if tail.startswith("/bookmark-jump"):
            return f"{PAGES_BASE}{tail}"
        if tail in ("/field", "/field/"):
            return f"{PAGES_BASE}/desktop/"
        if bm_id in _JUMP_IDS:
            return f"{PAGES_BASE}/bookmark-jump/?id={bm_id}{_https_secure_suffix()}"
        return f"{PAGES_BASE}{tail if tail.startswith('/') else '/' + tail}"
    if ":9481" in u:
        return f"{PAGES_BASE}/queen/browser.html?launch={quote(u, safe='')}"
    return u


def _loopback_url(url: str, bm_id: str) -> str:
    u = (url or "").strip()
    panel = f"http://127.0.0.1:{PANEL_PORT}"
    queen = f"http://127.0.0.1:{QUEEN_PORT}"
    if ":9488" in u or bm_id == "h7-training-viewer":
        return f"{panel}/bookmark-jump/?id=h7-training-viewer"
    if ":9477" in u:
        if "/bookmark-jump" in u:
            return u
        return f"{panel}/bookmark-jump/?to={quote(u, safe='')}"
    if ":9481" in u:
        return f"{queen}/world/browser.html?launch={quote(u, safe='')}"
    return u


def secure_url(url: str, bm_id: str) -> str:
    if BOOKMARK_MODE == "loopback":
        return _loopback_url(url, bm_id)
    if BOOKMARK_MODE == "dual":
        return _pages_url(url, bm_id)
    return _pages_url(url, bm_id)


def _netscape_html(rows: list[dict[str, str]]) -> str:
    lines = [
        "<!DOCTYPE NETSCAPE-Bookmark-file-1>",
        "<!-- Hostess7 secure bookmarks — All Rights Reserved -->",
        '<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">',
        "<title>AmmoOS Secure Bookmarks</title>",
        "<h1>Bookmarks</h1>",
        "<dl><dt><h3 personal_toolbar_folder=\"true\">AmmoOS Field</h3><dl>",
    ]
    for row in rows:
        lines.append(
            f'<dt><a href="{row["url"]}" add_date="{int(time.time())}">{row["title"]}</a>'
        )
    lines.extend(["</dl></dl>", ""])
    return "\n".join(lines)


def _firefox_profiles() -> list[Path]:
    roots = [Path.home() / ".mozilla" / "firefox"]
    out: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        ini = root / "profiles.ini"
        if ini.is_file():
            for line in ini.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.startswith("Path="):
                    rel = line.split("=", 1)[1].strip()
                    p = root / rel
                    if (p / "places.sqlite").is_file():
                        out.append(p)
        for p in root.iterdir():
            if p.is_dir() and (p / "places.sqlite").is_file():
                out.append(p)
    seen: set[str] = set()
    deduped: list[Path] = []
    for p in out:
        key = str(p.resolve())
        if key not in seen:
            seen.add(key)
            deduped.append(p)
    return deduped


def _chromium_profiles() -> list[tuple[str, Path]]:
    out: list[tuple[str, Path]] = []
    seen: set[str] = set()
    for browser_id, root in CHROMIUM_ROOTS:
        if not root.is_dir():
            continue
        local_state = root / "Local State"
        if not local_state.is_file():
            continue
        for name in ("Default", "Profile 1", "Profile 2", "Profile 3"):
            prof = root / name
            if (prof / "Bookmarks").is_file():
                key = str(prof.resolve())
                if key not in seen:
                    seen.add(key)
                    out.append((browser_id, prof))
    return out


def _rev_host(url: str) -> str:
    try:
        from urllib.parse import urlparse
        host = (urlparse(url).hostname or "").lower()
        return ("." + host)[::-1] if host else ""
    except Exception:
        return ""


def _purge_orphan_firefox(profile: Path) -> dict[str, Any]:
    """Remove raw loopback bookmarks — HTTPS+Secure replaces them."""
    places = profile / "places.sqlite"
    if not places.is_file():
        return {"ok": False, "error": "no_places", "engine": "gecko"}
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".sqlite")
    os.close(tmp_fd)
    removed = 0
    try:
        shutil.copy2(places, tmp_path)
        conn = sqlite3.connect(tmp_path, timeout=5.0)
        cur = conn.cursor()
        cur.execute(
            "SELECT b.id, b.parent, p.url FROM moz_bookmarks b "
            "JOIN moz_places p ON b.fk = p.id "
            "WHERE b.type = 1 AND p.url LIKE 'http://127.0.0.1:%'"
        )
        for bid, parent, url in cur.fetchall():
            if not url or not _ORPHAN_LOOPBACK_RE.match(str(url)):
                continue
            cur.execute("SELECT title FROM moz_bookmarks WHERE id=? AND type=2", (parent,))
            folder = cur.fetchone()
            if folder and str(folder[0]) == "AmmoOS Field":
                continue
            cur.execute("DELETE FROM moz_bookmarks WHERE id=?", (int(bid),))
            removed += 1
        conn.commit()
        conn.close()
        if removed:
            shutil.copy2(tmp_path, places)
        return {"ok": True, "profile": str(profile), "removed": removed, "engine": "gecko"}
    except (sqlite3.Error, OSError) as exc:
        return {"ok": False, "error": str(exc), "profile": str(profile), "engine": "gecko"}
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _purge_orphan_chromium(profile: Path, *, browser_id: str) -> dict[str, Any]:
    bookmarks = profile / "Bookmarks"
    if not bookmarks.is_file():
        return {"ok": False, "error": "no_bookmarks", "engine": "chromium", "browser_id": browser_id}
    try:
        doc = json.loads(bookmarks.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": str(exc), "engine": "chromium", "browser_id": browser_id}

    def _scrub(nodes: list[Any]) -> tuple[list[Any], int]:
        out: list[Any] = []
        n = 0
        for node in nodes:
            if not isinstance(node, dict):
                continue
            if node.get("type") == "url":
                url = str(node.get("url") or "")
                if _ORPHAN_LOOPBACK_RE.match(url):
                    n += 1
                    continue
            if node.get("type") == "folder":
                kids, sub = _scrub(list(node.get("children") or []))
                node = {**node, "children": kids}
                n += sub
            out.append(node)
        return out, n

    roots = doc.setdefault("roots", {})
    removed = 0
    for key in ("bookmark_bar", "other", "synced"):
        block = roots.get(key)
        if not isinstance(block, dict):
            continue
        kids, n = _scrub(list(block.get("children") or []))
        block["children"] = kids
        removed += n
    if removed:
        backup = bookmarks.with_suffix(".bak-purge")
        shutil.copy2(bookmarks, backup)
        bookmarks.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "profile": str(profile),
        "removed": removed,
        "engine": "chromium",
        "browser_id": browser_id,
    }


def purge_orphan_bookmarks() -> dict[str, Any]:
    firefox: list[dict[str, Any]] = []
    chromium: list[dict[str, Any]] = []
    for prof in _firefox_profiles():
        firefox.append(_purge_orphan_firefox(prof))
    for browser_id, prof in _chromium_profiles():
        chromium.append(_purge_orphan_chromium(prof, browser_id=browser_id))
    total = sum(int(x.get("removed") or 0) for x in firefox + chromium)
    return {
        "ok": True,
        "schema": "queen-host-bookmark-purge/v1",
        "updated": _now(),
        "removed": total,
        "firefox": firefox,
        "chromium": chromium,
        "notice": "Raw loopback bookmarks removed — HTTPS+Secure AmmoOS Field replaces them",
    }


def _import_places(profile: Path, rows: list[dict[str, str]]) -> dict[str, Any]:
    places = profile / "places.sqlite"
    if not places.is_file():
        return {"ok": False, "error": "no_places", "engine": "gecko"}
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".sqlite")
    os.close(tmp_fd)
    try:
        shutil.copy2(places, tmp_path)
        conn = sqlite3.connect(tmp_path, timeout=5.0)
        cur = conn.cursor()
        cur.execute("SELECT id FROM moz_bookmarks WHERE parent=1 AND title='AmmoOS Field' LIMIT 1")
        row = cur.fetchone()
        if row:
            folder_id = int(row[0])
            cur.execute("DELETE FROM moz_bookmarks WHERE parent=?", (folder_id,))
        else:
            now = int(time.time() * 1_000_000)
            cur.execute(
                "INSERT INTO moz_bookmarks (type, parent, position, title, dateAdded, lastModified) "
                "VALUES (2, 1, 0, 'AmmoOS Field', ?, ?)",
                (now, now),
            )
            folder_id = int(cur.lastrowid)
        added = 0
        now = int(time.time() * 1_000_000)
        for pos, bm in enumerate(rows):
            cur.execute("SELECT id FROM moz_places WHERE url=? LIMIT 1", (bm["url"],))
            place = cur.fetchone()
            if place:
                place_id = int(place[0])
            else:
                cur.execute(
                    "INSERT INTO moz_places (url, title, rev_host, hidden, visit_count, frecency, last_visit_date) "
                    "VALUES (?, ?, ?, 0, 0, -1, 0)",
                    (bm["url"], bm["title"], _rev_host(bm["url"])),
                )
                place_id = int(cur.lastrowid)
            guid = "{" + str(uuid.uuid4()) + "}"
            cur.execute(
                "INSERT INTO moz_bookmarks (type, fk, parent, position, title, dateAdded, lastModified, guid) "
                "VALUES (1, ?, ?, ?, ?, ?, ?, ?)",
                (place_id, folder_id, pos, bm["title"], now, now, guid),
            )
            added += 1
        conn.commit()
        conn.close()
        shutil.copy2(tmp_path, places)
        return {"ok": True, "profile": str(profile), "added": added, "engine": "gecko"}
    except (sqlite3.Error, OSError) as exc:
        return {"ok": False, "error": str(exc), "profile": str(profile), "engine": "gecko"}
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _chromium_bookmark_children(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    ts = str(int(time.time() * 1_000_000))
    children: list[dict[str, Any]] = []
    for bm in rows:
        children.append({
            "date_added": ts,
            "date_last_used": "0",
            "guid": str(uuid.uuid4()),
            "id": str(len(children) + 1),
            "name": bm["title"],
            "type": "url",
            "url": bm["url"],
        })
    return children


def _import_chromium(profile: Path, rows: list[dict[str, str]], *, browser_id: str) -> dict[str, Any]:
    bookmarks = profile / "Bookmarks"
    if not bookmarks.is_file():
        return {"ok": False, "error": "no_bookmarks", "engine": "chromium", "browser_id": browser_id}
    try:
        doc = json.loads(bookmarks.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": str(exc), "engine": "chromium", "browser_id": browser_id}
    roots = doc.setdefault("roots", {})
    bar = roots.setdefault("bookmark_bar", {"children": [], "name": "Bookmarks bar", "type": "folder"})
    children = list(bar.get("children") or [])
    children = [c for c in children if not (isinstance(c, dict) and c.get("name") == "AmmoOS Field")]
    folder = {
        "children": _chromium_bookmark_children(rows),
        "date_added": str(int(time.time() * 1_000_000)),
        "date_modified": str(int(time.time() * 1_000_000)),
        "guid": str(uuid.uuid4()),
        "id": str(len(children) + 1),
        "name": "AmmoOS Field",
        "type": "folder",
    }
    children.insert(0, folder)
    bar["children"] = children
    bar["date_modified"] = str(int(time.time() * 1_000_000))
    backup = bookmarks.with_suffix(".bak-queen")
    try:
        shutil.copy2(bookmarks, backup)
        bookmarks.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        return {"ok": False, "error": str(exc), "engine": "chromium", "browser_id": browser_id}
    return {
        "ok": True,
        "profile": str(profile),
        "added": len(rows),
        "engine": "chromium",
        "browser_id": browser_id,
        "backup": str(backup),
    }


def export_host_bookmarks(*, import_browsers: bool = True, purge_orphans: bool = True) -> dict[str, Any]:
    purge_out: dict[str, Any] = {"skipped": True}
    if purge_orphans:
        purge_out = purge_orphan_bookmarks()

    trees = _load_trees()
    raw: list[dict[str, Any]] = []
    _walk(trees, raw)
    rows: list[dict[str, str]] = []
    for bm in raw:
        url = str(bm.get("url") or "")
        bm_id = str(bm.get("id") or "")
        if not url:
            continue
        if url.startswith("http://127.0.0.1") or url.startswith("https://"):
            rows.append({
                "id": bm_id,
                "title": str(bm.get("title") or bm_id or "Bookmark"),
                "url": secure_url(url, bm_id),
                "loopback_url": _loopback_url(url, bm_id) if url.startswith("http://127.0.0.1") else url,
                "hint": str(bm.get("hint") or ""),
                "https_secure": HTTPS_SECURE and (bm_id in _JUMP_IDS or ":9477" in url or ":9488" in url),
            })
    STATE.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(_netscape_html(rows), encoding="utf-8")
    firefox: list[dict[str, Any]] = []
    chromium: list[dict[str, Any]] = []
    if import_browsers:
        for prof in _firefox_profiles():
            firefox.append(_import_places(prof, rows))
        for browser_id, prof in _chromium_profiles()[:8]:
            chromium.append(_import_chromium(prof, rows, browser_id=browser_id))
    doc = {
        "ok": True,
        "schema": "queen-host-bookmark-export/v3",
        "updated": _now(),
        "count": len(rows),
        "mode": BOOKMARK_MODE,
        "https_secure": HTTPS_SECURE,
        "scheme_label": "HTTPS+Secure",
        "pages_base": PAGES_BASE,
        "html": str(OUT_HTML),
        "bookmarks": rows,
        "purge": purge_out,
        "firefox": firefox,
        "chromium": chromium,
        "browsers_supported": ["firefox", "chrome", "chromium", "brave", "edge", "vivaldi", "opera", "ie_html"],
        "notice": "All Rights Reserved — HTTPS+Secure jump URLs · Firefox toolbar AmmoOS Field",
    }
    MANIFEST.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return doc


def main() -> int:
    import sys
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "export").strip().lower()
    if cmd in ("export", "json"):
        html_only = "--html-only" in sys.argv
        no_purge = "--no-purge" in sys.argv
        out = export_host_bookmarks(import_browsers=not html_only, purge_orphans=not no_purge)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("ok") else 1
    if cmd in ("purge", "purge_orphans", "clean"):
        out = purge_orphan_bookmarks()
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("ok") else 1
    print(json.dumps({
        "error": "usage: queen-host-bookmark-export.py [export|json|purge] [--html-only] [--no-purge]",
        "modes": ["pages", "loopback", "dual"],
        "scheme": "HTTPS+Secure",
    }))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())