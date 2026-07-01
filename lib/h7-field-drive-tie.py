#!/usr/bin/env pythong
"""Tie Hostess7 TEAM fieldstorage into NEXUS library — corpora, manifest, staging, path resolve."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
HOSTESS7_ROOT = Path(os.environ.get("HOSTESS7_ROOT", str(INSTALL / "Hostess7")))
HOSTESS7_TEAM_FIELD = Path(os.environ.get("HOSTESS7_TEAM_FIELD", "/media/default/HOSTESS7_TEAM/fieldstorage"))
CACHE_FIELD = HOSTESS7_ROOT / "cache" / "fieldstorage"

# Brain corpora → Dewey-classified virtual field books (readable in panel)
BRAIN_CORPUS_BOOKS: tuple[dict[str, str], ...] = (
    {"id": "h7-warfare-field-corpus", "corpus": "warfare", "title": "Hostess7 Warfare Field Corpus", "author": "Hostess7 War-Chief", "category": "military", "dewey": "355.02"},
    {"id": "h7-legal-field-corpus", "corpus": "legal", "title": "Hostess7 Legal Field Corpus", "author": "Hostess7 Counsel", "category": "law", "dewey": "340"},
    {"id": "h7-medical-field-corpus", "corpus": "medical", "title": "Hostess7 Medical Field Corpus", "author": "Hostess7 Clinic", "category": "medical", "dewey": "610"},
    {"id": "h7-detective-field-corpus", "corpus": "detective", "title": "Hostess7 Detective Field Corpus", "author": "Hostess7 Detective", "category": "security", "dewey": "363.25"},
    {"id": "h7-physics-field-corpus", "corpus": "physics", "title": "Hostess7 Physics Field Corpus", "author": "Hostess7 Bench", "category": "physics", "dewey": "530"},
    {"id": "h7-chemistry-field-corpus", "corpus": "chemistry", "title": "Hostess7 Chemistry Field Corpus", "author": "Hostess7 Bench", "category": "chemistry", "dewey": "540"},
    {"id": "h7-english-field-corpus", "corpus": "english", "title": "Hostess7 English Field Corpus", "author": "Hostess7 Talk", "category": "language", "dewey": "428"},
    {"id": "h7-code-field-corpus", "corpus": "code", "title": "Hostess7 Code Field Corpus", "author": "Hostess7 Bench", "category": "programming", "dewey": "005"},
    {"id": "h7-hearing-field-corpus", "corpus": "hearing", "title": "Hostess7 Hearing & Acoustics Corpus", "author": "Hostess7", "category": "hearing", "dewey": "534"},
    {"id": "h7-imagine-field-corpus", "corpus": "imagine", "title": "Hostess7 Imagine Field Corpus", "author": "Hostess7", "category": "art", "dewey": "700"},
    {"id": "h7-beyond-field-corpus", "corpus": "beyond", "title": "Hostess7 Beyond Field Corpus", "author": "Hostess7", "category": "philosophy", "dewey": "100"},
    {"id": "h7-world-field-corpus", "corpus": "world", "title": "Hostess7 World Brief Corpus", "author": "Hostess7", "category": "civics", "dewey": "320"},
    {"id": "h7-k12-field-corpus", "corpus": "k12", "title": "Hostess7 K-12 Textbook Corpus", "author": "Hostess7 Education", "category": "education", "dewey": "370"},
    {"id": "h7-security-field-corpus", "corpus": "security", "title": "Hostess7 Security & Network Corpus", "author": "Hostess7 / NEXUS-Shield", "category": "security", "dewey": "005.8"},
    {"id": "h7-vision-field-corpus", "corpus": "vision", "title": "Hostess7 Vision & Motion Corpus", "author": "Hostess7", "category": "vision", "dewey": "006.3"},
    {"id": "h7-memes-field-corpus", "corpus": "memes", "title": "Hostess7 Memes Corpus", "author": "Hostess7", "category": "culture", "dewey": "302"},
    {"id": "h7-people-field-corpus", "corpus": "people", "title": "Hostess7 People Registry Corpus", "author": "Hostess7", "category": "social", "dewey": "305"},
)


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



def field_roots() -> list[Path]:
    roots: list[Path] = []
    for p in (HOSTESS7_TEAM_FIELD, CACHE_FIELD):
        if p.is_dir() and p not in roots:
            roots.append(p)
    return roots or [HOSTESS7_TEAM_FIELD]


def primary_field_root() -> Path:
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "field_drive_system",
            Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield")) / "lib" / "field-drive-system.py",
        )
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return Path(mod.primary_field_root())
    except Exception:
        pass
    for root in field_roots():
        if (root / "brain").is_dir():
            return root
    return HOSTESS7_TEAM_FIELD


def resolve_field_path(path: str | Path) -> Path | None:
    """Remap Hostess7 cache paths to TEAM NVMe when the file lives on field drive."""
    p = Path(path)
    if p.is_file():
        return p
    s = str(p)
    cache_prefix = str(CACHE_FIELD)
    team_prefix = str(HOSTESS7_TEAM_FIELD)
    if s.startswith(cache_prefix):
        alt = Path(team_prefix + s[len(cache_prefix):])
        if alt.is_file():
            return alt
    # basename lookup in textbooks
    name = p.name
    if name:
        for root in field_roots():
            for hit in (root / "textbooks").glob(name):
                if hit.is_file():
                    return hit
            for hit in (root / "textbooks").glob(f"**/{name}"):
                if hit.is_file():
                    return hit
    return None


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _corpus_domains(doc: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize heterogeneous brain corpus.json layouts."""
    out: list[dict[str, Any]] = []
    for key in ("domains", "entries", "hearing_workflow", "hearing", "lanes", "items"):
        for row in doc.get(key) or []:
            if isinstance(row, dict):
                out.append(row)
    return out


