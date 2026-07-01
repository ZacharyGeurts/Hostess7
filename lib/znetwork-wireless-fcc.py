#!/usr/bin/env pythong
"""ZNetwork wireless FCC — permitted bands only; outbound signals are threats.

Binds the operator's own router at relayer takeover. Foreign/outbound RF egress
is flagged hostile; the home router is never killed — we fix path, ARP, and trust.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
OWN_ROUTER = STATE / "znetwork-own-router.json"
FIX_LOG = STATE / "znetwork-own-router-fix.jsonl"
STRIKE_LOG = STATE / "znetwork-action-strike.jsonl"
INTENT = STATE / "connection-intent.json"
WIRELESS_STATE = STATE / "znetwork-wireless-fcc.json"
FCC_PERMITTED = INSTALL / "data" / "fcc-permitted-frequencies.json"
TRUSTED_TSV = STATE / "firewall-trusted.tsv"
SCHEMA = "znetwork-wireless-fcc/v1"

PRIVATE_RE = re.compile(
    r"^(127\.|10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.|169\.254\.|::1|fe80:|fd)"
)
_WLAN_RE = re.compile(r"^(wlan|wlp|wl)", re.I)

_MOD_CACHE: dict[str, Any] = {}


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _load(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        return default if default is not None else {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _append_log(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"ts": _now(), **row}, ensure_ascii=False) + "\n")


def _run(cmd: list[str], *, timeout: float = 10.0) -> dict[str, Any]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return {
            "ok": proc.returncode == 0,
            "stdout": (proc.stdout or "").strip(),
            "stderr": (proc.stderr or "").strip(),
        }
    except (subprocess.SubprocessError, OSError) as exc:
        return {"ok": False, "error": str(exc)}


def _norm_mac(mac: str) -> str:
    raw = re.sub(r"[^0-9a-fA-F]", "", mac or "")
    if len(raw) != 12:
        return ""
    return ":".join(raw[i : i + 2] for i in range(0, 12, 2)).lower()


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


def _default_route() -> dict[str, Any]:
    rep = _run(["ip", "-4", "route", "show", "default"])
    if not rep.get("ok") or not rep.get("stdout"):
        return {}
    parts = rep["stdout"].split()
    row: dict[str, Any] = {}
    if "via" in parts:
        row["gateway"] = parts[parts.index("via") + 1]
    if "dev" in parts:
        row["iface"] = parts[parts.index("dev") + 1]
    if "src" in parts:
        row["wan_ip"] = parts[parts.index("src") + 1]
    return row


def _neighbor(ip: str) -> dict[str, Any]:
    if not ip:
        return {}
    rep = _run(["ip", "-j", "neigh", "show", ip])
    if rep.get("ok") and rep.get("stdout"):
        try:
            rows = json.loads(rep["stdout"])
            if rows:
                ent = rows[0]
                return {
                    "ip": ip,
                    "mac": _norm_mac(str(ent.get("lladdr") or "")),
                    "iface": str(ent.get("dev") or ""),
                    "state": str(ent.get("state") or ""),
                }
        except json.JSONDecodeError:
            pass
    rep = _run(["ip", "neigh", "show", ip])
    text = rep.get("stdout") or ""
    if not text:
        return {"ip": ip}
    parts = text.split()
    mac = parts[4] if len(parts) > 5 and parts[3] == "lladdr" else ""
    return {"ip": ip, "mac": _norm_mac(mac), "iface": parts[2] if len(parts) > 2 else ""}


def _active_wifi() -> dict[str, Any] | None:
    rf = _mod(INSTALL / "lib" / "field-rf-sentinel.py", "rf_wifi_active")
    if rf and hasattr(rf, "_wifi_device_rows") and hasattr(rf, "_active_wifi_connection"):
        for row in rf._wifi_device_rows():
            dev = str(row.get("device") or "")
            if not dev:
                continue
            conn = rf._active_wifi_connection(dev)
            if conn and conn.get("ssid"):
                return conn
    rep = _run(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "dev", "status"])
    if not rep.get("ok"):
        return None
    wifi_dev = ""
    for line in (rep.get("stdout") or "").splitlines():
        parts = line.split(":")
        if len(parts) >= 3 and parts[1] == "wifi" and "connected" in parts[2].lower():
            wifi_dev = parts[0]
            break
    if not wifi_dev:
        return None
    show = _run(
        [
            "nmcli",
            "-t",
            "-f",
            "GENERAL.CONNECTION,802-11-wireless.ssid,802-11-wireless.bssid",
            "dev",
            "show",
            wifi_dev,
        ]
    )
    doc: dict[str, str] = {}
    for line in (show.get("stdout") or "").splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            doc[k] = v
    if not doc.get("802-11-wireless.ssid"):
        return None
    return {
        "device": wifi_dev,
        "ssid": doc.get("802-11-wireless.ssid", ""),
        "bssid": _norm_mac(doc.get("802-11-wireless.bssid", "")),
    }


def _is_wireless_iface(iface: str) -> bool:
    if not iface:
        return False
    if _WLAN_RE.match(iface):
        return True
    return Path(f"/sys/class/net/{iface}/wireless").is_dir()


def bind_own_router(*, force: bool = False) -> dict[str, Any]:
    """Capture operator home router — gateway, MAC, wireless BSSID when applicable."""
    existing = _load(OWN_ROUTER)
    if existing.get("bound") and not force:
        return {"ok": True, "schema": SCHEMA, "skipped": True, "router": existing}

    route = _default_route()
    gw = str(route.get("gateway") or "").strip()
    iface = str(route.get("iface") or "").strip()
    neigh = _neighbor(gw) if gw else {}
    wifi = _active_wifi() if _is_wireless_iface(iface) else None

    doc = {
        "schema": "znetwork-own-router/v1",
        "bound": bool(gw),
        "gateway_ip": gw,
        "gateway_mac": neigh.get("mac") or "",
        "iface": iface,
        "wan_ip": route.get("wan_ip") or "",
        "wireless": bool(wifi),
        "ssid": (wifi or {}).get("ssid") or "",
        "bssid": (wifi or {}).get("bssid") or "",
        "wifi_device": (wifi or {}).get("device") or "",
        "neighbor_state": neigh.get("state") or "",
        "policy": "fix_not_kill",
        "bound_at": _now(),
        "motto": "Operator router is sacred — remediate, never shoot-to-kill.",
    }
    if gw:
        _save(OWN_ROUTER, doc)
        _trust_gateway(gw)
    return {"ok": bool(gw), "schema": SCHEMA, "router": doc, "bound_at": doc["bound_at"]}


def load_own_router() -> dict[str, Any]:
    return _load(OWN_ROUTER, {})


def is_own_router(
    *,
    ip: str = "",
    mac: str = "",
    bssid: str = "",
    ssid: str = "",
) -> bool:
    """True when target matches bound operator router."""
    doc = load_own_router()
    if not doc.get("bound"):
        return False
    gw = str(doc.get("gateway_ip") or "")
    if ip and gw and ip == gw:
        return True
    gmac = _norm_mac(str(doc.get("gateway_mac") or ""))
    if mac and gmac and _norm_mac(mac) == gmac:
        return True
    bnorm = _norm_mac(str(doc.get("bssid") or ""))
    if bssid and bnorm and _norm_mac(bssid) == bnorm:
        return True
    bound_ssid = str(doc.get("ssid") or "")
    if ssid and bound_ssid and ssid == bound_ssid:
        return True
    return False


def _trust_gateway(ip: str) -> bool:
    if not ip:
        return False
    try:
        STATE.mkdir(parents=True, exist_ok=True)
        if not TRUSTED_TSV.is_file():
            TRUSTED_TSV.write_text("ts\tlabel\tip\treason\tsource\n", encoding="utf-8")
        text = TRUSTED_TSV.read_text(encoding="utf-8", errors="replace")
        if f"\t{ip}\t" in text:
            return True
        with TRUSTED_TSV.open("a", encoding="utf-8") as fh:
            fh.write(f"{_now()}\town_router\t{ip}\tZNetwork own router\tznetwork-wireless-fcc\n")
        return True
    except OSError:
        return False


def fix_own_router(*, issue: str = "", detail: str = "") -> dict[str, Any]:
    """Remediate home router path — never firewall/autokill the gateway."""
    doc = load_own_router()
    if not doc.get("bound"):
        bind = bind_own_router(force=True)
        doc = bind.get("router") or {}
    gw = str(doc.get("gateway_ip") or "")
    iface = str(doc.get("iface") or "")
    wifi_dev = str(doc.get("wifi_device") or "")
    actions: list[dict[str, Any]] = []

    if gw:
        ping = _run(["ping", "-c", "2", "-W", "2", gw])
        actions.append({"action": "ping_gateway", "ok": ping.get("ok"), "ip": gw})
        flush = _run(["ip", "neigh", "flush", gw])
        actions.append({"action": "flush_neighbor", "ok": flush.get("ok"), "ip": gw})
        ping2 = _run(["ping", "-c", "1", "-W", "2", gw])
        neigh = _neighbor(gw)
        actions.append({"action": "refresh_arp", "ok": ping2.get("ok"), "neighbor": neigh})
        if neigh.get("mac"):
            doc["gateway_mac"] = neigh["mac"]
        _trust_gateway(gw)

    if wifi_dev and doc.get("ssid"):
        conn = _run(["nmcli", "-t", "-f", "GENERAL.CONNECTION", "dev", "show", wifi_dev])
        conn_name = ""
        for line in (conn.get("stdout") or "").splitlines():
            if line.startswith("GENERAL.CONNECTION:"):
                conn_name = line.split(":", 1)[1]
        if conn_name and conn_name != "--":
            up = _run(["nmcli", "connection", "up", conn_name, "ifname", wifi_dev], timeout=20)
            actions.append({"action": "reconnect_wifi", "ok": up.get("ok"), "connection": conn_name})
        else:
            rescan = _run(["nmcli", "dev", "wifi", "rescan", "ifname", wifi_dev])
            actions.append({"action": "wifi_rescan", "ok": rescan.get("ok"), "device": wifi_dev})

    doc["last_fix"] = _now()
    doc["last_fix_issue"] = issue[:120]
    doc["last_fix_detail"] = detail[:240]
    _save(OWN_ROUTER, doc)

    rep = {
        "schema": SCHEMA,
        "ok": True,
        "policy": "fix_not_kill",
        "issue": issue,
        "detail": detail,
        "actions": actions,
        "router": doc,
        "at": _now(),
    }
    _append_log(FIX_LOG, {"event": "fix_own_router", **rep})
    return rep


def _permitted_frequency(freq_mhz: float | int | None, channel: int | None) -> tuple[bool, str]:
    rf = _mod(INSTALL / "lib" / "field-rf-sentinel.py", "rf_permitted")
    if rf and hasattr(rf, "_is_permitted_frequency"):
        return rf._is_permitted_frequency(freq_mhz, channel)
    return True, "rf_sentinel_unavailable"


def _trusted_proc(proc: str) -> bool:
    base = (proc or "").split("/")[-1].lower()
    trusted = (
        "firefox", "chrome", "chromium", "brave", "vivaldi", "waterfox",
        "nexus", "znetwork", "nmcli", "NetworkManager", "wpa_supplicant",
        "systemd", "sshd", "cupsd", "dnsmasq",
    )
    return any(t in base for t in trusted)


def _ss_flows(*, iface: str = "") -> list[dict[str, Any]]:
    flows: list[dict[str, Any]] = []
    try:
        proc = subprocess.run(["ss", "-H", "-tunap"], capture_output=True, text=True, timeout=8)
        lines = proc.stdout.splitlines() if proc.returncode == 0 else []
    except (subprocess.SubprocessError, OSError):
        return flows
    for line in lines:
        if iface and iface not in line:
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        state = parts[0]
        local = parts[3]
        remote = parts[4]
        rip = remote.rsplit(":", 1)[0] if ":" in remote else remote
        rport = int(remote.rsplit(":", 1)[1]) if ":" in remote and remote.rsplit(":", 1)[1].isdigit() else 0
        lip = local.rsplit(":", 1)[0] if ":" in local else local
        lport = int(local.rsplit(":", 1)[1]) if ":" in local and local.rsplit(":", 1)[1].isdigit() else 0
        proc_m = re.search(r'users:\(\("([^"]+)",pid=(\d+)', line)
        proc_name = proc_m.group(1) if proc_m else ""
        pid = int(proc_m.group(2)) if proc_m else 0
        flows.append(
            {
                "state": state,
                "local_ip": lip,
                "local_port": lport,
                "remote_ip": rip,
                "remote_port": rport,
                "process": proc_name,
                "pid": pid,
                "iface_hint": iface,
                "raw": line[:240],
            }
        )
    return flows


def _gatekeeper_rows() -> list[dict[str, Any]]:
    doc = _load(INTENT, {})
    rows = doc.get("connections") or []
    return [r for r in rows if isinstance(r, dict)]


def _pick_worst_gatekeeper(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None
    best_score = -1
    for row in rows:
        verdict = str(row.get("verdict") or "")
        iff = str(row.get("iff") or "")
        score = 0
        if verdict == "HARM_CANDIDATE":
            score += 8
        if iff == "HOSTILE":
            score += 6
        if row.get("block_recommended"):
            score += 4
        if row.get("kill_eligible"):
            score += 3
        if score > best_score:
            best_score = score
            best = row
    return best


def trace_action_behind(threat: dict[str, Any]) -> dict[str, Any]:
    """Find the process or remote peer responsible for a wireless/FCC symptom."""
    kind = str(threat.get("kind") or threat.get("symptom_kind") or "unknown")
    symptom_ip = str(
        threat.get("ip")
        or threat.get("remote_ip")
        or threat.get("symptom_ip")
        or ""
    ).strip()
    symptom_proc = str(threat.get("process") or "")
    route = _default_route()
    iface = str(threat.get("iface") or route.get("iface") or "")
    flows = _ss_flows(iface=iface)
    gk_rows = _gatekeeper_rows()

    attributed: dict[str, Any] = {
        "schema": "znetwork-action-trace/v1",
        "symptom_kind": kind,
        "symptom_ip": symptom_ip,
        "symptom_process": symptom_proc,
        "iface": iface,
        "traced_at": _now(),
    }

    # Symptom is our router — find the local actor abusing the path.
    if symptom_ip and is_own_router(ip=symptom_ip):
        attributed["symptom_is_own_router"] = True
        suspects = [
            f for f in flows
            if f.get("remote_ip")
            and not is_own_router(ip=str(f.get("remote_ip") or ""))
            and not _trusted_proc(str(f.get("process") or ""))
        ]
        gk_bad = [
            r for r in gk_rows
            if str(r.get("remote_ip") or "") and not is_own_router(ip=str(r.get("remote_ip") or ""))
            and (
                r.get("verdict") in ("HARM_CANDIDATE", "BLOCK_RECOMMENDED")
                or r.get("iff") == "HOSTILE"
                or r.get("block_recommended")
            )
        ]
        if gk_bad:
            pick = _pick_worst_gatekeeper(gk_bad) or gk_bad[0]
            attributed.update({
                "action_ip": str(pick.get("remote_ip") or ""),
                "action_process": str(pick.get("process") or ""),
                "action_pid": int(pick.get("pid") or 0),
                "action_source": "gatekeeper_behind_router",
                "strike_eligible": True,
                "policy": "fix_router_strike_actor",
            })
            return attributed
        if suspects:
            pick = suspects[0]
            attributed.update({
                "action_ip": str(pick.get("remote_ip") or ""),
                "action_process": str(pick.get("process") or ""),
                "action_pid": int(pick.get("pid") or 0),
                "action_source": "ss_flow_behind_router",
                "strike_eligible": True,
                "policy": "fix_router_strike_actor",
            })
            return attributed
        attributed.update({
            "action_source": "router_symptom_no_actor",
            "strike_eligible": False,
            "policy": "fix_router_only",
        })
        return attributed

    # Outbound wireless signal — strike the process and remote peer directly.
    if kind == "outbound_wireless_signal" or symptom_proc:
        for flow in flows:
            if symptom_ip and str(flow.get("remote_ip") or "") != symptom_ip:
                continue
            if symptom_proc and symptom_proc not in str(flow.get("process") or ""):
                continue
            attributed.update({
                "action_ip": str(flow.get("remote_ip") or symptom_ip),
                "action_process": str(flow.get("process") or symptom_proc),
                "action_pid": int(flow.get("pid") or 0),
                "action_source": "outbound_signal_flow",
                "strike_eligible": bool(flow.get("remote_ip") or flow.get("pid")),
                "policy": "strike_actor_not_router",
            })
            return attributed

    # RF threat with correlated IP — match gatekeeper / ss to process.
    if symptom_ip:
        for row in gk_rows:
            if str(row.get("remote_ip") or "") == symptom_ip:
                attributed.update({
                    "action_ip": symptom_ip,
                    "action_process": str(row.get("process") or ""),
                    "action_pid": int(row.get("pid") or 0),
                    "action_source": "gatekeeper_ip_match",
                    "strike_eligible": True,
                    "policy": "strike_actor_not_router",
                })
                return attributed
        for flow in flows:
            if str(flow.get("remote_ip") or "") == symptom_ip:
                attributed.update({
                    "action_ip": symptom_ip,
                    "action_process": str(flow.get("process") or ""),
                    "action_pid": int(flow.get("pid") or 0),
                    "action_source": "ss_ip_match",
                    "strike_eligible": True,
                    "policy": "strike_actor_not_router",
                })
                return attributed

    # BSSID-only RF pollution — strike any hostile egress on wlan, not the AP hardware.
    bssid = str(threat.get("bssid") or "")
    if bssid and not is_own_router(bssid=bssid):
        bad_flows = [
            f for f in flows
            if f.get("remote_ip")
            and not is_own_router(ip=str(f.get("remote_ip") or ""))
            and not _trusted_proc(str(f.get("process") or ""))
        ]
        if bad_flows:
            pick = bad_flows[0]
            attributed.update({
                "action_ip": str(pick.get("remote_ip") or ""),
                "action_process": str(pick.get("process") or ""),
                "action_pid": int(pick.get("pid") or 0),
                "action_source": "rf_pollution_correlated_egress",
                "strike_eligible": True,
                "policy": "strike_actor_not_ap",
                "symptom_bssid": bssid,
            })
            return attributed

    attributed.update({
        "action_source": "unattributed",
        "strike_eligible": bool(symptom_ip and not is_own_router(ip=symptom_ip)),
        "action_ip": symptom_ip if symptom_ip and not is_own_router(ip=symptom_ip) else "",
        "policy": "strike_if_foreign_ip",
    })
    return attributed


def _graceful_stop_pid(pid: int, *, reason: str = "") -> dict[str, Any]:
    if pid <= 1:
        return {"ok": False, "pid": pid, "skipped": True}
    try:
        os.kill(pid, signal.SIGTERM)
        return {"ok": True, "pid": pid, "signal": "SIGTERM", "reason": reason}
    except ProcessLookupError:
        return {"ok": True, "pid": pid, "already_gone": True}
    except OSError as exc:
        return {"ok": False, "pid": pid, "error": str(exc)}


def strike_action_behind(
    threat: dict[str, Any],
    *,
    trace: dict[str, Any] | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Fix own-router symptoms; shoot-to-kill the traced action behind the problem."""
    traced = trace or trace_action_behind(threat)
    rep: dict[str, Any] = {
        "schema": SCHEMA,
        "ok": False,
        "trace": traced,
        "strikes": [],
        "at": _now(),
    }

    if traced.get("symptom_is_own_router") or is_own_router(
        ip=str(traced.get("symptom_ip") or threat.get("ip") or ""),
        bssid=str(threat.get("bssid") or ""),
    ):
        rep["router_fix"] = fix_own_router(
            issue="symptom_on_own_router",
            detail=f"Traced {traced.get('action_source')} — router fixed, actor struck",
        )

    if not traced.get("strike_eligible"):
        rep["ok"] = bool(rep.get("router_fix"))
        rep["policy"] = traced.get("policy") or "no_strike"
        _append_log(STRIKE_LOG, {"event": "strike_skip", **rep})
        return rep

    action_ip = str(traced.get("action_ip") or "").strip()
    action_pid = int(traced.get("action_pid") or 0)
    action_proc = str(traced.get("action_process") or "")

    if action_pid and not _trusted_proc(action_proc):
        stop = _graceful_stop_pid(action_pid, reason=f"action_behind:{traced.get('action_source')}")
        rep["strikes"].append({"kind": "process_sigterm", **stop})
        if stop.get("ok"):
            rep["ok"] = True

    if action_ip and not is_own_router(ip=action_ip) and not PRIVATE_RE.match(action_ip):
        relayer = _mod(INSTALL / "lib" / "znetwork-relayer.py", "relayer_strike")
        target = {
            "ip": action_ip,
            "remote_ip": action_ip,
            "process": action_proc,
            "pid": action_pid,
            "verdict": "HARM_CANDIDATE",
            "iff": "HOSTILE",
            "immediate": True,
            "reason": f"action_behind:{traced.get('symptom_kind')}:{traced.get('action_source')}",
            "vector": "OUTBOUND_WIRELESS_SIGNAL",
            "kill_tier": "strike",
        }
        if relayer and hasattr(relayer, "retaliate"):
            strike = relayer.retaliate(target, force=force)
            rep["strikes"].append({"kind": "relayer_retaliate", **strike})
            if strike.get("ok") or strike.get("actions"):
                rep["ok"] = True
        else:
            hostile = _mod(INSTALL / "lib" / "znetwork-hostile-threat.py", "hostile_strike")
            if hostile and hasattr(hostile, "_strike_target"):
                strike = hostile._strike_target(target)
                rep["strikes"].append({"kind": "hostile_strike", **strike})
                if strike.get("ok") or strike.get("actions"):
                    rep["ok"] = True

    rep["policy"] = traced.get("policy") or "strike_action_behind"
    _append_log(STRIKE_LOG, {"event": "strike_action_behind", **rep})
    return rep


