#!/usr/bin/env pythong
"""Queen CHIPS / Game Room bridge — retro systems, G16-optimized silicon, Webbrowser surface."""
from __future__ import annotations

import json
import mimetypes
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

QUEEN = Path(__file__).resolve().parents[1]
SG = QUEEN.parent.parent
NEXUS = Path(os.environ.get("NEXUS_INSTALL_ROOT", SG / "NewLatest"))
NEXUS_STATE = Path(os.environ.get("NEXUS_STATE_DIR", NEXUS / ".nexus-state"))
RTX = Path(os.environ.get("AMOURANTHRTX_ROOT", SG / "NewLatest" / "AMOURANTHRTX"))
_SG_PATHS_LIB = Path(__file__).resolve().parents[2] / "lib"
if str(_SG_PATHS_LIB) not in sys.path:
    sys.path.insert(0, str(_SG_PATHS_LIB))
from sg_paths import grok16_root

GROK16 = grok16_root()
MANIFEST = QUEEN / "data" / "queen-game-room.json"
TEST_ROMS = QUEEN / "data" / "queen-test-roms.json"
G16_CHIPS = QUEEN / "data" / "chips-g16-manifest.json"
CHIPS_HPP = RTX / "Navigator" / "engine" / "CHIPS" / "FieldChips.hpp"
NES_CATALOG = NEXUS / "data" / "nes-cartridge-catalog.json"
SESSION_PATH = NEXUS_STATE / "queen-game-room-session.json"
SNAP_DIR = QUEEN / "data" / "snap"
PUMP_LOG = QUEEN / ".queen-emulator-pump.log"
RETRO_SYSTEMS = frozenset({
    "nes", "snes", "genesis", "sms", "a2600", "gameboy", "gamegear",
    "n64", "pce", "neogeo", "msx", "spectrum", "c64", "c64_ultimate", "apple2", "amiga",
})

# Game Room system id → ironclad platform_stack (CHIPS catalog facet)
SYSTEM_PLATFORM_STACK: dict[str, str | None] = {
    "nes": "retro_6502",
    "snes": "console_snes",
    "genesis": "console_genesis",
    "sms": "retro_z80",
    "a2600": "retro_6502",
    "coco": "retro_m68k",
    "coco2": "retro_m68k",
    "coco3": "retro_m68k",
    "c64": "retro_c64",
    "c64_ultimate": "c64_ultimate_fpga",
    "apple2": "retro_6502",
    "msx": "retro_z80",
    "spectrum": "retro_z80",
    "gameboy": "retro_z80",
    "amiga": "amiga_chipset",
    "ps1": "console_ps1",
    "n64": "console_n64",
    "dreamcast": None,
    "dos": "pc_pentium",
    "neogeo": "retro_m68k",
    "saturn": "console_saturn",
    "gamegear": "retro_z80",
    "pce": "retro_6502",
    "3do": "arm_soc_template",
    "jaguar": None,
    "cinema": None,
}

