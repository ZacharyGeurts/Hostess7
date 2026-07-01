#!/usr/bin/env python3
"""Wire sovereign-clock.py into every lib module that still uses wall-clock _now()."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "lib"

SKIP = {
    "sovereign-time.py",
    "sovereign-clock.py",
    "field-sovereign-sync.py",
    "field-sovereign-gate.py",
    "field-operator.py",
}

OLD = re.compile(
    r"def _now\(\) -> str:\n"
    r"    return datetime\.now\(timezone\.utc\)\.strftime\(\"%Y-%m-%dT%H:%M:%SZ\"\)\n",
    re.MULTILINE,
)

NEW = '''def _now() -> str:
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

'''

OLD_ISO = re.compile(
    r"def _now\(\) -> str:\n"
    r"    return datetime\.now\(timezone\.utc\)\.isoformat\(\)\n",
    re.MULTILINE,
)

NEW_ISO = '''def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        import importlib.util
        _p = Path(__file__).resolve().parent / "sovereign-clock.py"
        _s = importlib.util.spec_from_file_location("sovereign_clock", _p)
        if not _s or not _s.loader:
            raise ImportError("sovereign-clock.py missing")
        _SOVEREIGN_CLOCK_MOD = importlib.util.module_from_spec(_s)
        _s.loader.exec_module(_SOVEREIGN_CLOCK_MOD)
    return _SOVEREIGN_CLOCK_MOD.utc_iso()


_SOVEREIGN_CLOCK_MOD = None

'''


def ensure_path_import(text: str) -> str:
    if "from pathlib import Path" in text:
        return text
    if "import os" in text and "from pathlib import Path" not in text:
        return text.replace("from pathlib import Path", "from pathlib import Path", 1) or text
    # insert after future import or shebang block
    lines = text.splitlines(keepends=True)
    insert_at = 0
    for i, line in enumerate(lines):
        if line.startswith("from __future__"):
            insert_at = i + 1
        elif line.startswith("import ") or line.startswith("from "):
            if insert_at == 0:
                insert_at = i
    if "from pathlib import Path\n" not in text:
        lines.insert(insert_at, "from pathlib import Path\n")
    return "".join(lines)


def wire_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if "_SOVEREIGN_CLOCK_MOD" in text:
        return False
    new_text, n = OLD.subn(NEW, text, count=1)
    if n == 0:
        new_text, n = OLD_ISO.subn(NEW_ISO, text, count=1)
    if n == 0:
        return False
    new_text = ensure_path_import(new_text)
    path.write_text(new_text, encoding="utf-8")
    return True


def main() -> int:
    wired = 0
    for py in sorted(LIB.glob("*.py")):
        if py.name in SKIP:
            continue
        if wire_file(py):
            wired += 1
            print(f"wired {py.name}")
    print(f"total wired: {wired}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())