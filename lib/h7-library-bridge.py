#!/usr/bin/env pythong
"""NEXUS H7 Library — live field-drive catalog, Dewey shelves, search, H7 read/write. No cache."""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
HOSTESS7_ROOT = Path(os.environ.get("HOSTESS7_ROOT", str(INSTALL / "Hostess7")))
HOSTESS7_TEAM_FIELD = Path(os.environ.get("HOSTESS7_TEAM_FIELD", "/media/default/HOSTESS7_TEAM/fieldstorage"))
BOOKS_SRC = INSTALL / "lib" / "field-books"
GITHUB_LIBRARY = INSTALL / "library" / "dewey"
FIELD_BRAIN_DATA = INSTALL / "data" / "field-brain"
DEWEY_MAP = INSTALL / "data" / "dewey-decimal-map.json"
DEWEY_TREE = INSTALL / "data" / "dewey-full-tree.json"
LIBRARY_PROFILES = INSTALL / "data" / "library-profiles.json"
WAR_SEED = INSTALL / "data" / "war-books-seed.json"
PAGE_CHARS = int(os.environ.get("NEXUS_H7_PAGE_CHARS", "3200"))
DEFAULT_PROFILE = os.environ.get("NEXUS_LIBRARY_PROFILE", "hostess7")

BUILTIN_CATALOG: list[dict[str, Any]] = [
    {
        "id": "network-security-field-guide",
        "title": "Network Security — Field Guide",
        "author": "NEXUS-Shield / Hostess7",
        "category": "security",
        "license": "MIT",
        "description": "TCP/IP, DPI, firewalls, false-positive discipline, and operator ethics.",
    },
    {
        "id": "nexus-shield-operator-manual",
        "title": "NEXUS-Shield Operator Manual",
        "author": "Zachary Geurts",
        "category": "program",
        "license": "MIT",
        "description": "Monitor, Inspect, Host Attack, KILL/RE-KILL/NO-KILL, field storage, autokill.",
    },
    {
        "id": "amouranthrtx-field-biography-vol1",
        "title": "AMOURANTHRTX Field Die — Biography Vol. 1",
        "author": "Hostess7 Field Press",
        "category": "biography",
        "license": "Field (AMOURANTHRTX dual-license)",
        "description": "Origins of the Field Die, 94/6 truth filter, and the invisible daemon ethos.",
    },
    {
        "id": "h7-vision-existence-field-guide",
        "title": "H7 Vision & Existence Field Guide",
        "author": "Hostess7 Team / NEXUS-Shield",
        "category": "vision",
        "license": "Field (Hostess7 TEAM drive)",
        "description": "OCR, computer vision, motion tracking, and persistent existence identity.",
    },
]

READER_FONTS = [
    {"id": "georgia", "label": "Georgia", "family": "Georgia, 'Times New Roman', serif"},
    {"id": "palatino", "label": "Palatino", "family": "'Palatino Linotype', Palatino, serif"},
    {"id": "garamond", "label": "Garamond", "family": "Garamond, 'EB Garamond', serif"},
    {"id": "charter", "label": "Charter", "family": "Charter, 'Bitstream Charter', serif"},
    {"id": "iowan", "label": "Iowan", "family": "Iowan Old Style, serif"},
    {"id": "athelas", "label": "Athelas", "family": "Athelas, serif"},
    {"id": "seravek", "label": "Seravek", "family": "Seravek, system-ui, sans-serif"},
    {"id": "menlo", "label": "Menlo", "family": "Menlo, Monaco, 'Courier New', monospace"},
    {"id": "consolas", "label": "Consolas", "family": "Consolas, 'Liberation Mono', monospace"},
    {"id": "opendyslexic", "label": "OpenDyslexic", "family": "OpenDyslexic, sans-serif"},
]

_h7_mod: Any = None
_dewey_doc: dict[str, Any] | None = None
_dewey_tree: dict[str, Any] | None = None
_library_profiles: dict[str, Any] | None = None
_librarian_mod: Any = None
_field_tie_mod: Any = None
_balance_mod: Any = None
_checkout_mod: Any = None


def _field_tie() -> Any:
    global _field_tie_mod
    if _field_tie_mod is not None:
        return _field_tie_mod
    import importlib.util
    spec = importlib.util.spec_from_file_location("h7_field_drive_tie", INSTALL / "lib" / "h7-field-drive-tie.py")
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _field_tie_mod = mod
    return mod


def _balance() -> Any:
    global _balance_mod
    if _balance_mod is not None:
        return _balance_mod
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "field_combinatronic_balance", INSTALL / "lib" / "field-combinatronic-balance.py"
    )
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _balance_mod = mod
    return mod


def _content_balance(
    book_id: str,
    meta: dict[str, Any],
    *,
    read_stats: dict[str, Any] | None = None,
    elapsed_ms: float | None = None,
) -> dict[str, Any]:
    bal = _balance()
    if not bal or not hasattr(bal, "read_content_balance"):
        return {}
    try:
        return bal.read_content_balance(
            book_id,
            fmt=str(meta.get("format", "")),
            collection=str(meta.get("collection", "")),
            read_stats=read_stats,
            elapsed_ms=elapsed_ms,
        )
    except Exception:
        return {}


def _dewey_lib() -> Any:
    import importlib.util
    path = INSTALL / "lib" / "field-dewey-library.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("field_dewey_library", path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _find_h7c_path(book_id: str) -> Path | None:
    dewey = _dewey_lib()
    if dewey and hasattr(dewey, "find_h7c"):
        hit = dewey.find_h7c(book_id)
        if hit:
            return hit
    return None


def _read_content(
    book_id: str,
    meta: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    """Read book text from H7c anywhere in Dewey tree."""
    import time

    dewey = _dewey_lib()
    if dewey and hasattr(dewey, "read_h7c_text"):
        try:
            t0 = time.perf_counter()
            text, header, stats = dewey.read_h7c_text(book_id)
            if text:
                stats = dict(stats or {})
                stats["text_sha256"] = (header or {}).get("text_sha256")
                stats["elapsed_ms"] = stats.get("elapsed_ms") or round((time.perf_counter() - t0) * 1000, 3)
                return text, stats
        except Exception:
            pass

    if dewey and hasattr(dewey, "ensure_h7c_for_book"):
        ensured = dewey.ensure_h7c_for_book(book_id)
        if ensured and ensured.is_file():
            h7c_py = INSTALL / "lib" / "field-h7c-compression.py"
            if h7c_py.is_file():
                try:
                    import importlib.util
                    spec = importlib.util.spec_from_file_location("h7c_read", h7c_py)
                    if spec and spec.loader:
                        mod = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(mod)
                        t0 = time.perf_counter()
                        header, text, stats = mod.decompress_h7c(ensured.read_bytes(), verify=True)
                        stats = dict(stats)
                        stats["text_sha256"] = header.get("text_sha256")
                        stats["elapsed_ms"] = stats.get("elapsed_ms") or round((time.perf_counter() - t0) * 1000, 3)
                        stats["auto_converted"] = True
                        return text, stats
                except Exception:
                    pass

    h7c_path = _find_h7c_path(book_id)
    if h7c_path and h7c_path.is_file():
        h7c_py = INSTALL / "lib" / "field-h7c-compression.py"
        if h7c_py.is_file():
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location("h7c_read", h7c_py)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    t0 = time.perf_counter()
                    header, text, stats = mod.decompress_h7c(h7c_path.read_bytes(), verify=True)
                    stats = dict(stats)
                    stats["text_sha256"] = header.get("text_sha256")
                    stats["elapsed_ms"] = stats.get("elapsed_ms") or round((time.perf_counter() - t0) * 1000, 3)
                    return text, stats
            except Exception:
                pass
    text = _source_text_legacy(book_id)
    return text, {}


def _checkout() -> Any | None:
    global _checkout_mod
    if _checkout_mod is not None:
        return _checkout_mod
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "h7_library_checkout",
        INSTALL / "lib" / "h7-library-checkout.py",
    )
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _checkout_mod = mod
    return mod


