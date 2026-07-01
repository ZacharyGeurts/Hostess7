#!/usr/bin/env pythong
"""Storage — AmmoOS disk & partition GUI backend (fdisk-class, sovereign guards)."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-storage-doctrine.json"
PANEL = STATE / "field-storage-panel.json"
LEDGER = STATE / "field-storage-ledger.jsonl"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


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


def _log(row: dict[str, Any]) -> None:
    try:
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": _now(), **row}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {"protected_mounts": ["/"], "allowed_fs": ["ext4", "vfat"]})


def _run(cmd: list[str], *, timeout: int = 30, input_text: str | None = None) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            input=input_text,
        )
        return {
            "ok": proc.returncode == 0,
            "rc": proc.returncode,
            "stdout": (proc.stdout or "").strip(),
            "stderr": (proc.stderr or "").strip(),
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": str(exc)}


def _bytes_human(n: int | float | None) -> str:
    if n is None:
        return "—"
    try:
        v = float(n)
    except (TypeError, ValueError):
        return "—"
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if v < 1024 or unit == "TiB":
            if unit == "B":
                return f"{int(v)} {unit}"
            return f"{v:.1f} {unit}"
        v /= 1024
    return f"{v:.1f} PiB"


def _norm_dev(path: str) -> str:
    p = str(path or "").strip()
    if p.startswith("/dev/"):
        return p
    if p:
        return f"/dev/{p}"
    return ""


def _is_protected_device(dev: str, mount: str = "") -> bool:
    doc = _doctrine()
    dev = _norm_dev(dev)
    mount = str(mount or "").strip()
    for m in doc.get("protected_mounts") or []:
        if mount == m or mount.startswith(m + "/"):
            return True
    for pref in doc.get("protected_prefixes") or []:
        if mount.startswith(pref):
            return True
    root_dev = _run(["findmnt", "-n", "-o", "SOURCE", "/"], timeout=5)
    if root_dev.get("ok") and dev and root_dev.get("stdout"):
        root = root_dev["stdout"].split()[0]
        if dev == root or dev.startswith(root.rstrip("0123456789")):
            return True
    return False


def _node_row(node: dict[str, Any], *, parent_name: str = "") -> dict[str, Any]:
    name = str(node.get("name") or "")
    dev = _norm_dev(name)
    mount = str(node.get("mountpoint") or "")
    return {
        "name": name,
        "dev": dev,
        "type": str(node.get("type") or ""),
        "size_bytes": int(node.get("size") or 0),
        "size_human": _bytes_human(node.get("size")),
        "model": (node.get("model") or "").strip(),
        "vendor": (node.get("vendor") or "").strip(),
        "serial": (node.get("serial") or "").strip(),
        "tran": (node.get("tran") or "").strip(),
        "ro": bool(node.get("ro")),
        "rm": bool(node.get("rm")),
        "mountpoint": mount,
        "fstype": node.get("fstype") or "",
        "uuid": node.get("uuid") or "",
        "partlabel": node.get("partlabel") or "",
        "parttypename": node.get("parttypename") or "",
        "pkname": node.get("pkname") or parent_name,
        "protected": _is_protected_device(dev, mount),
    }


def _lsblk_tree() -> list[dict[str, Any]]:
    if not shutil.which("lsblk"):
        return []
    res = _run(["lsblk", "-J", "-O", "-b", "-e", "7"], timeout=15)
    if not res.get("ok"):
        return []
    try:
        doc = json.loads(res.get("stdout") or "{}")
    except json.JSONDecodeError:
        return []

    disks: list[dict[str, Any]] = []
    for block in doc.get("blockdevices") or []:
        if str(block.get("type") or "") != "disk":
            continue
        disk = _node_row(block)
        disk["children"] = [_node_row(c, parent_name=disk["name"]) for c in (block.get("children") or [])]
        disks.append(disk)
    return disks


def _df_usage() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    res = _run(["df", "-B1", "-T"], timeout=10)
    if not res.get("ok"):
        return rows
    lines = (res.get("stdout") or "").splitlines()
    for line in lines[1:]:
        parts = line.split()
        if len(parts) < 7:
            continue
        fs, typ, blocks, used, avail = parts[0], parts[1], parts[2], parts[3], parts[4]
        mount = parts[6]
        try:
            total = int(blocks)
            used_i = int(used)
            pct = int(used_i * 100 / total) if total else 0
        except ValueError:
            total = used_i = pct = 0
        rows.append({
            "device": fs,
            "fstype": typ,
            "mount": mount,
            "total_bytes": total,
            "used_bytes": used_i,
            "avail_bytes": int(avail) if avail.isdigit() else 0,
            "pct_used": pct,
            "size_human": _bytes_human(total),
            "used_human": _bytes_human(used_i),
        })
    return rows


def scan() -> dict[str, Any]:
    disks = _lsblk_tree()
    usage = _df_usage()
    part_count = sum(len(d.get("children") or []) for d in disks)
    doc = {
        "schema": "field-storage-panel/v1",
        "ok": True,
        "ts": _now(),
        "motto": _doctrine().get("motto"),
        "disk_count": len(disks),
        "partition_count": part_count,
        "disks": disks,
        "usage": usage,
        "tools": {
            "lsblk": bool(shutil.which("lsblk")),
            "parted": bool(shutil.which("parted")),
            "sfdisk": bool(shutil.which("sfdisk")),
            "udisksctl": bool(shutil.which("udisksctl")),
        },
    }
    _save(PANEL, doc)
    return doc


def panel_doc() -> dict[str, Any]:
    cached = _load(PANEL, {})
    if cached.get("disks"):
        cached["ts"] = _now()
        return cached
    return scan()


def _mount_udisks(dev: str, mount: bool) -> dict[str, Any]:
    dev = _norm_dev(dev)
    if not dev:
        return {"ok": False, "error": "device_required"}
    if _is_protected_device(dev):
        return {"ok": False, "error": "protected_device"}
    if not shutil.which("udisksctl"):
        return {"ok": False, "error": "udisksctl_missing"}
    op = "mount" if mount else "unmount"
    res = _run(["udisksctl", op, "-b", dev], timeout=30)
    _log({"op": op, "dev": dev, "ok": res.get("ok")})
    if res.get("ok"):
        return {"ok": True, "action": op, "dev": dev, "scan": scan()}
    return {"ok": False, "error": res.get("stderr") or res.get("error") or f"{op}_failed"}


def _format_partition(dev: str, fstype: str, *, confirm: str) -> dict[str, Any]:
    dev = _norm_dev(dev)
    fstype = str(fstype or "ext4").lower().replace("fat32", "vfat")
    allowed = [str(x).lower() for x in (_doctrine().get("allowed_fs") or [])]
    if fstype not in allowed:
        return {"ok": False, "error": "fstype_not_allowed"}
    if confirm != _doctrine().get("confirm_phrase_format", "FORMAT"):
        return {"ok": False, "error": "confirm_required", "need": _doctrine().get("confirm_phrase_format")}
    if _is_protected_device(dev):
        return {"ok": False, "error": "protected_device"}
    mkfs_map = {
        "ext4": ["mkfs.ext4", "-F"],
        "ext3": ["mkfs.ext3", "-F"],
        "vfat": ["mkfs.vfat", "-F"],
        "fat32": ["mkfs.vfat", "-F"],
        "ntfs": ["mkfs.ntfs", "-f"],
        "btrfs": ["mkfs.btrfs", "-f"],
        "xfs": ["mkfs.xfs", "-f"],
    }
    cmd_base = mkfs_map.get(fstype)
    if not cmd_base or not shutil.which(cmd_base[0]):
        return {"ok": False, "error": "mkfs_unavailable", "fstype": fstype}
    res = _run([*cmd_base, dev], timeout=120)
    _log({"op": "format", "dev": dev, "fstype": fstype, "ok": res.get("ok")})
    if res.get("ok"):
        return {"ok": True, "formatted": dev, "fstype": fstype, "scan": scan()}
    return {"ok": False, "error": res.get("stderr") or "format_failed"}


def _partition_plan(disk: str, table: str, partitions: list[dict[str, Any]]) -> dict[str, Any]:
    disk = _norm_dev(disk)
    if not disk or not disk.startswith("/dev/"):
        return {"ok": False, "error": "disk_required"}
    if _is_protected_device(disk, "/"):
        return {"ok": False, "error": "protected_disk"}
    table = str(table or "gpt").lower()
    if table not in [t.lower() for t in (_doctrine().get("partition_table_types") or ["gpt"])]:
        return {"ok": False, "error": "invalid_table"}
    plan: list[dict[str, Any]] = []
    for i, part in enumerate(partitions, start=1):
        size = str(part.get("size") or "").strip()
        fstype = str(part.get("fstype") or "ext4")
        if not size:
            continue
        plan.append({"number": i, "size": size, "fstype": fstype})
    return {
        "ok": True,
        "dry_run": True,
        "disk": disk,
        "table": table,
        "partitions": plan,
        "warning": "Applying will destroy all data on this disk.",
        "commands_preview": [
            f"parted -s {disk} mklabel {table}",
            *[f"parted -s {disk} mkpart primary {p['fstype']} {p['size']}" for p in plan],
        ],
    }


def _partition_apply(disk: str, table: str, partitions: list[dict[str, Any]], *, confirm: str) -> dict[str, Any]:
    if confirm != _doctrine().get("confirm_phrase_partition", "PARTITION"):
        return {"ok": False, "error": "confirm_required", "need": _doctrine().get("confirm_phrase_partition")}
    plan = _partition_plan(disk, table, partitions)
    if not plan.get("ok"):
        return plan
    disk = plan["disk"]
    if not shutil.which("parted"):
        return {"ok": False, "error": "parted_missing"}
    res = _run(["parted", "-s", disk, "mklabel", plan["table"]], timeout=30)
    if not res.get("ok"):
        return {"ok": False, "error": res.get("stderr") or "mklabel_failed"}
    created: list[str] = []
    cursor = "1MiB"
    for i, part in enumerate(plan["partitions"], start=1):
        end = str(part["size"]).strip()
        if not end.endswith("%") and not end.lower().endswith("b"):
            end = f"+{end}"
        res = _run(["parted", "-s", disk, "mkpart", "primary", cursor, end], timeout=30)
        if not res.get("ok"):
            return {"ok": False, "error": res.get("stderr") or f"mkpart_{i}_failed", "created": created}
        created.append(f"{disk}{i}")
        cursor = end
    _run(["partprobe", disk], timeout=10)
    _log({"op": "partition", "disk": disk, "table": table, "parts": len(created)})
    return {"ok": True, "disk": disk, "created": created, "scan": scan()}


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "scan").lower().replace("-", "_")
    if action in ("scan", "refresh", "json", "panel"):
        return scan()
    if action == "mount":
        return _mount_udisks(str(body.get("device") or body.get("dev") or ""), True)
    if action == "unmount":
        return _mount_udisks(str(body.get("device") or body.get("dev") or ""), False)
    if action == "format":
        return _format_partition(
            str(body.get("device") or body.get("dev") or ""),
            str(body.get("fstype") or "ext4"),
            confirm=str(body.get("confirm") or ""),
        )
    if action in ("partition_plan", "plan"):
        return _partition_plan(
            str(body.get("disk") or body.get("device") or ""),
            str(body.get("table") or "gpt"),
            body.get("partitions") if isinstance(body.get("partitions"), list) else [],
        )
    if action in ("partition_apply", "partition"):
        return _partition_apply(
            str(body.get("disk") or body.get("device") or ""),
            str(body.get("table") or "gpt"),
            body.get("partitions") if isinstance(body.get("partitions"), list) else [],
            confirm=str(body.get("confirm") or ""),
        )
    return {"ok": False, "error": "unknown_action", "action": action}


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] in ("json", "panel", "scan"):
        print(json.dumps(panel_doc(), ensure_ascii=False, indent=2))
        return 0
    if args[0] == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}))
            return 1
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    if args[0] == "scan":
        print(json.dumps(scan(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps(dispatch({"action": args[0], **dict(zip(args[1::2], args[2::2]))}), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())