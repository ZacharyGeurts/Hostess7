#!/usr/bin/env pythong
"""Ironclad-rooted chip combinatorics — every die a leaf off Ironclad truth, no battery."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))
from sg_paths import grok16_root

GROK16 = grok16_root()
DOCTRINE = INSTALL / "data" / "field-ironclad-chips-combinatorics-doctrine.json"
SEED = INSTALL / "data" / "field-chip-battery-seed.json"
WORLD_SEED = INSTALL / "data" / "field-world-chips-seed.json"
SEMICONDUCTOR_WORLD_SEED = INSTALL / "data" / "field-semiconductor-world-seed.json"
COMPANION_SEED = INSTALL / "data" / "field-cpu-companion-seed.json"
PATH_PREDICT_SEED = INSTALL / "data" / "field-chip-path-predict-seed.json"
MAME_CACHE = INSTALL / "data" / "field-chip-battery-mame-cache.json"
CATALOG = INSTALL / "data" / "field-combinatronic-chip-catalog.json"
PANEL = STATE / "field-ironclad-chips-combinatorics-panel.json"
COMBINATORICS = STATE / "field-ironclad-chips-combinatorics.json"
LOW_POWER = os.environ.get("NEXUS_IRONCLAD_CHIPS_LOW_POWER", os.environ.get("NEXUS_CHIP_BATTERY_LOW_POWER", "1")) == "1"
MAME_LIVE = os.environ.get("NEXUS_IRONCLAD_CHIPS_MAME_LIVE", os.environ.get("NEXUS_CHIP_BATTERY_MAME_LIVE", "0")) == "1"
LEAF_PREFIX = "chip"
FACET = "ironclad_chips"


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        _p = INSTALL / "lib" / "sovereign-clock.py"
        _s = importlib.util.spec_from_file_location("sovereign_clock", _p)
        if not _s or not _s.loader:
            raise ImportError("sovereign-clock.py missing")
        _SOVEREIGN_CLOCK_MOD = importlib.util.module_from_spec(_s)
        _s.loader.exec_module(_SOVEREIGN_CLOCK_MOD)
    return _SOVEREIGN_CLOCK_MOD.utc_z()


_SOVEREIGN_CLOCK_MOD = None
IRONCLAD_CITE = "ironclad:chips:3"


def _ironclad_truth() -> dict[str, Any]:
    """Ironclad connected throughout — truth plate grounds every chip sort."""
    imm = _load(STATE / "ironclad-immediate.json", {})
    if not imm.get("schema"):
        ic = INSTALL / "lib" / "ironclad-immediate.py"
        if ic.is_file():
            try:
                spec = importlib.util.spec_from_file_location("ic_chip_bat", ic)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    if hasattr(mod, "immediate_slice"):
                        imm = mod.immediate_slice()
            except Exception:
                pass
    pts = imm.get("plate_to_sense") or {}
    truth = float(imm.get("truth_percent") or pts.get("truth_percent") or 0)
    grounded = bool(imm.get("ironclad_sealed") or pts.get("ironclad_grounded"))
    sanity = _load(STATE / "ironclad-field-sanity-panel.json", {})
    return {
        "ironclad_citation": IRONCLAD_CITE,
        "truth_percent": truth,
        "ironclad_grounded": grounded,
        "ironclad_sealed": bool(imm.get("ironclad_sealed")),
        "meld_citation": imm.get("meld_citation") or "ironclad:meld:2",
        "field_sanity_ok": bool(sanity.get("pass_ok") or sanity.get("ok")),
        "connected": True,
    }


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


def _thermal_gate_light(*, ops: int = 1) -> dict[str, Any]:
    """Cache-first ingest — headroom only; never block on missing sanity panels."""
    thermal = _load(STATE / "field-thermal-guard.json", {})
    advisory = _load(STATE / "thermal-advisory.json", {})
    headroom = float(thermal.get("headroom_pct") or 100)
    level = str(advisory.get("level") or thermal.get("level") or "ok").lower()
    allow = headroom >= 12 and level not in ("crit", "storm")
    if not LOW_POWER:
        try:
            tg = INSTALL / "lib" / "field-thermal-guard.py"
            if tg.is_file():
                spec = importlib.util.spec_from_file_location("ftg_chip", tg)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    if hasattr(mod, "FieldThermalGuard"):
                        guard = mod.FieldThermalGuard()
                        allow = allow and guard.allow_update(max(1, min(ops, 4)))
        except Exception:
            pass
    return {
        "ok": allow,
        "light_gate": LOW_POWER,
        "thermal_headroom_pct": headroom,
        "thermal_level": level,
        "ops_requested": ops,
    }


def _combinatorics_leaf(chip_id: str, family: str = "") -> str:
    fam = family or "misc"
    slug = re.sub(r"[^a-z0-9]+", "_", chip_id.lower()).strip("_")
    return f"{LEAF_PREFIX}:{fam}:{slug}"


def _normalize_chip(row: dict[str, Any], *, source: str, family: str = "") -> dict[str, Any]:
    cid = str(row.get("id") or row.get("mame_device") or row.get("chip") or "").strip()
    if not cid:
        return {}
    fam = str(row.get("family") or family or source).strip()
    kind = str(row.get("kind") or "mame_device").strip()
    return {
        "id": cid,
        "label": row.get("label") or row.get("title") or cid,
        "vendor": row.get("vendor") or "—",
        "family": fam,
        "kind": kind,
        "mhz": row.get("mhz"),
        "bits": row.get("bits"),
        "platforms": list(row.get("platforms") or []),
        "mame_device": row.get("mame_device"),
        "chips_header": row.get("header") or row.get("chips"),
        "note": row.get("note"),
        "era": row.get("era"),
        "status": row.get("status"),
        "cpu": row.get("cpu"),
        "thermal_tier": row.get("thermal_tier") or "cool",
        "combinatorics_leaf": row.get("combinatorics_leaf") or _combinatorics_leaf(cid, fam),
        "source": source,
        "country": row.get("country"),
        "live": row.get("live", True),
        "companion_role": row.get("companion_role"),
        "always_with": list(row.get("always_with") or []),
        "platform_stack": row.get("platform_stack"),
    }


def _world_chips() -> list[dict[str, Any]]:
    """Rare and national silicon — every country indexed for combinatorics."""
    world = _load(WORLD_SEED, {})
    out: list[dict[str, Any]] = []
    for country, rows in (world.get("countries") or {}).items():
        if not isinstance(rows, list):
            continue
        fam = f"world_{country}"
        for row in rows:
            if not isinstance(row, dict):
                continue
            chip = _normalize_chip(
                {**row, "family": row.get("family") or fam},
                source="world_chips",
                family=fam,
            )
            if chip:
                out.append(chip)
    return out


def _semiconductor_world_chips() -> list[dict[str, Any]]:
    """Classic semiconductor corpus — logic, memory, analog, MCU, DSP, GPU, fab."""
    semi = _load(SEMICONDUCTOR_WORLD_SEED, {})
    out: list[dict[str, Any]] = []
    for category, rows in (semi.get("categories") or {}).items():
        if not isinstance(rows, list):
            continue
        fam = f"semi_{category}"
        for row in rows:
            if not isinstance(row, dict):
                continue
            chip = _normalize_chip(
                {**row, "family": row.get("family") or fam},
                source="semiconductor_world",
                family=fam,
            )
            if chip:
                out.append(chip)
    return out


_CPU_KINDS = frozenset({"host_cpu", "guest_cpu", "soc", "mame_device"})


def _companion_match_value(chip: dict[str, Any], key: str) -> Any:
    if key == "label":
        return str(chip.get("label") or "")
    if key == "vendor":
        return str(chip.get("vendor") or "")
    if key == "family":
        return str(chip.get("family") or "")
    if key == "arch":
        return str(chip.get("cpu") or chip.get("arch") or "")
    if key == "mame_device":
        return str(chip.get("mame_device") or "")
    if key == "bits":
        return chip.get("bits")
    if key == "platforms":
        return list(chip.get("platforms") or [])
    return chip.get(key)


def _companion_stack_matches(chip: dict[str, Any], rules: dict[str, Any]) -> bool:
    if not rules:
        return False
    label_low = str(chip.get("label") or "").lower()
    arch_low = str(chip.get("cpu") or chip.get("arch") or "").lower()
    vendor = str(chip.get("vendor") or "")
    bits = chip.get("bits")
    platforms = [str(p).lower() for p in (chip.get("platforms") or [])]
    mame_dev = str(chip.get("mame_device") or "").lower()

    for key, expected in rules.items():
        if key == "era_max":
            continue
        if not isinstance(expected, list):
            expected = [expected]
        hay = _companion_match_value(chip, key)
        if key == "label":
            if not any(str(val).lower() in label_low for val in expected):
                return False
        elif key == "arch":
            joined = f"{label_low} {arch_low}"
            if not any(str(val).lower() in joined for val in expected):
                return False
        elif key == "vendor":
            if vendor and not any(str(val).lower() in vendor.lower() for val in expected):
                return False
        elif key == "family":
            if not any(str(val).lower() in str(hay).lower() for val in expected):
                return False
        elif key == "bits":
            if bits is not None and int(bits) not in [int(v) for v in expected]:
                return False
        elif key == "mame_device":
            if mame_dev and not any(str(val).lower() == mame_dev for val in expected):
                return False
        elif key == "platforms":
            if platforms and not any(str(val).lower() in platforms for val in expected):
                return False
    return True


def _detect_cpu_platform_stack(chip: dict[str, Any], stacks: dict[str, Any]) -> str | None:
    kind = str(chip.get("kind") or "")
    if kind not in _CPU_KINDS:
        return None
    label_low = str(chip.get("label") or "").lower()
    if kind == "mame_device" and not any(x in label_low for x in ("cpu", "808", "680", "6502", "z80", "486", "pentium", "athlon", "ryzen")):
        if not chip.get("mame_device"):
            return None
    best: tuple[int, str] | None = None
    for stack_id, stack in stacks.items():
        if not isinstance(stack, dict):
            continue
        rules = stack.get("match") or {}
        if not _companion_stack_matches(chip, rules):
            continue
        score = len(rules) + (2 if kind in ("host_cpu", "soc") else 0)
        if kind == "host_cpu":
            score += 3
        plat_rules = rules.get("platforms") or []
        chip_plats = [str(p).lower() for p in (chip.get("platforms") or [])]
        if plat_rules and chip_plats and any(str(v).lower() in chip_plats for v in plat_rules):
            score += 8
        if best is None or score > best[0]:
            best = (score, stack_id)
    return best[1] if best else None


def _cpu_companion_chips(cpu_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Universal north/south bridge + platform stacks — populate companion dies for free."""
    companion_doc = _load(COMPANION_SEED, {})
    stacks = companion_doc.get("platform_stacks") or {}
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    meta: dict[str, Any] = {
        "universal": 0,
        "platform_companions": 0,
        "cpus_stamped": 0,
        "by_stack": {},
        "by_role": {},
    }

    def emit(row: dict[str, Any], *, family: str, stack_id: str = "") -> None:
        cid = str(row.get("id") or "").strip()
        if not cid or cid in seen:
            return
        seen.add(cid)
        payload = {**row, "family": row.get("family") or family}
        if stack_id:
            payload["platform_stack"] = stack_id
        chip = _normalize_chip(payload, source="cpu_companion", family=family)
        if chip:
            out.append(chip)
            role = str(chip.get("companion_role") or chip.get("kind") or "companion")
            meta["by_role"][role] = meta.get("by_role", {}).get(role, 0) + 1

    for row in companion_doc.get("universal") or []:
        if isinstance(row, dict):
            emit(row, family="cpu_companion_universal")
            meta["universal"] += 1

    for stack_id, stack in stacks.items():
        if not isinstance(stack, dict):
            continue
        fam = f"cpu_companion_{stack_id}"
        for row in stack.get("companions") or []:
            if isinstance(row, dict):
                emit(row, family=fam, stack_id=stack_id)
                meta["platform_companions"] += 1
        meta["by_stack"][stack_id] = len(stack.get("companions") or [])

    stack_hits: dict[str, int] = {}
    for chip in cpu_rows:
        kind = str(chip.get("kind") or "")
        if kind not in _CPU_KINDS:
            continue
        stack_id = _detect_cpu_platform_stack(chip, stacks)
        if not stack_id:
            continue
        stack_hits[stack_id] = stack_hits.get(stack_id, 0) + 1

    meta["stack_hits"] = stack_hits
    meta["total_companions"] = len(out)
    return out, meta


