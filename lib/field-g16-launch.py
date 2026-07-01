#!/usr/bin/env pythong
"""G16 Launch — discover, explore, and fire .launch chambers (no AmmoOS compile)."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))
DOCTRINE = INSTALL / "data" / "field-g16-launch-doctrine.json"
SETTINGS = STATE / "field-g16-launch-settings.json"
INDEX = STATE / "field-g16-launch-index.json"
PANEL = STATE / "field-g16-launch-panel.json"

_SKIP = {
    ".git", "node_modules", "__pycache__", "build", "dist", "target",
    ".nexus-state", "venv", ".venv", "upstream", "linux-kernel",
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def _save_atomic(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _queen_root() -> Path:
    for cand in (INSTALL / "Queen", SG / "NewLatest" / "Queen", SG / "Queen"):
        if (cand / "lib" / "queen-launch-chamber.py").is_file():
            return cand.resolve()
    return (INSTALL / "Queen").resolve()


def _grok16_root() -> Path:
    from sg_paths import grok16_root
    return grok16_root()


def _g16_bin() -> Path | None:
    g16 = _grok16_root()
    for rel in (
        "bin/g16",
        "build/gcc/gcc/x86_64-pc-linux-gnu/g16",
        "build/gcc/gcc/g16",
    ):
        p = g16 / rel
        if p.is_file() and os.access(p, os.X_OK):
            return p.resolve()
    which = subprocess.run(
        ["which", "g16"], capture_output=True, text=True, timeout=3, check=False,
    )
    if which.returncode == 0 and which.stdout.strip():
        p = Path(which.stdout.strip())
        if p.is_file():
            return p.resolve()
    return None


def _chamber_mod() -> Any | None:
    script = _queen_root() / "lib" / "queen-launch-chamber.py"
    if not script.is_file():
        return None
    spec = importlib.util.spec_from_file_location("queen_launch_chamber_g16", script)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _expand_root(raw: str) -> Path | None:
    s = str(raw).strip().replace("~/Desktop/SG", str(SG)).replace("~/SG", str(SG))
    if s.startswith("~/"):
        s = str(Path.home() / s[2:])
    try:
        p = Path(s).expanduser().resolve()
        return p if p.is_dir() else None
    except (OSError, RuntimeError):
        return None


def _scan_roots() -> list[Path]:
    doctrine = _load(DOCTRINE, {})
    roots: list[Path] = []
    seen: set[str] = set()
    for raw in doctrine.get("scan_roots") or []:
        p = _expand_root(str(raw))
        if p and str(p) not in seen:
            seen.add(str(p))
            roots.append(p)
    for extra in (SG, _grok16_root(), _queen_root()):
        try:
            r = extra.resolve()
            if r.is_dir() and str(r) not in seen:
                seen.add(str(r))
                roots.append(r)
        except OSError:
            pass
    return roots


def g16_probe() -> dict[str, Any]:
    g16 = _g16_bin()
    root = _grok16_root()
    ver = ""
    if g16:
        try:
            proc = subprocess.run(
                [str(g16), "-dumpversion"],
                capture_output=True, text=True, timeout=8, check=False,
            )
            ver = (proc.stdout or proc.stderr or "").strip().splitlines()[0][:40]
        except (OSError, subprocess.TimeoutExpired):
            pass
    doctrine = _load(_grok16_root() / "data" / "field-exec-uncompiled-doctrine.json", {})
    return {
        "ok": bool(g16),
        "g16_path": str(g16) if g16 else None,
        "grok16_root": str(root),
        "dumpversion": ver,
        "uncompiled_doctrine": doctrine.get("launch_format", {}).get("statement"),
        "organized_field": True,
        "compile_on_launch": False,
    }


def discover_launches(*, force: bool = False) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    policy = doctrine.get("policy") or {}
    max_n = int(policy.get("max_launches") or 500)
    max_depth = int(policy.get("max_depth") or 8)

    if not force and INDEX.is_file():
        cached = _load(INDEX, {})
        if cached.get("items"):
            return cached

    ch = _chamber_mod()
    items: list[dict[str, Any]] = []
    for root in _scan_roots():
        if len(items) >= max_n:
            break
        try:
            for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
                depth = len(Path(dirpath).relative_to(root).parts)
                if depth > max_depth:
                    dirnames.clear()
                    continue
                dirnames[:] = [d for d in dirnames if d not in _SKIP and not d.startswith(".")]
                for name in filenames:
                    if len(items) >= max_n:
                        break
                    if not name.endswith(".launch"):
                        continue
                    lp = Path(dirpath) / name
                    try:
                        if not lp.is_file():
                            continue
                        st = lp.stat()
                    except OSError:
                        continue
                    summary: dict[str, Any] = {
                        "path": str(lp.resolve()),
                        "name": name,
                        "title": lp.stem,
                        "dir": str(lp.parent),
                        "bytes": st.st_size,
                        "mtime": int(st.st_mtime),
                    }
                    if ch:
                        try:
                            doc = ch.load_launch_manifest(lp)
                            summary.update({
                                "title": doc.get("title") or lp.stem,
                                "entry": doc.get("entry"),
                                "runtime": doc.get("runtime"),
                                "chamber_root": doc.get("chamber_root"),
                                "launchable_count": doc.get("launchable_count"),
                                "file_count": doc.get("file_count"),
                                "locked": doc.get("locked"),
                                "uncompiled": doc.get("uncompiled"),
                            })
                        except Exception:
                            pass
                    items.append(summary)
        except OSError:
            continue

    items.sort(key=lambda x: (x.get("title") or "").lower())
    doc = {"scanned": _now(), "count": len(items), "roots": [str(r) for r in _scan_roots()], "items": items}
    _save_atomic(INDEX, doc)
    return doc


def explore(path_str: str) -> dict[str, Any]:
    ch = _chamber_mod()
    if not ch:
        return {"ok": False, "error": "launch_chamber_missing"}
    path = Path(path_str).expanduser().resolve()
    if not path.exists():
        return {"ok": False, "error": "path_missing", "path": str(path)}
    try:
        if path.suffix.lower() == ".launch" and path.is_file():
            manifest = ch.load_launch_manifest(path)
            root = Path(manifest.get("chamber_root") or manifest.get("_resolved_root") or path.parent)
        elif path.is_dir():
            facade = ch.ensure_launch_facade(path, write=False)
            if facade.get("ok"):
                manifest = facade.get("manifest") or {}
                root = path
            else:
                manifest = ch.build_manifest_fast(path)
                root = path
        else:
            return {"ok": False, "error": "not_launch_or_chamber"}
    except Exception as exc:
        return {"ok": False, "error": "explore_failed", "detail": str(exc)[:200]}

    launchables = list(manifest.get("launchables") or [])
    files = list(manifest.get("files") or [])[:80]
    return {
        "ok": True,
        "path": str(path),
        "chamber_root": str(root),
        "manifest": {
            "title": manifest.get("title"),
            "entry": manifest.get("entry"),
            "runtime": manifest.get("runtime"),
            "launchable_count": manifest.get("launchable_count"),
            "file_count": manifest.get("file_count"),
            "locked": manifest.get("locked"),
            "uncompiled": manifest.get("uncompiled"),
            "organized_field": manifest.get("organized_field"),
            "iron_plate": manifest.get("iron_plate"),
        },
        "launchables": launchables,
        "files": files,
        "desktop_actions": (_load(DOCTRINE, {}).get("desktop_actions") or {}).get(".launch", []),
    }


def run_launch(path_str: str, *, args: list[str] | None = None, timeout: int = 180) -> dict[str, Any]:
    ch = _chamber_mod()
    if not ch:
        return {"ok": False, "error": "launch_chamber_missing"}
    path = Path(path_str).expanduser().resolve()
    g16 = _g16_bin()
    env_patch = {
        "QUEEN_LAUNCH_ORGANIZED_FIELD": "1",
        "QUEEN_LAUNCH_COMPILE": "0",
        "GROK16_ROOT": str(_grok16_root()),
        "SG_ROOT": str(SG),
        "NEXUS_INSTALL_ROOT": str(INSTALL),
        "NEXUS_STATE_DIR": str(STATE),
    }
    if g16:
        env_patch["CC"] = str(g16)
        env_patch["CXX"] = str(g16)
        env_patch["G16_BIN"] = str(g16)
    old = {k: os.environ.get(k) for k in env_patch}
    os.environ.update({k: v for k, v in env_patch.items() if v})
    try:
        out = ch.run_chamber(path, args=args or [], timeout=timeout)
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    out["g16"] = g16_probe()
    out["fired_by"] = "field-g16-launch"
    return out


def _settings() -> dict[str, Any]:
    saved = _load(SETTINGS, {})
    return {
        "last_launch": saved.get("last_launch"),
        "last_run_ok": saved.get("last_run_ok"),
    }


def posture(*, rescan: bool = False) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    policy = doctrine.get("policy") or {}
    if rescan or policy.get("discover_on_open", True):
        index = discover_launches(force=rescan)
    else:
        index = _load(INDEX, {}) or discover_launches()
    settings = _settings()
    g16 = g16_probe()
    doc = {
        "schema": "field-g16-launch/v1",
        "ts": _now(),
        "ok": True,
        "doctrine": doctrine.get("title"),
        "motto": doctrine.get("motto"),
        "g16": g16,
        "index": {
            "scanned": index.get("scanned"),
            "count": index.get("count", 0),
            "roots": index.get("roots") or [],
        },
        "settings": settings,
        "routes": doctrine.get("routes") or {},
        "desktop_actions": doctrine.get("desktop_actions") or {},
        "policy": policy,
        "posture": (
            f"G16 Launch — g16={'ready' if g16.get('ok') else 'missing'} · "
            f"{index.get('count', 0)} .launch chambers · uncompiled"
        ),
    }
    _save_atomic(PANEL, doc)
    return doc


def save_settings(patch: dict[str, Any]) -> dict[str, Any]:
    allowed = {"last_launch", "last_run_ok"}
    saved = _load(SETTINGS, {})
    for k, v in patch.items():
        if k in allowed:
            saved[k] = v
    _save_atomic(SETTINGS, saved)
    return posture()


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "status", "posture"):
        rescan = "--rescan" in sys.argv[2:]
        print(json.dumps(posture(rescan=rescan), ensure_ascii=False, indent=2))
        return 0
    if cmd == "discover":
        print(json.dumps(discover_launches(force=True), ensure_ascii=False, indent=2))
        return 0
    if cmd == "probe":
        print(json.dumps(g16_probe(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "explore" and len(sys.argv) > 2:
        print(json.dumps(explore(sys.argv[2]), ensure_ascii=False, indent=2))
        return 0
    if cmd == "run" and len(sys.argv) > 2:
        out = run_launch(sys.argv[2])
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("ok") else 1
    print("usage: field-g16-launch.py [json|discover|probe|explore PATH|run PATH]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())