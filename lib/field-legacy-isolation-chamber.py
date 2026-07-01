#!/usr/bin/env pythong
"""Legacy language isolation chamber — refresh toolchains, run old BASIC/Pascal/VB tests sealed."""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))
from sg_paths import grok16_root

GROK16 = grok16_root()
DOCTRINE = INSTALL / "data" / "field-legacy-isolation-chamber-doctrine.json"
PANEL = STATE / "field-legacy-isolation-chamber-panel.json"
TOOLCHAINS = STATE / "field-legacy-isolation-toolchains.json"
SEED = INSTALL / "data" / "field-program-combinatronic-seed.json"
SCHEMA = "field-legacy-isolation-chamber/v1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _probe_bin(name: str) -> dict[str, Any]:
    path = shutil.which(name)
    if not path:
        return {"name": name, "ready": False, "path": None, "version": None}
    try:
        proc = subprocess.run(
            [path, "--version"],
            capture_output=True,
            text=True,
            timeout=8,
        )
        ver = (proc.stdout or proc.stderr or "").strip().split("\n", 1)[0][:120]
    except (subprocess.SubprocessError, OSError):
        ver = None
    return {"name": name, "ready": True, "path": path, "version": ver}


def _probe_driver(rel_paths: list[str]) -> dict[str, Any]:
    for rel in rel_paths:
        for base in (SG, INSTALL.parent.parent, GROK16):
            p = base / rel
            if p.is_file() and os.access(p, os.X_OK):
                try:
                    proc = subprocess.run(
                        [str(p), "--version"],
                        capture_output=True,
                        text=True,
                        timeout=8,
                    )
                    ver = (proc.stdout or proc.stderr or "").strip().split("\n", 1)[0][:120]
                except (subprocess.SubprocessError, OSError):
                    ver = None
                return {"ready": True, "path": str(p), "version": ver}
    return {"ready": False, "path": None, "version": None}


def probe_toolchains() -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    tc = doctrine.get("toolchains") or {}
    pg_ver = _load(SG / "PythonG" / "data" / "pythong-version.json", {})
    g16 = _load(GROK16 / "data" / "grok16-toolchain.json", {})
    queen_g16 = _load(INSTALL / "Queen" / "data" / "g16-toolchain.json", {})
    pg_tc = _load(SG / "PythonG" / "data" / "pythong-toolchain.json", {})
    return {
        "schema": "field-legacy-isolation-toolchains/v1",
        "updated": _now(),
        "host_gcc": _probe_bin(str(tc.get("host_gcc") or "gcc-14")),
        "host_gxx": _probe_bin(str(tc.get("host_gxx") or "g++-14")),
        "pythong": {
            "target_version": pg_ver.get("pythong_version"),
            "gpy16_version": pg_ver.get("gpy16_version"),
            "manifest_version": (pg_tc.get("toolchain") or {}).get("pythong_version"),
            "driver": _probe_driver(["PythonG/bin/pythong", "Grok16/bin/gpy-16", "GrokPy/bin/gpy-16"]),
        },
        "g16": {
            "g16_version": g16.get("g16_version"),
            "dumpversion": g16.get("dumpversion"),
            "driver": _probe_driver(["Grok16/bin/g16"]),
        },
        "queen_g16_version": queen_g16.get("g16_version"),
        "sync_needed": {
            "pythong_toolchain": (pg_tc.get("toolchain") or {}).get("pythong_version") != pg_ver.get("pythong_version"),
            "queen_g16": queen_g16.get("g16_version") != g16.get("g16_version"),
        },
    }


