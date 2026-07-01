#!/usr/bin/env pythong
"""Canonical Hostess7 paths — env > package > git tree."""
from __future__ import annotations

import json
import os
import sys
import warnings
from pathlib import Path
from typing import Any


def _normalize_path(p: Path) -> Path:
    resolved = p.resolve()
    if sys.platform == "win32":
        return resolved.absolute()
    return resolved


def _package_dir() -> Path | None:
    try:
        import hostess7  # noqa: WPS433

        return _normalize_path(Path(hostess7.__file__).parent)
    except Exception:
        return None


def _is_dev_tree(path: Path) -> bool:
    """Dev tree requires scripts/ with Python modules — avoids pip false-positives."""
    if not path.is_dir():
        return False
    scripts = path / "scripts"
    has_scripts = scripts.is_dir() and any(scripts.glob("*.py"))
    if not has_scripts:
        return False
    if (path / "Hostess7.sh").is_file():
        return True
    return path.name == "Hostess7"


def _dev_tree_root() -> Path | None:
    pkg = _package_dir()
    if not pkg:
        return None
    for parent in pkg.parents:
        if _is_dev_tree(parent):
            return _normalize_path(parent)
    return None


def is_packaged_install() -> bool:
    """True when running from installed wheel/sdist without Hostess7.sh tree."""
    pkg = _package_dir()
    if not pkg:
        return False
    dev = _dev_tree_root()
    if dev:
        return False
    return True


def hostess7_root() -> Path:
    env = os.environ.get("HOSTESS7_ROOT", "").strip()
    if env:
        p = _normalize_path(Path(env))
        if p.is_dir():
            _export_root_env(p)
            return p
    dev = _dev_tree_root()
    if dev and dev.is_dir():
        _export_root_env(dev)
        return dev
    here = _normalize_path(Path(__file__))
    for parent in here.parents:
        if _is_dev_tree(parent):
            _export_root_env(parent)
            return parent
    fallback = _normalize_path(here.parents[2])
    _export_root_env(fallback)
    return fallback


def _export_root_env(root: Path) -> None:
    os.environ.setdefault("HOSTESS7_ROOT", str(root))


def nexus_install_root() -> Path:
    env = os.environ.get("NEXUS_INSTALL_ROOT", "").strip()
    if env:
        return _normalize_path(Path(env))
    root = hostess7_root()
    parent = root.parent
    if parent.name == "NewLatest":
        return parent
    if (parent / "lib").is_dir() and (parent / "nexus.sh").is_file():
        return parent
    return parent if parent.is_dir() else root


def _warn_migration_errors(log: list[dict[str, Any]]) -> None:
    errors = [e for e in log if e.get("error") or e.get("action") == "error"]
    if errors:
        warnings.warn(
            f"Hostess7 state migration completed with {len(errors)} error(s) — see migration.json",
            RuntimeWarning,
            stacklevel=3,
        )


def _prune_legacy_after_migration(
    root: Path,
    unified: Path,
    legacy: Path,
    *,
    prune: bool,
) -> list[dict[str, Any]]:
    log: list[dict[str, Any]] = []
    if not prune:
        return log
    legacy_brain = root / "cache" / "fieldstorage" / "brain"
    targets: list[tuple[Path, str]] = []
    if legacy_brain.is_dir() and legacy_brain.resolve() != unified.resolve():
        targets.append((legacy_brain, "fieldstorage_brain"))
    if legacy.is_dir() and legacy.resolve() != unified.resolve():
        for name in ("cortex.json", "hostess7-cortex.json"):
            src = legacy / name
            if src.is_file() and (unified / "cortex.json").is_file():
                targets.append((src, f"legacy_state_{name}"))

    for path, label in targets:
        migrated_marker = unified / "legacy" / "pruned" / f"{label}.marker"
        if migrated_marker.is_file():
            continue
        try:
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                import shutil
                shutil.rmtree(path, ignore_errors=True)
            migrated_marker.parent.mkdir(parents=True, exist_ok=True)
            migrated_marker.write_text("pruned\n", encoding="utf-8")
            log.append({"action": "prune", "path": str(path), "label": label})
        except OSError as exc:
            log.append({"action": "error", "path": str(path), "error": str(exc)[:120]})

    if legacy_brain.is_dir() and any(legacy_brain.rglob("*.json")):
        warnings.warn(
            "Legacy cache/fieldstorage/brain still present after migration — set HOSTESS7_MIGRATION_PRUNE=1",
            RuntimeWarning,
            stacklevel=3,
        )
    return log


