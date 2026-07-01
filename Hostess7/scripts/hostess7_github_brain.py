#!/usr/bin/env pythong
"""CLI — build and query the isolated GitHub brain mirror."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hostess7.github_brain import ask_mirror, build_corpus, status_mirror  # noqa: E402


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip().lower()
    if cmd in ("build", "mirror", "publish-prep"):
        print(json.dumps(build_corpus(), indent=2))
        return 0
    if cmd in ("ask", "query") and len(sys.argv) > 2:
        print(json.dumps(ask_mirror(" ".join(sys.argv[2:])), indent=2))
        return 0
    if cmd in ("status", "json"):
        print(json.dumps(status_mirror(), indent=2))
        return 0
    print(json.dumps({"usage": "hostess7_github_brain.py [build|status|ask QUERY]"}, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())