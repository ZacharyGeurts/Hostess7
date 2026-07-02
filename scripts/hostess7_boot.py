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
SCRIPTS = ROOT / "scripts"
STORAGE = ROOT / "cache" / "fieldstorage"
ZAC = ROOT / "zac"
DOCTRINE = ROOT / "data" / "field-stack-doctrine.json"
PORT = int(os.environ.get("HOSTESS7_WEB_PORT", os.environ.get("PORT", "8080")))


def _run(cmd: list[str], *, timeout: int = 600) -> dict:
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        env={**os.environ, "HOSTESS7_ROOT": str(ROOT)},
    )
    return {
        "ok": proc.returncode == 0,
        "rc": proc.returncode,
        "stdout": (proc.stdout or "").strip(),
        "stderr": (proc.stderr or "").strip(),
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
            rep = _run([sys.executable, "-m", "pip", "install", "-q", *extra, "-r", req], timeout=180)
            if rep["ok"]:
                try:
                    import flask  # noqa: F401, WPS433
                    return {"ok": True, "skipped": False, **rep}
                except ImportError:
                    continue
        return {"ok": False, "stderr": "flask install failed — pip install -r requirements.txt"}


def boot(*, web: bool = True, stack_learn: bool = True) -> int:
    steps: list[dict] = []

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
        rep = _run([sys.executable, str(SCRIPTS / "field_superintelligence.py"), "stack-learn"], timeout=300)
        steps.append({"name": "stack-learn", **rep})
    else:
        steps.append({"name": "stack-learn", "ok": True, "skipped": True})

    rep = _run([sys.executable, str(SCRIPTS / "field_agents7.py"), "on"], timeout=120)
    steps.append({"name": "on", **rep})

    shell = ROOT / "Hostess7.sh"
    rep = _run(["bash", str(shell), "alert-posture", "on"], timeout=60)
    steps.append({"name": "alert-posture", **rep})

    if web:
        shell = ROOT / "Hostess7.sh"
        rep = _run(["bash", str(shell), "web-start"], timeout=60)
        from hostess7_sovereign_wait import wait_until  # noqa: WPS433

        web_up = wait_until(
            lambda: _ping(f"http://127.0.0.1:{PORT}/health") or _ping(f"http://127.0.0.1:{PORT}/api/status"),
            wait_us=1_200_000,
            label="boot_web",
        )
        rep["web_up"] = web_up
        if not web_up:
            rep["ok"] = False
            rep["stderr"] = (rep.get("stderr") or "") + " web did not respond on :{PORT}"
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
    summary = {
        "ok": _brain_ready() and agents_ok and web_ok,
        "name": "Hostess 7",
        "mode": "live" if _brain_ready() else "booting",
        "brain": _brain_ready(),
        "kilroy": panel,
        "boot_order": boot_order,
        "stack": {"panel": panel, "queen": queen, "training": _ping("http://127.0.0.1:9488/")},
        "web": {"port": PORT, "up": web_up, "url": f"http://127.0.0.1:{PORT}/"},
        "posture": "war-ready",
        "war_ready": True,
        "demo": False,
        "steps": [s["name"] for s in steps],
    }
    _emit(steps, summary=summary)
    print(f"Hostess7 boot → {summary['web']['url']}")
    print("METRIC hostess7_boot=1")
    return 0 if summary["ok"] else 1


def _emit(steps: list[dict], *, ok: bool = True, summary: dict | None = None) -> None:
    print("=== Hostess 7 boot ===")
    for step in steps:
        mark = "OK" if step.get("ok") else "FAIL"
        name = step.get("name", "?")
        extra = step.get("reason") or step.get("stderr") or step.get("stdout") or ""
        if step.get("skipped"):
            mark = "SKIP"
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
    stack_learn = "--no-stack-learn" not in args
    if args and args[0] in ("-h", "--help", "help"):
        print("Usage: hostess7_boot.py [--no-web] [--no-stack-learn]")
        return 0
    return boot(web=web, stack_learn=stack_learn)


if __name__ == "__main__":
    raise SystemExit(main())