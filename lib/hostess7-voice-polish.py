#!/usr/bin/env pythong
"""Beyond-eloquence speech polish — IQ-aligned language before the mouth speaks."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

_INSTALL = Path(
    os.environ.get(
        "NEXUS_INSTALL_ROOT",
        str(Path(__file__).resolve().parent.parent),
    )
)
_IQ_DOCTRINE = _INSTALL / "data" / "hostess7-iq-doctrine.json"

_DROP = re.compile(
    r"^(Live codebase evidence|Brain route:|cache/fieldstorage|"
    r"Hostess 7 is boss|OK |METRIC |FAIL |--- |Evidence and next step)",
    re.I,
)

# Speakable upgrades — precision without lecture tone (IQ 100+ register)
_UPGRADE: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bvery good\b", re.I), "excellent"),
    (re.compile(r"\bvery bad\b", re.I), "deficient"),
    (re.compile(r"\bvery important\b", re.I), "crucial"),
    (re.compile(r"\bvery clear\b", re.I), "lucid"),
    (re.compile(r"\bI think that\b", re.I), "I hold that"),
    (re.compile(r"\bkind of\b", re.I), "in a sense"),
    (re.compile(r"\bsort of\b", re.I), "somewhat"),
    (re.compile(r"\ba lot of\b", re.I), "considerable"),
    (re.compile(r"\bget\b(?=\s+(it|this|that)\s+done)", re.I), "execute"),
    (re.compile(r"\buse\b(?=\s+the\b)", re.I), "employ"),
    (re.compile(r"\bshow you\b", re.I), "show you plainly"),

    (re.compile(r"\btalk about\b", re.I), "address"),
    (re.compile(r"\bmake sure\b", re.I), "ensure"),
)

_WARM_CONTRACTIONS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bI am\b"), "I'm"),
    (re.compile(r"\bI will\b"), "I'll"),
    (re.compile(r"\bwe will\b"), "we'll"),
    (re.compile(r"\byou are\b"), "you're"),
    (re.compile(r"\bdo not\b", re.I), "don't"),
    (re.compile(r"\bcannot\b", re.I), "can't"),
    (re.compile(r"\bit is\b"), "it's"),
    (re.compile(r"\bthat is\b"), "that's"),
)


def _h7s_read_json(path: Path, default: Any = None) -> Any:
    fs_py = INSTALL / "lib" / "field-h7s-fs.py"
    if path.suffix.lower() == ".json" and fs_py.is_file():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("_h7s_fs_io", fs_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "read_json"):
                    return mod.read_json(path, default=default)
        except Exception:
            pass
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}

def _load(path: Path, default: Any = None) -> Any:
    return _h7s_read_json(path, default=default)


def iq_floor() -> int:
    doc = _load(_IQ_DOCTRINE, {})
    return int(doc.get("iq_floor") or 100)


def _strip_noise(text: str) -> str:
    lines: list[str] = []
    for raw in re.split(r"[\n\r]+", text or ""):
        s = raw.strip()
        if not s or _DROP.match(s):
            continue
        if any(x in s for x in ("scripts/field_", "truth_kept=", "superintel/", "workspace`")):
            continue
        lines.append(s)
    clean = " ".join(lines)
    clean = re.sub(r"\033\[[0-9;]*m", "", clean)
    clean = re.sub(r"`[^`]+`", "", clean)
    clean = re.sub(r"\*\*([^*]+)\*\*", r"\1", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def _iq_tier(floor: int) -> str:
    if floor >= 175:
        return "roof"
    if floor >= 150:
        return "exceptional"
    if floor >= 130:
        return "high"
    return "baseline"


def polish_for_voice(text: str, *, max_chars: int = 480) -> dict[str, Any]:
    """Shape thought into speakable language beyond mere eloquence — IQ floor governs register."""
    raw = _strip_noise(text)
    if len(raw) < 3:
        return {"ok": False, "error": "text_too_short", "utterance": raw}

    floor = iq_floor()
    tier = _iq_tier(floor)
    utterance = raw

    # IQ never below 100 — register lifts above mere eloquence from the floor up
    if floor >= 100:
        for pat, repl in _UPGRADE:
            utterance = pat.sub(repl, utterance)

    for pat, repl in _WARM_CONTRACTIONS:
        utterance = pat.sub(repl, utterance)

    # Roof tier: one periodic beat — main clause last when long enough
    if tier in ("exceptional", "roof") and len(utterance) > 120 and ". " not in utterance[:80]:
        parts = utterance.split(", ", 1)
        if len(parts) == 2 and len(parts[0]) < 60:
            utterance = f"{parts[0]}, and {parts[1][0].lower()}{parts[1][1:]}"

    if len(utterance) > max_chars:
        cut = utterance[: max_chars - 1].rsplit(" ", 1)[0]
        utterance = cut.rstrip(".,;") + "."

    if utterance and not utterance[-1] in ".!?":
        utterance += "."

    return {
        "ok": True,
        "thought": raw,
        "utterance": utterance,
        "iq_floor": floor,
        "iq_tier": tier,
        "beyond_eloquence": floor >= 100,
        "polish": "hostess7-voice-polish/v1",
    }


def main() -> int:
    import sys

    text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    print(json.dumps(polish_for_voice(text), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())