def detect_outbound_signal_threats() -> list[dict[str, Any]]:
    """Outbound traffic on wireless iface to non-own-router peers = RF egress threat."""
    route = _default_route()
    iface = str(route.get("iface") or "")
    if not _is_wireless_iface(iface):
        return []

    threats: list[dict[str, Any]] = []
    ts = _now()
    try:
        proc = subprocess.run(["ss", "-H", "-tunap"], capture_output=True, text=True, timeout=8)
        lines = proc.stdout.splitlines() if proc.returncode == 0 else []
    except (subprocess.SubprocessError, OSError):
        lines = []

    for line in lines:
        if iface not in line:
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        local = parts[3] if len(parts) > 3 else ""
        remote = parts[4] if len(parts) > 4 else ""
        rip = remote.rsplit(":", 1)[0] if ":" in remote else remote
        if not rip or PRIVATE_RE.match(rip):
            continue
        if is_own_router(ip=rip):
            continue
        proc_m = re.search(r'users:\(\("([^"]+)"', line)
        proc = proc_m.group(1) if proc_m else ""
        if _trusted_proc(proc):
            continue
        threats.append({
            "ts": ts,
            "kind": "outbound_wireless_signal",
            "severity": "high",
            "iface": iface,
            "remote_ip": rip,
            "process": proc,
            "detail": f"Outbound signal on {iface} → {rip} via {proc or 'unknown'}",
            "fcc_permitted_iface": True,
            "fix_router_instead": is_own_router(ip=str(route.get("gateway") or "")),
        })
    return threats


