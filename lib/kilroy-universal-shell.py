#!/usr/bin/env pythong
"""KILROY Universal Shell — every OS CLI name resolves to one canonical op."""
from __future__ import annotations

import json
import os
import platform
import shlex
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
DOCTRINE = INSTALL / "data" / "kilroy-universal-cli-doctrine.json"

_ALIAS_INDEX: dict[str, dict[str, Any]] | None = None
_COMMANDS: list[dict[str, Any]] | None = None


def _load_doctrine() -> dict[str, Any]:
    try:
        return json.loads(DOCTRINE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"commands": []}


def _build_index() -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    global _ALIAS_INDEX, _COMMANDS
    if _ALIAS_INDEX is not None and _COMMANDS is not None:
        return _ALIAS_INDEX, _COMMANDS
    doc = _load_doctrine()
    commands = list(doc.get("commands") or [])
    index: dict[str, dict[str, Any]] = {}
    for row in commands:
        cid = str(row.get("id") or "")
        for alias in row.get("aliases") or []:
            index[str(alias).lower()] = row
        posix = str(row.get("posix") or "").lower()
        if posix:
            index[posix] = row
    _ALIAS_INDEX = index
    _COMMANDS = commands
    return index, commands


def all_aliases() -> set[str]:
    index, _ = _build_index()
    return set(index.keys())


def resolve_line(line: str) -> dict[str, Any]:
    """Map any OS CLI name to canonical id + POSIX rewrite."""
    stripped = (line or "").strip()
    if not stripped:
        return {"ok": False, "error": "empty", "line": stripped}
    try:
        parts = shlex.split(stripped, posix=os.name != "nt")
    except ValueError as exc:
        return {"ok": False, "error": str(exc), "line": stripped}
    if not parts:
        return {"ok": False, "error": "empty", "line": stripped}
    raw = parts[0]
    key = raw.lower()
    if key.endswith(".exe"):
        key = key[:-4]
    index, _ = _build_index()
    row = index.get(key)
    if not row:
        return {
            "ok": True,
            "canonical": None,
            "raw": raw,
            "argv": parts,
            "posix_argv": parts,
            "posix_line": stripped,
            "builtin": False,
            "matched_family": None,
        }
    posix = str(row.get("posix") or raw)
    posix_argv = [posix, *parts[1:]]
    posix_line = " ".join(shlex.quote(p) for p in posix_argv)
    return {
        "ok": True,
        "canonical": row.get("id"),
        "label": row.get("label"),
        "raw": raw,
        "argv": parts,
        "posix_argv": posix_argv,
        "posix_line": posix_line,
        "builtin": bool(row.get("builtin")),
        "matched_family": _guess_family(raw, row),
    }


def _guess_family(raw: str, row: dict[str, Any]) -> str:
    low = raw.lower()
    aliases = [str(a).lower() for a in (row.get("aliases") or [])]
    if low in ("dir", "type", "cls", "copy", "del", "erase", "md", "chdir", "ren", "findstr", "ver"):
        return "cmd"
    if low in ("get-childitem", "get-content", "clear-host", "get-location", "set-location", "copy-item", "remove-item", "move-item", "select-string", "get-command", "write-output", "write-host", "new-item"):
        return "powershell"
    if low in ("sw_vers",):
        return "darwin"
    if low in ("gmake",):
        return "bsd"
    if low in aliases:
        return "posix"
    return "kilroy"


