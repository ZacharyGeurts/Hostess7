#!/usr/bin/env pythong
"""Hostess7 path resolution — project root plus reachable external trees."""
from __future__ import annotations

import os
from pathlib import Path

_HOSTESS7_ROOT: Path | None = None


def hostess7_root() -> Path:
    global _HOSTESS7_ROOT
    if _HOSTESS7_ROOT is not None:
        return _HOSTESS7_ROOT
    env = os.environ.get("HOSTESS7_ROOT", "").strip()
    if env:
        _HOSTESS7_ROOT = Path(env).resolve()
        return _HOSTESS7_ROOT
    _HOSTESS7_ROOT = Path(__file__).resolve().parents[1]
    return _HOSTESS7_ROOT


def sg_root() -> Path | None:
    env = os.environ.get("SG_ROOT", "").strip()
    if env:
        p = Path(env).resolve()
        return p if p.is_dir() else None
    h = hostess7_root()
    if h.parent.name == "SG":
        return h.parent.resolve()
    desktop_sg = Path.home() / "Desktop" / "SG"
    return desktop_sg.resolve() if desktop_sg.is_dir() else None


def _looks_like_amouranthrtx(path: Path) -> bool:
    return path.is_dir() and (
        (path / "CMakeLists.txt").is_file()
        or (path / "linux.sh").is_file()
        or (path / "Navigator").is_dir()
    )


def amouranthrtx_root() -> Path | None:
    env = os.environ.get("AMOURANTHRTX_ROOT", "").strip()
    if env:
        p = Path(env).resolve()
        return p if _looks_like_amouranthrtx(p) else None
    h = hostess7_root()
    sg = sg_root()
    for candidate in (
        sg / "AMOURANTHRTX" if sg else None,
        h.parent / "AMOURANTHRTX",
        Path.home() / "Desktop" / "AMOURANTHRTX",
        Path.home() / "Desktop" / "SG" / "AMOURANTHRTX",
    ):
        if candidate and _looks_like_amouranthrtx(candidate):
            return candidate.resolve()
    return None


def extra_roots() -> list[Path]:
    """Optional comma-separated extra scan roots (HOSTESS7_EXTRA_ROOTS)."""
    raw = os.environ.get("HOSTESS7_EXTRA_ROOTS", "")
    out: list[Path] = []
    for part in raw.split(":"):
        part = part.strip()
        if not part:
            continue
        p = Path(part).expanduser().resolve()
        if p.is_dir():
            out.append(p)
    return out


def reach_roots() -> list[dict[str, str]]:
    """All trees Hostess7 can read — herself first, then SG, AMOURANTHRTX, extras."""
    roots: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(role: str, path: Path | None) -> None:
        if path is None or not path.is_dir():
            return
        key = str(path)
        if key in seen:
            return
        seen.add(key)
        roots.append({"role": role, "path": key})

    add("hostess7", hostess7_root())
    add("sg", sg_root())
    add("amouranthrtx", amouranthrtx_root())
    for i, p in enumerate(extra_roots()):
        add(f"extra_{i}", p)
    return roots


def field_storage_root() -> Path:
    """Best scored fieldstorage — TEAM NVMe when mounted, else cache."""
    team = os.environ.get("HOSTESS7_TEAM_FIELD", "").strip()
    storage = os.environ.get("HOSTESS7_STORAGE", "").strip()
    if storage:
        p = Path(storage).expanduser().resolve()
        if p.is_dir():
            return p
    candidates: list[Path] = []
    if team:
        candidates.append(Path(team))
    candidates.append(Path("/mnt/team/fieldstorage"))
    candidates.append(hostess7_root() / "cache" / "fieldstorage")
    rtx = amouranthrtx_root()
    if rtx:
        candidates.append(rtx / "cache" / "fieldstorage")
    for c in candidates:
        if (c / "brain").is_dir() or c.is_dir():
            return c.resolve()
    return (hostess7_root() / "cache" / "fieldstorage").resolve()


# Default import alias — Hostess7 project root
ROOT = hostess7_root()
STORAGE = field_storage_root()
BRAIN = STORAGE / "brain"