def scan_wireless_fcc(*, bind: bool = True) -> dict[str, Any]:
    """FCC-only wireless scan with own-router fix queue instead of kill."""
    if bind:
        bind_own_router()

    rf = _mod(INSTALL / "lib" / "field-rf-sentinel.py", "rf_scan")
    rf_doc: dict[str, Any] = {}
    if rf and hasattr(rf, "cycle"):
        try:
            rf_doc = rf.cycle()
        except Exception as exc:
            rf_doc = {"ok": False, "error": str(exc)}

    outbound = detect_outbound_signal_threats()
    own = load_own_router()
    fix_queue: list[dict[str, Any]] = []
    kill_queue: list[dict[str, Any]] = []

    for threat in (rf_doc.get("threats") or []):
        if not isinstance(threat, dict):
            continue
        bssid = str(threat.get("bssid") or "")
        ssid = str(threat.get("ssid") or "")
        ip = str(threat.get("ip") or "")
        if is_own_router(ip=ip, bssid=bssid, ssid=ssid):
            fix_queue.append({**threat, "remediation": "own_router_fix_not_kill"})
            continue
        if threat.get("kind") == "global_wireless_field":
            continue
        kill_queue.append(threat)

    for ob in outbound:
        rip = str(ob.get("remote_ip") or "")
        if is_own_router(ip=rip):
            fix_queue.append({**ob, "remediation": "own_router_path_fix"})
        else:
            kill_queue.append(ob)

    fixes_applied: list[dict[str, Any]] = []
    strikes_applied: list[dict[str, Any]] = []
    if fix_queue:
        fixes_applied.append(
            fix_own_router(
                issue="own_router_threat_confusion",
                detail=f"{len(fix_queue)} threat(s) matched home router — remediated not killed",
            )
        )

    for threat in kill_queue:
        traced = trace_action_behind(threat)
        strike = strike_action_behind(threat, trace=traced)
        strikes_applied.append({"threat": threat.get("kind"), "trace": traced, "strike": strike})

    rep = {
        "schema": SCHEMA,
        "ok": True,
        "fcc_permitted_only": True,
        "own_router": own,
        "outbound_threats": len(outbound),
        "fix_queue": fix_queue,
        "kill_queue": kill_queue,
        "fixes_applied": fixes_applied,
        "strikes_applied": strikes_applied,
        "action_strike_count": sum(1 for s in strikes_applied if (s.get("strike") or {}).get("ok")),
        "rf_sentinel": {
            "ok": rf_doc.get("ok", True),
            "threat_count": len(rf_doc.get("threats") or []),
            "permitted_bands": bool(rf_doc.get("permitted_bands") or rf_doc.get("frequency_registry")),
        },
        "at": _now(),
        "motto": "FCC wireless only — find action behind symptom; fix router, strike actor.",
    }
    _save(WIRELESS_STATE, rep)
    return rep


