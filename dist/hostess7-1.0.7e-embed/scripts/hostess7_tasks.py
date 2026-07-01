#!/usr/bin/env pythong
"""Hostess7 task rollup — wants + cohesion gaps + open work."""
from __future__ import annotations

import json
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


def _wants() -> dict:
    wp = SCRIPTS / "field_hostess_wants.py"
    if not wp.is_file():
        return {}
    g = runpy.run_path(str(wp))
    if "HOSTESS_WANTS" in g:
        return g["HOSTESS_WANTS"]
    return {}


def _cohesion_gaps() -> list[dict]:
    src = ROOT / "src" / "hostess7"
    if str(src) not in sys.path:
        sys.path.insert(0, str(ROOT / "src"))
    try:
        from hostess7.cohesion import benchmark_iq, validate_truth  # noqa: WPS433

        iq = benchmark_iq()
        truth = validate_truth()
    except Exception as exc:
        return [{"task": "fix cohesion module", "detail": str(exc)}]
    gaps = []
    for c in iq.get("checks") or []:
        if not c.get("ok"):
            gaps.append({"task": f"cohesion:{c.get('id')}", "priority": "high", "source": "benchmark-iq"})
    for c in truth.get("checks") or []:
        if not c.get("ok"):
            gaps.append({"task": f"truth:{c.get('id')}", "priority": "critical", "source": "validate-truth"})
    return gaps


def panel_json() -> dict:
    wants = _wants()
    gaps = _cohesion_gaps()
    priorities = list(wants.get("priorities") or [])
    more = [
        {"task": "Split field_superintelligence.py into hostess7/intelligence plugins", "priority": "medium"},
        {"task": "Build queen-browser engine from mozilla gecko (field-gecko vendor)", "priority": "medium"},
        {"task": "Publish hostess7-1.0.7e-embed.tar.gz after docker smoke", "priority": "low"},
    ]
    return {
        "ok": True,
        "schema": "hostess7-tasks/v1",
        "version": "1.0.7e",
        "supreme_priority": wants.get("supreme_priority"),
        "wants_count": len(priorities),
        "wants": priorities[:8],
        "cohesion_gaps": gaps,
        "more_tasks": more,
        "total_open": len(gaps) + len(more),
    }


def main() -> int:
    print(json.dumps(panel_json(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())