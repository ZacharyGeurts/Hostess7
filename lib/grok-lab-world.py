#!/usr/bin/env python3
"""Grok AI Lab — worldwide field node registry, pack, deploy orchestration."""
from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
import tarfile
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
LAB = Path(os.environ.get("GROK_LAB_ROOT", str(INSTALL / "GrokLab")))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
DEPLOY = LAB / "deploy"
NODES_PATH = DEPLOY / "world-nodes.json"
REGISTRY_PATH = STATE / "grok-lab-world-registry.json"
EXAMPLE_NODES = DEPLOY / "world-nodes.example.json"
BUNDLE_DIR = DEPLOY / "dist"
BUNDLE_NAME = "grok-lab-node-bundle.tar.gz"


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


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _ensure_nodes_file() -> Path:
    if not NODES_PATH.is_file() and EXAMPLE_NODES.is_file():
        doc = _load(EXAMPLE_NODES, {})
        local = doc.get("nodes") or []
        for n in local:
            if n.get("id") == "node-local":
                n["enabled"] = True
                n["region"] = n.get("region") or "local"
        _save(NODES_PATH, doc)
    return NODES_PATH


def _hostname() -> str:
    try:
        return socket.gethostname()
    except OSError:
        return "unknown"


def _probe_loopback(port: int = 9477, path: str = "/grok-lab", timeout: float = 3.0) -> dict[str, Any]:
    url = f"http://127.0.0.1:{port}{path}"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return {"ok": resp.status == 200, "http": resp.status, "url": url}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"ok": False, "http": 0, "url": url, "error": str(exc)[:200]}


def register_local_node(*, region: str = "", node_id: str = "") -> dict[str, Any]:
    region = region or os.environ.get("GROK_LAB_NODE_REGION", "local")
    node_id = node_id or os.environ.get("GROK_LAB_NODE_ID") or f"node-{_hostname()}"
    panel = int(os.environ.get("NEXUS_THREAT_PANEL_PORT", "9477"))
    eye = int(os.environ.get("FINAL_EYE_PORT", "9479"))
    grok = _probe_loopback(panel, "/grok-lab")
    field = _probe_loopback(panel, "/field")
    eye_ops = _probe_loopback(eye, "/ops")

    entry = {
        "id": node_id,
        "region": region,
        "provider": "sovereign-host" if region == "local" else os.environ.get("GROK_LAB_NODE_PROVIDER", "field_node"),
        "role": "home_sanctuary" if region == "local" else "field_node",
        "hostname": _hostname(),
        "sanctuary": "127.0.0.1",
        "urls": {
            "grok_lab": f"http://127.0.0.1:{panel}/grok-lab",
            "field": f"http://127.0.0.1:{panel}/field",
            "final_eye": f"http://127.0.0.1:{eye}/ops",
        },
        "health": {"grok_lab": grok, "field": field, "final_eye": eye_ops},
        "ok": grok.get("ok") and field.get("ok"),
        "updated": _now(),
        "world_node": True,
        "perimeter": "the_world",
    }

    reg = _load(REGISTRY_PATH, {"schema": "grok-lab-world-registry/v1", "nodes": []})
    reg.setdefault("schema", "grok-lab-world-registry/v1")
    reg.setdefault("motto", "A new internet everywhere, from each and every home")
    nodes = [n for n in (reg.get("nodes") or []) if n.get("id") != node_id]
    nodes.append(entry)
    reg["nodes"] = nodes
    reg["count"] = len(nodes)
    reg["updated"] = _now()
    _save(REGISTRY_PATH, reg)
    return {"ok": True, "registered": entry, "registry_path": str(REGISTRY_PATH)}


