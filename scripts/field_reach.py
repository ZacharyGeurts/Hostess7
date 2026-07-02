#!/usr/bin/env pythong
"""Hostess7 reach — OS tools, external projects, gated self-update execution.

Hostess 7 reads outside her own folder: SG, AMOURANTHRTX, PATH tools, git state.
Self-update runs only when HOSTESS7_EXEC=1 (or ./Hostess7.sh self-update apply).
"""
from __future__ import annotations

import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from field_paths import ROOT, amouranthrtx_root, hostess7_root, reach_roots, sg_root

REACH_MANIFEST = ROOT / "cache" / "fieldstorage" / "brain" / "superintel" / "reach.json"
REACH_LOG = ROOT / "cache" / "fieldstorage" / "brain" / "superintel" / "reach_exec.jsonl"

SCAN_SUFFIXES = frozenset({".hpp", ".cpp", ".py", ".sh", ".md", ".inc", ".c", ".h", ".json", ".cmake"})
SCAN_SUBDIRS = (
    "scripts", "docs", "Navigator", "Navigator/engine", "dos", "AmmoOS",
    "build", "cache/fieldstorage/brain",
)

OS_TOOLS = (
    "git", "pythong", "python", "cmake", "make", "ninja", "rustc", "cargo",
    "node", "npm", "bash", "sh", "rsync", "curl", "wget", "tar", "gzip",
    "unzip", "which", "uname", "ldd", "gcc", "g++", "clang",
)

_BLOCKED_RE = re.compile(
    r"(?:^|[\s;|&])(?:sudo|su\s|rm\s+-rf|mkfs|dd\s|>\s*/dev/|chmod\s+777|curl\s+.*\|\s*sh|wget\s+.*\|\s*sh)",
    re.I,
)

_ALLOWED_PREFIXES = (
    "git status", "git diff", "git log", "git fetch", "git pull", "git rev-parse",
    "pythong scripts/", "python scripts/",
    "./Hostess7.sh", "Hostess7.sh",
    "cmake --build", "cmake -S", "make -j", "ninja",
    "rsync -a", "cp -a", "cp ",
    "which ", "uname ", "ls ", "ls\n",
    "rustc --version", "cargo --version", "node --version", "npm --version",
)


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def exec_enabled() -> bool:
    return os.environ.get("HOSTESS7_EXEC", "0").strip() in ("1", "true", "yes", "apply")


def _git_head(path: Path) -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=path, text=True, stderr=subprocess.DEVNULL,
        )
        return out.strip()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return "unknown"


def _git_dirty(path: Path) -> bool:
    try:
        out = subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=path, text=True, stderr=subprocess.DEVNULL,
        )
        return bool(out.strip())
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return False


def scan_os_tools() -> dict[str, str]:
    tools: dict[str, str] = {}
    for name in OS_TOOLS:
        found = shutil.which(name)
        if found:
            tools[name] = found
    return tools


def scan_roots_detail() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in reach_roots():
        path = Path(entry["path"])
        row: dict[str, Any] = {
            "role": entry["role"],
            "path": entry["path"],
            "exists": path.is_dir(),
            "git": (path / ".git").is_dir(),
            "head": _git_head(path) if (path / ".git").is_dir() else None,
            "dirty": _git_dirty(path) if (path / ".git").is_dir() else None,
        }
        if entry["role"] == "hostess7":
            row["launcher"] = str(path / "Hostess7.sh")

        if entry["role"] == "amouranthrtx":
            row["linux_sh"] = (path / "linux.sh").is_file()
            row["cmake"] = (path / "CMakeLists.txt").is_file()
        rows.append(row)
    return rows


def reach_snapshot() -> dict[str, Any]:
    """Full reach state — OS, roots, tools."""
    return {
        "updated": _ts(),
        "host": platform.node(),
        "os": f"{platform.system()} {platform.release()}",
        "arch": platform.machine(),
        "exec_enabled": exec_enabled(),
        "hostess7_root": str(hostess7_root()),
        "sg_root": str(sg_root()) if sg_root() else None,
        "amouranthrtx_root": str(amouranthrtx_root()) if amouranthrtx_root() else None,
        "roots": scan_roots_detail(),
        "tools": scan_os_tools(),
        "path": os.environ.get("PATH", ""),
    }


