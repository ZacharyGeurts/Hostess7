#!/usr/bin/env pythong
"""Sovereign linear time — immutable; nothing adjusts the timer.

Linear clock advances from a sealed monotonic epoch only. Temperature, thermal,
cpufreq, NTP, and RTC are witness-only — they never touch linear time.
``Take time out`` means gap detection or red flag — not pause, not stop.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import socket
import struct
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))

RECEIPT_LOG = STATE / "sovereign-time-receipts.jsonl"
PULSE_STATE = STATE / "sovereign-time-pulse.json"
KEY_FILE = STATE / "sovereign-time-key.bin"
CYCLE_STATE = STATE / "sovereign-cycle-state.json"
CYCLE_LEDGER = STATE / "sovereign-cycle-ledger.jsonl"
ANCHOR_STATE = STATE / "sovereign-time-anchor.json"
LINEAR_STATE = STATE / "sovereign-linear-time.json"
RED_FLAG_LEDGER = STATE / "sovereign-time-red-flags.jsonl"

DEFAULT_PORT = int(os.environ.get("NEXUS_SOVEREIGN_TIME_PORT", "9123"))
HEARTBEAT_SEC = float(os.environ.get("NEXUS_SOVEREIGN_HEARTBEAT_SEC", "1"))
MAX_SKEW_MS = float(os.environ.get("NEXUS_TIME_MAX_SKEW_MS", "50"))
MAX_FREQ_DELTA_KHZ = int(os.environ.get("NEXUS_TIME_MAX_FREQ_DELTA_KHZ", "250000"))
MAX_LINEAR_GAP_MS = float(os.environ.get("NEXUS_TIME_MAX_LINEAR_GAP_MS", "5"))
SCHEMA = "sovereign-time/v3"
IMMUTABLE_RULE = "Nothing affects linear time; take time out = gap or red flag only"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        fh.flush()
        try:
            os.fsync(fh.fileno())
        except OSError:
            pass


def _save_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _load_linear() -> dict[str, Any]:
    return _load_json(LINEAR_STATE, {})


def _save_linear(doc: dict[str, Any]) -> None:
    doc["immutable_rule"] = IMMUTABLE_RULE
    doc["schema"] = "sovereign-linear-time/v1"
    _save_json(LINEAR_STATE, doc)


def _seal_linear_epoch() -> dict[str, Any]:
    """One-time seal — after this, linear advances by monotonic delta only."""
    linear = _load_linear()
    if linear.get("sealed"):
        return linear
    mono = time.monotonic_ns()
    linear = {
        "schema": "sovereign-linear-time/v1",
        "sealed": True,
        "sealed_at": _now_iso(),
        "epoch_mono_ns": mono,
        "epoch_linear_ns": time.time_ns(),
        "last_linear_ns": time.time_ns(),
        "last_mono_ns": mono,
        "red_flag_count": 0,
        "gap_count": 0,
        "immutable_rule": IMMUTABLE_RULE,
        "policy": "Linear time never stops — take time out means gap or red flag",
    }
    _save_linear(linear)
    _append_jsonl(RECEIPT_LOG, {
        "ts": _now_iso(),
        "event": "linear_sealed",
        "epoch_mono_ns": mono,
        "epoch_linear_ns": linear["epoch_linear_ns"],
    })
    return linear


def linear_time_ns() -> int:
    """Authoritative sovereign linear clock — monotonic epoch only; never pauses."""
    linear = _load_linear()
    if not linear.get("sealed"):
        linear = _seal_linear_epoch()
    epoch_mono = int(linear.get("epoch_mono_ns") or 0)
    epoch_linear = int(linear.get("epoch_linear_ns") or 0)
    return epoch_linear + (time.monotonic_ns() - epoch_mono)


def take_time_out(
    *,
    kind: str = "red_flag",
    reason: str = "witness",
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Gap or red flag — the only response when linear story breaks. Does NOT pause the clock."""
    linear = _load_linear()
    if not linear.get("sealed"):
        linear = _seal_linear_epoch()
    now_linear = linear_time_ns()
    now_mono = time.monotonic_ns()
    row = {
        "ts": derived_utc(),
        "event": "take_time_out",
        "kind": kind,
        "reason": reason,
        "linear_ns": now_linear,
        "mono_ns": now_mono,
        "evidence": evidence or {},
        "affects_linear": False,
        "red_flag": True,
    }
    if kind == "gap":
        linear["gap_count"] = int(linear.get("gap_count") or 0) + 1
        linear["last_gap"] = row
    else:
        linear["red_flag_count"] = int(linear.get("red_flag_count") or 0) + 1
        linear["last_red_flag"] = row
    linear["red_flag_active"] = True
    linear["last_take_time_out"] = derived_utc()
    _save_linear(linear)
    _append_jsonl(RED_FLAG_LEDGER, row)
    _append_jsonl(RECEIPT_LOG, row)
    return {
        "ok": True,
        "take_time_out": True,
        "kind": kind,
        "reason": reason,
        "red_flag": True,
        "linear_ns": now_linear,
        "derived_utc": derived_utc(),
        "immutable_rule": IMMUTABLE_RULE,
        "clock_paused": False,
    }


