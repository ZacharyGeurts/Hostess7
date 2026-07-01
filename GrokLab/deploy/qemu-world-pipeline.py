#!/usr/bin/env python3
"""Rolling 3-QEMU pipeline — deploy 3 at a time, optional fast reboot + deferred check pass."""
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
STAGED = DEPLOY / ".qemu-staged.json"
STATE_PATH = DEPLOY / ".qemu-pipeline-state.json"
LOG_PATH = Path(
    os.environ.get(
        "WORLD_PIPELINE_LOG",
        str(DEPLOY.parent.parent / ".nexus-state" / "world-pipeline.log"),
    )
)
SSH_KEY = os.environ.get("GROK_LAB_SSH_KEY", str(DEPLOY / "world-ssh" / "id_ed25519"))
NL = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(DEPLOY.parent.parent)))
VERIFY_SEC = int(os.environ.get("WORLD_PIPELINE_VERIFY_SEC", "120"))
REBOOT_SSH_SEC = int(os.environ.get("WORLD_PIPELINE_REBOOT_SSH_SEC", "180"))
# Fast path: deploy+reboot fire-and-forget, then second pass for panel checks (default on).
FAST_DEPLOY = os.environ.get("WORLD_PIPELINE_FAST", "1") != "0"

SLOTS = [
    {"slot": 0, "port": 2222, "tunnel": 19477},
    {"slot": 1, "port": 2223, "tunnel": 19478},
    {"slot": 2, "port": 2224, "tunnel": 19479},
]

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
_check_queue: deque[dict[str, Any]] = deque()


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(msg: str) -> None:
    line = f"[{_ts()}] [pipeline] {msg}"
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    if sys.stdout.isatty():
        print(line, flush=True)


def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _target() -> int:
    regions = _load_json(REGIONS, {})
    return int(regions.get("target_geographic_nodes") or len(regions.get("nodes") or []) or 30)


def _save_state() -> None:
    with _lock:
        snap = json.loads(json.dumps(_state))
    snap["updated"] = _ts()
    STATE_PATH.write_text(json.dumps(snap, indent=2) + "\n", encoding="utf-8")


def _provisioned_ids() -> set[str]:
    doc = _load_json(PROVISIONED, {})
    return set(doc.get("provisioned") or [])


def _staged_ids() -> set[str]:
    doc = _load_json(STAGED, {})
    return set(doc.get("staged") or [])


