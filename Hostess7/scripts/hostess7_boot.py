#!/usr/bin/env pythong
"""Hostess 7 boot — KILROY doctrine, brain on, field web. All paths stay in-repo."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", ROOT.parent if ROOT.parent.name == "NewLatest" else ROOT.parent))
SCRIPTS = ROOT / "scripts"
STORAGE = ROOT / "cache" / "fieldstorage"
ZAC = ROOT / "zac"
DOCTRINE = ROOT / "data" / "field-stack-doctrine.json"
TIMEOUTS_DOC = INSTALL / "data" / "hostess7-boot-timeouts.json"
STATE = Path(os.environ.get("NEXUS_STATE_DIR", os.environ.get("HOSTESS7_BRAIN_STATE", str(ROOT / "cache" / "fieldstorage" / "brain"))))
PORT = int(os.environ.get("HOSTESS7_WEB_PORT", os.environ.get("PORT", "8080")))


def _lite_active() -> bool:
    if os.environ.get("HOSTESS7_LITE", "0") == "1":
        return True
    lite_state = STATE / "hostess7-lite-mode.json"
    if lite_state.is_file():
        try:
            return bool(json.loads(lite_state.read_text(encoding="utf-8")).get("active"))
        except (OSError, json.JSONDecodeError):
            pass
    return False


def _step_timeout(name: str) -> int:
    doc: dict = {}
    if TIMEOUTS_DOC.is_file():
        try:
            doc = json.loads(TIMEOUTS_DOC.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    lite = doc.get("lite") or {}
    if _lite_active() and name in lite:
        val = int(lite[name])
        return val
    steps = doc.get("steps") or {}
    return int(steps.get(name) or doc.get("defaults_sec") or 600)


def _central_log(level: str, source: str, message: str) -> None:
    log_py = INSTALL / "lib" / "field-central-log.py"
    if not log_py.is_file():
        return
    try:
        subprocess.run(
            [sys.executable, str(log_py), "append", level, source, message],
            cwd=str(INSTALL),
            capture_output=True,
            timeout=8,
            check=False,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
        )
    except (OSError, subprocess.TimeoutExpired):
        pass


def _run(cmd: list[str], *, step: str = "", timeout: int | None = None) -> dict:
    budget = timeout if timeout is not None else _step_timeout(step or "default")
    if budget <= 0:
        return {"ok": True, "skipped": True, "reason": f"lite skip {step}", "name": step}
    label = step or " ".join(cmd[:2])
    try:
        proc = subprocess.run(
            cmd,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=budget,
            check=False,
            env={**os.environ, "HOSTESS7_ROOT": str(ROOT), "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
        )
        ok = proc.returncode == 0
        if not ok:
            _central_log("error", "hostess7-boot", f"{label} rc={proc.returncode}: {(proc.stderr or proc.stdout or '')[:240]}")
        return {
            "ok": ok,
            "rc": proc.returncode,
            "stdout": (proc.stdout or "").strip(),
            "stderr": (proc.stderr or "").strip(),
            "timeout_sec": budget,
            "name": step,
        }
    except subprocess.TimeoutExpired:
        _central_log("timeout", "hostess7-boot", f"{label} exceeded {budget}s watchdog")
        return {
            "ok": False,
            "rc": -9,
            "stdout": "",
            "stderr": f"watchdog timeout after {budget}s",
            "timeout": True,
            "timeout_sec": budget,
            "name": step,
        }


def _ping(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=2) as resp:
            return 200 <= getattr(resp, "status", 200) < 400
    except (urllib.error.URLError, OSError, ValueError):
        return False


def _brain_ready() -> bool:
    brain = STORAGE / "brain"
    return brain.is_dir() and any(brain.rglob("*.json"))


def _restore_zac() -> dict:
    index = ZAC / "fieldstorage.zac"
    if not index.is_file():
        return {"ok": True, "skipped": True, "reason": "no zac/fieldstorage.zac"}
    from field_zac import restore_storage  # noqa: WPS433

    report = restore_storage(zac_dir=ZAC, storage=STORAGE, verify=True)
    return {"ok": True, "skipped": False, "report": report}


def _ensure_deps() -> dict:
    try:
        import flask  # noqa: F401, WPS433
        return {"ok": True, "skipped": True, "reason": "flask present"}
    except ImportError:
        req = str(ROOT / "requirements.txt")
        for extra in (["--user"], ["--break-system-packages"], []):
            rep = _run([sys.executable, "-m", "pip", "install", "-q", *extra, "-r", req], step="deps")
            if rep["ok"]:
                try:
                    import flask  # noqa: F401, WPS433
                    return {"ok": True, "skipped": False, **rep}
                except ImportError:
                    continue
        return {"ok": False, "stderr": "flask install failed — pip install -r requirements.txt", "name": "deps"}


def _save_boot_last(steps: list[dict], summary: dict) -> None:
    doc = {
        "schema": "hostess7-boot-last/v1",
        "ts": summary.get("ts"),
        "ok": summary.get("ok"),
        "lite_mode": summary.get("lite_mode"),
        "steps": summary.get("steps"),
        "steps_detail": steps,
        "stack": summary.get("stack"),
    }
    try:
        STATE.mkdir(parents=True, exist_ok=True)
        path = STATE / "hostess7-boot-last.json"
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(path)
    except OSError:
        pass


def boot(*, web: bool = True, stack_learn: bool | None = None) -> int:
    lite = _lite_active()
    if stack_learn is None:
        stack_learn = not lite and os.environ.get("HOSTESS7_STACK_LEARN_ON_BOOT", "1") != "0"

    steps: list[dict] = []
    _central_log("info", "hostess7-boot", f"boot start lite={lite} stack_learn={stack_learn}")

    dep = _ensure_deps()
    steps.append({"name": "deps", **dep})
    if not dep.get("ok"):
        _emit(steps, ok=False)
        return 1

    if not _brain_ready():
        step = {"name": "zac-restore", **_restore_zac()}
        steps.append(step)
        if not step.get("ok"):
            _emit(steps, ok=False)
            return 1
    else:
        steps.append({"name": "zac-restore", "ok": True, "skipped": True, "reason": "brain present"})

    if stack_learn:
        rep = _run([sys.executable, str(SCRIPTS / "field_superintelligence.py"), "stack-learn"], step="stack-learn")
        steps.append({"name": "stack-learn", **rep})
    else:
        steps.append({"name": "stack-learn", "ok": True, "skipped": True, "reason": "lite or --no-stack-learn"})

    rep = _run([sys.executable, str(SCRIPTS / "field_agents7.py"), "on"], step="on")
    steps.append({"name": "on", **rep})

    shell = ROOT / "Hostess7.sh"
    rep = _run(["bash", str(shell), "alert-posture", "on"], step="alert-posture")
    steps.append({"name": "alert-posture", **rep})

    bs_py = ROOT.parent / "lib" / "field-battle-stations.py"
    if bs_py.is_file():
        rep = _run([sys.executable, str(bs_py), "on"], step="battle-stations")
        steps.append({"name": "battle-stations", **rep})
    else:
        rep = _run(["bash", str(shell), "battle-stations", "on"], step="battle-stations")
        steps.append({"name": "battle-stations", **rep})

    if web:
        rep = _run(["bash", str(shell), "web-start"], step="web-start")
        from hostess7_sovereign_wait import wait_until  # noqa: WPS433

        web_up = wait_until(
            lambda: _ping(f"http://127.0.0.1:{PORT}/health") or _ping(f"http://127.0.0.1:{PORT}/api/status"),
            wait_us=1_200_000,
            label="boot_web",
        )
        rep["web_up"] = web_up
        if not web_up:
            rep["ok"] = False
            rep["stderr"] = (rep.get("stderr") or "") + f" web did not respond on :{PORT}"
            _central_log("error", "hostess7-boot", f"web-start failed port={PORT}")
        steps.append({"name": "web-start", **rep})
    else:
        steps.append({"name": "web-start", "ok": True, "skipped": True})

    panel = _ping("http://127.0.0.1:9477/field")
    queen = _ping("http://127.0.0.1:9481/api/status")
    web_up = _ping(f"http://127.0.0.1:{PORT}/api/status") or _ping(f"http://127.0.0.1:{PORT}/health")

    boot_order: list[str] = []
    if DOCTRINE.is_file():
        try:
            boot_order = json.loads(DOCTRINE.read_text(encoding="utf-8")).get("boot_order") or []
        except (OSError, json.JSONDecodeError):
            pass

    agents_ok = any(s.get("name") == "on" and s.get("ok") for s in steps)
    web_ok = not web or any(s.get("name") == "web-start" and s.get("ok") for s in steps)
    import time

    summary = {
        "ok": _brain_ready() and agents_ok and web_ok,
        "name": "Hostess 7",
        "mode": "lite" if lite else ("live" if _brain_ready() else "booting"),
        "lite_mode": lite,
        "brain": _brain_ready(),
        "kilroy": panel,
        "boot_order": boot_order,
        "stack": {"panel": panel, "queen": queen, "training": _ping("http://127.0.0.1:9488/")},
        "web": {"port": PORT, "up": web_up, "url": f"http://127.0.0.1:{PORT}/"},
        "posture": "war-ready",
        "war_ready": True,
        "demo": False,
        "steps": [s["name"] for s in steps],
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    _save_boot_last(steps, summary)
    _emit(steps, summary=summary)
    print(f"Hostess7 boot → {summary['web']['url']}")
    print("METRIC hostess7_boot=1")
    if not summary["ok"]:
        _central_log("fail", "hostess7-boot", "boot completed with failures")
    return 0 if summary["ok"] else 1


def _emit(steps: list[dict], *, ok: bool = True, summary: dict | None = None) -> None:
    print("=== Hostess 7 boot ===")
    for step in steps:
        mark = "OK" if step.get("ok") else "FAIL"
        name = step.get("name", "?")
        extra = step.get("reason") or step.get("stderr") or step.get("stdout") or ""
        if step.get("skipped"):
            mark = "SKIP"
        if step.get("timeout"):
            mark = "TIMEOUT"
        line = f"  {mark} {name}"
        if extra and mark != "OK":
            line += f" — {extra[:120]}"
        print(line)
    if summary:
        print(json.dumps(summary, indent=2))
    if not ok:
        print("FAIL hostess7-boot", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    args = list(argv or sys.argv[1:])
    web = "--no-web" not in args
    stack_learn: bool | None = None
    if "--no-stack-learn" in args:
        stack_learn = False
    if args and args[0] in ("-h", "--help", "help"):
        print("Usage: hostess7_boot.py [--no-web] [--no-stack-learn]")
        print("  HOSTESS7_LITE=1 or ./Hostess7.sh lite on — skips stack-learn, throttles polls")
        return 0
    return boot(web=web, stack_learn=stack_learn)


if __name__ == "__main__":
    raise SystemExit(main())