def _check_linear_gap(sample: dict[str, Any]) -> dict[str, Any] | None:
    """Detect discontinuity in linear chain — take time out (gap), never rewind clock."""
    linear = _load_linear()
    if not linear.get("sealed"):
        return None
    prev_linear = int(linear.get("last_linear_ns") or 0)
    prev_mono = int(linear.get("last_mono_ns") or 0)
    cur_mono = int(sample.get("mono_ns") or 0)
    cur_linear = linear_time_ns()
    if not prev_mono or not prev_linear:
        linear["last_linear_ns"] = cur_linear
        linear["last_mono_ns"] = cur_mono
        _save_linear(linear)
        return None
    d_mono = cur_mono - prev_mono
    d_linear = cur_linear - prev_linear
    if d_mono < 0:
        return take_time_out(
            kind="gap",
            reason="monotonic_backward",
            evidence={"d_mono_ns": d_mono, "prev_mono_ns": prev_mono, "cur_mono_ns": cur_mono},
        )
    if d_linear < 0:
        return take_time_out(
            kind="gap",
            reason="linear_backward",
            evidence={"d_linear_ns": d_linear, "prev_linear_ns": prev_linear, "cur_linear_ns": cur_linear},
        )
    if d_mono > 0:
        gap_ms = abs(d_linear - d_mono) / 1_000_000.0
        if gap_ms > MAX_LINEAR_GAP_MS:
            return take_time_out(
                kind="gap",
                reason=f"linear_mono_gap_{gap_ms:.2f}ms",
                evidence={
                    "gap_ms": gap_ms,
                    "d_mono_ns": d_mono,
                    "d_linear_ns": d_linear,
                },
            )
    linear["last_linear_ns"] = cur_linear
    linear["last_mono_ns"] = cur_mono
    _save_linear(linear)
    return None


def derived_realtime_ns() -> int:
    """Alias — all consumers get linear sovereign time, never mutable wall clock."""
    return linear_time_ns()


