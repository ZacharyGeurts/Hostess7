#!/usr/bin/env python3
"""GitHub isolation — sovereign primary, world export, GitHub degraded mirror only."""
from __future__ import annotations

import importlib.util
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
DOCTRINE = INSTALL / "data" / "field-github-isolation-doctrine.json"
PANEL = STATE / "field-github-isolation-panel.json"
H7_DOCS = INSTALL / "Hostess7" / "docs"
HOST_MIRROR = INSTALL / ".nexus-field-drive" / "nexus-field"
TEAM = Path(os.environ.get("HOSTESS7_TEAM_FIELD", "/media/default/HOSTESS7_TEAM1/fieldstorage"))
QUBES = Path(os.environ.get("FIELD_QUBES_MOUNT", "/media/default/FIELD_QUBES"))


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _run_json(rel: str, args: list[str] | None = None, *, timeout: float = 30.0) -> dict[str, Any]:
    py = INSTALL / rel
    if not py.is_file():
        return {}
    try:
        proc = subprocess.run(
            [sys.executable, str(py), *(args or ["json"])],
            cwd=str(INSTALL),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
            check=False,
        )
        raw = (proc.stdout or "").strip()
        if raw.startswith("{"):
            return json.loads(raw)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        pass
    return {}


def _zachub_truth_roots() -> list[Path]:
    zachub_py = INSTALL / "lib" / "field-zachub-storage.py"
    if not zachub_py.is_file():
        return []
    try:
        spec = importlib.util.spec_from_file_location("field_zachub_export_roots", zachub_py)
        if not spec or not spec.loader:
            return []
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "zachub_truth_roots"):
            return list(mod.zachub_truth_roots())
    except Exception:
        pass
    return []


