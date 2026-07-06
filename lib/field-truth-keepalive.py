#!/usr/bin/env python3
"""Truth keepalive — rate every sovereign surface; retruth when below floor."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-truth-keepalive-doctrine.json"
PANEL = STATE / "field-truth-keepalive-panel.json"
SCHEMA = "field-truth-keepalive/v1"


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


def _env() -> dict[str, str]:
    env = {
        **os.environ,
        "NEXUS_INSTALL_ROOT": str(INSTALL),
        "NEXUS_STATE_DIR": str(STATE),
        "NEXUS_FIELD_COLLISION_SOFT_INGRESS": "1",
        "NEXUS_FIELD_DHCP_SOFT_INGRESS": "1",
    }
    return env


def _import_py(rel: str, name: str) -> Any | None:
    path = INSTALL / rel
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    except Exception:
        pass
    return None


def _cached_panel(filename: str) -> dict[str, Any]:
    doc = _load(STATE / filename, {})
    if doc:
        doc = dict(doc)
        doc["from_cache"] = True
    return doc


def _run(rel: str, args: list[str] | None = None, *, timeout: int = 120, cache: str | None = None) -> dict[str, Any]:
    path = INSTALL / rel
    if not path.is_file():
        return {"ok": False, "error": "missing", "script": rel}
    py = os.environ.get("PYTHON", "python3")
    if rel.endswith(".sh"):
        cmd = ["bash", str(path), *(args or [])]
        cwd = str(INSTALL)
    else:
        cmd = [py, str(path), *(args or [])]
        cwd = str(INSTALL)
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            env=_env(),
            check=False,
        )
        raw = (proc.stdout or "").strip()
        if raw.startswith("{"):
            out = json.loads(raw)
            out.setdefault("ok", proc.returncode == 0)
            out["_rc"] = proc.returncode
            return out
        return {"ok": proc.returncode == 0, "raw": raw[:500], "_rc": proc.returncode, "script": rel}
    except subprocess.TimeoutExpired:
        if cache:
            cached = _cached_panel(cache)
            if cached:
                cached["ok"] = cached.get("ok", True)
                cached["timeout_fallback"] = True
                return cached
        return {"ok": False, "error": "timeout", "script": rel}
    except (OSError, json.JSONDecodeError) as exc:
        if cache:
            cached = _cached_panel(cache)
            if cached:
                cached["timeout_fallback"] = True
                return cached
        return {"ok": False, "error": str(exc), "script": rel}


def _truth_mod() -> Any | None:
    return _import_py("lib/hostess7-truth-rating.py", "truth_keepalive_rating")


def _score_surface(surface_id: str, doc: dict[str, Any], floor: float) -> dict[str, Any]:
    if doc.get("truth_score") is not None:
        pct = float(doc["truth_score"])
    elif doc.get("truth_percent") is not None:
        pct = float(doc["truth_percent"])
    elif doc.get("assurance_pct") is not None:
        pct = float(doc["assurance_pct"])
    elif doc.get("ironclad_sealed") or doc.get("ironclad_grounded"):
        pct = 72.0
    elif doc.get("ok") is False:
        pct = 18.0
    else:
        summary = json.dumps(
            {k: doc.get(k) for k in ("ok", "schema", "motto", "boss", "counts", "lanes", "everyone_total") if k in doc},
            ensure_ascii=False,
        )[:3500]
        rating = _truth_mod()
        if rating and hasattr(rating, "rate_response"):
            try:
                rated = rating.rate_response(
                    summary or surface_id,
                    question=f"Truth keepalive witness: {surface_id}",
                    context={"instant": True, "kind": "truth_keepalive", "surface": surface_id},
                    instant=True,
                )
                pct = float(
                    rated.get("truth_percent")
                    or rated.get("truth_score")
                    or rated.get("assurance_pct")
                    or 50
                )
            except Exception:
                pct = 50.0 if doc.get("ok") is not False else 22.0
        else:
            pct = 55.0 if doc.get("ok") is not False else 25.0
    held = pct >= floor and doc.get("ok") is not False
    return {
        "surface": surface_id,
        "truth_pct": round(pct, 1),
        "floor_pct": floor,
        "held": held,
        "needs_retruth": not held,
        "ok": doc.get("ok"),
    }


def _retruth_hooks(surface_id: str, doc: dict[str, Any], doctrine: dict[str, Any]) -> list[dict[str, Any]]:
    if doc.get("ok") is not False:
        return []
    out: list[dict[str, Any]] = []
    for hook in doctrine.get("retruth_hooks") or []:
        if str(hook.get("when") or "") != surface_id:
            continue
        script = str(hook.get("script") or "")
        args = list(hook.get("args") or [])
        if not script:
            continue
        result = _run(script, args, timeout=90 if script.endswith(".sh") else 60)
        out.append({"hook": script, "args": args, **result})
    return out


def _verify_h7t_chamber() -> dict[str, Any]:
    h7t = _import_py("lib/field-h7t-truth.py", "h7t_keepalive")
    chamber = STATE / "h7t-chamber"
    if not chamber.is_dir() or not h7t:
        return {"ok": True, "chamber_count": 0, "verified": 0, "retruthed": 0}
    verified = 0
    retruthed = 0
    errors: list[str] = []
    for fp in sorted(chamber.glob("*.h7t")):
        try:
            data = fp.read_bytes()
            if hasattr(h7t, "unpack_h7t"):
                h7t.unpack_h7t(data)
                verified += 1
        except Exception as exc:
            errors.append(f"{fp.name}:{str(exc)[:80]}")
            retruthed += 1
    return {
        "ok": len(errors) == 0,
        "chamber_count": len(list(chamber.glob("*.h7t"))),
        "verified": verified,
        "retruthed": retruthed,
        "errors": errors[:8],
    }


def keepalive(*, write: bool = True, retruth: bool = True) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    pol = doctrine.get("policy") or {}
    max_passes = int(pol.get("max_retruth_passes") or 2)
    surfaces_out: list[dict[str, Any]] = []
    retruth_ran = 0
    held_count = 0
    drift_count = 0

    for spec in doctrine.get("surfaces") or []:
        sid = str(spec.get("id") or "surface")
        script = str(spec.get("script") or "")
        args = list(spec.get("args") or [])
        floor = float(spec.get("floor") or doctrine.get("truth_floor_pct") or 40)
        timeout = int(spec.get("timeout") or 60)
        cache = str(spec.get("cache") or "") or None
        if not script:
            continue
        if cache and os.environ.get("NEXUS_TRUTH_KEEPALIVE_FAST", "").strip().lower() in ("1", "yes", "on"):
            doc = _cached_panel(cache) or {"ok": False, "error": "cache_miss", "cache": cache}
        else:
            doc = _run(script, args, timeout=timeout, cache=cache)
        score = _score_surface(sid, doc, floor)
        hooks: list[dict[str, Any]] = []
        if retruth and score.get("needs_retruth") and retruth_ran < max_passes:
            hooks = _retruth_hooks(sid, doc, doctrine)
            doc = _run(script, args, timeout=timeout, cache=cache)
            score = _score_surface(sid, doc, floor)
            score["retruth_pass"] = True
            retruth_ran += 1
        if score.get("held"):
            held_count += 1
        else:
            drift_count += 1
        slim = {"ok": doc.get("ok"), "schema": doc.get("schema")}
        if sid == "everyone_counter":
            slim["everyone_total"] = doc.get("everyone_total")
        if sid == "device_map":
            slim["stats"] = doc.get("stats")
        surfaces_out.append({**score, "result": slim, "hooks": hooks})

    chamber = _verify_h7t_chamber()
    everyone = next((s for s in surfaces_out if s.get("surface") == "everyone_counter"), {})
    device = next((s for s in surfaces_out if s.get("surface") == "device_map"), {})

    out = {
        "ok": drift_count == 0 or held_count >= len(surfaces_out) // 2,
        "schema": SCHEMA,
        "updated": _utc(),
        "title": doctrine.get("title"),
        "motto": doctrine.get("motto"),
        "boss": doctrine.get("boss", "hostess7"),
        "sole_internet": True,
        "policy": pol,
        "held_count": held_count,
        "drift_count": drift_count,
        "surface_count": len(surfaces_out),
        "retruth_passes": retruth_ran,
        "surfaces": surfaces_out,
        "h7t_chamber": chamber,
        "summary": {
            "everyone_total": (everyone.get("result") or {}).get("everyone_total"),
            "devices_mapped": (device.get("result") or {}).get("stats"),
            "all_held": drift_count == 0,
            "retruth_active": bool(retruth),
        },
        "api": doctrine.get("api", "/api/field-truth-keepalive"),
        "cycle_hash": hashlib.sha256(
            json.dumps(surfaces_out, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()[:16],
    }
    if write:
        _save(PANEL, out)
    return out


def panel() -> dict[str, Any]:
    cached = _load(PANEL, {})
    if cached.get("schema") == SCHEMA:
        return cached
    return keepalive(write=True)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    no_retruth = "--no-retruth" in sys.argv
    if cmd in ("json", "panel", "status"):
        print(json.dumps(panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("keepalive", "cycle", "pulse", "run"):
        out = keepalive(write=True, retruth=not no_retruth)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("ok") else 1
    print(json.dumps({
        "usage": "field-truth-keepalive.py [json|keepalive|cycle] [--no-retruth]",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())