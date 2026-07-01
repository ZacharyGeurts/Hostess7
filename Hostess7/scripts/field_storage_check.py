#!/usr/bin/env pythong
"""Field storage audit — lossless-first policy for Hostess 7 talk window."""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STORAGE = ROOT / "cache" / "fieldstorage"
BRAIN = STORAGE / "brain"
WAVE = STORAGE / "field_wave.persist"
TEAM_IMG = STORAGE / "team_drive.img"
LOSSLESS_EXT = frozenset({
    ".json", ".jsonl", ".ppm", ".png", ".tiff", ".tif", ".bmp", ".wav", ".flac",
    ".txt", ".md", ".xml", ".html", ".persist", ".img",
})
LOSSY_EXT = frozenset({".jpg", ".jpeg", ".webp", ".mp3", ".aac", ".mp4", ".mkv"})


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dir_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def _count_ext(root: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    if not root.is_dir():
        return counts
    for p in root.rglob("*"):
        if p.is_file():
            ext = p.suffix.lower()
            counts[ext] = counts.get(ext, 0) + 1
    return counts


def scan_storage() -> dict[str, Any]:
    """Scan Field storage — prioritize lossless brain + wave persist."""
    brain_bytes = _dir_bytes(BRAIN)
    staging = _dir_bytes(STORAGE / "team_staging")
    total = _dir_bytes(STORAGE)
    ext_counts = _count_ext(STORAGE)
    lossless_n = sum(ext_counts.get(e, 0) for e in LOSSLESS_EXT)
    lossy_n = sum(ext_counts.get(e, 0) for e in LOSSY_EXT)
    infinite_legal = BRAIN / "legal" / "infinite" / "search_index.jsonl"
    infinite_med = BRAIN / "medical" / "infinite" / "search_index.jsonl"

    report: dict[str, Any] = {
        "scanned": _ts(),
        "storage_root": str(STORAGE),
        "total_bytes": total,
        "brain_bytes": brain_bytes,
        "staging_bytes": staging,
        "field_wave_bytes": WAVE.stat().st_size if WAVE.is_file() else 0,
        "field_wave_live": WAVE.is_file(),
        "team_drive_img": TEAM_IMG.is_file(),
        "team_drive_bytes": TEAM_IMG.stat().st_size if TEAM_IMG.is_file() else 0,
        "lossless_files": lossless_n,
        "lossy_files": lossy_n,
        "lossless_policy": "prefer json jsonl ppm png tiff flac persist — avoid lossy ingest unless source-only",
        "infinite_legal_lines": sum(1 for _ in infinite_legal.open()) if infinite_legal.is_file() else 0,
        "infinite_medical_lines": sum(1 for _ in infinite_med.open()) if infinite_med.is_file() else 0,
        "team_device": os.environ.get("TEAM_DRIVE_DEV", "/dev/nvme2n1"),
        "team_device_present": Path(os.environ.get("TEAM_DRIVE_DEV", "/dev/nvme2n1")).exists(),
    }

    bench = ROOT / "scripts" / "bench_storage.py"
    if bench.is_file():
        try:
            proc = subprocess.run(
                [os.environ.get("PYTHON", "pythong"), str(bench)],
                cwd=ROOT, capture_output=True, text=True, timeout=120, check=False,
            )
            for line in proc.stdout.splitlines():
                if line.startswith("METRIC bo_gain="):
                    report["bo_gain"] = line.split("=", 1)[1].strip()
                if line.startswith("METRIC transform_anchor_gb="):
                    report["transform_anchor_gb"] = line.split("=", 1)[1].strip()
            report["bench_rc"] = proc.returncode
        except (subprocess.TimeoutExpired, OSError):
            report["bench_rc"] = -1
    return report


def format_storage_report(report: dict[str, Any] | None = None) -> str:
    r = report or scan_storage()
    mb = lambda b: f"{b / (1024 * 1024):.1f} MiB"
    lines = [
        "=== Field Storage (lossless-first) ===",
        f"Root: {r.get('storage_root')}",
        f"Total: {mb(r.get('total_bytes', 0))} · Brain: {mb(r.get('brain_bytes', 0))} · Staging: {mb(r.get('staging_bytes', 0))}",
        f"field_wave.persist: {'live' if r.get('field_wave_live') else 'missing'} ({mb(r.get('field_wave_bytes', 0))})",
        f"team_drive.img: {'present' if r.get('team_drive_img') else 'absent'} ({mb(r.get('team_drive_bytes', 0))})",
        f"Infinite index: legal {r.get('infinite_legal_lines', 0)} · medical {r.get('infinite_medical_lines', 0)}",
        f"Files: {r.get('lossless_files', 0)} lossless · {r.get('lossy_files', 0)} lossy (deprioritized)",
        f"Policy: {r.get('lossless_policy')}",
    ]
    if r.get("bo_gain"):
        lines.append(f"SDF wave: anchor {r.get('transform_anchor_gb', '2')} GiB · bo_gain={r.get('bo_gain')}")
    if r.get("team_device_present"):
        lines.append(f"TEAM device: {r.get('team_device')} present")
    return "\n".join(lines)


def save_storage_snapshot(report: dict[str, Any] | None = None) -> Path:
    r = report or scan_storage()
    out = STORAGE / "brain" / "superintel" / "storage_snapshot.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(r, indent=2) + "\n", encoding="utf-8")
    return out


if __name__ == "__main__":
    rep = scan_storage()
    save_storage_snapshot(rep)
    print(format_storage_report(rep))
    print(f"METRIC storage_total_bytes={rep.get('total_bytes', 0)}")
    print(f"METRIC storage_lossless={rep.get('lossless_files', 0)}")
    print("OK storage_check")