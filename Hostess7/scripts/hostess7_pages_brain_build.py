#!/usr/bin/env pythong
"""Build GitHub Pages brain — delegates to isolated github-brain mirror."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
sys.path.insert(0, str(ROOT / "src"))

from hostess7 import __version__
from hostess7.github_brain import build_corpus, status_mirror  # noqa: E402


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _combinatronic_snap() -> dict[str, Any]:
    """Live combinatronic snap before brain mirror — avoids 16+ min optimal cycles."""
    import importlib.util

    auto_py = ROOT.parent / "lib" / "field-brain-combinatronic-auto.py"
    if not auto_py.is_file():
        return {"ok": False, "skipped": True, "hint": "brain_auto_missing"}
    spec = importlib.util.spec_from_file_location("brain_comb_auto", auto_py)
    if not spec or not spec.loader:
        return {"ok": False, "skipped": True}
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if hasattr(mod, "auto_brain_combinatronic"):
        return mod.auto_brain_combinatronic(context="pages_brain_build")
    return {"ok": False, "skipped": True}


def build(*, full: bool = True) -> dict[str, Any]:
    comb = _combinatronic_snap()
    doc = build_corpus(include_repo_files=True)
    doc["combinatronic_auto"] = comb
    st = status_mirror()
    st_path = DOCS / "status.json"
    boot_path = DOCS / "boot.json"

    status_doc = {
        "name": "Hostess 7",
        "version": __version__,
        "mode": "pages-surfaces",
        "pages_role": "hostess7_main",
        "lane": "github-mirror",
        "brain": True,
        "sovereign_brain": False,
        "writes_to_sovereign": False,
        "read_only": True,
        "chunk_count": doc.get("chunks", 0),
        "corpus": "/github-brain/corpus.json",
        "posture": "war-ready",
        "war_ready": True,
        "demo": False,
        "pages_url": "https://zacharygeurts.github.io/Hostess7/",
        "updated": _ts()[:10],
        **st,
    }
    st_path.write_text(json.dumps(status_doc, indent=2) + "\n", encoding="utf-8")

    boot_doc = {}
    if boot_path.is_file():
        try:
            boot_doc = json.loads(boot_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    boot_doc.update({
        "pages_role": "github_brain_mirror",
        "pages_note": "GitHub io uses isolated github-brain — same knowledge, sovereign brain untouched.",
        "brain": True,
        "lane": "github-mirror",
        "sovereign_brain": False,
    })
    boot_path.write_text(json.dumps(boot_doc, indent=2) + "\n", encoding="utf-8")

    return doc


def main() -> int:
    doc = build(full="--lite" not in sys.argv)
    print(json.dumps(doc, indent=2))
    print(f"METRIC pages_brain_build={doc.get('chunks', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())