def corpus_text(corpus_id: str) -> str:
    for root in field_roots():
        path = root / "brain" / corpus_id / "corpus.json"
        if not path.is_file():
            continue
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        meta = next((b for b in BRAIN_CORPUS_BOOKS if b["corpus"] == corpus_id), {})
        lines = [
            meta.get("title", f"Hostess7 {corpus_id} corpus"),
            f"Source: {path}",
            "",
        ]
        domains = _corpus_domains(doc)
        if not domains:
            if doc.get("disclaimer"):
                lines.append(str(doc["disclaimer"]))
                lines.append("")
            stats = []
            for key in ("textbook_count", "fetched_count", "entity_count", "file_count"):
                if doc.get(key) is not None:
                    stats.append(f"{key}: {doc[key]}")
            if stats:
                lines.append("## Corpus stats")
                lines.append(", ".join(stats))
                lines.append("")
            for key in ("by_grade", "by_subject", "training"):
                val = doc.get(key)
                if val:
                    lines.append(f"## {key}")
                    lines.append(json.dumps(val, ensure_ascii=False) if isinstance(val, dict) else str(val))
                    lines.append("")
        for dom in domains:
            title = dom.get("title") or dom.get("name") or dom.get("id") or "Section"
            body = dom.get("body") or dom.get("text") or dom.get("summary") or dom.get("why") or ""
            if not body and dom.get("url"):
                body = f"Reference: {dom['url']}"
            lines.append(f"## {title}")
            lines.append(str(body))
            tags = dom.get("tags")
            if tags:
                lines.append(f"*Tags: {', '.join(tags) if isinstance(tags, list) else tags}*")
            lines.append("")
        return "\n".join(lines)
    return ""


