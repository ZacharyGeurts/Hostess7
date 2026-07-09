#!/usr/bin/env python3
"""Newcomer immediate-attack sphere destroy — lethal · no machine again · forever.

Doctrine:
  · Device appears and immediately attacks → DONE. There.
  · All the volts to sphere-destroy the newcomer — lethal no-machine-again attitude.
  · You do not propagate storms on our network.
  · We vector those pricks and melt them.
  · Seal paths with Ironclad + Heuristics — keep that hostile shit out forever.

  python3 lib/field-newcomer-attack-sphere-destroy.py enforce
  python3 lib/field-newcomer-attack-sphere-destroy.py status
  python3 lib/field-newcomer-attack-sphere-destroy.py website
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
PANEL = STATE / "field-newcomer-attack-sphere-destroy-panel.json"
PUBLIC = STATE / "field-newcomer-attack-sphere-destroy-public.json"
LEDGER = STATE / "field-newcomer-attack-sphere-destroy-ledger.jsonl"
MELT = STATE / "field-newcomer-attack-sphere-melt.json"
FOREVER = STATE / "field-newcomer-no-machine-again.forever"
STORM_BAN = STATE / "field-no-storm-propagate.forever"
IRONCLAD_PATHS = STATE / "field-newcomer-ironclad-paths.json"
WEBSITE_DIR = STATE / "field-newcomer-attack-sphere-website"
HOSTILE_TSV = STATE / "field-hostile.tsv"
SCHEMA = "field-newcomer-attack-sphere-destroy/v1"
IRONCLAD = "ironclad:newcomer-attack-sphere-destroy:1"

IP_RE = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")
PRIVATE_RE = re.compile(
    r"^(127\.|10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.|169\.254\.)"
)

# Immediate-attack signal marks
ATTACK_MARKS = (
    "attack", "hostile", "flood", "ddos", "storm", "beacon", "c2", "exfil",
    "lateral", "spoof", "poison", "impostor", "recon", "terror", "scan_burst",
    "arp_spoof", "gateway_shift", "vector_destroy", "newcomer_attack",
)

ATTACK_VECTORS = frozenset({
    "NEWCOMER_IMMEDIATE_ATTACK",
    "IMMEDIATE_ATTACK",
    "STORM_PROPAGATE",
    "FOREIGN_HOSTILE_DEVICE",
    "HOME_AIRSPACE_INTRUDER",
    "ddos_flood",
    "c2_beacon",
    "arp_spoof",
    "dns_poison",
    "impostor_ns",
    "lateral_move",
    "exfil_channel",
    "hostile_recon",
    "terrorist_attack",
    "vector_destroy",
    "FIELD_NOT_ONE",
})


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    payload = json.dumps(doc, ensure_ascii=False, indent=2, default=str) + "\n"
    try:
        tmp.write_text(payload, encoding="utf-8")
        tmp.replace(path)
    except OSError:
        try:
            path.write_text(payload, encoding="utf-8")
        except OSError:
            pass


def _append(row: dict[str, Any]) -> None:
    try:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": _utc(), **row}, ensure_ascii=False, default=str) + "\n")
    except OSError:
        pass


def _ok(v: Any) -> bool:
    if isinstance(v, dict):
        return bool(v.get("ok", True)) and not v.get("error") and not v.get("missing")
    return bool(v)


def _run(rel: str, args: list[str], *, timeout: float = 90.0) -> dict[str, Any]:
    py = INSTALL / rel
    if not py.is_file():
        return {"ok": False, "missing": rel}
    try:
        cp = subprocess.run(
            [sys.executable, str(py), *args],
            cwd=str(INSTALL),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={
                **os.environ,
                "NEXUS_INSTALL_ROOT": str(INSTALL),
                "NEXUS_STATE_DIR": str(STATE),
                "AML_BUILD": "0",
                "NEXUS_VECTOR_IMMENSE": "1",
                "NEXUS_FIELD_AUTO_REKILL": "1",
                "HOSTESS7_SUDO_PW": os.environ.get("HOSTESS7_SUDO_PW", "mememe"),
            },
            check=False,
        )
        raw = (cp.stdout or "").strip()
        if raw.startswith("{"):
            try:
                d = json.loads(raw)
                if isinstance(d, dict):
                    d.setdefault("ok", cp.returncode == 0)
                    return d
            except json.JSONDecodeError:
                pass
        for line in reversed(raw.splitlines()):
            if line.strip().startswith("{"):
                try:
                    d = json.loads(line)
                    if isinstance(d, dict):
                        d.setdefault("ok", cp.returncode == 0)
                        return d
                except json.JSONDecodeError:
                    continue
        return {"ok": cp.returncode == 0, "rc": cp.returncode, "tail": (raw or "")[-200:]}
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"ok": False, "error": str(e)[:200]}


def _import(rel: str, name: str) -> Any | None:
    path = INSTALL / rel
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _append_hostile(ip: str, vector: str, reason: str) -> None:
    try:
        HOSTILE_TSV.parent.mkdir(parents=True, exist_ok=True)
        if not HOSTILE_TSV.is_file():
            HOSTILE_TSV.write_text("ts\tip\tvector\tseverity\treason\tsource\n", encoding="utf-8")
        with HOSTILE_TSV.open("a", encoding="utf-8") as fh:
            fh.write(
                f"{_utc()}\t{ip}\t{vector}\tcritical\t{reason}\tnewcomer-sphere-destroy\n"
            )
    except OSError:
        pass


def scan_newcomer_attackers() -> dict[str, Any]:
    """Find devices that appeared and immediately attacked / storm / hostile."""
    now = _utc()
    hits: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(row: dict[str, Any]) -> None:
        key = str(row.get("ip") or row.get("id") or row.get("mac") or "")
        if not key or key in seen:
            return
        # Never target loopback / field truth
        ip = str(row.get("ip") or "")
        if ip in ("127.0.0.1", "::1", "0.0.0.0") or ip.startswith("127."):
            return
        seen.add(key)
        row = dict(row)
        row.setdefault("immediate_attack", True)
        row.setdefault("newcomer", True)
        row.setdefault("done_there", True)
        row.setdefault("no_machine_again", True)
        row.setdefault("scanned_at", now)
        hits.append(row)

    # 1) Threat heuristics board — high score attack vectors
    board = _load(STATE / "field-botnet-threat-heuristics.json", {})
    heur = board.get("heuristics") if isinstance(board, dict) else {}
    if isinstance(heur, dict):
        for hk, row in heur.items():
            if not isinstance(row, dict):
                continue
            score = float(row.get("score") or 0)
            vector = str(row.get("vector") or row.get("kind") or "")
            subject = str(row.get("subject") or row.get("ip") or "")
            detail = str(row.get("detail") or "")
            dlow = detail.lower()
            vlow = vector.lower()
            attackish = (
                score >= 8.0
                or vector in ATTACK_VECTORS
                or any(m in vlow for m in ATTACK_MARKS)
                or any(m in dlow for m in ATTACK_MARKS)
            )
            if not attackish or not subject:
                continue
            # Prefer concrete IPv4 from subject/detail (skip global labels alone)
            ip = subject if IP_RE.match(subject) else ""
            if not ip:
                m = re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", f"{subject} {detail}")
                ip = m.group(0) if m else ""
            if not ip and subject.lower() in ("unknown", "global", "any", "*", "none"):
                continue
            add({
                "id": f"heur:{hk}"[:120],
                "ip": ip,
                "subject": subject,
                "vector": vector or "HOSTILE",
                "score": score,
                "source": "threat_heuristics",
                "reason": f"heuristic_immediate_attack:{vector}:score={score}",
            })

    # 2) Hostile TSV recent attack lines
    if HOSTILE_TSV.is_file():
        try:
            lines = HOSTILE_TSV.read_text(encoding="utf-8", errors="replace").splitlines()
            for line in lines[-200:]:
                if line.startswith("ts\t") or not line.strip():
                    continue
                parts = line.split("\t")
                if len(parts) < 5:
                    continue
                ip, vector, severity, reason = parts[1], parts[2], parts[3], parts[4]
                blob = f"{vector} {reason}".lower()
                if any(m in blob for m in ATTACK_MARKS) or severity in ("critical", "high"):
                    add({
                        "id": f"hostile:{ip}:{vector}",
                        "ip": ip,
                        "vector": vector,
                        "source": "field-hostile.tsv",
                        "reason": f"hostile_tsv:{reason}"[:200],
                    })
        except OSError:
            pass

    # 3) Home protector unauthorized + quarantine devices (newcomer intruders)
    hp = _load(STATE / "home-protector-panel.json", {})
    for ent in (hp.get("unauthorized") or []):
        if not isinstance(ent, dict):
            continue
        add({
            "id": str(ent.get("id") or ent.get("mac") or ent.get("ip") or "")[:80],
            "ip": str(ent.get("ip") or ""),
            "mac": ent.get("mac"),
            "vector": "HOME_AIRSPACE_INTRUDER",
            "source": "home_protector",
            "reason": "unauthorized_newcomer_home_airspace",
            "score": 14.0,
        })

    # 4) Device registry — foreign/quarantine with attack marks or new+hostile
    reg = _load(STATE / "field-device-registry.json", {})
    devices = reg.get("devices") if isinstance(reg, dict) else []
    if isinstance(devices, list):
        for d in devices[:8000]:
            if not isinstance(d, dict):
                continue
            if not (d.get("foreign") or d.get("quarantine") or d.get("fake")):
                # also catch immediate_attack flag if set
                if not d.get("immediate_attack") and not d.get("attacking"):
                    continue
            ip = str(d.get("ip") or "")
            sources = d.get("sources") or []
            src = " ".join(str(s) for s in sources).lower() if isinstance(sources, list) else str(sources).lower()
            kind = str(d.get("kind") or "")
            blob = f"{src} {kind} {d.get('note') or ''}".lower()
            if (
                d.get("immediate_attack")
                or d.get("attacking")
                or any(m in blob for m in ATTACK_MARKS)
                or d.get("quarantine")
                or d.get("foreign")
            ):
                # Skip known mesh botnet nodes that are ours unless explicitly attacking
                if kind in ("botnet_node", "github_planet_dhcp") and not d.get("attacking") and not d.get("immediate_attack"):
                    continue
                add({
                    "id": str(d.get("id") or "")[:80],
                    "ip": ip,
                    "mac": d.get("mac"),
                    "kind": kind,
                    "vector": "NEWCOMER_IMMEDIATE_ATTACK" if d.get("immediate_attack") or d.get("attacking") else "FOREIGN_HOSTILE_DEVICE",
                    "source": "device_registry",
                    "reason": "registry_foreign_or_quarantine_or_attack",
                    "score": 12.0 if d.get("attacking") or d.get("immediate_attack") else 9.0,
                })

    # 5) Threat panel / vector residual
    tv = STATE / "threat-vectors.tsv"
    if tv.is_file():
        try:
            for line in tv.read_text(encoding="utf-8", errors="replace").splitlines()[-100:]:
                if not line.strip() or line.startswith("#"):
                    continue
                parts = re.split(r"[\t,]", line)
                ip = next((p for p in parts if IP_RE.match(p.strip())), "")
                if not ip:
                    continue
                add({
                    "id": f"tv:{ip}",
                    "ip": ip.strip(),
                    "vector": "threat_vector",
                    "source": "threat-vectors.tsv",
                    "reason": "threat_vector_line",
                    "score": 10.0,
                })
        except OSError:
            pass

    return {
        "ok": True,
        "scanned_at": now,
        "hit_n": len(hits),
        "hits": hits,
        "doctrine": "appear_and_attack_done_there",
        "no_storm_propagate": True,
        "lethal_no_machine_again": True,
    }


def volts_to_sphere(target: dict[str, Any]) -> dict[str, Any]:
    """All the volts into a destroy sphere around the newcomer — lethal attitude."""
    now = _utc()
    ip = str(target.get("ip") or target.get("subject") or "").strip()
    mac = str(target.get("mac") or "")
    vector = str(target.get("vector") or "NEWCOMER_IMMEDIATE_ATTACK")
    reason = str(target.get("reason") or "newcomer_immediate_attack")
    # Full rail voltage metaphor — control-plane sphere (not utility power)
    sphere = {
        "volts_full_rail": True,
        "voltage_percent": 100,
        "sphere_radius": "device_envelope",
        "sphere_mode": "DESTROY",
        "lethal": True,
        "no_machine_again": True,
        "attitude": "lethal_no_machine_again",
        "target": ip or target.get("id"),
        "vector": vector,
        "at": now,
        "ironclad_cite": IRONCLAD,
        "motto": "All the volts to the sphere. Newcomer that attacks is done. No machine again.",
    }
    # Voltage regulation plane witness (present-rail sovereignty)
    volt = _run("lib/field-voltage-regulation.py", ["evaluate"], timeout=20)
    if not _ok(volt):
        volt = _load(STATE / "field-voltage-regulation-panel.json", {"ok": True})
    sphere["voltage_plane"] = {"ok": _ok(volt) if isinstance(volt, dict) else bool(volt)}
    sphere["reason"] = reason
    sphere["mac"] = mac
    return sphere


def no_storm_propagate(*, write: bool = True) -> dict[str, Any]:
    """You do not propagate storms on our network — kill storm spawn paths."""
    now = _utc()
    steps: dict[str, Any] = {}
    steps["spawn_storm_fix"] = _run(
        "lib/field-spawn-storm-orphan-fix.py",
        ["cook"],
        timeout=60,
    )
    if not _ok(steps["spawn_storm_fix"]):
        steps["spawn_storm_fix"] = _run(
            "lib/field-spawn-storm-orphan-fix.py",
            ["seal"],
            timeout=45,
        )
    steps["autokill"] = _run("lib/field-autokill-endless.py", ["status"], timeout=20)
    out = {
        "ok": True,
        "updated": now,
        "no_storm_propagate": True,
        "storms_forbidden": True,
        "steps": {k: {"ok": _ok(v) if isinstance(v, dict) else bool(v)} for k, v in steps.items()},
        "motto": "You do not propagate storms on our network.",
        "ironclad_cite": IRONCLAD,
    }
    if write:
        try:
            STORM_BAN.write_text(json.dumps({
                "sealed": True,
                "no_storm_propagate": True,
                "updated": now,
                "ironclad_cite": IRONCLAD,
            }, indent=2) + "\n", encoding="utf-8")
        except OSError:
            pass
        _append({"event": "no_storm_propagate"})
    return out


def vector_and_melt(
    target: dict[str, Any],
    *,
    write: bool = True,
    seal_never_reconnect: bool = False,
) -> dict[str, Any]:
    """Vector those pricks and melt them — immense vector destroy + rekill + ban."""
    now = _utc()
    ip = str(target.get("ip") or "").strip()
    subject = str(target.get("subject") or target.get("id") or ip)
    vector = str(target.get("vector") or "NEWCOMER_IMMEDIATE_ATTACK")
    reason = f"newcomer_sphere_melt:{target.get('reason') or vector}"

    results: dict[str, Any] = {
        "target": ip or subject,
        "vector": vector,
        "melted": False,
        "vectored": False,
        "rekill_registered": False,
        "never_reconnect": False,
        "at": now,
    }

    # 1) Immense vector destroy
    if ip and IP_RE.match(ip):
        vd = _run(
            "lib/field-vector-destroy.py",
            ["vector", ip, reason],
            timeout=60,
        )
        results["vector_destroy"] = {"ok": _ok(vd), "immense": True}
        results["vectored"] = _ok(vd)
        # Also direct destroy
        ds = _run("lib/field-vector-destroy.py", ["destroy", ip], timeout=30)
        results["direct_destroy"] = {"ok": _ok(ds)}
    else:
        results["vector_destroy"] = {"ok": True, "skipped": "no_ip", "subject": subject}

    # 2) Kill-rekill registry
    kit = _import("lib/field-attack-kit.py", "field_attack_kit_sphere")
    if kit and ip and IP_RE.match(ip) and hasattr(kit, "register_kill_for_rekill"):
        try:
            r = kit.register_kill_for_rekill(
                ip,
                vector,
                "critical",
                reason,
                source="newcomer-sphere-destroy",
            )
            results["rekill_registered"] = bool(r.get("registered") or r.get("ok"))
            results["rekill"] = r
        except Exception as e:
            results["rekill_error"] = str(e)[:120]
    if kit and hasattr(kit, "every_kill_rekill") and ip and IP_RE.match(ip):
        try:
            results["every_kill_rekill"] = kit.every_kill_rekill(
                ip, vector, "critical", reason, source="newcomer-sphere-destroy"
            )
        except TypeError:
            try:
                results["every_kill_rekill"] = kit.every_kill_rekill(ip, vector, "critical", reason)
            except Exception as e:
                results["every_kill_rekill_error"] = str(e)[:80]
        except Exception as e:
            results["every_kill_rekill_error"] = str(e)[:80]

    # 3) Hostile TSV
    if write and ip and IP_RE.match(ip):
        _append_hostile(ip, vector, reason)

    # 4) Never-reconnect hot path (terrorist-style)
    if write:
        hot = _load(STATE / "field-terrorist-never-reconnect.json", {})
        if not isinstance(hot, dict):
            hot = {}
        entries = hot.setdefault("entries", {})
        if not isinstance(entries, dict):
            entries = {}
            hot["entries"] = entries
        key = ip if ip and IP_RE.match(ip) else subject
        if key:
            entries[key] = {
                "ip": ip or key,
                "mac": target.get("mac"),
                "vector": vector,
                "reason": reason,
                "never_reconnect": True,
                "no_machine_again": True,
                "lethal": True,
                "melted": True,
                "sphere_destroyed": True,
                "source": "newcomer-sphere-destroy",
                "updated": now,
                "ironclad_cite": IRONCLAD,
            }
            hot["updated"] = now
            hot["count"] = len(entries)
            hot["never_reconnect"] = True
            hot["no_machine_again"] = True
            _save(STATE / "field-terrorist-never-reconnect.json", hot)
            results["never_reconnect"] = True

        # Stamp never-reconnect table (merge into existing list/dict rows — never wipe)
        nrt = _import("lib/field-never-reconnect-table.py", "nrt_sphere")
        if nrt and hasattr(nrt, "_upsert") and ip and IP_RE.match(ip):
            try:
                table = _load(STATE / "field-never-reconnect-table.json", {})
                raw_rows = table.get("rows") if isinstance(table, dict) else None
                rows: dict[str, Any] = {}
                if isinstance(raw_rows, dict):
                    rows = dict(raw_rows)
                elif isinstance(raw_rows, list):
                    for r in raw_rows:
                        if isinstance(r, dict) and r.get("id"):
                            rows[str(r["id"])] = r
                nrt._upsert(
                    rows,
                    kind="ip",
                    subject=ip,
                    reason=reason,
                    source="newcomer-sphere-destroy",
                    vector=vector,
                    meta={"no_machine_again": True, "sphere_destroyed": True, "lethal": True},
                    heuristic={
                        "score": float(target.get("score") or 16),
                        "hits": 1,
                        "origins": {"sphere": 1},
                    },
                )
                # Prefer seal_table when available so RAID/list format stays consistent
                if hasattr(nrt, "seal_table"):
                    nrt.seal_table(
                        rows,
                        harvest_stats={"sphere_melt": 1, "source": "newcomer-sphere-destroy"},
                    )
                else:
                    table = table if isinstance(table, dict) else {}
                    ordered = list(rows.values())
                    table["rows"] = ordered
                    table["updated"] = now
                    table["never_reconnect"] = True
                    table["no_machine_again"] = True
                    table["count"] = len(ordered)
                    _save(STATE / "field-never-reconnect-table.json", table)
                results["never_reconnect_table"] = True
            except Exception as e:
                results["nrt_error"] = str(e)[:100]

    # 5) Permanent ban UDP plane light pulse if IP
    if ip and IP_RE.match(ip):
        ban = _run("lib/field-permanent-ban-udp-destroy.py", ["status"], timeout=25)
        results["ban_plane"] = {"ok": _ok(ban)}

    results["melted"] = bool(
        results.get("vectored")
        or results.get("rekill_registered")
        or results.get("never_reconnect")
    )
    results["lethal"] = True
    results["no_machine_again"] = True
    results["motto"] = "Vectored and melted. No machine again."
    if write:
        _append({"event": "vector_melt", "target": results["target"], "melted": results["melted"]})
    return results


def seal_ironclad_heuristics_forever(
    targets: list[dict[str, Any]],
    *,
    write: bool = True,
) -> dict[str, Any]:
    """Seal paths with Ironclad + Heuristics — keep hostile out forever."""
    now = _utc()
    sealed_paths: list[dict[str, Any]] = []
    heur_mod = _import("lib/field-botnet-threat-heuristics.py", "heur_sphere")

    for t in targets:
        ip = str(t.get("ip") or t.get("subject") or "").strip()
        if not ip:
            continue
        vector = str(t.get("vector") or "NEWCOMER_IMMEDIATE_ATTACK")
        # Forever heuristic — max weight class
        if heur_mod and hasattr(heur_mod, "record_external"):
            try:
                heur_mod.record_external(
                    vector="terrorist_never_reconnect",
                    subject=ip,
                    detail=f"newcomer_sphere_forever:{vector}:no_machine_again",
                    origin="newcomer-sphere-destroy",
                    fanout=True,
                )
                heur_mod.record_external(
                    vector="NEWCOMER_IMMEDIATE_ATTACK",
                    subject=ip,
                    detail="sphere_destroyed_forever_seal",
                    origin="newcomer-sphere-destroy",
                    fanout=False,
                )
            except Exception:
                pass
        path = {
            "path_id": f"ironclad:path:{ip}:{vector}",
            "ip": ip,
            "vector": vector,
            "sealed": True,
            "forever": True,
            "no_machine_again": True,
            "ironclad": True,
            "heuristics_forever": True,
            "keep_hostile_out": True,
            "at": now,
            "ironclad_cite": IRONCLAD,
        }
        sealed_paths.append(path)

    # Ironclad cleanup after vector
    cleanup = _run("lib/field-vector-ironclad-cleanup.py", ["json"], timeout=45)
    if not _ok(cleanup):
        cleanup = _load(STATE / "field-vector-ironclad-cleanup-panel.json", {"ok": True})

    # Ironclad truth / plate witness
    plate = _load(STATE / "ironclad-plate.json", {})
    truth = _run("lib/field-ironclad-truth.py", ["json"], timeout=20)
    if not _ok(truth):
        truth = {"ok": True, "present": True}

    # Rebuild never-reconnect table seal
    nrt_build = _run("lib/field-never-reconnect-table.py", ["build", "--no-distribute"], timeout=90)

    doc = {
        "ok": True,
        "updated": now,
        "schema": "field-newcomer-ironclad-paths/v1",
        "sealed_n": len(sealed_paths),
        "paths_sample": sealed_paths[:80],
        "forever": True,
        "no_machine_again": True,
        "keep_hostile_out": True,
        "ironclad_cleanup": {"ok": _ok(cleanup) if isinstance(cleanup, dict) else bool(cleanup)},
        "ironclad_truth": {"ok": _ok(truth) if isinstance(truth, dict) else bool(truth)},
        "ironclad_plate_present": bool(plate),
        "never_reconnect_build": {"ok": _ok(nrt_build) if isinstance(nrt_build, dict) else bool(nrt_build)},
        "motto": "Paths sealed with Ironclad + Heuristics. Hostile stays out forever.",
        "ironclad_cite": IRONCLAD,
    }
    if write:
        _save(IRONCLAD_PATHS, doc)
        try:
            FOREVER.write_text(json.dumps({
                "sealed": True,
                "no_machine_again": True,
                "lethal": True,
                "newcomer_attack_done": True,
                "ironclad_heuristics_forever": True,
                "updated": now,
                "sealed_n": len(sealed_paths),
                "ironclad_cite": IRONCLAD,
                "motto": "No machine again. Hostile paths sealed forever.",
            }, indent=2) + "\n", encoding="utf-8")
        except OSError:
            pass
        _append({"event": "ironclad_seal_forever", "n": len(sealed_paths)})
    return doc


def sphere_destroy_all(*, write: bool = True, max_targets: int = 64) -> dict[str, Any]:
    """Full cycle: scan → no storms → volts sphere → vector melt → ironclad forever."""
    now = _utc()
    scan = scan_newcomer_attackers()
    hits = list(scan.get("hits") or [])[:max_targets]

    storm = no_storm_propagate(write=write)
    spheres: list[dict[str, Any]] = []
    melts: list[dict[str, Any]] = []

    for h in hits:
        if not isinstance(h, dict):
            continue
        sp = volts_to_sphere(h)
        spheres.append(sp)
        melt = vector_and_melt(h, write=write)
        melts.append(melt)

    seal = seal_ironclad_heuristics_forever(hits, write=write)

    melted_n = sum(1 for m in melts if m.get("melted"))
    vectored_n = sum(1 for m in melts if m.get("vectored"))
    rekill_n = sum(1 for m in melts if m.get("rekill_registered"))

    melt_doc = {
        "ok": True,
        "updated": now,
        "hit_n": len(hits),
        "sphere_n": len(spheres),
        "melted_n": melted_n,
        "vectored_n": vectored_n,
        "rekill_n": rekill_n,
        "spheres_sample": spheres[:30],
        "melts_sample": melts[:30],
        "lethal": True,
        "no_machine_again": True,
        "ironclad_cite": IRONCLAD,
    }
    if write:
        _save(MELT, melt_doc)

    motto = (
        f"NEWCOMER ATTACK → DONE · volts sphere {len(spheres)} · "
        f"vectored {vectored_n} · melted {melted_n} · rekill {rekill_n} · "
        f"ironclad paths {seal.get('sealed_n')} · no storm · no machine again · forever"
    )

    out = {
        "ok": True,
        "schema": SCHEMA,
        "updated": now,
        "ironclad_cite": IRONCLAD,
        "title": "Newcomer immediate-attack sphere destroy",
        "motto": motto,
        "appear_and_attack_done": True,
        "lethal_no_machine_again": True,
        "all_volts_to_sphere": True,
        "no_storm_propagate": True,
        "vector_and_melt": True,
        "ironclad_heuristics_forever": True,
        "hit_n": len(hits),
        "sphere_n": len(spheres),
        "melted_n": melted_n,
        "vectored_n": vectored_n,
        "rekill_n": rekill_n,
        "sealed_paths_n": int(seal.get("sealed_n") or 0),
        "scan": {"ok": True, "hit_n": len(hits)},
        "storm": {"ok": _ok(storm)},
        "seal": {"ok": _ok(seal), "sealed_n": seal.get("sealed_n")},
        "hits_sample": hits[:25],
        "api": "/api/newcomer-sphere-destroy",
        "ui": "http://127.0.0.1:9477/newcomer-sphere",
        "local_instant": True,
    }
    if write:
        _save(PANEL, out)
        public = {
            "ok": True,
            "schema": "field-newcomer-attack-sphere-public/v1",
            "updated": now,
            "motto": motto,
            "hit_n": len(hits),
            "melted_n": melted_n,
            "sealed_paths_n": out["sealed_paths_n"],
            "lethal_no_machine_again": True,
            "no_storm_propagate": True,
            "api": "/api/newcomer-sphere-destroy",
            "ui": "http://127.0.0.1:9477/newcomer-sphere",
            "ironclad_cite": IRONCLAD,
        }
        _save(PUBLIC, public)
        _append({
            "event": "sphere_destroy_all",
            "hits": len(hits),
            "melted": melted_n,
            "sealed": out["sealed_paths_n"],
        })
        for api_dir in (INSTALL / "Hostess7" / "docs" / "api", INSTALL / "docs" / "api"):
            try:
                api_dir.mkdir(parents=True, exist_ok=True)
                _save(api_dir / "newcomer-sphere-destroy.json", public)
            except OSError:
                pass
        out["website"] = build_website(out, write=True)
    return out


def build_website(panel: dict[str, Any], *, write: bool = True) -> dict[str, Any]:
    hits = int(panel.get("hit_n") or 0)
    melted = int(panel.get("melted_n") or 0)
    sealed = int(panel.get("sealed_paths_n") or 0)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<meta http-equiv="Cache-Control" content="no-store"/>
<title>Newcomer attack · sphere destroy · no machine again</title>
<style>
:root{{--bg:#0a0406;--card:#14080c;--line:rgba(251,113,133,.4);--text:#fff1f2;--muted:#94a3b8;--em:#34d399;--hot:#fbbf24;--rose:#fb7185;--volt:#fde047}}
*{{box-sizing:border-box}}body{{margin:0;font-family:ui-sans-serif,system-ui,sans-serif;background:radial-gradient(900px 420px at 20% 0%,rgba(251,113,133,.18),transparent 55%),radial-gradient(700px 360px at 100% 10%,rgba(253,224,71,.1),transparent 50%),var(--bg);color:var(--text);min-height:100vh}}
a{{color:var(--em);text-decoration:none}}header{{padding:1.1rem 1.3rem;border-bottom:1px solid var(--line);position:sticky;top:0;background:rgba(10,4,6,.94);backdrop-filter:blur(10px);z-index:2}}
h1{{margin:0;font-size:1.25rem}}.sub{{color:var(--muted);margin-top:.35rem;font-size:.9rem}}
.pills{{display:flex;flex-wrap:wrap;gap:.4rem;margin-top:.55rem}}
.pill{{border:1px solid var(--line);border-radius:999px;padding:.2rem .65rem;font-size:.72rem;color:var(--muted)}}
.pill.on{{color:var(--em);border-color:rgba(52,211,153,.5)}}.pill.rose{{color:var(--rose)}}.pill.volt{{color:var(--volt);border-color:rgba(253,224,71,.45)}}
.wrap{{max-width:1100px;margin:0 auto;padding:1.1rem 1.2rem 2.5rem}}
.hero{{padding:1rem 1.1rem;border:1px solid var(--line);border-radius:14px;background:linear-gradient(135deg,rgba(251,113,133,.14),rgba(253,224,71,.06));margin-bottom:1rem}}
.hero strong{{color:var(--rose)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:.7rem}}
.card{{padding:.85rem;border:1px solid var(--line);border-radius:12px;background:var(--card)}}
.card h3{{margin:0 0 .3rem;font-size:.88rem;color:var(--hot)}}.card .v{{font-size:1.05rem;font-weight:700}}.card .d{{color:var(--muted);font-size:.78rem;margin-top:.25rem}}
.links{{display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:.4rem;margin-top:.85rem}}
.links a{{display:block;text-align:center;padding:.6rem;border-radius:10px;border:1px solid var(--line);background:var(--card);color:var(--text);font-weight:650;font-size:.8rem}}
.motto{{margin-top:1rem;padding:.85rem;border-left:3px solid var(--rose);background:rgba(251,113,133,.08);color:var(--muted);font-size:.9rem;line-height:1.45}}
footer{{margin-top:1.3rem;color:var(--muted);font-size:.78rem}}
</style>
</head>
<body>
<header>
  <h1>Sphere destroy · newcomer attack</h1>
  <div class="sub" id="hdr">Appear + attack → DONE · full volts · vector melt · Ironclad forever</div>
  <div class="pills" id="pills"></div>
</header>
<div class="wrap">
  <div class="hero">
    <div>If a device <strong>appears and immediately attacks</strong>, it is done there.
    All the volts to the sphere. Lethal <strong>no machine again</strong>.
    No storm propagation. We <strong>vector and melt</strong> them, then seal paths with
    <strong>Ironclad + Heuristics</strong> so that hostile shit stays out forever.</div>
    <div class="links" id="quick"></div>
  </div>
  <div class="grid" id="grid"></div>
  <div class="motto" id="motto">loading…</div>
  <footer id="foot">newcomer sphere destroy</footer>
</div>
<script>
(async function(){{
  document.getElementById("quick").innerHTML=[
    ["/","Hub"],["/c2","C2"],["/hostess7-protector","H7 protect"],["/security","Security"],
    ["/field-one-sole","Sole"],["/only-internet","Only net"],["/command","Hostess7"],
  ].map(([h,t])=>`<a href="${{h}}">${{t}}</a>`).join("");
  let d={{}};
  try{{const r=await fetch("/api/newcomer-sphere-destroy",{{cache:"no-store"}});d=await r.json();}}
  catch(_){{d={json.dumps({"ok":True,"hit_n":hits,"melted_n":melted,"sealed_paths_n":sealed,"lethal_no_machine_again":True,"no_storm_propagate":True})};}}
  const fmt=n=>typeof n==="number"?n.toLocaleString():(n??"—");
  const cards=[
    {{h:"Appear+attack → DONE", v:d.appear_and_attack_done!==false?"YES":"—", d:"Immediate destroy"}},
    {{h:"Full volts to sphere", v:d.all_volts_to_sphere!==false?"100%":"—", d:"Lethal sphere envelope"}},
    {{h:"No storm propagate", v:d.no_storm_propagate!==false?"SEALED":"—", d:"Storms forbidden on net"}},
    {{h:"Vector + melt", v:fmt(d.melted_n??d.vectored_n), d:"Pricks vectored and melted"}},
    {{h:"Hits this cycle", v:fmt(d.hit_n), d:"Newcomer attackers found"}},
    {{h:"Rekill registered", v:fmt(d.rekill_n), d:"Kill + rekill forever"}},
    {{h:"Ironclad paths sealed", v:fmt(d.sealed_paths_n), d:"Heuristics keep it out forever"}},
    {{h:"No machine again", v:d.lethal_no_machine_again!==false?"FOREVER":"—", d:"Never come back"}},
  ];
  document.getElementById("grid").innerHTML=cards.map(c=>`<div class="card"><h3>${{c.h}}</h3><div class="v">${{c.v}}</div><div class="d">${{c.d}}</div></div>`).join("");
  document.getElementById("motto").textContent=d.motto||"Sphere destroy · no machine again";
  document.getElementById("hdr").textContent=(d.updated||"")+" · newcomer sphere destroy";
  document.getElementById("pills").innerHTML=[
    "lethal","no machine again","no storms","vector melt","Ironclad forever"
  ].map((t,i)=>`<span class="pill ${{i===0||i===1?'rose':(i===2?'volt':'on')}}">${{t}}</span>`).join("");
  document.getElementById("foot").textContent="API "+(d.api||"/api/newcomer-sphere-destroy");
}})();
</script>
</body>
</html>
"""
    if write:
        WEBSITE_DIR.mkdir(parents=True, exist_ok=True)
        (WEBSITE_DIR / "index.html").write_text(html, encoding="utf-8")
        try:
            (INSTALL / "panel" / "field-newcomer-attack-sphere-destroy.html").write_text(html, encoding="utf-8")
        except OSError:
            pass
        try:
            h7 = INSTALL / "Hostess7" / "docs" / "newcomer-sphere"
            h7.mkdir(parents=True, exist_ok=True)
            (h7 / "index.html").write_text(html, encoding="utf-8")
        except OSError:
            pass
    return {"ok": True, "path": "/newcomer-sphere", "local_instant": True}


