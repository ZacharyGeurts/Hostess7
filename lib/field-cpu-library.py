#!/usr/bin/env pythong
"""CPU Library — every make/model catalog: ARM, Mac, mobile, x86, retro — H7-grade detail."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))
DOCTRINE = INSTALL / "data" / "field-cpu-library-doctrine.json"
SEED = INSTALL / "data" / "field-cpu-library-seed.json"
PANEL = STATE / "field-cpu-library-panel.json"
LIBRARY = STATE / "field-cpu-library.json"

ARM_CORES: tuple[dict[str, str], ...] = (
    {"id": "armv6", "label": "ARMv6", "arch": "ARMv6", "bits": "32", "era": "2002"},
    {"id": "armv7_a", "label": "ARMv7-A", "arch": "ARMv7-A", "bits": "32", "era": "2005"},
    {"id": "armv8_a", "label": "ARMv8-A", "arch": "ARMv8-A", "bits": "64", "era": "2011"},
    {"id": "armv8_1_a", "label": "ARMv8.1-A", "arch": "ARMv8.1-A", "bits": "64", "era": "2014"},
    {"id": "armv8_2_a", "label": "ARMv8.2-A", "arch": "ARMv8.2-A", "bits": "64", "era": "2016"},
    {"id": "armv8_3_a", "label": "ARMv8.3-A", "arch": "ARMv8.3-A", "bits": "64", "era": "2017"},
    {"id": "armv8_4_a", "label": "ARMv8.4-A", "arch": "ARMv8.4-A", "bits": "64", "era": "2018"},
    {"id": "armv8_5_a", "label": "ARMv8.5-A", "arch": "ARMv8.5-A", "bits": "64", "era": "2019"},
    {"id": "armv8_6_a", "label": "ARMv8.6-A", "arch": "ARMv8.6-A", "bits": "64", "era": "2020"},
    {"id": "armv8_7_a", "label": "ARMv8.7-A", "arch": "ARMv8.7-A", "bits": "64", "era": "2021"},
    {"id": "armv8_8_a", "label": "ARMv8.8-A", "arch": "ARMv8.8-A", "bits": "64", "era": "2022"},
    {"id": "armv9_a", "label": "ARMv9-A", "arch": "ARMv9-A", "bits": "64", "era": "2021"},
    {"id": "armv9_2_a", "label": "ARMv9.2-A", "arch": "ARMv9.2-A", "bits": "64", "era": "2023"},
    {"id": "cortex_m0", "label": "Cortex-M0", "arch": "ARMv6-M", "bits": "32", "era": "2009"},
    {"id": "cortex_m0plus", "label": "Cortex-M0+", "arch": "ARMv6-M", "bits": "32", "era": "2012"},
    {"id": "cortex_m3", "label": "Cortex-M3", "arch": "ARMv7-M", "bits": "32", "era": "2005"},
    {"id": "cortex_m4", "label": "Cortex-M4", "arch": "ARMv7-M", "bits": "32", "era": "2010"},
    {"id": "cortex_m7", "label": "Cortex-M7", "arch": "ARMv7-M", "bits": "32", "era": "2014"},
    {"id": "cortex_m23", "label": "Cortex-M23", "arch": "ARMv8-M", "bits": "32", "era": "2016"},
    {"id": "cortex_m33", "label": "Cortex-M33", "arch": "ARMv8-M", "bits": "32", "era": "2018"},
    {"id": "cortex_m55", "label": "Cortex-M55", "arch": "ARMv8.1-M", "bits": "32", "era": "2020"},
    {"id": "cortex_m85", "label": "Cortex-M85", "arch": "ARMv8.1-M", "bits": "32", "era": "2022"},
    {"id": "cortex_a53", "label": "Cortex-A53", "arch": "ARMv8-A", "bits": "64", "era": "2012"},
    {"id": "cortex_a55", "label": "Cortex-A55", "arch": "ARMv8.2-A", "bits": "64", "era": "2017"},
    {"id": "cortex_a57", "label": "Cortex-A57", "arch": "ARMv8-A", "bits": "64", "era": "2013"},
    {"id": "cortex_a72", "label": "Cortex-A72", "arch": "ARMv8-A", "bits": "64", "era": "2015"},
    {"id": "cortex_a73", "label": "Cortex-A73", "arch": "ARMv8-A", "bits": "64", "era": "2016"},
    {"id": "cortex_a75", "label": "Cortex-A75", "arch": "ARMv8.2-A", "bits": "64", "era": "2017"},
    {"id": "cortex_a76", "label": "Cortex-A76", "arch": "ARMv8.2-A", "bits": "64", "era": "2018"},
    {"id": "cortex_a77", "label": "Cortex-A77", "arch": "ARMv8.2-A", "bits": "64", "era": "2019"},
    {"id": "cortex_a78", "label": "Cortex-A78", "arch": "ARMv8.2-A", "bits": "64", "era": "2020"},
    {"id": "cortex_a78c", "label": "Cortex-A78C", "arch": "ARMv8.2-A", "bits": "64", "era": "2020"},
    {"id": "cortex_a710", "label": "Cortex-A710", "arch": "ARMv9-A", "bits": "64", "era": "2021"},
    {"id": "cortex_a715", "label": "Cortex-A715", "arch": "ARMv9-A", "bits": "64", "era": "2022"},
    {"id": "cortex_a720", "label": "Cortex-A720", "arch": "ARMv9.2-A", "bits": "64", "era": "2023"},
    {"id": "cortex_a725", "label": "Cortex-A725", "arch": "ARMv9.2-A", "bits": "64", "era": "2024"},
    {"id": "cortex_x1", "label": "Cortex-X1", "arch": "ARMv8.2-A", "bits": "64", "era": "2020"},
    {"id": "cortex_x2", "label": "Cortex-X2", "arch": "ARMv9-A", "bits": "64", "era": "2021"},
    {"id": "cortex_x3", "label": "Cortex-X3", "arch": "ARMv9-A", "bits": "64", "era": "2022"},
    {"id": "cortex_x4", "label": "Cortex-X4", "arch": "ARMv9.2-A", "bits": "64", "era": "2023"},
    {"id": "cortex_r52", "label": "Cortex-R52", "arch": "ARMv8-R", "bits": "32", "era": "2016"},
    {"id": "cortex_r82", "label": "Cortex-R82", "arch": "ARMv8-R", "bits": "64", "era": "2020"},
)

APPLE_CHIPS: tuple[dict[str, str], ...] = (
    {"id": "apple_a4", "label": "Apple A4", "era": "2010", "bits": "32"},
    {"id": "apple_a5", "label": "Apple A5", "era": "2011", "bits": "32"},
    {"id": "apple_a6", "label": "Apple A6", "era": "2012", "bits": "32"},
    {"id": "apple_a7", "label": "Apple A7", "era": "2013", "bits": "64"},
    {"id": "apple_a8", "label": "Apple A8", "era": "2014", "bits": "64"},
    {"id": "apple_a9", "label": "Apple A9", "era": "2015", "bits": "64"},
    {"id": "apple_a10", "label": "Apple A10 Fusion", "era": "2016", "bits": "64"},
    {"id": "apple_a11", "label": "Apple A11 Bionic", "era": "2017", "bits": "64"},
    {"id": "apple_a12", "label": "Apple A12 Bionic", "era": "2018", "bits": "64"},
    {"id": "apple_a13", "label": "Apple A13 Bionic", "era": "2019", "bits": "64"},
    {"id": "apple_a14", "label": "Apple A14 Bionic", "era": "2020", "bits": "64"},
    {"id": "apple_a15", "label": "Apple A15 Bionic", "era": "2021", "bits": "64"},
    {"id": "apple_a16", "label": "Apple A16 Bionic", "era": "2022", "bits": "64"},
    {"id": "apple_a17_pro", "label": "Apple A17 Pro", "era": "2023", "bits": "64"},
    {"id": "apple_a18", "label": "Apple A18", "era": "2024", "bits": "64"},
    {"id": "apple_m1", "label": "Apple M1", "era": "2020", "bits": "64"},
    {"id": "apple_m1_pro", "label": "Apple M1 Pro", "era": "2021", "bits": "64"},
    {"id": "apple_m1_max", "label": "Apple M1 Max", "era": "2021", "bits": "64"},
    {"id": "apple_m1_ultra", "label": "Apple M1 Ultra", "era": "2022", "bits": "64"},
    {"id": "apple_m2", "label": "Apple M2", "era": "2022", "bits": "64"},
    {"id": "apple_m2_pro", "label": "Apple M2 Pro", "era": "2023", "bits": "64"},
    {"id": "apple_m2_max", "label": "Apple M2 Max", "era": "2023", "bits": "64"},
    {"id": "apple_m2_ultra", "label": "Apple M2 Ultra", "era": "2023", "bits": "64"},
    {"id": "apple_m3", "label": "Apple M3", "era": "2023", "bits": "64"},
    {"id": "apple_m3_pro", "label": "Apple M3 Pro", "era": "2023", "bits": "64"},
    {"id": "apple_m3_max", "label": "Apple M3 Max", "era": "2023", "bits": "64"},
    {"id": "apple_m4", "label": "Apple M4", "era": "2024", "bits": "64"},
    {"id": "apple_m4_pro", "label": "Apple M4 Pro", "era": "2024", "bits": "64"},
    {"id": "apple_m4_max", "label": "Apple M4 Max", "era": "2024", "bits": "64"},
)

MOBILE_SOCS: tuple[dict[str, str], ...] = (
    {"id": "snapdragon_8_gen1", "label": "Snapdragon 8 Gen 1", "vendor": "Qualcomm", "era": "2021"},
    {"id": "snapdragon_8_gen2", "label": "Snapdragon 8 Gen 2", "vendor": "Qualcomm", "era": "2022"},
    {"id": "snapdragon_8_gen3", "label": "Snapdragon 8 Gen 3", "vendor": "Qualcomm", "era": "2023"},
    {"id": "snapdragon_8_elite", "label": "Snapdragon 8 Elite", "vendor": "Qualcomm", "era": "2024"},
    {"id": "dimensity_9300", "label": "MediaTek Dimensity 9300", "vendor": "MediaTek", "era": "2023"},
    {"id": "dimensity_9400", "label": "MediaTek Dimensity 9400", "vendor": "MediaTek", "era": "2024"},
    {"id": "exynos_2400", "label": "Samsung Exynos 2400", "vendor": "Samsung", "era": "2024"},
    {"id": "tensor_g4", "label": "Google Tensor G4", "vendor": "Google", "era": "2024"},
    {"id": "kirin_9000s", "label": "HiSilicon Kirin 9000S", "vendor": "HiSilicon", "era": "2023"},
)

INTEL_CPUS: tuple[dict[str, str], ...] = (
    {"id": "intel_8086", "label": "Intel 8086", "era": "1978", "arch": "x86"},
    {"id": "intel_80286", "label": "Intel 80286", "era": "1982", "arch": "x86"},
    {"id": "intel_80386", "label": "Intel 80386", "era": "1985", "arch": "x86-32"},
    {"id": "intel_80486", "label": "Intel 80486", "era": "1989", "arch": "x86-32"},
    {"id": "intel_pentium", "label": "Intel Pentium", "era": "1993", "arch": "x86-32"},
    {"id": "intel_pentium_pro", "label": "Intel Pentium Pro", "era": "1995", "arch": "x86-32"},
    {"id": "intel_pentium_mmx", "label": "Intel Pentium MMX", "era": "1996", "arch": "x86-32"},
    {"id": "intel_pentium_ii", "label": "Intel Pentium II", "era": "1997", "arch": "x86-32"},
    {"id": "intel_pentium_iii", "label": "Intel Pentium III", "era": "1999", "arch": "x86-32"},
    {"id": "intel_pentium_4", "label": "Intel Pentium 4", "era": "2000", "arch": "x86-32"},
    {"id": "intel_core2_duo", "label": "Intel Core 2 Duo", "era": "2006", "arch": "x86-64"},
    {"id": "intel_core_i3_1st", "label": "Intel Core i3 (1st Gen)", "era": "2010", "arch": "x86-64"},
    {"id": "intel_core_i5_1st", "label": "Intel Core i5 (1st Gen)", "era": "2010", "arch": "x86-64"},
    {"id": "intel_core_i7_1st", "label": "Intel Core i7 (1st Gen)", "era": "2008", "arch": "x86-64"},
    {"id": "intel_core_i9_7900x", "label": "Intel Core i9-7900X", "era": "2017", "arch": "x86-64"},
    {"id": "intel_core_i9_12900k", "label": "Intel Core i9-12900K", "era": "2021", "arch": "x86-64"},
    {"id": "intel_core_i9_14900k", "label": "Intel Core i9-14900K", "era": "2023", "arch": "x86-64"},
    {"id": "intel_core_ultra_7_265k", "label": "Intel Core Ultra 7 265K", "era": "2024", "arch": "x86-64"},
    {"id": "intel_xeon_e5_2699v4", "label": "Intel Xeon E5-2699 v4", "era": "2016", "arch": "x86-64"},
    {"id": "intel_xeon_scalable_8280", "label": "Intel Xeon Platinum 8280", "era": "2019", "arch": "x86-64"},
    {"id": "intel_atom_z530", "label": "Intel Atom Z530", "era": "2008", "arch": "x86-32"},
    {"id": "intel_quark_x1000", "label": "Intel Quark X1000", "era": "2013", "arch": "x86-32"},
    {"id": "intel_n100", "label": "Intel Processor N100", "era": "2023", "arch": "x86-64"},
    {"id": "intel_n305", "label": "Intel Processor N305", "era": "2023", "arch": "x86-64"},
)

AMD_CPUS: tuple[dict[str, str], ...] = (
    {"id": "amd_am386", "label": "AMD Am386", "era": "1991", "arch": "x86-32"},
    {"id": "amd_k5", "label": "AMD K5", "era": "1996", "arch": "x86-32"},
    {"id": "amd_k6", "label": "AMD K6", "era": "1997", "arch": "x86-32"},
    {"id": "amd_k6_2", "label": "AMD K6-2", "era": "1998", "arch": "x86-32"},
    {"id": "amd_k7_athlon", "label": "AMD Athlon (K7)", "era": "1999", "arch": "x86-32"},
    {"id": "amd_k8_athlon64", "label": "AMD Athlon 64 (K8)", "era": "2003", "arch": "x86-64"},
    {"id": "amd_phenom_ii", "label": "AMD Phenom II", "era": "2008", "arch": "x86-64"},
    {"id": "amd_fx_8350", "label": "AMD FX-8350", "era": "2012", "arch": "x86-64"},
    {"id": "amd_ryzen_3_1200", "label": "AMD Ryzen 3 1200", "era": "2017", "arch": "x86-64"},
    {"id": "amd_ryzen_5_1600", "label": "AMD Ryzen 5 1600", "era": "2017", "arch": "x86-64"},
    {"id": "amd_ryzen_7_1700", "label": "AMD Ryzen 7 1700", "era": "2017", "arch": "x86-64"},
    {"id": "amd_ryzen_9_3900x", "label": "AMD Ryzen 9 3900X", "era": "2019", "arch": "x86-64"},
    {"id": "amd_ryzen_9_5950x", "label": "AMD Ryzen 9 5950X", "era": "2020", "arch": "x86-64"},
    {"id": "amd_ryzen_9_7950x", "label": "AMD Ryzen 9 7950X", "era": "2022", "arch": "x86-64"},
    {"id": "amd_ryzen_9_9950x", "label": "AMD Ryzen 9 9950X", "era": "2024", "arch": "x86-64"},
    {"id": "amd_epyc_7742", "label": "AMD EPYC 7742", "era": "2019", "arch": "x86-64"},
    {"id": "amd_epyc_9654", "label": "AMD EPYC 9654", "era": "2022", "arch": "x86-64"},
    {"id": "amd_epyc_9965", "label": "AMD EPYC 9965", "era": "2024", "arch": "x86-64"},
    {"id": "amd_threadripper_3970x", "label": "AMD Ryzen Threadripper 3970X", "era": "2019", "arch": "x86-64"},
    {"id": "amd_threadripper_7980x", "label": "AMD Ryzen Threadripper 7980X", "era": "2023", "arch": "x86-64"},
    {"id": "amd_a10_7850k", "label": "AMD A10-7850K APU", "era": "2014", "arch": "x86-64"},
    {"id": "amd_ryzen_ai_9_hx_370", "label": "AMD Ryzen AI 9 HX 370", "era": "2024", "arch": "x86-64"},
)


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


def _catalog_row(
    *,
    cid: str,
    label: str,
    vendor: str,
    company: str,
    family: str,
    arch: str = "",
    bits: int | str = 0,
    mfg_date_start: str = "",
    source: str = "catalog",
    **extra: Any,
) -> dict[str, Any]:
    return {
        "id": cid,
        "label": label,
        "vendor": vendor,
        "company": company,
        "family": family,
        "arch": arch or family,
        "bits": int(bits) if str(bits).isdigit() else bits,
        "mfg_date_start": mfg_date_start or extra.get("era", ""),
        "source": source,
        "address_map": extra.get("address_map", ""),
        "schematic_blueprint": extra.get("schematic_blueprint", f"{label} — catalog entry; see detailed dies for blueprint text."),
        "ai_detail": extra.get("ai_detail", f"Library catalog: {label} ({vendor})."),
        "diagram_hint": extra.get("diagram_hint", f"{family}:{cid}"),
        "combinatorics_leaf": extra.get("combinatorics_leaf") or f"cpu:{family}:{cid}",
        **{k: v for k, v in extra.items() if k not in ("era",)},
    }


def _expand_catalog(seed: dict[str, Any]) -> list[dict[str, Any]]:
    templates = seed.get("catalog_templates") or {}
    rows: list[dict[str, Any]] = []
    detailed_ids = {str(d.get("id")) for d in (seed.get("detailed") or []) if isinstance(d, dict)}

    if templates.get("expand_arm"):
        for arm in ARM_CORES:
            cid = f"arm_{arm['id']}"
            if cid in detailed_ids:
                continue
            rows.append(_catalog_row(
                cid=cid,
                label=arm["label"],
                vendor="ARM",
                company="ARM Ltd.",
                family="arm",
                arch=arm.get("arch", ""),
                bits=arm.get("bits", 32),
                mfg_date_start=arm.get("era", ""),
                source="arm_catalog",
            ))

    if templates.get("expand_apple"):
        for ap in APPLE_CHIPS:
            cid = ap["id"]
            if cid in detailed_ids:
                continue
            rows.append(_catalog_row(
                cid=cid,
                label=ap["label"],
                vendor="Apple",
                company="Apple Inc.",
                family="apple_silicon",
                arch="ARM64",
                bits=ap.get("bits", 64),
                mfg_date_start=ap.get("era", ""),
                source="apple_catalog",
                address_map="Apple SoC unified memory map — see Secure Enclave island.",
            ))

    if templates.get("expand_mobile"):
        for mob in MOBILE_SOCS:
            cid = mob["id"]
            if cid in detailed_ids:
                continue
            rows.append(_catalog_row(
                cid=cid,
                label=mob["label"],
                vendor=mob.get("vendor", "Mobile"),
                company=mob.get("vendor", "Mobile"),
                family="mobile_soc",
                arch="ARM64",
                bits=64,
                mfg_date_start=mob.get("era", ""),
                source="mobile_catalog",
            ))

    if templates.get("expand_intel"):
        for cpu in INTEL_CPUS:
            cid = cpu["id"]
            if cid in detailed_ids:
                continue
            rows.append(_catalog_row(
                cid=cid,
                label=cpu["label"],
                vendor="Intel",
                company="Intel Corporation",
                family="x86_intel",
                arch=cpu.get("arch", "x86-64"),
                bits=64 if "64" in cpu.get("arch", "") else 32,
                mfg_date_start=cpu.get("era", ""),
                source="intel_catalog",
                address_map="Real-mode 0–1MiB · APIC MMIO 0xFEE0_0000 · PCIe ECAM 0xE000_0000",
            ))

    if templates.get("expand_amd"):
        for cpu in AMD_CPUS:
            cid = cpu["id"]
            if cid in detailed_ids:
                continue
            rows.append(_catalog_row(
                cid=cid,
                label=cpu["label"],
                vendor="AMD",
                company="Advanced Micro Devices",
                family="x86_amd",
                arch=cpu.get("arch", "x86-64"),
                bits=64 if "64" in cpu.get("arch", "") else 32,
                mfg_date_start=cpu.get("era", ""),
                source="amd_catalog",
                address_map="IFetch 0xFFFF_F000 reset vector · IOMMU MMIO · Infinity Fabric link map",
            ))

    return rows


def _ironclad_chips_rows() -> list[dict[str, Any]]:
    chip_py = INSTALL / "lib" / "field-ironclad-chips-combinatorics.py"
    if not chip_py.is_file():
        return []
    try:
        spec = importlib.util.spec_from_file_location("field_ironclad_chips_lib", chip_py)
        if not spec or not spec.loader:
            return []
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "build_ironclad_chips_combinatorics"):
            bat = mod.build_ironclad_chips_combinatorics()
            out: list[dict[str, Any]] = []
            for chip in bat.get("chips") or []:
                cid = str(chip.get("id") or "")
                out.append(_catalog_row(
                    cid=f"chip_{cid}" if not cid.startswith("chip_") else cid,
                    label=str(chip.get("label") or cid),
                    vendor=str(chip.get("vendor") or "—"),
                    company=str(chip.get("vendor") or "—"),
                    family=str(chip.get("family") or chip.get("kind") or "chips"),
                    bits=chip.get("bits") or 0,
                    source="ironclad_chips",
                    combinatorics_leaf=chip.get("combinatorics_leaf"),
                    path_pct=chip.get("path_pct"),
                    band=chip.get("band"),
                ))
            return out
    except Exception:
        pass
    return []


def _balance_mod() -> Any | None:
    path = INSTALL / "lib" / "field-combinatronic-balance.py"
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("cpu_bal", path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    except Exception:
        pass
    return None


def build_library(*, force: bool = False) -> dict[str, Any]:
    import time
    t0 = time.perf_counter()
    bal = _balance_mod()
    entry: dict[str, Any] = {}
    if bal and hasattr(bal, "combinatoric_entry"):
        entry = bal.combinatoric_entry("cpu", refresh=False, force=force, battery_path=LIBRARY)
        if entry.get("skip_build") and entry.get("cached_doc"):
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
            if hasattr(bal, "record_cycle"):
                bal.record_cycle(reorganized=False, elapsed_ms=elapsed_ms)
            out = dict(entry["cached_doc"])
            out["fast_path"] = True
            out["balance_hold"] = True
            out["balance_gate"] = entry.get("gate")
            out["elapsed_ms"] = elapsed_ms
            return out
    seed = _load(SEED, {})
    entries: list[dict[str, Any]] = []
    seen: set[str] = set()

    for row in seed.get("detailed") or []:
        if not isinstance(row, dict) or not row.get("id"):
            continue
        cid = str(row["id"])
        seen.add(cid)
        entries.append({**row, "source": row.get("source") or "seed_detailed", "detailed": True})

    for row in _expand_catalog(seed):
        if row["id"] in seen:
            continue
        seen.add(row["id"])
        entries.append(row)

    for row in _ironclad_chips_rows():
        if row["id"] in seen:
            continue
        seen.add(row["id"])
        entries.append({**row, "detailed": False})

    by_family: dict[str, int] = {}
    for e in entries:
        fam = str(e.get("family") or "unknown")
        by_family[fam] = by_family.get(fam, 0) + 1

    entries.sort(key=lambda e: (str(e.get("family") or ""), str(e.get("label") or "")))
    for row in entries:
        row["combinatronic"] = True
    gate = entry.get("gate") or {}
    if bal and hasattr(bal, "stamp_optimized"):
        entries = bal.stamp_optimized(entries, balanced=bool(gate.get("balanced")))
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    result = {
        "schema": "field-cpu-library/v1",
        "updated": _now(),
        "motto": "Every CPU make and model — ARM, Mac, mobile, x86, retro — library database.",
        "ok": True,
        "counts": {
            "total": len(entries),
            "detailed": sum(1 for e in entries if e.get("detailed")),
            "by_family": by_family,
            "arm": by_family.get("arm", 0),
            "apple_silicon": by_family.get("apple_silicon", 0),
            "mobile_soc": by_family.get("mobile_soc", 0),
            "x86_intel": by_family.get("x86_intel", 0),
            "x86_amd": by_family.get("x86_amd", 0),
        },
        "entries": entries,
        "elapsed_ms": elapsed_ms,
        "balance_gate": gate or None,
        "combinatronic": True,
        "all_data_combinatronic": True,
        "optimized_combinatronic": bool(gate.get("balanced")),
        "entry_synchronous": True,
    }
    if bal and hasattr(bal, "record_cycle"):
        bal.record_cycle(reorganized=not gate.get("skip_reorganize"), elapsed_ms=elapsed_ms)
    return result


def library_json(*, refresh: bool = False) -> dict[str, Any]:
    if refresh or not LIBRARY.is_file():
        return build_library()
    doc = _load(LIBRARY, {})
    if doc.get("entries"):
        return doc
    return build_library()


def search_library(query: str, *, limit: int = 48) -> list[dict[str, Any]]:
    lib = _load(LIBRARY, {}) or build_library()
    q = query.lower().strip()
    if not q:
        return (lib.get("entries") or [])[:limit]
    hits: list[tuple[int, dict[str, Any]]] = []
    for row in lib.get("entries") or []:
        blob = " ".join(str(row.get(k) or "") for k in (
            "id", "label", "vendor", "company", "family", "arch", "ai_detail", "schematic_blueprint"
        )).lower()
        score = 0
        for tok in q.split():
            if tok in blob:
                score += 2
            if tok in str(row.get("id") or "").lower():
                score += 3
        if score:
            hits.append((score, row))
    hits.sort(key=lambda x: (-x[0], x[1].get("label", "")))
    return [h[1] for h in hits[:limit]]


def entry_detail(entry_id: str) -> dict[str, Any] | None:
    lib = _load(LIBRARY, {}) or build_library()
    for row in lib.get("entries") or []:
        if str(row.get("id")) == entry_id:
            return row
    return None


def publish_panel() -> dict[str, Any]:
    lib = build_library()
    _save(LIBRARY, lib)
    panel = {
        "schema": "field-cpu-library-panel/v1",
        "updated": lib.get("updated"),
        "ok": True,
        "counts": lib.get("counts"),
        "sample": (lib.get("entries") or [])[:24],
        "families": sorted((lib.get("counts") or {}).get("by_family", {}).keys()),
    }
    _save(PANEL, panel)
    return {"ok": True, "panel": panel, "library_path": str(LIBRARY)}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        if PANEL.is_file():
            print(json.dumps(_load(PANEL), ensure_ascii=False, indent=2))
        else:
            print(json.dumps(publish_panel().get("panel"), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("build", "publish"):
        print(json.dumps(publish_panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "library":
        print(json.dumps(library_json(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "search":
        q = sys.argv[2] if len(sys.argv) > 2 else ""
        print(json.dumps({"query": q, "hits": search_library(q)}, ensure_ascii=False, indent=2))
        return 0
    if cmd == "detail":
        eid = sys.argv[2] if len(sys.argv) > 2 else ""
        row = entry_detail(eid)
        print(json.dumps(row or {"ok": False, "error": "not_found"}, ensure_ascii=False, indent=2))
        return 0 if row else 1
    if cmd == "verify":
        pub = publish_panel()
        counts = (pub.get("panel") or {}).get("counts") or {}
        ok = counts.get("total", 0) >= 80 and counts.get("arm", 0) >= 20
        print(json.dumps({"ok": ok, "counts": counts}, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    print(json.dumps({"error": "usage", "cmds": ["json", "build", "library", "search", "detail", "verify"]}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())