def node_status_all() -> dict[str, Any]:
    _ensure_nodes_file()
    cfg = _load(NODES_PATH, {"nodes": []})
    reg = _load(REGISTRY_PATH, {"nodes": []})
    local_reg = {n["id"]: n for n in reg.get("nodes") or [] if n.get("id")}

    results: list[dict[str, Any]] = []
    for node in cfg.get("nodes") or []:
        if not node.get("enabled", True):
            results.append({**node, "status": "disabled"})
            continue
        nid = str(node.get("id") or "")
        ssh = str(node.get("ssh") or "").strip()
        if not ssh:
            # Local sovereign node
            loc = local_reg.get(nid) or register_local_node(
                region=str(node.get("region") or "local"), node_id=nid
            ).get("registered", {})
            results.append({**node, "status": "local", "health": loc.get("health"), "ok": loc.get("ok")})
            continue
        # Remote probe via SSH curl on loopback (panel + Final Eye stream)
        key = str(node.get("ssh_key") or "").strip()
        port = int(node.get("ssh_port") or 22)
        key_opt = f"-i {os.path.expanduser(key)} " if key else ""
        port_opt = f"-p {port} " if port != 22 else ""
        probe = (
            "g=$(curl -sf -o /dev/null -w %{http_code} http://127.0.0.1:9477/grok-lab 2>/dev/null || echo 000); "
            "e=$(curl -sf -o /dev/null -w %{http_code} http://127.0.0.1:9479/api/health 2>/dev/null || echo 000); "
            "s=$(curl -sf http://127.0.0.1:9479/api/stream/status 2>/dev/null | head -c 120 || echo down); "
            "echo GROK:$g EYE:$e STREAM:$s"
        )
        cmd = (
            f"ssh -o BatchMode=yes -o ConnectTimeout=8 -o StrictHostKeyChecking=accept-new "
            f"{port_opt}{key_opt}{ssh} {probe!r}"
        )
        try:
            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=25)
            out = (proc.stdout or "").strip()
            grok_m = re.search(r"GROK:(\d{3})", out)
            eye_m = re.search(r"EYE:(\d{3})", out)
            stream_m = re.search(r"STREAM:(.+)", out)
            code = grok_m.group(1) if grok_m else "000"
            eye_code = eye_m.group(1) if eye_m else "000"
            stream_snip = (stream_m.group(1) if stream_m else "")[:120]
            ok = code == "200" and eye_code == "200"
            results.append({
                **node,
                "status": "remote",
                "http_grok_lab": code,
                "http_final_eye": eye_code,
                "stream_status": stream_snip,
                "ok": ok,
                "tunnel": node.get("tunnel") or f"ssh -N -L 19477:127.0.0.1:9477 {ssh}",
            })
        except (subprocess.TimeoutExpired, OSError) as exc:
            results.append({**node, "status": "unreachable", "ok": False, "error": str(exc)[:200]})

    live = sum(1 for r in results if r.get("ok"))
    return {
        "schema": "grok-lab-world-status/v1",
        "updated": _now(),
        "motto": cfg.get("motto"),
        "perimeter": "the_world",
        "nodes_total": len(results),
        "nodes_live": live,
        "nodes": results,
        "registry_path": str(REGISTRY_PATH),
        "bundle": str(BUNDLE_DIR / BUNDLE_NAME),
    }


def _pack_kilroy_runtime(stage_nl: Path, nl: Path) -> None:
    """Ship KILROY war package runtime (~260MB), not linux-1.0 source (2.7GB)."""
    import shutil

    src = nl / "KILROY"
    if not src.is_dir() or not (src / "scripts" / "build-kilroy.sh").is_file():
        return
    dest = stage_nl / "KILROY"
    if dest.exists():
        shutil.rmtree(dest)
    for part in ("boot", "dist", "rootfs", "scripts", "data", "kernel", "userspace", "Grok"):
        if (src / part).exists():
            subprocess.run(
                ["rsync", "-a", f"{src / part}/", f"{dest / part}/"],
                check=False,
                timeout=180,
            )
    for extra in ("KILROY.launch", "KILROY_VERSION", "README.md", "FIELD_STATUS.md"):
        if (src / extra).is_file():
            shutil.copy2(src / extra, dest / extra)