DEWEY_STACK_PAGE: dict[str, dict[str, str]] = {
    "console_genesis": {"slug": "stack-genesis", "title": "Sega Genesis Platform Stack"},
    "console_snes": {"slug": "stack-snes", "title": "Super Nintendo Platform Stack"},
    "console_ps1": {"slug": "stack-ps1", "title": "PlayStation Platform Stack"},
    "console_saturn": {"slug": "stack-saturn", "title": "Sega Saturn Platform Stack"},
    "console_n64": {"slug": "stack-n64", "title": "Nintendo 64 Platform Stack"},
    "retro_c64": {"slug": "stack-retro-c64", "title": "Commodore 64 Classic Platform Stack"},
    "c64_ultimate_fpga": {"slug": "stack-c64-ultimate", "title": "Commodore 64 Ultimate (FPGA)"},
    "retro_6502": {"slug": "stack-retro-6502", "title": "6502 Family Platform Stack"},
    "retro_z80": {"slug": "stack-retro-z80", "title": "Z80 Family Platform Stack"},
    "retro_m68k": {"slug": "stack-retro-m68k", "title": "Motorola 68000 Platform Stack"},
    "amiga_chipset": {"slug": "stack-amiga", "title": "Commodore Amiga Chipset Stack"},
    "pc_pentium": {"slug": "stack-pc-pentium", "title": "PC / DOS Pentium Stack"},
    "arm_soc_template": {"slug": "stack-arm-soc-pmic", "title": "ARM SoC PMIC Platform Stack"},
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _chips_tree_stats() -> dict[str, Any]:
    chips = RTX / "Navigator" / "engine" / "CHIPS"
    if not chips.is_dir():
        return {"present": False, "headers": 0}
    headers = list(chips.rglob("*.hpp"))
    platforms = [d.name for d in chips.iterdir() if d.is_dir()]
    return {
        "present": True,
        "root": str(chips),
        "headers": len(headers),
        "platforms": sorted(platforms),
        "aggregator": str(CHIPS_HPP) if CHIPS_HPP.is_file() else None,
    }


def _engine_binary() -> Path | None:
    """RTX engine for CHIPS emulation — AMOURANTHRTX or queen-browser build."""
    for p in (
        RTX / "build" / "bin" / "Linux" / "AMOURANTHRTX",
        RTX / "build-release" / "bin" / "Linux" / "AMOURANTHRTX",
        RTX / "build" / "bin" / "Linux" / "queen-browser",
        RTX / "build-release" / "bin" / "Linux" / "queen-browser",
        QUEEN / "build" / "rtx" / "bin" / "Linux" / "queen-browser",
        SG / "AMOURANTHRTX" / "build" / "bin" / "Linux" / "AMOURANTHRTX",
    ):
        if p.is_file():
            return p.resolve()
    return None


def _rtx_binary() -> Path | None:
    return _engine_binary()


def _save_session(doc: dict[str, Any]) -> None:
    SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = SESSION_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(SESSION_PATH)


def _load_session() -> dict[str, Any]:
    return _load(SESSION_PATH)


def _pid_alive(pid: int | None) -> bool:
    if not pid or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _stop_session() -> dict[str, Any]:
    sess = _load_session()
    for key in ("pump_pid", "engine_pid"):
        pid = int(sess.get(key) or 0)
        if _pid_alive(pid):
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                pass
    sess["stop"] = True
    sess["stopped_at"] = _now()
    _save_session(sess)
    return {"ok": True, "stopped": True, "session": sess}


def _test_roms_doc() -> dict[str, Any]:
    return _load(TEST_ROMS)


def _system_rom_spec(system: str) -> dict[str, Any]:
    doc = _test_roms_doc()
    return (doc.get("systems") or {}).get(system) or {}


def _rom_probe_dirs(system: str = "nes") -> list[Path]:
    bases = [
        QUEEN / "build" / "rtx" / "bin" / "Kilroy" / "assets" / "dos" / "incoming",
        RTX / "assets" / "dos" / "incoming",
        SG / "AMOURANTHRTX" / "assets" / "dos" / "incoming",
        NEXUS / "assets" / "dos" / "incoming",
    ]
    dirs: list[Path] = []
    seen: set[str] = set()
    for base in bases:
        for sub in (system, "nes" if system == "nes" else None):
            if not sub:
                continue
            d = base / sub
            key = str(d)
            if key in seen:
                continue
            seen.add(key)
            if d.is_dir():
                dirs.append(d.resolve())
    if system == "nes":
        lib = NEXUS / "library" / "dewey" / "700-arts" / "games" / "nes"
        if lib.is_dir():
            dirs.append(lib.resolve())
    return dirs


def resolve_test_rom(system: str) -> dict[str, Any]:
    """Best test ROM path for system — canonical filename, fallback, or first match."""
    spec = _system_rom_spec(system)
    exts = list(spec.get("extensions") or [])
    if system == "nes" and not exts:
        exts = [".nes", ".NES"]
    primary = str(spec.get("filename") or "").strip()
    fallback = str(spec.get("fallback") or "").strip()
    for name in (primary, fallback):
        if not name:
            continue
        for d in _rom_probe_dirs(system):
            hit = d / name
            if hit.is_file():
                return {
                    "ok": True,
                    "system": system,
                    "path": str(hit.resolve()),
                    "filename": hit.name,
                    "title": spec.get("title") or hit.stem,
                    "kind": spec.get("kind") or "test_rom",
                    "source": "canonical" if name == primary else "fallback",
                }
    if exts:
        for d in _rom_probe_dirs(system):
            for ext in exts:
                hits = sorted(d.glob(f"*{ext}"))
                if hits:
                    p = hits[0]
                    return {
                        "ok": True,
                        "system": system,
                        "path": str(p.resolve()),
                        "filename": p.name,
                        "title": spec.get("title") or p.stem,
                        "kind": "probe",
                        "source": "first_match",
                    }
    return {
        "ok": False,
        "system": system,
        "title": spec.get("title"),
        "expected": spec.get("filename"),
        "probe_dirs": [str(d) for d in _rom_probe_dirs(system)],
        "hint": f"Run Queen/scripts/fetch-queen-test-roms.py or place ROM in assets/dos/incoming/{system}/",
    }


def _catalog_rom_entry(*, nes_id: str | None = None, title: str | None = None) -> dict[str, Any] | None:
    cat = _load(NES_CATALOG)
    entries = cat.get("entries") or []
    if nes_id:
        for e in entries:
            if str(e.get("id") or "") == nes_id and e.get("rom"):
                return e
    if title:
        low = title.lower().strip()
        for e in entries:
            if str(e.get("title") or "").lower().strip() == low and e.get("rom"):
                return e
    for e in entries:
        if e.get("rom"):
            return e
    return None


def _resolve_rom_path(body: dict[str, Any], system: str) -> tuple[Path | None, str | None]:
    """Resolve playable ROM — explicit path, catalog id, or probe dirs."""
    raw = (
        body.get("rom_path")
        or body.get("rom")
        or (body.get("entry") or {}).get("rom", {}).get("path")
        if isinstance(body.get("entry"), dict)
        else None
    )
    if isinstance(raw, dict):
        raw = raw.get("path")
    if raw:
        p = Path(str(raw)).expanduser()
        if not p.is_absolute():
            for base in (NEXUS, SG / "NewLatest", QUEEN, RTX):
                cand = (base / p).resolve()
                if cand.is_file():
                    return cand, None
        if p.is_file():
            return p.resolve(), None

    nes_id = str(body.get("nes_id") or body.get("game_id") or body.get("catalog_id") or "").strip()
    title = str(body.get("title") or "").strip()
    entry = _catalog_rom_entry(nes_id=nes_id or None, title=title or None)
    if entry:
        rom = entry.get("rom") or {}
        for candidate in (rom.get("path"), rom.get("filename")):
            if not candidate:
                continue
            p = Path(str(candidate)).expanduser()
            if p.is_file():
                return p.resolve(), str(entry.get("id"))
            for d in _rom_probe_dirs(system):
                hit = d / Path(str(candidate)).name
                if hit.is_file():
                    return hit.resolve(), str(entry.get("id"))

    stem = str(body.get("rom_stem") or body.get("rom_name") or "").strip().lower()
    if stem:
        spec = _system_rom_spec(system)
        exts = spec.get("extensions") or ([".nes", ".NES"] if system == "nes" else [".bin"])
        for d in _rom_probe_dirs(system):
            for ext in exts:
                hit = d / f"{stem}{ext}"
                if hit.is_file():
                    return hit.resolve(), nes_id or None

    test = resolve_test_rom(system)
    if test.get("ok") and test.get("path"):
        return Path(str(test["path"])).resolve(), nes_id or None
    return None, nes_id or None


def _ppm_to_png(ppm: Path, png: Path) -> bool:
    if not ppm.is_file():
        return False
    try:
        from PIL import Image  # noqa: WPS433

        data = ppm.read_bytes()
        header, _, rest = data.partition(b"\n255\n")
        lines = header.decode("ascii", errors="ignore").strip().split("\n")
        if len(lines) < 3:
            return False
        w, h = map(int, lines[1].split())
        img = Image.frombytes("RGB", (w, h), rest[: w * h * 3])
        png.parent.mkdir(parents=True, exist_ok=True)
        img.save(png)
        return True
    except Exception:
        pass
    if subprocess.run(
        ["convert", str(ppm), str(png)],
        capture_output=True,
        timeout=30,
        check=False,
    ).returncode == 0:
        return png.is_file()
    return False


def _capture_nes_frame(engine: Path, rom_path: Path, *, snap_ppm: Path, snap_png: Path) -> dict[str, Any]:
    snap_ppm.unlink(missing_ok=True)
    env = {
        **os.environ,
        "AMOURANTHRTX_HEADLESS": "1",
        "AMOURANTHRTX_NO_VALIDATION": "1",
        "VK_INSTANCE_LAYERS": "",
        "QUEEN_SKIP_RTX_BOOT": "0",
        "QUEEN_WEB_SHELL": "0",
        "QUEEN_BROWSER_BUILD": "0",
        "AMOURANTHRTX_NES_TEST": "1",
        "AMOURANTHRTX_BENCH_W": "640",
        "AMOURANTHRTX_BENCH_H": "480",
        "AMOURANTHRTX_MAX_FRAMES": "360",
        "AMOURANTHRTX_NES_FB_SNAP": str(snap_ppm),
        "AMOURANTHRTX_NES_FB_FRAME": "240",
        "AMOURANTHRTX_NES_ROM": str(rom_path),
        "NEXUS_INSTALL_ROOT": str(NEXUS),
        "QUEEN_ROOT": str(QUEEN),
        "SG_ROOT": str(SG),
        "AMOURANTHRTX_ROOT": str(RTX),
    }
    try:
        proc = subprocess.run(
            [str(engine)],
            cwd=str(engine.parent),
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": str(exc)}
    log = (proc.stderr or "") + (proc.stdout or "")
    ok = snap_ppm.is_file()
    if ok:
        _ppm_to_png(snap_ppm, snap_png)
    return {
        "ok": ok,
        "returncode": proc.returncode,
        "snap": str(snap_ppm) if ok else None,
        "image": str(snap_png) if snap_png.is_file() else None,
        "launched": "[NES_QA] launched" in log,
        "log_tail": log[-800:],
    }


def emulator_pump_loop(system: str, rom_path: str) -> int:
    """Background frame pump — repeated headless captures for web canvas."""
    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    engine = _engine_binary()
    rom = Path(rom_path)
    if not engine or not rom.is_file():
        return 1
    ppm = SNAP_DIR / "nes_fb.ppm"
    png = SNAP_DIR / "nes_fb.png"
    sess = _load_session()
    sess["pump_pid"] = os.getpid()
    sess["pump_started"] = _now()
    sess["stop"] = False
    _save_session(sess)
    log_f = open(PUMP_LOG, "a", encoding="utf-8")
    log_f.write(f"\n# pump start {system} {rom} pid={os.getpid()} {_now()}\n")
    while True:
        sess = _load_session()
        if sess.get("stop"):
            break
        if sess.get("pump_pid") not in (None, os.getpid()) and not _pid_alive(int(sess.get("pump_pid") or 0)):
            break
        out = _capture_nes_frame(engine, rom, snap_ppm=ppm, snap_png=png)
        sess = _load_session()
        sess["last_capture"] = _now()
        sess["last_capture_ok"] = out.get("ok")
        sess["programs_canvas_ready"] = bool(out.get("ok") and png.is_file())
        sess["image"] = str(png) if png.is_file() else None
        _save_session(sess)
        log_f.write(f"# capture ok={out.get('ok')} rc={out.get('returncode')} {_now()}\n")
        log_f.flush()
        time.sleep(1.5)
    log_f.write(f"# pump stop pid={os.getpid()} {_now()}\n")
    log_f.close()
    return 0


def launch_emulator(
    *,
    system: str,
    body: dict[str, Any] | None = None,
    host_cpu: str = "native",
    memory: str = "stock",
) -> dict[str, Any]:
    """Spawn CHIPS emulator frame pump for Queen Game Room web surface."""
    body = body or {}
    _stop_session()
    engine = _engine_binary()
    if not engine:
        return {
            "ok": False,
            "error": "engine_missing",
            "hint": "Build queen-browser: Queen/scripts/g16-build.sh or AMOURANTHRTX ./kilroy.sh run",
        }
    rom_path, catalog_id = _resolve_rom_path(body, system)
    if not rom_path:
        return {
            "ok": False,
            "error": "rom_missing",
            "system": system,
            "hint": "Place a .nes ROM under assets/dos/incoming/nes/ or pass rom_path",
            "probe_dirs": [str(d) for d in _rom_probe_dirs()],
        }

    log_f = open(PUMP_LOG, "a", encoding="utf-8")
    try:
        proc = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "pump", system, str(rom_path)],
            cwd=str(QUEEN),
            start_new_session=True,
            stdout=log_f,
            stderr=subprocess.STDOUT,
            env={
                **os.environ,
                "NEXUS_INSTALL_ROOT": str(NEXUS),
                "NEXUS_STATE_DIR": str(NEXUS_STATE),
                "QUEEN_ROOT": str(QUEEN),
                "SG_ROOT": str(SG),
                "AMOURANTHRTX_ROOT": str(RTX),
            },
        )
    except OSError as exc:
        return {"ok": False, "error": "spawn_failed", "detail": str(exc)}

    session = {
        "schema": "queen-game-room-session/v1",
        "started": _now(),
        "system": system,
        "rom_path": str(rom_path),
        "catalog_id": catalog_id,
        "engine": str(engine),
        "pump_pid": proc.pid,
        "host_cpu": host_cpu,
        "memory": memory,
        "stop": False,
        "surface": "webbrowser",
        "spawn_rtx": True,
        "spawned": True,
    }
    _save_session(session)
    return {
        "ok": True,
        "mode": "chips",
        "surface": "webbrowser",
        "spawned": True,
        "spawn_rtx": True,
        "system_id": system,
        "rom_path": str(rom_path),
        "catalog_id": catalog_id,
        "engine": str(engine),
        "pump_pid": proc.pid,
        "framebuffer_url": "/api/game-room/fb/image",
        "message": f"CHIPS {system.upper()} pump started — {rom_path.name}",
    }