def run_builtin(
    canonical: str,
    argv: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    kilroy_status_fn: Any = None,
) -> dict[str, Any] | None:
    """Execute canonical builtin; None if not handled here."""
    args = argv[1:]
    env = env or os.environ

    if canonical == "list_dir":
        show_all = any(a in ("-a", "-la", "-al", "-A") for a in args)
        long_fmt = any(a.startswith("-l") or a == "-la" or a == "-al" for a in args)
        try:
            entries = sorted(cwd.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except OSError as exc:
            return {"ok": False, "output": str(exc)}
        lines: list[str] = []
        if show_all:
            lines.extend([".", ".."])
        for p in entries:
            if not show_all and p.name.startswith("."):
                continue
            mark = "/" if p.is_dir() else "@" if p.is_symlink() else ""
            if long_fmt:
                try:
                    st = p.stat()
                    mode = "d" if p.is_dir() else "-"
                    lines.append(f"{mode}rwxr-xr-x {st.st_size:8d} {p.name}{mark}")
                except OSError:
                    lines.append(f"?---------        {p.name}{mark}")
            else:
                lines.append(f"{p.name}{mark}")
        return {"ok": True, "output": "  ".join(lines) if lines else "(empty)"}

    if canonical == "print":
        return {"ok": True, "output": " ".join(args)}

    if canonical == "cat":
        if not args:
            return {"ok": False, "output": "usage: cat <file>  (also: type, get-content)"}
        out: list[str] = []
        for name in args:
            if name.startswith("-"):
                continue
            target = Path(name).expanduser()
            if not target.is_absolute():
                target = (cwd / target).resolve()
            try:
                out.append(target.read_text(encoding="utf-8", errors="replace"))
            except OSError as exc:
                return {"ok": False, "output": f"cat: {name}: {exc}"}
        return {"ok": True, "output": "".join(out)}

    if canonical == "pwd":
        return {"ok": True, "output": str(cwd.resolve())}

    if canonical == "clear":
        return {"ok": True, "clear": True, "output": ""}

    if canonical == "whoami":
        user = env.get("USER") or env.get("USERNAME") or "kilroy"
        return {"ok": True, "output": user}

    if canonical == "hostname":
        try:
            return {"ok": True, "output": socket.gethostname()}
        except OSError:
            return {"ok": True, "output": "kilroy-field"}

    if canonical == "uname":
        if argv[0].lower() in ("ver",):
            return {
                "ok": True,
                "output": f"KILROY Universal Shell [{platform.system()} {platform.release()}]",
            }
        try:
            u = platform.uname()
            return {"ok": True, "output": f"{u.system} {u.node} {u.release} {u.machine}"}
        except Exception:
            return {"ok": True, "output": "KILROY Field OS 1.1.0 Sanctuary"}

    if canonical == "mkdir":
        if not args:
            return {"ok": False, "output": "usage: mkdir <dir>  (also: md, new-item)"}
        created = []
        for name in args:
            if name.startswith("-"):
                continue
            target = Path(name).expanduser()
            if not target.is_absolute():
                target = (cwd / target).resolve()
            try:
                target.mkdir(parents=True, exist_ok=True)
                created.append(str(target))
            except OSError as exc:
                return {"ok": False, "output": f"mkdir: {name}: {exc}"}
        return {"ok": True, "output": "\n".join(created) if created else ""}

    if canonical == "help":
        _, commands = _build_index()
        lines = [
            "KILROY Universal CLI — same name, same shit across every OS",
            "",
        ]
        for row in commands:
            aliases = ", ".join((row.get("aliases") or [])[:6])
            lines.append(f"  {row.get('id', ''):14}  {aliases}")
        lines.append("")
        lines.append("Families: POSIX · GNU · BSD · CMD · PowerShell · KILROY")
        return {"ok": True, "output": "\n".join(lines)}

    if canonical == "kilroy_status":
        if callable(kilroy_status_fn):
            return {"ok": True, "output": kilroy_status_fn()}
        return {
            "ok": True,
            "output": "KILROY universal shell · loopback · " + datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

    if canonical == "source_tree":
        return {
            "ok": True,
            "output": "source tree: github.com/ZacharyGeurts/KILROY · type ls /home/kilroy",
        }

    return None


def dispatch(
    line: str,
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    kilroy_status_fn: Any = None,
) -> dict[str, Any]:
    """Resolve + builtin dispatch. Returns posix_line when caller should subprocess."""
    resolved = resolve_line(line)
    if not resolved.get("ok"):
        return {"ok": False, "output": resolved.get("error") or "resolve failed", "cwd": str(cwd)}
    canonical = resolved.get("canonical")
    if not canonical:
        return {
            "ok": True,
            "delegate": True,
            "posix_line": resolved.get("posix_line") or line,
            "resolved": resolved,
            "cwd": str(cwd),
        }
    if resolved.get("builtin"):
        out = run_builtin(
            canonical,
            resolved.get("argv") or [],
            cwd=cwd,
            env=env,
            kilroy_status_fn=kilroy_status_fn,
        )
        if out is not None:
            out["resolved"] = resolved
            out["cwd"] = str(cwd)
            return out
    return {
        "ok": True,
        "delegate": True,
        "posix_line": resolved.get("posix_line") or line,
        "resolved": resolved,
        "cwd": str(cwd),
    }


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "json":
        doc = _load_doctrine()
        doc["alias_count"] = len(all_aliases())
        print(json.dumps(doc, indent=2))
        return 0
    if cmd == "resolve" and len(sys.argv) > 2:
        print(json.dumps(resolve_line(" ".join(sys.argv[2:])), indent=2))
        return 0
    if cmd == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}))
            return 1
        cwd = Path(str(body.get("cwd") or ".")).expanduser().resolve()
        print(json.dumps(dispatch(str(body.get("line") or ""), cwd=cwd), indent=2))
        return 0
    print(json.dumps({"error": "usage: kilroy-universal-shell.py [json|resolve LINE|dispatch]"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())