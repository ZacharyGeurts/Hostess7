#!/usr/bin/env pythong
"""Kernel meld — witness host kernel + KILROY bzImage in-place with plate chain.

linux-7.1.1 / KILROY CONFIG_RTX_FIELD_DIE is the last version: melded with plates,
not flashed over the host. Host kernel remains witness until Grok/KILROY boot.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
DOCTRINE = INSTALL / "data" / "field-kernel-meld-doctrine.json"
PANEL = STATE / "field-kernel-meld-panel.json"
RUNTIME = STATE / "field-kernel-meld-runtime.json"
LEDGER = STATE / "field-kernel-meld-ledger.jsonl"
LOCK = STATE / "field-kernel-meld.lock"
REDUNDANT = STATE / "kernel-meld-redundant"
MANIFEST = STATE / "field-kernel-inplace-manifest.json"

CONFIG_FRAGMENTS: tuple[str, ...] = (
    "config/kilroy-identity.config",
    "build-cmake/kilroy-auto.fragment",
)

_GEN = 0


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
    for name in ("field-kernel-meld-panel.json", "field-kernel-meld-runtime.json"):
        for suffix in ("", ".bak"):
            (REDUNDANT / f"{name}{suffix}").write_text(payload, encoding="utf-8")


def _sg_root() -> Path:
    env = os.environ.get("SG_ROOT", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return INSTALL.parent.parent.resolve()


def _kilroy_root() -> Path:
    env = os.environ.get("KILROY_ROOT", "").strip()
    if env:
        p = Path(env).expanduser().resolve()
        if (p / "scripts" / "build-kilroy.sh").is_file():
            return p
    sg = _sg_root()
    for candidate in (
        sg.parent / "KILROY",
        sg / "KILROY",
        Path.home() / "Desktop" / "KILROY",
        Path.home() / "KILROY",
    ):
        if (candidate / "scripts" / "build-kilroy.sh").is_file():
            return candidate.resolve()
    return sg / "KILROY"


def _substrate_root() -> Path | None:
    env = os.environ.get("KILROY_COMPAT_SRC", "").strip()
    if env:
        p = Path(env).expanduser().resolve()
        if (p / "Makefile").is_file():
            return p
    sg = _sg_root()
    for candidate in (
        sg / "compat" / "linux-7.1.1",
        sg / "linux-kernel" / "linux-7.1.1",
    ):
        if (candidate / "Makefile").is_file():
            return candidate.resolve()
    return None


def _bzimage_path(kilroy: Path) -> Path | None:
    for bz in (
        kilroy / "build" / "bzImage",
        kilroy / "rootfs" / "production-staging" / "boot" / "kilroy" / "bzImage",
    ):
        if bz.is_file():
            return bz.resolve()
    return None


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _file_witness(path: Path | None) -> dict[str, Any]:
    if not path or not path.is_file():
        return {"present": False, "path": str(path) if path else None}
    try:
        st = path.stat()
        digest = _sha256_file(path)
        return {
            "present": True,
            "path": str(path),
            "size": st.st_size,
            "mtime": int(st.st_mtime),
            "sha256": digest,
            "hash_byte": int(digest[:2], 16),
        }
    except OSError as exc:
        return {"present": False, "path": str(path), "error": str(exc)}


def _host_kernel() -> dict[str, Any]:
    version = ""
    try:
        version = Path("/proc/version").read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        pass
    is_kilroy = "kilroy" in version.lower()
    uname = platform.uname()
    return {
        "version": version[:240],
        "release": uname.release[:120],
        "machine": uname.machine,
        "is_kilroy": is_kilroy,
        "witness_only": not is_kilroy,
    }


def _kilroy_proc() -> dict[str, Any]:
    root = Path("/proc/kilroy_field")
    nodes = [
        "status", "security", "stack", "sdf", "ai", "boot",
        "power", "thermo", "flow", "cache", "direct", "gpu",
    ]
    live = root.is_dir()
    present: dict[str, bool] = {}
    for node in nodes:
        present[node] = (root / node).exists()
    dev = Path("/dev/kilroy_field").exists()
    return {
        "live": live or any(present.values()),
        "proc_kilroy_field": live,
        "dev_kilroy_field": dev,
        "nodes": present,
        "node_count": sum(1 for v in present.values() if v),
    }


def _config_rtx_field_die(kilroy: Path) -> dict[str, Any]:
    hits: list[str] = []
    for rel in CONFIG_FRAGMENTS:
        path = kilroy / rel
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if "CONFIG_RTX_FIELD_DIE=y" in text:
            hits.append(rel)
    rtx_dir = kilroy / "kernel" / "rtx"
    return {
        "enabled": bool(hits) or rtx_dir.is_dir(),
        "fragments": hits,
        "rtx_module": str(rtx_dir) if rtx_dir.is_dir() else None,
    }


def _substrate_version(substrate: Path | None) -> dict[str, Any]:
    if not substrate:
        return {"pinned": False, "version": None}
    version = "linux-7.1.1"
    makefile = substrate / "Makefile"
    if makefile.is_file():
        try:
            for line in makefile.read_text(encoding="utf-8", errors="replace").splitlines()[:30]:
                if line.startswith("VERSION") or line.startswith("PATCHLEVEL"):
                    version = f"{version} ({line.strip()})"
                    break
        except OSError:
            pass
    witness = _file_witness(makefile if makefile.is_file() else None)
    return {
        "pinned": True,
        "path": str(substrate),
        "version": version,
        "makefile": witness if witness.get("present") else {"present": makefile.is_file()},
    }


def _plate_meld_link() -> dict[str, Any]:
    rt = _load(STATE / "field-plate-meld-runtime.json", {})
    meld = _load(STATE / "field-plate-meld.json", {})
    return {
        "plate_generation": int(rt.get("generation") or meld.get("generation") or 0),
        "plate_chain_hash": rt.get("chain_hash") or meld.get("chain_hash"),
        "plate_count": meld.get("plate_count"),
    }


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


def meld(*, link_plates: bool = True) -> dict[str, Any]:
    """Witness kernel stack and write in-place meld panel for plate fuse."""
    global _GEN
    fd = _meld_lock()
    try:
        prev = _load(RUNTIME, {})
        prev_gen = int(prev.get("generation") or 0)
        _GEN = prev_gen + 1

        kilroy = _kilroy_root()
        substrate = _substrate_root()
        bz = _bzimage_path(kilroy)
        bz_w = _file_witness(bz)
        host = _host_kernel()
        proc = _kilroy_proc()
        config = _config_rtx_field_die(kilroy)
        sub = _substrate_version(substrate)
        plate_link = _plate_meld_link() if link_plates else {}

        boot_vector = int(bz_w.get("hash_byte") or 0) if bz_w.get("present") else 0
        if proc.get("live"):
            boot_vector = min(proc.get("node_count", 0) * 17 + 0xA5, 255)

        inplace: dict[str, Any] = {
            "schema": "field-kernel-inplace/v1",
            "ts": _now(),
            "policy": "non_destructive",
            "target_bzimage": bz_w.get("path"),
            "target_sha256": bz_w.get("sha256"),
            "substrate": sub.get("path"),
            "host_witness": host.get("version"),
            "grok_boot_ready": bool(bz_w.get("present") and config.get("enabled")),
            "plate_generation": plate_link.get("plate_generation"),
        }
        _fsync_write(MANIFEST, json.dumps(inplace, ensure_ascii=False, indent=2) + "\n")

        doc: dict[str, Any] = {
            "schema": "field-kernel-meld/v1",
            "ts": _now(),
            "generation": _GEN,
            "motto": str(_load(DOCTRINE, {}).get("motto") or "Kernel meld in-place"),
            "end_of_basic_computing": True,
            "in_place": True,
            "kilroy_root": str(kilroy),
            "kilroy_present": kilroy.is_dir(),
            "substrate_pinned": sub.get("pinned", False),
            "substrate": sub,
            "config_rtx_field_die": config,
            "host_kernel": host,
            "kilroy_proc": proc,
            "kilroy_live": proc.get("live", False),
            "bzimage": bz_w,
            "bzimage_ready": bz_w.get("present", False),
            "bzimage_hash_byte": bz_w.get("hash_byte", 0),
            "boot_vector": boot_vector,
            "plate_link": plate_link,
            "inplace_manifest": str(MANIFEST),
            "summary": {
                "field_kernel_running": proc.get("live") or host.get("is_kilroy"),
                "witness_host": host.get("witness_only", True),
                "target_ready": bool(bz_w.get("present")),
                "substrate": sub.get("version"),
                "rtx_field_die": config.get("enabled"),
            },
        }

        payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
        _fsync_write(PANEL, payload)
        runtime = {
            "schema": "field-kernel-meld-runtime/v1",
            "ts": doc["ts"],
            "generation": _GEN,
            "kilroy_live": doc["kilroy_live"],
            "bzimage_ready": doc["bzimage_ready"],
            "boot_vector": boot_vector,
            "summary": doc["summary"],
        }
        _fsync_write(RUNTIME, json.dumps(runtime, ensure_ascii=False, indent=2) + "\n")
        _mirror(doc)
        _append_ledger({
            "ts": doc["ts"],
            "generation": _GEN,
            "bzimage_sha256": bz_w.get("sha256"),
            "kilroy_live": doc["kilroy_live"],
            "plate_generation": plate_link.get("plate_generation"),
        })
        return doc
    finally:
        _meld_unlock(fd)


def read_panel() -> dict[str, Any]:
    doc = _load(PANEL, {})
    if doc.get("schema"):
        return doc
    for path in (REDUNDANT / "field-kernel-meld-panel.json", REDUNDANT / "field-kernel-meld-panel.json.bak"):
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
    print(json.dumps({"error": "usage: field-kernel-meld.py [json|meld|manifest|witness]"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())