def _queen_process_running() -> bool:
    sess = _load_session()
    if _pid_alive(int(sess.get("pump_pid") or 0)):
        return True
    try:
        r = subprocess.run(
            ["pgrep", "-f", "queen-chips.py pump"],
            capture_output=True,
            timeout=3,
        )
        return r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _fb_snap_paths() -> list[Path]:
    names = ("nes_fb.ppm", "snap.ppm", "game_room_fb.ppm", "framebuffer.ppm")
    dirs = (
        RTX / "build" / "snap",
        RTX / "build",
        RTX / "cache" / "snap",
        QUEEN / "data" / "snap",
    )
    out: list[Path] = []
    for d in dirs:
        for n in names:
            p = d / n
            if p.is_file():
                out.append(p.resolve())
    return out


def _g16_status() -> dict[str, Any]:
    g16 = GROK16 / "bin" / "g16"
    manifest = _load(G16_CHIPS)
    tc = _load(GROK16 / "data" / "grok16-toolchain.json")
    return {
        "ready": g16.is_file(),
        "g16": str(g16) if g16.is_file() else None,
        "profile": manifest.get("profile") or "field_opt",
        "version": tc.get("version") or "16.1.1",
        "chips_optimizations": manifest.get("hot_paths") or [],
    }


def _qa_hint() -> dict[str, Any]:
    qa = RTX / "scripts" / "qa_nes_cpu_test.cpp"
    linux_sh = RTX / "linux.sh"
    return {
        "qa_nes": qa.is_file(),
        "linux_sh": linux_sh.is_file(),
        "launch_cmd": str(linux_sh) + " run" if linux_sh.is_file() else None,
    }


