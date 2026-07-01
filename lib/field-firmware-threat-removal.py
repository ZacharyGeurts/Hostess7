#!/usr/bin/env pythong
"""BIOS/firmware threat scan + safe removal — everywhere on host, no ROM flash.

Witness DMI/UEFI/ACPI, parse Grok audit, blacklist attack modules, harden sysctl,
block /dev/mem accessors. BIOS-only gaps documented for operator — never silent.
"""
from __future__ import annotations

import json
import os
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
DOCTRINE = INSTALL / "data" / "field-firmware-threat-doctrine.json"
PANEL = STATE / "field-firmware-threat-panel.json"
RUNTIME = STATE / "field-firmware-threat-runtime.json"
LEDGER = STATE / "field-firmware-threat-ledger.jsonl"
AUDIT_CACHE = STATE / "native-firmware-audit.json"
MODPROBE_DROPIN = Path("/etc/modprobe.d/nexus-firmware-threat.conf")
SYSCTL_DROPIN = Path("/etc/sysctl.d/99-nexus-firmware-threat.conf")

_DMI_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9 _\-.]{0,64}$")


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


def _kilroy_root() -> Path:
    env = os.environ.get("KILROY_ROOT", "").strip()
    if env:
        p = Path(env).expanduser().resolve()
        if (p / "scripts" / "build-kilroy.sh").is_file():
            return p
    sg = INSTALL.parent.parent
    for candidate in (sg.parent / "KILROY", sg / "KILROY", Path.home() / "Desktop" / "KILROY"):
        if (candidate / "scripts" / "build-kilroy.sh").is_file():
            return candidate.resolve()
    return sg / "KILROY"


def _dmi(key: str) -> str:
    p = Path(f"/sys/class/dmi/id/{key}")
    try:
        if p.is_file():
            return p.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        pass
    return ""


def _read_text(path: Path, *, limit: int = 200_000) -> str:
    try:
        if path.is_file():
            return path.read_text(encoding="utf-8", errors="replace")[:limit]
    except OSError:
        pass
    return ""


def _run(cmd: list[str], *, timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)


def _loaded_modules() -> dict[str, bool]:
    out: dict[str, bool] = {}
    for line in _read_text(Path("/proc/modules")).splitlines():
        parts = line.split()
        if parts:
            out[parts[0]] = True
    return out


def _firmware_witness() -> dict[str, Any]:
    fw: dict[str, Any] = {
        "uefi": Path("/sys/firmware/efi").is_dir(),
        "efi_vars": Path("/sys/firmware/efi/efivars").is_dir(),
        "acpi": Path("/sys/firmware/acpi").is_dir(),
        "tpm": Path("/dev/tpm0").exists() or Path("/dev/tpmrm0").exists(),
        "iommu": Path("/sys/kernel/iommu_groups").is_dir(),
        "nx": "nx" in _read_text(Path("/proc/cpuinfo")),
        "vendor": _dmi("bios_vendor"),
        "version": _dmi("bios_version"),
        "date": _dmi("bios_date"),
        "board": _dmi("board_name"),
        "product": _dmi("product_name"),
    }
    sb = Path("/sys/firmware/efi/efivars/SecureBoot-8be4df61-93ca-11d2-aa0d-00e098032b8c")
    if sb.is_file():
        try:
            raw = sb.read_bytes()
            fw["secure_boot"] = raw[-1] == 1 if raw else None
        except OSError:
            fw["secure_boot"] = None
    else:
        fw["secure_boot"] = None
    tables = Path("/sys/firmware/acpi/tables")
    if tables.is_dir():
        fw["acpi_tables"] = sorted(p.name for p in tables.iterdir() if p.is_file())
    return fw


