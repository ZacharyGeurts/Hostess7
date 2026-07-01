#!/usr/bin/env pythong
"""Hostess7 secure git — pinned GitHub SSH keys, MITM/redirect/hook resistant."""
from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import re
import shutil
import socket
import ssl
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", ROOT.parent if ROOT.parent.name == "NewLatest" else ROOT.parent / "NewLatest"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = ROOT / "data" / "github-known-hosts.json"
KNOWN_HOSTS = STATE / "hostess7-github-known_hosts"
OWNER = os.environ.get("HOSTESS7_GITHUB_OWNER", "ZacharyGeurts")

_SSH_BASE = (
    "-F /dev/null "
    "-o StrictHostKeyChecking=yes "
    "-o GlobalKnownHostsFile=/dev/null "
    "-o HashKnownHosts=no "
    "-o ConnectTimeout=30 "
    "-o BatchMode=yes "
    "-o ClearAllForwardings=yes "
    "-o PermitLocalCommand=no "
    "-o ProxyCommand=none "
    "-o ProxyJump=none"
)

_STRIP_ENV = (
    "GIT_ASKPASS",
    "SSH_ASKPASS",
    "GIT_CREDENTIAL_HELPER",
    "GIT_REDIRECT_STDERR",
    "GIT_SSH",
    "GIT_SSH_COMMAND",
    "GIT_PROXY_COMMAND",
    "ALL_PROXY",
    "all_proxy",
    "HTTP_PROXY",
    "http_proxy",
    "HTTPS_PROXY",
    "https_proxy",
    "GIT_CONFIG_GLOBAL",
    "GIT_CONFIG_SYSTEM",
)

_BLOCKING_CONFIG = (
    (re.compile(r"^url\..*\.insteadof=", re.I), "url.insteadOf redirect"),
    (re.compile(r"^http\.proxy=", re.I), "http.proxy redirect"),
    (re.compile(r"^https\.proxy=", re.I), "https.proxy redirect"),
    (re.compile(r"^core\.sshcommand=", re.I), "core.sshCommand override"),
    (re.compile(r"^core\.gitproxy=", re.I), "core.gitProxy redirect"),
    (re.compile(r"^remote\..*\.url=.*@(?!github\.com)", re.I), "non-github remote"),
    (re.compile(r"^remote\..*\.url=https?://(?!github\.com)", re.I), "non-github https remote"),
)
_WARN_CONFIG = (
    (re.compile(r"^credential(\..*)?\.helper=", re.I), "credential helper (bypassed by secure git)"),
)

_HOOK_NAMES = frozenset(
    {"pre-push", "pre-commit", "post-commit", "update", "pre-receive", "post-receive", "post-checkout", "post-merge"}
)


def _load_doctrine() -> dict[str, Any]:
    if not DOCTRINE.is_file():
        raise SystemExit(f"missing {DOCTRINE}")
    return json.loads(DOCTRINE.read_text(encoding="utf-8"))


def _write_known_hosts(doc: dict[str, Any]) -> Path:
    lines: list[str] = []
    for _host, spec in (doc.get("hosts") or {}).items():
        for line in spec.get("keys") or []:
            if line.strip():
                lines.append(line.strip())
    KNOWN_HOSTS.parent.mkdir(parents=True, exist_ok=True)
    KNOWN_HOSTS.write_text("\n".join(lines) + "\n", encoding="utf-8")
    KNOWN_HOSTS.chmod(0o600)
    return KNOWN_HOSTS