def _chip_battery_script() -> Path:
    for root in (NEXUS, SG / "NewLatest"):
        p = root / "lib" / "field-chip-battery.py"
        if p.is_file():
            return p
    return NEXUS / "lib" / "field-chip-battery.py"


def _chip_battery_env() -> dict[str, str]:
    return {
        **os.environ,
        "SG_ROOT": str(SG),
        "QUEEN_ROOT": str(QUEEN),
        "NEXUS_INSTALL_ROOT": str(NEXUS),
        "NEXUS_STATE_DIR": str(NEXUS_STATE),
        "GROK16_ROOT": str(GROK16),
    }


def combinatronic_status(*, refresh: bool = False) -> dict[str, Any]:
    script = _chip_battery_script()
    if not script.is_file():
        return {
            "schema": "field-chips-combinatronic/v1",
            "ok": False,
            "error": "chip_battery_missing",
            "path": str(script),
        }
    args = ["combinatronic"]
    if refresh:
        args.append("--refresh")
    try:
        proc = subprocess.run(
            [sys.executable, str(script), *args],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(QUEEN),
            env=_chip_battery_env(),
        )
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {"schema": "field-chips-combinatronic/v1", "ok": False, "error": "bad_json"}
    except subprocess.TimeoutExpired:
        return {"schema": "field-chips-combinatronic/v1", "ok": False, "error": "timeout"}