def _parse_grok_audit() -> dict[str, Any]:
    cached = _load(AUDIT_CACHE, {})
    stdout = str(cached.get("stdout") or "")
    if not stdout:
        script = _kilroy_root() / "scripts" / "grok-firmware-audit.sh"
        if script.is_file():
            try:
                proc = _run(["bash", str(script)], timeout=45)
                stdout = proc.stdout or ""
                _fsync_write(
                    AUDIT_CACHE,
                    json.dumps({
                        "ok": proc.returncode == 0,
                        "exit_code": proc.returncode,
                        "stdout": stdout[-8000:],
                        "stderr": (proc.stderr or "")[-2000:],
                        "updated": _now(),
                    }, ensure_ascii=False, indent=2) + "\n",
                )
            except (subprocess.SubprocessError, OSError):
                pass
    major: list[dict[str, str]] = []
    minor: list[dict[str, str]] = []
    for line in stdout.splitlines():
        if "[FAIL]" in line:
            major.append({"line": line.strip(), "bios_manual": True})
        elif "[WARN]" in line:
            minor.append({"line": line.strip(), "bios_manual": True})
    return {
        "major": major,
        "minor": minor,
        "major_count": len(major),
        "minor_count": len(minor),
        "ok": len(major) == 0,
    }


def _dmesg_threats(patterns: list[str]) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    text = ""
    proc = _run(["dmesg", "--ctime"], timeout=15)
    if proc.returncode == 0 and proc.stdout:
        text = proc.stdout
    else:
        text = _read_text(Path("/var/log/kern.log"), limit=500_000)
    seen: set[str] = set()
    for pat in patterns:
        for line in text.splitlines():
            if pat.lower() not in line.lower():
                continue
            key = line.strip()[:200]
            if key in seen:
                continue
            seen.add(key)
            hits.append({"pattern": pat, "line": key})
            if len(hits) >= 40:
                return hits
    return hits


def _efi_boot_threats() -> list[dict[str, Any]]:
    threats: list[dict[str, Any]] = []
    ev = Path("/sys/firmware/efi/efivars")
    if not ev.is_dir():
        return threats
    suspicious = re.compile(r"(grub|shim|windows|ubuntu|fedora|linupe|bootkit|unknown)", re.I)
    for path in sorted(ev.glob("Boot*"))[:64]:
        name = path.name
        if suspicious.search(name):
            continue
        if name.startswith("BootOrder") or name.startswith("BootOption"):
            continue
        if len(name) > 120:
            threats.append({"type": "efi_long_name", "name": name[:120]})
    return threats[:12]


