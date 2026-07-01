#!/usr/bin/env python3
"""Rolling 3-QEMU pipeline — deploy all nodes (no reboot wait), then loop checks from top."""
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
from typing import Any, Callable

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
VERIFY_SEC = int(os.environ.get("WORLD_PIPELINE_VERIFY_SEC", "90"))
REBOOT_SSH_SEC = int(os.environ.get("WORLD_PIPELINE_REBOOT_SSH_SEC", "120"))
CHECK_MAX_ROUNDS = int(os.environ.get("WORLD_PIPELINE_CHECK_MAX_ROUNDS", "100"))
DEPLOY_SETTLE_SEC = int(os.environ.get("WORLD_PIPELINE_DEPLOY_SETTLE_SEC", "2"))

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


def _pending_check_ids() -> set[str]:
    return _staged_ids() - _provisioned_ids()


def _mark_provisioned(node_id: str) -> None:
    ids = _provisioned_ids()
    ids.add(node_id)
    staged = _staged_ids()
    staged.discard(node_id)
    PROVISIONED.write_text(
        json.dumps(
            {
                "schema": "grok-lab-qemu-provisioned/v1",
                "updated": _ts(),
                "provisioned": sorted(ids),
                "count": len(ids),
                "target": _target(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
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


def _unstage(node_id: str) -> None:
    ids = _staged_ids()
    ids.discard(node_id)
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


def _init_deploy_queue() -> None:
    done = _provisioned_ids()
    staged = _staged_ids()
    pending = [
        n
        for n in _all_region_nodes()
        if n.get("id") not in done and n.get("id") not in staged
    ]
    _queue.clear()
    _queue.extend(pending)
    tgt = _target()
    _state.update(
        {
            "schema": "grok-lab-qemu-pipeline/v3",
            "running": True,
            "mode": "deploy-then-loop-check",
            "phase": "deploy",
            "slots": SLOTS,
            "pending_deploy": len(_queue),
            "pending_check": len(_pending_check_ids()),
            "completed": len(done),
            "target": tgt,
            "check_round": 0,
            "slot_status": {str(s["slot"]): {"state": "idle", "node": None} for s in SLOTS},
            "log": str(LOG_PATH),
        }
    )
    _save_state()


def _init_check_queue_from_top() -> None:
    """Rebuild check queue in manifest order (top → bottom)."""
    done = _provisioned_ids()
    staged = _staged_ids()
    need = [n for n in _all_region_nodes() if n.get("id") in staged and n.get("id") not in done]
    _check_queue.clear()
    _check_queue.extend(need)
    with _lock:
        _state["phase"] = "check"
        _state["pending_check"] = len(_check_queue)
        _state["completed"] = len(done)
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
        _state["pending_deploy"] = len(_queue)
        _state["pending_check"] = len(_pending_check_ids())
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
    for _ in range(max(1, timeout // 2)):
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
        if (r.stdout or "").strip() == "200":
            return True
        if not boot_nudged and i >= 3:
            boot_nudged = True
            _trigger_panel_boot(port)
        time.sleep(5)
    return False


def _stop_vm(nid: str) -> None:
    if nid:
        _run(["bash", str(DEPLOY / "qemu-world-stop-one.sh"), nid], timeout=60)


def _launch_node(slot: int, port: int, node: dict[str, Any]) -> bool:
    nid = node["id"]
    r = _run(
        [
            "bash",
            str(DEPLOY / "qemu-world-launch-one.sh"),
            nid,
            node["region"],
            str(port),
            str(int(node.get("mem_mb") or 1024)),
        ],
        timeout=300,
    )
    if r.returncode != 0:
        _log(f"slot {slot} LAUNCH FAIL {nid}: {(r.stderr or r.stdout)[-200:]}")
        return False
    return True


def _slot_worker_deploy(slot: int) -> None:
    """Launch → SSH → deploy → stage → stop VM. Never wait for reboot or verify."""
    port = SLOTS[slot]["port"]
    while True:
        node = _pop_next(_queue)
        if node is None:
            _set_slot(slot, state="idle", node=None)
            _log(f"slot {slot} idle — deploy queue empty")
            return

        nid = node["id"]
        try:
            _set_slot(slot, state="launching", node=node)
            _log(f"slot {slot} :{port} launching {nid} ({node.get('city', node['region'])})")

            if not _launch_node(slot, port, node):
                with _lock:
                    _queue.appendleft(node)
                time.sleep(5)
                continue

            _set_slot(slot, state="ssh_wait", node=node)
            if not _wait_ssh(port, timeout=120):
                _log(f"slot {slot} SSH TIMEOUT {nid}")
                _stop_vm(nid)
                with _lock:
                    _queue.appendleft(node)
                continue

            _set_slot(slot, state="deploying", node=node)
            _log(f"slot {slot} deploying {nid} (reboot fire-and-forget)")
            r = _run(
                [
                    "bash",
                    str(DEPLOY / "world-node-c2-kilroy-war-deploy.sh"),
                    str(port),
                    nid,
                    node["region"],
                ],
                timeout=3600,
            )
            deploy_ok = _deploy_ok(port, r.returncode)

            if deploy_ok:
                _mark_staged(nid)
                tgt = _target()
                _log(
                    f"slot {slot} STAGED {nid} — load next "
                    f"({len(_staged_ids())} staged, {len(_provisioned_ids())}/{tgt} online)"
                )
                time.sleep(DEPLOY_SETTLE_SEC)
            else:
                _log(f"slot {slot} DEPLOY FAIL {nid} — re-queue")
                with _lock:
                    _queue.appendleft(node)

            _stop_vm(nid)
            _set_slot(slot, state="idle", node=None)
            time.sleep(1)

        except Exception as exc:  # noqa: BLE001
            _log(f"slot {slot} DEPLOY UNHANDLED {nid} {type(exc).__name__}: {exc}")
            _stop_vm(nid)
            with _lock:
                _queue.appendleft(node)
            time.sleep(5)


def _slot_worker_check(slot: int) -> None:
    """Check pass: launch staged node, verify panel online, provision or retry next round."""
    port = SLOTS[slot]["port"]
    while True:
        node = _pop_next(_check_queue)
        if node is None:
            _set_slot(slot, state="idle", node=None)
            return

        nid = node["id"]
        try:
            _set_slot(slot, state="check_launch", node=node)
            _log(f"slot {slot} check {nid} ({node.get('city', node['region'])})")

            if not _launch_node(slot, port, node):
                with _lock:
                    _check_queue.append(node)
                time.sleep(5)
                continue

            _set_slot(slot, state="check_ssh", node=node)
            if not _wait_ssh(port, timeout=REBOOT_SSH_SEC):
                _log(f"slot {slot} CHECK SSH TIMEOUT {nid} — retry next round")
                _stop_vm(nid)
                continue

            _set_slot(slot, state="check_verify", node=node)
            _trigger_panel_boot(port)
            verified = _verify_panel(port)
            tree_ok = _deploy_ok(port, 0)

            if tree_ok and verified:
                _mark_provisioned(nid)
                tgt = _target()
                _log(f"slot {slot} ONLINE {nid} — {len(_provisioned_ids())}/{tgt}")
            elif not tree_ok:
                _log(f"slot {slot} CHECK FAIL {nid} — tree missing, back to deploy queue")
                _unstage(nid)
                with _lock:
                    _queue.append(node)
            else:
                _log(f"slot {slot} CHECK NOT READY {nid} — retry next round from top")

            _stop_vm(nid)
            _set_slot(slot, state="idle", node=None)
            time.sleep(1)

        except Exception as exc:  # noqa: BLE001
            _log(f"slot {slot} CHECK UNHANDLED {nid} {exc}")
            _stop_vm(nid)
            time.sleep(5)


def _run_slot_pool(worker: Callable[[int], None], label: str) -> None:
    _log(f"{label} — 3 QEMU slots")
    threads = [threading.Thread(target=worker, args=(s["slot"],), daemon=True) for s in SLOTS]
    for t in threads:
        t.start()
    for t in threads:
        t.join()


def _run_check_loop() -> None:
    """Sweep staged nodes from top of manifest until all online or max rounds."""
    round_num = 0
    while _pending_check_ids():
        round_num += 1
        if round_num > CHECK_MAX_ROUNDS:
            _log(f"check loop stopped after {CHECK_MAX_ROUNDS} rounds — {_len_pending()} still offline")
            break
        _init_check_queue_from_top()
        pending = len(_check_queue)
        if not pending:
            break
        with _lock:
            _state["check_round"] = round_num
        _log(f"=== check round {round_num} — {pending} nodes from top ===")
        _run_slot_pool(_slot_worker_check, f"check round {round_num}")
        done = len(_provisioned_ids())
        tgt = _target()
        still = len(_pending_check_ids())
        _log(f"=== end round {round_num} — {done}/{tgt} online, {still} awaiting check ===")
        if still:
            time.sleep(5)


def _len_pending() -> int:
    return len(_pending_check_ids())


def run_pipeline() -> dict[str, Any]:
    pid_path = DEPLOY.parent.parent / ".nexus-state" / "world-pipeline.pid"
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    pid_path.write_text(f"{os.getpid()}\n", encoding="utf-8")
    tgt = _target()
    _init_deploy_queue()

    to_deploy = len(_queue)
    to_check = len(_pending_check_ids())
    if not to_deploy and not to_check:
        _state["running"] = False
        _save_state()
        return {"ok": True, "message": f"all {tgt} nodes online", "completed": len(_provisioned_ids())}

    _log(
        f"pipeline start — {to_deploy} to deploy, {to_check} awaiting check, "
        f"{len(_provisioned_ids())}/{tgt} online (deploy-only then loop-check)"
    )

    ensure = DEPLOY / "world-node-panel-ensure.sh"
    if ensure.is_file():
        _run(["bash", str(ensure)], timeout=60)

    if _queue:
        with _lock:
            _state["phase"] = "deploy"
        _run_slot_pool(_slot_worker_deploy, "deploy phase")

    if _pending_check_ids():
        _run_check_loop()

    with _lock:
        _state["running"] = False
        _state["phase"] = "done"
        _state["completed"] = len(_provisioned_ids())
        _state["pending_deploy"] = len(_queue)
        _state["pending_check"] = len(_pending_check_ids())
    _save_state()
    done = len(_provisioned_ids())
    still = len(_pending_check_ids())
    _log(f"pipeline finished — {done}/{tgt} online, {still} still need check")
    return {"ok": still == 0, "completed": done, "target": tgt, "remaining_check": still}


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
    st["pending_check"] = len(_pending_check_ids())
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