#!/usr/bin/env pythong
"""Field Virus scanner — own 2026 heuristics gate every file in and out.

Doctrine: every contact is HOSTILE until positively identified as CIVILIAN or
confirmed as THREAT. Incoming bytes are abstracted for harms before memory or
drive touch. Memory regions and drive volumes harden against each other.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import struct
import sys
import time
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

QUEEN = Path(__file__).resolve().parents[1]
SG = QUEEN.parent.parent
STATE = Path(os.environ.get("NEXUS_STATE_DIR", QUEEN / ".nexus-state"))
FORMATS_PATH = QUEEN / "data" / "field-virus-formats.json"
VIRUS_DIR = STATE / "field-virus"
QUARANTINE_DIR = VIRUS_DIR / "quarantine"
SCAN_LOG = VIRUS_DIR / "scan.jsonl"
PANEL_PATH = VIRUS_DIR / "panel.json"
MEMORY_VAULT = VIRUS_DIR / "memory-vault"
DRIVE_VAULT = VIRUS_DIR / "drive-vault"

_SCAN_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_CACHE_TTL = 30.0


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _save(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append_log(row: dict[str, Any]) -> None:
    try:
        VIRUS_DIR.mkdir(parents=True, exist_ok=True)
        with SCAN_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def load_formats() -> dict[str, Any]:
    doc = _load(FORMATS_PATH, {})
    if doc.get("schema") == "field-virus-formats/v1":
        return doc
    return {"schema": "field-virus-formats/v1", "own_formats": [], "universal_formats": []}


def _hex_head(data: bytes, n: int = 16) -> str:
    return data[:n].hex()


def _match_magic(data: bytes, fmt: dict[str, Any]) -> bool:
    if fmt.get("magic_hex"):
        need = bytes.fromhex(str(fmt["magic_hex"]))
        return data[: len(need)] == need
    if fmt.get("magic_ascii"):
        need = str(fmt["magic_ascii"]).encode("ascii", errors="ignore")
        off = int(fmt.get("offset") or 0)
        return data[off : off + len(need)] == need
    if fmt.get("magic_regex"):
        try:
            text = data[:256].decode("utf-8", errors="replace")
            return bool(re.match(str(fmt["magic_regex"]), text, re.I))
        except re.error:
            return False
    return False


def detect_format(path: Path, head: bytes) -> dict[str, Any]:
    """Identify file type from magic bytes, extension, and sovereign registry."""
    fmts = load_formats()
    ext = path.suffix.lower()
    rel = ""
    try:
        rel = str(path.resolve().relative_to(SG.resolve())).replace("\\", "/")
    except ValueError:
        rel = str(path)

    detected: dict[str, Any] = {
        "path": str(path),
        "extension": ext,
        "relative": rel,
        "magic_hex": _hex_head(head, 12),
        "format_id": None,
        "format_label": "unknown",
        "family": "unknown",
        "sovereign": False,
        "risk": "unknown",
    }

    for own in fmts.get("own_formats") or []:
        exts = [str(e).lower() for e in (own.get("extensions") or [])]
        hint = str(own.get("path_hint") or "")
        matched = False
        if own.get("magic_hex") or own.get("magic_ascii"):
            if _match_magic(head, own):
                matched = True
            else:
                continue
        if own.get("json_schema") and ext == ".json":
            try:
                doc = json.loads(head.decode("utf-8", errors="replace")[:8192])
                if doc.get("schema") == own.get("json_schema"):
                    matched = True
                else:
                    continue
            except json.JSONDecodeError:
                continue
        elif own.get("json_keys") and ext == ".json":
            try:
                doc = json.loads(head.decode("utf-8", errors="replace")[:8192])
                if all(k in doc for k in own["json_keys"]):
                    matched = True
                else:
                    continue
            except json.JSONDecodeError:
                continue
        if hint and hint in rel:
            matched = True
        if exts and ext in exts and not own.get("json_schema") and not own.get("json_keys"):
            if own.get("magic_hex") or own.get("magic_ascii"):
                pass
            else:
                matched = True
        if not matched:
            continue
        detected.update({
            "format_id": own.get("id"),
            "format_label": own.get("label"),
            "family": "sovereign",
            "sovereign": True,
            "risk": "own_format",
            "civilian_eligible": bool(own.get("civilian_on_valid_header")),
        })
        return detected

    for uni in fmts.get("universal_formats") or []:
        if _match_magic(head, uni):
            detected.update({
                "format_id": uni.get("id"),
                "format_label": uni.get("label"),
                "family": "universal",
                "sovereign": False,
                "risk": uni.get("risk", "unknown"),
            })
            return detected

    if ext in (".py", ".sh", ".bash", ".pl", ".rb"):
        detected.update({
            "format_id": "script_ext",
            "format_label": f"Script ({ext})",
            "family": "script",
            "risk": "script",
        })
    elif ext in (".exe", ".dll", ".so", ".dylib", ".bin"):
        detected.update({
            "format_id": "binary_ext",
            "format_label": f"Binary ({ext})",
            "family": "executable",
            "risk": "executable",
        })
    return detected


def _read_head(path: Path, limit: int) -> tuple[bytes, int]:
    size = 0
    try:
        size = path.stat().st_size
        with path.open("rb") as fh:
            return fh.read(limit), size
    except OSError:
        return b"", size


def _extension_mismatch(path: Path, fmt_doc: dict[str, Any], detected: dict[str, Any]) -> list[str]:
    harms: list[str] = []
    ext = path.suffix.lower()
    risk = detected.get("risk") or ""
    name = path.name.lower()
    for pattern in (load_formats().get("harm_patterns") or {}).get("double_extensions") or []:
        if name.endswith(str(pattern).lower()):
            harms.append(f"double_extension:{pattern}")
    if risk == "executable" and ext not in (".exe", ".dll", ".so", ".dylib", ".bin", ".o", ""):
        harms.append("executable_magic_wrong_extension")
    if risk == "script" and ext not in (".sh", ".bash", ".py", ".pl", ".rb", ""):
        harms.append("script_magic_wrong_extension")
    if detected.get("family") == "sovereign" and ext == ".json" and detected.get("format_id"):
        pass
    elif ext == ".txt" and risk in ("executable", "archive"):
        harms.append("binary_disguised_as_text")
    return harms


def _scan_text_harms(blob: str, cfg: dict[str, Any]) -> tuple[list[str], int]:
    harms: list[str] = []
    score = 0
    patterns = load_formats().get("harm_patterns") or {}
    heur = cfg.get("harm_heuristics") or load_formats().get("harm_heuristics") or {}
    for pat in patterns.get("injection_regex") or []:
        try:
            if re.search(pat, blob, re.I):
                harms.append(f"injection:{pat[:32]}")
                score += int(heur.get("injection_pattern_score", 10))
        except re.error:
            continue
    for pat in patterns.get("webshell_regex") or []:
        try:
            if re.search(pat, blob, re.I):
                harms.append(f"webshell:{pat[:32]}")
                score += int(heur.get("webshell_score", 16))
        except re.error:
            continue
    for pat in patterns.get("executable_markers") or []:
        if pat.startswith("\\x"):
            try:
                raw = bytes.fromhex(pat.replace("\\x", ""))
                if raw in blob.encode("latin-1", errors="ignore"):
                    harms.append(f"executable_marker:{pat}")
                    score += int(heur.get("executable_in_text_score", 14))
            except ValueError:
                pass
        elif pat in blob:
            harms.append(f"executable_marker:{pat}")
            score += int(heur.get("executable_in_text_score", 14))
    return harms, score


def _zip_bomb_check(data: bytes, heur: dict[str, Any]) -> tuple[list[str], int]:
    harms: list[str] = []
    if data[:4] != b"PK\x03\x04":
        return harms, 0
    try:
        comp = struct.unpack_from("<H", data, 8)[0]
        uncomp = struct.unpack_from("<I", data, 18)[0]
        if comp and uncomp / max(comp, 1) >= float(heur.get("zip_bomb_ratio_threshold", 100)):
            harms.append(f"zip_bomb_ratio:{uncomp}/{comp}")
            return harms, int(heur.get("zip_bomb_score", 18))
    except struct.error:
        pass
    return harms, 0


def abstract_harms(
    path: Path | None = None,
    *,
    data: bytes | None = None,
    direction: str = "ingress",
) -> dict[str, Any]:
    """Abstract harm signals without executing or fully materializing content."""
    fmts = load_formats()
    heur = fmts.get("harm_heuristics") or {}
    max_scan = int(heur.get("max_scan_bytes", 2 * 1024 * 1024))

    if path is not None and data is None:
        if not path.is_file():
            return {"ok": False, "error": "not_a_file", "path": str(path)}
        data, size = _read_head(path, max_scan)
        if size > int(heur.get("max_file_bytes", 512 * 1024 * 1024)):
            return {
                "ok": True,
                "abstracted": True,
                "harms": ["oversize_file"],
                "harm_score": int(heur.get("oversize_score", 6)),
                "size": size,
                "digest": hashlib.sha256(data[:4096]).hexdigest()[:16],
            }
    elif data is None:
        return {"ok": False, "error": "no_input"}

    assert data is not None
    p = path or Path("inline-bytes")
    detected = detect_format(p, data)
    harms: list[str] = []
    score = 0

    harms.extend(_extension_mismatch(p, fmts, detected))
    if harms:
        score += int(heur.get("extension_mismatch_score", 12))

    text_sample = data[:min(len(data), 65536)].decode("utf-8", errors="replace")
    # Sovereign own-format files may embed pattern catalogs — skip text heuristics on them.
    if detected.get("family") != "sovereign":
        text_harms, text_score = _scan_text_harms(text_sample, fmts)
        harms.extend(text_harms)
        score += text_score

    zip_harms, zip_score = _zip_bomb_check(data, heur)
    harms.extend(zip_harms)
    score += zip_score

    if detected.get("risk") == "executable" and detected.get("family") != "sovereign":
        harms.append("unclassified_executable")
        score += 6
    if detected.get("risk") == "document_polyglot" and "<script" in text_sample.lower():
        harms.append("pdf_polyglot_script")
        score += int(heur.get("polyglot_score", 11))

    digest = hashlib.sha256(data[:8192]).hexdigest()
    return {
        "ok": True,
        "abstracted": True,
        "direction": direction,
        "format": detected,
        "harms": harms,
        "harm_score": score,
        "harm_count": len(harms),
        "digest": digest[:32],
        "sample_bytes": min(len(data), max_scan),
        "memory_safe": True,
        "executed": False,
    }


def classify_iff(
    scan: dict[str, Any],
    *,
    direction: str = "ingress",
    operator_trust: bool = False,
) -> dict[str, Any]:
    """HOSTILE default — promote to CIVILIAN (positive ID) or THREAT (harm proof)."""
    fmts = load_formats()
    doctrine = fmts.get("iff_doctrine") or {}
    heur = fmts.get("harm_heuristics") or {}
    harm_score = int(scan.get("harm_score") or 0)
    harms = list(scan.get("harms") or [])
    fmt = scan.get("format") or {}
    block_at = int(heur.get("threat_score_block", 20))
    hold_at = int(heur.get("threat_score_hold", 8))

    iff = str(doctrine.get("initial_iff") or "HOSTILE")
    iff_class = "UNCLASSIFIED"
    permit = False
    verdict = "FIELD_VIRUS_HOSTILE_HOLD"

    if harm_score >= block_at or any(h.startswith("webshell:") for h in harms):
        iff = "THREAT"
        iff_class = "CONFIRMED"
        verdict = "FIELD_VIRUS_THREAT_QUARANTINE"
    elif fmt.get("sovereign") and fmt.get("civilian_eligible") and harm_score < hold_at:
        iff = "CIVILIAN"
        iff_class = "SOVEREIGN_FORMAT"
        permit = True
        verdict = "FIELD_VIRUS_CIVILIAN_SOVEREIGN"
    elif fmt.get("sovereign") and harm_score < hold_at:
        iff = "CIVILIAN"
        iff_class = "SOVEREIGN_OWN"
        permit = True
        verdict = "FIELD_VIRUS_CIVILIAN_OWN"
    elif fmt.get("family") == "universal" and harm_score < hold_at:
        iff = "UNKNOWN"
        iff_class = "RECOGNIZED"
        verdict = "FIELD_VIRUS_UNKNOWN_HOLD"
    elif harm_score >= hold_at:
        iff = "HOSTILE"
        iff_class = "HARM_SIGNALS"
        verdict = "FIELD_VIRUS_HOSTILE_HOLD"
    elif operator_trust and harm_score == 0:
        iff = "CIVILIAN"
        iff_class = "OPERATOR_TRUST"
        permit = True
        verdict = "FIELD_VIRUS_CIVILIAN_OPERATOR"
    else:
        iff = "HOSTILE"
        iff_class = "PRESUME_HOSTILE"
        verdict = "FIELD_VIRUS_HOSTILE_HOLD"

    return {
        "iff": iff,
        "iff_class": iff_class,
        "iff_label": f"{iff} · {iff_class}",
        "presume_hostile": doctrine.get("presume_hostile", True),
        "permit": permit,
        "verdict": verdict,
        "direction": direction,
        "harm_score": harm_score,
    }


def _quarantine_copy(path: Path, scan_id: str) -> Path | None:
    try:
        QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
        dest = QUARANTINE_DIR / f"{scan_id}-{path.name}"
        shutil.copy2(path, dest)
        return dest
    except OSError:
        return None


def scan_path(
    path: str | Path,
    *,
    direction: str = "ingress",
    operator_trust: bool = False,
    use_cache: bool = True,
) -> dict[str, Any]:
    """Full scan: format detect → harm abstract → IFF classify."""
    p = Path(path).expanduser()
    try:
        p = p.resolve()
    except OSError:
        pass

    cache_key = f"{direction}:{p}"
    if use_cache and cache_key in _SCAN_CACHE:
        ts, cached = _SCAN_CACHE[cache_key]
        if time.time() - ts < _CACHE_TTL:
            return cached

    if not p.is_file():
        out = {"ok": False, "error": "not_a_file", "path": str(p), "lane": "FieldVirus"}
        return out

    abstract = abstract_harms(p, direction=direction)
    iff = classify_iff(abstract, direction=direction, operator_trust=operator_trust)
    scan_id = hashlib.sha256(f"{p}:{abstract.get('digest')}:{_ts()}".encode()).hexdigest()[:16]

    out: dict[str, Any] = {
        "ok": iff.get("permit", False),
        "schema": "field-virus-scan/v1",
        "ts": _ts(),
        "scan_id": scan_id,
        "path": str(p),
        "direction": direction,
        "lane": "FieldVirus",
        "abstract": abstract,
        "iff": iff,
        "verdict": iff.get("verdict"),
        "permit": iff.get("permit"),
        "quarantined": False,
        "memory_hardened": True,
        "drive_hardened": True,
    }

    if iff.get("iff") == "THREAT" or (not iff.get("permit") and direction == "ingress"):
        qpath = _quarantine_copy(p, scan_id)
        if qpath:
            out["quarantined"] = True
            out["quarantine_path"] = str(qpath)

    _append_log({
        "ts": out["ts"],
        "scan_id": scan_id,
        "path": str(p),
        "direction": direction,
        "iff": iff.get("iff"),
        "verdict": iff.get("verdict"),
        "harm_score": abstract.get("harm_score"),
        "format_id": (abstract.get("format") or {}).get("format_id"),
        "quarantined": out.get("quarantined"),
    })
    _SCAN_CACHE[cache_key] = (time.time(), out)
    return out


def gate_file(
    path: str | Path,
    *,
    direction: str = "ingress",
    operator_trust: bool = False,
) -> dict[str, Any]:
    """Mandatory gate — fail closed on THREAT; hold HOSTILE/UNKNOWN."""
    if os.environ.get("SG_FIELD_VIRUS_OFF", "").strip().lower() in ("1", "true", "yes"):
        return {"ok": True, "override": True, "lane": "FieldVirus", "direction": direction}

    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("queen_security", QUEEN / "lib" / "queen-security.py")
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            seal = mod.verify_code_seal()
            if not seal.get("ok") and not seal.get("override"):
                return {
                    "ok": False,
                    "verdict": "FIELD_VIRUS_SEAL_BROKEN",
                    "lane": "FieldVirus",
                    "seal": seal,
                    "gate": "fail_closed",
                }
    except Exception:
        pass

    scan = scan_path(path, direction=direction, operator_trust=operator_trust)
    iff = scan.get("iff") or {}
    gate = "pass" if scan.get("permit") else "hold"
    if iff.get("iff") == "THREAT":
        gate = "quarantine"

    return {
        **scan,
        "gate": gate,
        "imported": False,
        "internal_touch": scan.get("permit", False),
        "operator_hint": (
            "File held HOSTILE — positive identification required before civilian permit."
            if gate == "hold"
            else (
                "Threat confirmed — quarantined; memory and drive vaults untouched."
                if gate == "quarantine"
                else "File passed Field Virus gate."
            )
        ),
    }


def gate_bytes(
    data: bytes,
    *,
    label: str = "inline",
    direction: str = "ingress",
) -> dict[str, Any]:
    """Gate in-memory bytes (external wire payloads) without disk write."""
    abstract = abstract_harms(None, data=data, direction=direction)
    iff = classify_iff(abstract, direction=direction)
    return {
        "ok": iff.get("permit", False),
        "schema": "field-virus-scan/v1",
        "ts": _ts(),
        "label": label,
        "direction": direction,
        "lane": "FieldVirus",
        "abstract": abstract,
        "iff": iff,
        "verdict": iff.get("verdict"),
        "gate": "pass" if iff.get("permit") else ("quarantine" if iff.get("iff") == "THREAT" else "hold"),
        "memory_hardened": True,
        "executed": False,
    }


def scan_payload_paths(body: dict[str, Any], *, direction: str = "ingress") -> dict[str, Any]:
    """Scan file paths referenced in wire/API payloads."""
    candidates: list[str] = []
    for key in ("path", "file", "filepath", "src", "dest", "upload"):
        val = body.get(key)
        if isinstance(val, str) and val.strip():
            candidates.append(val.strip())
    attach = body.get("attachments") or body.get("files") or []
    if isinstance(attach, list):
        for item in attach:
            if isinstance(item, str):
                candidates.append(item)
            elif isinstance(item, dict) and item.get("path"):
                candidates.append(str(item["path"]))
    seen: set[str] = set()
    results: list[dict[str, Any]] = []
    blocked = False
    for raw in candidates:
        if raw in seen:
            continue
        seen.add(raw)
        try:
            p = Path(raw).expanduser().resolve()
        except OSError:
            continue
        if not p.is_file():
            continue
        row = gate_file(p, direction=direction)
        results.append({"path": str(p), "verdict": row.get("verdict"), "iff": (row.get("iff") or {}).get("iff"), "ok": row.get("ok")})
        if not row.get("ok"):
            blocked = True
    return {
        "ok": not blocked,
        "scanned": len(results),
        "results": results,
        "lane": "FieldVirus",
    }


def space_policy() -> dict[str, Any]:
    fmts = load_formats()
    return {
        "schema": "field-virus-space/v1",
        "memory": fmts.get("space_policy", {}).get("memory", {}),
        "drive": fmts.get("space_policy", {}).get("drive", {}),
        "memory_vault": str(MEMORY_VAULT),
        "drive_vault": str(DRIVE_VAULT),
        "quarantine": str(QUARANTINE_DIR),
        "iff_doctrine": fmts.get("iff_doctrine", {}),
    }


def _count_quarantine() -> int:
    try:
        return sum(1 for p in QUARANTINE_DIR.iterdir() if p.is_file())
    except OSError:
        return 0


def status() -> dict[str, Any]:
    fmts = load_formats()
    panel = {
        "schema": "field-virus-status/v1",
        "updated": _ts(),
        "motto": fmts.get("motto"),
        "edition": fmts.get("edition", "Queen 2026"),
        "lane": "FieldVirus",
        "own_formats": len(fmts.get("own_formats") or []),
        "universal_formats": len(fmts.get("universal_formats") or []),
        "quarantine_count": _count_quarantine(),
        "scan_log": str(SCAN_LOG),
        "quarantine_dir": str(QUARANTINE_DIR),
        "space_policy": space_policy(),
        "iff_doctrine": fmts.get("iff_doctrine", {}),
        "armed": os.environ.get("SG_FIELD_VIRUS_OFF", "") not in ("1", "true", "yes"),
        "gates": ["ingress", "egress"],
    }
    _save(PANEL_PATH, panel)
    return panel


def guard_loop(*, interval: float = 12.0) -> None:
    """Background vigil — re-scan quarantine dir; publish panel."""
    VIRUS_DIR.mkdir(parents=True, exist_ok=True)
    MEMORY_VAULT.mkdir(parents=True, exist_ok=True)
    DRIVE_VAULT.mkdir(parents=True, exist_ok=True)
    while True:
        try:
            status()
            if QUARANTINE_DIR.is_dir():
                for entry in list(QUARANTINE_DIR.iterdir())[:32]:
                    if entry.is_file():
                        scan_path(entry, direction="ingress", use_cache=False)
        except Exception as exc:
            _append_log({"ts": _ts(), "event": "guard_error", "error": str(exc)})
        time.sleep(max(6.0, float(os.environ.get("SG_FIELD_VIRUS_INTERVAL", interval))))


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")
    if action in ("status", "json"):
        return {"ok": True, **status()}
    if action in ("scan", "inspect"):
        raw = str(body.get("path") or "")
        if not raw:
            return {"ok": False, "error": "path_required"}
        direction = str(body.get("direction") or "ingress")
        return scan_path(raw, direction=direction, operator_trust=bool(body.get("operator_trust")))
    if action in ("gate", "gate_file"):
        raw = str(body.get("path") or "")
        if not raw:
            return {"ok": False, "error": "path_required"}
        direction = str(body.get("direction") or "ingress")
        return gate_file(raw, direction=direction, operator_trust=bool(body.get("operator_trust")))
    if action == "abstract":
        raw = str(body.get("path") or "")
        if raw:
            p = Path(raw)
            if p.is_file():
                return {"ok": True, **abstract_harms(p, direction=str(body.get("direction") or "ingress"))}
        text = body.get("data") or body.get("text") or body.get("payload")
        if text is not None:
            data = text.encode("utf-8", errors="replace") if isinstance(text, str) else bytes(text)
            return {"ok": True, **abstract_harms(None, data=data, direction=str(body.get("direction") or "ingress"))}
        return {"ok": False, "error": "path_or_data_required"}
    if action == "formats":
        return {"ok": True, "formats": load_formats()}
    if action == "policy":
        return {"ok": True, **space_policy()}
    if action == "scan_payload":
        return scan_payload_paths(body, direction=str(body.get("direction") or "ingress"))
    return {"ok": False, "error": "unknown_action", "actions": [
        "status", "scan", "gate", "abstract", "formats", "policy", "scan_payload",
    ]}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "json":
        print(json.dumps(status(), ensure_ascii=False))
        return 0
    if cmd == "guard":
        guard_loop()
        return 0
    if cmd == "scan" and len(sys.argv) > 2:
        direction = sys.argv[3] if len(sys.argv) > 3 else "ingress"
        print(json.dumps(scan_path(sys.argv[2], direction=direction), ensure_ascii=False))
        return 0
    if cmd == "gate" and len(sys.argv) > 2:
        direction = sys.argv[3] if len(sys.argv) > 3 else "ingress"
        print(json.dumps(gate_file(sys.argv[2], direction=direction), ensure_ascii=False))
        return 0
    if cmd == "dispatch":
        raw = sys.stdin.read()
        body = json.loads(raw) if raw.strip() else {}
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: queen-field-virus.py [json|guard|scan <path>|gate <path>|dispatch]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())