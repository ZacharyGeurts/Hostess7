#!/usr/bin/env python3
"""AIA AI Accelerator — FIELD_QUBES staging lane for ZacharyGeurts/AIA + Hostess7 Pages mirror."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-aia-accelerator-doctrine.json"
PANEL = STATE / "field-aia-accelerator-panel.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _import_qubes() -> Any | None:
    qpy = INSTALL / "lib" / "field-qubes-drive-provision.py"
    if not qpy.is_file():
        return None
    import importlib.util

    spec = importlib.util.spec_from_file_location("field_qubes_aia", qpy)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _qubes_mount() -> Path:
    doc = _load(DOCTRINE, {})
    q = doc.get("qubes_drive") or {}
    return Path(os.environ.get("FIELD_QUBES_MOUNT", q.get("mount") or "/media/default/FIELD_QUBES"))


def _staging_root() -> Path:
    doc = _load(DOCTRINE, {})
    sub = str((doc.get("qubes_drive") or {}).get("staging_subdir") or "fieldstorage/aia-publish")
    mount = _qubes_mount()
    if mount.is_dir():
        return mount / sub
    team = Path(os.environ.get("HOSTESS7_TEAM_FIELD", "/media/default/HOSTESS7_TEAM1/fieldstorage"))
    return team / "aia-publish"


def _full_ironclad_cert(*, held: bool) -> dict[str, Any]:
    cert_py = INSTALL / "lib" / "field-ironclad-component-cert.py"
    if cert_py.is_file():
        try:
            import importlib.util

            spec = importlib.util.spec_from_file_location("icc_aia", cert_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "full_cert"):
                    return mod.full_cert(
                        component_id="aia_accelerator",
                        citation="ironclad:aia:1",
                        layers=["ironclad", "aia_accelerator", "field_qubes_drive", "g16_build_cache", "queen_chips"],
                        held=held,
                        facet="aia_accelerator",
                    )
        except Exception:
            pass
    return {
        "schema": "ironclad-component-cert/v1",
        "component_id": "aia_accelerator",
        "citation": "ironclad:aia:1",
        "full_cert": held,
        "verdict": "GREEN" if held else "WATCH",
    }


def _dir_size(path: Path) -> int:
    total = 0
    if not path.exists():
        return 0
    try:
        for p in path.rglob("*"):
            if p.is_file():
                total += p.stat().st_size
    except OSError:
        pass
    return total


def export_aia_bundle(*, write_readme: bool = True) -> dict[str, Any]:
    """Stage accelerator bundle on FIELD_QUBES (or team fallback) for ZacharyGeurts/AIA upload."""
    doc = _load(DOCTRINE, {})
    repo = doc.get("repo") or {}
    qmod = _import_qubes()
    qpanel = qmod.panel() if qmod and hasattr(qmod, "panel") else {}
    mount = _qubes_mount()
    qubes_ready = mount.is_dir() and any(mount.iterdir()) if mount.is_dir() else False
    if qmod and hasattr(qmod, "ensure_team_layout"):
        qmod.ensure_team_layout()

    staging = _staging_root()
    staging.mkdir(parents=True, exist_ok=True)
    build_cache = staging.parent / "build-cache"
    if not build_cache.is_dir() and mount.is_dir():
        alt = mount / "fieldstorage" / "build-cache"
        if alt.is_dir():
            build_cache = alt

    copied: list[str] = []
    for sub in ("g16-rtx", "cmake", "queen-roms"):
        src = build_cache / sub if build_cache.is_dir() else None
        if src and src.is_dir():
            dst = staging / "build-cache" / sub
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.is_dir():
                try:
                    shutil.copytree(src, dst, symlinks=True, dirs_exist_ok=True)
                    copied.append(str(dst))
                except OSError:
                    pass

    posture = {
        "schema": "aia-accelerator-posture/v1",
        "updated": _utc(),
        "boss": "hostess7",
        "repo": repo.get("full"),
        "pages_url": repo.get("pages_url"),
        "qubes_mount": str(mount),
        "qubes_ready": qubes_ready,
        "staging": str(staging),
        "build_cache_sources": [str(build_cache / s) for s in ("g16-rtx", "cmake", "queen-roms") if (build_cache / s).is_dir()],
        "hostess7_pages": (doc.get("hostess7_pages") or {}).get("runtime"),
    }
    (staging / "accelerator-posture.json").write_text(
        json.dumps(posture, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    upload_ready = bool(copied) or (staging / "manifest.json").is_file()
    ironclad_cert = _full_ironclad_cert(held=upload_ready and qubes_ready)
    manifest = {
        "schema": "aia-accelerator-manifest/v1",
        "title": "AIA — AI Accelerator",
        "repo": repo.get("full"),
        "github": repo.get("url"),
        "pages": repo.get("pages_url"),
        "hostess7_mirror": (doc.get("hostess7_pages") or {}).get("pages_api"),
        "ironclad_citation": doc.get("ironclad_citation") or "ironclad:aia:1",
        "ironclad_cert": ironclad_cert,
        "staged": _utc(),
        "qubes_device": qpanel.get("qubes_device"),
        "bundle_paths": copied,
        "upload_steps": doc.get("upload_steps") or [],
    }
    (staging / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if write_readme:
        readme = (
            f"# AIA — AI Accelerator\n\n"
            f"Staged from **FIELD_QUBES** by Hostess 7 for [{repo.get('full')}]({repo.get('url')}).\n\n"
            f"- Pages: {repo.get('pages_url')}\n"
            f"- Hostess7 mirror: {(doc.get('hostess7_pages') or {}).get('runtime')}api/field-aia-accelerator.json\n"
            f"- Staged: {manifest['staged']}\n"
        )
        (staging / "README.md").write_text(readme, encoding="utf-8")

    return {
        "ok": qubes_ready or staging.is_dir(),
        "schema": "field-aia-accelerator-export/v1",
        "updated": _utc(),
        "repo": repo.get("full"),
        "pages_url": repo.get("pages_url"),
        "qubes_ready": qubes_ready,
        "staging": str(staging),
        "staging_bytes": _dir_size(staging),
        "copied": copied,
        "manifest": str(staging / "manifest.json"),
        "upload_ready": upload_ready,
        "ironclad_cert": ironclad_cert,
        "upload_steps": doc.get("upload_steps") or [],
    }


def panel(*, write: bool = True) -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    repo = doc.get("repo") or {}
    h7 = doc.get("hostess7_pages") or {}
    export = export_aia_bundle(write_readme=False)
    qmod = _import_qubes()
    qpanel = qmod.panel() if qmod and hasattr(qmod, "panel") else {}

    upload_ready = bool(export.get("upload_ready"))
    ironclad_cert = _full_ironclad_cert(held=upload_ready and bool(export.get("qubes_ready")))
    out = {
        "ok": True,
        "schema": "field-aia-accelerator-panel/v1",
        "title": doc.get("title"),
        "motto": doc.get("motto"),
        "updated": _utc(),
        "boss": "hostess7",
        "ironclad_citation": doc.get("ironclad_citation") or "ironclad:aia:1",
        "ironclad_cert": ironclad_cert,
        "ironclad_sealed": ironclad_cert.get("ironclad_sealed"),
        "full_cert": ironclad_cert.get("full_cert"),
        "repo": repo,
        "hostess7_pages": {
            **h7,
            "pages_api_live": f"{h7.get('runtime', 'https://zacharygeurts.github.io/Hostess7/').rstrip('/')}/api/field-aia-accelerator.json",
        },
        "qubes": {
            "device": qpanel.get("qubes_device"),
            "mount": str(_qubes_mount()),
            "ready": export.get("qubes_ready"),
            "panel": qpanel,
        },
        "export": export,
        "upload_ready": export.get("upload_ready"),
        "upload_steps": doc.get("upload_steps") or [],
        "api": doc.get("api"),
    }
    if write:
        PANEL.parent.mkdir(parents=True, exist_ok=True)
        PANEL.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("export", "aia-export", "stage"):
        print(json.dumps(export_aia_bundle(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("panel", "json", "status"):
        print(json.dumps(panel(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage", "cmds": ["json", "export", "aia-export"]}, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())