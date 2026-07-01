#!/usr/bin/env pythong
"""Queen Program Library v3 — Dewey-classified icon index, zero-copy serve, AI-operable metadata."""
from __future__ import annotations

import configparser
import hashlib
import importlib.util
import io
import json
import mimetypes
import os
import platform
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

_ICON_KIT_MOD: Any = None

QUEEN = Path(__file__).resolve().parents[1]
NEXUS = QUEEN.parent
SG = NEXUS.parent
STATE = Path(os.environ.get("NEXUS_STATE_DIR", QUEEN / ".nexus-state"))
LIBRARY_PATH = STATE / "queen-program-library.json"
BATTERY_PATH = QUEEN / "data" / "queen-icon-battery.json"
FILE_TYPES_PATH = QUEEN / "data" / "queen-file-types.json"
DEWEY_MAP_PATH = NEXUS / "data" / "dewey-decimal-map.json"
DEWEY_ROOT = NEXUS / "library" / "dewey"
DEVICE_ASSETS = NEXUS / "library" / "assets" / "devices"
CARTRIDGE_ASSETS = NEXUS / "library" / "assets" / "cartridges"
NES_CATALOG_PATH = NEXUS / "data" / "nes-cartridge-catalog.json"
FORGED_ICONS = QUEEN / "world" / "assets" / "icons" / "forged"
SHELL_ICONS = QUEEN / "world" / "assets" / "icons" / "shell"
ICON_MANIFEST = QUEEN / "data" / "queen-windows-icons-manifest.json"
WORLD_ASSETS = QUEEN / "world" / "assets"
WORLD_ICONS = WORLD_ASSETS / "icons"
WORLD_BRANDING = WORLD_ASSETS / "branding"

_KIND_DEWEY: dict[str, tuple[str, str]] = {
    "queen_program": ("005.4", "Systems & programs"),
    "host_program": ("005.4", "Systems & programs"),
    "file_type": ("005.74", "Data formats & file types"),
    "queen_asset": ("006.3", "Computer graphics"),
    "queen_branding": ("006.3", "Computer graphics"),
    "dewey_book": ("004", "Computer science & platforms"),
    "dewey_shelf": ("000", "General works"),
    "game_console": ("004.678", "Computer platforms — consoles"),
    "video_game": ("794.8", "Indoor games — video games"),
    "device_platform": ("004.16", "Personal computers & devices"),
    "shell_icon": ("005.4", "Desktop shell"),
    "dos_icon": ("004.16", "DOS era"),
    "kilroy_icon": ("005.437", "KILROY kernel"),
    "game_media_icon": ("794.8", "Game media"),
}

ICON_EXTS = (".png", ".svg", ".xpm", ".jpg", ".jpeg", ".webp", ".ico")

LINUX_SCAN_DIRS = (
    "/usr/share/applications",
    "/usr/local/share/applications",
    "~/.local/share/applications",
    "/var/lib/snapd/desktop/applications",
    "/var/lib/flatpak/exports/share/applications",
    "~/.local/share/flatpak/exports/share/applications",
)