def save_reach_snapshot(snap: dict[str, Any] | None = None) -> Path:
    snap = snap or reach_snapshot()
    REACH_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    REACH_MANIFEST.write_text(json.dumps(snap, indent=2) + "\n", encoding="utf-8")
    return REACH_MANIFEST


def _query_tokens(query: str) -> list[str]:
    return [t for t in re.split(r"\W+", query.lower()) if len(t) > 2]


def grep_reach(query: str, *, limit: int = 10) -> list[dict[str, str | int]]:
    """Search codebase across all reachable roots."""
    tokens = _query_tokens(query)[:8]
    if not tokens:
        return []
    hits: list[tuple[int, dict[str, str | int]]] = []
    skip_parts = frozenset({"build", "cache", ".git", "node_modules", "__pycache__"})

    for entry in reach_roots():
        base = Path(entry["path"])
        role = entry["role"]
        for sub in SCAN_SUBDIRS:
            scan_base = base / sub
            if not scan_base.is_dir():
                continue
            for path in scan_base.rglob("*"):
                if not path.is_file() or path.suffix not in SCAN_SUFFIXES:
                    continue
                if any(p in path.parts for p in skip_parts):
                    continue
                try:
                    text = path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                rel = str(path.relative_to(base))
                for i, line in enumerate(text.splitlines(), 1):
                    low = line.lower()
                    score = sum(2 if t in low else 0 for t in tokens)
                    if score <= 0:
                        continue
                    hits.append((score, {
                        "root": role,
                        "path": rel,
                        "line": i,
                        "text": line.strip()[:140],
                    }))
                    if len(hits) >= limit * 6:
                        break
                if len(hits) >= limit * 6:
                    break
            if len(hits) >= limit * 6:
                break

    hits.sort(key=lambda x: -x[0])
    seen: set[str] = set()
    out: list[dict[str, str | int]] = []
    for _, h in hits:
        key = f"{h['root']}:{h['path']}:{h['line']}"
        if key in seen:
            continue
        seen.add(key)
        out.append(h)
        if len(out) >= limit:
            break
    return out


def command_allowed(cmd: str) -> bool:
    cmd = cmd.strip()
    if not cmd or _BLOCKED_RE.search(cmd):
        return False
    low = cmd.lower()
    return any(low.startswith(p.lower()) for p in _ALLOWED_PREFIXES)


def run_command(cmd: str, *, cwd: Path | None = None, timeout: int = 300) -> dict[str, Any]:
    """Run allowlisted OS command — requires HOSTESS7_EXEC=1."""
    cwd = cwd or hostess7_root()
    record: dict[str, Any] = {
        "ts": _ts(),
        "cmd": cmd,
        "cwd": str(cwd),
        "allowed": command_allowed(cmd),
        "exec_enabled": exec_enabled(),
        "rc": None,
        "stdout": "",
        "stderr": "",
        "ok": False,
    }
    if not record["allowed"]:
        record["stderr"] = "command not on Hostess7 allowlist"
        _log_exec(record)
        return record
    if not exec_enabled():
        record["stderr"] = "advisory only — set HOSTESS7_EXEC=1 or ./Hostess7.sh self-update apply"
        _log_exec(record)
        return record
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "HOSTESS7_ROOT": str(hostess7_root())},
        )
        record["rc"] = proc.returncode
        record["stdout"] = proc.stdout[-8000:]
        record["stderr"] = proc.stderr[-4000:]
        record["ok"] = proc.returncode == 0
    except subprocess.TimeoutExpired:
        record["stderr"] = f"timeout after {timeout}s"
    except OSError as exc:
        record["stderr"] = str(exc)
    _log_exec(record)
    return record


def _log_exec(record: dict[str, Any]) -> None:
    REACH_LOG.parent.mkdir(parents=True, exist_ok=True)
    with REACH_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps({k: record[k] for k in ("ts", "cmd", "cwd", "allowed", "exec_enabled", "rc", "ok")}) + "\n")


