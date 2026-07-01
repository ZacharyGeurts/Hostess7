#!/usr/bin/env pythong
"""Sense package meld — witness + protect Final_Eye, Ear, Mouth, Redata, Hostess7.

Non-destructive: sibling repos stay in SG/; Hostess7 brain witnessed read-only.
flock + fsync + triple mirror. Shallow HTTP probe with TTL cache — no probe storms.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
DOCTRINE = INSTALL / "data" / "field-sense-package-doctrine.json"
PANEL = STATE / "field-sense-package-panel.json"
RUNTIME = STATE / "field-sense-package-runtime.json"
LEDGER = STATE / "field-sense-package-ledger.jsonl"
LOCK = STATE / "field-sense-package.lock"
REDUNDANT = STATE / "sense-package-redundant"
MANIFEST = STATE / "field-sense-package-manifest.json"

_GEN = 0
_PROBE_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        import importlib.util
        _p = Path(__file__).resolve().parent / "sovereign-clock.py"
        _s = importlib.util.spec_from_file_location("sovereign_clock", _p)
        if not _s or not _s.loader:
            raise ImportError("sovereign-clock.py missing")
        _SOVEREIGN_CLOCK_MOD = importlib.util.module_from_spec(_s)
        _s.loader.exec_module(_SOVEREIGN_CLOCK_MOD)
    return _SOVEREIGN_CLOCK_MOD.utc_z()


_SOVEREIGN_CLOCK_MOD = None



def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _fsync_write(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        fh.write(payload)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def _append_ledger(row: dict[str, Any]) -> None:
    line = json.dumps(row, ensure_ascii=False) + "\n"
    with LEDGER.open("a", encoding="utf-8") as fh:
        fh.write(line)
        fh.flush()
        try:
            os.fsync(fh.fileno())
        except OSError:
            pass


def _mirror(doc: dict[str, Any]) -> None:
    REDUNDANT.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    for name in ("field-sense-package-panel.json", "field-sense-package-runtime.json"):
        for suffix in ("", ".bak"):
            (REDUNDANT / f"{name}{suffix}").write_text(payload, encoding="utf-8")


def _sg_root() -> Path:
    env = os.environ.get("SG_ROOT", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return INSTALL.parent.parent.resolve()


def _resolve_root(env_key: str, *candidates: Path) -> Path | None:
    env = os.environ.get(env_key, "").strip()
    if env:
        p = Path(env).expanduser().resolve()
        if p.is_dir():
            return p
    sg = _sg_root()
    for rel in candidates:
        p = (sg / rel) if not rel.is_absolute() else rel
        if p.is_dir():
            return p.resolve()
    return None


def _final_eye_root() -> Path | None:
    sp = _sg_paths()
    if sp:
        root = sp.final_eye_root()
        if root.is_dir():
            return root
    return _resolve_root("FINAL_EYE_ROOT", Path("Final_Eye"), INSTALL / "Final_Eye")


def _final_ear_root() -> Path | None:
    return _resolve_root("FINAL_EAR_ROOT", Path("Final_Ear"))


def _hostess7_root() -> Path | None:
    return _resolve_root("HOSTESS7_ROOT", Path("Hostess7"))


def _sg_paths():
    import importlib.util

    py = INSTALL / "lib" / "sg_paths.py"
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location("sg_paths", py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _hostess7_team_field() -> Path:
    sp = _sg_paths()
    if sp:
        return sp.hostess7_team_field()
    env = os.environ.get("HOSTESS7_TEAM_FIELD", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    h7 = _hostess7_root()
    return (h7 / "cache" / "fieldstorage") if h7 else Path("cache/fieldstorage")


def _hostess7_team1_field() -> Path | None:
    sp = _sg_paths()
    if sp:
        return sp.hostess7_team1_field()
    env = os.environ.get("HOSTESS7_TEAM1_FIELD", "").strip()
    return Path(env).expanduser().resolve() if env else None


def _hostess7_nexus_cache_field() -> Path:
    sp = _sg_paths()
    if sp:
        return sp.hostess7_nexus_cache_field()
    env = os.environ.get("HOSTESS7_NEXUS_CACHE", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return Path("/var/lib/nexus-shield/hostess7-cache/fieldstorage")


def _hostess7_brain_score(root: Path) -> int:
    if not root.is_dir():
        return 0
    score = 0
    if (root / "brain").is_dir():
        score += 5
    if (root / "brain" / "library" / "manifest.json").is_file():
        score += 80
    if (root / "brain" / "library" / "search_index.jsonl").is_file():
        score += 40
    if (root / "brain" / "superintel").is_dir():
        score += 50
    if (root / "brain" / "superintel" / "context.json").is_file():
        score += 30
    if (root / "brain" / "sdf").is_dir():
        score += 20
    return score


def _brain_dir_bytes(brain_dir: Path | None) -> int:
    if not brain_dir or not brain_dir.is_dir():
        return 0
    total = 0
    try:
        for p in brain_dir.rglob("*"):
            if p.is_file():
                try:
                    total += p.stat().st_size
                except OSError:
                    pass
    except OSError:
        return 0
    return total


def _hostess7_all_brain_candidates(h7: Path | None) -> list[dict[str, Any]]:
    """Read-only scan of every known Hostess7 brain root — no relocate, no sync."""
    if not h7:
        return []
    cache = h7 / "cache" / "fieldstorage"
    team_env = os.environ.get("HOSTESS7_TEAM_FIELD", "").strip()
    team = _hostess7_team_field() if team_env else None
    entries: list[tuple[str, Path | None]] = []
    if team and str(team) != str(cache):
        entries.append(("team", team))
    elif team_env:
        entries.append(("team", team))
    team1 = _hostess7_team1_field()
    if team1:
        entries.append(("team1", team1))
    entries.extend([
        ("cache", cache),
        ("nexus_cache", _hostess7_nexus_cache_field()),
    ])
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for label, candidate in entries:
        if not candidate:
            continue
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        if not candidate.is_dir():
            out.append({
                "label": label,
                "path": key,
                "present": False,
                "mounted": False,
                "score": 0,
                "brain_bytes": 0,
                "sdf_segments": 0,
            })
            continue
        brain_dir = candidate / "brain"
        score = _hostess7_brain_score(candidate)
        out.append({
            "label": label,
            "path": key,
            "present": True,
            "mounted": brain_dir.is_dir() and score > 0,
            "score": score,
            "brain_bytes": _brain_dir_bytes(brain_dir if brain_dir.is_dir() else None),
            "sdf_segments": _count_glob(brain_dir / "sdf", "*.json") if brain_dir.is_dir() else 0,
            "has_manifest": (brain_dir / "library" / "manifest.json").is_file(),
            "has_superintel": (brain_dir / "superintel" / "context.json").is_file(),
        })
    out.sort(key=lambda c: (c.get("score") or 0, c.get("brain_bytes") or 0), reverse=True)
    return out


def _hostess7_best_brain_root(h7: Path | None) -> tuple[Path | None, int, str]:
    if not h7:
        return None, 0, "missing"
    candidates = _hostess7_all_brain_candidates(h7)
    for row in candidates:
        if row.get("present") and int(row.get("score") or 0) > 0:
            return Path(row["path"]), int(row["score"]), str(row["label"])
    return None, 0, "none"


def _file_witness(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"present": False, "path": str(path)}
    try:
        data = path.read_bytes()
        return {
            "present": True,
            "path": str(path),
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "mtime": path.stat().st_mtime,
        }
    except OSError:
        return {"present": False, "path": str(path)}


def _count_glob(root: Path, pattern: str, *, limit: int = 5000) -> int:
    if not root.is_dir():
        return 0
    count = 0
    try:
        for p in root.rglob(pattern):
            if p.is_file():
                count += 1
                if count >= limit:
                    break
    except OSError:
        return 0
    return count


def _witness_hostess7(h7: Path | None) -> dict[str, Any]:
    if not h7 or not h7.is_dir():
        return {"product": "Hostess7", "present": False, "root": None}
    status = _load(h7 / "docs" / "status.json", {})
    neural = _load(h7 / "data" / "hostess7-neural-stack.json", {})
    brain_candidates = _hostess7_all_brain_candidates(h7)
    brain_root, brain_score, brain_source = _hostess7_best_brain_root(h7)
    brain_dir = (brain_root / "brain") if brain_root else None
    manifest = _file_witness(brain_dir / "library" / "manifest.json") if brain_dir else {"present": False}
    context = _file_witness(brain_dir / "superintel" / "context.json") if brain_dir else {"present": False}
    sdf_segments = _count_glob(brain_dir / "sdf", "*.json") if brain_dir else 0
    nexus_ctx = _load(INSTALL / "data" / "field-brain" / "context.json", {})
    live = bool(brain_score >= 100 and manifest.get("present"))
    smart_row = brain_candidates[0] if brain_candidates and brain_candidates[0].get("present") else {}
    smart_one = {
        "label": smart_row.get("label") or brain_source,
        "path": smart_row.get("path") or (str(brain_root) if brain_root else None),
        "score": int(smart_row.get("score") or brain_score),
        "brain_bytes": int(smart_row.get("brain_bytes") or 0),
        "sdf_segments": int(smart_row.get("sdf_segments") or sdf_segments),
        "reason": "best_of_team_team1_cache_nexus",
    } if brain_score > 0 else None
    return {
        "product": "Hostess7",
        "present": True,
        "root": str(h7),
        "version": str(status.get("version") or neural.get("schema") or "hostess7"),
        "codename": "watchguard-angel",
        "bridge": "lib/hostess7-field.sh",
        "brain_sync": "lib/field-brain-sync.sh",
        "heaven_hell": "lib/heaven-hell.py",
        "brain_protected": True,
        "brain_relocate": False,
        "brain_witness_only": True,
        "brain_candidates": brain_candidates,
        "smart_one": smart_one,
        "brain_roots": {
            "team": next((c["path"] for c in brain_candidates if c.get("label") == "team" and c.get("present")), None),
            "team1": next((c["path"] for c in brain_candidates if c.get("label") == "team1" and c.get("present")), None),
            "cache": next((c["path"] for c in brain_candidates if c.get("label") == "cache" and c.get("present")), None),
            "nexus_cache": next((c["path"] for c in brain_candidates if c.get("label") == "nexus_cache" and c.get("present")), None),
            "chosen": str(brain_root) if brain_root else None,
            "source": brain_source,
        },
        "brain_score": brain_score,
        "brain_live": live,
        "live": live,
        "manifest": manifest,
        "superintel_context": context,
        "sdf_segments": sdf_segments,
        "library_h7": status.get("library_h7"),
        "neural_stack": neural.get("schema"),
        "nexus_field_brain": nexus_ctx.get("brain_root"),
        "team_mounted": any(c.get("label") == "team" and c.get("mounted") for c in brain_candidates),
        "ocr_brain": _witness_hostess7_ocr_brain(),
    }


def _witness_hostess7_ocr_brain() -> dict[str, Any]:
    """Hostess 7 OCR training corpora — preserved under NEXUS_STATE_DIR, fed by Final_Eye."""
    chambers = (
        ("calculator", "hostess7-calculator-ocr-corpus.json", "hostess7-calculator-ocr-train.json"),
        ("biology", "hostess7-biology-ocr-corpus.json", "hostess7-biology-ocr-train.json"),
        ("engineering", "hostess7-engineering-ocr-corpus.json", "hostess7-engineering-ocr-train.json"),
        ("combat", "hostess7-combat-ocr-corpus.json", "hostess7-combat-ocr-train.json"),
        ("mos", "hostess7-mos-ocr-corpus.json", "hostess7-mos-ocr-train.json"),
        ("programming", "hostess7-programming-ocr-corpus.json", "hostess7-programming-ocr-train.json"),
        ("g16", "hostess7-g16-ocr-corpus.json", "hostess7-g16-ocr-train.json"),
        ("codecraft", "hostess7-codecraft-ocr-corpus.json", "hostess7-codecraft-ocr-train.json"),
        ("geography", "hostess7-geography-ocr-corpus.json", "hostess7-geography-ocr-train.json"),
        ("music", "hostess7-music-ocr-corpus.json", "hostess7-music-ocr-train.json"),
        ("imaging", "hostess7-imaging-ocr-corpus.json", "hostess7-imaging-ocr-train.json"),
        ("sense", "hostess7-sense-ocr-corpus.json", "hostess7-sense-ocr-train.json"),
        ("reality_physics", "hostess7-reality_physics-ocr-corpus.json", "hostess7-reality_physics-ocr-train.json"),
    )
    rows: list[dict[str, Any]] = []
    total_candidates = 0
    total_verified = 0
    for chamber, corpus_name, train_name in chambers:
        corpus = _load(STATE / corpus_name, {})
        train = _load(STATE / train_name, {})
        c_count = int(corpus.get("candidate_count") or len(corpus.get("candidates") or []))
        v_count = int(train.get("verified_count") or 0)
        total_candidates += c_count
        total_verified += v_count
        rows.append({
            "chamber": chamber,
            "corpus": str(STATE / corpus_name),
            "corpus_present": (STATE / corpus_name).is_file(),
            "candidate_count": c_count,
            "train_present": (STATE / train_name).is_file(),
            "verified_count": v_count,
            "fluent": bool(train.get("fluent")),
            "mastered": bool(train.get("mastered")),
        })
    return {
        "schema": "hostess7-ocr-brain/v1",
        "preserved": True,
        "final_eye_root": str(_final_eye_root() or ""),
        "chambers": rows,
        "total_candidates": total_candidates,
        "total_verified": total_verified,
        "doctrine": "data/final-eye-plate-doctrine.json#hostess7_ocr_brain",
    }


def _world_redata_root() -> Path | None:
    env = os.environ.get("WORLD_REDATA_ROOT", "").strip()
    if env:
        p = Path(env).expanduser().resolve()
        if (p / "redata" / "cli.py").is_file():
            return p
    sg = _sg_root()
    for candidate in (sg / "World_Redata", sg.parent / "World_Redata"):
        if (candidate / "redata" / "cli.py").is_file():
            return candidate.resolve()
    return None


def _read_version(root: Path | None) -> str:
    if not root:
        return ""
    vf = root / "VERSION"
    try:
        return vf.read_text(encoding="utf-8").strip() if vf.is_file() else ""
    except OSError:
        return ""


def _witness_seal(root: Path | None) -> dict[str, Any]:
    if not root:
        return {"present": False}
    seal_path = root / "data" / "code-seal.json"
    doc = _load(seal_path, {})
    if not doc.get("schema"):
        return {"present": False, "path": str(seal_path)}
    return {
        "present": True,
        "path": str(seal_path),
        "schema": doc.get("schema"),
        "mandate_id": doc.get("mandate_id"),
        "root_seal": doc.get("root_seal"),
        "file_count": doc.get("file_count"),
        "ts": doc.get("ts"),
    }


def _witness_product(root: Path | None, *, product_id: str) -> dict[str, Any]:
    if not root or not root.is_dir():
        return {"product": product_id, "present": False, "root": None}
    w: dict[str, Any] = {
        "product": product_id,
        "present": True,
        "root": str(root),
        "version": _read_version(root),
        "code_seal": _witness_seal(root),
        "has_product_module": (root / "zocr_product.py").is_file(),
        "has_gui": (root / "gui" / "app.py").is_file(),
    }
    manual = root / "data" / "field-manual-index.json"
    if manual.is_file():
        w["field_manual"] = str(manual)
    return w


def _probe_ttl() -> float:
    doc = _load(DOCTRINE, {})
    return float((doc.get("policy") or {}).get("probe_cache_seconds") or 12)


def _http_probe(url: str, *, cache_key: str) -> dict[str, Any]:
    ttl = _probe_ttl()
    now = time.monotonic()
    cached = _PROBE_CACHE.get(cache_key)
    if cached and (now - cached[0]) < ttl:
        return {**cached[1], "cached": True}

    out: dict[str, Any] = {"url": url, "ok": False, "cached": False}
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            body = resp.read(8192).decode("utf-8", errors="replace")
            out["status"] = resp.status
            out["ok"] = 200 <= resp.status < 300
            try:
                out["json"] = json.loads(body)
            except json.JSONDecodeError:
                out["body_preview"] = body[:200]
    except urllib.error.HTTPError as exc:
        out["status"] = exc.code
        out["error"] = f"http_{exc.code}"
    except Exception as exc:
        out["error"] = type(exc).__name__

    _PROBE_CACHE[cache_key] = (now, out)
    return out


def _eye_port() -> int:
    for key in ("FINAL_EYE_PORT",):
        val = os.environ.get(key, "").strip()
        if val.isdigit():
            return int(val)
    return 9479


def _redata_port() -> int:
    val = os.environ.get("WORLD_REDATA_WEB_PORT", "").strip()
    return int(val) if val.isdigit() else 9478


def _witness_redata_live(root: Path | None) -> dict[str, Any]:
    if not root:
        return {"present": False}
    port = _redata_port()
    probe = _http_probe(f"http://127.0.0.1:{port}/api/health", cache_key=f"redata:{port}")
    live = probe.get("ok", False)
    status_doc: dict[str, Any] = {}
    if not live:
        try:
            sys.path.insert(0, str(root))
            from redata.status import live_status  # noqa: WPS433

            status_doc = live_status()
            live = bool(status_doc.get("ok", True))
        except Exception as exc:
            status_doc = {"import_error": type(exc).__name__}
        finally:
            if str(root) in sys.path:
                sys.path.remove(str(root))
    return {
        "present": True,
        "root": str(root),
        "port": port,
        "http_live": probe.get("ok", False),
        "live": live,
        "probe": {k: v for k, v in probe.items() if k != "json"},
        "status": status_doc if status_doc else probe.get("json"),
        "formats": ["WRDT1", "WRZC1", "ZAC7"],
    }


def _witness_ear(root: Path | None) -> dict[str, Any]:
    w = _witness_product(root, product_id="Final_Ear")
    if not w.get("present"):
        return w
    w["bridge"] = "Queen/lib/queen-earball.py"
    w["fusion_ready"] = (root / "zocr_ear_stoard.py").is_file() if root else False
    w["gac1"] = (root / "data" / "sound-registry.json").is_file() if root else False
    w["live"] = w.get("code_seal", {}).get("present", False)
    return w


def _witness_eye(root: Path | None) -> dict[str, Any]:
    w = _witness_product(root, product_id="Final_Eye")
    if not w.get("present"):
        return w
    w["bridge"] = "Queen/lib/queen_final_eye.py"
    w["plate_doctrine"] = "data/final-eye-plate-doctrine.json"
    w["plate_melded"] = bool((STATE / "eye-ear-plate.json").is_file())
    w["ocr_ready"] = (root / "zocr.py").is_file() if root else False
    w["eyeball_bridge"] = "Queen/lib/queen-eyeball.py"
    w["trained"] = True
    w["enhancement_room"] = True
    w["hostess7_ocr_brain"] = _witness_hostess7_ocr_brain()
    port = _eye_port()
    probe = _http_probe(f"http://127.0.0.1:{port}/api/health", cache_key=f"eye:{port}")
    w["port"] = port
    w["http_live"] = probe.get("ok", False)
    w["live"] = probe.get("ok", False)
    w["probe"] = {k: v for k, v in probe.items() if k != "json"}
    if probe.get("json"):
        w["health"] = probe["json"]
    w["motion_track"] = (root / "zocr_eye_motion.py").is_file() if root else False
    return w




def _package_digest(members: dict[str, Any], prev_chain: str) -> str:
    material = json.dumps(members, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(f"{prev_chain}|{material}".encode()).hexdigest()


def _ironclad_sense_goldmine() -> dict[str, Any]:
    """Plate → eye/ear/mouth receipts for sense package meld."""
    ic_py = INSTALL / "lib" / "ironclad-immediate.py"
    if ic_py.is_file():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("ironclad_immediate", ic_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "read_immediate"):
                    doc = mod.read_immediate()
                    gm = doc.get("plate_to_sense") or {}
                    if gm:
                        return gm
                if hasattr(mod, "plate_to_sense_goldmine"):
                    return mod.plate_to_sense_goldmine()
        except Exception:
            pass
    cached = _load(STATE / "ironclad-immediate.json", {})
    return cached.get("plate_to_sense") or {}


def _sense_member_ironclad(member_key: str, goldmine: dict[str, Any]) -> dict[str, Any]:
    mapping = {
        "final_eye": "eye_neural",
        "final_ear": "ear_neural",
        "hostess7": "sense_neural_wire",
    }
    target = mapping.get(member_key)
    members = goldmine.get("members") or {}
    receipt = members.get(target) or {}
    return {
        "ironclad_grounded": bool(goldmine.get("ironclad_grounded")),
        "goldmine": bool(goldmine.get("goldmine")),
        "truth_percent": receipt.get("truth_percent") or goldmine.get("truth_percent"),
        "citation": receipt.get("citation") or goldmine.get("citation"),
        "read_first": bool(receipt.get("read_first") or goldmine.get("read_first")),
        "wire": receipt.get("wire"),
    }


def _plate_meld_link() -> dict[str, Any]:
    rt = _load(STATE / "field-plate-meld-runtime.json", {})
    if rt.get("generation"):
        return {"plate_generation": rt.get("generation"), "chain_hash": rt.get("chain_hash")}
    doc = _load(STATE / "field-plate-meld.json", {})
    return {"plate_generation": doc.get("generation"), "chain_hash": doc.get("chain_hash")}


def _meld_lock() -> int:
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(LOCK), os.O_CREAT | os.O_RDWR, 0o644)
    fcntl.flock(fd, fcntl.LOCK_EX)
    return fd


def _meld_unlock(fd: int) -> None:
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
    except OSError:
        pass


def _verdict(members: dict[str, Any]) -> str:
    eye = members.get("final_eye") or {}
    ear = members.get("final_ear") or {}
    wr = members.get("world_redata") or {}
    h7 = members.get("hostess7") or {}
    present = sum(1 for m in (eye, ear, wr, h7) if m.get("present"))
    if present < 2:
        return "WARN"
    seals_ok = all(
        (m.get("code_seal") or {}).get("present")
        or m.get("product") in ("World_Redata", "Hostess7")
        for m in (eye, ear)
        if m.get("present")
    )
    if not seals_ok:
        return "WARN"
    brain_ok = not h7.get("present") or h7.get("brain_score", 0) >= 50
    if h7.get("present") and not brain_ok:
        return "WATCH"
    live_count = sum(
        1 for m in (eye, ear, wr, h7) if m.get("live") or m.get("http_live") or m.get("brain_live")
    )
    if live_count >= 3 and brain_ok:
        return "GREEN"
    if present >= 4 and brain_ok:
        return "GREEN"
    if present >= 3:
        return "WATCH"
    return "WATCH"


def _witness_obs_field_stack() -> dict[str, Any]:
    """OBS-native sense lane — Scene Guard, tree prune, posterity inspect, threat ledger witness."""
    sg = _sg_root()
    root = sg / "OBS-FieldVoiceFilter"
    home = Path.home()
    plugin_data = home / ".config/obs-studio/plugins/obs-field-voice-filter/data"
    runtime_paths = [
        plugin_data / "field-obs-stack.json",
        root / "data/field-obs-stack.json",
    ]
    stack_doc: dict[str, Any] = {}
    stack_path: Path | None = None
    for p in runtime_paths:
        if p.is_file():
            stack_doc = _load(p, {})
            stack_path = p
            break

    posterity_bridge: dict[str, Any] = {}
    try:
        import importlib.util
        bridge_py = Path(__file__).resolve().parent / "obs-threat-posterity-bridge.py"
        spec = importlib.util.spec_from_file_location("obs_threat_posterity_bridge", bridge_py)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            posterity_bridge = mod.panel_json()
    except Exception:
        posterity_bridge = {}

    posterity_doc = root / "data/field-security-posterity-doctrine.json"
    threat_ledger = plugin_data / "threat-ledger.jsonl"
    if not threat_ledger.is_file():
        threat_ledger = root / "data/threat-ledger.jsonl"

    present = root.is_dir() and (root / "install.sh").is_file()
    threat_summary = (posterity_bridge.get("threat_ledger") or {}).get("summary") or {}
    live = bool(stack_doc) or bool(threat_summary.get("rows")) or posterity_bridge.get("live")
    return {
        "present": present,
        "root": str(root) if present else None,
        "install": "OBS-FieldVoiceFilter/install.sh",
        "runtime_status": str(stack_path) if stack_path else None,
        "stack": stack_doc,
        "live": live,
        "filters": [f.get("id") for f in (stack_doc.get("filters") or []) if isinstance(f, dict)],
        "ai": stack_doc.get("ai") or {},
        "bridges": stack_doc.get("bridges") or posterity_bridge.get("bridges") or {},
        "defaults": stack_doc.get("defaults") or "clean_passthrough",
        "posterity": posterity_bridge.get("posterity") or {},
        "repeat_inspect": posterity_bridge.get("repeat_inspect") or {},
        "threat_ledger_present": threat_ledger.is_file(),
        "threat_summary": threat_summary,
        "posterity_doctrine_sha256": (posterity_bridge.get("posterity") or {}).get("doctrine_sha256"),
        "ironclad": {
            "read_first": True,
            "citation": "ironclad:sense:obs_posterity",
            "wire": "scene_guard → field-tree-prune → field-security-posterity → threat-ledger.jsonl",
            "ear_ref": (posterity_bridge.get("bridges") or {}).get("final_ear"),
            "eye_ref": (posterity_bridge.get("bridges") or {}).get("final_eye"),
        },
    }


def meld(*, link_plates: bool = True) -> dict[str, Any]:
    """Witness all sense products and write protected meld panel."""
    global _GEN
    fd = _meld_lock()
    try:
        prev = _load(RUNTIME, {})
        prev_chain = str(prev.get("chain_hash") or "")
        prev_gen = int(prev.get("generation") or 0)
        _GEN = prev_gen + 1

        eye_root = _final_eye_root()
        ear_root = _final_ear_root()
        wr_root = _world_redata_root()
        h7_root = _hostess7_root()

        members: dict[str, Any] = {
            "final_eye": _witness_eye(eye_root),
            "final_ear": _witness_ear(ear_root),
            "world_redata": _witness_redata_live(wr_root),
            "hostess7": _witness_hostess7(h7_root),
            "obs_field_stack": _witness_obs_field_stack(),
        }
        goldmine = _ironclad_sense_goldmine()
        mouth_receipt = (goldmine.get("members") or {}).get("mouth_neural") or {}
        for key in ("final_eye", "final_ear", "hostess7"):
            if members.get(key):
                members[key]["ironclad"] = _sense_member_ironclad(key, goldmine)
        if goldmine:
            members.setdefault("mouth_neural", {
                "present": True,
                "role": "voice hemisphere — thought≠utterance",
                "bridge": mouth_receipt.get("bridge") or "Final_Mouth/zocr_neural_assist.py",
                "ironclad": {
                    "ironclad_grounded": bool(goldmine.get("ironclad_grounded")),
                    "goldmine": True,
                    "truth_percent": mouth_receipt.get("truth_percent") or goldmine.get("truth_percent"),
                    "citation": mouth_receipt.get("citation") or goldmine.get("citation"),
                    "read_first": True,
                    "wire": mouth_receipt.get("wire"),
                },
            })
        chain = _package_digest(members, prev_chain)
        verdict = _verdict(members)
        plate_link = _plate_meld_link() if link_plates else {}

        protected = {
            "flock": True,
            "fsync": True,
            "triple_mirror": True,
            "destructive_merge": False,
            "seal_witness": {
                k: (members[k].get("code_seal") or {}).get("root_seal")
                for k in ("final_eye", "final_ear")
                if (members[k] or {}).get("present")
            },
            "brain_witness": {
                "hostess7": (members["hostess7"].get("manifest") or {}).get("sha256"),
                "brain_root": (members["hostess7"].get("brain_roots") or {}).get("chosen"),
                "brain_score": members["hostess7"].get("brain_score"),
                "relocate": False,
            },
        }

        inplace = {
            "schema": "field-sense-package-manifest/v1",
            "ts": _now(),
            "policy": "non_destructive",
            "sg_root": str(_sg_root()),
            "members": {k: v.get("root") for k, v in members.items()},
            "plate_generation": plate_link.get("plate_generation"),
        }
        _fsync_write(MANIFEST, json.dumps(inplace, ensure_ascii=False, indent=2) + "\n")

        summary = {
            "verdict": verdict,
            "present_count": sum(1 for m in members.values() if m.get("present")),
            "live_count": sum(
                1 for m in members.values() if m.get("live") or m.get("http_live")
            ),
            "eye_version": members["final_eye"].get("version"),
            "ear_version": members["final_ear"].get("version"),
            "eye_live": members["final_eye"].get("live"),
            "ear_sealed": (members["final_ear"].get("code_seal") or {}).get("present"),
            "eye_plate_melded": bool((STATE / "eye-ear-plate.json").is_file()),
            "redata_live": members["world_redata"].get("live"),
            "hostess_brain_score": members["hostess7"].get("brain_score"),
            "hostess_brain_live": members["hostess7"].get("brain_live"),
            "hostess_brain_source": (members["hostess7"].get("brain_roots") or {}).get("source"),
            "hostess_smart_one": (members["hostess7"].get("smart_one") or {}).get("label"),
            "hostess_brain_candidates": len(members["hostess7"].get("brain_candidates") or []),
            "obs_field_live": members["obs_field_stack"].get("live"),
            "obs_field_filters": len(members["obs_field_stack"].get("filters") or []),
            "ironclad_goldmine_ok": bool(goldmine.get("goldmine_ok")),
            "ironclad_grounded": bool(goldmine.get("ironclad_grounded")),
            "plate_to_sense": bool(goldmine.get("goldmine")),
            "protected": True,
        }

        bus_pack = {
            "eye_live": 1 if summary["eye_live"] else 0,
            "ear_sealed": 1 if summary["ear_sealed"] else 0,
            "eye_plate": 1 if summary.get("eye_plate_melded") else 0,
            "redata_ok": 1 if members["world_redata"].get("present") else 0,
            "hostess_brain": 1 if members["hostess7"].get("brain_live") else 0,
            "hostess_brain_tier": min(int(members["hostess7"].get("brain_score") or 0) // 10, 255),
        }

        doc: dict[str, Any] = {
            "schema": "field-sense-package/v1",
            "ts": _now(),
            "generation": _GEN,
            "motto": str(_load(DOCTRINE, {}).get("motto") or "Sense package meld"),
            "verdict": verdict,
            "protected": protected,
            "chain_hash": chain,
            "prev_chain_hash": prev_chain or None,
            "plate_link": plate_link,
            "members": members,
            "summary": summary,
            "bus_pack": bus_pack,
            "inplace_manifest": str(MANIFEST),
            "bridges": {
                "queen_final_eye": "Queen/lib/queen_final_eye.py",
                "queen_earball": "Queen/lib/queen-earball.py",
                "queen_final_eye_dispatch": "Queen/lib/queen_final_eye.py",
                "queen_sense_neural": "Queen/lib/queen-sense-neural.py",
                "world_redata_converter": "lib/field-drive-converter.py",
                "hostess7_field": "lib/hostess7-field.sh",
                "field_brain_sync": "lib/field-brain-sync.sh",
                "heaven_hell": "lib/heaven-hell.py",
                "ironclad_immediate": "lib/ironclad-immediate.py",
                "obs_field_stack": "OBS-FieldVoiceFilter/install.sh",
            },
            "ironclad_goldmine": goldmine,
            "plate_to_sense": goldmine,
        }
        combo_slice = sense_universal_slice(state_dir=STATE, sense_doc=doc)
        doc["combinatorics"] = combo_slice
        doc["universal_lock"] = bool(combo_slice.get("universal_lock"))

        payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
        _fsync_write(PANEL, payload)
        runtime = {
            "schema": "field-sense-package-runtime/v1",
            "ts": doc["ts"],
            "generation": _GEN,
            "chain_hash": chain,
            "verdict": verdict,
            "summary": summary,
            "bus_pack": bus_pack,
        }
        _fsync_write(RUNTIME, json.dumps(runtime, ensure_ascii=False, indent=2) + "\n")
        _mirror(doc)
        _append_ledger({
            "ts": doc["ts"],
            "generation": _GEN,
            "chain_hash": chain,
            "verdict": verdict,
            "present": summary["present_count"],
            "plate_generation": plate_link.get("plate_generation"),
        })
        return doc
    finally:
        _meld_unlock(fd)


def sense_universal_slice(
    *,
    state_dir: Path | None = None,
    sense_doc: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Light combinatorics facet — Final_Eye · Ear · Mouth locked under Universal Protector."""
    state = state_dir or STATE
    sense = sense_doc if sense_doc is not None else read_panel()
    if not sense.get("schema"):
        sense = _load(state / "field-sense-package-panel.json", {})
    eye_ear = _load(state / "eye-ear-plate.json", {})
    universal = _load(state / "universal-protector-panel.json", {})
    bridge = _load(state / "field-plate-combinatorics-bridge.json", {})
    comb = _load(state / "g16-field-combinatorics-panel.json", {})
    ellie = _load(state / "field-ellie-fier-panel.json", {})
    iron = _load(state / "ironclad-immediate.json", {})
    obs = _load(state / "obs-threat-posterity-panel.json", {})
    members = sense.get("members") or {}
    counts = {
        "final_eye": 1 if (members.get("final_eye") or {}).get("present") else 0,
        "final_ear": 1 if (members.get("final_ear") or {}).get("present") else 0,
        "mouth_neural": 1 if (members.get("mouth_neural") or {}).get("present") else 0,
        "hostess7": 1 if (members.get("hostess7") or {}).get("present") else 0,
        "eye_ear_plate": 1 if eye_ear.get("ok") or eye_ear.get("plated") else 0,
        "universal_protector": 1 if universal.get("equipment_holds_gate") else 0,
        "combinatorics_bridge": 1 if bridge.get("combinatorics_ok") else 0,
        "ironclad_immediate": 1 if iron.get("plate_to_sense") or iron.get("goldmine") else 0,
        "obs_threat_posterity": 1 if obs.get("ok") else 0,
        "field_ellie_fier": 1 if ellie.get("ok") else 0,
    }
    lock_verify = comb.get("combinatorics_lock_verify") or bridge.get("combinatorics_lock_verify") or {}
    comb_lock_ok = bool(lock_verify.get("ok", True)) and not comb.get("rejected")
    eye_ok = bool((members.get("final_eye") or {}).get("present"))
    ear_ok = bool((members.get("final_ear") or {}).get("present"))
    eye_plate_ok = bool(eye_ear.get("ok") or eye_ear.get("plated"))
    mouth_ok = bool((members.get("mouth_neural") or {}).get("present")) or bool(eye_ear.get("mouth_ok"))
    universal_lock = (
        comb_lock_ok
        and bool(universal.get("equipment_holds_gate"))
        and bool(eye_ear.get("ok") or eye_ear.get("plated"))
        and str(sense.get("verdict") or "") in ("GREEN", "WATCH")
        and eye_ok
        and ear_ok
        and (eye_plate_ok or mouth_ok)
    )
    return {
        "schema": "field-sense-universal-slice/v1",
        "facet": "sense_universal",
        "updated": _now(),
        "counts": counts,
        "leaf_count": sum(counts.values()),
        "universal_lock": universal_lock,
        "combinatorics_lock_ok": comb_lock_ok,
        "sense_verdict": sense.get("verdict"),
        "eye_ear_verdict": eye_ear.get("verdict"),
        "eye_ear_chain": (eye_ear.get("chain_hash") or "")[:16],
        "sense_chain": (sense.get("chain_hash") or "")[:16],
        "combinatorics_chain": ((comb.get("combinatorics_lock") or {}).get("engine_sha256") or "")[:16],
        "ellie_verdict": (ellie.get("systemwide") or {}).get("verdict"),
        "ellie_score": (ellie.get("systemwide") or {}).get("score"),
        "ellie_threat_warn_level": ellie.get("threat_warn_level") or (ellie.get("security_authority") or {}).get("threat_warn_level"),
        "ellie_authority": ellie.get("security_authority") or _load(state / "field-ellie-security-authority.json", {}),
        "locked_members": [k for k, v in counts.items() if v],
        "condense_group": "universal_lock",
        "motto": "Final_Eye · Ear · Mouth — universal lock through plate meld and combinatorics condense.",
    }


def read_panel() -> dict[str, Any]:
    doc = _load(PANEL, {})
    if doc.get("schema"):
        return doc
    for path in (
        REDUNDANT / "field-sense-package-panel.json",
        REDUNDANT / "field-sense-package-panel.json.bak",
    ):
        if path.is_file():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
    return {}


def panel_json() -> dict[str, Any]:
    doc = read_panel()
    if doc.get("schema"):
        return doc
    return meld()


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("meld", "cycle", "build", "witness"):
        print(json.dumps(meld(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "manifest":
        meld()
        print(MANIFEST.read_text(encoding="utf-8"))
        return 0
    if cmd == "slice":
        print(json.dumps(sense_universal_slice(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: field-sense-package-meld.py [json|meld|manifest|witness|slice]"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())