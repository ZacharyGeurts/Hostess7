#!/usr/bin/env pythong
"""Field I/O packet — sovereign time in; notify when out is ready; voltage regulated; SDF after evaluation."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
DOCTRINE = INSTALL / "data" / "field-io-packet-doctrine.json"
PANEL = STATE / "field-io-packet-panel.json"
CONVERSATION_STREAM = STATE / "field-io-conversation.stream.jsonl"
PENDING_OUT = STATE / "field-io-pending-out.jsonl"
NOTIFY = STATE / "field-io-packet-notify.json"
SDF_EXPORT = STATE / "field-io-sdf-export.jsonl"
PACKET_LEDGER = STATE / "field-io-packet-ledger.jsonl"
SCHEMA = "field-io-packet/v1"
SDF_SCHEMA = "field-io-sdf/v1"
MELD_CITATION = "ironclad:meld:2"

_VERB_AMPLITUDE: dict[str, float] = {
    "say": 0.55,
    "move_leg": 0.82,
    "turn_head": 0.74,
    "tilt_head": 0.68,
    "step": 0.85,
    "gesture": 0.62,
    "point": 0.58,
    "reach": 0.76,
    "wave": 0.60,
    "nod": 0.48,
    "blink": 0.35,
    "pause": 0.12,
    "look": 0.52,
    "shift_weight": 0.70,
    "raise_hand": 0.64,
}

_SEQ = 0
_MOD_CACHE: dict[str, Any] = {}

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


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        py = Path(__file__).resolve().parent / "sovereign-clock.py"
        spec = importlib.util.spec_from_file_location("sovereign_clock_io", py)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            _SOVEREIGN_CLOCK_MOD = mod
    if _SOVEREIGN_CLOCK_MOD and hasattr(_SOVEREIGN_CLOCK_MOD, "utc_z"):
        return _SOVEREIGN_CLOCK_MOD.utc_z("field_io")
    return ""


def _mod(py: Path, name: str) -> Any | None:
    key = str(py)
    if key in _MOD_CACHE:
        return _MOD_CACHE[key]
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _MOD_CACHE[key] = mod
    return mod


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        fh.flush()
        try:
            os.fsync(fh.fileno())
        except OSError:
            pass


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def sovereign_time_input() -> dict[str, Any]:
    clk = _mod(Path(__file__).resolve().parent / "sovereign-clock.py", "sovereign_clock_io_in")
    if not clk:
        return {"ok": False, "error": "sovereign_clock_missing"}
    try:
        know = clk.know() if hasattr(clk, "know") else {}
        linear_ns = int(know.get("linear_ns") or know.get("derived_ns") or 0)
        if linear_ns <= 0 and hasattr(clk, "ns_linear"):
            linear_ns = int(clk.ns_linear())
        return {
            "ok": True,
            "schema": "field-io-sovereign-input/v1",
            "linear_ns": linear_ns,
            "derived_utc": str(know.get("utc") or clk.utc_z("field_io")),
            "never_desync": bool(know.get("never_desync", True)),
            "immutable_linear": bool(know.get("immutable_linear", True)),
            "synced": bool((know.get("desync") or {}).get("synced", know.get("synced", True))),
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def voltage_gate() -> dict[str, Any]:
    """Present-rail voltage regulation — grid blocked from trust layer."""
    vr = _mod(INSTALL / "lib" / "field-voltage-regulation.py", "voltage_reg_io")
    if not vr or not hasattr(vr, "evaluate"):
        return {"ok": False, "id": "voltage_regulation", "error": "voltage_module_missing"}
    try:
        doc = vr.evaluate(seal=False)
        return {
            "ok": bool(doc.get("ok")),
            "id": "voltage_regulation",
            "operate_at_present_rail": bool(doc.get("operate_at_present_rail")),
            "grid_blocked": doc.get("power_company_grid_trust_layer") == "blocked",
            "no_conversion": doc.get("conversion_on_voltage_path") is False,
            "no_entropy": doc.get("entropy_on_trust_layer") is False,
            "voltage_is_voltage": bool(doc.get("voltage_is_voltage")),
            "voltage_started_at": doc.get("voltage_started_at"),
        }
    except Exception as exc:
        return {"ok": False, "id": "voltage_regulation", "error": str(exc)}


def truth_gate() -> dict[str, Any]:
    """Gate file I/O on Ironclad + field sanity + G1ID baselines + voltage regulation."""
    iron: dict[str, Any] = {"ok": False, "id": "ironclad"}
    sanity: dict[str, Any] = {"ok": False, "id": "field_sanity"}
    baselines: dict[str, Any] = {"ok": False, "id": "g1id_baselines"}
    voltage: dict[str, Any] = voltage_gate()

    ic = _mod(INSTALL / "lib" / "ironclad-plate.py", "ironclad_io_gate")
    if ic and hasattr(ic, "verify_integrity"):
        try:
            integrity = ic.verify_integrity()
            iron = {
                "ok": bool(integrity.get("ok")),
                "id": "ironclad",
                "realized": bool(integrity.get("realized")),
                "immutable": bool(integrity.get("immutable")),
                "canonical_hash": integrity.get("canonical_hash"),
                "detail": integrity.get("detail"),
            }
        except Exception as exc:
            iron = {"ok": False, "id": "ironclad", "error": str(exc)}

    fs = _mod(INSTALL / "lib" / "ironclad-field-sanity.py", "field_sanity_io_gate")
    if fs and hasattr(fs, "build_panel"):
        try:
            panel = fs.build_panel(write=False)
            receipt = panel.get("ironclad") or {}
            queen = panel.get("queen") or {}
            layers_in = int(queen.get("layers_in") or 0)
            sanity_ok = bool(
                receipt.get("absorbed")
                and receipt.get("integrity_ok")
                and receipt.get("ironclad_sealed")
                and (
                    receipt.get("pass_ok")
                    or (
                        queen.get("ok")
                        and queen.get("integral")
                        and layers_in == 0
                    )
                )
            )
            sanity = {
                "ok": sanity_ok,
                "id": "field_sanity",
                "pass_ok": bool(receipt.get("pass_ok")),
                "absorbed": bool(receipt.get("absorbed")),
                "integral": queen.get("integral") or receipt.get("integral"),
                "ironclad_sealed": bool(receipt.get("ironclad_sealed")),
                "layers_in": layers_in,
            }
        except Exception as exc:
            sanity = {"ok": False, "id": "field_sanity", "error": str(exc)}

    bl = _mod(INSTALL / "lib" / "g1id-baseline.py", "g1id_baseline_io_gate")
    if bl and hasattr(bl, "verify_all"):
        try:
            verify = bl.verify_all()
            baselines = {
                "ok": bool(verify.get("ok")),
                "id": "g1id_baselines",
                "required_ok": bool(verify.get("required_ok")),
                "count": verify.get("count"),
            }
        except Exception as exc:
            baselines = {"ok": False, "id": "g1id_baselines", "error": str(exc)}

    pass_ok = bool(
        iron.get("ok") and sanity.get("ok") and baselines.get("ok") and voltage.get("ok")
    )
    advisory: dict[str, Any] = {"advisory_only": True, "skipped": True}
    wholes = _mod(INSTALL / "lib" / "field-body-component-wholes.py", "fio_wholes_advisory")
    if wholes and hasattr(wholes, "advisory_for_truth_gate"):
        try:
            advisory = wholes.advisory_for_truth_gate(skip_refresh=True)
        except Exception as exc:
            advisory = {"advisory_only": True, "error": str(exc)}
    beyond_darpa: dict[str, Any] = {"advisory_only": True, "skipped": True}
    bds = _mod(INSTALL / "lib" / "beyond-darpa-security.py", "fio_beyond_darpa_advisory")
    if bds and hasattr(bds, "advisory_for_truth_gate"):
        try:
            beyond_darpa = bds.advisory_for_truth_gate(skip_refresh=True)
        except Exception as exc:
            beyond_darpa = {"advisory_only": True, "error": str(exc)}
    return {
        "schema": "field-io-truth-gate/v1",
        "pass_ok": pass_ok,
        "meld_citation": MELD_CITATION,
        "ironclad": iron,
        "field_sanity": sanity,
        "g1id_baselines": baselines,
        "voltage_regulation": voltage,
        "advisory": advisory,
        "beyond_darpa_security": beyond_darpa,
        "advisory_never_defeats_gate": True,
        "file_write_forbidden": True,
        "output_stream_only": True,
        "await_output_forbidden": True,
        "no_hacks": True,
        "checked_at": _now(),
    }


def _pending_count() -> int:
    if not PENDING_OUT.is_file():
        return 0
    try:
        return sum(1 for line in PENDING_OUT.read_text(encoding="utf-8").splitlines() if line.strip())
    except OSError:
        return 0


def _write_notify(*, packet_id: str, verb: str, linear_ns: int, derived_utc: str) -> dict[str, Any]:
    """Signal that a packet is ready — we do not await; the field notifies us."""
    doc = {
        "schema": "field-io-notify/v1",
        "await_forbidden": True,
        "notify": True,
        "pending_count": _pending_count(),
        "latest": {
            "packet_id": packet_id,
            "verb": verb,
            "linear_ns": linear_ns,
            "notify_at": derived_utc,
            "message": "packet_ready_pull_when_you_want",
        },
        "updated": _now(),
    }
    _save(NOTIFY, doc)
    try:
        h7n = INSTALL / "lib" / "hostess7-noti.py"
        if h7n.is_file():
            import subprocess
            import sys

            subprocess.run(
                [sys.executable, str(h7n), "dispatch"],
                input=json.dumps({"action": "field_io", "notify": doc}),
                capture_output=True,
                text=True,
                timeout=30,
                env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
            )
    except (OSError, subprocess.TimeoutExpired):
        pass
    return doc


def check_notify() -> dict[str, Any]:
    """Non-blocking — tells us when a packet needs to come through."""
    doc = _load(NOTIFY, {})
    if not doc:
        return {
            "schema": "field-io-notify/v1",
            "notify": False,
            "await_forbidden": True,
            "pending_count": _pending_count(),
            "message": "no_pending_notify",
        }
    doc.setdefault("await_forbidden", True)
    doc["pending_count"] = _pending_count()
    return doc


def _conversation_verbs() -> set[str]:
    doc = _load(DOCTRINE, {})
    return {str(v) for v in (doc.get("conversation_verbs") or [])}


def _read_allowlist(rel: str) -> bool:
    doc = _load(DOCTRINE, {})
    prefixes = doc.get("read_allowlist_prefixes") or []
    norm = rel.replace("\\", "/").lstrip("/")
    return any(norm.startswith(str(p)) for p in prefixes)


def gate_read(path: Path | str) -> dict[str, Any]:
    """Truth-gated cold read — baselines and doctrine only."""
    gate = truth_gate()
    if not gate.get("pass_ok"):
        return {"ok": False, "error": "truth_gate_failed", "truth_gate": gate}
    p = Path(path)
    if p.is_absolute():
        try:
            rel = str(p.relative_to(INSTALL))
        except ValueError:
            return {"ok": False, "error": "path_outside_install", "path": str(p)}
    else:
        rel = str(p).replace("\\", "/").lstrip("/")
        p = INSTALL / rel
    if not _read_allowlist(rel):
        return {"ok": False, "error": "read_not_allowlisted", "path": rel, "truth_gate": gate}
    if not p.is_file():
        return {"ok": False, "error": "missing", "path": rel}
    if p.suffix.lower() == ".g1id":
        bl = _mod(INSTALL / "lib" / "g1id-baseline.py", "g1id_read_gate")
        if bl and hasattr(bl, "verify_baseline"):
            return {**bl.verify_baseline(p), "truth_gate": gate, "read_kind": "baseline"}
    try:
        raw = p.read_bytes()
        if len(raw) > 65536:
            return {"ok": False, "error": "file_too_large", "path": rel}
        doc = json.loads(raw.decode("utf-8"))
        return {
            "ok": True,
            "path": rel,
            "read_kind": "doctrine",
            "bytes": len(raw),
            "document": doc,
            "truth_gate": gate,
        }
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": str(exc), "path": rel, "truth_gate": gate}


def gate_write(path: Path | str, **_kwargs: Any) -> dict[str, Any]:
    """All direct file writes forbidden — output is conversation stream only."""
    gate = truth_gate()
    return {
        "ok": False,
        "error": "file_write_forbidden",
        "policy": "output_stream_only",
        "path": str(path),
        "truth_gate": gate,
        "hint": "emit_conversation() for move_leg, turn_head, say, etc.",
    }


def _next_seq() -> int:
    global _SEQ
    _SEQ += 1
    return _SEQ


def build_packet(
    *,
    direction: str,
    body: dict[str, Any] | None = None,
    gate: dict[str, Any] | None = None,
    sovereign: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble field I/O packet envelope."""
    if direction not in ("in", "out"):
        raise ValueError("direction must be in or out")
    st = sovereign or sovereign_time_input()
    if not st.get("ok"):
        raise ValueError(st.get("error") or "sovereign_time_unavailable")
    tg = gate or truth_gate()
    seq = _next_seq()
    packet: dict[str, Any] = {
        "schema": SCHEMA,
        "packet_id": hashlib.sha256(f"{st.get('linear_ns')}:{seq}:{direction}".encode()).hexdigest()[:16],
        "direction": direction,
        "seq": seq,
        "sovereign_time": {k: v for k, v in st.items() if k != "ok"},
        "truth_gate": {
            "pass_ok": tg.get("pass_ok"),
            "meld_citation": tg.get("meld_citation"),
            "ironclad_ok": (tg.get("ironclad") or {}).get("ok"),
            "sanity_ok": (tg.get("field_sanity") or {}).get("ok"),
            "baselines_ok": (tg.get("g1id_baselines") or {}).get("ok"),
            "voltage_ok": (tg.get("voltage_regulation") or {}).get("ok"),
        },
        "io_policy": {
            "file_write_forbidden": True,
            "output_stream_only": True,
            "await_output_forbidden": True,
            "notify_when_ready": direction == "out",
            "sovereign_time_in_only": direction == "in",
        },
        "body": body or {},
    }
    packet["integrity"] = {
        "payload_hash": hashlib.sha256(
            json.dumps(
                {
                    "direction": packet["direction"],
                    "seq": packet["seq"],
                    "sovereign_time": packet["sovereign_time"],
                    "truth_gate": packet["truth_gate"],
                    "body": packet["body"],
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest(),
        "sealed_at": st.get("derived_utc"),
    }
    return packet


def process_in(*, kind: str = "sovereign_tick", path: str = "") -> dict[str, Any]:
    """Sovereign time in — optional gated baseline/doctrine read."""
    gate = truth_gate()
    st = sovereign_time_input()
    if not st.get("ok"):
        return {"ok": False, "error": "sovereign_time_unavailable", "truth_gate": gate}
    body: dict[str, Any] = {"kind": kind, "sovereign_tick": True}
    if kind == "baseline_verify" and path:
        read = gate_read(path)
        body["read"] = read
        if not read.get("ok"):
            pkt = build_packet(direction="in", body=body, gate=gate, sovereign=st)
            _append_jsonl(PACKET_LEDGER, {"ts": _now(), "event": "in_reject", "packet": pkt})
            return {"ok": False, "packet": pkt, "read": read}
    elif kind == "doctrine_read" and path:
        read = gate_read(path)
        body["read"] = read
    pkt = build_packet(direction="in", body=body, gate=gate, sovereign=st)
    _append_jsonl(PACKET_LEDGER, {"ts": _now(), "event": "in", "packet": pkt})
    return {"ok": gate.get("pass_ok", False), "packet": pkt, "truth_gate": gate}


def queue_conversation(
    *,
    verb: str,
    text: str = "",
    params: dict[str, Any] | None = None,
    actor: str = "this_one",
) -> dict[str, Any]:
    """Queue out packet and notify — never await output; no hacks."""
    gate = truth_gate()
    verbs = _conversation_verbs()
    v = str(verb).strip().lower()
    if v not in verbs:
        return {
            "ok": False,
            "error": "verb_not_allowed",
            "verb": v,
            "allowed": sorted(verbs),
            "truth_gate": gate,
        }
    if not gate.get("pass_ok"):
        return {"ok": False, "error": "truth_gate_failed", "truth_gate": gate}
    st = sovereign_time_input()
    if not st.get("ok"):
        return {"ok": False, "error": "sovereign_time_unavailable"}
    body = {
        "kind": "conversation",
        "actor": actor,
        "verb": v,
        "text": str(text)[:2048],
        "params": params or {},
        "queued": True,
        "evaluated": False,
        "sdf_exported": False,
    }
    pkt = build_packet(direction="out", body=body, gate=gate, sovereign=st)
    pending_row = {
        "ts": st.get("derived_utc"),
        "linear_ns": st.get("linear_ns"),
        "packet_id": pkt.get("packet_id"),
        "packet": pkt,
        "status": "pending",
    }
    _append_jsonl(PENDING_OUT, pending_row)
    _append_jsonl(PACKET_LEDGER, {"ts": _now(), "event": "queued_out", "packet": pkt})
    notify = _write_notify(
        packet_id=str(pkt.get("packet_id")),
        verb=v,
        linear_ns=int(st.get("linear_ns") or 0),
        derived_utc=str(st.get("derived_utc") or ""),
    )
    return {
        "ok": True,
        "queued": True,
        "await_forbidden": True,
        "notify": True,
        "packet_id": pkt.get("packet_id"),
        "verb": v,
        "notify_doc": notify,
        "hint": "check_notify() or pull_pending() when you want the packet — we do not await",
    }


def emit_conversation(
    *,
    verb: str,
    text: str = "",
    params: dict[str, Any] | None = None,
    actor: str = "this_one",
) -> dict[str, Any]:
    """Alias — queues and notifies; does not block on output."""
    return queue_conversation(verb=verb, text=text, params=params, actor=actor)


def pull_pending(*, limit: int = 1) -> dict[str, Any]:
    """Operator-initiated pull — moves pending packets to conversation stream."""
    if not PENDING_OUT.is_file():
        return {"ok": True, "pulled": 0, "packets": [], "await_forbidden": True}
    try:
        lines = [ln for ln in PENDING_OUT.read_text(encoding="utf-8").splitlines() if ln.strip()]
    except OSError:
        return {"ok": False, "error": "pending_read_failed"}
    pulled: list[dict[str, Any]] = []
    remain: list[str] = []
    for i, line in enumerate(lines):
        if len(pulled) >= max(1, limit):
            remain.append(line)
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        pkt = row.get("packet") or {}
        body = pkt.get("body") or {}
        stream_row = {
            "ts": row.get("ts"),
            "linear_ns": row.get("linear_ns"),
            "actor": body.get("actor"),
            "verb": body.get("verb"),
            "text": body.get("text"),
            "params": body.get("params"),
            "packet_id": row.get("packet_id"),
            "integrity": pkt.get("integrity"),
            "packet_ref": pkt,
            "pulled_at": _now(),
        }
        _append_jsonl(CONVERSATION_STREAM, stream_row)
        _append_jsonl(PACKET_LEDGER, {"ts": _now(), "event": "pulled_out", "packet": pkt})
        pulled.append({"packet_id": row.get("packet_id"), "verb": body.get("verb"), "stream": stream_row})
    if remain:
        PENDING_OUT.write_text("\n".join(remain) + "\n", encoding="utf-8")
    else:
        try:
            PENDING_OUT.unlink()
        except OSError:
            PENDING_OUT.write_text("", encoding="utf-8")
    if _pending_count() == 0:
        _save(
            NOTIFY,
            {
                "schema": "field-io-notify/v1",
                "notify": False,
                "await_forbidden": True,
                "pending_count": 0,
                "updated": _now(),
            },
        )
    else:
        latest = json.loads(remain[-1]) if remain else {}
        pkt = latest.get("packet") or {}
        body = pkt.get("body") or {}
        _write_notify(
            packet_id=str(latest.get("packet_id") or pkt.get("packet_id") or ""),
            verb=str(body.get("verb") or ""),
            linear_ns=int(latest.get("linear_ns") or 0),
            derived_utc=str(latest.get("ts") or _now()),
        )
    return {"ok": True, "pulled": len(pulled), "packets": pulled, "await_forbidden": True}


def _find_packet(packet_id: str) -> dict[str, Any] | None:
    pid = str(packet_id).strip()
    if not pid:
        return None
    if PACKET_LEDGER.is_file():
        try:
            for line in reversed(PACKET_LEDGER.read_text(encoding="utf-8").splitlines()):
                if pid not in line:
                    continue
                row = json.loads(line)
                pkt = row.get("packet") or {}
                if str(pkt.get("packet_id")) == pid and pkt.get("schema") == SCHEMA:
                    return pkt
        except (OSError, json.JSONDecodeError):
            pass
    if PENDING_OUT.is_file():
        try:
            for line in PENDING_OUT.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                pkt = row.get("packet") or {}
                if str(pkt.get("packet_id")) == pid or str(row.get("packet_id")) == pid:
                    return pkt if pkt.get("schema") == SCHEMA else row.get("packet")
        except (OSError, json.JSONDecodeError):
            pass
    return None


def evaluate_packet(packet_id: str) -> dict[str, Any]:
    """Truth + voltage evaluation before any SDF share — no hacks."""
    pkt = _find_packet(packet_id)
    if not pkt:
        return {"ok": False, "error": "packet_not_found", "packet_id": packet_id}
    gate = truth_gate()
    body = pkt.get("body") or {}
    integrity = pkt.get("integrity") or {}
    expected = hashlib.sha256(
        json.dumps(
            {
                "direction": pkt.get("direction"),
                "seq": pkt.get("seq"),
                "sovereign_time": pkt.get("sovereign_time"),
                "truth_gate": pkt.get("truth_gate"),
                "body": body,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    integrity_ok = integrity.get("payload_hash") == expected
    verb = str(body.get("verb") or "")
    verb_ok = verb in _conversation_verbs()
    pass_ok = bool(gate.get("pass_ok") and integrity_ok and verb_ok and pkt.get("direction") == "out")
    result = {
        "schema": "field-io-packet-evaluation/v1",
        "ok": pass_ok,
        "packet_id": packet_id,
        "pass_ok": pass_ok,
        "integrity_ok": integrity_ok,
        "verb_ok": verb_ok,
        "truth_gate": gate,
        "voltage_ok": (gate.get("voltage_regulation") or {}).get("ok"),
        "share_sdf_allowed": pass_ok,
        "evaluated_at": _now(),
        "no_hacks": True,
    }
    _append_jsonl(PACKET_LEDGER, {"ts": _now(), "event": "evaluate", "evaluation": result})
    return result


def translate_to_sdf(packet_id: str) -> dict[str, Any]:
    """Translator to SDF — only after evaluation pass; for sharing after review."""
    ev = evaluate_packet(packet_id)
    if not ev.get("pass_ok"):
        return {
            "ok": False,
            "error": "evaluation_failed",
            "evaluation": ev,
            "share_forbidden": True,
        }
    pkt = _find_packet(packet_id)
    if not pkt:
        return {"ok": False, "error": "packet_not_found", "packet_id": packet_id}
    body = pkt.get("body") or {}
    verb = str(body.get("verb") or "pause")
    text = str(body.get("text") or "")
    amp = _VERB_AMPLITUDE.get(verb, 0.5)
    doctrine = _load(DOCTRINE, {})
    anchor = (doctrine.get("sdf_translator") or {}).get("topology_anchor") or [256, 192]
    text_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    sdf_doc = {
        "schema": SDF_SCHEMA,
        "id": f"io-{packet_id}",
        "source": "field-io-packet",
        "action": "conversation_plate",
        "verb": verb,
        "text": text,
        "caption_stub": text[:120],
        "text_sha256": text_sha,
        "topology": {
            "anchor": anchor,
            "amplitude": round(amp, 4),
            "units": "normalized",
            "voltage_is_voltage": True,
        },
        "evaluation": {
            "pass_ok": ev.get("pass_ok"),
            "integrity_ok": ev.get("integrity_ok"),
            "voltage_ok": ev.get("voltage_ok"),
        },
        "sovereign_time": pkt.get("sovereign_time"),
        "integrity": pkt.get("integrity"),
        "lossless": True,
        "share_after_evaluation_only": True,
        "translator": "field-io-packet",
        "exported_at": _now(),
    }
    sdf_doc["sdf_hash"] = hashlib.sha256(
        json.dumps(sdf_doc, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    _append_jsonl(SDF_EXPORT, sdf_doc)
    _append_jsonl(PACKET_LEDGER, {"ts": _now(), "event": "sdf_export", "packet_id": packet_id, "sdf_id": sdf_doc["id"]})
    return {"ok": True, "sdf": sdf_doc, "evaluation": ev, "export_path": str(SDF_EXPORT)}


def conversation_stream(*, limit: int = 20) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    if CONVERSATION_STREAM.is_file():
        try:
            lines = CONVERSATION_STREAM.read_text(encoding="utf-8").strip().splitlines()
            for line in lines[-max(1, limit) :]:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        except OSError:
            pass
    return {
        "schema": "field-io-conversation-stream/v1",
        "path": str(CONVERSATION_STREAM),
        "count": len(rows),
        "entries": rows,
        "output_only": True,
    }


def build_panel(*, write: bool = True) -> dict[str, Any]:
    gate = truth_gate()
    stream = conversation_stream(limit=5)
    notify = check_notify()
    panel = {
        "schema": "field-io-packet-panel/v1",
        "updated": _now(),
        "title": "Field I/O Packet — sovereign in, notify when out ready",
        "meld_citation": MELD_CITATION,
        "ok": gate.get("pass_ok"),
        "truth_gate": gate,
        "policy": (_load(DOCTRINE, {}).get("policy") or {}),
        "notify": notify,
        "pending_count": _pending_count(),
        "await_output_forbidden": True,
        "voltage_regulation": gate.get("voltage_regulation"),
        "conversation_stream": {
            "path": str(CONVERSATION_STREAM),
            "count": stream.get("count"),
            "recent": stream.get("entries"),
        },
        "pending_out": str(PENDING_OUT),
        "sdf_export": str(SDF_EXPORT),
        "ledger": str(PACKET_LEDGER),
        "doctrine_ref": str(DOCTRINE.relative_to(INSTALL)) if DOCTRINE.is_file() else None,
    }
    if write:
        _save(PANEL, panel)
    return panel


def melded_extension_slice() -> dict[str, Any]:
    panel = build_panel(write=False)
    return {
        "id": "field_io_packet",
        "absorbed": DOCTRINE.is_file(),
        "meld_citation": MELD_CITATION,
        "ok": panel.get("ok"),
        "truth_gate_pass": (panel.get("truth_gate") or {}).get("pass_ok"),
        "sovereign_time_in": True,
        "conversation_out_only": True,
        "await_output_forbidden": True,
        "notify_when_ready": True,
        "voltage_regulated": bool((panel.get("voltage_regulation") or {}).get("ok")),
        "file_write_forbidden": True,
        "sdf_after_evaluation": True,
        "pending_count": panel.get("pending_count"),
        "stream_count": (panel.get("conversation_stream") or {}).get("count"),
        "updated": panel.get("updated"),
    }


def bus_pack() -> dict[str, int]:
    """Pack I/O lane words for unified bus slots 44–47."""
    gate = truth_gate()
    panel = build_panel(write=False)
    stream_count = int((panel.get("conversation_stream") or {}).get("count") or 0)

    def _word(mag: int, tier: int = 0, flags: int = 0) -> int:
        return (mag & 0xFF) | ((tier & 0xFF) << 8) | ((flags & 0xFF) << 16) | ((44 & 0xFF) << 24)

    pending = _pending_count()
    voltage_ok = (gate.get("voltage_regulation") or {}).get("ok")
    return {
        "io_gate_pass": _word(1 if gate.get("pass_ok") else 0, flags=0x01),
        "io_sanity_ok": _word(1 if (gate.get("field_sanity") or {}).get("ok") else 0),
        "io_baselines_ok": _word(1 if (gate.get("g1id_baselines") or {}).get("ok") else 0),
        "io_stream_count": _word(min(pending or stream_count, 255), flags=0x04 if voltage_ok else 0),
    }


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(build_panel(), ensure_ascii=False))
        return 0
    if cmd == "gate":
        print(json.dumps(truth_gate(), ensure_ascii=False))
        return 0
    if cmd == "in":
        kind = sys.argv[2] if len(sys.argv) > 2 else "sovereign_tick"
        path = sys.argv[3] if len(sys.argv) > 3 else ""
        out = process_in(kind=kind, path=path)
        print(json.dumps(out, ensure_ascii=False))
        return 0 if out.get("ok") else 1
    if cmd in ("emit", "queue") and len(sys.argv) > 2:
        verb = sys.argv[2]
        text = sys.argv[3] if len(sys.argv) > 3 else ""
        out = queue_conversation(verb=verb, text=text)
        print(json.dumps(out, ensure_ascii=False))
        return 0 if out.get("ok") else 1
    if cmd == "notify":
        print(json.dumps(check_notify(), ensure_ascii=False))
        return 0
    if cmd == "pull":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        print(json.dumps(pull_pending(limit=limit), ensure_ascii=False))
        return 0
    if cmd == "evaluate" and len(sys.argv) > 2:
        out = evaluate_packet(sys.argv[2])
        print(json.dumps(out, ensure_ascii=False))
        return 0 if out.get("ok") else 1
    if cmd in ("translate-sdf", "sdf") and len(sys.argv) > 2:
        out = translate_to_sdf(sys.argv[2])
        print(json.dumps(out, ensure_ascii=False))
        return 0 if out.get("ok") else 1
    if cmd == "read" and len(sys.argv) > 2:
        out = gate_read(sys.argv[2])
        print(json.dumps(out, ensure_ascii=False, default=str))
        return 0 if out.get("ok") else 1
    if cmd == "write":
        path = sys.argv[2] if len(sys.argv) > 2 else "/tmp/forbidden"
        out = gate_write(path)
        print(json.dumps(out, ensure_ascii=False))
        return 1
    if cmd == "stream":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        print(json.dumps(conversation_stream(limit=limit), ensure_ascii=False))
        return 0
    if cmd == "slice":
        print(json.dumps(melded_extension_slice(), ensure_ascii=False))
        return 0
    if cmd == "demo":
        demos = [
            ("say", "Voltage regulated — notify when ready."),
            ("turn_head", "left"),
            ("move_leg", "step forward"),
        ]
        results = [queue_conversation(verb=v, text=t) for v, t in demos]
        notify = check_notify()
        pulled = pull_pending(limit=3)
        sdf_rows = []
        for row in pulled.get("packets") or []:
            pid = row.get("packet_id")
            if pid:
                sdf_rows.append(translate_to_sdf(str(pid)))
        print(json.dumps({
            "ok": all(r.get("ok") for r in results),
            "queued": results,
            "notify": notify,
            "pulled": pulled,
            "sdf": sdf_rows,
            "await_forbidden": True,
        }, ensure_ascii=False))
        return 0
    print(json.dumps({
        "error": "usage: field-io-packet.py [json|gate|notify|queue VERB [TEXT]|pull [N]|evaluate ID|translate-sdf ID|in|read|write|stream|slice|demo]",
        "doctrine": str(DOCTRINE),
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())