def refresh_toolchains(*, write: bool = True) -> dict[str, Any]:
    """Pull new toolchain pins from live manifests and sync stale JSON."""
    probe = probe_toolchains()
    pg_ver = _load(SG / "PythonG" / "data" / "pythong-version.json", {})
    g16 = _load(GROK16 / "data" / "grok16-toolchain.json", {})
    updates: list[str] = []
    pg_tc_path = SG / "PythonG" / "data" / "pythong-toolchain.json"
    if probe["sync_needed"]["pythong_toolchain"] and pg_tc_path.is_file():
        doc = _load(pg_tc_path, {})
        toolchain = dict(doc.get("toolchain") or {})
        toolchain["pythong_version"] = pg_ver.get("pythong_version")
        toolchain["gpy16_version"] = pg_ver.get("gpy16_version")
        doc["toolchain"] = toolchain
        doc["updated"] = _now()
        doc["ready_pythong"] = bool(probe["pythong"]["driver"].get("ready"))
        if write:
            _save(pg_tc_path, doc)
        updates.append("pythong-toolchain.json")
    queen_path = INSTALL / "Queen" / "data" / "g16-toolchain.json"
    if probe["sync_needed"]["queen_g16"] and queen_path.is_file() and g16.get("g16_version"):
        qdoc = _load(queen_path, {})
        qdoc["g16_version"] = g16.get("g16_version")
        qdoc["updated"] = _now()
        if write:
            _save(queen_path, qdoc)
        updates.append("queen-g16-toolchain.json")
    out = {
        "schema": SCHEMA,
        "action": "refresh_toolchains",
        "updated": _now(),
        "probe": probe,
        "updates": updates,
        "ok": probe["host_gcc"]["ready"] and probe["pythong"]["driver"]["ready"],
    }
    if write:
        _save(TOOLCHAINS, {"refresh": out, "probe": probe})
    return out


def _legacy_langs() -> list[dict[str, Any]]:
    return list((_load(DOCTRINE, {}).get("legacy_languages") or []))


def _chamber_env(chamber_dir: Path) -> dict[str, str]:
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in frozenset(_load(DOCTRINE, {}).get("isolation", {}).get("env_scrub") or [])
    }
    env.update({
        "NEXUS_INSTALL_ROOT": str(INSTALL),
        "NEXUS_STATE_DIR": str(chamber_dir),
        "SG_ROOT": str(SG),
        "GROK16_ROOT": str(GROK16),
        "FIELD_LEGACY_ISOLATION": "1",
        "FIELD_LEGACY_CHAMBER": str(chamber_dir),
        "CC": shutil.which("gcc-14") or env.get("CC", "gcc"),
        "CXX": shutil.which("g++-14") or env.get("CXX", "g++"),
    })
    return env


def _import_boil():
    spec = importlib.util.spec_from_file_location(
        "field_program_combinatronic", INSTALL / "lib" / "field-program-combinatronic.py"
    )
    if not spec or not spec.loader:
        raise ImportError("field-program-combinatronic.py missing")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _test_boil(lang_id: str, probes: list[dict[str, Any]]) -> dict[str, Any]:
    mod = _import_boil()
    rows: list[dict[str, Any]] = []
    ok = True
    for probe in probes:
        cmd = str(probe.get("command") or "")
        expect = str(probe.get("expect") or "")
        got = mod.boil_command(lang_id, cmd)
        canonical = str(got.get("canonical") or "")
        passed = canonical == expect
        ok = ok and passed
        rows.append({
            "command": cmd,
            "expect": expect,
            "canonical": canonical,
            "ok": passed,
        })
    return {"test": "boil", "ok": ok, "probes": rows}


def _test_seed_pack(lang_id: str) -> dict[str, Any]:
    seed = _load(SEED, {})
    packs = seed.get("language_packs") or {}
    pack = packs.get(lang_id)
    if not pack:
        return {"test": "seed_pack", "ok": False, "error": "pack_missing"}
    cmds = pack.get("commands") or {}
    extends = pack.get("extends")
    return {
        "test": "seed_pack",
        "ok": bool(cmds),
        "command_count": len(cmds),
        "extends": extends,
    }


def _test_manual_book(lang_id: str) -> dict[str, Any]:
    book_id = f"explaining_{lang_id}"
    base = INSTALL / "library" / "dewey" / "000-computer-science" / book_id
    h7c = base / f"{book_id}.h7c"
    book_json = base / "book.json"
    ok = h7c.is_file() or book_json.is_file()
    return {
        "test": "manual_book",
        "ok": ok,
        "book_id": book_id,
        "h7c": h7c.is_file(),
        "book_json": book_json.is_file(),
    }


def run_lang_chamber(lang_spec: dict[str, Any], *, chamber_root: Path | None = None) -> dict[str, Any]:
    """Run all chamber tests for one legacy language inside an isolated state dir."""
    lang_id = str(lang_spec.get("id") or "")
    probes = list(lang_spec.get("boil_probes") or [])
    owned = chamber_root is None
    if chamber_root is None:
        prefix = (_load(DOCTRINE, {}).get("isolation") or {}).get("chamber_prefix") or "legacy-chamber-"
        chamber_root = Path(tempfile.mkdtemp(prefix=prefix))
    tests: list[dict[str, Any]] = []
    try:
        tests.append(_test_boil(lang_id, probes))
        tests.append(_test_seed_pack(lang_id))
        tests.append(_test_manual_book(lang_id))
        ok = all(t.get("ok") for t in tests)
        return {
            "lang": lang_id,
            "era": lang_spec.get("era"),
            "chamber": str(chamber_root),
            "isolated": True,
            "ok": ok,
            "tests": tests,
        }
    finally:
        if owned and chamber_root.is_dir():
            shutil.rmtree(chamber_root, ignore_errors=True)