def _probe_tcp(host: str, port: int, timeout: float = 5.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _pick_route(doc: dict[str, Any] | None = None) -> str:
    force = os.environ.get("HOSTESS7_GIT_TUNNEL", "").strip().lower()
    if force in ("443", "tunnel", "yes", "1", "on"):
        return "tunnel"
    if force in ("22", "direct", "no", "0", "off"):
        return "direct"
    hosts = (doc or _load_doctrine()).get("hosts") or {}
    direct_port = int((hosts.get("github.com") or {}).get("port") or 22)
    tunnel_port = int((hosts.get("ssh.github.com") or {}).get("port") or 443)
    if _probe_tcp("github.com", direct_port):
        return "direct"
    if _probe_tcp("ssh.github.com", tunnel_port):
        return "tunnel"
    return "none"


def _resolve_host(host: str) -> list[str]:
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return []
    ips: list[str] = []
    for info in infos:
        ip = info[4][0]
        if ip not in ips:
            ips.append(ip)
    return ips


def _ip_allowed(ip_str: str, cidrs: list[str]) -> bool:
    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    for cidr in cidrs:
        try:
            if addr in ipaddress.ip_network(cidr, strict=False):
                return True
        except ValueError:
            continue
    return False


def _verify_dns(doc: dict[str, Any]) -> dict[str, Any]:
    anti = doc.get("anti_hook") or {}
    if not anti.get("dns_pin_git_cidrs", True):
        return {"ok": True, "skipped": True}
    cidrs = (doc.get("dns_allow") or {}).get("git_cidrs") or []
    if not cidrs:
        return {"ok": True, "skipped": True, "reason": "no cidrs in doctrine"}
    per_host: dict[str, Any] = {}
    all_ok = True
    for host in (doc.get("hosts") or {}):
        ips = _resolve_host(host)
        bad = [ip for ip in ips if not _ip_allowed(ip, cidrs)]
        ok = bool(ips) and not bad
        per_host[host] = {"ips": ips, "ok": ok, "bad": bad}
        all_ok = all_ok and ok
    return {"ok": all_ok, "hosts": per_host}


def _verify_host_keys(doc: dict[str, Any]) -> dict[str, Any]:
    per_host: dict[str, Any] = {}
    all_ok = True
    for host, spec in (doc.get("hosts") or {}).items():
        port = int(spec.get("port") or 22)
        pinned = {
            line.split()[-1]
            for line in (spec.get("keys") or [])
            if "ssh-ed25519" in line and line.split()
        }
        proc = subprocess.run(
            ["ssh-keyscan", "-t", "ed25519", "-p", str(port), host],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        live = [ln.strip() for ln in (proc.stdout or "").splitlines() if "ssh-ed25519" in ln]
        live_fps = {ln.split()[-1] for ln in live if ln.split()}
        match = bool(pinned & live_fps) if pinned and live_fps else False
        per_host[host] = {
            "port": port,
            "ok": match,
            "pinned_ed25519": len(pinned),
            "live_ed25519": len(live_fps),
        }
        all_ok = all_ok and match
    return {"ok": all_ok, "hosts": per_host}


def _tls_pin_ok(host: str) -> bool:
    ctx = ssl.create_default_context()
    with socket.create_connection((host, 443), timeout=12) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as ssock:
            der = ssock.getpeercert(binary_form=True)
    fp = hashlib.sha256(der).hexdigest() if der else ""
    doc = _load_doctrine()
    expected = (doc.get("api") or {}).get("tls_pin_sha256")
    if not expected:
        return True
    return fp.lower() == str(expected).lower().replace(":", "")


def _audit_git_config(cwd: Path | None = None) -> dict[str, Any]:
    blockers: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    scopes: list[tuple[str, list[str]]] = [("global", ["git", "config", "--global", "--list"])]
    if cwd and (cwd / ".git").exists():
        scopes.append(("local", ["git", "-C", str(cwd), "config", "--local", "--list"]))
    for scope, cmd in scopes:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=False)
        for line in (proc.stdout or "").splitlines():
            blocked = False
            for pat, label in _BLOCKING_CONFIG:
                if pat.search(line):
                    blockers.append({"scope": scope, "line": line, "risk": label})
                    blocked = True
                    break
            if blocked:
                continue
            for pat, label in _WARN_CONFIG:
                if pat.search(line):
                    entry = {"scope": scope, "line": line, "risk": label}
                    if scope == "local":
                        entry["risk"] = label.replace("bypassed by secure git", "active in repo")
                        blockers.append(entry)
                    else:
                        warnings.append(entry)
                    break
    return {"ok": len(blockers) == 0, "blockers": blockers, "warnings": warnings}


def _audit_git_hooks(cwd: Path | None) -> dict[str, Any]:
    if not cwd:
        return {"ok": True, "findings": []}
    hooks = cwd / ".git" / "hooks"
    if not hooks.is_dir():
        return {"ok": True, "findings": []}
    active: list[str] = []
    for p in hooks.iterdir():
        if p.name.endswith(".sample"):
            continue
        if p.name in _HOOK_NAMES and p.is_file() and os.access(p, os.X_OK):
            active.append(p.name)
    return {"ok": len(active) == 0, "findings": active}


def _ssh_command(known: Path, route: str) -> str:
    tunnel = ""
    if route == "tunnel":
        tunnel = "-p 443 -o Hostname=ssh.github.com "
    return f"ssh {_SSH_BASE} -o UserKnownHostsFile={known} {tunnel}".strip()


def _sanitize_env(base: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(base or os.environ)
    for key in _STRIP_ENV:
        env.pop(key, None)
    env["GIT_TERMINAL_PROMPT"] = "0"
    return env


def _git_isolated_prefix(ssh_cmd: str) -> list[str]:
    return [
        "-c",
        "credential.helper=",
        "-c",
        "credential.useHttpPath=false",
        "-c",
        f"core.sshCommand={ssh_cmd}",
        "-c",
        "http.proxy=",
        "-c",
        "https.proxy=",
        "-c",
        "http.sslVerify=true",
        "-c",
        "protocol.file.allow=never",
        "-c",
        "core.hooksPath=/dev/null",
        "-c",
        "transfer.fsckobjects=true",
    ]


def _https_to_ssh(url: str, doc: dict[str, Any]) -> str:
    url = url.strip()
    m = re.match(r"https://github\.com/([^/]+)/([^/.]+)(?:\.git)?/?$", url)
    if m:
        owner, repo = m.group(1), m.group(2)
        return f"git@github.com:{owner}/{repo}.git"
    if url.startswith("git@github.com:"):
        return url if url.endswith(".git") else f"{url}.git"
    repos = doc.get("repos") or {}
    for _name, ssh_url in repos.items():
        if url in (ssh_url, ssh_url.replace(".git", "")):
            return ssh_url
    return url


def _validate_remote(url: str, doc: dict[str, Any]) -> dict[str, Any]:
    ssh = _https_to_ssh(url, doc)
    m = re.match(r"git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$", ssh)
    if not m:
        return {"ok": False, "remote": ssh, "error": "remote must be git@github.com:owner/repo.git"}
    owner, repo = m.group(1), m.group(2)
    allowed_owner = str(doc.get("owner") or OWNER)
    if owner != allowed_owner:
        return {"ok": False, "remote": ssh, "error": f"owner {owner} != doctrine owner {allowed_owner}"}
    allowlist = {f"{allowed_owner}/{name}" for name in (doc.get("repos") or {})}
    pair = f"{owner}/{repo.replace('.git', '')}"
    if allowlist and pair not in allowlist:
        repos = doc.get("repos") or {}
        known = {v.replace("git@github.com:", "").replace(".git", "") for v in repos.values()}
        if pair not in known:
            return {"ok": False, "remote": ssh, "error": f"repo {pair} not in known-hosts allowlist"}
    if "@" in ssh.split(":", 1)[-1]:
        return {"ok": False, "remote": ssh, "error": "embedded credentials in remote URL"}
    return {"ok": True, "remote": ssh}


def _token() -> str:
    for key in ("HOSTESS7_GITHUB_TOKEN", "GITHUB_TOKEN", "GH_TOKEN"):
        val = os.environ.get(key, "").strip()
        if val:
            return val
    return ""


def audit(cwd: Path | None = None) -> dict[str, Any]:
    doc = _load_doctrine()
    return {
        "git_config": _audit_git_config(cwd),
        "git_hooks": _audit_git_hooks(cwd),
        "dns": _verify_dns(doc),
        "anti_hook": doc.get("anti_hook"),
    }


def verify(cwd: Path | None = None) -> dict[str, Any]:
    doc = _load_doctrine()
    known = _write_known_hosts(doc)
    keys = _verify_host_keys(doc)
    dns = _verify_dns(doc)
    route = _pick_route(doc)
    api_host = (doc.get("api") or {}).get("host") or "api.github.com"
    tls_ok = _tls_pin_ok(api_host) if (doc.get("api") or {}).get("verify_tls", True) else True
    gh = shutil.which("gh")
    token = bool(_token())
    hook_audit = audit(cwd)
    config_ok = hook_audit["git_config"]["ok"]
    hooks_ok = hook_audit["git_hooks"]["ok"]
    out = {
        "ok": (
            keys.get("ok")
            and dns.get("ok")
            and tls_ok
            and route != "none"
            and bool(gh or token)
            and config_ok
            and hooks_ok
        ),
        "known_hosts": str(known),
        "ssh_key_match": keys,
        "dns_pin": dns,
        "route": route,
        "tls_ok": tls_ok,
        "gh_cli": bool(gh),
        "token_present": token,
        "anti_hook": hook_audit,
        "policy": doc.get("policy"),
        "repos": doc.get("repos"),
    }
    return out


def _run_git(cwd: Path | None, args: list[str], *, ssh_cmd: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    prefix = _git_isolated_prefix(ssh_cmd)
    cmd = ["git", *prefix]
    if cwd:
        cmd.extend(["-C", str(cwd)])
    cmd.extend(args)
    return subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=7200, check=False)


def git_run(cwd: Path, args: list[str], *, remote: str | None = None) -> dict[str, Any]:
    doc = _load_doctrine()
    v = verify(cwd)
    if not v.get("ok"):
        err = "secure git verify failed"
        if not v.get("ssh_key_match", {}).get("ok"):
            err = "pinned SSH keys do not match live GitHub — possible MITM"
        elif not v.get("dns_pin", {}).get("ok"):
            err = "DNS resolves outside GitHub git CIDRs — possible redirect"
        elif not v.get("anti_hook", {}).get("git_config", {}).get("ok"):
            err = "blocking git config (redirect/proxy/ssh override) — fix before push"
        elif not v.get("anti_hook", {}).get("git_hooks", {}).get("ok"):
            err = "active git hooks detected — remove or use clean stage"
        elif v.get("route") == "none":
            err = "cannot reach github.com:22 or ssh.github.com:443"
        return {"ok": False, "error": err, **v}
    known = Path(v["known_hosts"])
    ssh_cmd = _ssh_command(known, str(v.get("route")))
    env = _sanitize_env()
    if remote:
        chk = _validate_remote(remote, doc)
        if not chk.get("ok"):
            return {"ok": False, "error": chk.get("error"), "remote": remote}
        _run_git(cwd, ["remote", "set-url", "origin", chk["remote"]], ssh_cmd=ssh_cmd, env=env)
    proc = _run_git(cwd, args, ssh_cmd=ssh_cmd, env=env)
    return {
        "ok": proc.returncode == 0,
        "rc": proc.returncode,
        "stdout": (proc.stdout or "").strip(),
        "stderr": (proc.stderr or "").strip(),
        "cwd": str(cwd),
        "args": args,
        "route": v.get("route"),
    }


def push_repo(cwd: Path, *, branch: str = "main", remote: str, tag: str | None = None, force: bool = False) -> dict[str, Any]:
    steps: list[dict] = []
    flag = ["--force"] if force else []
    r = git_run(cwd, ["push", "-u", "origin", branch, *flag], remote=remote)
    steps.append({"step": "push", **r})
    if tag:
        git_run(cwd, ["tag", "-a", tag, "-m", tag, "-f"], remote=remote)
        tr = git_run(cwd, ["push", "origin", tag, "--force"], remote=remote)
        steps.append({"step": "tag", **tr})
    ok = all(s.get("ok") for s in steps)
    return {"ok": ok, "branch": branch, "tag": tag, "steps": steps}


def clone_repo(dest: Path, remote: str, *, branch: str | None = None) -> dict[str, Any]:
    doc = _load_doctrine()
    chk = _validate_remote(remote, doc)
    if not chk.get("ok"):
        return {"ok": False, "error": chk.get("error")}
    v = verify()
    if not v.get("ok"):
        return {"ok": False, "error": "verify failed before clone", **v}
    known = Path(v["known_hosts"])
    ssh_cmd = _ssh_command(known, str(v.get("route")))
    env = _sanitize_env()
    args = ["clone", chk["remote"], str(dest)]
    if branch:
        args[1:1] = ["--branch", branch, "--single-branch"]
    proc = _run_git(None, args, ssh_cmd=ssh_cmd, env=env)
    return {
        "ok": proc.returncode == 0,
        "rc": proc.returncode,
        "stdout": (proc.stdout or "").strip(),
        "stderr": (proc.stderr or "").strip(),
        "remote": chk["remote"],
        "route": v.get("route"),
    }


def main(argv: list[str] | None = None) -> int:
    args = list(argv or sys.argv[1:])
    if not args or args[0] in ("-h", "--help", "help"):
        print(
            "Usage: hostess7_secure_git.py verify|audit|route|push|clone ...\n"
            "  Anti-MITM: pinned keys, DNS CIDR pin, -F /dev/null SSH, hooks disabled\n"
            "  HOSTESS7_GIT_TUNNEL=direct|tunnel — force github.com:22 or ssh.github.com:443"
        )
        return 0
    if args[0] == "verify":
        cwd = Path(args[1]).resolve() if len(args) > 1 and not args[1].startswith("-") else None
        doc = verify(cwd)
        print(json.dumps(doc, indent=2))
        return 0 if doc.get("ok") else 1
    if args[0] == "audit":
        cwd = Path(args[1]).resolve() if len(args) > 1 else None
        doc = audit(cwd)
        print(json.dumps(doc, indent=2))
        return 0 if doc.get("git_config", {}).get("ok") and doc.get("git_hooks", {}).get("ok") else 1
    if args[0] == "route":
        route = _pick_route()
        print(json.dumps({"route": route, "policy": "direct=github.com:22 tunnel=ssh.github.com:443"}, indent=2))
        return 0 if route != "none" else 1
    if args[0] == "push":
        cwd = Path(args[1]).resolve()
        branch = "main"
        remote = f"git@github.com:{OWNER}/Hostess7.git"
        tag = None
        force = "--force" in args
        i = 2
        while i < len(args):
            if args[i] == "--branch" and i + 1 < len(args):
                branch = args[i + 1]
                i += 2
            elif args[i] == "--remote" and i + 1 < len(args):
                remote = args[i + 1]
                i += 2
            elif args[i] == "--tag" and i + 1 < len(args):
                tag = args[i + 1]
                i += 2
            else:
                i += 1
        doc = push_repo(cwd, branch=branch, remote=remote, tag=tag, force=force)
        print(json.dumps(doc, indent=2))
        return 0 if doc.get("ok") else 1
    if args[0] == "clone":
        if len(args) < 2:
            print("clone requires DEST", file=sys.stderr)
            return 1
        dest = Path(args[1]).resolve()
        remote = f"git@github.com:{OWNER}/Hostess7.git"
        branch = None
        i = 2
        while i < len(args):
            if args[i] == "--remote" and i + 1 < len(args):
                remote = args[i + 1]
                i += 2
            elif args[i] == "--branch" and i + 1 < len(args):
                branch = args[i + 1]
                i += 2
            else:
                i += 1
        doc = clone_repo(dest, remote, branch=branch)
        print(json.dumps(doc, indent=2))
        return 0 if doc.get("ok") else 1
    print(f"unknown: {args[0]}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())