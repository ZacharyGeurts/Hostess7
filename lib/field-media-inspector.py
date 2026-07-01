#!/usr/bin/env pythong
"""Field Media Inspector — provenance, OCR, neural generation tags, Ironclad content threat."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import re
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))
DOCTRINE = INSTALL / "data" / "field-media-inspector-doctrine.json"
CODEC_DOCTRINE = INSTALL / "data" / "field-media-codec-doctrine.json"
CACHE = STATE / "field-media-inspect-cache.json"


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


def _doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {})


def _read_head(path: Path, limit: int = 65536) -> bytes:
    try:
        with path.open("rb") as fh:
            return fh.read(limit)
    except OSError:
        return b""


def _ascii_haystack(blob: bytes) -> str:
    try:
        return blob.decode("utf-8", errors="ignore").lower()
    except Exception:
        return ""


def _provenance_from_text(text: str, name: str = "") -> tuple[str, float, list[str]]:
    doctrine = _doctrine()
    hay = f"{text} {name}".lower()
    best_id = "unknown"
    best_score = 0.0
    hits: list[str] = []
    for row in doctrine.get("generation_sources") or []:
        sid = str(row.get("id") or "")
        if sid == "unknown":
            continue
        for marker in row.get("markers") or []:
            m = str(marker).lower()
            if m and m in hay:
                score = min(1.0, 0.55 + len(m) * 0.04)
                hits.append(m)
                if score > best_score:
                    best_score = score
                    best_id = sid
    if best_score < 0.4 and any(k in hay for k in ("canon", "nikon", "iphone", "exif")):
        return "camera", 0.5, hits
    return best_id, round(best_score, 3), sorted(set(hits))


def _neural_generated_score(text: str, *, kind: str) -> dict[str, Any]:
    doctrine = _doctrine()
    cfg = doctrine.get("neural_generated") or {}
    threshold = float(cfg.get("confidence_threshold") or 0.55)
    score = 0.0
    signals: list[str] = []
    hay = text.lower()
    for pat in cfg.get("trained_patterns") or []:
        rx = str(pat.get("regex") or "")
        if not rx:
            continue
        try:
            if re.search(rx, hay, re.IGNORECASE):
                w = float(pat.get("weight") or 0.5)
                score = max(score, w)
                signals.append(str(pat.get("id") or rx[:24]))
        except re.error:
            continue
    if kind == "image":
        if "parameters" in hay and "sampler" in hay:
            score = max(score, 0.82)
            signals.append("sd_parameters_chunk")
        if "c2pa" in hay or "claim_generator" in hay:
            score = max(score, 0.78)
            signals.append("c2pa_manifest")
        if re.search(r"\b(1024|2048|512)\s*[x×]\s*(1024|2048|512)\b", hay):
            score = max(score, 0.35)
            signals.append("square_resolution_ai")
    return {
        "ai_generated": score >= threshold,
        "generation_confidence": round(score, 3),
        "neural_signals": signals,
        "threshold": threshold,
    }


def _parse_wav(head: bytes, size: int) -> dict[str, Any]:
    issues: list[str] = []
    props: dict[str, Any] = {"format": "wav", "container": "wav"}
    if len(head) < 12 or head[:4] != b"RIFF" or head[8:12] != b"WAVE":
        issues.append("invalid_riff_header")
        return {**props, "encoding_issues": issues, "valid": False}
    pos = 12
    fmt: dict[str, Any] = {}
    chunks: list[str] = []
    data_size = 0
    while pos + 8 <= len(head):
        cid = head[pos : pos + 4].decode("latin-1", errors="replace")
        clen = struct.unpack_from("<I", head, pos + 4)[0]
        chunks.append(cid)
        body = head[pos + 8 : pos + 8 + min(clen, len(head) - pos - 8)]
        if cid == "fmt " and len(body) >= 16:
            (
                audio_format,
                channels,
                sample_rate,
                byte_rate,
                block_align,
                bits_per_sample,
            ) = struct.unpack_from("<HHIIHH", body, 0)
            fmt = {
                "audio_format": audio_format,
                "channels": channels,
                "sample_rate": sample_rate,
                "byte_rate": byte_rate,
                "block_align": block_align,
                "bit_depth": bits_per_sample,
                "codec": "pcm" if audio_format == 1 else f"format_{audio_format}",
            }
            doctrine = _doctrine().get("audio_threat") or {}
            if sample_rate > int(doctrine.get("max_sample_rate_hz") or 192000):
                issues.append("sample_rate_excessive")
            if sample_rate < int(doctrine.get("min_sample_rate_hz") or 8000):
                issues.append("sample_rate_too_low")
            if channels > int(doctrine.get("max_channels") or 32):
                issues.append("channel_count_suspicious")
            if audio_format != 1:
                issues.append("non_pcm_wav")
        elif cid == "data":
            data_size = clen
        pos += 8 + clen + (clen % 2)
    props.update(fmt)
    props["chunks"] = chunks
    props["data_bytes"] = data_size
    suspicious = set(_doctrine().get("audio_threat", {}).get("suspicious_chunk_ids") or [])
    for c in chunks:
        if c.strip() in suspicious and c != "LIST":
            issues.append(f"suspicious_chunk:{c}")
    if data_size and size and data_size > size:
        issues.append("data_chunk_larger_than_file")
    if fmt.get("sample_rate") and fmt.get("bit_depth") and fmt.get("channels"):
        props["bitrate_est"] = int(fmt["sample_rate"]) * int(fmt["bit_depth"]) * int(fmt["channels"])
    return {**props, "encoding_issues": issues, "valid": "invalid_riff_header" not in issues}


def _wav_amplitude_threat(path: Path, fmt: dict[str, Any]) -> dict[str, Any]:
    threats: list[str] = []
    score = 0.0
    try:
        sample_rate = int(fmt.get("sample_rate") or 0)
        channels = int(fmt.get("channels") or 1)
        bit_depth = int(fmt.get("bit_depth") or 16)
        if sample_rate <= 0 or bit_depth not in (8, 16, 24, 32):
            return {"audio_content_score": 0.0, "audio_content_threats": ["unreadable_pcm"]}
        max_samples = min(48000 * channels, 200000)
        with path.open("rb") as fh:
            fh.seek(44)
            raw = fh.read(max_samples * (bit_depth // 8))
        if not raw:
            return {"audio_content_score": 0.0, "audio_content_threats": ["empty_pcm"]}
        if bit_depth == 16:
            count = len(raw) // 2
            samples = struct.unpack(f"<{count}h", raw[: count * 2])
        elif bit_depth == 8:
            samples = [b - 128 for b in raw[: max_samples]]
        else:
            return {"audio_content_score": 0.05, "audio_content_threats": []}
        if not samples:
            return {"audio_content_score": 0.0, "audio_content_threats": ["no_samples"]}
        peak = max(abs(s) for s in samples)
        rms = math.sqrt(sum(s * s for s in samples) / len(samples))
        if peak >= (32767 if bit_depth == 16 else 127):
            threats.append("clipping_detected")
            score += 0.15
        if rms < 1.0 and peak > 1000:
            threats.append("sparse_high_peaks")
            score += 0.25
        doctrine = _doctrine().get("audio_threat") or {}
        ultrasonic = int(doctrine.get("ultrasonic_carrier_hz") or 18000)
        if sample_rate > ultrasonic * 1.2:
            threats.append("ultrasonic_sample_rate")
            score += 0.2
    except (OSError, struct.error, ValueError):
        threats.append("pcm_probe_failed")
        score += 0.1
    return {
        "audio_content_score": round(min(1.0, score), 3),
        "audio_content_threats": threats,
    }


def _image_dimensions(head: bytes) -> dict[str, Any]:
    if head[:8] == b"\x89PNG\r\n\x1a\n" and len(head) >= 24:
        w, h = struct.unpack(">II", head[16:24])
        return {"width": w, "height": h, "color_space": "rgba" if head[25:26] == b"\x06" else "rgb"}
    if head[:2] == b"\xff\xd8":
        i = 2
        while i + 9 < len(head):
            if head[i] != 0xFF:
                break
            marker = head[i + 1]
            if marker in (0xC0, 0xC1, 0xC2):
                h, w = struct.unpack(">HH", head[i + 5 : i + 9])
                return {"width": w, "height": h, "color_space": "jpeg"}
            seg_len = struct.unpack(">H", head[i + 2 : i + 4])[0]
            i += 2 + seg_len
    if head[:6] in (b"GIF87a", b"GIF89a"):
        w, h = struct.unpack("<HH", head[6:10])
        return {"width": w, "height": h, "color_space": "indexed"}
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return {"color_space": "webp"}
    return {}


def _ocr_image(path: Path) -> dict[str, Any]:
    doctrine = _doctrine().get("ocr") or {}
    max_bytes = int((_doctrine().get("policy") or {}).get("max_ocr_bytes") or 8_388_608)
    try:
        if path.stat().st_size > max_bytes:
            return {"ocr_text": "", "ocr_confidence": 0.0, "ocr_engine": "skipped_size"}
    except OSError:
        return {"ocr_text": "", "ocr_confidence": 0.0, "ocr_engine": "unreadable"}
    eye_root = Path(os.environ.get(str(doctrine.get("bridge") or "FINAL_EYE_ROOT"), SG / "NewLatest" / "Final_Eye"))
    assist = eye_root / "zocr_product.py"
    if assist.is_file():
        try:
            spec = importlib.util.spec_from_file_location("zocr_product", assist)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                if str(eye_root) not in sys.path:
                    sys.path.insert(0, str(eye_root))
                spec.loader.exec_module(mod)
                if hasattr(mod, "ocr_file"):
                    out = mod.ocr_file(str(path))
                    if isinstance(out, dict):
                        return {
                            "ocr_text": (out.get("text") or "")[:2000],
                            "ocr_confidence": float(out.get("confidence") or 0.0),
                            "ocr_engine": "zocr",
                        }
        except Exception:
            pass
    head = _read_head(path, 131072)
    text = _ascii_haystack(head)
    printable = re.findall(r"[ -~]{8,}", text)
    snippet = " ".join(printable[:12])[:500]
    conf = 0.25 if snippet else 0.0
    return {"ocr_text": snippet, "ocr_confidence": conf, "ocr_engine": "heuristic_ascii"}


def _ironclad_slice() -> dict[str, Any]:
    py = INSTALL / "lib" / "ironclad-immediate.py"
    if not py.is_file():
        return {}
    try:
        spec = importlib.util.spec_from_file_location("ironclad_immediate", py)
        if not spec or not spec.loader:
            return {}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "read_immediate"):
            return mod.read_immediate()
        if hasattr(mod, "build_immediate"):
            return mod.build_immediate()
    except Exception:
        pass
    return _load(STATE / "ironclad-immediate.json", {})


def _ironclad_content_threat(
    path: Path,
    kind: str,
    *,
    encoding_issues: list[str],
    audio_extra: dict[str, Any] | None = None,
    generation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    iron = _ironclad_slice()
    sealed = bool(iron.get("ironclad_sealed") or (iron.get("plate") or {}).get("realized"))
    doctrine = _doctrine().get("ironclad") or {}
    score = 0.0
    threats: list[str] = []
    verdict = "clear"

    if encoding_issues:
        score += min(0.5, 0.08 * len(encoding_issues))
        threats.extend(encoding_issues[:6])

    if kind == "audio" and path.suffix.lower() == ".wav":
        audio_extra = audio_extra or {}
        act = audio_extra.get("audio_content_threats") or []
        threats.extend(act)
        score += float(audio_extra.get("audio_content_score") or 0.0)
        if doctrine.get("wav_content_gate") and not sealed:
            threats.append("ironclad_gate_pending")
            score = max(score, 0.12)
        elif act:
            verdict = "review"

    gen = generation or {}
    if gen.get("ai_generated") and gen.get("generation_source") == "unknown":
        threats.append("unattributed_ai_media")
        score = max(score, 0.2)

    if score >= 0.65:
        verdict = "threat"
    elif score >= 0.3:
        verdict = "review"
    elif threats:
        verdict = "watch"

    return {
        "content_threat": {
            "score": round(min(1.0, score), 3),
            "verdict": verdict,
            "threats": sorted(set(threats)),
            "ironclad_sealed": sealed,
            "ironclad_verdict": "pass" if verdict == "clear" and sealed else verdict,
            "citation": doctrine.get("citation") or "ironclad:media-threat:1",
        }
    }


def _container_for_ext(ext: str) -> str | None:
    e = ext.lower().lstrip(".")
    doc = _load(CODEC_DOCTRINE, {})
    for row in doc.get("containers") or []:
        if e in (row.get("extensions") or []):
            return str(row.get("id") or e)
    mime_map = doc.get("mime_by_extension") or {}
    return e if e in mime_map else None


def inspect_path(path: Path, kind: str, *, deep: bool = False, media_id: str | None = None) -> dict[str, Any]:
    path = path.resolve()
    try:
        st = path.stat()
    except OSError:
        return {"ok": False, "error": "unreadable"}

    head = _read_head(path)
    text = _ascii_haystack(head)
    ext = path.suffix.lower().lstrip(".")
    container = _container_for_ext(ext)
    mime_map = (_load(CODEC_DOCTRINE, {}).get("mime_by_extension") or {})
    mime = mime_map.get(ext)

    gen_id, gen_conf, gen_hits = _provenance_from_text(text, path.name)
    neural = _neural_generated_score(text, kind=kind)
    if neural.get("ai_generated") and gen_id == "unknown":
        gen_conf = max(gen_conf, float(neural.get("generation_confidence") or 0))

    details: dict[str, Any] = {
        "path": str(path),
        "kind": kind,
        "ext": ext,
        "size": st.st_size,
        "container": container,
        "mime": mime,
        "metadata_keys": [],
        "encoding_issues": [],
    }

    if kind == "image":
        details.update(_image_dimensions(head))
        if deep:
            ocr = _ocr_image(path)
            details.update(ocr)
        else:
            details["ocr_text"] = ""
            details["ocr_confidence"] = 0.0

    audio_extra: dict[str, Any] = {}
    if kind == "audio" and ext == "wav":
        wav = _parse_wav(head, st.st_size)
        details.update({k: v for k, v in wav.items() if k != "encoding_issues"})
        details["encoding_issues"] = list(wav.get("encoding_issues") or [])
        if deep:
            audio_extra = _wav_amplitude_threat(path, wav)
            details.update(audio_extra)

    if kind == "video":
        if head[4:8] == b"ftyp":
            details["container"] = details.get("container") or "mp4"
        elif head[:4] == b"\x1aE\xdf\xa3":
            details["container"] = details.get("container") or "mkv"

    generation = {
        "generation_source": gen_id,
        "generation_confidence": gen_conf,
        "generation_hits": gen_hits,
        "ai_generated": bool(neural.get("ai_generated")),
        "neural_signals": neural.get("neural_signals") or [],
    }

    threat = _ironclad_content_threat(
        path,
        kind,
        encoding_issues=details.get("encoding_issues") or [],
        audio_extra=audio_extra if kind == "audio" else None,
        generation=generation,
    )

    mid = media_id or hashlib.sha256(str(path).encode()).hexdigest()[:20]
    out = {
        "ok": True,
        "schema": "field-media-inspect/v1",
        "media_id": mid,
        "inspected": _now(),
        "deep": deep,
        "file_details": details,
        "generation": generation,
        **threat,
        "provenance_chain": [
            {"layer": "metadata", "source": gen_id, "confidence": gen_conf},
            {"layer": "neural", "ai_generated": generation["ai_generated"]},
            {"layer": "ironclad", "verdict": threat["content_threat"]["ironclad_verdict"]},
        ],
    }
    _cache_put(mid, out)
    return out


def _cache_doc() -> dict[str, Any]:
    return _load(CACHE, {"items": {}})


def _cache_put(media_id: str, row: dict[str, Any]) -> None:
    doc = _cache_doc()
    items = doc.get("items") if isinstance(doc.get("items"), dict) else {}
    items[media_id] = row
    doc["updated"] = _now()
    doc["items"] = items
    _save_atomic(CACHE, doc)


def inspect_cached(media_id: str) -> dict[str, Any] | None:
    items = (_cache_doc().get("items") or {})
    row = items.get(media_id)
    return row if isinstance(row, dict) else None


def inspect_light(path: Path, kind: str, *, media_id: str | None = None) -> dict[str, Any]:
    return inspect_path(path, kind, deep=False, media_id=media_id)


def inspect_deep(path: Path, kind: str, *, media_id: str | None = None) -> dict[str, Any]:
    return inspect_path(path, kind, deep=True, media_id=media_id)


def cache_summary() -> dict[str, Any]:
    items = (_cache_doc().get("items") or {})
    threats = {"clear": 0, "watch": 0, "review": 0, "threat": 0}
    sources: dict[str, int] = {}
    ai_count = 0
    for row in items.values():
        if not isinstance(row, dict):
            continue
        ct = row.get("content_threat") or {}
        v = str(ct.get("verdict") or "clear")
        threats[v] = threats.get(v, 0) + 1
        gen = row.get("generation") or {}
        sid = str(gen.get("generation_source") or "unknown")
        sources[sid] = sources.get(sid, 0) + 1
        if gen.get("ai_generated"):
            ai_count += 1
    return {
        "cached": len(items),
        "threats": threats,
        "generation_sources": sources,
        "ai_generated_count": ai_count,
    }


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "summary").strip().lower()
    if cmd == "summary":
        print(json.dumps({"ok": True, "summary": cache_summary()}, ensure_ascii=False, indent=2))
        return 0
    if cmd == "inspect" and len(sys.argv) > 2:
        try:
            payload = json.loads(sys.argv[2])
        except json.JSONDecodeError:
            payload = {"path": sys.argv[2]}
        p = Path(str(payload.get("path") or ""))
        kind = str(payload.get("kind") or "image")
        deep = bool(payload.get("deep", True))
        print(json.dumps(inspect_path(p, kind, deep=deep, media_id=payload.get("media_id")), ensure_ascii=False, indent=2))
        return 0
    if cmd == "cached" and len(sys.argv) > 2:
        row = inspect_cached(sys.argv[2])
        print(json.dumps({"ok": bool(row), "inspect": row}, ensure_ascii=False, indent=2))
        return 0
    print("usage: field-media-inspector.py [summary|inspect JSON|cached ID]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())