def posture() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "ok": True,
        "own_router": load_own_router(),
        "wireless_state": _load(WIRELESS_STATE),
        "fcc_policy": str(FCC_PERMITTED),
        "at": _now(),
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    handlers = {
        "json": posture,
        "bind": bind_own_router,
        "own": load_own_router,
        "is-own": lambda: {
            "ok": True,
            "own": is_own_router(
                ip=sys.argv[2] if len(sys.argv) > 2 else "",
                mac=sys.argv[3] if len(sys.argv) > 3 else "",
                bssid=sys.argv[4] if len(sys.argv) > 4 else "",
            ),
        },
        "fix": lambda: fix_own_router(issue=sys.argv[2] if len(sys.argv) > 2 else "manual"),
        "outbound": lambda: {"ok": True, "threats": detect_outbound_signal_threats()},
        "trace": lambda: trace_action_behind(
            json.loads(sys.argv[2]) if len(sys.argv) > 2 else {"kind": "manual"}
        ),
        "strike": lambda: strike_action_behind(
            json.loads(sys.argv[2]) if len(sys.argv) > 2 else {"kind": "manual"},
            force="--force" in sys.argv,
        ),
        "scan": scan_wireless_fcc,
    }
    fn = handlers.get(cmd)
    if not fn:
        print(
            json.dumps(
                {
                    "error": (
                        "usage: znetwork-wireless-fcc.py "
                        "[json|bind|own|is-own IP [MAC] [BSSID]|fix [issue]|outbound|trace JSON|strike JSON|scan]"
                    )
                }
            ),
            file=sys.stderr,
        )
        return 2
    force = "--force" in sys.argv[2:]
    if cmd == "bind":
        result = bind_own_router(force=force)
    else:
        result = fn()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())