def brain_state_dir() -> Path:
    """Unified cortex state — brain/state/ is canonical."""
    root = hostess7_root()
    env = os.environ.get("HOSTESS7_BRAIN_STATE", "").strip()
    unified = _normalize_path(Path(env)) if env else _normalize_path(root / "brain" / "state")
    legacy_state = Path(os.environ.get("NEXUS_STATE_DIR", "")).resolve() if os.environ.get("NEXUS_STATE_DIR") else None
    if legacy_state is None or not legacy_state.is_dir():
        legacy_state = nexus_install_root() / ".nexus-state"

    os.environ["HOSTESS7_BRAIN_STATE"] = str(unified)
    os.environ.setdefault("NEXUS_STATE_DIR", str(unified))
    _export_root_env(root)
    os.environ.setdefault("NEXUS_INSTALL_ROOT", str(nexus_install_root()))

    unified.mkdir(parents=True, exist_ok=True)
    (unified / "snapshots").mkdir(exist_ok=True)

    migrate_marker = unified / "migration.json"
    if not migrate_marker.is_file():
        log = _migrate_legacy_state(root, unified, legacy_state, migrate_marker)
        _warn_migration_errors(log)
        prune = os.environ.get("HOSTESS7_MIGRATION_PRUNE", "1").strip().lower() in ("1", "true", "yes")
        extra = _prune_legacy_after_migration(root, unified, legacy_state, prune=prune)
        if extra and migrate_marker.is_file():
            try:
                doc = json.loads(migrate_marker.read_text(encoding="utf-8"))
                doc.setdefault("entries", []).extend(extra)
                doc["pruned"] = True
                migrate_marker.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
            except (OSError, json.JSONDecodeError, NameError):
                pass

    return unified


def _migrate_legacy_state(root: Path, unified: Path, legacy: Path, marker: Path) -> list[dict[str, Any]]:
    from datetime import datetime, timezone

    log: list[dict[str, Any]] = []
    legacy_brain = root / "cache" / "fieldstorage" / "brain"
    target_legacy = unified / "legacy"
    target_legacy.mkdir(parents=True, exist_ok=True)

    if legacy_brain.is_dir() and legacy_brain.resolve() != unified.resolve():
        for src in sorted(legacy_brain.rglob("*.json")):
            try:
                rel = src.relative_to(legacy_brain)
                dest = target_legacy / "fieldstorage_brain" / rel
                if dest.is_file():
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(src.read_bytes())
                log.append({"action": "copy", "from": str(src), "to": str(dest)})
            except OSError as exc:
                log.append({"action": "error", "path": str(src), "error": str(exc)[:120]})

    if legacy.is_dir() and legacy.resolve() != unified.resolve():
        for name in ("cortex.json", "hostess7-cortex.json"):
            src = legacy / name
            if src.is_file() and not (unified / "cortex.json").is_file():
                try:
                    (unified / "cortex.json").write_bytes(src.read_bytes())
                    log.append({"action": "cortex_import", "from": str(src)})
                except OSError as exc:
                    log.append({"action": "error", "path": str(src), "error": str(exc)[:120]})

    doc = {
        "schema": "hostess7-state-migration/v1",
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "unified": str(unified),
        "legacy_state": str(legacy),
        "legacy_brain": str(legacy_brain),
        "entries": log,
        "count": len(log),
        "errors": [e for e in log if e.get("error")],
    }
    try:
        marker.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        log.append({"action": "error", "path": str(marker), "error": str(exc)[:120]})
    return log


def scripts_dir() -> Path:
    return hostess7_root() / "scripts"


def scripts_available() -> bool:
    sd = scripts_dir()
    return sd.is_dir() and any(sd.glob("*.py"))


def storage_dir() -> Path:
    """Prefer brain/state for new writes; legacy cache/fieldstorage still readable."""
    root = hostess7_root()
    state_brain = brain_state_dir() / "legacy" / "fieldstorage_brain"
    if state_brain.is_dir() and any(state_brain.rglob("*.json")):
        return brain_state_dir() / "legacy"
    return root / "cache" / "fieldstorage"


def cortex_file() -> Path:
    return brain_state_dir() / "cortex.json"


def packaged_context() -> dict[str, Any]:
    root = hostess7_root()
    pkg = _package_dir()
    scripts_ok = scripts_available()
    return {
        "packaged": is_packaged_install(),
        "package_dir": str(pkg) if pkg else None,
        "scripts_available": scripts_ok,
        "scripts_missing_in_packaged": is_packaged_install() and not scripts_ok,
        "root": str(root),
        "brain_state": str(brain_state_dir()),
        "dev_tree": bool(_dev_tree_root()),
        "platform": sys.platform,
    }