def _pack_grok16_runtime(stage_nl: Path, nl: Path) -> None:
    """Ship Grok16 python driver + libs (~380MB), not gcc/dist/vendor (20GB+)."""
    import shutil

    src = nl / "Grok16"
    if not src.is_dir():
        return
    dest = stage_nl / "Grok16"
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    for part in ("python", "data", "lib", "lib64", "share"):
        if (src / part).is_dir():
            subprocess.run(
                ["rsync", "-a", f"{src / part}/", f"{dest / part}/"],
                check=False,
                timeout=120,
            )
    if (src / "libexec" / "grok16").is_dir():
        (dest / "libexec").mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["rsync", "-a", f"{src / 'libexec' / 'grok16'}/", f"{dest / 'libexec' / 'grok16'}/"],
            check=False,
            timeout=120,
        )
    (dest / "bin").mkdir(parents=True, exist_ok=True)
    for script in sorted((src / "bin").glob("g*")):
        if script.is_file() and script.stat().st_size < 512_000:
            shutil.copy2(script, dest / "bin" / script.name)
            if script.stat().st_mode & 0o111:
                (dest / "bin" / script.name).chmod(script.stat().st_mode)
    gpy = dest / "bin" / "gpy-16"
    if gpy.is_file():
        pythong = dest / "bin" / "pythong"
        if pythong.exists() or pythong.is_symlink():
            pythong.unlink()
        pythong.symlink_to("gpy-16")


def _slim_pack_excludes() -> list[str]:
    """Exclude heavy/local-only trees; Grok16 runtime packed separately."""
    return [
        ".git", ".nexus-state", "__pycache__", "*.pyc", "*.pyo",
        # Recursive dist/cache (GrokLab/deploy/dist was 25GB in prior packs)
        "dist", "*/dist", "GrokLab/deploy/dist", "GrokLab/deploy/stage",
        "GrokLab/deploy/qemu-vms", "cache", "*/cache",
        # Grok16 bulk toolchain — runtime re-packed via _pack_grok16_runtime
        "Grok16",
        # Local-only heavy stacks
        "compat", "AMOURANTHRTX", "OBS-Field", "OBS-FieldVoiceFilter",
        "GIMP", "GIMP-Field", "linux-kernel", "Hostess7", "KILROY",
        "Field_Primer", "Field_Research", "Kill-Grok-Orphans", "AmmoCode",
        "Textbook", "library", ".nexus-field-drive", ".pages-hub-*",
        # Queen browser/RTX payloads
        "Queen/vendor", "Queen/.venv*", "Queen/build", "Queen/world",
        "Queen/field", "Queen/field-gecko",
        # Final Eye media/cache (virtual eye on VMs)
        "Final_Eye/cache", "Final_Eye/releases", "Final_Eye/*.log",
        "Final_Eye/amouranth_engine.log",
    ]