def _module_threats(blacklist: list[str], loaded: dict[str, bool]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for mod in blacklist:
        base = mod.replace("-", "_")
        if loaded.get(base) or loaded.get(mod):
            rows.append({"module": base, "loaded": True, "removable": True})
        elif any(k.startswith(base) for k in loaded):
            hit = next(k for k in loaded if k.startswith(base))
            rows.append({"module": hit, "loaded": True, "removable": True})
    return rows


def _dev_mem_processes() -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for dev in ("/dev/mem", "/dev/kmem", "/dev/port"):
        if not Path(dev).exists():
            continue
        proc = _run(["fuser", "-v", dev], timeout=8)
        if proc.returncode != 0 and not proc.stderr and not proc.stdout:
            continue
        text = (proc.stdout or "") + (proc.stderr or "")
        pids = sorted({int(m) for m in re.findall(r"\b(\d+)\b", text) if int(m) > 1})
        for pid in pids[:16]:
            comm = _read_text(Path(f"/proc/{pid}/comm"), limit=64).strip()
            hits.append({"device": dev, "pid": pid, "comm": comm})
    return hits


def _cmdline_threats() -> list[str]:
    cmd = _read_text(Path("/proc/cmdline"))
    bad = (
        "mitigations=off", "nospec", "noibrs", "noibpb", "nopti",
        "acpi=off", "intel_iommu=off", "amd_iommu=off", "iommu=off",
    )
    return [tok for tok in bad if tok in cmd]


def _dmi_anomalies() -> list[str]:
    anomalies: list[str] = []
    for key in ("bios_vendor", "bios_version", "board_name", "product_name"):
        val = _dmi(key)
        if not val:
            anomalies.append(f"{key}:missing")
        elif not _DMI_RE.match(val):
            anomalies.append(f"{key}:suspicious_chars")
    return anomalies


def scan_threats() -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    policy = doctrine.get("policy") or {}
    patterns = doctrine.get("dmesg_threat_patterns") or []
    blacklist = list(doctrine.get("module_blacklist") or [])
    if os.environ.get("NEXUS_FIRMWARE_BLACKLIST_MEI", "0") == "1":
        blacklist.extend(doctrine.get("module_blacklist_optional") or [])

    loaded = _loaded_modules()
    grok = _parse_grok_audit()
    fw = _firmware_witness()

    threats: list[dict[str, Any]] = []

    for row in grok.get("major") or []:
        threats.append({"id": "bios_major", "severity": "major", **row})
    for row in grok.get("minor") or []:
        threats.append({"id": "bios_minor", "severity": "minor", **row})

    for mod in _module_threats(blacklist, loaded):
        threats.append({"id": "kernel_module", "severity": "high", **mod})

    for hit in _dmesg_threats(patterns):
        threats.append({"id": "dmesg_firmware", "severity": "medium", **hit})

    for tok in _cmdline_threats():
        threats.append({"id": "cmdline", "severity": "high", "token": tok})

    for anom in _dmi_anomalies():
        threats.append({"id": "dmi_anomaly", "severity": "low", "detail": anom})

    for proc in _dev_mem_processes():
        threats.append({"id": "dev_mem_accessor", "severity": "high", **proc})

    if fw.get("secure_boot") is False:
        threats.append({"id": "secure_boot_off", "severity": "major", "bios_manual": True})
    if not fw.get("tpm"):
        threats.append({"id": "tpm_missing", "severity": "major", "bios_manual": True})
    if not fw.get("iommu"):
        threats.append({"id": "iommu_off", "severity": "major", "bios_manual": True})
    if not fw.get("nx"):
        threats.append({"id": "nx_off", "severity": "major", "bios_manual": True})

    removable = [t for t in threats if t.get("removable") or t.get("id") in (
        "kernel_module", "dev_mem_accessor", "cmdline", "dmesg_firmware",
    ) and not t.get("bios_manual")]
    bios_manual = [t for t in threats if t.get("bios_manual")]

    verdict = "GREEN"
    if any(t.get("severity") == "major" for t in threats):
        verdict = "BIOS_REQUIRED"
    elif any(t.get("severity") == "high" for t in threats):
        verdict = "WARN"
    elif threats:
        verdict = "WATCH"

    return {
        "schema": "field-firmware-threat-scan/v1",
        "ts": _now(),
        "firmware_witness": fw,
        "grok_audit": grok,
        "threat_count": len(threats),
        "removable_count": len(removable),
        "bios_manual_count": len(bios_manual),
        "threats": threats,
        "removable": removable,
        "bios_manual": bios_manual,
        "verdict": verdict,
        "flash_chip": False,
        "policy": policy,
    }


def _read_sysctl(key: str) -> str | None:
    path = Path("/proc/sys") / key.replace(".", "/")
    try:
        if path.is_file():
            return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        pass
    return None


def _apply_sysctl(want: dict[str, Any]) -> dict[str, Any]:
    applied: list[str] = []
    failed: list[str] = []
    for key, val in want.items():
        try:
            subprocess.run(
                ["sysctl", "-w", f"{key}={val}"],
                capture_output=True, text=True, timeout=5, check=False,
            )
            cur = _read_sysctl(key)
            if str(cur).strip() == str(val).strip():
                applied.append(key)
            else:
                failed.append(f"{key}:have={cur}")
        except (subprocess.SubprocessError, OSError) as exc:
            failed.append(f"{key}:{exc}")
    lines = [f"# NEXUS firmware threat hardening {_now()}", *[f"{k} = {v}" for k, v in want.items()]]
    state_copy = STATE / "99-nexus-firmware-threat.conf"
    try:
        state_copy.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except OSError:
        failed.append("state_dropin")
    if os.environ.get("NEXUS_FIRMWARE_SYSCTL_SYSTEM", "1") == "1":
        try:
            proc = _run(["sudo", "-n", "tee", str(SYSCTL_DROPIN)], timeout=10)
            if proc.returncode != 0:
                proc2 = subprocess.run(
                    ["sudo", "tee", str(SYSCTL_DROPIN)],
                    input="\n".join(lines) + "\n",
                    capture_output=True, text=True, timeout=30, check=False,
                )
                if proc2.returncode != 0:
                    failed.append("sysctl_dropin_sudo")
            else:
                _run(["sudo", "-n", "sysctl", "--system"], timeout=20)
        except (subprocess.SubprocessError, OSError):
            failed.append("sysctl_dropin")
    return {"ok": not failed, "applied": applied, "failed": failed, "state_dropin": str(state_copy)}


def _write_modprobe_blacklist(modules: list[str]) -> dict[str, Any]:
    lines = [f"# NEXUS firmware threat blacklist {_now()}"]
    for mod in modules:
        lines.append(f"blacklist {mod}")
        lines.append(f"install {mod} /bin/false")
    payload = "\n".join(lines) + "\n"
    state_copy = STATE / "nexus-firmware-threat-modprobe.conf"
    try:
        state_copy.write_text(payload, encoding="utf-8")
    except OSError:
        return {"ok": False, "error": "state_modprobe_write"}
    installed = False
    try:
        proc = subprocess.run(
            ["sudo", "-n", "tee", str(MODPROBE_DROPIN)],
            input=payload, capture_output=True, text=True, timeout=15, check=False,
        )
        if proc.returncode != 0:
            proc = subprocess.run(
                ["sudo", "tee", str(MODPROBE_DROPIN)],
                input=payload, capture_output=True, text=True, timeout=30, check=False,
            )
        installed = proc.returncode == 0
    except (subprocess.SubprocessError, OSError):
        pass
    return {"ok": True, "modules": modules, "state_copy": str(state_copy), "system_installed": installed}


def _unload_modules(modules: list[str]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    loaded = _loaded_modules()
    for mod in modules:
        if mod not in loaded:
            continue
        try:
            proc = subprocess.run(
                ["sudo", "-n", "modprobe", "-r", mod],
                capture_output=True, text=True, timeout=10, check=False,
            )
            if proc.returncode != 0:
                proc = subprocess.run(
                    ["sudo", "modprobe", "-r", mod],
                    capture_output=True, text=True, timeout=15, check=False,
                )
            results.append({
                "module": mod,
                "removed": proc.returncode == 0,
                "stderr": (proc.stderr or "")[:200],
            })
        except (subprocess.SubprocessError, OSError) as exc:
            results.append({"module": mod, "removed": False, "error": str(exc)})
    return results


def _signal_dev_mem_pids(pids: list[int]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for pid in pids:
        if pid <= 1:
            continue
        try:
            proc = subprocess.run(
                ["sudo", "-n", "kill", "-TERM", str(pid)],
                capture_output=True, text=True, timeout=5, check=False,
            )
            if proc.returncode != 0:
                proc = subprocess.run(
                    ["sudo", "kill", "-TERM", str(pid)],
                    capture_output=True, text=True, timeout=8, check=False,
                )
            results.append({"pid": pid, "signaled": proc.returncode == 0})
        except (subprocess.SubprocessError, OSError) as exc:
            results.append({"pid": pid, "signaled": False, "error": str(exc)})
    return results


def remove_threats(scan: dict[str, Any], *, apply: bool = True) -> dict[str, Any]:
    if not apply:
        return {"ok": True, "dry_run": True, "would_remove": scan.get("removable_count", 0)}

    doctrine = _load(DOCTRINE, {})
    policy = doctrine.get("policy") or {}
    removed: list[dict[str, Any]] = []

    mod_hits = [t["module"] for t in scan.get("threats", []) if t.get("id") == "kernel_module" and t.get("module")]
    blacklist = list(dict.fromkeys(mod_hits + list(doctrine.get("module_blacklist") or [])))
    if policy.get("remove_kernel_module_threats", True) and blacklist:
        mp = _write_modprobe_blacklist(blacklist)
        removed.append({"action": "modprobe_blacklist", **mp})
        removed.extend({"action": "rmmod", **r} for r in _unload_modules(blacklist))

    if policy.get("block_dev_mem_access", True):
        pids = [int(t["pid"]) for t in scan.get("threats", []) if t.get("id") == "dev_mem_accessor" and t.get("pid")]
        if pids:
            removed.extend({"action": "kill_dev_mem", **r} for r in _signal_dev_mem_pids(pids))

    if policy.get("apply_sysctl_hardening", True):
        sysctl = _apply_sysctl(doctrine.get("sysctl_hardening") or {})
        removed.append({"action": "sysctl_harden", **sysctl})

    cpu_py = INSTALL / "lib" / "cpu-vulnerability-shield.py"
    if cpu_py.is_file() and os.environ.get("NEXUS_FIRMWARE_CPU_SHIELD", "1") == "1":
        try:
            proc = subprocess.run(
                [sys.executable, str(cpu_py), "apply"],
                capture_output=True, text=True, timeout=30, check=False,
                env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
            )
            removed.append({
                "action": "cpu_vulnerability_shield",
                "ok": proc.returncode == 0,
                "stdout": (proc.stdout or "")[-500:],
            })
        except (subprocess.SubprocessError, OSError) as exc:
            removed.append({"action": "cpu_vulnerability_shield", "ok": False, "error": str(exc)})

    removed_count = sum(1 for r in removed if r.get("removed") or r.get("ok"))
    return {
        "schema": "field-firmware-threat-removal/v1",
        "ts": _now(),
        "removed_actions": removed,
        "removed_count": removed_count,
        "bios_manual_remaining": scan.get("bios_manual_count", 0),
        "safe": True,
        "flash_chip": False,
    }


def cycle(*, apply: bool | None = None) -> dict[str, Any]:
    if apply is None:
        apply = os.environ.get("NEXUS_FIRMWARE_APPLY", "1") == "1"
    scan = scan_threats()
    removal = remove_threats(scan, apply=apply)
    doc: dict[str, Any] = {
        "schema": "field-firmware-threat/v1",
        "ts": _now(),
        "updated": _now(),
        "host": platform.node(),
        "scan": scan,
        "removal": removal,
        "verdict": scan.get("verdict"),
        "threat_count": scan.get("threat_count"),
        "removed_count": removal.get("removed_count"),
        "bios_manual_count": scan.get("bios_manual_count"),
        "safe": scan.get("verdict") in ("GREEN", "WATCH") or removal.get("removed_count", 0) > 0,
        "flash_chip": False,
        "motto": str(_load(DOCTRINE, {}).get("motto") or ""),
    }
    runtime = {
        "schema": "field-firmware-threat-runtime/v1",
        "ts": doc["ts"],
        "verdict": doc["verdict"],
        "threat_count": doc["threat_count"],
        "removed_count": doc["removed_count"],
        "bios_manual_count": doc["bios_manual_count"],
        "secure_boot": (scan.get("firmware_witness") or {}).get("secure_boot"),
        "iommu": (scan.get("firmware_witness") or {}).get("iommu"),
    }
    _fsync_write(PANEL, json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
    _fsync_write(RUNTIME, json.dumps(runtime, ensure_ascii=False, indent=2) + "\n")
    _append_ledger({
        "ts": doc["ts"],
        "verdict": doc["verdict"],
        "threat_count": doc["threat_count"],
        "removed_count": doc["removed_count"],
        "bios_manual": doc["bios_manual_count"],
    })
    return doc


def panel_json() -> dict[str, Any]:
    doc = _load(PANEL, {})
    if doc.get("schema"):
        return doc
    return cycle()


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("cycle", "meld", "build"):
        print(json.dumps(cycle(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "scan":
        print(json.dumps(scan_threats(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "remove":
        scan = scan_threats()
        print(json.dumps(remove_threats(scan, apply=True), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: field-firmware-threat-removal.py [json|cycle|scan|remove]"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())