def chip_battery_panel() -> dict[str, Any]:
    script = _chip_battery_script()
    if not script.is_file():
        return {"schema": "field-chip-battery-panel/v1", "ok": False, "error": "chip_battery_missing"}
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "json"],
            capture_output=True,
            text=True,
            timeout=90,
            cwd=str(QUEEN),
            env=_chip_battery_env(),
        )
        return json.loads(proc.stdout or "{}")
    except (json.JSONDecodeError, subprocess.TimeoutExpired):
        return {"schema": "field-chip-battery-panel/v1", "ok": False, "error": "chip_battery_failed"}


def _catalog_py() -> Path:
    return NEXUS / "lib" / "field-chips-catalog.py"


def _run_catalog(*args: str, timeout: int = 60) -> dict[str, Any]:
    script = _catalog_py()
    if not script.is_file():
        return {"ok": False, "error": "field-chips-catalog missing"}
    try:
        proc = subprocess.run(
            [sys.executable, str(script), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(NEXUS),
        )
        return json.loads(proc.stdout or "{}")
    except (json.JSONDecodeError, subprocess.TimeoutExpired):
        return {"ok": False, "error": "catalog_failed"}


def _device_image_url(system_id: str) -> str:
    for base in (
        NEXUS / "library" / "assets" / "devices",
        NEXUS / "data" / "combinatronic-visuals" / "devices",
    ):
        if (base / f"{system_id}.png").is_file():
            if base.name == "devices" and "library" in str(base):
                return f"/library/assets/devices/{system_id}.png"
            return f"/data/combinatronic-visuals/devices/{system_id}.png"
    return f"/library/assets/devices/{system_id}.png"


def _chip_summary(row: dict[str, Any]) -> dict[str, Any]:
    cid = str(row.get("id") or "")
    return {
        "id": cid,
        "label": str(row.get("label") or cid),
        "kind": row.get("kind"),
        "vendor": row.get("vendor"),
        "platform_stack": row.get("platform_stack"),
        "thumb_url": row.get("thumb_url") or "/world/assets/combinatronic/chips/generic_die.png",
        "detail_url": f"/world/queen-chips-detail.html?id={cid}",
    }


def system_emulator_info(system_id: str) -> dict[str, Any]:
    """Aggregate Game Room system + device visual + CHIPS catalog stack."""
    room = _load(MANIFEST)
    systems = {str(s.get("id")): s for s in room.get("systems") or []}
    sys_row = systems.get(system_id)
    if not sys_row:
        return {"schema": "queen-emulator-system-info/v1", "ok": False, "error": "unknown_system", "system_id": system_id}

    chip_id = f"system_{system_id}"
    platform_stack = SYSTEM_PLATFORM_STACK.get(system_id)
    device_image = _device_image_url(system_id)

    catalog_path = str(sys_row.get("catalog") or f"004-computers/{system_id}")
    dewey_book: dict[str, Any] = {}
    book_json = NEXUS / "library" / "dewey" / catalog_path / "book.json"
    if book_json.is_file():
        try:
            dewey_book = json.loads(book_json.read_text(encoding="utf-8"))
            if dewey_book.get("cover"):
                device_image = str(dewey_book["cover"])
        except (OSError, json.JSONDecodeError):
            pass

    cat_doc = _run_catalog("catalog")
    entries = list(cat_doc.get("entries") or [])
    by_id = {str(e.get("id")): e for e in entries if e.get("id")}

    system_chip = by_id.get(chip_id)
    if not system_chip:
        detail = _run_catalog("detail", chip_id)
        if detail and detail.get("id"):
            system_chip = detail

    companion_ids: list[str] = []
    if system_chip:
        companion_ids = list(system_chip.get("always_with") or [])

    stack_chips: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _add_chip(row: dict[str, Any] | None) -> None:
        if not row:
            return
        cid = str(row.get("id") or "")
        if not cid or cid in seen:
            return
        seen.add(cid)
        stack_chips.append(_chip_summary(row))

    _add_chip(system_chip)
    for cid in companion_ids:
        _add_chip(by_id.get(cid))

    if platform_stack:
        for row in entries:
            if str(row.get("platform_stack") or "") == platform_stack:
                _add_chip(row)
    for row in entries:
        platforms = row.get("platforms") or []
        if system_id in platforms or sys_row.get("app_id", "").lower() in {str(p).lower() for p in platforms}:
            _add_chip(row)

    stack_page: dict[str, Any] | None = None
    if platform_stack and platform_stack in DEWEY_STACK_PAGE:
        spec = DEWEY_STACK_PAGE[platform_stack]
        page_path = (
            NEXUS / "library" / "dewey" / "621-computer-engineering" / "chips-catalog"
            / "ironclad-chips-catalog" / "pages" / f"page-031-{spec['slug']}.json"
        )
        for candidate in sorted(
            (NEXUS / "library" / "dewey" / "621-computer-engineering" / "chips-catalog"
             / "ironclad-chips-catalog" / "pages").glob(f"page-*-{spec['slug']}.json")
        ) if (NEXUS / "library" / "dewey" / "621-computer-engineering" / "chips-catalog"
              / "ironclad-chips-catalog" / "pages").is_dir() else []:
            page_path = candidate
            break
        if page_path.is_file():
            try:
                stack_page = json.loads(page_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                stack_page = None

    catalog_stack_url = (
        f"/world/queen-chips-catalog.html?stack={platform_stack}" if platform_stack else "/world/queen-chips-catalog.html"
    )

    return {
        "schema": "queen-emulator-system-info/v1",
        "ok": True,
        "updated": _now(),
        "system_id": system_id,
        "system": dict(sys_row),
        "chip_id": chip_id,
        "platform_stack": platform_stack,
        "platform_stack_label": (DEWEY_STACK_PAGE.get(platform_stack or "") or {}).get("title"),
        "device_image": device_image,
        "device_image_source": "field-device-visuals",
        "dewey_book": dewey_book,
        "system_chip": _chip_summary(system_chip) if system_chip else None,
        "stack_chips": stack_chips,
        "stack_chip_count": len(stack_chips),
        "stack_page": stack_page,
        "urls": {
            "info": f"/world/queen-system-info.html?system={system_id}",
            "game_room": f"/world/queen-game-room.html?system={system_id}",
            "catalog_stack": catalog_stack_url,
            "chip_detail": f"/world/queen-chips-detail.html?id={chip_id}",
            "chips_catalog": "/world/queen-chips-catalog.html",
            "dewey_device": f"/library/dewey/{catalog_path}/",
            "dewey_catalog": catalog_path,
        },
    }


def game_room_status() -> dict[str, Any]:
    room = _load(MANIFEST)
    comb = combinatronic_status()
    pred = comb.get("path_prediction") or {}
    enriched_systems = []
    for row in room.get("systems") or []:
        sid = str(row.get("id") or "")
        copy = dict(row)
        copy["info_url"] = f"/world/queen-system-info.html?system={sid}"
        copy["catalog"] = str(row.get("catalog") or f"004-computers/{sid}")
        copy["catalog_url"] = f"/library/dewey/{copy['catalog']}/"
        copy["device_image"] = _device_image_url(sid)
        copy["platform_stack"] = SYSTEM_PLATFORM_STACK.get(sid)
        copy["chip_id"] = f"system_{sid}"
        enriched_systems.append(copy)
    return {
        "schema": "queen-chips/v1",
        "updated": _now(),
        "title": room.get("title"),
        "motto": room.get("motto"),
        "systems": enriched_systems,
        "host_cpus": room.get("host_cpus") or [],
        "memory_profiles": room.get("memory_profiles") or [],
        "movie_formats": room.get("movie_formats") or [],
        "aspect": room.get("aspect") or {},
        "chips": _chips_tree_stats(),
        "grok16": _g16_status(),
        "surface": "webbrowser",
        "web_surface": True,
        "game_room_url": "/world/queen-game-room.html",
        "chips_cores_url": "/world/queen-chips-cores.html",
        "combinatronic_url": "/world/queen-chips-cores.html#combinatronic",
        "combinatronic": comb,
        "chip_battery": {
            "counts": comb.get("counts"),
            "leaf_count": comb.get("leaf_count"),
            "path_total_pct": pred.get("total_pct"),
            "narrow_band_width": (comb.get("line_safety") or {}).get("narrow_band_width"),
            "band_count": len(pred.get("bands") or []),
        },
        "rtx": {
            "root": str(RTX),
            "present": RTX.is_dir(),
            "desktop_comp_shader": False,
            "note": "CHIPS/cores route through Queen Webbrowser — no RTX comp shader boot",
        },
        "qa": _qa_hint(),
        "test_roms": {
            "manifest": str(TEST_ROMS),
            "fetch_script": str(QUEEN / "scripts" / "fetch-queen-test-roms.py"),
        },
        "layout": {"theater_pct": 75, "arcade_pct": 25, "theme": "movie_theater_arcade"},
        "selected": {
            "system": "nes",
            "host_cpu": "native",
            "memory": "stock",
            "aspect": "16/9",
        },
    }


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower()
    if action in ("status", "json"):
        return {"ok": True, **game_room_status()}

    system = str(body.get("system") or body.get("system_id") or "nes").strip()

    if action in ("system", "system_info", "info"):
        return system_emulator_info(system)

    status = game_room_status()
    host_cpu = str(body.get("host_cpu") or body.get("cpu") or "native").strip()
    memory = str(body.get("memory") or "stock").strip()
    aspect = str(body.get("aspect") or "16/9").strip()

    if action in ("configure", "select"):
        status["selected"] = {"system": system, "host_cpu": host_cpu, "memory": memory, "aspect": aspect}
        systems = {s["id"]: s for s in status.get("systems") or []}
        sel = systems.get(system)
        if not sel:
            return {"ok": False, "error": "unknown_system", "systems": list(systems.keys())}
        test = resolve_test_rom(system)
        return {
            "ok": True,
            "configured": status["selected"],
            "system": sel,
            "test_rom": test,
            "grok16_profile": status["grok16"].get("profile"),
            "message": f"Game Room armed: {sel.get('label')} · CPU {host_cpu} · {memory} RAM",
        }

    if action in ("launch", "run", "start"):
        systems = {s["id"]: s for s in status.get("systems") or []}
        sel = systems.get(system)
        if not sel:
            return {"ok": False, "error": "unknown_system"}
        if sel.get("movie"):
            return {
                "ok": True,
                "mode": "cinema",
                "system": sel,
                "message": "Cinema mode — load a movie file in the Game Room theater",
            }
        spawn = bool(body.get("spawn_rtx", body.get("spawn", True)))
        if spawn and system in RETRO_SYSTEMS:
            test = resolve_test_rom(system)
            body = {**body, "test_rom": test}
            out = launch_emulator(system=system, body=body, host_cpu=host_cpu, memory=memory)
            out["test_rom"] = test
            out["system"] = sel
            out["host_cpu"] = host_cpu
            out["memory"] = memory
            out["url"] = "/world/queen-game-room.html"
            out["grok16_profile"] = status["grok16"].get("profile")
            out["combinatronic"] = status.get("combinatronic")
            return out
        return {
            "ok": True,
            "mode": "chips",
            "surface": "webbrowser",
            "spawned": False,
            "spawn_rtx": False,
            "system": sel,
            "host_cpu": host_cpu,
            "memory": memory,
            "url": "/world/queen-game-room.html",
            "grok16_profile": status["grok16"].get("profile"),
            "message": f"{sel.get('label')} configured — pass spawn_rtx=true to start CHIPS pump",
        }

    if action in ("stop", "halt", "shutdown"):
        stopped = _stop_session()
        stopped["message"] = "Game Room emulator pump stopped"
        return stopped

    if action in ("rebuild", "rebuild_chips", "g16_rebuild"):
        g16 = GROK16 / "bin" / "g16"
        script = RTX / "linux.sh"
        cmd = (
            f"cd {RTX} && G16_PREFIX={GROK16} QUEEN_BROWSER_BUILD=1 "
            f"cmake -B build -DQUEEN_BROWSER_BUILD=ON && cmake --build build -j$(nproc)"
        )
        if body.get("run"):
            try:
                subprocess.Popen(
                    ["bash", "-lc", cmd],
                    cwd=str(RTX),
                    start_new_session=True,
                    stdout=open(QUEEN / ".queen-chips-rebuild.log", "a", encoding="utf-8"),
                    stderr=subprocess.STDOUT,
                )
                return {"ok": True, "started": True, "cmd": cmd, "log": str(QUEEN / ".queen-chips-rebuild.log")}
            except OSError as e:
                return {"ok": False, "error": "rebuild_start_failed", "detail": str(e)}
        return {
            "ok": True,
            "cmd": cmd,
            "g16_ready": g16.is_file(),
            "linux_sh": script.is_file(),
            "profile": _load(G16_CHIPS).get("profile") or "field_opt",
            "message": "POST action=rebuild run=true to start G16 CHIPS rebuild in background",
        }

    if action in ("fullscreen", "aspect"):
        return {"ok": True, "aspect": aspect, "fullscreen": body.get("fullscreen", True)}

    if action in ("combinatronic", "chips_combinatronic", "chip_battery", "chip-battery"):
        refresh = bool(body.get("refresh"))
        panel = combinatronic_status(refresh=refresh) if action != "chip-battery" else chip_battery_panel()
        return {"ok": True, **panel}

    return {
        "ok": False,
        "error": "unknown_action",
        "actions": ["status", "configure", "launch", "stop", "rebuild", "combinatronic", "chip_battery"],
    }


def _fb_image_path() -> Path | None:
    rtx = RTX
    for name in ("nes_fb.png", "game_room_fb.png", "framebuffer.png", "snap.png"):
        for d in (rtx / "build" / "snap", rtx / "build", rtx / "cache" / "snap", QUEEN / "data" / "snap"):
            p = d / name
            if p.is_file():
                return p.resolve()
    return None


def framebuffer_status() -> dict[str, Any]:
    snaps = _fb_snap_paths()
    img = _fb_image_path()
    sess = _load_session()
    running = _queen_process_running()
    canvas_ready = bool(img and img.is_file()) or bool(sess.get("programs_canvas_ready"))
    if running and not canvas_ready:
        canvas_ready = bool(img and img.is_file())
    out: dict[str, Any] = {
        "schema": "queen-game-room-fb/v1",
        "updated": _now(),
        "surface": "webbrowser",
        "web_surface": True,
        "desktop_comp_shader": False,
        "ready": running or canvas_ready,
        "programs_canvas_ready": canvas_ready,
        "spawned": bool(sess.get("spawned")) or running,
        "spawn_rtx": bool(sess.get("spawn_rtx")),
        "queen_process": running,
        "pump_pid": sess.get("pump_pid"),
        "system": sess.get("system"),
        "rom_path": sess.get("rom_path"),
        "last_capture": sess.get("last_capture"),
        "last_capture_ok": sess.get("last_capture_ok"),
        "snap": str(snaps[0]) if snaps else None,
        "image": str(img) if img else sess.get("image"),
    }
    if img or sess.get("image"):
        out["image_url"] = "/api/game-room/fb/image"
    return out


def framebuffer_image_bytes() -> tuple[bytes, str] | None:
    img = _fb_image_path()
    if not img:
        return None
    mime = mimetypes.guess_type(str(img))[0] or "application/octet-stream"
    try:
        return img.read_bytes(), mime
    except OSError:
        return None


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "pump":
        system = sys.argv[2] if len(sys.argv) > 2 else "nes"
        rom = sys.argv[3] if len(sys.argv) > 3 else ""
        if not rom:
            print(json.dumps({"ok": False, "error": "rom_required"}))
            return 1
        return emulator_pump_loop(system, rom)
    if len(sys.argv) > 1 and sys.argv[1] == "fb":
        print(json.dumps(framebuffer_status(), ensure_ascii=False))
        return 0
    if len(sys.argv) > 1 and sys.argv[1] in ("combinatronic", "chip-battery"):
        refresh = "--refresh" in sys.argv[2:]
        if sys.argv[1] == "chip-battery":
            print(json.dumps(chip_battery_panel(), ensure_ascii=False))
        else:
            print(json.dumps(combinatronic_status(refresh=refresh), ensure_ascii=False))
        return 0
    if len(sys.argv) > 1 and sys.argv[1] == "system":
        sid = sys.argv[2] if len(sys.argv) > 2 else "nes"
        print(json.dumps(system_emulator_info(sid), ensure_ascii=False))
        return 0
    if len(sys.argv) > 1 and sys.argv[1] == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}))
            return 1
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    print(json.dumps(game_room_status(), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())