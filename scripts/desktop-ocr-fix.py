#!/usr/bin/env pythong
"""OCR-driven desktop cleanup — read icon labels, sort clutter, drop broken launchers."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

DESKTOP = Path.home() / "Desktop"
STATE = Path(os.environ.get("NEXUS_STATE_DIR", Path(__file__).resolve().parents[1] / ".nexus-state"))
OUT = STATE / "ocr-desktop"
REPORT = OUT / "fix-report.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _capture(path: Path) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":0")}
    for cmd in (
        ["gnome-screenshot", "-f", str(path)],
        ["import", "-window", "root", str(path)],
    ):
        try:
            subprocess.run(cmd, env=env, capture_output=True, timeout=30, check=False)
            if path.is_file() and path.stat().st_size > 5000:
                return True
        except (OSError, subprocess.SubprocessError):
            continue
    return path.is_file()


def _ocr(path: Path) -> str:
    if not path.is_file():
        return ""
    install = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
    bridge = install / "lib" / "final-eye-h7-ocr.py"
    if bridge.is_file():
        try:
            proc = subprocess.run(
                [os.environ.get("PYTHON", "python3"), str(bridge), "ocr", str(path)],
                capture_output=True, text=True, timeout=90, check=False,
                env={**os.environ, "NEXUS_INSTALL_ROOT": str(install), "NEXUS_STATE_DIR": str(STATE)},
            )
            doc = json.loads(proc.stdout or "{}")
            text = str(doc.get("text") or doc.get("ocr") or "")
            if text.strip():
                h7 = doc.get("h7_file") or doc.get("ocr_file")
                if h7:
                    (OUT / "last-capture.h7").write_bytes(Path(h7).read_bytes()) if Path(h7).is_file() else None
                return text
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
            pass
    return ""


def _desktop_items() -> list[Path]:
    items: list[Path] = []
    for p in DESKTOP.iterdir():
        if p.name.startswith("."):
            continue
        items.append(p)
    return sorted(items, key=lambda x: x.name.lower())


def _normalize_label(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "", text)
    return text


def _ocr_labels(ocr_text: str) -> list[str]:
    labels: list[str] = []
    for line in ocr_text.splitlines():
        line = line.strip()
        if not line or len(line) < 3:
            continue
        if any(tok in line.lower() for tok in ("devices", "free space", "composer", "shift+tab")):
            continue
        if re.search(r"\d+\s*(gb|tb|items)", line, re.I):
            continue
        labels.append(line)
    return labels


def _match_score(name: str, label: str) -> float:
    n = _normalize_label(name)
    l = _normalize_label(label)
    if not n or not l:
        return 0.0
    if n in l or l in n:
        return 1.0
    # partial overlap for truncated OCR (e.g. reportitxt → report.txt)
    overlap = sum(1 for c in n if c in l)
    return overlap / max(len(n), len(l))


def _desktop_exec_ok(path: Path) -> bool:
    if not path.suffix == ".desktop":
        return True
    text = path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"^Exec=(.+)$", text, re.M)
    if not m:
        return False
    raw = m.group(1).strip()
    quoted = re.findall(r'"([^"]+)"', raw)
    if quoted:
        for target in quoted:
            p = Path(target)
            if p.suffix.lower() in {".exe", ".bat", ".cmd", ".msi"} or str(p).startswith("/mnt/"):
                return p.is_file()
        return Path(quoted[0]).is_file()
    token = raw.split()[0]
    return Path(token).is_file() or shutil.which(token) is not None


def _move(src: Path, dest_dir: Path, report: dict) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    if dest.exists():
        stamp = time.strftime("%Y%m%dT%H%M%S")
        dest = dest_dir / f"{src.stem}-{stamp}{src.suffix}"
    shutil.move(str(src), str(dest))
    report["moved"].append({"from": str(src), "to": str(dest)})


def _remove(path: Path, report: dict, reason: str) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    report["removed"].append({"path": str(path), "reason": reason})


def _rename(src: Path, new_name: str, report: dict) -> None:
    dest = src.parent / new_name
    if dest.exists():
        return
    src.rename(dest)
    report["renamed"].append({"from": str(src), "to": str(dest)})


def fix_desktop() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    shot = OUT / "desktop-full.png"
    if not _capture(shot):
        shot = OUT / "desktop-full.png"  # reuse prior capture if present

    ocr_text = _ocr(shot)
    (OUT / "ocr.txt").write_text(ocr_text, encoding="utf-8")

    report: dict = {
        "schema": "desktop-ocr-fix/v1",
        "ts": _now(),
        "screenshot": str(shot),
        "ocr_labels": _ocr_labels(ocr_text),
        "moved": [],
        "removed": [],
        "renamed": [],
        "kept": [],
        "errors": [],
    }

    sorted_root = DESKTOP / "_sorted"
    buckets = {
        ".md": sorted_root / "docs",
        ".txt": sorted_root / "docs",
        ".mp4": sorted_root / "media",
        ".comp": sorted_root / "shaders",
        ".appimage": sorted_root / "apps",
    }
    rename_map = {
        "Untitled Folder": "display-driver",
        "Untitled Folder 2": "amouranthrtx-archive",
        "Untitled Folder 3": "grok-docs",
    }
    keep_names = {
        "nexus-field.desktop",
        "SG",
        "KILROY",
        "NewLatest",
        "NEXUS-Shield",
        "AMOURANTHRTX",
        "ocr",
        "_sorted",
    }

    for item in _desktop_items():
        name = item.name
        if name in keep_names or name in rename_map:
            if name in rename_map:
                _rename(item, rename_map[name], report)
            else:
                report["kept"].append(str(item))
            continue

        if item.suffix.lower() == ".desktop":
            if not _desktop_exec_ok(item):
                quarantine = OUT / "broken-launchers"
                quarantine.mkdir(parents=True, exist_ok=True)
                dest = quarantine / item.name
                shutil.move(str(item), str(dest))
                report["removed"].append(
                    {"path": str(item), "reason": "broken Exec — quarantined", "quarantine": str(dest)}
                )
                local = Path.home() / ".local" / "share" / "applications" / item.name
                if local.is_file():
                    local.unlink()
                    report["removed"].append({"path": str(local), "reason": "duplicate broken launcher"})
            else:
                report["kept"].append(str(item))
            continue

        ext = item.suffix.lower()
        if ext in buckets and item.is_file():
            try:
                _move(item, buckets[ext], report)
            except OSError as exc:
                report["errors"].append({"path": str(item), "error": str(exc)})
            continue

        if item.is_dir():
            report["kept"].append(str(item))
            continue

        if item.is_file() and name == "Ace":
            try:
                _move(item, sorted_root / "notes", report)
            except OSError as exc:
                report["errors"].append({"path": str(item), "error": str(exc)})
            continue

        report["kept"].append(str(item))

    # OCR ↔ filesystem cross-check
    matches = []
    for label in report["ocr_labels"]:
        best = None
        best_score = 0.0
        for item in _desktop_items():
            score = _match_score(item.name, label)
            if score > best_score:
                best_score = score
                best = item.name
        if best and best_score >= 0.45:
            matches.append({"ocr": label, "file": best, "score": round(best_score, 2)})
    report["ocr_matches"] = matches
    report["ok"] = not report["errors"]

    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    doc = fix_desktop()
    print(json.dumps(doc, ensure_ascii=False, indent=2))
    return 0 if doc.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())