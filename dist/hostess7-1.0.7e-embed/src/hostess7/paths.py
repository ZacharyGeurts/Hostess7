#!/usr/bin/env pythong
"""Canonical Hostess7 paths — single root, unified brain state."""
from __future__ import annotations

import os
from pathlib import Path


def hostess7_root() -> Path:
    env = os.environ.get("HOSTESS7_ROOT", "").strip()
    if env:
        p = Path(env).resolve()
        if p.is_dir():
            return p
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "Hostess7.sh").is_file():
            return parent
        if parent.name == "Hostess7" and (parent / "scripts").is_dir():
            return parent
    return Path(__file__).resolve().parents[2]


def nexus_install_root() -> Path:
    env = os.environ.get("NEXUS_INSTALL_ROOT", "").strip()
    if env:
        return Path(env).resolve()
    root = hostess7_root()
    parent = root.parent
    return parent if parent.name == "NewLatest" else root


def brain_state_dir() -> Path:
    """Unified cortex state — versioned snapshots under brain/state."""
    root = hostess7_root()
    env = os.environ.get("HOSTESS7_BRAIN_STATE", "").strip()
    if env:
        return Path(env).resolve()
    unified = root / "brain" / "state"
    legacy = Path(os.environ.get("NEXUS_STATE_DIR", nexus_install_root() / ".nexus-state"))
    os.environ.setdefault("HOSTESS7_BRAIN_STATE", str(unified))
    os.environ.setdefault("NEXUS_STATE_DIR", str(unified))
    os.environ.setdefault("HOSTESS7_ROOT", str(root))
    os.environ.setdefault("NEXUS_INSTALL_ROOT", str(nexus_install_root()))
    unified.mkdir(parents=True, exist_ok=True)
    (unified / "snapshots").mkdir(exist_ok=True)
    if legacy.is_dir() and legacy != unified and not (unified / "migrated_from").is_file():
        marker = unified / "migrated_from"
        marker.write_text(f"legacy={legacy}\n", encoding="utf-8")
    return unified


def scripts_dir() -> Path:
    return hostess7_root() / "scripts"


def storage_dir() -> Path:
    return hostess7_root() / "cache" / "fieldstorage"


def cortex_file() -> Path:
    return brain_state_dir() / "cortex.json"