def _mark_provisioned(node_id: str) -> None:
    ids = _provisioned_ids()
    ids.add(node_id)
    staged = _staged_ids()
    staged.discard(node_id)
    doc = {
        "schema": "grok-lab-qemu-provisioned/v1",
        "updated": _ts(),
        "provisioned": sorted(ids),
        "count": len(ids),
        "target": _target(),
    }
    PROVISIONED.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    STAGED.write_text(
        json.dumps(
            {
                "schema": "grok-lab-qemu-staged/v1",
                "updated": _ts(),
                "staged": sorted(staged),
                "count": len(staged),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    subprocess.run(
        [sys.executable, str(DEPLOY / "world-nodes-sync.py"), "sync"],
        check=False,
        capture_output=True,
    )


def _mark_staged(node_id: str) -> None:
    ids = _staged_ids()
    ids.add(node_id)
    STAGED.write_text(
        json.dumps(
            {
                "schema": "grok-lab-qemu-staged/v1",
                "updated": _ts(),
                "staged": sorted(ids),
                "count": len(ids),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _all_region_nodes() -> list[dict[str, Any]]:
    return list(_load_json(REGIONS, {}).get("nodes") or [])


def _node_by_id(node_id: str) -> dict[str, Any] | None:
    for n in _all_region_nodes():
        if n.get("id") == node_id:
            return n
    return None


def _init_queue() -> None:
    regions = _load_json(REGIONS, {})
    done = _provisioned_ids()
    staged = _staged_ids()
    pending = [
        n
        for n in regions.get("nodes") or []
        if n.get("id") not in done and n.get("id") not in staged
    ]
    _queue.clear()
    _queue.extend(pending)
    tgt = _target()
    _state.update(
        {
            "schema": "grok-lab-qemu-pipeline/v2",
            "running": True,
            "fast_deploy": FAST_DEPLOY,
            "phase": "deploy",
            "slots": SLOTS,
            "pending": len(_queue),
            "staged": len(staged),
            "completed": len(done),
            "target": tgt,
            "slot_status": {str(s["slot"]): {"state": "idle", "node": None} for s in SLOTS},
            "log": str(LOG_PATH),
        }
    )
    _save_state()


def _init_check_queue() -> None:
    done = _provisioned_ids()
    staged = _staged_ids()
    need = [n for n in _all_region_nodes() if n.get("id") in staged and n.get("id") not in done]
    _check_queue.clear()
    _check_queue.extend(need)
    with _lock:
        _state["phase"] = "check"
        _state["pending_check"] = len(_check_queue)
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
        _state["staged"] = len(_staged_ids())
        _state["completed"] = len(_provisioned_ids())
    _save_state()


def _pop_next(q: deque[dict[str, Any]]) -> dict[str, Any] | None:
    with _lock:
        if not q:
            return None
        return q.popleft()


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


def _deploy_ok(port: int, deploy_rc: int) -> bool:
    if deploy_rc == 0:
        return True
    chk = _run(
        _ssh_cmd(
            port,
            "test -f /opt/ammoos/ammoos/NewLatest/lib/field-war-hardening.sh",
            connect_timeout=8,
        ),
        timeout=20,
    )
    return chk.returncode == 0


def _trigger_panel_boot(port: int) -> None:
    ensure = "/opt/ammoos/ammoos/NewLatest/GrokLab/deploy/world-node-panel-ensure.sh"
    boot = "/opt/ammoos/ammoos/NewLatest/GrokLab/deploy/world-node-c2-kilroy-boot.sh"
    _run(
        _ssh_cmd(
            port,
            f"sudo systemctl start nexus-c2-kilroy.service 2>/dev/null; "
            f"sudo systemctl start nexus-panel.service 2>/dev/null; "
            f"test -x {ensure} && GROK_LAB_WORLD_NODE=1 AML_BUILD=0 bash {ensure} >/dev/null 2>&1 || "
            f"(test -x {boot} && AML_BUILD=0 bash {boot} >/dev/null 2>&1) || true",
            connect_timeout=8,
        ),
        timeout=45,
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
        if not boot_nudged and i >= 4:
            boot_nudged = True
            _trigger_panel_boot(port)
        time.sleep(5)
    return False


def _stop_vm(nid: str) -> None:
    _run(["bash", str(DEPLOY / "qemu-world-stop-one.sh"), nid], timeout=60)


def _finish_node(
    slot: int,
    node: dict[str, Any],
    *,
    deploy_ok: bool,
    verified: bool | None = None,
    fast: bool = False,
) -> None:
    nid = node["id"]
    tgt = _target()
    if deploy_ok and fast:
        _mark_staged(nid)
        _set_slot(slot, state="staged", node=node, extra={"verified": False})
        _log(f"slot {slot} STAGED {nid} — reboot fire-and-forget ({len(_staged_ids())} staged, {len(_provisioned_ids())}/{tgt} done)")
    elif deploy_ok and verified:
        _mark_provisioned(nid)
        _set_slot(slot, state="complete", node=node, extra={"verified": True})
        _log(f"slot {slot} DONE {nid} — {len(_provisioned_ids())}/{tgt}")
    elif deploy_ok:
        _mark_provisioned(nid)
        _set_slot(slot, state="complete", node=node, extra={"verified": bool(verified)})
        _log(f"slot {slot} DONE {nid} (panel={'ok' if verified else 'warn'}) — {len(_provisioned_ids())}/{tgt}")
    else:
        _set_slot(slot, state="error", node=node, extra={"error": "deploy_failed"})
        with _lock:
            _queue.appendleft(node)
    _stop_vm(nid)
    _set_slot(slot, state="idle", node=None)
    time.sleep(1)


def _slot_worker(slot: int) -> None:
    port = SLOTS[slot]["port"]
    while True:
        node = _pop_next(_queue)
        if node is None:
            _set_slot(slot, state="idle", node=None)
            _log(f"slot {slot} idle — deploy queue empty")
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
                _stop_vm(nid)
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
            deploy_ok = _deploy_ok(port, r.returncode)

            if FAST_DEPLOY and deploy_ok:
                _log(f"slot {slot} deploy sent reboot for {nid} — not waiting")
                time.sleep(3)
                _finish_node(slot, node, deploy_ok=True, fast=True)
                continue

            _set_slot(slot, state="reboot_wait", node=node)
            _log(f"slot {slot} waiting post-reboot SSH on {nid} (up to {REBOOT_SSH_SEC}s)")
            _clear_slot_host_key(port)
            if not _wait_ssh(port, timeout=REBOOT_SSH_SEC):
                _log(f"slot {slot} REBOOT SSH TIMEOUT {nid}")
                if deploy_ok:
                    _finish_node(slot, node, deploy_ok=True, verified=False)
                else:
                    _stop_vm(nid)
                    _set_slot(slot, state="error", node=node, extra={"error": "reboot_ssh_timeout"})
                    with _lock:
                        _queue.appendleft(node)
                continue

            _set_slot(slot, state="verifying", node=node)
            _log(f"slot {slot} verifying {nid} panel (up to {VERIFY_SEC}s)")
            verified = _verify_panel(port)
            if not verified:
                _log(f"slot {slot} VERIFY WARN {nid} deploy_ok={deploy_ok}")
            _finish_node(slot, node, deploy_ok=deploy_ok, verified=verified)

        except Exception as exc:  # noqa: BLE001
            nid = node.get("id", "?")
            _log(f"slot {slot} UNHANDLED {nid} {type(exc).__name__}: {exc}")
            _stop_vm(nid)
            _set_slot(slot, state="error", node=node, extra={"error": type(exc).__name__})
            with _lock:
                _queue.appendleft(node)
            time.sleep(5)


def _check_worker(slot: int) -> None:
    port = SLOTS[slot]["port"]
    while True:
        node = _pop_next(_check_queue)
        if node is None:
            _set_slot(slot, state="idle", node=None)
            _log(f"slot {slot} idle — check queue empty")
            return

        try:
            nid = node["id"]
            region = node["region"]
            mem = int(node.get("mem_mb") or 1024)

            _set_slot(slot, state="check_launch", node=node)
            _log(f"slot {slot} check-pass launching {nid}")

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
                _log(f"slot {slot} CHECK LAUNCH FAIL {nid}")
                with _lock:
                    _check_queue.appendleft(node)
                time.sleep(5)
                continue

            _set_slot(slot, state="check_ssh", node=node)
            if not _wait_ssh(port, timeout=REBOOT_SSH_SEC):
                _log(f"slot {slot} CHECK SSH TIMEOUT {nid}")
                _stop_vm(nid)
                with _lock:
                    _check_queue.appendleft(node)
                continue

            _set_slot(slot, state="check_verify", node=node)
            _trigger_panel_boot(port)
            verified = _verify_panel(port)
            deploy_ok = _deploy_ok(port, 0)
            if deploy_ok:
                _finish_node(slot, node, deploy_ok=True, verified=verified)
            else:
                _log(f"slot {slot} CHECK FAIL {nid} — tree missing, re-stage for deploy")
                staged = _staged_ids()
                staged.discard(nid)
                STAGED.write_text(
                    json.dumps({"schema": "grok-lab-qemu-staged/v1", "staged": sorted(staged), "count": len(staged)}, indent=2) + "\n",
                    encoding="utf-8",
                )
                with _lock:
                    _queue.appendleft(node)
                _stop_vm(nid)

        except Exception as exc:  # noqa: BLE001
            _log(f"slot {slot} CHECK UNHANDLED {node.get('id')} {exc}")
            _stop_vm(node.get("id", ""))
            with _lock:
                _check_queue.appendleft(node)
            time.sleep(5)


def _run_slot_pool(worker, label: str) -> None:
    _log(f"{label} — 3 slots active")
    threads = [threading.Thread(target=worker, args=(s["slot"],), daemon=True) for s in SLOTS]
    for t in threads:
        t.start()
    for t in threads:
        t.join()


def run_pipeline() -> dict[str, Any]:
    pid_path = DEPLOY.parent.parent / ".nexus-state" / "world-pipeline.pid"
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    pid_path.write_text(f"{os.getpid()}\n", encoding="utf-8")
    tgt = _target()
    _init_queue()

    if not _queue and not (_staged_ids() - _provisioned_ids()):
        _state["running"] = False
        _save_state()
        return {"ok": True, "message": f"all {tgt} nodes already provisioned", "completed": len(_provisioned_ids())}

    mode = "fast deploy+check" if FAST_DEPLOY else "deploy+inline-verify"
    _log(f"pipeline start — {_state['pending']} to deploy, {len(_staged_ids())} staged, target {tgt} ({mode})")

    ensure = DEPLOY / "world-node-panel-ensure.sh"
    if ensure.is_file():
        r = _run(["bash", str(ensure)], timeout=60)
        if r.returncode == 0:
            _log("local sanctuary panel :9477 ready")

    if _queue:
        _run_slot_pool(_slot_worker, "deploy phase")

    if FAST_DEPLOY:
        _init_check_queue()
        if _check_queue:
            _run_slot_pool(_check_worker, "check phase")

    with _lock:
        _state["running"] = False
        _state["completed"] = len(_provisioned_ids())
        _state["pending"] = len(_queue)
        _state["staged"] = len(_staged_ids() - _provisioned_ids())
    _save_state()
    done = len(_provisioned_ids())
    _log(f"pipeline finished — {done}/{tgt} provisioned, {len(_staged_ids() - _provisioned_ids())} awaiting check")
    return {"ok": True, "completed": done, "target": tgt, "remaining": max(0, tgt - done)}


def show_status() -> dict[str, Any]:
    st = _load_json(STATE_PATH, {})
    prov = _load_json(PROVISIONED, {})
    staged = _load_json(STAGED, {})
    tgt = _target()
    if not st:
        return {
            "ok": True,
            "running": False,
            "completed": prov.get("count", len(prov.get("provisioned") or [])),
            "target": tgt,
            "message": "pipeline not started — run: qemu-world-pipeline.py run",
        }
    st["completed"] = prov.get("count", len(prov.get("provisioned") or []))
    st["provisioned"] = prov.get("provisioned") or []
    st["staged"] = staged.get("staged") or []
    st["target"] = tgt
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
            tgt = _target()
            while True:
                os.system("clear")  # noqa: S605
                print(json.dumps(show_status(), indent=2))
                st = show_status()
                if not st.get("running") and st.get("completed", 0) >= tgt:
                    break
                time.sleep(5)
        except KeyboardInterrupt:
            pass
        return 0
    print("usage: qemu-world-pipeline.py [run|status|watch]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())