def _export_roots(doc: dict[str, Any]) -> list[Path]:
    sub = str((doc.get("world_visible") or {}).get("export_subdir") or "world-publish")
    roots: list[Path] = []
    for base in (HOST_MIRROR, TEAM, QUBES):
        if not base:
            continue
        p = base / sub if base.name != "nexus-field" else base / sub
        if base.name == "nexus-field" or "nexus-field" in str(base):
            p = base / sub
        elif base.name in ("fieldstorage", "FIELD_QUBES") or "fieldstorage" in str(base):
            p = base / sub
        else:
            p = base / "fieldstorage" / sub if (base / "fieldstorage").is_dir() else base / sub
        roots.append(p)
    for zroot in _zachub_truth_roots():
        roots.append(zroot)
    seen: set[str] = set()
    out: list[Path] = []
    for r in roots:
        key = str(r)
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def export_world(*, write: bool = True) -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    wv = doc.get("world_visible") or {}
    api_names = list(wv.get("api_snapshots") or [])
    surfaces = list(wv.get("surfaces") or [])
    written: list[str] = []
    errors: list[str] = []

    port = os.environ.get("NEXUS_THREAT_PANEL_PORT", "9477")
    sovereign = doc.get("sovereign_primary") or {}
    branding = doc.get("branding") or {}
    index = {
        "schema": "field-world-index/v1",
        "updated": _utc(),
        "product": doc.get("product") or branding.get("product") or "AmmoDrive",
        "owners": branding.get("owners") or ["Grok", "Zac"],
        "motto": doc.get("motto"),
        "github_role": doc.get("github_role"),
        "zachub_storage": (doc.get("sovereign_primary") or {}).get("zachub_storage"),
        "ammonet_version": (_load(H7_DOCS / "api" / "ammonet.json") or {}).get("version"),
        "sovereign_primary": {
            **sovereign,
            "panel": f"http://127.0.0.1:{port}/field",
            "ammonet": f"http://127.0.0.1:{port}/ammonet/",
            "grow_watch": f"http://127.0.0.1:{port}/field-grow-watch",
        },
        "world_surfaces": [
            {"id": s, "sovereign": f"http://127.0.0.1:{port}/{s.strip('/')}/"}
            for s in surfaces
        ],
        "github_mirror": doc.get("github_mirror") or {},
        "notice": wv.get("public_readme"),
    }

    for root in _export_roots(doc):
        try:
            root.mkdir(parents=True, exist_ok=True)
            api_dst = root / "api"
            api_dst.mkdir(parents=True, exist_ok=True)
            for name in api_names:
                src = H7_DOCS / "api" / name
                if src.is_file():
                    shutil.copy2(src, api_dst / name)
                    written.append(str(api_dst / name))
            for surf in surfaces:
                src_dir = H7_DOCS / surf.strip("/")
                if src_dir.is_dir():
                    dst = root / surf.strip("/")
                    if dst.exists():
                        shutil.rmtree(dst, ignore_errors=True)
                    shutil.copytree(src_dir, dst, dirs_exist_ok=True)
                    written.append(str(dst))
            (root / "world-index.json").write_text(
                json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"/><title>Field — sovereign world index</title>
<meta http-equiv="refresh" content="0;url=http://127.0.0.1:{port}/field"/>
<link rel="canonical" href="http://127.0.0.1:{port}/field"/>
</head><body><p>Sovereign Field — primary runtime on loopback. GitHub is degraded mirror only.</p>
<p><a href="http://127.0.0.1:{port}/field">Open Field</a> · AmmoNet {index.get('ammonet_version') or ''}</p></body></html>"""
            (root / "index.html").write_text(html, encoding="utf-8")
            written.append(str(root / "index.html"))
        except OSError as exc:
            errors.append(f"{root}: {exc}")

    zachub_mirror: dict[str, Any] = {}
    zachub_py = INSTALL / "lib" / "field-zachub-storage.py"
    if zachub_py.is_file() and write:
        try:
            spec = importlib.util.spec_from_file_location("field_zachub_export_mirror", zachub_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "mirror_github_truth"):
                    zachub_mirror = mod.mirror_github_truth(write=True)
        except Exception as exc:
            zachub_mirror = {"ok": False, "error": str(exc)[:200]}

    return {
        "ok": not errors or bool(written),
        "schema": "field-github-isolation-export/v1",
        "updated": _utc(),
        "written_count": len(written),
        "written": written[:32],
        "errors": errors,
        "world_index": index,
        "zachub_github_truth": zachub_mirror,
    }


def isolate(*, push_github: bool = False, write: bool = True) -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    os.environ.setdefault("NEXUS_HUB_STUBS_ENABLE", "0")
    os.environ.setdefault("NEXUS_GITHUB_ISOLATED", "1")
    os.environ.setdefault("HOSTESS7_PRESUME_HOSTILE", "1")
    os.environ.setdefault("HOSTESS7_GIT_TUNNEL", "tunnel")

    path_harden = _run_json("lib/field-github-path-harden.py", ["audit", "--apply"], timeout=45.0)
    rescue = _run_json("lib/field-rescue-ingress.py", ["clear-fakes"], timeout=20.0)
    drive: dict[str, Any] = {}
    if os.environ.get("NEXUS_FIELD_DRIVE_PUBLISH", "0").strip() in ("1", "yes", "on"):
        drive = _run_json("lib/field-drive-system.py", ["publish"], timeout=90.0)
    else:
        drive = {"ok": True, "skipped": True, "host_mirror_only": True}
    world = export_world(write=write)
    ammonet = _load(H7_DOCS / "api" / "ammonet.json", {})

    gh_mirror = doc.get("github_mirror") or {}
    push_result: dict[str, Any] = {"skipped": True, "reason": "github_isolated"}
    if push_github and gh_mirror.get("enabled"):
        script = INSTALL / "scripts" / "github-unflake.sh"
        if script.is_file():
            try:
                proc = subprocess.run(
                    ["bash", str(script), "push", "main"],
                    cwd=str(INSTALL),
                    capture_output=True,
                    text=True,
                    timeout=120,
                    env={**os.environ, "NEXUS_GITHUB_ISOLATED": "0"},
                    check=False,
                )
                push_result = {
                    "skipped": False,
                    "ok": proc.returncode == 0,
                    "rc": proc.returncode,
                    "tail": (proc.stdout or proc.stderr or "")[-400:],
                }
            except (OSError, subprocess.TimeoutExpired) as exc:
                push_result = {"skipped": False, "ok": False, "error": str(exc)[:200]}

    out = {
        "ok": True,
        "schema": "field-github-isolation/v1",
        "updated": _utc(),
        "motto": doc.get("motto"),
        "github_role": doc.get("github_role"),
        "isolated": True,
        "stub_publish": False,
        "sovereign_primary": doc.get("sovereign_primary"),
        "world_visible": world,
        "path_harden": {"verdict": path_harden.get("verdict"), "route": path_harden.get("recommended_route")},
        "fakes_cleared": rescue.get("fakes_removed") or rescue.get("ok"),
        "field_drive": {"ok": drive.get("ok"), "host_mirror_only": drive.get("host_mirror_only")},
        "ammonet_version": ammonet.get("version"),
        "github_mirror": gh_mirror,
        "github_push": push_result,
        "world_urls": {
            "sovereign_panel": f"http://127.0.0.1:{os.environ.get('NEXUS_THREAT_PANEL_PORT', '9477')}/field",
            "sovereign_ammonet": f"http://127.0.0.1:{os.environ.get('NEXUS_THREAT_PANEL_PORT', '9477')}/ammonet/",
            "github_pages": (gh_mirror.get("pages_urls") or [None])[0],
            "world_export": str(_export_roots(doc)[0]) if _export_roots(doc) else None,
        },
    }
    if write:
        _save(PANEL, out)
        api_dst = H7_DOCS / "api" / "field-github-isolation.json"
        api_dst.parent.mkdir(parents=True, exist_ok=True)
        api_dst.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def panel(*, write: bool = True) -> dict[str, Any]:
    cached = _load(PANEL, {})
    if cached.get("schema"):
        return cached
    return isolate(push_github=False, write=write)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    push = "--push-github" in sys.argv or os.environ.get("NEXUS_GITHUB_MIRROR_PUSH", "").strip() in ("1", "yes")
    if cmd in ("json", "panel", "status"):
        print(json.dumps(panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("isolate", "apply", "world"):
        print(json.dumps(isolate(push_github=push), ensure_ascii=False, indent=2))
        return 0
    if cmd == "export":
        print(json.dumps(export_world(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"usage": "field-github-isolation.py [json|isolate|export] [--push-github]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())