def self_update_steps(*, apply: bool = False) -> list[dict[str, Any]]:
    """Truth-ordered self-update pipeline — scan → QA → Field 1 sync → git."""
    h = hostess7_root()
    steps: list[dict[str, Any]] = []

    steps.append({
        "id": "reach-scan",
        "action": "refresh reach manifest (OS + external roots)",
        "cmd": None,
        "fn": "reach",
    })

    qa_scripts = [
        h / "scripts" / "qa_hostess_turing_test.py",
        h / "scripts" / "qa_code_corpus_test.py",
        h / "scripts" / "qa_intelligence_flow_test.py",
    ]
    for script in qa_scripts:
        if script.is_file():
            rel = script.relative_to(h)
            steps.append({
                "id": f"qa-{script.stem}",
                "action": f"run {rel}",
                "cmd": f"pythong {rel}",
                "cwd": str(h),
            })

    field_one = Path(os.environ.get("NEXUS_INSTALL_ROOT", h.parent)) / "lib" / "field-one.py"
    if not field_one.is_file():
        field_one = h.parent / "lib" / "field-one.py"
    if field_one.is_file():
        steps.append({
            "id": "field-sync",
            "action": "Field 1 sync — fieldstorage → TEAM NVMe",
            "cmd": "./Hostess7.sh field sync",
            "cwd": str(h),
        })

    for entry in reach_roots():
        path = Path(entry["path"])
        if not (path / ".git").is_dir():
            continue
        steps.append({
            "id": f"git-pull-{entry['role']}",
            "action": f"git pull {entry['role']}",
            "cmd": "git pull --ff-only",
            "cwd": entry["path"],
        })

    rtx = amouranthrtx_root()
    if rtx and (rtx / "Hostess7.sh").is_file():
        steps.append({
            "id": "delegate-check",
            "action": "verify AMOURANTHRTX delegates to SG/Hostess7",
            "cmd": f"head -n 5 {rtx / 'Hostess7.sh'}",
            "cwd": str(rtx),
        })

    if apply:
        results: list[dict[str, Any]] = []
        save_reach_snapshot()
        agents_script = h / "scripts" / "field_agents7.py"
        agents_were_on = False
        for step in steps:
            if step.get("fn") == "reach":
                results.append({"step": step["id"], "ok": True, "note": "reach snapshot saved"})
                continue
            cmd = step.get("cmd")
            if not cmd:
                continue
            cwd = Path(step.get("cwd", h))
            if step.get("id") == "field-sync" and agents_script.is_file():
                try:
                    off = subprocess.run(
                        [sys.executable, str(agents_script), "off"],
                        cwd=h, capture_output=True, text=True, check=False,
                    )
                    agents_were_on = off.returncode == 0
                    results.append({
                        "step": "agents-off",
                        "ok": True,
                        "note": "stopped agent daemon before Field 1 sync",
                    })
                except OSError as exc:
                    results.append({"step": "agents-off", "ok": False, "error": str(exc)})
            if cmd.startswith("head "):
                # read-only check without exec gate
                try:
                    target = rtx / "Hostess7.sh" if rtx else None
                    text = target.read_text(encoding="utf-8", errors="replace")[:200] if target else ""
                    ok = "SG/Hostess7" in text or "HOSTESS7_ROOT" in text
                    results.append({"step": step["id"], "ok": ok, "preview": text[:120]})
                except OSError as exc:
                    results.append({"step": step["id"], "ok": False, "error": str(exc)})
                continue
            rec = run_command(cmd, cwd=cwd)
            results.append({"step": step["id"], "ok": rec["ok"], "rc": rec["rc"], "stderr": rec["stderr"][-500:]})
            if step.get("id") == "field-sync" and agents_were_on and agents_script.is_file():
                try:
                    on = subprocess.run(
                        [sys.executable, str(agents_script), "on"],
                        cwd=h, capture_output=True, text=True, check=False,
                    )
                    results.append({
                        "step": "agents-on",
                        "ok": on.returncode == 0,
                        "note": "restarted agent daemon after Field 1 sync",
                    })
                except OSError as exc:
                    results.append({"step": "agents-on", "ok": False, "error": str(exc)})
        return results  # type: ignore[return-value]

    return steps


