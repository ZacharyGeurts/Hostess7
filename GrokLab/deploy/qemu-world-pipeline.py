#!/usr/bin/env python3
"""Rolling 3-QEMU pipeline — keep 3 VMs active until all 30 geographic nodes are set up."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEPLOY = Path(__file__).resolve().parent
REGIONS = DEPLOY / "world-node-regions.json"
PROVISIONED = DEPLOY / ".qemu-provisioned.json"
STATE_PATH = DEPLOY / ".qemu-pipeline-state.json"
LOG_PATH = Path(
    os.environ.get(
        "WORLD_PIPELINE_LOG",
        str(DEPLOY.parent.parent / ".nexus-state" / "world-pipeline.log"),
    )
)
SSH_KEY = os.environ.get("GROK_LAB_SSH_KEY", str(DEPLOY / "world-ssh" / "id_ed25519"))
NL = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(DEPLOY.parent.parent)))
VERIFY_SEC = int(os.environ.get("WORLD_PIPELINE_VERIFY_SEC", "360"))
REBOOT_SSH_SEC = int(os.environ.get("WORLD_PIPELINE_REBOOT_SSH_SEC", "180"))

SLOTS = [
    {"slot": 0, "port": 2222, "tunnel": 19477},
    {"slot": 1, "port": 2223, "tunnel": 19478},
    {"slot": 2, "port": 2224, "tunnel": 19479},
]

# Loopback slots rotate VMs — host keys change; never use pinned known_hosts.
SSH_SLOT_OPTS = [
    "-o",
    "BatchMode=yes",
    "-o",
    "ConnectTimeout=2",
    "-o",
    "StrictHostKeyChecking=no",
    "-o",
    "UserKnownHostsFile=/dev/null",
    "-o",
    "LogLevel=ERROR",
]

_lock = threading.Lock()
_state: dict[str, Any] = {}
_queue: deque[dict[str, Any]] = deque()


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(msg: str) -> None:
    line = f"[{_ts()}] [pipeline] {msg}"
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    # When stdout is redirected (nohup >> log), printing would duplicate the file write.
    if sys.stdout.isatty():
        print(line, flush=True)


def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _save_state() -> None:
    with _lock:
        snap = json.loads(json.dumps(_state))
    snap["updated"] = _ts()
    STATE_PATH.write_text(json.dumps(snap, indent=2) + "\n", encoding="utf-8")


def _provisioned_ids() -> set[str]:
    doc = _load_json(PROVISIONED, {})
    return set(doc.get("provisioned") or [])


def _mark_provisioned(node_id: str) -> None:
    ids = _provisioned_ids()
    ids.add(node_id)
    doc = {
        "schema": "grok-lab-qemu-provisioned/v1",
        "updated": _ts(),
        "provisioned": sorted(ids),
        "count": len(ids),
        "target": 30,
    }
    PROVISIONED.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    subprocess.run(
        [sys.executable, str(DEPLOY / "world-nodes-sync.py"), "sync"],
        check=False,
        capture_output=True,
    )


def _init_queue() -> None:
    regions = _load_json(REGIONS, {})
    done = _provisioned_ids()
    pending = [n for n in regions.get("nodes") or [] if n.get("id") not in done]
    _queue.clear()
    _queue.extend(pending)
    _state.update(
        {
            "schema": "grok-lab-qemu-pipeline/v1",
            "running": True,
            "slots": SLOTS,
            "pending": len(_queue),
            "completed": len(done),
            "target": 30,
            "slot_status": {str(s["slot"]): {"state": "idle", "node": None} for s in SLOTS},
            "log": str(LOG_PATH),
        }
    )
    _save_state()


def _set_slot(slot: int, *, state: str, node: dict[str, Any] | None = None, extra: dict | None = None) -> None:
    with _lock:
        entry: dict[str, Any] = {
            "state": state,
            "node_id": node.get("id") if node else None,
            "region": node.get("region") if node else None,
            "city": node.get("city") if node else None,
            "port": SLOTS[slot]["port"],
            "since": _ts(),
        }
        if extra:
            entry.update(extra)
        _state["slot_status"][str(slot)] = entry
        _state["pending"] = len(_queue)
        _state["completed"] = len(_provisioned_ids())
    _save_state()


def _pop_next() -> dict[str, Any] | None:
    with _lock:
        if not _queue:
            return None
        return _queue.popleft()


def _run(cmd: list[str], *, timeout: int = 3600) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        return subprocess.CompletedProcess(
            cmd,
            returncode=124,
            stdout=(exc.stdout or b"").decode() if isinstance(exc.stdout, bytes) else (exc.stdout or ""),
            stderr=(exc.stderr or b"").decode() if isinstance(exc.stderr, bytes) else (exc.stderr or ""),
        )


def _clear_slot_host_key(port: int) -> None:
    subprocess.run(
        ["ssh-keygen", "-f", f"{Path.home()}/.ssh/known_hosts", "-R", f"[127.0.0.1]:{port}"],
        capture_output=True,
        check=False,
    )


def _wait_ssh(port: int, timeout: int = 120) -> bool:
    _clear_slot_host_key(port)
    for _ in range(timeout // 2):
        r = _run(
            [
                "ssh",
                *SSH_SLOT_OPTS,
                "-p",
                str(port),
                "-i",
                SSH_KEY,
                "ubuntu@127.0.0.1",
                "echo",
                "ready",
            ],
            timeout=10,
        )
        if r.returncode == 0 and "ready" in (r.stdout or ""):
            return True
        time.sleep(2)
    return False


def _ssh_cmd(port: int, remote: str, *, connect_timeout: int = 4) -> list[str]:
    return [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        f"ConnectTimeout={connect_timeout}",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "-o",
        "LogLevel=ERROR",
        "-p",
        str(port),
        "-i",
        SSH_KEY,
        "ubuntu@127.0.0.1",
        remote,
    ]


def _trigger_panel_boot(port: int) -> None:
    rb = "/opt/ammoos/ammoos/NewLatest/GrokLab/deploy/world-node-c2-kilroy-boot.sh"
    _run(
        _ssh_cmd(
            port,
            f"sudo systemctl start nexus-c2-kilroy.service 2>/dev/null; "
            f"test -x {rb} && AML_BUILD=0 bash {rb} >/dev/null 2>&1 || true",
            connect_timeout=8,
        ),
        timeout=30,
    )


def _verify_panel(port: int, timeout: int | None = None) -> bool:
    limit = timeout if timeout is not None else VERIFY_SEC
    boot_nudged = False
    for i in range(max(1, limit // 5)):
        r = _run(
            _ssh_cmd(
                port,
                "curl -sf -o /dev/null -w '%{http_code}' "
                "http://127.0.0.1:9477/field 2>/dev/null || echo 000",
            ),
            timeout=20,
        )
        code = (r.stdout or "").strip()
        if code == "200":
            return True
        if not boot_nudged and i >= 6:
            boot_nudged = True
            _trigger_panel_boot(port)
        time.sleep(5)
    return False


def _slot_worker(slot: int) -> None:
    port = SLOTS[slot]["port"]
    while True:
        node = _pop_next()
        if node is None:
            _set_slot(slot, state="idle", node=None)
            _log(f"slot {slot} idle — queue empty")
            return

        try:
            nid = node["id"]
            region = node["region"]
            mem = int(node.get("mem_mb") or 1024)

            _set_slot(slot, state="launching", node=node)
            _log(f"slot {slot} :{port} launching {nid} ({region})")

            r = _run(
                [
                    "bash",
                    str(DEPLOY / "qemu-world-launch-one.sh"),
                    nid,
                    region,
                    str(port),
                    str(mem),
                ],
                timeout=300,
            )
            if r.returncode != 0:
                _log(f"slot {slot} LAUNCH FAIL {nid}: {(r.stderr or r.stdout)[-200:]}")
                _set_slot(slot, state="error", node=node, extra={"error": "launch_failed"})
                with _lock:
                    _queue.appendleft(node)
                time.sleep(5)
                continue

            _set_slot(slot, state="ssh_wait", node=node)
            if not _wait_ssh(port):
                _log(f"slot {slot} SSH TIMEOUT {nid}")
                _run(["bash", str(DEPLOY / "qemu-world-stop-one.sh"), nid], timeout=60)
                _set_slot(slot, state="error", node=node, extra={"error": "ssh_timeout"})
                with _lock:
                    _queue.appendleft(node)
                continue

            _set_slot(slot, state="deploying", node=node)
            _log(f"slot {slot} deploying {nid}")
            r = _run(
                [
                    "bash",
                    str(DEPLOY / "world-node-c2-kilroy-war-deploy.sh"),
                    str(port),
                    nid,
                    region,
                ],
                timeout=3600,
            )
            deploy_ok = r.returncode == 0
            if not deploy_ok:
                chk = _run(
                    _ssh_cmd(
                        port,
                        "test -f /opt/ammoos/ammoos/NewLatest/lib/field-war-hardening.sh",
                        connect_timeout=8,
                    ),
                    timeout=20,
                )
                deploy_ok = chk.returncode == 0

            _set_slot(slot, state="reboot_wait", node=node)
            _log(f"slot {slot} waiting post-reboot SSH on {nid} (up to {REBOOT_SSH_SEC}s)")
            _clear_slot_host_key(port)
            if not _wait_ssh(port, timeout=REBOOT_SSH_SEC):
                _log(f"slot {slot} REBOOT SSH TIMEOUT {nid}")
                if deploy_ok:
                    _mark_provisioned(nid)
                    _set_slot(slot, state="complete", node=node, extra={"verified": False, "reboot_ssh": False})
                else:
                    _set_slot(slot, state="error", node=node, extra={"error": "reboot_ssh_timeout"})
                    with _lock:
                        _queue.appendleft(node)
                _run(["bash", str(DEPLOY / "qemu-world-stop-one.sh"), nid], timeout=60)
                _set_slot(slot, state="idle", node=None)
                time.sleep(1)
                continue

            _set_slot(slot, state="verifying", node=node)
            _log(f"slot {slot} verifying {nid} panel (up to {VERIFY_SEC}s)")
            verified = _verify_panel(port)

            if verified and deploy_ok:
                _mark_provisioned(nid)
                _set_slot(slot, state="complete", node=node, extra={"verified": True})
                _log(f"slot {slot} DONE {nid} — {len(_provisioned_ids())}/30")
            else:
                _log(f"slot {slot} VERIFY WARN {nid} deploy_ok={deploy_ok} panel={verified}")
                if deploy_ok:
                    _mark_provisioned(nid)
                    _set_slot(slot, state="complete", node=node, extra={"verified": False})
                else:
                    _set_slot(slot, state="error", node=node, extra={"error": "deploy_failed"})
                    with _lock:
                        _queue.appendleft(node)

            _run(["bash", str(DEPLOY / "qemu-world-stop-one.sh"), nid], timeout=60)
            _set_slot(slot, state="idle", node=None)
            time.sleep(1)
        except Exception as exc:  # noqa: BLE001 — keep slot alive after transient failures
            nid = node.get("id", "?")
            _log(f"slot {slot} UNHANDLED {nid} {type(exc).__name__}: {exc}")
            _run(["bash", str(DEPLOY / "qemu-world-stop-one.sh"), nid], timeout=60)
            _set_slot(slot, state="error", node=node, extra={"error": type(exc).__name__})
            with _lock:
                _queue.appendleft(node)
            time.sleep(5)


def run_pipeline() -> dict[str, Any]:
    pid_path = DEPLOY.parent.parent / ".nexus-state" / "world-pipeline.pid"
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    pid_path.write_text(f"{os.getpid()}\n", encoding="utf-8")
    _init_queue()
    if not _queue:
        _state["running"] = False
        _save_state()
        return {"ok": True, "message": "all 30 nodes already provisioned", "completed": 30}

    _log(f"pipeline start — {_state['pending']} pending, 3 slots active")
    threads = [threading.Thread(target=_slot_worker, args=(s["slot"],), daemon=True) for s in SLOTS]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    with _lock:
        _state["running"] = False
        _state["completed"] = len(_provisioned_ids())
        _state["pending"] = len(_queue)
    _save_state()
    _log(f"pipeline finished — {_state['completed']}/30 provisioned")
    return {"ok": True, "completed": _state["completed"], "remaining": len(_queue)}


def show_status() -> dict[str, Any]:
    st = _load_json(STATE_PATH, {})
    prov = _load_json(PROVISIONED, {})
    if not st:
        return {
            "ok": True,
            "running": False,
            "completed": prov.get("count", len(prov.get("provisioned") or [])),
            "target": 30,
            "message": "pipeline not started — run: qemu-world-pipeline.py run",
        }
    st["completed"] = prov.get("count", len(prov.get("provisioned") or []))
    st["provisioned"] = prov.get("provisioned") or []
    return st


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip().lower()
    if cmd == "run":
        print(json.dumps(run_pipeline(), indent=2))
        return 0
    if cmd == "status":
        print(json.dumps(show_status(), indent=2))
        return 0
    if cmd == "watch":
        try:
            while True:
                os.system("clear")  # noqa: S605
                print(json.dumps(show_status(), indent=2))
                st = show_status()
                if not st.get("running") and st.get("completed", 0) >= 30:
                    break
                time.sleep(5)
        except KeyboardInterrupt:
            pass
        return 0
    print("usage: qemu-world-pipeline.py [run|status|watch]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())