def _run_lang_subprocess(lang_spec: dict[str, Any]) -> dict[str, Any]:
    """Full subprocess isolation — chamber env scrub + fresh interpreter."""
    prefix = (_load(DOCTRINE, {}).get("isolation") or {}).get("chamber_prefix") or "legacy-chamber-"
    chamber_dir = Path(tempfile.mkdtemp(prefix=prefix))
    lang_id = str(lang_spec.get("id") or "")
    script = str(Path(__file__).resolve())
    env = _chamber_env(chamber_dir)
    try:
        proc = subprocess.run(
            [sys.executable, script, "chamber-one", lang_id],
            capture_output=True,
            text=True,
            timeout=45,
            env=env,
            cwd=str(INSTALL),
        )
        if proc.stdout.strip().startswith("{"):
            return json.loads(proc.stdout)
        return {
            "lang": lang_id,
            "ok": False,
            "isolated": True,
            "error": "bad_output",
            "exit_code": proc.returncode,
            "tail": (proc.stdout or proc.stderr or "")[-300:],
        }
    except (subprocess.TimeoutExpired, OSError) as exc:
        return {"lang": lang_id, "ok": False, "isolated": True, "error": str(exc)[:200]}
    finally:
        shutil.rmtree(chamber_dir, ignore_errors=True)


def run_chamber(*, lang: str = "") -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    langs = _legacy_langs()
    if lang:
        langs = [s for s in langs if str(s.get("id")) == lang.strip().lower()]
        if not langs:
            return {"ok": False, "error": "lang_not_found", "lang": lang}
    use_subprocess = bool((doctrine.get("isolation") or {}).get("subprocess_per_lang", True))
    results: list[dict[str, Any]] = []
    for spec in langs:
        if use_subprocess:
            results.append(_run_lang_subprocess(spec))
        else:
            results.append(run_lang_chamber(spec))
    passed = sum(1 for r in results if r.get("ok"))
    doc = {
        "schema": SCHEMA,
        "action": "run_chamber",
        "updated": _now(),
        "toolchains": probe_toolchains(),
        "languages": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "ok": passed == len(results) and len(results) > 0,
        "results": results,
    }
    _save(PANEL, doc)
    return doc


def verify() -> dict[str, Any]:
    refresh = refresh_toolchains(write=True)
    chamber = run_chamber()
    out = {
        "schema": SCHEMA,
        "action": "verify",
        "updated": _now(),
        "ok": bool(refresh.get("ok")) and bool(chamber.get("ok")),
        "refresh": refresh,
        "chamber": chamber,
    }
    _save(PANEL, out)
    return out


def posture() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "updated": _now(),
        "doctrine": DOCTRINE.name,
        "legacy_count": len(_legacy_langs()),
        "toolchains": _load(TOOLCHAINS, probe_toolchains()),
        "panel": _load(PANEL, {}),
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "status", "panel"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("probe", "toolchains"):
        print(json.dumps(probe_toolchains(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("refresh", "refresh-toolchains"):
        print(json.dumps(refresh_toolchains(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "chamber-one" and len(sys.argv) > 2:
        lang_id = sys.argv[2].strip().lower()
        spec = next((s for s in _legacy_langs() if str(s.get("id")) == lang_id), None)
        if not spec:
            print(json.dumps({"ok": False, "error": "lang_not_found"}))
            return 1
        chamber_dir = Path(os.environ.get("FIELD_LEGACY_CHAMBER") or tempfile.mkdtemp())
        print(json.dumps(run_lang_chamber(spec, chamber_root=chamber_dir), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("chamber", "run"):
        lang = ""
        if "--lang" in sys.argv:
            lang = sys.argv[sys.argv.index("--lang") + 1]
        print(json.dumps(run_chamber(lang=lang), ensure_ascii=False, indent=2))
        return 0
    if cmd == "verify":
        out = verify()
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("ok") else 1
    print(json.dumps({
        "error": "usage",
        "cmds": ["json", "probe", "refresh", "chamber", "verify", "chamber-one LANG"],
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())