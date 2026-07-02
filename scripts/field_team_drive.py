#!/usr/bin/env pythong
"""TEAM field drive — Field 1 sync impl (library, bulk). Use ./Hostess7.sh field sync.

Default device: /dev/nvme2n1 (TEAM TM8FP6001T). Mount at HOSTESS7_TEAM_MOUNT (/mnt/team).
KILROY_FIELD on nvme1 is alternate: /media/default/KILROY_FIELD.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

LOCAL_STORAGE = ROOT / "cache" / "fieldstorage"
DEFAULT_DEV = os.environ.get("TEAM_DRIVE_DEV", "/dev/nvme2n1")
DEFAULT_MOUNT = Path(os.environ.get("HOSTESS7_TEAM_MOUNT", "/mnt/team"))
KILROY_MOUNT = Path("/media/default/KILROY_FIELD")
TEAM_LABEL = os.environ.get("HOSTESS7_TEAM_LABEL", "HOSTESS7_TEAM")


def team_mount_path() -> Path:
    if DEFAULT_MOUNT.is_dir() and os.access(DEFAULT_MOUNT, os.W_OK):
        return DEFAULT_MOUNT
    if KILROY_MOUNT.is_dir() and os.access(KILROY_MOUNT, os.W_OK):
        return KILROY_MOUNT
    return DEFAULT_MOUNT


def team_storage() -> Path:
    return team_mount_path() / "fieldstorage"


def team_hostess7() -> Path:
    return team_mount_path() / "Hostess7"


def status() -> dict[str, Any]:
    mount = team_mount_path()
    dev = Path(DEFAULT_DEV)
    storage = team_storage()
    h7 = team_hostess7()
    return {
        "team_device": str(dev),
        "team_device_present": dev.exists(),
        "team_mount": str(mount),
        "team_mount_writable": mount.is_dir() and os.access(mount, os.W_OK),
        "team_storage": str(storage),
        "team_storage_bytes": _dir_bytes(storage),
        "team_hostess7": str(h7),
        "team_hostess7_present": h7.is_dir(),
        "local_storage_bytes": _dir_bytes(LOCAL_STORAGE),
        "kilroy_mount": str(KILROY_MOUNT),
        "kilroy_present": KILROY_MOUNT.is_dir(),
    }


def _dir_bytes(path: Path) -> int:
    if not path.is_dir():
        return 0
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def _run(cmd: list[str], *, check: bool = True, sudo_pw: str = "") -> subprocess.CompletedProcess[str]:
    stdin = f"{sudo_pw}\n" if sudo_pw and cmd[0] == "sudo" else None
    return subprocess.run(cmd, text=True, capture_output=True, check=check, input=stdin)


def ensure_mount(*, sudo_pw: str | None = None) -> Path:
    """Mount TEAM NVMe at HOSTESS7_TEAM_MOUNT if not already mounted."""
    mount = team_mount_path()
    if mount.is_dir() and os.access(mount, os.W_OK) and _dir_bytes(mount) > 0:
        return mount

    pw = sudo_pw or os.environ.get("HOSTESS7_SUDO_PW", "")
    if not pw:
        raise RuntimeError("Need sudo to mount TEAM drive — set HOSTESS7_SUDO_PW or pass --sudo-pw")

    dev = Path(DEFAULT_DEV)
    if not dev.exists():
        if KILROY_MOUNT.is_dir() and os.access(KILROY_MOUNT, os.W_OK):
            return KILROY_MOUNT
        raise FileNotFoundError(f"TEAM device missing: {dev}")

    _run(["sudo", "-S", "mkdir", "-p", str(DEFAULT_MOUNT)], check=False, sudo_pw=pw)
    blk = _run(["sudo", "-S", "blkid", "-o", "value", "-s", "TYPE", str(dev)], check=False, sudo_pw=pw)
    fstype = (blk.stdout or "").strip()
    if not fstype:
        _run(["sudo", "-S", "mkfs.ext4", "-F", "-L", TEAM_LABEL, str(dev)], sudo_pw=pw)
    _run(["sudo", "-S", "mount", str(dev), str(DEFAULT_MOUNT)], sudo_pw=pw)
    _run(["sudo", "-S", "chown", "-R", f"{os.getuid()}:{os.getgid()}", str(DEFAULT_MOUNT)], sudo_pw=pw)
    marker = DEFAULT_MOUNT / "TEAM_DRIVE_OK"
    marker.write_text(f"device={dev}\nlabel={TEAM_LABEL}\n", encoding="utf-8")
    return DEFAULT_MOUNT


def sync_to_team(*, storage_only: bool = False) -> dict[str, Any]:
    """Rsync local Hostess7 + fieldstorage → TEAM drive (fast NVMe I/O)."""
    mount = ensure_mount(sudo_pw=os.environ.get("HOSTESS7_SUDO_PW"))
    dest_h7 = mount / "Hostess7"
    dest_storage = mount / "fieldstorage"
    dest_storage.mkdir(parents=True, exist_ok=True)

    if not storage_only:
        _rsync(ROOT, dest_h7, excludes=["cache/fieldstorage", ".git", "__pycache__", "*.pyc"])

    if LOCAL_STORAGE.is_dir():
        _rsync(LOCAL_STORAGE, dest_storage, excludes=[])

    return {
        "action": "sync_to_team",
        "mount": str(mount),
        "hostess7": str(dest_h7),
        "storage": str(dest_storage),
        "storage_bytes": _dir_bytes(dest_storage),
    }


def _rsync(src: Path, dest: Path, *, excludes: list[str]) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["rsync", "-a", "--delete"]
    for ex in excludes:
        cmd.extend(["--exclude", ex])
    cmd.extend([str(src) + "/", str(dest) + "/"])
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"rsync failed: {proc.stderr[-500:]}")


def run_on_team(cmd: str, *, storage: bool = True) -> dict[str, Any]:
    """Run a Hostess7 command on TEAM drive copy (parallel fast I/O)."""
    mount = ensure_mount(sudo_pw=os.environ.get("HOSTESS7_SUDO_PW"))
    h7 = mount / "Hostess7"
    if not (h7 / "Hostess7.sh").is_file():
        sync_to_team()
        h7 = mount / "Hostess7"

    env = os.environ.copy()
    if storage:
        env["HOSTESS7_STORAGE"] = str(mount / "fieldstorage")
    proc = subprocess.run(
        cmd,
        shell=True,
        cwd=h7,
        env=env,
        capture_output=True,
        text=True,
        timeout=3600,
    )
    return {
        "action": "run_on_team",
        "cmd": cmd,
        "cwd": str(h7),
        "rc": proc.returncode,
        "stdout": proc.stdout[-4000:],
        "stderr": proc.stderr[-2000:],
        "ok": proc.returncode == 0,
    }


def format_status(st: dict[str, Any]) -> str:
    mb = lambda b: f"{b / (1024 * 1024):.1f} MiB"
    lines = [
        "=== TEAM Field Drive (mirrors SG/Hostess7 — canonical local) ===",
        f"Device: {st['team_device']} ({'present' if st['team_device_present'] else 'missing'})",
        f"Mount: {st['team_mount']} ({'writable' if st['team_mount_writable'] else 'not ready'})",
        f"TEAM storage: {mb(st['team_storage_bytes'])} @ {st['team_storage']}",
        f"TEAM Hostess7: {'yes' if st['team_hostess7_present'] else 'no'} @ {st['team_hostess7']}",
        f"Local storage: {mb(st['local_storage_bytes'])}",
        f"KILROY_FIELD: {'present' if st['kilroy_present'] else 'absent'} @ {st['kilroy_mount']}",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hostess7 TEAM field drive")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="Show TEAM drive status")
    mount_p = sub.add_parser("mount", help="Format+mount nvme2n1 if needed")
    mount_p.add_argument("--sudo-pw", default=os.environ.get("HOSTESS7_SUDO_PW", ""))

    sync_p = sub.add_parser("sync", help="Rsync Hostess7 + fieldstorage to TEAM")
    sync_p.add_argument("--storage-only", action="store_true")

    run_p = sub.add_parser("run", help="Run command on TEAM Hostess7 copy")
    run_p.add_argument("command", help="Shell command e.g. ./Hostess7.sh library-fetch")

    args = parser.parse_args(argv)

    if args.cmd == "status":
        st = status()
        print(format_status(st))
        print("METRIC team_drive=1")
        return 0

    if args.cmd == "mount":
        if args.sudo_pw:
            os.environ["HOSTESS7_SUDO_PW"] = args.sudo_pw
        m = ensure_mount(sudo_pw=args.sudo_pw)
        print(f"OK team mount → {m}")
        return 0

    if args.cmd == "sync":
        rep = sync_to_team(storage_only=args.storage_only)
        print(f"OK sync → {rep['mount']} storage={rep['storage_bytes'] // (1024*1024)} MiB")
        return 0

    if args.cmd == "run":
        rep = run_on_team(args.command)
        print(rep["stdout"])
        if rep["stderr"]:
            print(rep["stderr"], file=sys.stderr)
        return 0 if rep["ok"] else 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())