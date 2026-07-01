#!/usr/bin/env pythong
"""KILROY Final Eye OCR brain — Grok vision slice for Field Brain corroboration."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
KILROY = Path(os.environ.get("KILROY_ROOT", str(INSTALL / "KILROY")))
HOSTESS7 = Path(os.environ.get("HOSTESS7_ROOT", str(INSTALL / "Hostess7")))
DOCTRINE = KILROY / "data" / "kilroy-final-eye-doctrine.json"
MARKER = STATE / "kilroy-final-eye-brain.json"
CORPUS = STATE / "kilroy-final-eye-corpus.json"


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


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def final_eye_root() -> Path:
    env = os.environ.get("FINAL_EYE_ROOT", "").strip()
    if env:
        p = Path(env)
        if p.is_dir():
            return p
    for candidate in (
        INSTALL / "Final_Eye",
        KILROY.parent / "Final_Eye",
        Path(__file__).resolve().parents[1] / "Final_Eye",
    ):
        if (candidate / "zocr_status.py").is_file():
            return candidate
    return INSTALL / "Final_Eye"


def _final_eye_env(root: Path) -> dict[str, str]:
    py_parts = [str(root)]
    gmf = root / "GrokMediaFormat"
    if gmf.is_dir():
        py_parts.append(str(gmf))
    py = os.pathsep.join(py_parts)
    if os.environ.get("PYTHONPATH"):
        py = py + os.pathsep + os.environ["PYTHONPATH"]
    return {
        **os.environ,
        "FINAL_EYE_ROOT": str(root),
        "NEXUS_INSTALL_ROOT": str(INSTALL),
        "KILROY_ROOT": str(KILROY),
        "HOSTESS7_ROOT": str(HOSTESS7),
        "PYTHONPATH": py,
        "ZOCR_RECORDING": "0",
        "FINAL_EYE_ASSIST": os.environ.get("FINAL_EYE_ASSIST", "1"),
    }


def _import_final_eye(root: Path) -> bool:
    env = _final_eye_env(root)
    for part in env.get("PYTHONPATH", "").split(os.pathsep):
        if part and part not in sys.path:
            sys.path.insert(0, part)
    return (root / "zocr_status.py").is_file()


def _tail_jsonl(path: Path, *, limit: int = 50) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    rows: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _summarize_capture(row: dict[str, Any]) -> dict[str, Any]:
    ocr = str(row.get("ocr") or "")
    preview = ocr[:240] + ("…" if len(ocr) > 240 else "")
    return {
        "ts": row.get("ts"),
        "label": row.get("label"),
        "ocr_len": row.get("ocr_len") or len(ocr),
        "ocr_preview": preview,
        "image": row.get("image"),
        "h7_file": row.get("h7_file") or row.get("ocr_file"),
        "format": row.get("format"),
    }


def ingest_corpus(*, session_limit: int = 120, manifest_limit: int = 40) -> dict[str, Any]:
    """Pull vision-session, manifest, and out/ into a Grok-readable OCR corpus."""
    root = final_eye_root()
    session_path = root / "data" / "vision-session.jsonl"
    manifest_path = root / "manifest.jsonl"
    out_dir = root / "out"

    session_rows = _tail_jsonl(session_path, limit=session_limit)
    manifest_rows = _tail_jsonl(manifest_path, limit=manifest_limit)

    ocr_bytes = 0
    capture_count = 0
    h7_count = 0
    for row in manifest_rows:
        ocr_bytes += int(row.get("ocr_len") or len(str(row.get("ocr") or "")))
        capture_count += 1
        if row.get("h7_file") or row.get("format"):
            h7_count += 1

    out_files: list[dict[str, Any]] = []
    if out_dir.is_dir():
        for p in sorted(out_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True)[:30]:
            if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".h7", ".txt"):
                out_files.append({
                    "name": p.name,
                    "bytes": p.stat().st_size,
                    "suffix": p.suffix,
                })

    recent_captures = [_summarize_capture(r) for r in manifest_rows[-12:]]
    recent_session = [
        {
            "ts": r.get("ts"),
            "action": r.get("action"),
            "ok": r.get("ok"),
            "ocr_len": r.get("ocr_len"),
            "label": r.get("label"),
        }
        for r in session_rows[-20:]
    ]

    doc = {
        "schema": "kilroy-final-eye-corpus/v1",
        "updated": _now(),
        "final_eye_root": str(root),
        "session_path": str(session_path),
        "manifest_path": str(manifest_path),
        "session_lines": len(session_rows),
        "manifest_captures": capture_count,
        "ocr_bytes_total": ocr_bytes,
        "h7_captures": h7_count,
        "out_artifacts": len(out_files),
        "recent_captures": recent_captures,
        "recent_session": recent_session,
        "out_sample": out_files[:15],
    }
    _save(CORPUS, doc)
    return doc


def _compact_live(live: dict[str, Any]) -> dict[str, Any]:
    """Trim live_status for brain/OCR context without dumping megabytes."""
    session = live.get("session") or {}
    zocr = live.get("zocr") or {}
    neural = live.get("neural") or {}
    pattern = live.get("pattern") or {}
    offense = live.get("offense") or {}
    eye = live.get("eye") or {}
    feb = live.get("final_eyeball") or {}
    caps = live.get("latest_captures") or []
    return {
        "ok": live.get("ok"),
        "product": live.get("product"),
        "version": live.get("version"),
        "schema": live.get("schema"),
        "ts": live.get("ts"),
        "uptime_sec": live.get("uptime_sec"),
        "recording": False,
        "live_feed_only": True,
        "session": {
            "captures": session.get("captures"),
            "frames": session.get("frames"),
            "ocr_bytes_total": session.get("ocr_bytes_total"),
            "errors": session.get("errors"),
        },
        "zocr": {
            "tesseract": zocr.get("tesseract"),
            "captures": zocr.get("captures"),
            "display": zocr.get("display"),
        },
        "neural": {
            "sealed": neural.get("sealed"),
            "assist": neural.get("assist"),
            "truth_percent": neural.get("truth_percent"),
        } if neural else {},
        "pattern": {
            "registry_entries": (pattern.get("registry") or {}).get("entries")
            if isinstance(pattern.get("registry"), dict) else pattern.get("entries"),
            "matches_recent": len(pattern.get("recent") or []) if isinstance(pattern.get("recent"), list) else 0,
        } if pattern else {},
        "offense": {
            "armed": offense.get("armed"),
            "mode": offense.get("mode"),
            "heaven_pass": offense.get("heaven_pass"),
        } if offense else {},
        "eye": {
            "mode": eye.get("mode"),
            "profile": eye.get("profile"),
            "heaven": eye.get("heaven"),
            "hell": eye.get("hell"),
        } if eye else {},
        "final_eyeball": {
            "armed": feb.get("armed"),
            "verdict": feb.get("verdict"),
        } if feb else {},
        "latest_captures": [_summarize_capture(c) for c in caps[-5:]],
        "latest_thumb": live.get("latest_thumb"),
    }


def live_slice(*, ingest: bool = True) -> dict[str, Any]:
    root = final_eye_root()
    if not _import_final_eye(root):
        return {"ok": False, "error": "final_eye_missing", "root": str(root)}
    try:
        from zocr_status import live_status

        live = live_status()
        live["recording"] = False
        live["live_feed_only"] = True
        compact = _compact_live(live)
        if ingest:
            compact["corpus"] = ingest_corpus()
        return compact
    except Exception as exc:
        return {"ok": False, "error": str(exc), "root": str(root)}


def ocr_brain_context(*, ingest: bool = True) -> dict[str, Any]:
    """Compact Grok OCR brain packet — vision telemetry + corpus + doctrine."""
    root = final_eye_root()
    doctrine = _load(DOCTRINE, {})
    hostess = _load(HOSTESS7 / "data/final-eye-12-doctrine.json", {})
    corpus = ingest_corpus() if ingest else (_load(CORPUS) or ingest_corpus())
    live = live_slice(ingest=False)

    texts: list[str] = []
    for cap in corpus.get("recent_captures") or []:
        prev = cap.get("ocr_preview") or ""
        if prev.strip():
            texts.append(prev.strip())

    return {
        "schema": "kilroy-grok-ocr-brain/v1",
        "updated": _now(),
        "owner": "grok",
        "role": "ocr_brain",
        "home": doctrine.get("home", "127.0.0.1"),
        "policy": doctrine.get("policy", "telemetry_only_no_recording"),
        "final_eye": {
            "root": str(root),
            "port": doctrine.get("port", 9479),
            "version": live.get("version"),
            "live": live,
        },
        "doctrine": {
            "kilroy": doctrine,
            "hostess7": hostess,
        },
        "corpus": {
            "manifest_captures": corpus.get("manifest_captures"),
            "ocr_bytes_total": corpus.get("ocr_bytes_total"),
            "h7_captures": corpus.get("h7_captures"),
            "session_lines": corpus.get("session_lines"),
            "recent_ocr_snippets": texts[:8],
            "recent_captures": corpus.get("recent_captures"),
        },
        "proc": "/proc/kilroy_field/eye",
        "bridge": str(Path(__file__).resolve()),
        "sync_cmd": "pythong lib/kilroy-final-eye-brain.py board",
    }


def build_board(*, write: bool = True, ingest: bool = True) -> dict[str, Any]:
    root = final_eye_root()
    live = live_slice(ingest=ingest)
    corpus = _load(CORPUS) if CORPUS.is_file() else ingest_corpus()
    doctrine = _load(DOCTRINE, {})
    doc = {
        "schema": "kilroy-final-eye-brain/v1",
        "updated": _now(),
        "owner": "grok_ocr_brain",
        "motto": doctrine.get(
            "motto",
            "Final Eye is Grok's OCR brain — live telemetry, silent capture on demand, corpus corroboration",
        ),
        "home": doctrine.get("home", "127.0.0.1"),
        "policy": doctrine.get("policy", "telemetry_only_no_recording"),
        "war_scope": doctrine.get("war_scope", "defensive_perimeter"),
        "final_eye_root": str(root),
        "port": doctrine.get("port", 9479),
        "live": live,
        "corpus": corpus,
        "proc": "/proc/kilroy_field/eye",
        "kilroy_root": str(KILROY),
        "install_root": str(INSTALL),
        "marker": str(MARKER),
        "corpus_path": str(CORPUS),
    }
    if write:
        _save(MARKER, doc)
    return doc


def look_once(*, prefer: str = "auto", timeout: int = 90) -> dict[str, Any]:
    """On-demand silent look — does not start recording stream."""
    root = final_eye_root()
    watch = root / "zocr_watch.py"
    if not watch.is_file():
        return {"ok": False, "error": "zocr_watch_missing", "root": str(root)}
    proc = subprocess.run(
        [sys.executable, str(watch), "look", f"--prefer={prefer}"],
        capture_output=True,
        text=True,
        timeout=timeout,
        env=_final_eye_env(root),
        cwd=str(root),
    )
    try:
        doc = json.loads(proc.stdout)
    except json.JSONDecodeError:
        doc = {"ok": False, "tail": (proc.stdout or "")[-1500:]}
    doc["returncode"] = proc.returncode
    if doc.get("ok"):
        ingest_corpus()
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "board", "status"):
        print(json.dumps(build_board(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "live":
        print(json.dumps(live_slice(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "ingest":
        print(json.dumps(ingest_corpus(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("corpus", "data"):
        doc = _load(CORPUS)
        if not doc:
            doc = ingest_corpus()
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 0
    if cmd in ("ocr-brain", "ocr_brain", "context"):
        print(json.dumps(ocr_brain_context(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "look":
        prefer = sys.argv[2] if len(sys.argv) > 2 else "auto"
        print(json.dumps(look_once(prefer=prefer), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "error": "usage: kilroy-final-eye-brain.py [json|live|ingest|corpus|ocr-brain|look [prefer]]",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())