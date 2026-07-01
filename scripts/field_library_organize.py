#!/usr/bin/env pythong
"""Organize H7 library by Dewey Decimal System — field drive folders on upload/pack."""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEWEY_INDEX = ROOT / "cache" / "fieldstorage" / "brain" / "library" / "dewey_index.json"

DEWEY_CLASSES: tuple[dict[str, str | tuple[int, int]], ...] = (
    {"code": "000", "title": "Computer science, information & general works", "range": (0, 99)},
    {"code": "100", "title": "Philosophy & psychology", "range": (100, 199)},
    {"code": "200", "title": "Religion", "range": (200, 299)},
    {"code": "300", "title": "Social sciences", "range": (300, 399)},
    {"code": "400", "title": "Language", "range": (400, 499)},
    {"code": "500", "title": "Science", "range": (500, 599)},
    {"code": "600", "title": "Technology", "range": (600, 699)},
    {"code": "700", "title": "Arts & recreation", "range": (700, 799)},
    {"code": "800", "title": "Literature", "range": (800, 899)},
    {"code": "900", "title": "History & geography", "range": (900, 999)},
)

SUBJECT_DEWEY: dict[str, tuple[str, str]] = {
    "programming": ("005", "Computer programming"),
    "computer_science": ("004", "Computer science"),
    "security": ("005.8", "Computer security"),
    "reference": ("030", "General encyclopedias"),
    "theology": ("230", "Christian theology"),
    "bible": ("220", "Bible"),
    "civics": ("320", "Political science"),
    "math": ("510", "Mathematics"),
    "science": ("500", "Science"),
    "physics": ("530", "Physics"),
    "chemistry": ("540", "Chemistry"),
    "biology": ("570", "Biology"),
    "medical": ("610", "Medicine & health"),
    "health": ("613", "Personal health"),
    "hearing": ("534", "Sound & acoustics"),
    "music": ("780", "Music"),
    "literature": ("813", "American fiction"),
    "children": ("028.5", "Children's literature"),
    "poetry": ("811", "American poetry"),
    "history": ("900", "History"),
    "k12": ("370", "K-12 textbooks"),
    "vision": ("006.3", "Computer vision"),
    "biography": ("920", "Biography"),
    "program": ("005.4", "Systems & programs"),
}

KEYWORD_RULES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("python", "programming", "software", "algorithm", "computer"), "005"),
    (("security", "firewall", "network", "tcp", "dpi"), "005.8"),
    (("physics", "relativity", "mechanics"), "530"),
    (("chemistry", "chemical"), "540"),
    (("biology", "microbiology"), "570"),
    (("medical", "nursing", "health", "medicine"), "610"),
    (("math", "algebra", "calculus"), "510"),
    (("history", "world war"), "900"),
    (("bible", "scripture", "koran", "theology"), "220"),
    (("music", "acoustic", "sound"), "534"),
    (("child", "juvenile", "young reader"), "028.5"),
    (("fiction", "novel", "story", "literature"), "813"),
    (("civics", "government", "political"), "320"),
)


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _field_root() -> Path:
    team = Path("/media/default/HOSTESS7_TEAM/fieldstorage")
    if (team / "brain").is_dir():
        return team
    return ROOT / "cache" / "fieldstorage"


def textbooks_dir() -> Path:
    return _field_root() / "textbooks"


def dewey_folder(code: str) -> Path:
    main = re.sub(r"[^0-9].*", "", code)[:3].ljust(3, "0")
    return textbooks_dir() / "dewey" / main


def classify_dewey(
    *,
    category: str = "",
    title: str = "",
    subject: str = "",
    author: str = "",
    text_sample: str = "",
) -> dict[str, str]:
    cat = (category or subject or "").lower().strip()
    if cat in SUBJECT_DEWEY:
        code, label = SUBJECT_DEWEY[cat]
        return {"code": code, "label": label}

    blob = f"{title} {subject} {author} {text_sample[:3000]}".lower()
    best = "000"
    best_score = 0
    for tokens, code in KEYWORD_RULES:
        score = sum(1 for t in tokens if t in blob)
        if score > best_score:
            best_score = score
            best = code

    label = SUBJECT_DEWEY.get(cat, (best, f"Dewey {best}"))[1]
    for _cat, (code, lbl) in SUBJECT_DEWEY.items():
        if code == best:
            label = lbl
            break
    return {"code": best, "label": label}


def h7_path_for_book(book_id: str, book: dict) -> Path:
    """Resolve .H7 destination under Dewey folder on field drive."""
    safe = re.sub(r"[^\w.-]", "_", book_id)
    dewey = classify_dewey(
        category=str(book.get("category", book.get("subject", ""))),
        title=str(book.get("title", book_id)),
        subject=str(book.get("subject", "")),
        author=str(book.get("author", "")),
    )
    folder = dewey_folder(dewey["code"])
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{safe}.h7"


def _load_catalog() -> list[dict]:
    from field_library_catalog import iter_all_library_books  # noqa: WPS433
    return list(iter_all_library_books())


def organize() -> dict:
    books = _load_catalog()
    buckets: dict[str, list[dict]] = {c["code"]: [] for c in DEWEY_CLASSES}
    for book in books:
        dewey = classify_dewey(
            category=str(book.get("category", book.get("subject", ""))),
            title=str(book.get("title", "")),
            subject=str(book.get("subject", "")),
            author=str(book.get("author", "")),
            text_sample=str(book.get("body", "")),
        )
        main = re.sub(r"[^0-9].*", "", dewey["code"])[:3].ljust(3, "0")
        buckets.setdefault(main, []).append({
            "id": book.get("id"),
            "title": book.get("title"),
            "author": book.get("author", ""),
            "dewey": dewey["code"],
            "dewey_label": dewey["label"],
            "h7_path": str(h7_path_for_book(str(book.get("id", "")), book)),
        })

    doc = {
        "updated": _ts(),
        "system": "dewey",
        "field_root": str(_field_root()),
        "shelves": [
            {
                "code": c["code"],
                "title": c["title"],
                "count": len(buckets.get(c["code"], [])),
                "books": buckets.get(c["code"], []),
            }
            for c in DEWEY_CLASSES
        ],
        "total_books": sum(len(v) for v in buckets.values()),
    }
    DEWEY_INDEX.parent.mkdir(parents=True, exist_ok=True)
    DEWEY_INDEX.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return doc


def print_shelves(doc: dict) -> None:
    print("Hostess 7 — Dewey Decimal library shelves")
    print("=" * 44)
    for shelf in doc["shelves"]:
        if not shelf["count"]:
            continue
        print(f"\n[{shelf['code']}] {shelf['title']} ({shelf['count']} books)")
        for b in shelf["books"][:6]:
            print(f"  · {b.get('dewey')} {b.get('title', '?')} — {b.get('author', '')}")
        if shelf["count"] > 6:
            print(f"  … +{shelf['count'] - 6} more")
    print(f"\nTotal catalogued: {doc['total_books']}")
    print(f"Index: {DEWEY_INDEX}")
    print("METRIC library_dewey_shelves=10")
    print("OK library-organize")


def main() -> int:
    doc = organize()
    print_shelves(doc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())