def _enrich_always_with_companions(chips: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Stamp always_with companion ids on CPU rows — free platform stack linkage."""
    companion_doc = _load(COMPANION_SEED, {})
    stacks = companion_doc.get("platform_stacks") or {}
    universal_ids = [
        str(row.get("id") or "")
        for row in (companion_doc.get("universal") or [])
        if isinstance(row, dict) and row.get("id")
    ]
    stamped = 0
    enriched: list[dict[str, Any]] = []
    for chip in chips:
        row = dict(chip)
        kind = str(row.get("kind") or "")
        if kind in _CPU_KINDS and str(row.get("source") or "") != "cpu_companion":
            stack_id = _detect_cpu_platform_stack(row, stacks)
            companions: list[str] = []
            if stack_id and stack_id in stacks:
                stack = stacks[stack_id]
                companions.extend(str(x) for x in (stack.get("always_with") or []) if x)
                for comp in stack.get("companions") or []:
                    if isinstance(comp, dict) and comp.get("id"):
                        companions.append(str(comp["id"]))
                row["platform_stack"] = stack_id
            elif kind == "host_cpu":
                companions.extend(universal_ids[:4])
            if companions:
                deduped = list(dict.fromkeys(companions))
                if deduped != (row.get("always_with") or []):
                    row["always_with"] = deduped
                    row["companion_populated"] = True
                    stamped += 1
        enriched.append(row)
    return enriched


def _seed_chips() -> list[dict[str, Any]]:
    seed = _load(SEED, {})
    out: list[dict[str, Any]] = []
    for fam, rows in (seed.get("families") or {}).items():
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            chip = _normalize_chip(row, source="seed", family=str(fam))
            if chip:
                out.append(chip)
    return out


def _queen_chips() -> list[dict[str, Any]]:
    game_path = INSTALL / "Queen" / "data" / "queen-game-room.json"
    if not game_path.is_file():
        game_path = SG / "NewLatest" / "Queen" / "data" / "queen-game-room.json"
    game = _load(game_path, {})
    out: list[dict[str, Any]] = []
    for sys_row in game.get("systems") or []:
        cpu = str(sys_row.get("cpu") or "")
        chip = _normalize_chip(
            {
                "id": f"system_{sys_row.get('id')}",
                "label": sys_row.get("label"),
                "vendor": "platform",
                "kind": "guest_cpu",
                "cpu": cpu,
                "era": sys_row.get("era"),
                "status": sys_row.get("status"),
                "platforms": [sys_row.get("id")],
                "chips": sys_row.get("chips"),
                "family": "queen_system",
            },
            source="queen_game_room",
            family="queen_system",
        )
        if chip:
            out.append(chip)
    for hc in game.get("host_cpus") or []:
        chip = _normalize_chip(
            {**hc, "family": "host_cpu", "kind": "host_cpu"},
            source="queen_game_room",
            family="host_cpu",
        )
        if chip:
            out.append(chip)
    return out


def _chips_manifest() -> list[dict[str, Any]]:
    manifest_path = INSTALL / "Queen" / "data" / "chips-g16-manifest.json"
    if not manifest_path.is_file():
        manifest_path = SG / "NewLatest" / "Queen" / "data" / "chips-g16-manifest.json"
    manifest = _load(manifest_path, {})
    out: list[dict[str, Any]] = []
    for row in manifest.get("hot_paths") or []:
        if not isinstance(row, dict):
            continue
        cid = str(row.get("chip") or "")
        chip = _normalize_chip(
            {
                "id": f"chips_{cid.lower()}",
                "label": cid,
                "vendor": "CHIPS",
                "kind": "chips_hot",
                "header": row.get("header"),
                "note": row.get("note"),
                "family": "chips_hot",
            },
            source="chips_manifest",
            family="chips_hot",
        )
        if chip:
            out.append(chip)
    return out


def _isa_platforms() -> list[dict[str, Any]]:
    isa_py = INSTALL / "Hostess7" / "scripts" / "field_isa_data.py"
    if not isa_py.is_file():
        isa_py = SG / "NewLatest" / "Hostess7" / "scripts" / "field_isa_data.py"
    if not isa_py.is_file():
        return []
    try:
        spec = importlib.util.spec_from_file_location("field_isa_data_chip", isa_py)
        if not spec or not spec.loader:
            return []
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        platforms = getattr(mod, "CHIP_PLATFORMS", ())
    except Exception:
        return []
    out: list[dict[str, Any]] = []
    for row in platforms:
        if not isinstance(row, dict):
            continue
        chip = _normalize_chip(
            {
                "id": row.get("id"),
                "label": row.get("title"),
                "vendor": "ISA",
                "kind": "isa_platform",
                "bits": row.get("bits"),
                "platforms": list(row.get("platforms") or []),
                "family": "isa_platform",
                "note": ", ".join(row.get("tags") or ()),
            },
            source="isa_data",
            family="isa_platform",
        )
        if chip:
            out.append(chip)
    return out


_CPU_SOC_FAMILIES = frozenset({"apple_silicon", "mobile_soc"})


def _cpu_library_kind(family: str) -> str:
    if family in _CPU_SOC_FAMILIES or family == "cyrix":
        return "soc"
    return "host_cpu"


def _cpu_library_chips() -> list[dict[str, Any]]:
    """Ingest CPU library catalog dies — ARM, Apple, mobile, x86 — as combinatorics leaves."""
    cpu_py = INSTALL / "lib" / "field-cpu-library.py"
    if not cpu_py.is_file():
        return []
    try:
        spec = importlib.util.spec_from_file_location("field_cpu_library_chip", cpu_py)
        if not spec or not spec.loader:
            return []
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        seed_path = getattr(mod, "SEED", SEED.parent / "field-cpu-library-seed.json")
        seed = _load(Path(seed_path), {})
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()

        def ingest(row: dict[str, Any], *, src: str) -> None:
            cid = str(row.get("id") or "").strip()
            if not cid or cid in seen:
                return
            seen.add(cid)
            family = str(row.get("family") or "cpu_catalog")
            bits = row.get("bits")
            chip = _normalize_chip(
                {
                    "id": cid,
                    "label": row.get("label") or cid,
                    "vendor": row.get("vendor") or row.get("company") or "—",
                    "kind": _cpu_library_kind(family),
                    "bits": int(bits) if str(bits).isdigit() else bits,
                    "era": row.get("mfg_date_start") or row.get("era"),
                    "note": row.get("ai_detail") or row.get("schematic_blueprint"),
                    "family": family,
                    "cpu": row.get("arch"),
                },
                source="cpu_library",
                family=family,
            )
            if chip:
                rows.append(chip)

        for row in seed.get("detailed") or []:
            if isinstance(row, dict):
                ingest(row, src="seed_detailed")
        if hasattr(mod, "_expand_catalog"):
            for row in mod._expand_catalog(seed):
                if isinstance(row, dict):
                    ingest(row, src="catalog")
        return rows
    except Exception:
        return []


def _mame_binary() -> str | None:
    for name in ("mame", "mame64", "mame-sdl"):
        path = shutil.which(name)
        if path:
            return path
    return None


def _parse_mame_listdevices(text: str) -> list[dict[str, Any]]:
    """Parse `mame -listdevices` output into chip rows."""
    out: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("-") or "Device type" in line or "Brief description" in line:
            continue
        parts = line.split(None, 1)
        if len(parts) < 1:
            continue
        dev_id = parts[0].strip()
        desc = parts[1].strip() if len(parts) > 1 else dev_id
        if not re.match(r"^[a-z0-9_]+$", dev_id):
            continue
        kind = "mame_device"
        low = dev_id.lower()
        if any(x in low for x in ("cpu", "z80", "680", "808", "6502", "arm", "mips", "sh", "ppc", "sparc")):
            kind = "mame_device"
        elif any(x in low for x in ("ym", "sn764", "ay", "oki", "pokey", "sid", "dac", "sound", "fm")):
            kind = "sound"
        elif any(x in low for x in ("vdp", "crtc", "tia", "ppu", "video", "sprite", "tile")):
            kind = "video"
        out.append(
            _normalize_chip(
                {
                    "id": f"mame_{dev_id}",
                    "label": desc,
                    "vendor": "MAME",
                    "kind": kind,
                    "mame_device": dev_id,
                    "family": "mame_live",
                    "note": desc,
                },
                source="mame",
                family="mame_live",
            )
        )
    return [c for c in out if c]


def _mame_devices(*, live: bool = False) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    meta: dict[str, Any] = {"live": False, "cached": False, "count": 0}
    doctrine = _load(DOCTRINE, {})
    gate = doctrine.get("thermal_gate") or {}
    max_devices = int(gate.get("max_mame_live_devices") or 8000)

    if live and MAME_LIVE:
        gate_result = _thermal_gate_light(ops=3)
        if not gate_result.get("ok"):
            meta["skipped"] = "thermal_gate"
            meta["gate"] = gate_result
            live = False
        else:
            mame = _mame_binary()
            if mame:
                try:
                    proc = subprocess.run(
                        [mame, "-listdevices"],
                        capture_output=True,
                        text=True,
                        timeout=120,
                    )
                    if proc.returncode == 0 and proc.stdout:
                        rows = _parse_mame_listdevices(proc.stdout)[:max_devices]
                        cache_doc = {
                            "schema": "field-chip-battery-mame-cache/v1",
                            "updated": _now(),
                            "count": len(rows),
                            "devices": [{"id": r["id"], "mame_device": r.get("mame_device"), "label": r.get("label")} for r in rows],
                        }
                        _save(MAME_CACHE, cache_doc)
                        meta.update({"live": True, "count": len(rows), "mame": mame})
                        return rows, meta
                except (OSError, subprocess.TimeoutExpired) as exc:
                    meta["error"] = str(exc)

    cache = _load(MAME_CACHE, {})
    if cache.get("devices"):
        meta["cached"] = True
        rows = []
        for row in cache.get("devices") or []:
            if not isinstance(row, dict):
                continue
            chip = _normalize_chip(
                {
                    "id": row.get("id"),
                    "label": row.get("label"),
                    "vendor": "MAME",
                    "kind": "mame_device",
                    "mame_device": row.get("mame_device"),
                    "family": "mame_cache",
                },
                source="mame",
                family="mame_cache",
            )
            if chip:
                rows.append(chip)
        meta["count"] = len(rows)
        return rows, meta
    return [], meta


def _hard_percentages(weights: list[float]) -> list[float]:
    """Normalize weights to hard percentages summing exactly 100.00."""
    if not weights:
        return []
    total = sum(weights)
    if total <= 0:
        each = round(100.0 / len(weights), 2)
        out = [each] * len(weights)
        out[0] = round(100.0 - each * (len(weights) - 1), 2)
        return out
    scaled = [w / total * 10000.0 for w in weights]
    floors = [int(x) for x in scaled]
    remainder = 10000 - sum(floors)
    fracs = sorted(((scaled[i] - floors[i], i) for i in range(len(weights))), reverse=True)
    for k in range(remainder):
        floors[fracs[k % len(fracs)][1]] += 1
    return [round(f / 100.0, 2) for f in floors]


def _combinatorics_posture_boost() -> float:
    """Boost from active combinatorics exec posture when bridge panel is present."""
    bridge = _load(STATE / "field-plate-combinatorics-bridge.json", {})
    posture = bridge.get("exec_posture") or {}
    pattern_id = str(posture.get("pattern_id") or "")
    seed = _load(PATH_PREDICT_SEED, {})
    boosts = seed.get("combinatorics_pattern_boost") or {}
    return float(boosts.get(pattern_id) or 1.0)


def _predict_path_weights(chips: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build code path rows with raw weights before hard-percent normalization."""
    seed = _load(PATH_PREDICT_SEED, {})
    chip_by_id = {str(c.get("id") or ""): c for c in chips if c.get("id")}
    kind_boost = seed.get("kind_boost") or {}
    active_systems = set(seed.get("active_systems") or [])
    active_boost = float(seed.get("active_system_boost") or 2.0)
    comb_boost = _combinatorics_posture_boost()
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    for base in seed.get("base_paths") or []:
        if not isinstance(base, dict):
            continue
        cid = str(base.get("chip_id") or "")
        if cid not in chip_by_id:
            continue
        chip = chip_by_id[cid]
        w = float(base.get("weight") or 1.0)
        w *= float(kind_boost.get(str(chip.get("kind") or ""), 1.0))
        w *= comb_boost
        platforms = set(chip.get("platforms") or [])
        if platforms & active_systems or str(chip.get("id") or "").replace("system_", "") in active_systems:
            w *= active_boost
        pid = f"{cid}:{base.get('path_id') or 'main'}"
        seen.add(cid)
        rows.append({
            "chip_id": cid,
            "path_id": str(base.get("path_id") or "main"),
            "label": base.get("label") or chip.get("label"),
            "kind": chip.get("kind"),
            "family": chip.get("family"),
            "weight": w,
            "source": "seed_path",
        })

    for chip in chips:
        cid = str(chip.get("id") or "")
        if not cid or cid in seen:
            continue
        kind = str(chip.get("kind") or "")
        w = float(kind_boost.get(kind, 0.12))
        if kind == "chips_hot":
            w *= 2.5
        platforms = set(chip.get("platforms") or [])
        sys_id = cid.replace("system_", "")
        if platforms & active_systems or sys_id in active_systems:
            w *= active_boost
        w *= comb_boost
        if w < 0.01:
            w = 0.01
        rows.append({
            "chip_id": cid,
            "path_id": "device_tick",
            "label": chip.get("label"),
            "kind": kind,
            "family": chip.get("family"),
            "weight": w,
            "source": "kind_infer",
        })

    return rows


def _best_sort_mod() -> Any | None:
    path = INSTALL / "lib" / "field-best-sort.py"
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("fcb_best_sort", path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    except Exception:
        pass
    return None


def _the_sort_rows(
    rows: list[dict[str, Any]],
    *,
    context: str = "chip_paths",
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """THE sort — field-best-sort composite_bsp, one best ever."""
    best = _best_sort_mod()
    if best and hasattr(best, "apply_best"):
        try:
            return best.apply_best(rows, context=context, n=len(rows))
        except Exception:
            pass
    mod = _power_sort_mod()
    if mod and hasattr(mod, "apply_sort"):
        try:
            name_rows = [{**r, "name": str(r.get("label") or r.get("chip_id") or r.get("id") or "")} for r in rows]
            sorted_rows = mod.apply_sort(name_rows, context=context, n=len(rows))
            return sorted_rows, {"algorithm": "composite_bsp", "context": context, "source": "power_sort"}
        except Exception:
            pass
    out = sorted(rows, key=lambda r: (-float(r.get("path_pct") or r.get("weight") or 0), str(r.get("chip_id") or "")))
    return out, {"algorithm": "composite_bsp", "context": context, "source": "fallback"}


def _power_sort_mod() -> Any | None:
    for path in (GROK16 / "lib" / "field-power-sort.py", INSTALL / "Grok16" / "lib" / "field-power-sort.py"):
        if not path.is_file():
            continue
        try:
            spec = importlib.util.spec_from_file_location("fcb_power_sort", path)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                return mod
        except Exception:
            pass
    return None


def _libretro_cores() -> list[dict[str, Any]]:
    """Every installed libretro core — full combinatorics leaf."""
    roots = [
        Path.home() / ".local/share/Steam/steamapps/common/RetroArch/cores",
        Path.home() / ".local/share/RetroArch/cores",
        Path("/usr/lib/x86_64-linux-gnu/libretro"),
        Path("/usr/lib/libretro"),
    ]
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for root in roots:
        if not root.is_dir():
            continue
        for so in sorted(root.glob("*_libretro*.so")):
            core = so.stem.replace("_libretro", "").replace("libretro_", "")
            if not core or core in seen:
                continue
            seen.add(core)
            chip = _normalize_chip(
                {
                    "id": f"libretro_{core}",
                    "label": core.replace("_", " ").title(),
                    "vendor": "Libretro",
                    "kind": "guest_cpu",
                    "platforms": [core.split("_")[0]],
                    "note": str(so),
                    "family": "libretro_live",
                },
                source="libretro",
                family="libretro_live",
            )
            if chip:
                out.append(chip)
    return out


_RENDER_ONLY_KEYS = frozenset({
    "id", "label", "vendor", "package", "pins", "socket", "imprint", "body", "featured", "kind", "family",
})


def _catalog_render_rows() -> list[dict[str, Any]]:
    """Featured render overlay — imprint/package for felt macro; not a chip registry."""
    catalog = _load(CATALOG, {})
    return [dict(r) for r in (catalog.get("chips") or []) if isinstance(r, dict) and r.get("id")]


def promote_catalog_overlay_to_seed(*, write: bool = True) -> dict[str, Any]:
    """Promote catalog-only dies into seed so Ironclad owns truth — catalog stays render overlay."""
    seed = _load(SEED, {})
    families: dict[str, list] = dict(seed.get("families") or {})
    existing: set[str] = set()
    for rows in families.values():
        if not isinstance(rows, list):
            continue
        for row in rows:
            if isinstance(row, dict) and row.get("id"):
                existing.add(str(row["id"]))

    promoted: list[str] = []
    overlay = _catalog_render_rows()
    fam_key = "featured_render"
    fam_rows = list(families.get(fam_key) or [])
    fam_ids = {str(r.get("id")) for r in fam_rows if isinstance(r, dict)}

    for row in overlay:
        cid = str(row.get("id") or "")
        if not cid or cid in existing or cid in fam_ids:
            continue
        pkg = row.get("package") or "dip"
        pins = row.get("pins") or 40
        entry = {
            "id": cid,
            "label": row.get("label") or cid,
            "vendor": row.get("vendor") or "—",
            "kind": row.get("kind") or "mame_device",
            "note": f"featured render — package={pkg} pins={pins}",
        }
        if row.get("family"):
            entry["family"] = row["family"]
        fam_rows.append(entry)
        fam_ids.add(cid)
        existing.add(cid)
        promoted.append(cid)

    if promoted:
        families[fam_key] = fam_rows
        seed["families"] = families
        if write:
            _save(SEED, seed)

    return {"ok": True, "promoted": promoted, "promoted_count": len(promoted), "seed_family": fam_key}


def clean_catalog_render_layer(*, write: bool = True) -> dict[str, Any]:
    """Strip truth fields from catalog — render overlay only, no repetition above Ironclad."""
    catalog = _load(CATALOG, {})
    chips = catalog.get("chips") or []
    cleaned: list[dict[str, Any]] = []
    stripped = 0
    for row in chips:
        if not isinstance(row, dict):
            continue
        slim = {k: row[k] for k in _RENDER_ONLY_KEYS if row.get(k) is not None}
        slim["featured"] = bool(row.get("featured", True))
        if any(k in row for k in ("schematic_blueprint", "design_over_standard", "note", "source")):
            stripped += 1
        cleaned.append(slim)
    catalog["schema"] = "field-combinatronic-chip-catalog/v2"
    catalog["title"] = "Featured render overlay — imprint/package for felt macro; truth in Ironclad"
    catalog["role"] = "featured_render_overlay"
    catalog["truth_source"] = "field-ironclad-chips-combinatorics.json"
    catalog["chips"] = cleaned
    if write:
        _save(CATALOG, catalog)
    return {
        "ok": True,
        "chip_count": len(cleaned),
        "stripped_truth_fields": stripped,
        "role": catalog["role"],
    }


def _balance_mod() -> Any | None:
    path = INSTALL / "lib" / "field-combinatronic-balance.py"
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("fcb_balance", path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    except Exception:
        pass
    return None


def _the_sort_paths(paths: list[dict[str, Any]], *, sort_meta: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """THE sort — composite_bsp optimal order; slot = rank, no narrow bands."""
    sorted_paths, meta = _the_sort_rows(paths, context="chip_paths")
    if sort_meta is not None:
        sort_meta.update(meta)
    out: list[dict[str, Any]] = []
    for slot, row in enumerate(sorted_paths):
        out.append({
            **row,
            "sort_slot": slot,
            "slot": slot,
            "the_sort": True,
            "algorithm": meta.get("algorithm") or "composite_bsp",
            "one_best_ever": bool(meta.get("one_best_ever", True)),
        })
    return out


def predict_code_paths(chips: list[dict[str, Any]], *, skip_reorganize: bool = False) -> dict[str, Any]:
    """Hard-percentage paths + THE sort (composite_bsp) — Ironclad truth connected."""
    seed = _load(PATH_PREDICT_SEED, {})
    doctrine = _load(DOCTRINE, {})
    cpp = doctrine.get("code_path_prediction") or {}
    iron = _ironclad_truth()
    raw = _predict_path_weights(chips)
    if not raw:
        return {
            "schema": "field-chip-path-predict/v1",
            "hard_percent": True,
            "total_pct": 0.0,
            "paths": [],
            "the_sort": True,
            "algorithm": "composite_bsp",
            "ironclad": iron,
        }

    weights = [float(r.get("weight") or 0) for r in raw]
    pcts = _hard_percentages(weights)
    paths: list[dict[str, Any]] = []
    for row, pct in zip(raw, pcts):
        paths.append({**row, "path_pct": pct, "weight": None})

    sort_meta: dict[str, Any] = {}
    if not skip_reorganize:
        paths = _the_sort_paths(paths, sort_meta=sort_meta)

    total = round(sum(float(p.get("path_pct") or 0) for p in paths), 2)

    return {
        "schema": "field-chip-path-predict/v1",
        "hard_percent": True,
        "total_pct": total,
        "the_sort": True,
        "algorithm": sort_meta.get("algorithm") or "composite_bsp",
        "one_best_ever": True,
        "field_unique_best": True,
        "context": seed.get("context") or FACET,
        "path_count": len(paths),
        "paths": paths,
        "sort": sort_meta,
        "ironclad": iron,
        "ironclad_citation": IRONCLAD_CITE,
        "combinatorics_boost": _combinatorics_posture_boost(),
    }


def _apply_path_layout(
    chips: list[dict[str, Any]],
    leaves: list[dict[str, Any]],
    prediction: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Stamp path_pct/sort_slot on chips — THE sort order, Ironclad truth."""
    path_by_chip: dict[str, dict[str, Any]] = {}
    for p in prediction.get("paths") or []:
        cid = str(p.get("chip_id") or "")
        if cid and cid not in path_by_chip:
            path_by_chip[cid] = p

    def enrich(row: dict[str, Any]) -> dict[str, Any]:
        cid = str(row.get("id") or row.get("chip_id") or "")
        p = path_by_chip.get(cid) or {}
        return {
            **row,
            "path_id": p.get("path_id"),
            "path_pct": p.get("path_pct"),
            "sort_slot": p.get("sort_slot", p.get("slot")),
            "slot": p.get("slot"),
            "the_sort": p.get("the_sort", True),
            "ironclad_cite": IRONCLAD_CITE,
        }

    enriched = [enrich(c) for c in chips]
    enriched.sort(key=lambda c: (
        c.get("sort_slot") if c.get("sort_slot") is not None else c.get("slot") if c.get("slot") is not None else 999,
        -float(c.get("path_pct") or 0),
        str(c.get("label") or ""),
    ))

    leaf_by_chip = {str(l.get("chip_id") or ""): l for l in leaves}
    reordered_leaves: list[dict[str, Any]] = []
    for chip in enriched:
        cid = str(chip.get("id") or "")
        leaf = leaf_by_chip.get(cid)
        if leaf:
            reordered_leaves.append({**leaf, **{k: chip[k] for k in ("path_pct", "sort_slot", "slot", "the_sort", "ironclad_cite") if k in chip}})
    seen_leaf = {str(l.get("chip_id") or "") for l in reordered_leaves}
    for leaf in leaves:
        cid = str(leaf.get("chip_id") or "")
        if cid not in seen_leaf:
            reordered_leaves.append(leaf)

    return enriched, reordered_leaves


def _merge_chips(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Dedupe by id — seed/curated rows win over MAME flood."""
    priority = {
        "seed": 0,
        "world_chips": 1,
        "semiconductor_world": 1,
        "cpu_companion": 1,
        "featured_render": 2,
        "chips_manifest": 2,
        "queen_game_room": 3,
        "libretro": 4,
        "cpu_library": 5,
        "isa_data": 6,
        "mame": 7,
    }
    by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        cid = str(row.get("id") or "")
        if not cid:
            continue
        src = str(row.get("source") or "misc")
        existing = by_id.get(cid)
        if not existing or priority.get(src, 9) < priority.get(str(existing.get("source")), 9):
            by_id[cid] = row
    return sorted(by_id.values(), key=lambda c: (c.get("kind") or "", c.get("label") or c.get("id") or ""))


def combinatorics_leaves(chips: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map every chip to a combinatorics leaf — indexed, not cross-producted."""
    leaves: list[dict[str, Any]] = []
    for chip in chips:
        leaf_id = chip.get("combinatorics_leaf") or _combinatorics_leaf(str(chip.get("id") or ""), str(chip.get("family") or ""))
        leaves.append({
            "id": leaf_id,
            "chip_id": chip.get("id"),
            "label": chip.get("label"),
            "kind": chip.get("kind"),
            "family": chip.get("family"),
            "mame_device": chip.get("mame_device"),
            "source": chip.get("source"),
            "facet": FACET,
            "depth": 1,
            "runner": "emulator",
            "emulator": "FieldChips" if chip.get("kind") in ("chips_hot", "guest_cpu", "isa_platform") else "MAME",
            "thermal_tier": chip.get("thermal_tier") or "cool",
            "companion_role": chip.get("companion_role"),
            "always_with": list(chip.get("always_with") or []),
            "platform_stack": chip.get("platform_stack"),
        })
    return leaves


def _ironclad_root() -> dict[str, Any]:
    """Ironclad is the sole root — truth plate before any chip ingest."""
    iron = _ironclad_truth()
    imm = _load(STATE / "ironclad-immediate.json", {})
    if not imm.get("schema"):
        ic = INSTALL / "lib" / "ironclad-immediate.py"
        if ic.is_file():
            try:
                spec = importlib.util.spec_from_file_location("ic_ironclad_chips", ic)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    if hasattr(mod, "immediate_slice"):
                        imm = mod.immediate_slice()
                        iron = _ironclad_truth()
            except Exception:
                pass
    return {
        **iron,
        "root": "ironclad-immediate",
        "immediate_schema": imm.get("schema"),
        "plate_to_sense": imm.get("plate_to_sense"),
    }


def build_ironclad_chips_combinatorics(*, mame_live: bool = False, force: bool = False) -> dict[str, Any]:
    """Combinatorics every chip off Ironclad — ingest all sources, THE sort, hard path %."""
    t0 = time.perf_counter()
    ironclad_root = _ironclad_root()
    bal = _balance_mod()
    balance_gate: dict[str, Any] = {}
    if bal and hasattr(bal, "gate_refresh"):
        balance_gate = bal.gate_refresh(False, force=force)
        if balance_gate.get("skip_reorganize") and not force:
            cached = _load(COMBINATORICS, {})
            if cached.get("chips"):
                elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
                if hasattr(bal, "record_cycle"):
                    bal.record_cycle(reorganized=False, elapsed_ms=elapsed_ms)
                out = dict(cached)
                out["balance_hold"] = True
                out["fast_path"] = True
                out["balance_gate"] = balance_gate
                out["elapsed_ms"] = elapsed_ms
                out["optimized_combinatronic"] = True
                out["combinatronic"] = True
                return out

    gate = _thermal_gate_light(ops=2)
    rows: list[dict[str, Any]] = []
    sources_meta: dict[str, Any] = {}

    seed_rows = _seed_chips()
    rows.extend(seed_rows)
    sources_meta["seed"] = len(seed_rows)

    queen = _queen_chips()
    rows.extend(queen)
    sources_meta["queen_game_room"] = len(queen)

    manifest = _chips_manifest()
    rows.extend(manifest)
    sources_meta["chips_manifest"] = len(manifest)

    cpu_lib = _cpu_library_chips()
    rows.extend(cpu_lib)
    sources_meta["cpu_library"] = len(cpu_lib)

    isa = _isa_platforms()
    rows.extend(isa)
    sources_meta["isa_data"] = len(isa)

    world = _world_chips()
    rows.extend(world)
    sources_meta["world_chips"] = len(world)
    by_country: dict[str, int] = {}
    for chip in world:
        cc = str(chip.get("country") or chip.get("family") or "unknown")
        by_country[cc] = by_country.get(cc, 0) + 1
    sources_meta["world_chips_by_country"] = by_country

    semi = _semiconductor_world_chips()
    rows.extend(semi)
    sources_meta["semiconductor_world"] = len(semi)
    by_category: dict[str, int] = {}
    for chip in semi:
        fam = str(chip.get("family") or "unknown")
        by_category[fam] = by_category.get(fam, 0) + 1
    sources_meta["semiconductor_world_by_category"] = by_category

    promote_catalog_overlay_to_seed(write=True)
    sources_meta["featured_render_overlay"] = len(_catalog_render_rows())

    libretro = _libretro_cores()
    rows.extend(libretro)
    sources_meta["libretro"] = len(libretro)

    mame_rows, mame_meta = _mame_devices(live=mame_live)
    if mame_rows:
        rows.extend(mame_rows)
    sources_meta["mame"] = mame_meta

    companion_rows, companion_meta = _cpu_companion_chips(rows)
    rows.extend(companion_rows)
    sources_meta["cpu_companion"] = companion_meta

    chips = _merge_chips(rows)
    chips = _enrich_always_with_companions(chips)
    sources_meta["cpu_companion"]["cpus_stamped"] = sum(
        1 for c in chips if c.get("companion_populated")
    )
    cached = _load(COMBINATORICS, {})
    incremental_added = 0
    if balance_gate.get("reason") == "new_corpus" and cached.get("chips") and bal and hasattr(bal, "incremental_merge"):
        chips, incremental_added = bal.incremental_merge(cached.get("chips") or [], chips, id_field="id")

    leaves = combinatorics_leaves(chips)
    skip_reorg = bool(balance_gate.get("skip_reorganize")) or (
        balance_gate.get("reason") == "new_corpus" and incremental_added > 0
    )
    if skip_reorg and cached.get("code_path_prediction"):
        path_prediction = cached.get("code_path_prediction") or {}
    else:
        path_prediction = predict_code_paths(chips, skip_reorganize=skip_reorg)
    chips, leaves = _apply_path_layout(chips, leaves, path_prediction)
    if bal and hasattr(bal, "stamp_optimized"):
        at_balance = bool(balance_gate.get("balanced")) or balance_gate.get("reason") == "balanced_hold"
        leaves = bal.stamp_optimized(leaves, balanced=at_balance)

    by_kind: dict[str, int] = {}
    by_family: dict[str, int] = {}
    for chip in chips:
        k = str(chip.get("kind") or "unknown")
        f = str(chip.get("family") or "unknown")
        by_kind[k] = by_kind.get(k, 0) + 1
        by_family[f] = by_family.get(f, 0) + 1

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    result = {
        "schema": "field-ironclad-chips-combinatorics/v1",
        "updated": _now(),
        "motto": "Every chip combinatorics off Ironclad — Cyrix, CoCo, MAME, CHIPS — leaves from truth.",
        "ok": True,
        "facet": FACET,
        "ironclad_root": ironclad_root,
        "gate": gate,
        "low_power": LOW_POWER,
        "sources": sources_meta,
        "counts": {
            "total": len(chips),
            "leaves": len(leaves),
            "by_kind": by_kind,
            "by_family": by_family,
            "cyrix": sum(1 for c in chips if "cyrix" in str(c.get("family") or c.get("id") or "").lower()),
            "coco": sum(1 for c in chips if "coco" in str(c.get("family") or "") or "coco" in str(c.get("platforms") or [])),
            "mame": sum(1 for c in chips if c.get("source") == "mame" or c.get("mame_device")),
            "chips_hot": sum(1 for c in chips if c.get("kind") == "chips_hot"),
        },
        "chips": chips,
        "combinatorics_leaves": leaves,
        "code_path_prediction": path_prediction,
        "elapsed_ms": elapsed_ms,
        "balance_gate": balance_gate or None,
        "optimized_combinatronic": bool(balance_gate.get("balanced")),
        "combinatronic": True,
        "all_data_combinatronic": True,
        "the_sort": True,
        "ironclad": ironclad_root,
        "ironclad_citation": IRONCLAD_CITE,
    }
    if bal and hasattr(bal, "record_cycle"):
        bal.record_cycle(
            reorganized=not balance_gate.get("skip_reorganize"),
            elapsed_ms=elapsed_ms,
            incremental_added=incremental_added,
        )
    return result


def _g16_lang_health_slice() -> dict[str, Any]:
    """CHIPs ↔ G16 compiler test health — field_opt toolchain gate."""
    path = STATE / "g16-chips-lang-health.json"
    doc = _load(path, {})
    if doc:
        return {"ok": doc.get("ok"), "facet": "g16_lang_health", "hydrate": str(path), **doc}
    return {
        "ok": (GROK16 / "bin" / "g16").is_file(),
        "facet": "g16_lang_health",
        "hint": "Run lib/g16-compiler-test-harness.py",
        "manifest": "Queen/data/chips-g16-manifest.json",
    }


def publish_panel(*, mame_live: bool = False, write_combinatorics: bool = True) -> dict[str, Any]:
    combinatorics = build_ironclad_chips_combinatorics(mame_live=mame_live)
    panel = {
        "schema": "field-ironclad-chips-combinatorics-panel/v1",
        "updated": combinatorics.get("updated"),
        "ok": combinatorics.get("ok", True),
        "motto": combinatorics.get("motto"),
        "counts": combinatorics.get("counts"),
        "gate": combinatorics.get("gate"),
        "sources": combinatorics.get("sources"),
        "elapsed_ms": combinatorics.get("elapsed_ms"),
        "ironclad_root": combinatorics.get("ironclad_root"),
        "combinatorics_facet": FACET,
        "leaf_count": len(combinatorics.get("combinatorics_leaves") or []),
        "sample_leaves": (combinatorics.get("combinatorics_leaves") or [])[:12],
        "sample_chips": (combinatorics.get("chips") or [])[:24],
        "cyrix_chips": [c for c in (combinatorics.get("chips") or []) if "cyrix" in str(c.get("id") or "").lower()],
        "coco_chips": [
            c for c in (combinatorics.get("chips") or [])
            if "coco" in str(c.get("family") or "") or any("coco" in str(p) for p in (c.get("platforms") or []))
        ],
        "code_path_prediction": {
            "hard_percent": True,
            "total_pct": (combinatorics.get("code_path_prediction") or {}).get("total_pct"),
            "path_count": (combinatorics.get("code_path_prediction") or {}).get("path_count"),
            "top_paths": (combinatorics.get("code_path_prediction") or {}).get("paths", [])[:16],
            "the_sort": True,
            "algorithm": "composite_bsp",
        },
        "g16_lang_health": _g16_lang_health_slice(),
    }
    _save(PANEL, panel)
    if write_combinatorics:
        _save(COMBINATORICS, combinatorics)
    plate_stack: dict[str, Any] = {}
    cps = INSTALL / "lib" / "field-chips-plate-stack.py"
    if cps.is_file() and os.environ.get("NEXUS_CHIPS_PLATE_STACK", "1") == "1":
        try:
            spec = importlib.util.spec_from_file_location("chip_plate_stack_pub", cps)
            if spec and spec.loader:
                cps_mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(cps_mod)
                if hasattr(cps_mod, "publish_panel"):
                    plate_stack = cps_mod.publish_panel(refresh=False, write_battery=True) or {}
        except Exception:
            plate_stack = {"ok": False, "skipped": "plate_stack_refresh_failed"}
    core_out: dict[str, Any] = {}
    cc = INSTALL / "lib" / "field-chips-core.py"
    if cc.is_file() and os.environ.get("NEXUS_CHIPS_CORE", "1") == "1":
        try:
            spec = importlib.util.spec_from_file_location("chip_core_ic", cc)
            if spec and spec.loader:
                cc_mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(cc_mod)
                if hasattr(cc_mod, "maybe_condense_after_ironclad"):
                    core_out = cc_mod.maybe_condense_after_ironclad(refresh=False) or {}
        except Exception:
            core_out = {"ok": False, "skipped": "chips_core_condense_failed"}
    return {
        "ok": True,
        "panel": panel,
        "combinatorics_path": str(COMBINATORICS),
        "panel_path": str(PANEL),
        "plate_stack": {
            "ok": (plate_stack.get("panel") or {}).get("ok"),
            "module_count": ((plate_stack.get("battery") or {}).get("counts") or {}).get("modules"),
        },
        "chips_core": {
            "ok": (core_out.get("panel") or {}).get("ok"),
            "condensed": (core_out.get("panel") or {}).get("condensed"),
            "core_module_count": ((core_out.get("core") or {}).get("counts") or {}).get("core_modules"),
        } if core_out else None,
    }


def combinatronic_panel(*, refresh: bool = False, state_dir: Path | None = None, force: bool = False) -> dict[str, Any]:
    """Universal CHIPS Combinatronic — bands, leaves, hard path % for Queen + combinatorics."""
    state = state_dir or STATE
    bal = _balance_mod()
    if refresh and bal and hasattr(bal, "gate_refresh"):
        gate = bal.gate_refresh(refresh, force=force)
        if gate.get("skip_reorganize") and not force:
            refresh = False
    combinatorics = _load(state / "field-ironclad-chips-combinatorics.json", {})
    if refresh or not combinatorics.get("chips"):
        old_state = STATE
        try:
            if state_dir:
                globals()["STATE"] = state  # noqa: PLW0603 — publish into caller state
            publish_panel(write_combinatorics=True)
            combinatorics = _load(state / "field-ironclad-chips-combinatorics.json", {}) or build_ironclad_chips_combinatorics()
        finally:
            globals()["STATE"] = old_state
    if not combinatorics.get("chips"):
        combinatorics = build_ironclad_chips_combinatorics()

    pred = combinatorics.get("code_path_prediction") or {}
    counts = combinatorics.get("counts") or {}
    leaves = combinatorics.get("combinatorics_leaves") or []

    families: dict[str, list[dict[str, Any]]] = {}
    for leaf in leaves:
        fam = str(leaf.get("family") or "unknown")
        families.setdefault(fam, []).append({
            "id": leaf.get("id"),
            "chip_id": leaf.get("chip_id"),
            "label": leaf.get("label"),
            "kind": leaf.get("kind"),
            "path_pct": leaf.get("path_pct"),
            "band": leaf.get("band"),
            "slot": leaf.get("slot"),
            "pipe_width": leaf.get("pipe_width"),
        })

    family_rows = [
        {"family": fam, "count": len(rows), "chips": rows[:8]}
        for fam, rows in sorted(families.items(), key=lambda x: (-len(x[1]), x[0]))
    ]

    return {
        "schema": "field-chips-combinatronic/v1",
        "updated": combinatorics.get("updated"),
        "ok": True,
        "motto": "Ironclad CHIPS Combinatronic — every die a leaf off truth, every path a hard percent.",
        "facet": FACET,
        "combinatorics_facet": FACET,
        "ironclad_root": combinatorics.get("ironclad_root"),
        "counts": counts,
        "sources": combinatorics.get("sources"),
        "gate": combinatorics.get("gate"),
        "line_safety": {
            "the_sort": True,
            "algorithm": "composite_bsp",
            "pipe_policy": pred.get("pipe_policy") or "composite_bsp",
        },
        "path_prediction": {
            "hard_percent": pred.get("hard_percent", True),
            "total_pct": pred.get("total_pct"),
            "path_count": pred.get("path_count"),
            "bands": pred.get("bands") or [],
            "top_paths": (pred.get("paths") or [])[:32],
        },
        "combinatorics_leaves": leaves[:64],
        "leaf_count": len(leaves),
        "families": family_rows,
        "combinatorics_boost": pred.get("combinatorics_boost"),
        "elapsed_ms": combinatorics.get("elapsed_ms"),
        "balance_gate": combinatorics.get("balance_gate"),
        "optimized_combinatronic": combinatorics.get("optimized_combinatronic"),
        "combinatronic": True,
        "fast_path": combinatorics.get("fast_path", False),
    }


def ironclad_chips_slice(*, state_dir: Path | None = None) -> dict[str, Any]:
    """Light read for combinatorics engine — Ironclad cache first."""
    state = state_dir or STATE
    cached = _load(state / "field-ironclad-chips-combinatorics.json", {})
    overlay_n = len(_catalog_render_rows())
    if cached.get("chips"):
        pred = cached.get("code_path_prediction") or {}
        return {
            "schema": "field-ironclad-chips-combinatorics-slice/v1",
            "ok": True,
            "counts": cached.get("counts"),
            "chip_count": (cached.get("counts") or {}).get("total"),
            "leaf_count": len(cached.get("combinatorics_leaves") or []),
            "combinatorics_leaves": (cached.get("combinatorics_leaves") or [])[:48],
            "featured_render_overlay": overlay_n,
            "catalog_role": "featured_render_overlay",
            "code_path_prediction": {
                "hard_percent": True,
                "total_pct": pred.get("total_pct"),
                "the_sort": True,
                "algorithm": "composite_bsp",
            },
            "facet": FACET,
            "ironclad_root": cached.get("ironclad_root"),
            "cached": True,
        }
    pub = publish_panel(write_combinatorics=True)
    panel = pub.get("panel") or {}
    return {
        "schema": "field-ironclad-chips-combinatorics-slice/v1",
        "ok": bool(panel.get("counts")),
        "counts": panel.get("counts"),
        "chip_count": (panel.get("counts") or {}).get("total"),
        "leaf_count": panel.get("leaf_count"),
        "combinatorics_leaves": panel.get("sample_leaves") or [],
        "featured_render_overlay": overlay_n,
        "catalog_role": "featured_render_overlay",
        "facet": FACET,
        "ironclad_root": panel.get("ironclad_root"),
        "cached": False,
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        panel_path = PANEL
        if panel_path.is_file():
            print(json.dumps(_load(panel_path), ensure_ascii=False, indent=2))
        else:
            print(json.dumps(publish_panel().get("panel"), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("build", "publish"):
        mame_live = "--mame-live" in sys.argv[2:] or MAME_LIVE
        print(json.dumps(publish_panel(mame_live=mame_live), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("combinatorics", "chips"):
        mame_live = "--mame-live" in sys.argv[2:]
        print(json.dumps(build_ironclad_chips_combinatorics(mame_live=mame_live), ensure_ascii=False, indent=2))
        return 0
    if cmd == "slice":
        print(json.dumps(ironclad_chips_slice(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("paths", "predict", "path-predict"):
        combinatorics = build_ironclad_chips_combinatorics()
        print(json.dumps(combinatorics.get("code_path_prediction") or {}, ensure_ascii=False, indent=2))
        return 0
    if cmd in ("combinatronic", "combinatronics", "chips-combinatronic"):
        refresh = "--refresh" in sys.argv[2:]
        print(json.dumps(combinatronic_panel(refresh=refresh), ensure_ascii=False, indent=2))
        return 0
    if cmd == "mame-import":
        os.environ["NEXUS_CHIP_BATTERY_MAME_LIVE"] = "1"
        print(json.dumps(publish_panel(mame_live=True), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("sync-catalog-seed", "promote-catalog"):
        print(json.dumps(promote_catalog_overlay_to_seed(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("clean-catalog", "clean-catalog-layer"):
        print(json.dumps(clean_catalog_render_layer(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "verify":
        pub = publish_panel()
        panel = pub.get("panel") or {}
        counts = panel.get("counts") or {}
        pred = panel.get("code_path_prediction") or {}
        ok = (
            counts.get("total", 0) >= 50
            and counts.get("cyrix", 0) >= 5
            and counts.get("coco", 0) >= 5
            and any(c.get("id") == "cyrix_6x86" for c in (panel.get("cyrix_chips") or []))
            and pred.get("total_pct") == 100.0
            and pred.get("the_sort", True)
        )
        print(json.dumps({
            "ok": ok,
            "counts": counts,
            "leaf_count": panel.get("leaf_count"),
            "path_total_pct": pred.get("total_pct"),
            "facet": FACET,
            "ironclad_root": panel.get("ironclad_root"),
        }, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    print(json.dumps({
        "error": "usage",
        "cmds": [
            "json", "build", "publish", "combinatorics", "slice", "paths", "combinatronic",
            "sync-catalog-seed", "clean-catalog", "mame-import", "verify",
        ],
    }))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())