def _attach_checkouts(doc: dict[str, Any], books: list[dict[str, Any]]) -> None:
    co = _checkout()
    if not co:
        return
    try:
        co.run_daily_reminders()
        doc["checkout"] = co.posture()
        doc["books"] = co.attach_to_books(books)
    except Exception:
        doc.setdefault("checkout", {"ok": False})


def _librarian() -> Any:
    global _librarian_mod
    if _librarian_mod is not None:
        return _librarian_mod
    import importlib.util
    spec = importlib.util.spec_from_file_location("h7_library_librarian", INSTALL / "lib" / "h7-library-librarian.py")
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _librarian_mod = mod
    return mod


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        import importlib.util
        _p = Path(__file__).resolve().parent / "sovereign-clock.py"
        _s = importlib.util.spec_from_file_location("sovereign_clock", _p)
        if not _s or not _s.loader:
            raise ImportError("sovereign-clock.py missing")
        _SOVEREIGN_CLOCK_MOD = importlib.util.module_from_spec(_s)
        _s.loader.exec_module(_SOVEREIGN_CLOCK_MOD)
    return _SOVEREIGN_CLOCK_MOD.utc_z()


_SOVEREIGN_CLOCK_MOD = None



def _h7_book_module() -> Any:
    global _h7_mod
    if _h7_mod is not None:
        return _h7_mod
    scripts = HOSTESS7_ROOT / "scripts"
    if scripts.is_dir() and str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    try:
        import field_h7_book as mod  # type: ignore
        _h7_mod = mod
        return mod
    except ImportError:
        return None


def _load_dewey() -> dict[str, Any]:
    global _dewey_doc
    if _dewey_doc is not None:
        return _dewey_doc
    for path in (DEWEY_MAP, INSTALL / "data" / "dewey-decimal-map.json"):
        if path.is_file():
            try:
                _dewey_doc = json.loads(path.read_text(encoding="utf-8"))
                return _dewey_doc
            except (OSError, json.JSONDecodeError):
                pass
    _dewey_doc = {"classes": [], "subjects": {}, "keyword_rules": []}
    return _dewey_doc


def _load_dewey_tree() -> dict[str, Any]:
    global _dewey_tree
    if _dewey_tree is not None:
        return _dewey_tree
    for path in (DEWEY_TREE, INSTALL / "data" / "dewey-full-tree.json"):
        if path.is_file():
            try:
                _dewey_tree = json.loads(path.read_text(encoding="utf-8"))
                return _dewey_tree
            except (OSError, json.JSONDecodeError):
                pass
    _dewey_tree = {"classes": [], "subdivisions": {}, "war_shelves": []}
    return _dewey_tree


def _load_library_profiles() -> dict[str, Any]:
    global _library_profiles
    if _library_profiles is not None:
        return _library_profiles
    for path in (LIBRARY_PROFILES, INSTALL / "data" / "library-profiles.json"):
        if path.is_file():
            try:
                _library_profiles = json.loads(path.read_text(encoding="utf-8"))
                return _library_profiles
            except (OSError, json.JSONDecodeError):
                pass
    _library_profiles = {"default_profile": "hostess7", "profiles": {}}
    return _library_profiles


def list_library_profiles() -> list[dict[str, Any]]:
    doc = _load_library_profiles()
    out: list[dict[str, Any]] = []
    for pid, prof in (doc.get("profiles") or {}).items():
        out.append({
            "id": pid,
            "name": prof.get("name", pid),
            "short": prof.get("short", pid),
            "authority": prof.get("authority", ""),
            "description": prof.get("description", ""),
            "dewey_system": prof.get("dewey_system", "DDC23"),
            "github_path": prof.get("github_path", ""),
        })
    return sorted(out, key=lambda x: (x["id"] != doc.get("default_profile", "hostess7"), x["name"]))


def translate_dewey_label(code: str, *, profile_id: str | None = None) -> str:
    pid = profile_id or DEFAULT_PROFILE
    doc = _load_library_profiles()
    prof = (doc.get("profiles") or {}).get(pid) or {}
    overrides = prof.get("label_overrides") or {}
    if code in overrides:
        return str(overrides[code])
    main = re.sub(r"[^0-9].*", "", code)[:3].ljust(3, "0")
    if main in overrides:
        return str(overrides[main])
    tree = _load_dewey_tree()
    for sub in (tree.get("subdivisions") or {}).values():
        for child in sub.get("children") or []:
            if str(child.get("code")) == code:
                return str(child.get("title", code))
        if str(sub.get("code", "")) == code or str(sub.get("code", "")) == main:
            return str(sub.get("title", code))
    dewey = _load_dewey()
    subjects = dewey.get("subjects") or {}
    for row in subjects.values():
        if str(row.get("code")) == code:
            return str(row.get("label", code))
    return _dewey_class_label(code)


def apply_library_profile(books: list[dict[str, Any]], *, profile_id: str | None = None) -> list[dict[str, Any]]:
    pid = profile_id or DEFAULT_PROFILE
    out: list[dict[str, Any]] = []
    for book in books:
        code = str(book.get("dewey", "000"))
        label = translate_dewey_label(code, profile_id=pid)
        out.append({
            **book,
            "dewey_label": label,
            "dewey_label_base": book.get("dewey_label", ""),
            "library_profile": pid,
        })
    return out


def _dewey_class_label(code: str) -> str:
    doc = _load_dewey()
    main = re.sub(r"[^0-9].*", "", code)[:3].ljust(3, "0")
    for cls in doc.get("classes") or []:
        if str(cls.get("code", "")) == main:
            return str(cls.get("title", main))
    return f"Dewey {main}"


def classify_dewey(
    *,
    category: str = "",
    title: str = "",
    subject: str = "",
    author: str = "",
    text_sample: str = "",
) -> dict[str, str]:
    doc = _load_dewey()
    subjects = doc.get("subjects") or {}
    cat = (category or subject or "").lower().strip()
    if cat in subjects:
        row = subjects[cat]
        return {"code": str(row["code"]), "label": str(row.get("label", cat))}

    blob = f"{title} {subject} {author} {text_sample[:4000]}".lower()
    best_code = "000"
    best_score = 0
    for rule in doc.get("keyword_rules") or []:
        code = str(rule.get("code", "000"))
        score = sum(1 for tok in rule.get("tokens") or [] if tok in blob)
        if score > best_score:
            best_score = score
            best_code = code

    label = subjects.get(cat, {}).get("label") if cat else None
    if not label:
        for _k, v in subjects.items():
            if str(v.get("code")) == best_code:
                label = str(v.get("label", best_code))
                break
    return {"code": best_code, "label": label or _dewey_class_label(best_code)}


def _field_roots() -> list[Path]:
    roots: list[Path] = []
    for p in (
        HOSTESS7_TEAM_FIELD,
        HOSTESS7_ROOT / "cache" / "fieldstorage",
        STATE / "field-storage",
    ):
        if p.is_dir() and p not in roots:
            roots.append(p)
    return roots


def _textbook_roots() -> list[Path]:
    out: list[Path] = []
    for root in _field_roots():
        for sub in ("textbooks", "textbooks/dewey"):
            p = root / sub if sub == "textbooks" else root / "textbooks" / "dewey"
            if p.is_dir() and p not in out:
                out.append(root / "textbooks")
    return out or [HOSTESS7_TEAM_FIELD / "textbooks"]


def _brain_score(root: Path) -> int:
    score = 0
    if (root / "brain").is_dir():
        score += 5
    if (root / "brain/library/manifest.json").is_file():
        score += 80
    if (root / "brain/superintel").is_dir():
        score += 50
    return score


def _primary_field_root() -> Path:
    best: Path | None = None
    best_score = -1
    for root in _field_roots():
        s = _brain_score(root)
        if s > best_score:
            best_score = s
            best = root
    return best or HOSTESS7_TEAM_FIELD


def _dewey_dir(dewey_code: str, *, root: Path | None = None) -> Path:
    base = (root or _primary_field_root()) / "textbooks" / "dewey"
    main = re.sub(r"[^0-9].*", "", dewey_code)[:3].ljust(3, "0")
    return base / main