def pack_node_bundle(*, slim: bool = True) -> dict[str, Any]:
    """Pack portable SG/NewLatest tree for free VM deploy."""
    sg = Path(os.environ.get("SG_ROOT", str(INSTALL.parent)))
    nl = INSTALL if INSTALL.is_dir() else sg / "NewLatest"
    if not nl.is_dir():
        return {"ok": False, "error": f"missing install root {nl}"}

    BUNDLE_DIR.mkdir(parents=True, exist_ok=True)
    stage = BUNDLE_DIR / "stage"
    if stage.exists():
        import shutil
        shutil.rmtree(stage)
    stage.mkdir(parents=True)

    excludes = _slim_pack_excludes() if slim else [
        ".git", ".nexus-state", "dist", "cache", "__pycache__", "*.pyc",
        "Hostess7/cache", "Queen/vendor", "Queen/.venv*", "KILROY/linux-1.0",
        "GrokLab/deploy/dist", "GrokLab/deploy/stage", "GrokLab/deploy/qemu-vms",
    ]
    rsync_cmd = ["rsync", "-a", "--delete", "--no-perms", "--no-owner", "--no-group"]
    for ex in excludes:
        rsync_cmd.extend(["--exclude", ex])

    # Ship SG layout: NewLatest (slim) — siblings already under NL when wired
    dest_sg = stage
    dest_sg.mkdir(parents=True, exist_ok=True)
    rsync_cmd_nl = rsync_cmd + [f"{nl}/", f"{dest_sg}/NewLatest/"]
    proc = subprocess.run(rsync_cmd_nl, capture_output=True, text=True, check=False, timeout=600)
    if proc.returncode != 0 and proc.stderr:
        # Permission errors on sealed paths should not block slim pack
        if "Permission denied" not in proc.stderr and proc.returncode > 1:
            return {"ok": False, "error": proc.stderr[-400:], "stage": str(stage)}

    if slim:
        _pack_grok16_runtime(dest_sg / "NewLatest", nl)
        _pack_kilroy_runtime(dest_sg / "NewLatest", nl)

    if not slim:
        for name in ("Final_Eye", "Final_Ear", "Grok16", "KILROY", "Queen", "GrokLab"):
            src = sg / name
            if src.is_dir() and not (dest_sg / "NewLatest" / name).exists():
                link_dest = dest_sg / "NewLatest" / name
                rsync_cmd_s = rsync_cmd + [f"{src}/", f"{link_dest}/"]
                subprocess.run(rsync_cmd_s, check=False, timeout=300)

    bundle = BUNDLE_DIR / BUNDLE_NAME
    if bundle.exists():
        bundle.unlink()
    with tarfile.open(bundle, "w:gz") as tar:
        tar.add(stage, arcname="ammoos")

    size = bundle.stat().st_size if bundle.is_file() else 0
    manifest = {
        "schema": "grok-lab-node-bundle/v1",
        "updated": _now(),
        "slim": slim,
        "bundle": str(bundle),
        "size_bytes": size,
        "size_mb": round(size / (1024 * 1024), 2),
        "install_path": "/opt/ammoos",
        "bootstrap": "NewLatest/GrokLab/deploy/world-node-bootstrap.sh",
        "cloud_init": "NewLatest/GrokLab/deploy/cloud-init-world-node.yaml",
    }
    _save(BUNDLE_DIR / "bundle-manifest.json", manifest)
    return {"ok": True, **manifest}