HOST_ICON_ROOTS = (
    "/usr/share/icons",
    "/usr/share/pixmaps",
    "~/.local/share/icons",
    "/usr/share/applications",
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _expand(path_text: str) -> Path:
    return Path(path_text.replace("HOME", str(Path.home()))).expanduser()


def _world_url(path: Path) -> str | None:
    """Direct static URL for icons under Queen world — no API hop, no copy."""
    try:
        rel = path.resolve().relative_to((QUEEN / "world").resolve())
        return f"/world/{rel.as_posix()}"
    except ValueError:
        return None


def _api_icon_url(entry_id: str) -> str:
    return f"/api/queen-program-library/icon/{quote(entry_id, safe='')}"


def _dewey_map() -> dict[str, Any]:
    return _load(DEWEY_MAP_PATH, {})


def _dewey_label(code: str) -> str:
    doc = _dewey_map()
    code = str(code or "").strip()
    if not code:
        return ""
    for subj in (doc.get("subjects") or {}).values():
        if str(subj.get("code")) == code:
            return str(subj.get("label") or code)
    root = code[:3].ljust(3, "0")
    for cls in doc.get("classes") or []:
        if str(cls.get("code")) == root:
            return str(cls.get("title") or root)
    return code


def _classify_dewey(
    *,
    name: str = "",
    kind: str = "",
    text: str = "",
    explicit: str = "",
    shelf: str = "",
) -> tuple[str, str]:
    if explicit:
        return explicit, _dewey_label(explicit)
    if kind in _KIND_DEWEY:
        return _KIND_DEWEY[kind]
    blob = f"{name} {text} {shelf}".lower()
    best_code = ""
    best_score = 0
    for rule in _dewey_map().get("keyword_rules") or []:
        code = str(rule.get("code") or "")
        score = sum(1 for t in rule.get("tokens") or [] if t in blob)
        if score > best_score:
            best_score = score
            best_code = code
    if best_code:
        return best_code, _dewey_label(best_code)
    default = _KIND_DEWEY.get(kind, ("000", "General works"))
    return default


def _stamp_dewey(row: dict[str, Any]) -> None:
    if row.get("dewey") and row.get("dewey_label"):
        return
    code, label = _classify_dewey(
        name=str(row.get("name") or ""),
        kind=str(row.get("kind") or ""),
        text=" ".join(
            [
                str(row.get("ai", {}).get("description") or ""),
                str(row.get("category") or ""),
                str(row.get("genre") or ""),
                str(row.get("console_id") or ""),
                str(row.get("shelf") or ""),
                str(row.get("source") or ""),
            ]
        ),
        explicit=str(row.get("dewey") or ""),
        shelf=str(row.get("shelf") or ""),
    )
    row["dewey"] = code
    row["dewey_label"] = label


def _ai_block(
    *,
    kind: str,
    name: str,
    operate: str,
    command: str = "",
    description: str = "",
    surface: str = "",
    extensions: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "name": name,
        "operate": operate,
        "command": command,
        "description": description or name,
        "surface": surface,
        "extensions": extensions or [],
    }


def _allowed_icon_path(path: Path) -> bool:
    try:
        resolved = path.resolve()
    except OSError:
        return False
    roots: list[Path] = [
        WORLD_ASSETS.resolve(),
        (QUEEN / "world").resolve(),
        DEVICE_ASSETS.resolve(),
        CARTRIDGE_ASSETS.resolve(),
        FORGED_ICONS.resolve(),
        SHELL_ICONS.resolve(),
        _expand("~/.local/share/icons"),
        Path("/usr/share/icons"),
        Path("/usr/share/pixmaps"),
        Path("/usr/share/applications"),
        Path("/var/lib/snapd/desktop/applications"),
    ]
    for root in roots:
        try:
            if root.is_dir():
                resolved.relative_to(root)
                return True
        except ValueError:
            continue
    return False


def _pick_icon_file(candidates: list[Path]) -> Path | None:
    for p in candidates:
        if p.is_file() and _allowed_icon_path(p):
            return p.resolve()
    return None


def _resolve_host_icon(icon_name: str, desktop_path: str | None = None) -> Path | None:
    if not icon_name:
        return None
    raw = Path(icon_name)
    if raw.is_file():
        return raw.resolve() if _allowed_icon_path(raw) else None
    if desktop_path:
        sib = Path(desktop_path).parent / icon_name
        found = _pick_icon_file([sib.with_suffix(e) if e else sib for e in ("", *ICON_EXTS)])
        if found:
            return found
    name = Path(icon_name).stem if icon_name.endswith(tuple(ICON_EXTS)) else icon_name
    sizes = ("256x256", "128x128", "64x64", "48x48", "32x32", "24x24", "22x22", "16x16", "scalable")
    candidates: list[Path] = []
    for base in [_expand(p) for p in HOST_ICON_ROOTS]:
        if not base.is_dir():
            continue
        for sz in sizes:
            for ext in ICON_EXTS:
                candidates.append(base / sz / "apps" / f"{name}{ext}")
        for ext in ICON_EXTS:
            candidates.append(base / f"{name}{ext}")
    return _pick_icon_file(candidates)


def _entry(
    entry_id: str,
    *,
    name: str,
    kind: str,
    icon_path: Path | None,
    source: str,
    operate: str,
    command: str = "",
    description: str = "",
    surface: str = "",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": entry_id,
        "name": name,
        "kind": kind,
        "source": source,
        "icon_path": str(icon_path) if icon_path else None,
        "icon_url": None,
        "serve_mode": "none",
        "ai": _ai_block(
            kind=kind,
            name=name,
            operate=operate,
            command=command,
            description=description,
            surface=surface,
        ),
    }
    if icon_path and icon_path.is_file():
        web = _world_url(icon_path)
        if web:
            row["icon_url"] = web
            row["serve_mode"] = "static"
        else:
            row["icon_url"] = _api_icon_url(entry_id)
            row["serve_mode"] = "stream"
        try:
            st = icon_path.stat()
            row["icon_mtime"] = int(st.st_mtime)
            row["icon_bytes"] = st.st_size
        except OSError:
            pass
    if extra:
        row.update(extra)
    _stamp_dewey(row)
    return row


def _scan_queen_battery(entries: dict[str, Any]) -> int:
    bat = _load(BATTERY_PATH, {})
    added = 0
    icons_dir = WORLD_ICONS
    for prog in bat.get("programs") or []:
        eid = f"queen-prog-{prog}"
        candidates = [icons_dir / f"prog-{prog}-{sz}.png" for sz in (48, 32, 64, 24)] + [
            icons_dir / f"prog-{prog}.png",
        ]
        icon = _pick_icon_file(candidates)
        entries[eid] = _entry(
            eid,
            name=prog.replace("-", " ").title(),
            kind="queen_program",
            icon_path=icon,
            source="queen-icon-battery",
            operate="queen_launch",
            command=f"queen://{prog}" if prog not in ("browser", "files", "code", "terminal") else "",
            surface=f"queen-{prog}",
        )
        added += 1
    for fid in bat.get("files") or []:
        eid = f"file-{fid}"
        candidates = [icons_dir / f"file-{fid}-{sz}.png" for sz in (48, 32, 20)] + [
            icons_dir / f"file-{fid}.png",
        ]
        icon = _pick_icon_file(candidates)
        entries[eid] = _entry(
            eid,
            name=fid.replace("-", " ").title(),
            kind="file_type",
            icon_path=icon,
            source="queen-icon-battery",
            operate="file_type_icon",
            description=f"Queen Files icon for {fid} type",
            surface="queen-files",
        )
        added += 1
    return added


def _scan_queen_assets(entries: dict[str, Any]) -> int:
    added = 0
    for base, kind in ((WORLD_ICONS, "queen_asset"), (WORLD_BRANDING, "queen_branding")):
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.suffix.lower() not in ICON_EXTS:
                continue
            eid = f"asset-{path.stem}"
            if eid in entries:
                continue
            entries[eid] = _entry(
                eid,
                name=path.stem.replace("-", " ").title(),
                kind=kind,
                icon_path=path,
                source=str(path.relative_to(WORLD_ASSETS)),
                operate="display_icon",
                surface="queen-assets",
            )
            added += 1
    return added


def _scan_classic_programs(entries: dict[str, Any]) -> int:
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("queen_desktop", QUEEN / "lib" / "queen-desktop.py")
        if not spec or not spec.loader:
            return 0
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        programs = mod.CLASSIC_PROGRAMS
    except Exception:
        return 0
    added = 0
    for p in programs:
        pid = p.get("id") or ""
        if not pid:
            continue
        eid = f"queen-prog-{pid}"
        candidates = [WORLD_ICONS / f"prog-{pid}-{sz}.png" for sz in (48, 32, 64)] + [
            WORLD_ICONS / f"prog-{p.get('icon', pid)}-48.png",
            WORLD_ICONS / f"prog-{pid}.png",
        ]
        icon = _pick_icon_file(candidates)
        url = p.get("url") or ""
        entries[eid] = _entry(
            eid,
            name=p.get("name") or pid,
            kind="queen_program",
            icon_path=icon,
            source="queen-desktop",
            operate="open_url" if url.startswith("/") or url.startswith("http") else "queen_launch",
            command=url,
            description=f"Queen desktop program — {p.get('name')}",
            surface="queen-desktop",
            extra={
                "category": p.get("category"),
                "sdf_kind": p.get("kind"),
                "pinned": p.get("pinned"),
            },
        )
        added += 1
    return added


def _scan_file_types(entries: dict[str, Any]) -> int:
    reg = _load(FILE_TYPES_PATH, {})
    added = 0
    for tid, spec in (reg.get("types") or {}).items():
        eid = f"type-{tid}"
        candidates: list[Path] = []
        asset = spec.get("icon_asset")
        if asset:
            candidates.append(WORLD_ICONS / asset)
        for ext in spec.get("extensions") or []:
            stem = ext.lstrip(".")
            candidates.extend([WORLD_ICONS / f"file-{stem}-{sz}.png" for sz in (48, 32)])
        candidates.append(WORLD_ICONS / f"file-{tid}-48.png")
        icon = _pick_icon_file(candidates)
        entries[eid] = _entry(
            eid,
            name=spec.get("label") or tid,
            kind="file_type",
            icon_path=icon,
            source="queen-file-types",
            operate=spec.get("action") or "open_tab",
            command=spec.get("open_with") or "",
            description=spec.get("label") or tid,
            surface="queen-files",
            extra={
                "type_id": tid,
                "extensions": spec.get("extensions") or [],
                "compileable": bool(spec.get("compileable")),
                "global_icon": spec.get("global_icon"),
            },
        )
        entries[eid]["ai"]["extensions"] = spec.get("extensions") or []
        added += 1
    return added


def _parse_desktop(path: Path) -> dict[str, Any] | None:
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.optionxform = str  # type: ignore[method-assign]
    try:
        cfg.read_string(raw)
    except configparser.Error:
        return None
    if not cfg.has_section("Desktop Entry"):
        return None
    sec = cfg["Desktop Entry"]
    if sec.get("Type", "Application") != "Application":
        return None
    if sec.get("Hidden", "").lower() == "true" or sec.get("NoDisplay", "").lower() == "true":
        return None
    name = (sec.get("Name") or sec.get("GenericName") or path.stem).strip()
    exec_raw = (sec.get("Exec") or "").strip()
    if not name or not exec_raw:
        return None
    exec_clean = re.sub(r"%[fFuUdDnNickvm]", "", exec_raw).strip()
    icon = (sec.get("Icon") or "").strip() or path.stem
    categories = [c.strip() for c in (sec.get("Categories") or "").split(";") if c.strip()]
    return {
        "name": name,
        "exec": exec_clean,
        "exec_raw": exec_raw,
        "icon_name": icon,
        "category": categories[0] if categories else "Other",
        "categories": categories,
        "comment": (sec.get("Comment") or "").strip(),
        "desktop_path": str(path.resolve()),
        "desktop_file": path.name,
        "terminal": sec.get("Terminal", "false").lower() == "true",
    }


def _scan_host_programs(entries: dict[str, Any]) -> int:
    if platform.system().lower() != "linux" and not os.environ.get("QUEEN_LIBRARY_FORCE_SCAN"):
        return 0
    seen: set[str] = set()
    added = 0
    for base in [_expand(d) for d in LINUX_SCAN_DIRS]:
        if not base.is_dir():
            continue
        for path in sorted(base.glob("*.desktop")):
            row = _parse_desktop(path)
            if not row:
                continue
            dedupe = row["name"].lower()
            if dedupe in seen:
                continue
            seen.add(dedupe)
            eid = f"host-{path.stem}"
            icon = _resolve_host_icon(row["icon_name"], row.get("desktop_path"))
            entry = _entry(
                eid,
                name=row["name"],
                kind="host_program",
                icon_path=icon,
                source="linux_desktop",
                operate="host_exec",
                command=row["exec"],
                description=row.get("comment") or row["name"],
                surface="host-os",
                extra={
                    "exec_raw": row.get("exec_raw"),
                    "desktop_path": row.get("desktop_path"),
                    "desktop_file": row.get("desktop_file"),
                    "category": row.get("category"),
                    "categories": row.get("categories"),
                    "icon_name": row.get("icon_name"),
                    "terminal": row.get("terminal"),
                },
            )
            entries[eid] = entry
            added += 1
    return added


def _pick_forged_icon(stem: str, *, prefer: int = 48) -> Path | None:
    candidates: list[Path] = []
    for base in (FORGED_ICONS, SHELL_ICONS):
        if not base.is_dir():
            continue
        for sz in (prefer, 64, 32, 24):
            candidates.append(base / f"{stem}-{sz}.png")
        for sub in base.iterdir():
            if sub.is_dir():
                for sz in (prefer, 64, 32):
                    candidates.append(sub / f"{stem}-{sz}.png")
        for path in sorted(base.rglob(f"{stem}-*.png")):
            candidates.append(path)
    return _pick_icon_file(candidates)


def _scan_dewey_library(entries: dict[str, Any]) -> int:
    added = 0
    if not DEWEY_ROOT.is_dir():
        return 0
    for shelf_path in sorted(DEWEY_ROOT.rglob("shelf.json")):
        shelf_doc = _load(shelf_path, {})
        shelf_id = str(shelf_doc.get("shelf") or shelf_path.parent.name)
        shelf_code = str(shelf_doc.get("code") or "")
        shelf_title = str(shelf_doc.get("title") or shelf_id)
        seid = f"dewey-shelf-{shelf_id}"
        if seid not in entries:
            entries[seid] = _entry(
                seid,
                name=shelf_title,
                kind="dewey_shelf",
                icon_path=None,
                source=str(shelf_path.relative_to(NEXUS)),
                operate="dewey_browse",
                command=f"dewey://{shelf_id}",
                description=f"Dewey shelf — {shelf_title}",
                surface="queen-library",
                extra={"shelf": shelf_id, "dewey": shelf_code or None, "book_count": shelf_doc.get("book_count")},
            )
            added += 1
        for book in shelf_doc.get("books") or []:
            bid = str(book.get("id") or "")
            if not bid:
                continue
            eid = f"dewey-book-{bid}"
            if eid in entries:
                continue
            dewey = str(book.get("dewey") or shelf_code or "000")
            cover_url = str(book.get("cover") or "")
            icon = None
            if cover_url.startswith("/library/"):
                cov_path = NEXUS / cover_url.lstrip("/")
                if cov_path.is_file():
                    icon = cov_path.resolve()
            if not icon:
                dev = DEVICE_ASSETS / f"{bid}.png"
                if dev.is_file():
                    icon = dev.resolve()
                else:
                    cart = CARTRIDGE_ASSETS / "nes" / f"{bid}-box.png"
                    icon = cart.resolve() if cart.is_file() else None
            if not icon:
                icon = _pick_forged_icon(bid) or _pick_forged_icon(bid.replace("_", "-"))
            extra_book: dict[str, Any] = {
                "shelf": shelf_id,
                "dewey": dewey,
                "dewey_label": _dewey_label(dewey),
                "format": book.get("format"),
                "h7c": book.get("h7c"),
                "ready": book.get("ready"),
            }
            if cover_url:
                extra_book["cover_url"] = cover_url
            if book.get("has_rom"):
                extra_book["has_rom"] = True
            if book.get("console_id"):
                extra_book["console_id"] = book.get("console_id")
            entries[eid] = _entry(
                eid,
                name=str(book.get("title") or bid),
                kind="dewey_book",
                icon_path=icon,
                source=str(book.get("h7c") or shelf_path),
                operate="open_h7c",
                command=str(book.get("h7c") or ""),
                description=f"Dewey {dewey} — {book.get('title')}",
                surface="queen-library",
                extra=extra_book,
            )
            added += 1
    return added


def _scan_device_icons(entries: dict[str, Any]) -> int:
    added = 0
    if not DEVICE_ASSETS.is_dir():
        return 0
    for path in sorted(DEVICE_ASSETS.glob("*.png")):
        eid = f"device-{path.stem}"
        if eid in entries:
            continue
        entries[eid] = _entry(
            eid,
            name=path.stem.replace("_", " ").replace("-", " ").title(),
            kind="device_platform",
            icon_path=path.resolve(),
            source=str(path.relative_to(NEXUS)),
            operate="display_icon",
            description=f"Platform device icon — {path.stem}",
            surface="queen-library",
            extra={"platform_id": path.stem},
        )
        added += 1
    return added


def _scan_forged_icons(entries: dict[str, Any]) -> int:
    added = 0
    manifest = _load(ICON_MANIFEST, {})
    kind_by_cat = {
        "shell": "shell_icon",
        "dos": "dos_icon",
        "kilroy": "kilroy_icon",
        "game_media": "game_media_icon",
    }
    for cat_name, cat in (manifest.get("categories") or {}).items():
        kind = kind_by_cat.get(cat_name, "queen_asset")
        dewey = str(cat.get("dewey") or "")
        for spec in cat.get("icons") or []:
            iid = str(spec.get("id") or "")
            if not iid:
                continue
            eid = f"forged-{iid}"
            if eid in entries:
                continue
            icon = _pick_forged_icon(iid, prefer=48) or _pick_icon_file(
                [FORGED_ICONS / cat_name / f"{iid}-48.png", SHELL_ICONS / f"{iid}-48.png"]
            )
            entries[eid] = _entry(
                eid,
                name=str(spec.get("label") or iid),
                kind=kind,
                icon_path=icon,
                source=f"forged/{cat_name}/{iid}",
                operate="display_icon",
                description=f"Queen-forged {cat_name} icon — {spec.get('label')}",
                surface="queen-desktop",
                extra={"glyph": spec.get("glyph"), "category": cat_name, "dewey": dewey, "dewey_label": _dewey_label(dewey)},
            )
            added += 1
    for sub, kind in (("consoles", "game_console"), ("games", "video_game")):
        base = FORGED_ICONS / sub
        if not base.is_dir():
            continue
        seen: set[str] = set()
        for path in sorted(base.glob("*-48.png")):
            stem = path.name.replace("-48.png", "")
            if stem in seen:
                continue
            seen.add(stem)
            eid = f"{kind}-{stem}" if kind == "game_console" else f"game-{stem}"
            if eid in entries:
                continue
            icon = path.resolve()
            if kind == "game_console":
                entries[eid] = _entry(
                    eid,
                    name=stem.replace("_", " ").title(),
                    kind=kind,
                    icon_path=icon,
                    source=str(path.relative_to(FORGED_ICONS)),
                    operate="game_console",
                    command=f"console://{stem}",
                    description=f"Game console — {stem}",
                    surface="queen-gameroom",
                    extra={"console_id": stem},
                )
            else:
                entries[eid] = _entry(
                    eid,
                    name=stem.replace("_", " ").title(),
                    kind=kind,
                    icon_path=icon,
                    source=str(path.relative_to(FORGED_ICONS)),
                    operate="open_game",
                    command=f"game://{stem}",
                    description=f"Video game — {stem}",
                    surface="queen-gameroom",
                    extra={"game_id": stem},
                )
            added += 1
    return added


def _scan_videogames(entries: dict[str, Any]) -> int:
    added = 0
    try:
        import importlib.util
        vg_path = NEXUS / "Hostess7" / "scripts" / "field_videogame_db.py"
        spec = importlib.util.spec_from_file_location("field_videogame_db", vg_path)
        if not spec or not spec.loader:
            return 0
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.ensure_db()
        data = json.loads(mod.DB_PATH.read_text(encoding="utf-8"))
    except Exception:
        return 0

    for c in data.get("consoles") or []:
        cid = str(c.get("id") or "")
        if not cid:
            continue
        eid = f"console-{cid}"
        if eid in entries:
            continue
        icon = _pick_icon_file(
            [
                FORGED_ICONS / "consoles" / f"{cid}-48.png",
                DEVICE_ASSETS / f"{cid}.png",
            ]
        )
        entries[eid] = _entry(
            eid,
            name=str(c.get("name") or cid),
            kind="game_console",
            icon_path=icon,
            source="field_videogame_db",
            operate="game_console",
            command=f"console://{cid}",
            description=f"{c.get('maker', '')} {c.get('name', '')} ({c.get('year', '')})".strip(),
            surface="queen-gameroom",
            extra={
                "console_id": cid,
                "year": c.get("year"),
                "maker": c.get("maker"),
                "media": c.get("media"),
                "generation": c.get("generation"),
                "dewey": "004.678",
                "dewey_label": _dewey_label("004.678"),
            },
        )
        added += 1

    for g in data.get("games") or []:
        gid = str(g.get("id") or "")
        if not gid:
            continue
        eid = f"game-{gid}"
        if eid in entries:
            continue
        cid = str(g.get("console_id") or "")
        icon = _pick_icon_file([
            FORGED_ICONS / "games" / f"{gid}-48.png",
            CARTRIDGE_ASSETS / "nes" / f"{gid}-box.png",
            CARTRIDGE_ASSETS / "nes" / f"{gid}-cart.png",
        ])
        extra: dict[str, Any] = {
            "game_id": gid,
            "console_id": cid,
            "year": g.get("year"),
            "publisher": g.get("publisher"),
            "developer": g.get("developer"),
            "genre": g.get("genre"),
            "media_type": g.get("media_type"),
            "dewey": "794.8",
            "dewey_label": _dewey_label("794.8"),
        }
        if g.get("box_art_url"):
            extra["cover_url"] = g.get("box_art_url")
        if g.get("has_rom"):
            extra["has_rom"] = True
        if g.get("license_label"):
            extra["license_label"] = g.get("license_label")
        if g.get("hardware_form"):
            extra["hardware_form"] = g.get("hardware_form")
        if g.get("ines"):
            extra["ines"] = g.get("ines")
        entries[eid] = _entry(
            eid,
            name=str(g.get("title") or gid),
            kind="video_game",
            icon_path=icon,
            source="field_videogame_db",
            operate="open_game",
            command=f"game://{gid}",
            description=str(g.get("description") or g.get("title") or gid),
            surface="queen-gameroom",
            extra=extra,
        )
        added += 1
    return added


def _library_facets(entries: list[dict[str, Any]]) -> dict[str, Any]:
    kinds: dict[str, int] = {}
    dewey_roots: dict[str, int] = {}
    platforms: dict[str, int] = {}
    for e in entries:
        k = str(e.get("kind") or "other")
        kinds[k] = kinds.get(k, 0) + 1
        d = str(e.get("dewey") or "000")
        root = d[:3].ljust(3, "0")
        dewey_roots[root] = dewey_roots.get(root, 0) + 1
        pid = e.get("console_id") or e.get("platform_id")
        if pid:
            platforms[str(pid)] = platforms.get(str(pid), 0) + 1
    return {
        "kinds": [{"id": k, "count": v} for k, v in sorted(kinds.items(), key=lambda x: -x[1])],
        "dewey": [{"code": k, "label": _dewey_label(k), "count": v} for k, v in sorted(dewey_roots.items())],
        "platforms": [{"id": k, "count": v} for k, v in sorted(platforms.items(), key=lambda x: -x[1])[:24]],
    }


def build_library(*, include_host: bool = True) -> dict[str, Any]:
    entries: dict[str, Any] = {}
    _scan_queen_battery(entries)
    _scan_queen_assets(entries)
    _scan_classic_programs(entries)
    _scan_file_types(entries)
    dewey_n = _scan_dewey_library(entries)
    device_n = _scan_device_icons(entries)
    forged_n = _scan_forged_icons(entries)
    game_n = _scan_videogames(entries)
    host_n = _scan_host_programs(entries) if include_host else 0
    for row in entries.values():
        _stamp_dewey(row)
    programs = [e for e in entries.values() if e.get("kind") in ("queen_program", "host_program")]
    games = [e for e in entries.values() if e.get("kind") in ("video_game", "game_console")]
    programs.sort(key=lambda x: (x.get("kind") != "queen_program", (x.get("name") or "").lower()))
    games.sort(key=lambda x: ((x.get("kind") != "video_game"), (x.get("name") or "").lower()))
    with_icon = sum(1 for e in entries.values() if e.get("icon_url"))
    static_n = sum(1 for e in entries.values() if e.get("serve_mode") == "static")
    stream_n = sum(1 for e in entries.values() if e.get("serve_mode") == "stream")
    all_entries = list(entries.values())
    doc = {
        "schema": "queen-program-library/v3",
        "motto": "Dewey-classified icon index · zero-copy serve · AI-operable metadata",
        "policy": {
            "icon_cache": False,
            "disk_copy": False,
            "prefer_static_world_urls": True,
            "http_cache": "no-store",
            "dewey_required": True,
            "local_icon_generation": True,
            "generation_engine": "queen-icon-kit/pil",
        },
        "updated": _now(),
        "host_os": platform.system().lower(),
        "count": len(entries),
        "programs_count": len(programs),
        "games_count": len(games),
        "dewey_books": dewey_n,
        "device_icons": device_n,
        "forged_icons": forged_n,
        "videogame_entries": game_n,
        "host_programs": host_n,
        "icons_resolved": with_icon,
        "serve_static": static_n,
        "serve_stream": stream_n,
        "facets": _library_facets(all_entries),
        "entries": entries,
        "programs": programs,
        "games": games,
        "index": {
            eid: {
                "icon_url": e.get("icon_url"),
                "name": e.get("name"),
                "kind": e.get("kind"),
                "dewey": e.get("dewey"),
                "dewey_label": e.get("dewey_label"),
            }
            for eid, e in entries.items()
        },
    }
    _save(LIBRARY_PATH, doc)
    return {"ok": True, "built": len(entries), **doc}


def library_doc(*, index_only: bool = False) -> dict[str, Any]:
    doc = _load(LIBRARY_PATH, {})
    if not doc.get("entries"):
        return build_library()
    if index_only:
        return {
            "ok": True,
            "schema": doc.get("schema"),
            "updated": doc.get("updated"),
            "count": doc.get("count"),
            "policy": doc.get("policy"),
            "index": doc.get("index") or {},
        }
    return {"ok": True, **doc}


def _find_entry(entry_id: str) -> dict[str, Any] | None:
    doc = _load(LIBRARY_PATH, {})
    entries = doc.get("entries") or {}
    if entry_id in entries:
        return entries[entry_id]
    for eid, row in entries.items():
        if row.get("name", "").lower() == entry_id.lower():
            return row
    return None


def _icon_kit_mod() -> Any:
    global _ICON_KIT_MOD
    if _ICON_KIT_MOD is not None:
        return _ICON_KIT_MOD
    kit = QUEEN / "scripts" / "queen-icon-kit.py"
    if not kit.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("queen_icon_kit", kit)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _ICON_KIT_MOD = mod
        return mod
    except Exception:
        return None


def _entry_prog_id(entry_id: str, row: dict[str, Any] | None = None) -> str:
    ref = str(entry_id or "").strip()
    if ref.startswith("queen-prog-"):
        return ref.removeprefix("queen-prog-")
    if ref.startswith("prog-"):
        return ref.removeprefix("prog-")
    if ref.startswith("host-"):
        return ref.removeprefix("host-")
    if ref.startswith("file-"):
        return ref
    if row:
        name = str(row.get("name") or row.get("id") or "").strip().lower()
        if name:
            return re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    return re.sub(r"[^a-z0-9_-]+", "-", ref.lower()).strip("-")


def _generate_icon_png(entry_id: str, *, size: int = 48, row: dict[str, Any] | None = None) -> bytes | None:
    """Unlimited local PIL icon generation — no cloud, no quota."""
    kit = _icon_kit_mod()
    if not kit:
        return None
    prog_id = _entry_prog_id(entry_id, row)
    try:
        if prog_id.startswith("file-"):
            img = kit.render_file_icon(prog_id.removeprefix("file-"), size)
        else:
            face = None
            branding = WORLD_BRANDING / "amouranth-gentle.png"
            portrait_ids = {
                "ammoos", "nexus", "browser", "os", "field", "c2-desktop",
                "nexus-c2-desktop", "nexus-c2", "command", "shield",
            }
            if branding.is_file() and prog_id in portrait_ids:
                from PIL import Image

                face = Image.open(branding)
            img = kit.render_program_icon(prog_id, size, face)
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue()
    except Exception:
        return None


def _serve_icon_from_h7s_bundle(entry_id: str) -> tuple[bytes, str, dict[str, str]] | None:
    """Fast path — desktop H7s condenser slice (no filesystem scan)."""
    bundle_py = NEXUS / "lib" / "field-h7s-desktop-bundle.py"
    if not bundle_py.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("field_h7s_desktop_serve", bundle_py)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if not hasattr(mod, "read_icon"):
            return None
        hit = mod.read_icon(entry_id)
        if not hit:
            return None
        data, meta = hit
        mime = (meta.get("blob") or {}).get("mime") or "image/png"
        return data, mime, {
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "X-Queen-Serve-Mode": "h7s_slice",
            "X-Queen-Icon-Source": "field-desktop.h7s",
            "X-Queen-Icon-Ref": entry_id,
        }
    except Exception:
        return None


def serve_icon_bytes(entry_id: str, *, size: int = 48) -> tuple[bytes, str, dict[str, str]] | None:
    """Stream icon from H7s bundle, source path, or local generate on miss."""
    bundled = _serve_icon_from_h7s_bundle(entry_id)
    if bundled:
        return bundled
    row = _find_entry(entry_id)
    raw = row.get("icon_path") if row else None
    if raw:
        path = Path(raw)
        if path.is_file() and _allowed_icon_path(path):
            mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
            try:
                data = path.read_bytes()
            except OSError:
                data = None
            if data:
                headers = {
                    "Cache-Control": "no-store, no-cache, must-revalidate",
                    "X-Queen-Serve-Mode": row.get("serve_mode") or "stream",
                    "X-Queen-Icon-Source": str(path),
                }
                try:
                    headers["ETag"] = f'"{int(path.stat().st_mtime)}-{path.stat().st_size}"'
                except OSError:
                    pass
                return data, mime, headers
    generated = _generate_icon_png(entry_id, size=size, row=row)
    if generated:
        headers = {
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "X-Queen-Serve-Mode": "generated",
            "X-Queen-Icon-Source": "local:queen-icon-kit",
            "X-Queen-Icon-Ref": entry_id,
        }
        return generated, "image/png", headers
    return None


def resolve_icon(ref: str) -> dict[str, Any]:
    ref = (ref or "").strip()
    if not ref:
        return {"ok": False, "error": "ref_required"}
    doc = library_doc()
    entries = doc.get("entries") or {}
    aliases = {
        "folder": "file-folder",
        "file": "file-file",
        "program": "queen-prog-kilroy",
    }
    candidates = [ref, aliases.get(ref), f"queen-prog-{ref}", f"file-{ref}", f"type-{ref}", f"host-{ref}", f"asset-{ref}"]
    for cid in candidates:
        if cid and cid in entries:
            row = entries[cid]
            return {"ok": True, "ref": ref, "entry": row, "icon_url": row.get("icon_url"), "ai": row.get("ai")}
    return {"ok": False, "error": "not_found", "ref": ref}


def _search_blob(entry: dict[str, Any]) -> str:
    parts = [
        entry.get("name"),
        entry.get("id"),
        entry.get("kind"),
        entry.get("dewey"),
        entry.get("dewey_label"),
        entry.get("source"),
        entry.get("category"),
        entry.get("genre"),
        entry.get("console_id"),
        entry.get("platform_id"),
        entry.get("publisher"),
        entry.get("maker"),
        entry.get("shelf"),
        (entry.get("ai") or {}).get("command"),
        (entry.get("ai") or {}).get("description"),
        (entry.get("ai") or {}).get("operate"),
    ]
    return " ".join(str(p) for p in parts if p).lower()


def search_library_advanced(
    query: str,
    *,
    limit: int = 80,
    kind: str = "",
    dewey: str = "",
    platform: str = "",
) -> dict[str, Any]:
    doc = library_doc()
    entries = list((doc.get("entries") or {}).values())
    q = (query or "").strip().lower()
    tokens = [t for t in re.split(r"\W+", q) if len(t) > 1]
    kind_f = (kind or "").strip().lower()
    dewey_f = (dewey or "").strip()
    platform_f = (platform or "").strip().lower()
    scored: list[tuple[int, dict[str, Any]]] = []

    for e in entries:
        if kind_f and str(e.get("kind") or "").lower() != kind_f:
            continue
        if dewey_f and not str(e.get("dewey") or "").startswith(dewey_f):
            continue
        if platform_f:
            plat = str(e.get("console_id") or e.get("platform_id") or "").lower()
            if platform_f not in plat and platform_f not in _search_blob(e):
                continue
        if not q and not kind_f and not dewey_f and not platform_f:
            scored.append((0, e))
            continue
        blob = _search_blob(e)
        score = 0
        if q and q in blob:
            score += 20
        if dewey_f and str(e.get("dewey") or "").startswith(dewey_f):
            score += 14
        for t in tokens:
            if t in str(e.get("id") or "").lower():
                score += 12
            if t in str(e.get("name") or "").lower():
                score += 10
            if t in str(e.get("dewey") or ""):
                score += 9
            if t in str(e.get("dewey_label") or "").lower():
                score += 8
            if t in str(e.get("kind") or "").lower():
                score += 6
            if t in blob:
                score += 4
        if score > 0 or (not q and (kind_f or dewey_f or platform_f)):
            scored.append((score, e))

    scored.sort(key=lambda x: (-x[0], str(x[1].get("name") or "").lower()))
    hits = [{**row, "score": sc} for sc, row in scored[:limit]]
    return {
        "ok": True,
        "query": q,
        "hits": hits,
        "count": len(hits),
        "total": len(entries),
        "facets": doc.get("facets") or _library_facets(entries),
        "search_engine": "queen-library/v3-token-dewey",
    }


def search_library(query: str, *, limit: int = 80, **filters: Any) -> dict[str, Any]:
    return search_library_advanced(
        query,
        limit=limit,
        kind=str(filters.get("kind") or ""),
        dewey=str(filters.get("dewey") or ""),
        platform=str(filters.get("platform") or ""),
    )


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")
    if action in ("status", "json", "library"):
        return library_doc(index_only=body.get("index_only") is True)
    if action in ("scan", "rescan", "library_scan", "build"):
        return build_library(include_host=body.get("host", True) is not False)
    if action in ("search", "library_search"):
        return search_library(
            str(body.get("query") or body.get("q") or ""),
            limit=int(body.get("limit") or 80),
            kind=str(body.get("kind") or body.get("facet_kind") or ""),
            dewey=str(body.get("dewey") or body.get("facet_dewey") or ""),
            platform=str(body.get("platform") or body.get("facet_platform") or ""),
        )
    if action in ("resolve", "icon_resolve"):
        return resolve_icon(str(body.get("ref") or body.get("id") or ""))
    return {"ok": False, "error": "unknown_action", "action": action}


# Back-compat alias
def scan_host(**_kwargs: Any) -> dict[str, Any]:
    return build_library()


def icon_path(token: str) -> Path | None:
    row = _find_entry(token)
    if not row or not row.get("icon_path"):
        return None
    p = Path(row["icon_path"])
    return p if p.is_file() and _allowed_icon_path(p) else None


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "json":
        print(json.dumps(library_doc(), ensure_ascii=False))
        return 0
    if cmd in ("scan", "build"):
        print(json.dumps(build_library(), ensure_ascii=False))
        return 0
    if cmd == "dispatch":
        raw = sys.stdin.read()
        body = json.loads(raw) if raw.strip() else {}
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    print(json.dumps(dispatch({"action": cmd}), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())