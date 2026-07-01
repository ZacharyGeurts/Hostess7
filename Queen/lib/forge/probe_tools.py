"""Field Technology probes — GPU + compiler surface for Queen RTX."""
from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from forge.common import ok_result
from forge.engine import ForgeContext, ForgeEngine, ForgeResult
from forge.hostess_tools import probe_compilers


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _lspci_display() -> list[str]:
    try:
        out = subprocess.run(
            ["lspci", "-nn"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if out.returncode != 0:
            return []
        return [
            ln for ln in out.stdout.splitlines()
            if re.search(r"vga|3d|display", ln, re.I)
        ]
    except (OSError, subprocess.TimeoutExpired):
        return []


def _vulkan_summary() -> str:
    try:
        out = subprocess.run(
            ["vulkaninfo", "--summary"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if out.returncode != 0:
            return ""
        lines = out.stdout.splitlines()
        block: list[str] = []
        for ln in lines:
            if re.match(r"GPU\d", ln):
                block.append(ln)
            elif block and ln.strip():
                block.append(ln)
            if len(block) > 60:
                break
        return "\n".join(block)
    except (OSError, subprocess.TimeoutExpired):
        return ""


def gpu_probe_doc(ctx: ForgeContext) -> dict:
    pci = _lspci_display()
    arc = sum(1 for ln in pci if "8086" in ln and re.search(r"vga|3d|display", ln, re.I))
    nvidia = sum(1 for ln in pci if "10de" in ln.lower() or "nvidia" in ln.lower())
    return {
        "updated": _ts(),
        "pci_display": pci,
        "intel_arc_count": arc,
        "nvidia_count": nvidia,
        "vulkan_summary": _vulkan_summary(),
        "queen_env": {
            "arc_le": "QUEEN_PREFER_ARC_LE=1 AMOURANTHRTX_FORCED_VENDOR=0x8086 QUEEN_GPU_INDEX=0",
            "nvidia_rtx": "AMOURANTHRTX_FORCED_VENDOR=0x10DE QUEEN_GPU_INDEX=0",
            "field_gpu": "QUEEN_FIELD_GPU=1 QUEEN_FIELD_SURFACE=1",
        },
        "compilers": probe_compilers(ctx),
    }


def check_gpu_probe(ctx: ForgeContext) -> bool:
    return (ctx.queen / "data" / "gpu-probe.json").is_file()


def run_gpu_probe(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    engine.log("=== forge:gpu_probe — Field Technology GPU surface ===")
    doc = gpu_probe_doc(ctx)
    for ln in doc.get("pci_display", [])[:8]:
        engine.log(f"  pci: {ln}")
    engine.log(f"  intel_arc={doc['intel_arc_count']} nvidia={doc['nvidia_count']}")
    out = ctx.queen / "data" / "gpu-probe.json"
    out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    engine.log(f"  wrote {out.name}")
    return ok_result(engine, "gpu_probe", f"arc={doc['intel_arc_count']}")


PROBE_TOOLS: dict[str, tuple[str, str, object, object, str | None]] = {
    "gpu_probe": (
        "Probe Vulkan/PCI GPUs for Queen RTX",
        "field-probe",
        run_gpu_probe,
        check_gpu_probe,
        "scripts/queen-gpu-probe.sh",
    ),
}