def brain_corpus_books() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for spec in BRAIN_CORPUS_BOOKS:
        text = corpus_text(spec["corpus"])
        if len(text.strip()) < 80:
            continue
        out.append({
            "id": spec["id"],
            "title": spec["title"],
            "author": spec["author"],
            "category": spec["category"],
            "license": "Field (Hostess7 TEAM drive)",
            "description": f"Brain corpus — brain/{spec['corpus']}/corpus.json on field drive",
            "dewey": spec["dewey"],
            "format": "field-corpus",
            "char_count": len(text),
            "page_count": max(1, len(text) // 3200),
            "ready": True,
            "field_source": f"brain/{spec['corpus']}/corpus.json",
            "war_shelf": spec["corpus"] == "warfare",
        })
    return out


def manifest_index() -> dict[str, dict[str, Any]]:
    """Full Hostess7 library manifest + search index from TEAM field drive."""
    by_id: dict[str, dict[str, Any]] = {}
    for root in field_roots():
        lib = root / "brain" / "library"
        for row in _read_jsonl(lib / "search_index.jsonl"):
            bid = str(row.get("id", ""))
            if bid:
                by_id.setdefault(bid, {}).update(row)
        for row in _read_jsonl(lib / "bibliography.jsonl"):
            bid = str(row.get("id", ""))
            if bid:
                by_id.setdefault(bid, {}).update(row)
        manifest = lib / "manifest.json"
        if manifest.is_file():
            try:
                doc = json.loads(manifest.read_text(encoding="utf-8"))
                for row in doc.get("books") or []:
                    bid = str(row.get("id", ""))
                    if not bid:
                        continue
                    merged = {**by_id.get(bid, {}), **row}
                    raw_path = str(row.get("path") or row.get("h7_path") or "")
                    if raw_path:
                        resolved = resolve_field_path(raw_path)
                        if resolved:
                            merged["path"] = str(resolved)
                            merged["has_h7"] = True
                    by_id[bid] = merged
            except (OSError, json.JSONDecodeError):
                pass
    return by_id


def _tracking_row(
    *,
    bid: str,
    title: str,
    status: str,
    source: str,
    dewey: str = "",
    author: str = "",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": bid,
        "title": title,
        "author": author,
        "dewey": dewey,
        "status": status,
        "source": source,
        "library": False,
    }
    if extra:
        row.update(extra)
    return row


def tracking_lists(*, on_disk_ids: set[str] | None = None) -> dict[str, Any]:
    """Home-only tracking — manifest, staging, seed — not panel library books."""
    on_disk = on_disk_ids or set()
    manifest = manifest_index()
    lists: dict[str, list[dict[str, Any]]] = {
        "manifest": [],
        "staging": [],
        "seed": [],
        "unpacked": [],
    }

    for bid, meta in sorted(manifest.items()):
        if bid in on_disk:
            continue
        has_path = bool(meta.get("path") or meta.get("h7_path"))
        status = "packed" if meta.get("ok") and has_path else (
            "fetch_failed" if meta.get("error") else "catalog_only"
        )
        lists["manifest"].append(_tracking_row(
            bid=bid,
            title=str(meta.get("title", bid)),
            author=str(meta.get("author", "")),
            dewey=str(meta.get("dewey", "")),
            status=status,
            source="brain/library/manifest",
            extra={"error": meta.get("error", ""), "has_h7": meta.get("has_h7", False)},
        ))

    for root in field_roots():
        staging = root / "team_staging" / "k12_bulk" / "fetched"
        if not staging.is_dir():
            continue
        for path in sorted(staging.glob("*.txt")):
            bid = path.stem
            if bid in on_disk:
                continue
            try:
                size = path.stat().st_size
            except OSError:
                size = 0
            lists["staging"].append(_tracking_row(
                bid=bid,
                title=bid.replace("_", " ").replace("-", " ").title(),
                status="staging_txt",
                source=str(path.relative_to(root)),
                extra={"bytes": size},
            ))

    for path in (
        Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield")) / "data" / "war-books-seed.json",
        Path(__file__).resolve().parents[1] / "data" / "war-books-seed.json",
    ):
        if not path.is_file():
            continue
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for seed in doc.get("books") or []:
            bid = str(seed.get("id", ""))
            if not bid or bid in on_disk:
                continue
            lists["seed"].append(_tracking_row(
                bid=bid,
                title=str(seed.get("title", bid)),
                author=str(seed.get("author", "")),
                dewey=str(seed.get("dewey", "")),
                status="war_seed",
                source="data/war-books-seed.json",
            ))
        break

    total = sum(len(v) for v in lists.values())
    return {
        "updated": _now(),
        "total": total,
        "manifest_count": len(lists["manifest"]),
        "staging_count": len(lists["staging"]),
        "seed_count": len(lists["seed"]),
        "lists": lists,
        "note": "Tracking only — browse Library for H7 + virtual corpus books.",
    }


def organize_h7_to_dewey(*, dry_run: bool = False, classify_fn: Any = None) -> dict[str, Any]:
    """Move flat textbooks/*.h7 into textbooks/dewey/{class}/ — library shelf places."""
    root = primary_field_root()
    textbooks = root / "textbooks"
    moved: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    import importlib.util
    h7_mod = None
    scripts = HOSTESS7_ROOT / "scripts"
    if scripts.is_dir():
        import sys
        if str(scripts) not in sys.path:
            sys.path.insert(0, str(scripts))
        try:
            import field_h7_book as h7_mod  # type: ignore
        except ImportError:
            h7_mod = None

    for path in sorted(textbooks.glob("*.h7")):
        bid = path.stem
        dewey_code = "000"
        dewey_label = "General"
        title = bid
        if h7_mod:
            try:
                header, _ = h7_mod.unpack_h7(path.read_bytes(), verify=False)
                dewey_code = str(header.get("dewey") or dewey_code)
                dewey_label = str(header.get("dewey_label") or dewey_label)
                title = str(header.get("title") or title)
            except (OSError, ValueError):
                pass
        if classify_fn and dewey_code == "000":
            d = classify_fn(
                category="",
                title=title,
                subject="",
                author="",
            )
            dewey_code = d.get("code", dewey_code)
            dewey_label = d.get("label", dewey_label)

        main = re.sub(r"[^0-9].*", "", dewey_code)[:3].ljust(3, "0")
        dest_dir = textbooks / "dewey" / main
        safe = re.sub(r"[^\w.-]", "_", bid)
        dest = dest_dir / f"{safe}.h7"
        if dest.resolve() == path.resolve():
            skipped.append({"id": bid, "reason": "already_in_place", "path": str(path)})
            continue
        if dest.is_file():
            skipped.append({"id": bid, "reason": "dest_exists", "path": str(dest)})
            continue
        row = {"id": bid, "from": str(path), "to": str(dest), "dewey": dewey_code}
        if dry_run:
            moved.append({**row, "dry_run": True})
            continue
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
            path.rename(dest)
            dewey_lib = None
            try:
                tie_py = INSTALL / "lib" / "field-dewey-library.py"
                if tie_py.is_file():
                    import importlib.util
                    spec = importlib.util.spec_from_file_location("field_dewey_tie", tie_py)
                    if spec and spec.loader:
                        dewey_lib = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(dewey_lib)
            except Exception:
                dewey_lib = None
            if dewey_lib and hasattr(dewey_lib, "ensure_h7c_path"):
                h7c = dewey_lib.ensure_h7c_path(dest)
                if h7c.suffix.lower() == ".h7c":
                    row["h7c"] = str(h7c)
                    row["converted"] = True
            moved.append(row)
        except OSError as exc:
            errors.append({**row, "error": str(exc)})

    inv = field_drive_inventory()
    inv["textbooks_h7_flat"] = len(list(textbooks.glob("*.h7")))
    inv["textbooks_h7_dewey"] = len(list((textbooks / "dewey").glob("**/*.h7"))) if (textbooks / "dewey").is_dir() else 0

    return {
        "ok": not errors,
        "dry_run": dry_run,
        "field_root": str(root),
        "moved_count": len(moved),
        "skipped_count": len(skipped),
        "error_count": len(errors),
        "moved": moved,
        "skipped": skipped,
        "errors": errors,
        "inventory": inv,
    }


def field_drive_inventory() -> dict[str, Any]:
    root = primary_field_root()
    textbooks = root / "textbooks"
    inv: dict[str, Any] = {
        "updated": _now(),
        "primary_root": str(root),
        "team_mounted": HOSTESS7_TEAM_FIELD.is_dir(),
        "brain_mounted": (HOSTESS7_TEAM_FIELD / "brain").is_dir(),
        "textbooks_h7_flat": len(list(textbooks.glob("*.h7"))) if textbooks.is_dir() else 0,
        "textbooks_h7_dewey": len(list((textbooks / "dewey").glob("**/*.h7"))) if (textbooks / "dewey").is_dir() else 0,
        "textbooks_h7": (
            len(list(textbooks.glob("*.h7")))
            + len(list((textbooks / "dewey").glob("**/*.h7")))
        ) if textbooks.is_dir() else 0,
        "textbooks_txt": len(list(textbooks.glob("*.txt"))) if textbooks.is_dir() else 0,
        "dewey_shelf_dirs": len(list((textbooks / "dewey").iterdir())) if (textbooks / "dewey").is_dir() else 0,
        "k12_staging_txt": len(list((root / "team_staging/k12_bulk/fetched").glob("*.txt")))
        if (root / "team_staging/k12_bulk/fetched").is_dir() else 0,
        "bibliography_entries": 0,
        "search_index_entries": 0,
        "manifest_packed": 0,
        "brain_corpora": [],
    }
    lib = root / "brain" / "library"
    if (lib / "bibliography.jsonl").is_file():
        inv["bibliography_entries"] = sum(1 for _ in lib.joinpath("bibliography.jsonl").open())
    if (lib / "search_index.jsonl").is_file():
        inv["search_index_entries"] = sum(1 for _ in lib.joinpath("search_index.jsonl").open())
    if (lib / "manifest.json").is_file():
        try:
            m = json.loads((lib / "manifest.json").read_text(encoding="utf-8"))
            inv["manifest_packed"] = sum(1 for b in m.get("books", []) if b.get("ok"))
            inv["manifest_catalog_count"] = m.get("catalog_count", 0)
        except (OSError, json.JSONDecodeError):
            pass
    for spec in BRAIN_CORPUS_BOOKS:
        corp = root / "brain" / spec["corpus"] / "corpus.json"
        if corp.is_file():
            try:
                doc = json.loads(corp.read_text(encoding="utf-8"))
                n = len(doc.get("domains") or doc.get("entries") or [])
            except (OSError, json.JSONDecodeError):
                n = 0
            inv["brain_corpora"].append({
                "id": spec["id"],
                "corpus": spec["corpus"],
                "domains": n,
                "book_id": spec["id"],
            })
    inv["brain_corpus_count"] = len(inv["brain_corpora"])
    return inv


def tie_field_drive(*, classify_dewey: Any = None, on_disk_ids: set[str] | None = None) -> dict[str, Any]:
    """Library = virtual corpus only; manifest/staging = home tracking lists."""
    manifest = manifest_index()
    corpora = brain_corpus_books()
    tracking = tracking_lists(on_disk_ids=on_disk_ids)
    return {
        "ok": True,
        "inventory": field_drive_inventory(),
        "manifest_ids": list(manifest.keys()),
        "manifest_count": len(manifest),
        "corpus_books": corpora,
        "corpus_count": len(corpora),
        "tracking": tracking,
        "manifest": manifest,
    }


def source_text_for_id(book_id: str) -> str:
    """Readable text — virtual corpus books only (not staging tracking)."""
    for spec in BRAIN_CORPUS_BOOKS:
        if spec["id"] == book_id:
            return corpus_text(spec["corpus"])
    return ""


def is_library_book(book: dict[str, Any]) -> bool:
    """Panel library — virtual corpus + shelved H7/field-txt only (no tracking lists)."""
    fmt = str(book.get("format", ""))
    if fmt in ("catalog-seed", "staging-txt", "catalog-entry"):
        return False
    if fmt == "field-corpus":
        return bool(book.get("ready"))
    if fmt == "H7" and book.get("ready"):
        return bool(book.get("path"))
    if fmt == "field-txt" and book.get("ready"):
        return True
    return False


def main() -> int:
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "inventory"
    if cmd == "inventory":
        print(json.dumps(field_drive_inventory(), indent=2))
    elif cmd == "tie":
        print(json.dumps(tie_field_drive(), indent=2, default=str))
    elif cmd == "tracking":
        print(json.dumps(tracking_lists(), indent=2))
    elif cmd == "organize":
        dry = "--dry-run" in sys.argv
        classify_fn = None
        print(json.dumps(organize_h7_to_dewey(dry_run=dry, classify_fn=classify_fn), indent=2))
    elif cmd == "corpus" and len(sys.argv) >= 3:
        print(corpus_text(sys.argv[2])[:8000])
    else:
        print("usage: h7-field-drive-tie.py [inventory|tie|tracking|organize [--dry-run]|corpus <id>]", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())