def deploy_remote_node(node: dict[str, Any], bundle: Path) -> dict[str, Any]:
    ssh = str(node.get("ssh") or "").strip()
    if not ssh:
        return {"ok": False, "error": "no_ssh_target", "node": node.get("id")}
    key = str(node.get("ssh_key") or "").strip()
    port = int(node.get("ssh_port") or 22)
    port_opt = f"-P {port} " if port != 22 else ""
    key_opt = f"-i {os.path.expanduser(key)} " if key else ""
    ssh_port_opt = f"-p {port} " if port != 22 else ""
    nid = str(node.get("id") or "node")
    region = str(node.get("region") or "unknown")
    remote_root = "/opt/ammoos"

    if not bundle.is_file():
        return {"ok": False, "error": "bundle_missing", "bundle": str(bundle)}

    ssh_opts = "-o BatchMode=yes -o ConnectTimeout=15 -o StrictHostKeyChecking=accept-new"
    scp = f"scp {ssh_opts} {port_opt}{key_opt}{bundle} {ssh}:/tmp/{BUNDLE_NAME}"
    subprocess.run(scp, shell=True, check=True, timeout=600)

    remote_script = f"""set -e
sudo apt-get update -qq 2>/dev/null || true
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3 python3-pip curl tesseract-ocr 2>/dev/null || true
python3 -m pip install --user -q Pillow numpy cryptography 2>/dev/null || python3 -m pip install --user --break-system-packages -q Pillow numpy cryptography 2>/dev/null || true
sudo mkdir -p {remote_root} && sudo chown $(whoami):$(whoami) {remote_root}
tar -xzf /tmp/{BUNDLE_NAME} -C {remote_root}
cd {remote_root}/ammoos/NewLatest
export SG_ROOT={remote_root}/ammoos
export NEXUS_INSTALL_ROOT={remote_root}/ammoos/NewLatest
export NEXUS_STATE_DIR={remote_root}/ammoos/NewLatest/.nexus-state
export GROK_LAB_PY=python3
export GROK_LAB_NODE_ID={nid}
export GROK_LAB_NODE_REGION={region}
export GROK_LAB_NODE_PROVIDER={node.get('provider', 'field_node')}
export GROK_LAB_RELEASE_EYE=1
export ZOCR_VIRTUAL_EYE=1
export ZOCR_PREFER=virtual
export QUEEN_SKIP_RTX_BOOT=1
export NEXUS_FIELD_LAUNCH_BROWSER=0
bash GrokLab/deploy/world-node-bootstrap.sh --installed --region {region} --node-id {nid}
curl -sf -o /dev/null -w 'grok:%{{http_code}}\\n' http://127.0.0.1:9477/grok-lab || echo grok:000
curl -sf -o /dev/null -w 'eye:%{{http_code}}\\n' http://127.0.0.1:9479/api/health || echo eye:000
curl -sf http://127.0.0.1:9479/api/stream/status 2>/dev/null | head -c 300 || echo stream:down
"""
    ssh_base = f"ssh {ssh_opts} {ssh_port_opt}{key_opt}{ssh}"
    proc = subprocess.run(
        [*ssh_base.split(), "bash", "-s"],
        input=remote_script,
        capture_output=True,
        text=True,
        timeout=600,
    )
    tail = (proc.stdout or proc.stderr or "")[-500:]
    code = "000"
    for line in reversed((proc.stdout or "").splitlines()):
        line = line.strip()
        if re.fullmatch(r"\d{3}", line):
            code = line
            break
    return {
        "ok": proc.returncode == 0 and code == "200",
        "node": nid,
        "region": region,
        "ssh": ssh,
        "http_grok_lab": code,
        "returncode": proc.returncode,
        "tail": tail,
    }


def deploy_all(*, pack_first: bool | None = None) -> dict[str, Any]:
    _ensure_nodes_file()
    cfg = _load(NODES_PATH, {})
    bundle = BUNDLE_DIR / BUNDLE_NAME
    if pack_first is None:
        skip = os.environ.get("GROK_LAB_SKIP_PACK", "").strip() in ("1", "yes", "true")
        pack_first = not skip and not bundle.is_file()
    if pack_first:
        pack = pack_node_bundle()
        if not pack.get("ok"):
            return pack
    results: list[dict[str, Any]] = []
    for node in cfg.get("nodes") or []:
        if not node.get("enabled"):
            continue
        if not str(node.get("ssh") or "").strip():
            reg = register_local_node(
                region=str(node.get("region") or "local"),
                node_id=str(node.get("id") or "node-local"),
            )
            results.append({"ok": reg.get("ok"), "node": node.get("id"), "mode": "local", **reg})
            continue
        try:
            results.append(deploy_remote_node(node, bundle))
        except (subprocess.CalledProcessError, OSError) as exc:
            results.append({"ok": False, "node": node.get("id"), "error": str(exc)[:300]})

    live = sum(1 for r in results if r.get("ok"))
    out = {
        "schema": "grok-lab-world-deploy/v1",
        "updated": _now(),
        "nodes_deployed": len(results),
        "nodes_live": live,
        "results": results,
        "bundle": str(bundle),
    }
    _save(STATE / "grok-lab-world-deploy-last.json", out)
    return out


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip().lower().replace("-", "_")
    if cmd in ("status", "json"):
        print(json.dumps(node_status_all(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "register_local":
        print(json.dumps(register_local_node(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "pack":
        print(json.dumps(pack_node_bundle(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("deploy", "deploy_all"):
        print(json.dumps(deploy_all(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: grok-lab-world.py [status|pack|deploy|register-local]"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())