def derived_utc() -> str:
    ns = linear_time_ns()
    dt = datetime.fromtimestamp(ns / 1_000_000_000, tz=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def red_flags(*, limit: int = 20) -> dict[str, Any]:
    """Recent gap/red-flag ledger — witness only; clock never paused."""
    rows: list[dict[str, Any]] = []
    if RED_FLAG_LEDGER.is_file():
        try:
            lines = RED_FLAG_LEDGER.read_text(encoding="utf-8").strip().splitlines()
            for line in lines[-max(1, limit) :]:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        except OSError:
            pass
    linear = _load_linear()
    return {
        "schema": "sovereign-time-red-flags/v1",
        "count": len(rows),
        "red_flag_count": int(linear.get("red_flag_count") or 0),
        "gap_count": int(linear.get("gap_count") or 0),
        "red_flag_active": bool(linear.get("red_flag_active")),
        "clock_paused": False,
        "entries": rows,
        "ledger": str(RED_FLAG_LEDGER),
    }


def linear_status() -> dict[str, Any]:
    linear = _load_linear()
    if not linear.get("sealed"):
        linear = _seal_linear_epoch()
    return {
        "schema": "sovereign-linear-time/v1",
        "sealed": bool(linear.get("sealed")),
        "linear_ns": linear_time_ns(),
        "derived_utc": derived_utc(),
        "epoch_mono_ns": linear.get("epoch_mono_ns"),
        "epoch_linear_ns": linear.get("epoch_linear_ns"),
        "red_flag_count": int(linear.get("red_flag_count") or 0),
        "gap_count": int(linear.get("gap_count") or 0),
        "red_flag_active": bool(linear.get("red_flag_active")),
        "last_take_time_out": linear.get("last_take_time_out"),
        "immutable_rule": IMMUTABLE_RULE,
        "take_time_out_means": "gap or red_flag only",
        "clock_paused": False,
        "temperature_affects_linear": False,
        "ntp_affects_linear": False,
    }


def _read_thermal_millic() -> dict[str, int]:
    """Witness only — never feeds linear clock."""
    out: dict[str, int] = {}
    base = Path("/sys/class/thermal")
    if not base.is_dir():
        return out
    for zone in sorted(base.glob("thermal_zone*")):
        temp = zone / "temp"
        if temp.is_file():
            try:
                out[zone.name] = int(temp.read_text().strip())
            except (OSError, ValueError):
                pass
    return out


def _read_sysfs_freq_khz() -> dict[str, int]:
    out: dict[str, int] = {}
    base = Path("/sys/devices/system/cpu")
    if not base.is_dir():
        return out
    for cpu in sorted(base.glob("cpu[0-9]*")):
        for name in ("cpufreq/scaling_cur_freq", "cpufreq/cpuinfo_cur_freq"):
            p = cpu / name
            if p.is_file():
                try:
                    out[cpu.name] = int(p.read_text().strip())
                except (OSError, ValueError):
                    pass
                break
    return out


def _micron_witness(mono_ns: int, freqs: dict[str, int], thermal: dict[str, int]) -> str:
    payload = (
        f"{mono_ns}|"
        + "|".join(f"{k}:{v}" for k, v in sorted(freqs.items()))
        + "|"
        + "|".join(f"{k}:{v}" for k, v in sorted(thermal.items()))
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _witness_sample() -> dict[str, Any]:
    """Observation layer — thermal, freq, wall. Does NOT affect linear time."""
    mono = time.monotonic_ns()
    freqs = _read_sysfs_freq_khz()
    thermal = _read_thermal_millic()
    return {
        "mono_ns": mono,
        "linear_ns": linear_time_ns(),
        "realtime_ns": time.time_ns(),
        "utc": _now_iso(),
        "host": socket.gethostname(),
        "freq_khz": freqs,
        "freq_sum_khz": sum(freqs.values()) if freqs else 0,
        "thermal_millic": thermal,
        "thermal_sum_millic": sum(thermal.values()) if thermal else 0,
        "micron_witness": _micron_witness(mono, freqs, thermal),
        "witness_only": True,
        "affects_linear": False,
    }


def _detect_sonic_rf(prev: dict[str, Any], sample: dict[str, Any]) -> list[str]:
    threats: list[str] = []
    if not prev:
        return threats
    d_mono = int(sample.get("mono_ns") or 0) - int(prev.get("mono_ns") or 0)
    prev_w = str(prev.get("micron_witness") or "")
    cur_w = str(sample.get("micron_witness") or "")
    prev_sum = int(prev.get("freq_sum_khz") or 0)
    cur_sum = int(sample.get("freq_sum_khz") or 0)
    prev_temp = int(prev.get("thermal_sum_millic") or 0)
    cur_temp = int(sample.get("thermal_sum_millic") or 0)
    if prev_w and cur_w and prev_w != cur_w and 0 < d_mono < 100_000_000:
        threats.append("sonic_rf_witness_flip")
    if prev_sum and cur_sum and abs(cur_sum - prev_sum) > MAX_FREQ_DELTA_KHZ and d_mono < 50_000_000:
        threats.append("thermal_freq_witness_jump")
    if prev_temp and cur_temp and abs(cur_temp - prev_temp) > 5_000_000 and d_mono < 50_000_000:
        threats.append("thermal_witness_spike")
    skew = 0.0
    if d_mono > 0:
        d_linear = int(sample.get("linear_ns") or 0) - int(prev.get("linear_ns") or 0)
        if d_linear < 0:
            threats.append("linear_backward_forbidden")
        d_real = int(sample.get("realtime_ns") or 0) - int(prev.get("realtime_ns") or 0)
        skew = abs(d_real - d_mono) / 1_000_000.0
        if skew > MAX_SKEW_MS and d_mono < 20_000_000:
            threats.append(f"wall_witness_skew_{skew:.1f}ms")
    return threats


def cycle_advance(*, service: str, action: str) -> dict[str, Any]:
    state = _load_json(CYCLE_STATE, {"cycle": 0, "threats": 0, "services": {}})
    cycle = int(state.get("cycle") or 0) + 1
    sample = _witness_sample()
    gap_flag = _check_linear_gap(sample)
    prev_sample = {
        "mono_ns": state.get("last_mono_ns"),
        "linear_ns": state.get("last_linear_ns"),
        "realtime_ns": state.get("last_realtime_witness_ns"),
        "micron_witness": state.get("micron_witness"),
        "freq_sum_khz": state.get("freq_sum_khz"),
        "thermal_sum_millic": state.get("thermal_sum_millic"),
    }
    threats = _detect_sonic_rf(prev_sample, sample) if prev_sample.get("mono_ns") else []
    red_flag = None
    if threats:
        red_flag = take_time_out(
            kind="red_flag",
            reason=",".join(threats),
            evidence={
                "threats": threats,
                "service": service,
                "action": action,
                "thermal_sum_millic": sample.get("thermal_sum_millic"),
                "freq_sum_khz": sample.get("freq_sum_khz"),
            },
        )
    svc_stats = state.setdefault("services", {})
    svc_key = f"{service}:{action}"
    svc_stats[svc_key] = int(svc_stats.get(svc_key) or 0) + 1
    row = {
        "ts": derived_utc(),
        "cycle": cycle,
        "service": service,
        "action": action,
        "threats": threats,
        "linear_ns": linear_time_ns(),
        "micron_witness": sample.get("micron_witness"),
        "witness_affects_linear": False,
        "gap_flag": gap_flag,
        "red_flag": red_flag,
    }
    state.update({
        "schema": "sovereign-cycle/v1",
        "cycle": cycle,
        "never_lost": True,
        "last_mono_ns": sample["mono_ns"],
        "last_linear_ns": linear_time_ns(),
        "last_realtime_witness_ns": sample["realtime_ns"],
        "micron_witness": sample.get("micron_witness"),
        "freq_sum_khz": sample.get("freq_sum_khz"),
        "thermal_sum_millic": sample.get("thermal_sum_millic"),
        "updated": derived_utc(),
        "last_service": service,
        "last_action": action,
    })
    if threats:
        state["threats"] = int(state.get("threats") or 0) + 1
        state["last_threats"] = threats
    _save_json(CYCLE_STATE, state)
    _append_jsonl(CYCLE_LEDGER, row)
    return row


def cycle_gate(*, service: str, action: str = "serve") -> dict[str, Any]:
    row = cycle_advance(service=service, action=action)
    stale = False
    pulse_state = _load_json(PULSE_STATE, {})
    last = pulse_state.get("last") if isinstance(pulse_state.get("last"), dict) else None
    issued_at = float(pulse_state.get("issued_at") or 0)
    if not last or (time.time() - issued_at) > HEARTBEAT_SEC * 2:
        stale = True
    receipt = None
    verify: dict[str, Any] = {}
    if stale or not last:
        receipt = issue_pulse(chain=f"gate:{service}")
        prev = last
        verify = verify_receipt(receipt, prev_receipt=prev if isinstance(prev, dict) else None)
    else:
        verify = pulse_state.get("verify") if isinstance(pulse_state.get("verify"), dict) else {"verdict": "USER_OK"}
    threats = list(row.get("threats") or [])
    verdict = str(verify.get("verdict") or "USER_OK")
    if verdict == "SQUIDGIE":
        threats.append("squidgie_logged")
    return {
        "ok": True,
        "never_lose_cycle": True,
        "cycle": row["cycle"],
        "service": service,
        "action": action,
        "verdict": verdict,
        "threats": threats,
        "derived_utc": derived_utc(),
        "derived_ns": linear_time_ns(),
        "linear_ns": linear_time_ns(),
        "micron_witness": row.get("micron_witness"),
        "pulse": (receipt or last or {}).get("pulse"),
        "policy": "Linear time immutable — take time out means gap or red flag; clock never pauses",
        "temperature_affects_linear": False,
        "clock_paused": False,
    }


def cycle_status() -> dict[str, Any]:
    state = _load_json(CYCLE_STATE, {})
    anchor = _load_json(ANCHOR_STATE, {})
    return {
        "cycle": int(state.get("cycle") or 0),
        "never_lost": True,
        "threats": int(state.get("threats") or 0),
        "last_threats": state.get("last_threats") or [],
        "services": state.get("services") or {},
        "anchor_pulse": anchor.get("pulse"),
        "anchor_verdict": anchor.get("verdict"),
        "derived_utc": derived_utc(),
        "linear_ns": linear_time_ns(),
    }


def _signing_key() -> bytes:
    if KEY_FILE.is_file():
        return KEY_FILE.read_bytes()
    key = os.urandom(32)
    STATE.mkdir(parents=True, exist_ok=True)
    KEY_FILE.write_bytes(key)
    try:
        os.chmod(KEY_FILE, 0o600)
    except OSError:
        pass
    return key


def _receipt_body(sample: dict[str, Any], *, pulse: int, chain: str) -> dict[str, Any]:
    linear_ns = linear_time_ns()
    return {
        "schema": SCHEMA,
        "pulse": pulse,
        "chain": chain,
        "host": sample["host"],
        "mono_ns": sample["mono_ns"],
        "linear_ns": linear_ns,
        "realtime_ns": sample["realtime_ns"],
        "utc": derived_utc(),
        "freq_sum_khz": sample["freq_sum_khz"],
        "thermal_sum_millic": sample.get("thermal_sum_millic"),
        "micron_witness": sample["micron_witness"],
        "entropy_tag": hashlib.sha256(f"{linear_ns}:{pulse}".encode()).hexdigest()[:12],
        "witness_only_fields": ["realtime_ns", "utc", "freq_sum_khz", "thermal_sum_millic", "micron_witness"],
        "immutable_linear": True,
    }


def _sign(body: dict[str, Any]) -> str:
    key = _signing_key()
    msg = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def issue_pulse(*, chain: str = "operator") -> dict[str, Any]:
    prev_doc = _load_json(PULSE_STATE, {"pulse": 0})
    prev_pulse = int(prev_doc.get("pulse") or 0)
    pulse = prev_pulse + 1
    if pulse <= prev_pulse:
        pulse = prev_pulse + 1
    sample = _witness_sample()
    _check_linear_gap(sample)
    body = _receipt_body(sample, pulse=pulse, chain=chain)
    receipt = {**body, "sig": _sign(body)}
    prev_receipt = prev_doc.get("last") if isinstance(prev_doc.get("last"), dict) else None
    verify = verify_receipt(receipt, prev_receipt=prev_receipt)
    issues = list(verify.get("issues") or [])
    if issues:
        take_time_out(
            kind="red_flag",
            reason=",".join(issues),
            evidence={"pulse": pulse, "chain": chain, "issues": issues},
        )
    cycle_advance(service="sovereign", action="pulse")
    if verify.get("verdict") == "USER_OK" or not prev_receipt:
        _save_json(
            ANCHOR_STATE,
            {
                "schema": "sovereign-time-anchor/v1",
                "pulse": pulse,
                "mono_ns": receipt["mono_ns"],
                "linear_ns": receipt["linear_ns"],
                "realtime_witness_ns": receipt["realtime_ns"],
                "micron_witness": receipt.get("micron_witness"),
                "verdict": verify.get("verdict"),
                "updated": derived_utc(),
                "immutable_linear": True,
            },
        )
    PULSE_STATE.write_text(
        json.dumps({
            "pulse": pulse,
            "last": receipt,
            "verify": verify,
            "issued_at": time.time(),
        }, indent=2) + "\n",
        encoding="utf-8",
    )
    _append_jsonl(RECEIPT_LOG, {"ts": derived_utc(), "receipt": receipt, "verify": verify})
    return receipt


def verify_receipt(
    receipt: dict[str, Any],
    *,
    local: dict[str, Any] | None = None,
    prev_receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body = {k: v for k, v in receipt.items() if k != "sig"}
    sig = receipt.get("sig") or ""
    ok_sig = hmac.compare_digest(_sign(body), sig) if sig else False

    local = local or _witness_sample()
    issues: list[str] = []

    if not ok_sig:
        issues.append("bad_signature")

    if prev_receipt:
        d_mono = int(receipt.get("mono_ns") or 0) - int(prev_receipt.get("mono_ns") or 0)
        d_linear = int(receipt.get("linear_ns") or 0) - int(prev_receipt.get("linear_ns") or 0)
        if d_mono < 0:
            issues.append("monotonic_backward")
        if d_linear < 0:
            issues.append("linear_backward")
        if d_mono > 0 and d_linear < 0:
            issues.append("linear_rewind_forbidden")

        skew_ms = 0.0
        if d_mono > 0:
            d_real = int(receipt.get("realtime_ns") or 0) - int(prev_receipt.get("realtime_ns") or 0)
            skew_ms = abs(d_real - d_mono) / 1_000_000.0
            if skew_ms > MAX_SKEW_MS:
                issues.append(f"wall_witness_skew_{skew_ms:.2f}ms")

        prev_sum = int(prev_receipt.get("freq_sum_khz") or 0)
        cur_sum = int(receipt.get("freq_sum_khz") or 0)
        freq_jump = bool(prev_sum and cur_sum and abs(cur_sum - prev_sum) > MAX_FREQ_DELTA_KHZ)

        prev_w = prev_receipt.get("micron_witness") or ""
        cur_w = receipt.get("micron_witness") or ""
        witness_flip_fast = bool(prev_w and cur_w and prev_w != cur_w and d_mono < 50_000_000)

        if witness_flip_fast and (freq_jump or skew_ms > MAX_SKEW_MS / 2):
            issues.append("micron_squidgie")
        elif freq_jump and d_mono < 10_000_000 and skew_ms > MAX_SKEW_MS / 4:
            issues.append("freq_witness_squidgie")

    recv_linear = linear_time_ns()
    remote_linear = int(receipt.get("linear_ns") or 0)
    if remote_linear and recv_linear:
        linear_skew_ms = abs(recv_linear - remote_linear) / 1_000_000.0
        if linear_skew_ms > max(MAX_SKEW_MS * 4, 500):
            issues.append(f"receive_linear_skew_{linear_skew_ms:.1f}ms")

    verdict = "USER_OK" if not issues else "SQUIDGIE"
    return {
        "schema": SCHEMA,
        "verdict": verdict,
        "issues": issues,
        "sig_ok": ok_sig,
        "local_micron_witness": local.get("micron_witness"),
        "remote_micron_witness": receipt.get("micron_witness"),
        "checked_at": derived_utc(),
        "witness_affects_linear": False,
        "temperature_affects_linear": False,
    }


def sync_check(*, host: str = "127.0.0.1", port: int = DEFAULT_PORT, timeout: float = 2.0) -> dict[str, Any]:
    req = json.dumps({"op": "pulse", "client": socket.gethostname()}).encode()
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(timeout)
        sock.sendto(req, (host, port))
        data, _ = sock.recvfrom(65535)
    receipt = json.loads(data.decode())
    prev = _load_json(PULSE_STATE, {}).get("last")
    result = verify_receipt(receipt, prev_receipt=prev if isinstance(prev, dict) else None)
    PULSE_STATE.write_text(
        json.dumps({"pulse": receipt.get("pulse"), "last": receipt, "verify": result}, indent=2) + "\n",
        encoding="utf-8",
    )
    return {"receipt": receipt, "verify": result}


def _heartbeat_loop() -> None:
    while True:
        try:
            issue_pulse(chain="heartbeat")
        except Exception:
            cycle_advance(service="sovereign", action="heartbeat_fallback")
        time.sleep(HEARTBEAT_SEC)


def serve_udp(*, host: str = "127.0.0.1", port: int = DEFAULT_PORT) -> None:
    bind_host = os.environ.get("NEXUS_SOVEREIGN_TIME_BIND", host)
    threading.Thread(target=_heartbeat_loop, name="sovereign-heartbeat", daemon=True).start()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((bind_host, port))
    print(f"sovereign-time serve {bind_host}:{port} schema={SCHEMA} linear_immutable=1", flush=True)
    while True:
        data, addr = sock.recvfrom(65535)
        try:
            msg = json.loads(data.decode())
        except json.JSONDecodeError:
            continue
        if msg.get("op") != "pulse":
            continue
        cycle_gate(service="sovereign", action=f"udp:{addr[0]}")
        receipt = issue_pulse(chain=f"serve:{addr[0]}")
        sock.sendto(json.dumps(receipt).encode(), addr)


def melded_extension_slice() -> dict[str, Any]:
    """Ironclad meld slice — time is linear."""
    lin = linear_status()
    return {
        "id": "time",
        "absorbed": True,
        "declaration": "Time is linear.",
        "meld_citation": "ironclad:meld:2",
        "citation": "ironclad:time:1 — Time is linear — one axis, one direction, monotonic forever; no rewind, no branch, no pause on the sovereign clock.",
        "immutable_linear": True,
        "not_geometry_t": True,
        "linear_ns": lin.get("linear_ns"),
        "derived_utc": lin.get("derived_utc"),
        "sealed": lin.get("sealed"),
        "clock_paused": False,
        "witness_only": ["wall_clock", "ntp", "rtc", "thermal", "cpufreq"],
        "updated": derived_utc(),
    }


def status() -> dict[str, Any]:
    sample = _witness_sample()
    prev = _load_json(PULSE_STATE, {})
    last = prev.get("last") if isinstance(prev.get("last"), dict) else None
    verify = prev.get("verify") if isinstance(prev.get("verify"), dict) else None
    return {
        "schema": SCHEMA,
        "updated": derived_utc(),
        "port": DEFAULT_PORT,
        "heartbeat_sec": HEARTBEAT_SEC,
        "max_skew_ms": MAX_SKEW_MS,
        "max_freq_delta_khz": MAX_FREQ_DELTA_KHZ,
        "max_linear_gap_ms": MAX_LINEAR_GAP_MS,
        "never_lose_cycle": True,
        "immutable_linear": True,
        "temperature_affects_linear": False,
        "ntp_affects_linear": False,
        "take_time_out_means": "gap or red_flag only",
        "clock_paused": False,
        "derived_utc": derived_utc(),
        "linear_ns": linear_time_ns(),
        "linear": linear_status(),
        "red_flags": red_flags(limit=5),
        "local_witness": sample,
        "last_pulse": last,
        "last_verify": verify,
        "cycle": cycle_status(),
        "anchor": _load_json(ANCHOR_STATE, {}),
        "doctrine": str(INSTALL / "data" / "sovereign-time-doctrine.json"),
        "receipt_log": str(RECEIPT_LOG),
        "red_flag_ledger": str(RED_FLAG_LEDGER),
        "cycle_ledger": str(CYCLE_LEDGER),
        "declaration": "Time is linear.",
        "ironclad_citation": "ironclad:time:1",
        "posture": "Time is linear — sovereign clock immutable; take time out = gap or red flag; temperature changes nothing on the timer",
    }


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip().lower()
    if cmd in ("json", "status"):
        print(json.dumps(status(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("take-time-out", "take_time_out", "taketimeout"):
        kind = sys.argv[2] if len(sys.argv) > 2 else "red_flag"
        reason = sys.argv[3] if len(sys.argv) > 3 else "operator"
        if kind not in ("gap", "red_flag"):
            reason = kind
            kind = "red_flag"
        print(json.dumps(take_time_out(kind=kind, reason=reason), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("red-flags", "red_flags", "redflags"):
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        print(json.dumps(red_flags(limit=limit), ensure_ascii=False, indent=2))
        return 0
    if cmd == "linear":
        print(json.dumps(linear_status(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "gate" and len(sys.argv) > 2:
        svc = sys.argv[2]
        act = sys.argv[3] if len(sys.argv) > 3 else "serve"
        print(json.dumps(cycle_gate(service=svc, action=act), ensure_ascii=False, indent=2))
        return 0
    if cmd == "derived":
        print(json.dumps({
            "derived_utc": derived_utc(),
            "derived_ns": linear_time_ns(),
            "linear_ns": linear_time_ns(),
            "immutable_linear": True,
        }, ensure_ascii=False))
        return 0
    if cmd == "pulse":
        print(json.dumps(issue_pulse(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "serve":
        serve_udp()
        return 0
    if cmd == "sync":
        host = sys.argv[2] if len(sys.argv) > 2 else "127.0.0.1"
        port = int(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_PORT
        print(json.dumps(sync_check(host=host, port=port), ensure_ascii=False, indent=2))
        return 0
    if cmd == "verify" and len(sys.argv) > 2:
        receipt = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
        prev_path = sys.argv[3] if len(sys.argv) > 3 else ""
        prev = json.loads(Path(prev_path).read_text(encoding="utf-8")) if prev_path else None
        print(json.dumps(verify_receipt(receipt, prev_receipt=prev), ensure_ascii=False, indent=2))
        return 0
    print(
        json.dumps(
            {
                "error": "usage: sovereign-time.py [status|linear|derived|pulse|take-time-out|red-flags|serve|sync|gate SVC|verify]",
                "immutable_rule": IMMUTABLE_RULE,
            },
            ensure_ascii=False,
        )
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())