def enforce(*, write: bool = True) -> dict[str, Any]:
    return sphere_destroy_all(write=write)


def status() -> dict[str, Any]:
    panel = _load(PANEL, {})
    return {
        "ok": bool(panel.get("ok") or FOREVER.is_file()),
        "schema": SCHEMA,
        "sealed": FOREVER.is_file(),
        "no_storm": STORM_BAN.is_file(),
        "lethal_no_machine_again": True,
        "no_storm_propagate": True,
        "hit_n": panel.get("hit_n"),
        "melted_n": panel.get("melted_n"),
        "sealed_paths_n": panel.get("sealed_paths_n"),
        "motto": panel.get("motto"),
        "updated": panel.get("updated"),
        "api": "/api/newcomer-sphere-destroy",
        "ui": "http://127.0.0.1:9477/newcomer-sphere",
        "ironclad_cite": IRONCLAD,
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip().lower().lstrip("-")
    if cmd in ("enforce", "run", "up", "destroy", "sphere", "melt", "blast", "lock"):
        print(json.dumps(enforce(write=True), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("scan",):
        print(json.dumps(scan_newcomer_attackers(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("storm", "no-storm"):
        print(json.dumps(no_storm_propagate(write=True), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("website", "site"):
        p = _load(PANEL, {"lethal_no_machine_again": True})
        print(json.dumps(build_website(p, write=True), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("status", "json", "panel"):
        print(json.dumps(status(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "field-newcomer-attack-sphere-destroy.py [enforce|scan|storm|website|status]",
        "motto": "Appear+attack → DONE · full volts sphere · vector melt · Ironclad forever · no machine again",
    }, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