def _library_shelf_dir(dewey_code: str) -> Path:
    """Resolve Dewey shelf under library/dewey — glob tree, room for every book ever."""
    code = re.sub(r"[^\d.]", "", str(dewey_code or "000")).strip() or "000"
    root = GITHUB_LIBRARY
    root.mkdir(parents=True, exist_ok=True)
    tree = _load_dewey_tree()
    best_slug = ""
    best_len = -1
    for subdiv in (tree.get("subdivisions") or {}).values():
        sc = str(subdiv.get("code", ""))
        slug = str(subdiv.get("slug") or "")
        if slug and code.startswith(sc) and len(sc) > best_len and (root / slug).is_dir():
            best_slug = slug
            best_len = len(sc)
    if best_slug:
        return root / best_slug
    main = code.split(".")[0][:3].ljust(3, "0")
    candidates: list[str] = []
    if main in ("004", "005"):
        candidates.append("004-computers")
    for cls in tree.get("classes") or []:
        if str(cls.get("code")) == main:
            candidates.append(str(cls.get("slug") or ""))
    candidates.extend([
        f"{main}-computers",
        f"{main}-education",
        f"{main}-science",
        f"{main}-mathematics",
        f"{main}-history",
        main,
    ])
    for slug in candidates:
        if slug and (root / slug).is_dir():
            return root / slug
    for shelf in sorted(root.iterdir()):
        if shelf.is_dir() and shelf.name.startswith(main):
            return shelf
    slug = next((s for s in candidates if s), f"{main}-shelf")
    return root / slug


def _safe_id(book_id: str) -> str:
    return re.sub(r"[^\w.-]", "_", book_id)


