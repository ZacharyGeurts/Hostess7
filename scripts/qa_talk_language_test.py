#!/usr/bin/env pythong
"""QA: Language Expert — natural talk window replies."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

os.environ["HOSTESS7_TALK"] = "1"
os.environ["HOSTESS7_OUTPUT_WINDOW"] = "1"

from field_talk_language import fast_talk_reply, shape_brain_text  # noqa: E402


def fail(msg: str) -> int:
    print(f"FAIL {msg}", file=sys.stderr)
    return 1


def main() -> int:
    hi = fast_talk_reply("Hi again")
    if not hi or "Zachary" not in hi:
        return fail("greeting reply bad")
    if "Live codebase" in hi or "Economics" in hi:
        return fail("greeting has corpus dump")

    amo = fast_talk_reply("Do you know Amouranth?")
    if not amo or "Amouranth" not in amo:
        return fail("Amouranth reply bad")
    for bad in ("Live codebase", "People brain", "Economics & finance", "Brain workspaces"):
        if bad in amo:
            return fail(f"Amouranth has {bad}")

    shaped = shape_brain_text(
        "Hi",
        "Live codebase evidence:\n  foo\n\nEconomics & finance: Micro supply demand.\n\nHello there.",
    )
    if "Live codebase" in shaped or "Economics" in shaped:
        return fail("shape_brain_text did not strip dumps")

    print("OK talk_language greeting+people+shape")
    print("METRIC qa_talk_language=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())