def format_reach_report(snap: dict[str, Any] | None = None) -> str:
    snap = snap or reach_snapshot()
    lines = [
        "=== Hostess 7 — Reach (OS + external projects) ===",
        f"{snap.get('os')} · {snap.get('arch')} · exec={'ON' if snap.get('exec_enabled') else 'advisory'}",
        "",
        "Reachable roots:",
    ]
    for row in snap.get("roots") or []:
        git = ""
        if row.get("git"):
            dirty = " dirty" if row.get("dirty") else ""
            git = f" git={row.get('head')}{dirty}"
        lines.append(f"  • {row.get('role')}: {row.get('path')}{git}")
    tools = snap.get("tools") or {}
    lines.append("")
    lines.append(f"OS tools on PATH: {len(tools)} — {', '.join(sorted(tools)[:16])}")
    if len(tools) > 16:
        lines.append(f"  … +{len(tools) - 16} more")
    lines.append("")
    if snap.get("exec_enabled"):
        lines.append("Exec gate OPEN — Hostess7 may run allowlisted self-update commands.")
    else:
        lines.append(
            "Exec gate CLOSED — advisory only. "
            "Run `./Hostess7.sh self-update apply` to let Hostess7 execute updates."
        )
    lines.append(f"Manifest: {REACH_MANIFEST.relative_to(ROOT)}")
    return "\n".join(lines)


def format_self_update_plan(steps: list[dict[str, Any]], *, applied: list[dict[str, Any]] | None = None) -> str:
    lines = ["=== Hostess 7 — Self-Update Plan ==="]
    if applied is not None:
        lines.append("Applied:")
        for r in applied:
            status = "OK" if r.get("ok") else "FAIL"
            lines.append(f"  [{status}] {r.get('step')}")
            if r.get("stderr"):
                lines.append(f"       {r['stderr'][:120]}")
        return "\n".join(lines)
    lines.append("Hostess7 advises these steps (truth-filtered, allowlisted):")
    for i, step in enumerate(steps, 1):
        lines.append(f"  {i}. {step.get('action')}")
        if step.get("cmd"):
            lines.append(f"     → {step['cmd']}")
    lines.append("")
    lines.append("Apply: `./Hostess7.sh self-update apply` · Preview: `./Hostess7.sh self-update plan`")
    return "\n".join(lines)


def reach_cmd() -> int:
    snap = reach_snapshot()
    save_reach_snapshot(snap)
    print(format_reach_report(snap))
    print(f"METRIC reach_roots={len(snap.get('roots', []))}")
    print(f"METRIC reach_tools={len(snap.get('tools', {}))}")
    print(f"METRIC reach_exec={1 if snap.get('exec_enabled') else 0}")
    print(f"METRIC reach_manifest={REACH_MANIFEST}")
    print("OK reach")
    return 0


def self_update_cmd(mode: str | None = None) -> int:
    mode = (mode or "plan").strip().lower()
    if mode in ("apply", "run", "exec"):
        os.environ["HOSTESS7_EXEC"] = "1"
        results = self_update_steps(apply=True)
        print(format_self_update_plan([], applied=results))
        ok = all(r.get("ok") for r in results)
        print(f"METRIC self_update_steps={len(results)}")
        print(f"METRIC self_update_ok={1 if ok else 0}")
        print("OK self-update-apply" if ok else "FAIL self-update-apply")
        return 0 if ok else 1
    steps = self_update_steps(apply=False)
    print(format_self_update_plan(steps))
    print(f"METRIC self_update_planned={len(steps)}")
    print("OK self-update-plan")
    return 0


def exec_cmd(command: str) -> int:
    rec = run_command(command)
    if rec["stdout"]:
        print(rec["stdout"].rstrip())
    if rec["stderr"]:
        print(rec["stderr"].rstrip(), file=sys.stderr)
    print(f"METRIC exec_ok={1 if rec.get('ok') else 0}")
    print(f"METRIC exec_rc={rec.get('rc')}")
    return 0 if rec.get("ok") else 1


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: field_reach.py reach|self-update [plan|apply]|exec <cmd>", file=sys.stderr)
        return 1
    cmd = sys.argv[1]
    if cmd == "reach":
        return reach_cmd()
    if cmd == "self-update":
        return self_update_cmd(sys.argv[2] if len(sys.argv) > 2 else None)
    if cmd == "exec" and len(sys.argv) >= 3:
        return exec_cmd(" ".join(sys.argv[2:]))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())