def _vision_corpus_text() -> str:
    for root in (
        HOSTESS7_TEAM_FIELD / "brain" / "vision" / "corpus.json",
        HOSTESS7_ROOT / "cache" / "fieldstorage" / "brain" / "vision" / "corpus.json",
    ):
        if not root.is_file():
            continue
        try:
            doc = json.loads(root.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        lines = [
            "H7 Vision & Existence Field Guide",
            "Source: Hostess7 TEAM drive — brain/vision/corpus.json",
            "",
        ]
        for dom in doc.get("domains") or []:
            if not isinstance(dom, dict):
                continue
            lines.append(f"## {dom.get('title') or dom.get('id')}")
            lines.append(str(dom.get("body") or ""))
            lines.append("")
        return "\n".join(lines)
    return ""


def _iter_h7c_files() -> list[Path]:
    dewey = _dewey_lib()
    if dewey and hasattr(dewey, "glob_h7c_files"):
        return dewey.glob_h7c_files()
    if not GITHUB_LIBRARY.is_dir():
        return []
    return sorted(GITHUB_LIBRARY.rglob("*.h7c"))


def _h7c_meta(path: Path) -> dict[str, Any] | None:
    dewey = _dewey_lib()
    if dewey and hasattr(dewey, "h7c_meta"):
        return dewey.h7c_meta(path)
    return None


def _glob_dewey_books() -> list[dict[str, Any]]:
    dewey = _dewey_lib()
    if dewey and hasattr(dewey, "glob_books"):
        try:
            return dewey.glob_books()
        except Exception:
            pass
    return []


def _iter_h7_files() -> list[Path]:
    seen: set[str] = set()
    paths: list[Path] = []
    dewey_mod = _dewey_lib()
    for tb in _textbook_roots():
        for pattern in ("**/*.h7", "*.h7"):
            for path in sorted(tb.glob(pattern)):
                key = str(path.resolve())
                if key in seen:
                    continue
                seen.add(key)
                if dewey_mod and hasattr(dewey_mod, "ensure_h7c_path"):
                    h7c = dewey_mod.ensure_h7c_path(path)
                    if h7c.suffix.lower() == ".h7c" and h7c.is_file():
                        key2 = str(h7c.resolve())
                        if key2 not in seen:
                            seen.add(key2)
                            paths.append(h7c)
                    continue
                paths.append(path)
        dewey = tb / "dewey"
        if dewey.is_dir():
            for path in sorted(dewey.glob("**/*.h7")):
                key = str(path.resolve())
                if key in seen:
                    continue
                seen.add(key)
                if dewey_mod and hasattr(dewey_mod, "ensure_h7c_path"):
                    h7c = dewey_mod.ensure_h7c_path(path)
                    if h7c.suffix.lower() == ".h7c" and h7c.is_file():
                        key2 = str(h7c.resolve())
                        if key2 not in seen:
                            seen.add(key2)
                            paths.append(h7c)
                    continue
                paths.append(path)
    return paths


def _h7_meta(path: Path) -> dict[str, Any] | None:
    dewey = _dewey_lib()
    if dewey and hasattr(dewey, "ensure_h7c_path") and path.suffix.lower() == ".h7":
        h7c_path = dewey.ensure_h7c_path(path)
        if h7c_path.suffix.lower() == ".h7c":
            row = _h7c_meta(h7c_path)
            if row:
                return row
    mod = _h7_book_module()
    if not mod:
        return None
    try:
        header, _ = mod.unpack_h7(path.read_bytes(), verify=False)
        dewey = classify_dewey(
            category=str(header.get("subject", header.get("category", ""))),
            title=str(header.get("title", path.stem)),
            subject=str(header.get("subject", "")),
            author=str(header.get("author", "")),
        )
        if header.get("dewey"):
            dewey = {"code": str(header["dewey"]), "label": str(header.get("dewey_label", ""))}
        return {
            "id": str(header.get("id", path.stem)),
            "title": str(header.get("title", path.stem)),
            "author": str(header.get("author", "")),
            "category": str(header.get("subject", header.get("category", ""))),
            "license": str(header.get("license", "Field")),
            "description": str(header.get("full_name", header.get("title", ""))),
            "char_count": int(header.get("char_count", 0)),
            "line_count": int(header.get("line_count", 0)),
            "file_bytes": path.stat().st_size,
            "format": "H7",
            "path": str(path),
            "dewey": dewey["code"],
            "dewey_label": dewey["label"],
            "ready": True,
        }
    except (OSError, ValueError):
        return None


def _txt_meta(path: Path, book: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        text = ""
    bid = path.stem
    meta = book or {}
    dewey = classify_dewey(
        category=str(meta.get("category", "")),
        title=str(meta.get("title", bid)),
        subject=str(meta.get("subject", meta.get("category", ""))),
        author=str(meta.get("author", "")),
        text_sample=text[:2000],
    )
    pages = _paginate(text)
    return {
        "id": bid,
        "title": str(meta.get("title", bid.replace("-", " ").title())),
        "author": str(meta.get("author", "")),
        "category": str(meta.get("category", "")),
        "license": str(meta.get("license", "Field")),
        "description": str(meta.get("description", "")),
        "char_count": len(text),
        "page_count": len(pages),
        "format": "field-txt",
        "path": str(path),
        "dewey": dewey["code"],
        "dewey_label": dewey["label"],
        "ready": len(text) > 200,
    }


def _enrich_books(books: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lib = _librarian()
    if not lib:
        return books
    return [lib.merge_into_book(b) for b in books]


def _war_seed_entries() -> list[dict[str, Any]]:
    lib = _librarian()
    rows: list[dict[str, Any]] = []
    for path in (WAR_SEED, INSTALL / "data" / "war-books-seed.json"):
        if not path.is_file():
            continue
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for seed in doc.get("books") or []:
            bid = str(seed.get("id", ""))
            if not bid:
                continue
            row = {
                "id": bid,
                "title": seed.get("title", bid),
                "author": seed.get("author", ""),
                "category": seed.get("subject", "military"),
                "license": seed.get("license", "Public Domain"),
                "description": seed.get("study_note", ""),
                "dewey": seed.get("dewey", "355"),
                "dewey_label": translate_dewey_label(str(seed.get("dewey", "355"))),
                "study_note": seed.get("study_note", ""),
                "gutenberg_id": seed.get("gutenberg_id", ""),
                "fetch_url": seed.get("fetch_url", ""),
                "ready": False,
                "format": "catalog-seed",
                "war_shelf": True,
            }
            if lib:
                row = lib.merge_into_book(row)
            on_disk = bool(row.get("path")) or bool(_source_text(bid))
            if on_disk:
                row["ready"] = True
                row["format"] = "H7"
                rows.append(row)
        break
    return rows


def _library_only(books: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tie = _field_tie()
    if not tie:
        return [b for b in books if b.get("ready") and str(b.get("format", "")) not in ("catalog-seed", "staging-txt", "catalog-entry")]
    return [b for b in books if tie.is_library_book(b)]


def _registry_entries() -> list[dict[str, Any]]:
    """Unified library registry — devices, games, textbooks, file formats, all collections."""
    path = INSTALL / "lib" / "field-library-registry.py"
    if not path.is_file():
        return _extensive_library_entries()
    import importlib.util

    spec = importlib.util.spec_from_file_location("field_library_registry", path)
    if not spec or not spec.loader:
        return _extensive_library_entries()
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    try:
        rows = mod.registry_entries()
    except Exception:
        return _extensive_library_entries()
    out: list[dict[str, Any]] = []
    for row in rows:
        bid = str(row.get("id", ""))
        if not bid:
            continue
        dewey = row.get("dewey", "004")
        fmt = row.get("format") or "h7c"
        out.append({
            **row,
            "ready": row.get("ready", True),
            "format": fmt,
            "dewey": dewey,
            "dewey_label": translate_dewey_label(str(dewey)),
            "source": row.get("source", "field-library-registry"),
        })
    return out


def _extensive_library_entries() -> list[dict[str, Any]]:
    """Legacy catalog hook — delegates to field-library-registry when available."""
    path = INSTALL / "lib" / "field-extensive-library.py"
    if not path.is_file():
        return []
    import importlib.util

    spec = importlib.util.spec_from_file_location("field_extensive_library", path)
    if not spec or not spec.loader:
        return []
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    try:
        rows = mod.catalog_for_h7_bridge()
    except Exception:
        return []
    out: list[dict[str, Any]] = []
    for row in rows:
        bid = str(row.get("id", ""))
        if not bid:
            continue
        dewey = row.get("dewey", "004")
        out.append({
            **row,
            "ready": True,
            "format": row.get("format", "h7c"),
            "dewey": dewey,
            "dewey_label": translate_dewey_label(str(dewey)),
            "source": row.get("source", "field-extensive-library"),
        })
    return out


def _scan_github_library() -> list[dict[str, Any]]:
    """Zero-cost catalog from GitHub tree library/dewey/**/book.json (shipped with NEXUS-Shield)."""
    if not GITHUB_LIBRARY.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    for book_json in sorted(GITHUB_LIBRARY.glob("**/book.json")):
        try:
            row = json.loads(book_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(row, dict):
            continue
        bid = str(row.get("id") or book_json.parent.name)
        row["id"] = bid
        row.setdefault("format", "github-catalog")
        row["ready"] = True
        row["source"] = "github"
        row["github_path"] = str(book_json.relative_to(INSTALL))
        row.setdefault("dewey_label", translate_dewey_label(str(row.get("dewey", ""))))
        text = _source_text(bid)
        if text and len(text) > 200:
            meta = _txt_meta_from_text(bid, row, text)
            row.update(meta)
            row["ready"] = True
        rows.append(row)
    return rows


def _github_brain_manifest() -> dict[str, Any]:
    """Field brain manifests committed under data/field-brain/ on GitHub."""
    out: dict[str, Any] = {"source": "github", "files": []}
    if not FIELD_BRAIN_DATA.is_dir():
        return out
    for name in ("manifest.json", "context.json", "field_fingerprint.json", "index.json", "superintel.json"):
        fp = FIELD_BRAIN_DATA / name
        if not fp.is_file():
            continue
        try:
            doc = json.loads(fp.read_text(encoding="utf-8"))
            out["files"].append(name)
            if name == "manifest.json" and isinstance(doc, dict):
                out["manifest"] = doc
                out["catalog_count"] = doc.get("catalog_count") or len(doc.get("books") or [])
            if name == "context.json" and isinstance(doc, dict):
                out["superintel_context"] = doc
        except (OSError, json.JSONDecodeError):
            continue
    return out


def _scan_books() -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}

    for book in BUILTIN_CATALOG:
        bid = book["id"]
        text = _source_text(bid)
        row = {**book, **_txt_meta_from_text(bid, book, text)}
        by_id[bid] = row

    iron = _ironclad_h7_access()
    if iron and hasattr(iron, "catalog_entries"):
        try:
            for row in iron.catalog_entries():
                bid = str(row.get("id") or "")
                if not bid:
                    continue
                prev = by_id.get(bid) or {}
                merged = {**prev, **row, "format": row.get("format") or "h7c", "ready": bool(row.get("ready", True))}
                if row.get("h7c_path"):
                    merged["path"] = row["h7c_path"]
                elif row.get("h7c"):
                    merged["path"] = str(INSTALL / str(row["h7c"])) if not str(row["h7c"]).startswith("/") else row["h7c"]
                by_id[bid] = merged
        except Exception:
            iron = None

    if not iron:
        for row in _glob_dewey_books():
            bid = str(row.get("id") or "")
            if not bid:
                continue
            prev = by_id.get(bid) or {}
            merged = {**prev, **row, "format": row.get("format") or "h7c", "ready": True}
            if row.get("h7c"):
                merged["path"] = str(INSTALL / str(row["h7c"])) if not str(row["h7c"]).startswith("/") else row["h7c"]
            by_id[bid] = merged

        for path in _iter_h7c_files():
            row = _h7c_meta(path)
            if not row:
                continue
            bid = row["id"]
            if bid not in by_id or row.get("char_count", 0) > by_id[bid].get("char_count", 0):
                row["page_count"] = max(1, row.get("char_count", 0) // PAGE_CHARS)
                by_id[bid] = row

    for base in (BOOKS_SRC, STATE / "field-books"):
        if not base.is_dir():
            continue
        for path in sorted(base.glob("*.txt")):
            bid = path.stem
            if bid in by_id and by_id[bid].get("format") == "H7":
                continue
            builtin = next((b for b in BUILTIN_CATALOG if b["id"] == bid), None)
            by_id.setdefault(bid, _txt_meta(path, builtin))

    for tb in _textbook_roots():
        for path in sorted(tb.glob("*.txt")):
            bid = path.stem
            if bid in by_id:
                continue
            by_id[bid] = _txt_meta(path)

    for row in _war_seed_entries():
        bid = row["id"]
        if bid not in by_id:
            by_id[bid] = row
        else:
            merged = {**by_id[bid], **{k: v for k, v in row.items() if v}}
            merged["ready"] = True
            by_id[bid] = merged

    for row in _scan_github_library():
        bid = row["id"]
        prev = by_id.get(bid) or {}
        merged = {**prev, **row}
        if prev.get("char_count", 0) > row.get("char_count", 0):
            merged["char_count"] = prev["char_count"]
            merged["page_count"] = prev.get("page_count", merged.get("page_count"))
            merged["format"] = prev.get("format", merged.get("format"))
        by_id[bid] = merged

    for row in _registry_entries():
        bid = row["id"]
        prev = by_id.get(bid) or {}
        merged = {**prev, **row}
        if row.get("cover") and not merged.get("cover"):
            merged["cover"] = row["cover"]
        by_id[bid] = merged

    tie = _field_tie()
    if tie:
        on_disk_ids = set(by_id.keys())
        tied = tie.tie_field_drive(classify_dewey=classify_dewey, on_disk_ids=on_disk_ids)
        for row in tied.get("corpus_books") or []:
            bid = row["id"]
            by_id[bid] = {**by_id.get(bid, {}), **row}

    books = _library_only(_enrich_books(list(by_id.values())))
    for book in books:
        if book.get("dewey"):
            book["dewey_label"] = translate_dewey_label(str(book["dewey"]))
    return books


def _txt_meta_from_text(bid: str, book: dict[str, Any], text: str) -> dict[str, Any]:
    dewey = classify_dewey(
        category=str(book.get("category", "")),
        title=str(book.get("title", bid)),
        author=str(book.get("author", "")),
        text_sample=text[:2000],
    )
    pages = _paginate(text)
    return {
        "char_count": len(text),
        "page_count": len(pages),
        "format": "field-txt",
        "dewey": dewey["code"],
        "dewey_label": dewey["label"],
        "ready": len(text) > 200,
    }


def _source_text_legacy(book_id: str) -> str:
    if book_id == "h7-vision-existence-field-guide":
        text = _vision_corpus_text()
        if text:
            return text

    tie = _field_tie()
    if tie:
        tied_text = tie.source_text_for_id(book_id)
        if tied_text:
            return tied_text

    for base in (BOOKS_SRC, STATE / "field-books"):
        path = base / f"{book_id}.txt"
        if path.is_file():
            return path.read_text(encoding="utf-8", errors="replace")

    for tb in _textbook_roots():
        for path in (tb / f"{book_id}.txt", tb / "dewey" / "**" / f"{book_id}.txt"):
            if "*" in str(path):
                for hit in tb.glob("dewey/**/*.txt"):
                    if hit.stem == book_id:
                        return hit.read_text(encoding="utf-8", errors="replace")
            elif path.is_file():
                return path.read_text(encoding="utf-8", errors="replace")
    return ""


def _source_text(book_id: str) -> str:
    text, _ = _read_content(book_id, {"format": "h7c"})
    return text


def _paginate(text: str, *, page_chars: int | None = None) -> list[str]:
    limit = page_chars or PAGE_CHARS
    text = text.replace("\r\n", "\n").strip()
    if not text:
        return [""]
    pages: list[str] = []
    start = 0
    while start < len(text):
        chunk = text[start : start + limit]
        if start + limit < len(text):
            brk = max(chunk.rfind("\n\n"), chunk.rfind("\n"), chunk.rfind(". "))
            if brk > limit // 3:
                chunk = chunk[: brk + 1]
        pages.append(chunk.strip())
        start += max(len(chunk), 1)
    return pages or [""]


def _search_blob(book: dict[str, Any]) -> str:
    parts = [
        book.get("title", ""),
        book.get("author", ""),
        book.get("category", ""),
        book.get("dewey", ""),
        book.get("dewey_label", ""),
        book.get("description", ""),
        book.get("ein", ""),
        book.get("isbn_13", ""),
        book.get("isbn_10", ""),
    ]
    if book.get("ready") and book.get("char_count", 0) < 12000:
        parts.append(_source_text(str(book.get("id", "")))[:8000])
    return " ".join(str(p) for p in parts).lower()


def _atlas_mod() -> Any:
    import importlib.util
    path = INSTALL / "lib" / "h7-library-atlas.py"
    if not path.is_file():
        path = Path(__file__).resolve().parent / "h7-library-atlas.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("h7_library_atlas", path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _ironclad_h7_access() -> Any | None:
    import importlib.util
    path = INSTALL / "lib" / "ironclad-h7-access.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("ironclad_h7_access_bridge", path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def search_books(query: str, *, limit: int = 24) -> list[dict[str, Any]]:
    iron = _ironclad_h7_access()
    if iron and hasattr(iron, "search_books"):
        try:
            hits = iron.search_books(query, limit=limit)
            if hits:
                return hits
        except Exception:
            pass
    toks = [t for t in re.split(r"\W+", query.lower()) if len(t) > 1]
    if not toks:
        return []
    scored: list[tuple[int, dict[str, Any]]] = []
    for book in _scan_books():
        blob = _search_blob(book)
        blob += " " + " ".join(str(x) for x in (book.get("summary", ""), book.get("for_humans", "")))
        blob += " " + " ".join(book.get("topics") or [])
        score = 0
        for t in toks:
            if t in str(book.get("id", "")).lower():
                score += 12
            if t in str(book.get("title", "")).lower():
                score += 10
            if t in str(book.get("author", "")).lower():
                score += 6
            if t in str(book.get("dewey", "")):
                score += 8
            if t in (book.get("topics") or []):
                score += 9
            if t in blob:
                score += 4
        if score > 0:
            scored.append((score, book))
    scored.sort(key=lambda x: (-x[0], x[1].get("title", "")))
    return [{**b, "score": s} for s, b in scored[:limit]]


def search_library(query: str, *, limit: int = 24) -> dict[str, Any]:
    card_cat = None
    try:
        spec = importlib.util.spec_from_file_location(
            "field_card_catalog",
            INSTALL / "lib" / "field-card-catalog.py",
        )
        if spec and spec.loader:
            card_cat = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(card_cat)
    except Exception:
        card_cat = None
    if card_cat and hasattr(card_cat, "search_cards"):
        try:
            hits = card_cat.search_cards(query, limit=limit)
            cards = hits.get("hits") or []
            books = [
                {
                    "id": c.get("id"),
                    "title": c.get("title"),
                    "author": c.get("author"),
                    "dewey": c.get("dewey") or c.get("call_number"),
                    "card_id": c.get("card_id"),
                    "keywords": c.get("keywords"),
                    "shelf": c.get("shelf"),
                    "format": c.get("format"),
                    "score": c.get("score"),
                    "source": "field-card-catalog",
                }
                for c in cards
            ]
            if books or query.strip():
                return {
                    "ok": True,
                    "query": query,
                    "books": books,
                    "passages": [],
                    "topics": [],
                    "catalog": "field-card-catalog",
                    "catalog_hits": hits.get("count", len(books)),
                }
        except Exception:
            pass
    atlas = _atlas_mod()
    if atlas:
        return atlas.search_unified(query, _scan_books(), book_search_fn=search_books, limit=limit)
    return {"ok": True, "query": query, "books": search_books(query, limit=limit), "passages": [], "topics": []}


def dewey_shelves(*, profile_id: str | None = None) -> list[dict[str, Any]]:
    doc = _load_dewey()
    books = apply_library_profile(_library_only(_scan_books()), profile_id=profile_id)
    buckets: dict[str, list[dict[str, Any]]] = {str(c["code"]): [] for c in doc.get("classes") or []}
    for book in books:
        code = re.sub(r"[^0-9].*", "", str(book.get("dewey", "000")))[:3].ljust(3, "0")
        buckets.setdefault(code, []).append(book)
    shelves = []
    for cls in doc.get("classes") or []:
        code = str(cls["code"])
        shelf_books = sorted(buckets.get(code, []), key=lambda b: str(b.get("title", "")))
        shelves.append({
            "code": code,
            "title": translate_dewey_label(code, profile_id=profile_id) or cls.get("title", code),
            "title_base": cls.get("title", code),
            "count": len(shelf_books),
            "books": shelf_books,
        })
    return shelves


def war_shelves(*, profile_id: str | None = None) -> list[dict[str, Any]]:
    tree = _load_dewey_tree()
    books = apply_library_profile(_library_only(_scan_books()), profile_id=profile_id)
    war_ids = {str(b.get("id")) for b in books if b.get("war_shelf")}
    lib = _librarian()
    if lib:
        war_study = lib.ascertain_war_books(write=False)
        for row in war_study.get("books") or []:
            war_ids.add(str(row.get("id", "")))

    buckets: dict[str, list[dict[str, Any]]] = {}
    for book in books:
        bid = str(book.get("id", ""))
        code = str(book.get("dewey", ""))
        blob = f"{book.get('title', '')} {book.get('subject', '')} {book.get('category', '')}".lower()
        is_war = (
            book.get("war_shelf")
            or bid in war_ids
            or code.startswith("355")
            or code.startswith("940.5")
            or code.startswith("973.7")
            or any(k in blob for k in ("war", "military", "battle", "civil war"))
        )
        if not is_war:
            continue
        for shelf_def in tree.get("war_shelves") or []:
            sc = str(shelf_def["code"])
            if code == sc or code.startswith(sc + ".") or (sc == "355" and code.startswith("355")):
                buckets.setdefault(sc, []).append(book)
                break
        else:
            main = re.sub(r"[^0-9].*", "", code)[:3]
            if main in ("355", "940", "973"):
                buckets.setdefault(main, []).append(book)

    out: list[dict[str, Any]] = []
    for shelf_def in tree.get("war_shelves") or []:
        sc = str(shelf_def["code"])
        shelf_books = sorted(buckets.get(sc, []), key=lambda b: str(b.get("title", "")))
        if not shelf_books:
            continue
        out.append({
            "code": sc,
            "title": translate_dewey_label(sc, profile_id=profile_id) or shelf_def.get("title", sc),
            "icon": shelf_def.get("icon", "⚔"),
            "count": len(shelf_books),
            "books": shelf_books,
            "war_shelf": True,
        })
    return out


def _attach_book_knowledge(doc: dict[str, Any], books: list[dict[str, Any]]) -> None:
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "h7_secure_reader",
            INSTALL / "lib" / "h7-library-secure-reader.py",
        )
        if spec and spec.loader:
            reader_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(reader_mod)
            sync = reader_mod.sync_book_knowledge(books)
            doc["book_knowledge"] = {
                "book_count": sync.get("book_count", 0),
                "path": sync.get("path"),
            }
            return
    except Exception:
        pass
    doc["book_knowledge"] = {"book_count": len(books)}


def _aml_test_fast_catalog(profile_id: str) -> dict[str, Any] | None:
    if os.environ.get("AML_TEST_DIRECT", "0") != "1" and os.environ.get("AML_INLINE", "0") != "1":
        return None
    books = list(BUILTIN_CATALOG)
    return {
        "updated": _now(),
        "library_version": 5,
        "test_fast": True,
        "unchanged": True,
        "motto": "Read like a person. Retrieve like a model. — Hostess7 Library Atlas",
        "book_count": len(books),
        "ready_count": len(books),
        "library_profile": profile_id,
        "books": books,
        "shelves": [],
        "war_shelves": [],
        "atlas": {"schema": "h7-library-atlas/v1", "passage_count": 0},
        "librarian": {"corps": {"clara_catalog": True}},
    }


def build_catalog(*, force: bool = False, profile_id: str | None = None) -> dict[str, Any]:
    pid = profile_id or DEFAULT_PROFILE
    fast = _aml_test_fast_catalog(pid)
    if fast is not None and not force:
        return fast
    lib = _librarian()
    fp_doc: dict[str, Any] = {}
    if lib:
        fp_doc = lib.load_fingerprint_doc()
        if not force and lib.field_unchanged():
            snap = lib.load_catalog_snapshot()
            if snap:
                snap["unchanged"] = True
                snap["field_fingerprint"] = fp_doc.get("fingerprint", lib.compute_field_fingerprint())
                snap["last_touched"] = fp_doc.get("last_touched", "")
                snap["last_touched_same"] = lib.last_touched_unchanged()
                snap["librarian"] = lib.librarian_status()
                snap["library_profile"] = pid
                snap["books"] = apply_library_profile(snap.get("books") or [], profile_id=pid)
                snap["shelves"] = dewey_shelves(profile_id=pid)
                snap["war_shelves"] = war_shelves(profile_id=pid)
                _attach_book_knowledge(snap, snap.get("books") or [])
                snap["librarian_corps"] = (lib.librarian_status().get("corps") if lib else {}) or {}
                _attach_checkouts(snap, snap.get("books") or [])
                return snap

    if lib:
        lib.ascertain_war_books(write=force or not lib.field_unchanged())

    tie = _field_tie()
    if tie and force:
        tie.organize_h7_to_dewey(classify_fn=classify_dewey)

    raw_books = _scan_books()
    atlas_mod = _atlas_mod()
    atlas_doc: dict[str, Any] = {}
    if atlas_mod:
        atlas_doc = atlas_mod.build_atlas(raw_books, text_for_id=_source_text, force=force)
        raw_books = atlas_mod.apply_atlas_to_books(raw_books, atlas_doc)

    books = apply_library_profile(raw_books, profile_id=pid)
    if lib and (force or not lib.field_unchanged()):
        lib.build_bibliography_field(write=True)

    prof_doc = _load_library_profiles()
    active = (prof_doc.get("profiles") or {}).get(pid) or {}

    doc = {
        "updated": _now(),
        "library_version": 5,
        "page_chars": PAGE_CHARS,
        "motto": "Read like a person. Retrieve like a model. — Hostess7 Library Atlas",
        "field_root": str(_primary_field_root()),
        "field_fingerprint": lib.compute_field_fingerprint() if lib else "",
        "unchanged": False,
        "last_touched": fp_doc.get("last_touched", "") if lib else "",
        "last_touched_same": lib.last_touched_unchanged() if lib else True,
        "fingerprint_method": "micro_sig_v1",
        "book_count": len(books),
        "ready_count": sum(1 for b in books if b.get("ready")),
        "war_book_count": sum(s.get("count", 0) for s in war_shelves(profile_id=pid)),
        "dewey_classes": _load_dewey().get("classes", []),
        "dewey_tree": _load_dewey_tree().get("war_shelves", []),
        "library_profile": pid,
        "library_profile_name": active.get("name", pid),
        "library_profiles": list_library_profiles(),
        "profile_translation": prof_doc.get("translation_help", ""),
        "github_library": "library/dewey/",
        "github_library_books": len(_scan_github_library()),
        "github_field_brain": _github_brain_manifest(),
        "field_drive": {
            **(tie.field_drive_inventory() if (tie := _field_tie()) else {}),
            **({"tracking": tie.tracking_lists(on_disk_ids={b["id"] for b in books})} if tie else {}),
        },
        "fonts": READER_FONTS,
        "books": books,
        "shelves": dewey_shelves(profile_id=pid),
        "war_shelves": war_shelves(profile_id=pid),
        "librarian": lib.librarian_status() if lib else {},
        "atlas": {
            "schema": atlas_doc.get("schema", ""),
            "path": str(atlas_mod.atlas_dir() / "atlas.json") if atlas_mod else "",
            "passage_count": atlas_doc.get("passage_count", 0),
            "topic_count": atlas_doc.get("topic_count", 0),
            "collection_count": atlas_doc.get("collection_count", 0),
        },
        "collections": atlas_doc.get("collections", []),
        "topics": atlas_doc.get("topics", []),
        "human": atlas_doc.get("human", {}),
        "ai": atlas_doc.get("ai", {}),
    }
    if lib:
        lib.save_fingerprint(catalog=doc)
        lib.librarian_corps_learn(
            "catalog_build",
            detail=f"book_count={len(books)} shelves={len(doc.get('shelves') or [])}",
        )
    doc["librarian_corps"] = (lib.librarian_status().get("corps") if lib else {}) or {}
    _attach_book_knowledge(doc, books)
    _attach_checkouts(doc, doc.get("books") or books)
    return doc


def read_page(book_id: str, page: int, *, page_chars: int | None = None) -> dict[str, Any]:
    books = _scan_books()
    meta = next((b for b in books if b["id"] == book_id), None)
    if not meta:
        meta = next((b for b in BUILTIN_CATALOG if b["id"] == book_id), None)
    if not meta:
        return {"ok": False, "error": "unknown_book"}

    import time
    t0 = time.perf_counter()
    text, read_stats = _read_content(book_id, meta)
    if not text:
        return {"ok": False, "error": "empty_book", "book": meta}

    pages = _paginate(text, page_chars=page_chars)
    page = max(1, min(page, len(pages)))
    lib = _librarian()
    librarian: dict[str, Any] = {}
    if lib:
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "nexus_librarian_corps",
                INSTALL / "lib" / "nexus-librarian-corps.py",
            )
            if spec and spec.loader:
                corps = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(corps)
                route = corps.dispense_route(
                    book_id=book_id,
                    dewey=str(meta.get("dewey", "")),
                    page=page,
                )
                librarian = route.get("librarian") or {}
        except Exception:
            pass
    cb = _content_balance(
        book_id,
        meta,
        read_stats=read_stats,
        elapsed_ms=round((time.perf_counter() - t0) * 1000, 3),
    )
    return {
        "ok": True,
        "book": meta,
        "page": page,
        "page_count": len(pages),
        "text": pages[page - 1],
        "char_count": len(text),
        "has_prev": page > 1,
        "has_next": page < len(pages),
        "format": meta.get("format", "field-txt"),
        "librarian": librarian,
        "combinatronic_balance": cb,
        "balance_id": cb.get("balance_id"),
        "best_identifier": cb.get("best_identifier"),
        "precise_file": cb.get("precise_file"),
        "no_cost": cb.get("no_cost"),
    }


def read_full(book_id: str) -> dict[str, Any]:
    books = _scan_books()
    meta = next((b for b in books if b["id"] == book_id), None)
    if not meta:
        return {"ok": False, "error": "unknown_book"}
    import time
    t0 = time.perf_counter()
    text, read_stats = _read_content(book_id, meta)
    if not text:
        return {"ok": False, "error": "empty_book", "book": meta}
    cb = _content_balance(
        book_id,
        meta,
        read_stats=read_stats,
        elapsed_ms=round((time.perf_counter() - t0) * 1000, 3),
    )
    figures: dict[str, Any] = {}
    figure_ids: list[str] = []
    if isinstance(read_stats, dict):
        raw_figs = read_stats.get("_figures_raw") or {}
        if raw_figs:
            import base64
            for fid, spec in raw_figs.items():
                data = spec.get("data") or b""
                mime = spec.get("mime") or "image/png"
                figures[fid] = {
                    "id": fid,
                    "mime": mime,
                    "alt": spec.get("alt") or fid,
                    "data_url": f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}" if data else "",
                }
            figure_ids = sorted(figures.keys())
    return {
        "ok": True,
        "book": meta,
        "text": text,
        "char_count": len(text),
        "figures": figures,
        "figure_ids": figure_ids,
        "combinatronic_balance": cb,
        "balance_id": cb.get("balance_id"),
        "best_identifier": cb.get("best_identifier"),
        "precise_file": cb.get("precise_file"),
        "no_cost": cb.get("no_cost"),
    }


def _h7c_module() -> Any:
    import importlib.util
    path = INSTALL / "lib" / "field-h7c-compression.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("field_h7c_compression", path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def write_h7_book(
    book_id: str,
    text: str,
    meta: dict[str, Any],
    *,
    dewey_code: str | None = None,
) -> dict[str, Any]:
    h7c_mod = _h7c_module()
    if not h7c_mod:
        return {"ok": False, "error": "h7c_module_missing"}

    dewey = classify_dewey(
        category=str(meta.get("category", meta.get("subject", ""))),
        title=str(meta.get("title", book_id)),
        subject=str(meta.get("subject", "")),
        author=str(meta.get("author", "")),
        text_sample=text[:3000],
    )
    code = dewey_code or dewey["code"]
    dest_dir = _library_shelf_dir(code)
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe = _safe_id(book_id)
    book_subdir = dest_dir / safe
    book_subdir.mkdir(parents=True, exist_ok=True)
    path = book_subdir / f"{safe}.h7c"
    pack_meta = {
        "id": book_id,
        "title": meta.get("title", book_id),
        "author": meta.get("author", ""),
        "license": meta.get("license", "Field"),
        "subject": meta.get("category", meta.get("subject", "")),
        "category": str(meta.get("category", meta.get("subject", ""))),
        "dewey": code,
        "dewey_label": dewey["label"],
        "uploaded": _now(),
        "reader": "NEXUS_H7C",
    }
    packed = h7c_mod.pack_h7c(text, pack_meta, use_optimizer=True, format_version=2)
    path.write_bytes(packed)
    book_doc = {
        "id": book_id,
        "title": pack_meta["title"],
        "author": pack_meta["author"],
        "dewey": code,
        "dewey_label": dewey["label"],
        "format": "h7c",
        "h7c": str(path.relative_to(INSTALL)) if path.is_relative_to(INSTALL) else str(path),
        "h7": None,
        "cover": meta.get("cover"),
        "updated": _now(),
    }
    (book_subdir / "book.json").write_text(
        json.dumps(book_doc, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    lib = _librarian()
    if lib:
        lib.touch_book(book_id, dewey=code, title=str(meta.get("title", book_id)))
        lib.librarian_corps_learn(
            "upload",
            book_id=book_id,
            dewey=code,
            title=str(meta.get("title", book_id)),
            detail=dewey["label"],
        )
    return {
        "ok": True,
        "path": str(path),
        "format": "h7c",
        "bytes": len(packed),
        "dewey": code,
        "dewey_label": dewey["label"],
    }


def upload_book(
    *,
    title: str,
    author: str = "",
    text: str,
    category: str = "",
    license_name: str = "Field",
    dewey_code: str | None = None,
) -> dict[str, Any]:
    title = title.strip()
    text = text.strip()
    if not title or len(text) < 40:
        return {"ok": False, "error": "title_and_text_required"}
    book_id = re.sub(r"[^\w]+", "_", title.lower())[:64].strip("_") or "upload"
    base_id = book_id
    n = 1
    existing = {b["id"] for b in _scan_books()}
    while book_id in existing:
        book_id = f"{base_id}_{n}"
        n += 1
    return write_h7_book(
        book_id,
        text,
        {"title": title, "author": author, "category": category, "license": license_name},
        dewey_code=dewey_code,
    )


def reader_fonts() -> dict[str, Any]:
    return {"fonts": READER_FONTS}


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"

    if cmd == "build":
        force = "--force" in sys.argv
        pid = DEFAULT_PROFILE
        if "--profile" in sys.argv:
            idx = sys.argv.index("--profile")
            if idx + 1 < len(sys.argv):
                pid = sys.argv[idx + 1]
        json.dump(build_catalog(force=force, profile_id=pid), sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0

    if cmd == "fingerprint":
        lib = _librarian()
        if not lib:
            json.dump({"ok": False, "error": "librarian_missing"}, sys.stdout)
        else:
            json.dump({
                "ok": True,
                "fingerprint": lib.compute_field_fingerprint(),
                "unchanged": lib.field_unchanged(),
                **lib.load_fingerprint_doc(),
            }, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    if cmd == "page" and len(sys.argv) >= 4:
        chars = int(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4].isdigit() else None
        json.dump(read_page(sys.argv[2], int(sys.argv[3]), page_chars=chars), sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    if cmd == "full" and len(sys.argv) >= 3:
        json.dump(read_full(sys.argv[2]), sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    if cmd == "search" and len(sys.argv) >= 3:
        q = " ".join(sys.argv[2:])
        unified = search_library(q)
        json.dump({**unified, "hits": unified.get("books", [])}, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    if cmd in ("atlas", "collections"):
        atlas = _atlas_mod()
        if atlas:
            doc = atlas.load_atlas() or atlas.build_atlas(_scan_books(), text_for_id=_source_text, force="--force" in sys.argv)
            json.dump(doc, sys.stdout, indent=2)
        else:
            json.dump({"ok": False, "error": "atlas_module_missing"}, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    if cmd == "passages" and len(sys.argv) >= 3:
        q = " ".join(sys.argv[2:])
        atlas = _atlas_mod()
        hits = atlas.search_passages(q) if atlas else []
        json.dump({"ok": True, "query": q, "hits": hits}, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    if cmd == "topics":
        atlas = _atlas_mod()
        doc = atlas.load_atlas() if atlas else None
        json.dump({"ok": True, "topics": (doc or {}).get("topics", [])}, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    if cmd == "truth" and len(sys.argv) >= 3:
        truth_py = INSTALL / "lib" / "h7-library-truth.py"
        if not truth_py.is_file():
            json.dump({"ok": False, "error": "truth_module_missing"}, sys.stdout)
            sys.stdout.write("\n")
            return 1
        import subprocess
        proc = subprocess.run(
            [sys.executable, str(truth_py), "book", sys.argv[2]],
            capture_output=True,
            text=True,
            timeout=120,
            env=os.environ.copy(),
        )
        sys.stdout.write(proc.stdout or "{}")
        if not proc.stdout.endswith("\n"):
            sys.stdout.write("\n")
        return 0

    if cmd == "dewey":
        pid = DEFAULT_PROFILE
        if "--profile" in sys.argv:
            idx = sys.argv.index("--profile")
            if idx + 1 < len(sys.argv):
                pid = sys.argv[idx + 1]
        json.dump({
            "ok": True,
            "profile": pid,
            "shelves": dewey_shelves(profile_id=pid),
            "war_shelves": war_shelves(profile_id=pid),
            "map": _load_dewey(),
            "tree": _load_dewey_tree(),
        }, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    if cmd == "profiles":
        doc = _load_library_profiles()
        json.dump({
            "ok": True,
            "default_profile": doc.get("default_profile", "hostess7"),
            "translation_help": doc.get("translation_help", ""),
            "profiles": list_library_profiles(),
        }, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    if cmd == "war":
        lib = _librarian()
        if lib:
            json.dump(lib.ascertain_war_books(), sys.stdout, indent=2)
        else:
            json.dump({"ok": False, "error": "librarian_missing"}, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    if cmd == "organize":
        tie = _field_tie()
        if not tie:
            json.dump({"ok": False, "error": "field_tie_missing"}, sys.stdout, indent=2)
        else:
            dry = "--dry-run" in sys.argv
            json.dump(tie.organize_h7_to_dewey(dry_run=dry, classify_fn=classify_dewey), sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    if cmd == "tracking":
        tie = _field_tie()
        if tie:
            json.dump(tie.tracking_lists(), sys.stdout, indent=2)
        else:
            json.dump({"ok": False, "error": "field_tie_missing"}, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    if cmd == "fonts":
        json.dump(reader_fonts(), sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    if cmd == "reader-issue" and len(sys.argv) >= 3:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "h7_secure_reader",
            INSTALL / "lib" / "h7-library-secure-reader.py",
        )
        if not spec or not spec.loader:
            json.dump({"ok": False, "error": "secure_reader_missing"}, sys.stdout, indent=2)
        else:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            book_id = sys.argv[2]
            meta = next((b for b in _scan_books() if b["id"] == book_id), None)
            json.dump(mod.issue_session(book_id, book_meta=meta), sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    if cmd == "reader" and len(sys.argv) >= 3:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "h7_secure_reader",
            INSTALL / "lib" / "h7-library-secure-reader.py",
        )
        if not spec or not spec.loader:
            json.dump({"ok": False, "error": "secure_reader_missing"}, sys.stdout, indent=2)
            sys.stdout.write("\n")
            return 1
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        sub = sys.argv[2]
        if sub == "knowledge":
            bid = sys.argv[3] if len(sys.argv) > 3 else ""
            q = sys.argv[4] if len(sys.argv) > 4 else ""
            json.dump(mod.knowledge_query(book_id=bid, q=q), sys.stdout, indent=2)
        elif sub == "bookmarks" and len(sys.argv) >= 4:
            body = json.loads(sys.argv[3]) if sys.argv[3].startswith("{") else {}
            bid = str(body.get("book_id", ""))
            tok = str(body.get("token", ""))
            sig = str(body.get("signature", ""))
            if body.get("action") == "add":
                json.dump(mod.save_bookmark(
                    bid, page=int(body.get("page", 1)), label=str(body.get("label", "")),
                    token=tok, signature=sig,
                ), sys.stdout, indent=2)
            elif body.get("action") == "delete":
                json.dump(mod.delete_bookmark(
                    bid, bookmark_id=str(body.get("bookmark_id", "")),
                    token=tok, signature=sig,
                ), sys.stdout, indent=2)
            else:
                json.dump(mod.list_bookmarks(bid, token=tok, signature=sig), sys.stdout, indent=2)
        elif sub == "progress" and len(sys.argv) >= 4:
            body = json.loads(sys.argv[3])
            json.dump(mod.save_progress(
                str(body.get("book_id", "")),
                page=int(body.get("page", 1)),
                page_count=int(body.get("page_count", 0)),
                token=str(body.get("token", "")),
                signature=str(body.get("signature", "")),
            ), sys.stdout, indent=2)
        elif sub == "layout" and len(sys.argv) >= 4:
            body = json.loads(sys.argv[3])
            json.dump(mod.save_layout(
                str(body.get("book_id", "")),
                layout=body.get("layout") or {},
                token=str(body.get("token", "")),
                signature=str(body.get("signature", "")),
            ), sys.stdout, indent=2)
        else:
            json.dump({"ok": False, "error": "reader_subcommand"}, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    if cmd in ("librarians", "corps"):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "nexus_librarian_corps",
            INSTALL / "lib" / "nexus-librarian-corps.py",
        )
        if not spec or not spec.loader:
            json.dump({"ok": False, "error": "corps_missing"}, sys.stdout, indent=2)
        else:
            corps = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(corps)
            if "--teach" in sys.argv:
                lid = None
                if "--id" in sys.argv:
                    idx = sys.argv.index("--id")
                    if idx + 1 < len(sys.argv):
                        lid = sys.argv[idx + 1]
                json.dump(corps.teach_doctrine(librarian_id=lid), sys.stdout, indent=2)
            else:
                json.dump(corps.corps_status(), sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    if cmd == "checkout" and len(sys.argv) >= 3:
        co = _checkout()
        if not co:
            json.dump({"ok": False, "error": "checkout_missing"}, sys.stdout, indent=2)
        else:
            body: dict[str, Any] = {}
            if len(sys.argv) > 3:
                try:
                    body = json.loads(sys.argv[3])
                except json.JSONDecodeError:
                    body = {"days": sys.argv[3]}
            book_id = sys.argv[2]
            meta = body.get("book") if isinstance(body.get("book"), dict) else None
            if not meta:
                meta = next((b for b in _scan_books() if b["id"] == book_id), None)
            json.dump(
                co.checkout_book(
                    book_id,
                    days=body.get("days", 14),
                    patron=str(body.get("patron") or "operator"),
                    book_meta=meta,
                ),
                sys.stdout,
                indent=2,
            )
        sys.stdout.write("\n")
        return 0

    if cmd == "checkin" and len(sys.argv) >= 3:
        co = _checkout()
        if not co:
            json.dump({"ok": False, "error": "checkout_missing"}, sys.stdout, indent=2)
        else:
            patron = sys.argv[3] if len(sys.argv) > 3 else "operator"
            json.dump(co.checkin_book(sys.argv[2], patron=patron), sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    if cmd in ("checkout-status", "checkout-posture"):
        co = _checkout()
        if not co:
            json.dump({"ok": False, "error": "checkout_missing"}, sys.stdout, indent=2)
        else:
            json.dump(co.posture(), sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    if cmd == "checkout-remind":
        co = _checkout()
        if not co:
            json.dump({"ok": False, "error": "checkout_missing"}, sys.stdout, indent=2)
        else:
            force = "--force" in sys.argv
            json.dump(co.run_daily_reminders(force=force), sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    if cmd == "upload" and len(sys.argv) >= 3:
        try:
            payload = json.loads(sys.argv[2])
        except json.JSONDecodeError:
            print("upload requires JSON payload", file=sys.stderr)
            return 1
        json.dump(
            upload_book(
                title=str(payload.get("title", "")),
                author=str(payload.get("author", "")),
                text=str(payload.get("text", "")),
                category=str(payload.get("category", "")),
                license_name=str(payload.get("license", "Field")),
                dewey_code=payload.get("dewey") or None,
            ),
            sys.stdout,
            indent=2,
        )
        sys.stdout.write("\n")
        return 0

    print(
        "usage: h7-library-bridge.py [build [--force] [--profile <id>]|fingerprint|page <id> <n> [chars]|"
        "full <id>|search <q>|atlas|passages <q>|topics|dewey [--profile <id>]|profiles|war|organize [--dry-run]|tracking|fonts|"
        "checkout <id> [json]|checkin <id>|checkout-status|checkout-remind|upload <json>]",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())