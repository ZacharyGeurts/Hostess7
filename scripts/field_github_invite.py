#!/usr/bin/env pythong
"""Hostess7 GitHub API — collaborator invite, auth status, field-drive bootstrap.

Bot identity: https://github.com/hostess7 (write access to Owner repos).
Token never committed — lives on field drive only: brain/security/github.token
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from field_paths import ROOT, STORAGE

OWNER = os.environ.get("HOSTESS7_GITHUB_OWNER", "ZacharyGeurts")
BOT_LOGIN = os.environ.get("HOSTESS7_GITHUB_BOT", "hostess7")
DEFAULT_REPOS = tuple(
    r.strip()
    for r in os.environ.get(
        "HOSTESS7_GITHUB_REPOS",
        "Hostess7,NEXUS-Shield,AMOURANTHRTX,memes",
    ).split(",")
    if r.strip()
)
PERMISSION = os.environ.get("HOSTESS7_GITHUB_PERMISSION", "push")
API_VERSION = "2022-11-28"

SECURITY_DIR = STORAGE / "brain" / "security"
FIELD_SECURITY = Path("/media/default/HOSTESS7_TEAM/fieldstorage/brain/security")
META_PATH = SECURITY_DIR / "github.json"
TOKEN_PATH = SECURITY_DIR / "github.token"
META_FIELD = FIELD_SECURITY / "github.json"
TOKEN_FIELD = FIELD_SECURITY / "github.token"


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _security_dir() -> Path:
    for base in (FIELD_SECURITY.parent, SECURITY_DIR.parent):
        if base.is_dir():
            target = base / "security"
            target.mkdir(parents=True, exist_ok=True)
            return target
    SECURITY_DIR.parent.mkdir(parents=True, exist_ok=True)
    return SECURITY_DIR


def _meta_path() -> Path:
    d = _security_dir()
    return d / "github.json"


def _token_path() -> Path:
    d = _security_dir()
    return d / "github.token"


def _token_fingerprint(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]


def _gh_token() -> str | None:
    for key in ("HOSTESS7_GITHUB_TOKEN", "GITHUB_TOKEN", "GH_TOKEN"):
        val = os.environ.get(key, "").strip()
        if val:
            return val
    path = _token_path()
    if path.is_file():
        try:
            return path.read_text(encoding="utf-8").strip()
        except OSError:
            pass
    if shutil.which("gh"):
        try:
            out = subprocess.check_output(
                ["gh", "auth", "token", "-h", "github.com"],
                text=True,
                stderr=subprocess.DEVNULL,
            )
            tok = out.strip()
            return tok or None
        except (subprocess.CalledProcessError, FileNotFoundError, OSError):
            pass
    return None


def _api(
    method: str,
    path: str,
    *,
    token: str | None = None,
    body: dict[str, Any] | None = None,
) -> tuple[int, Any]:
    token = token or _gh_token()
    if not token:
        return 401, {"message": "no GitHub token — gh auth login or brain/security/github.token"}
    url = path if path.startswith("http") else f"https://api.github.com{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method.upper(),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": "Hostess7-GitHub-Invite/1.0",
            **({"Content-Type": "application/json"} if data else {}),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw) if raw.strip() else {"message": exc.reason}
        except json.JSONDecodeError:
            payload = {"message": raw or exc.reason}
        return exc.code, payload


def _owner_token() -> str | None:
    """Token for ZacharyGeurts (invite sender) — gh CLI or env."""
    return _gh_token()


def _bot_token() -> str | None:
    """Token for hostess7 bot — field drive only."""
    path = _token_path()
    if path.is_file():
        try:
            return path.read_text(encoding="utf-8").strip() or None
        except OSError:
            pass
    return os.environ.get("HOSTESS7_GITHUB_TOKEN", "").strip() or None


def github_user(token: str | None = None) -> dict[str, Any]:
    code, data = _api("GET", "/user", token=token)
    if code != 200 or not isinstance(data, dict):
        return {"ok": False, "code": code, "error": data}
    return {
        "ok": True,
        "login": data.get("login"),
        "id": data.get("id"),
        "name": data.get("name"),
        "public_repos": data.get("public_repos"),
    }


def collaborator_state(repo: str, username: str = BOT_LOGIN) -> dict[str, Any]:
    path = f"/repos/{OWNER}/{repo}/collaborators/{username}"
    code, data = _api("GET", path, token=_owner_token())
    if code == 204:
        return {"repo": repo, "state": "active", "permission": "write"}
    if code == 404:
        inv_code, invites = _api("GET", f"/repos/{OWNER}/{repo}/invitations", token=_owner_token())
        pending = None
        if inv_code == 200 and isinstance(invites, list):
            for inv in invites:
                invitee = (inv.get("invitee") or {}).get("login", "").lower()
                if invitee == username.lower():
                    pending = {
                        "id": inv.get("id"),
                        "permissions": inv.get("permissions"),
                        "html_url": inv.get("html_url"),
                        "created_at": inv.get("created_at"),
                    }
                    break
        return {
            "repo": repo,
            "state": "pending" if pending else "none",
            "invite": pending,
        }
    return {"repo": repo, "state": "error", "code": code, "error": data}


def send_invite(repo: str, *, permission: str = PERMISSION) -> dict[str, Any]:
    path = f"/repos/{OWNER}/{repo}/collaborators/{BOT_LOGIN}"
    code, data = _api(
        "PUT",
        path,
        token=_owner_token(),
        body={"permission": permission},
    )
    if code in (201, 204):
        return {
            "repo": repo,
            "ok": True,
            "state": "active" if code == 204 else "invited",
            "permission": permission,
            "invite_id": data.get("id") if isinstance(data, dict) else None,
            "html_url": data.get("html_url") if isinstance(data, dict) else None,
        }
    return {"repo": repo, "ok": False, "code": code, "error": data}


def invite_all(repos: list[str] | None = None) -> dict[str, Any]:
    repos = repos or list(DEFAULT_REPOS)
    results = [send_invite(r) for r in repos]
    doc = {
        "version": 1,
        "updated": _ts(),
        "owner": OWNER,
        "bot_login": BOT_LOGIN,
        "permission": PERMISSION,
        "repos": results,
        "accept_url": f"https://github.com/{OWNER}/Hostess7/invitations",
        "next_steps": [
            f"Log in as {BOT_LOGIN} on GitHub",
            "Accept pending repository invitations",
            "Create fine-grained PAT (repo Contents+Metadata write) or classic repo scope",
            "./Hostess7.sh github bootstrap  # stores token on field drive",
            "./Hostess7.sh github status     # verify bot can push",
        ],
    }
    _meta_path().write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return doc


def bootstrap_token(token: str | None = None) -> dict[str, Any]:
    token = (token or os.environ.get("HOSTESS7_GITHUB_TOKEN", "")).strip()
    if not token:
        return {"ok": False, "error": "pass token via HOSTESS7_GITHUB_TOKEN or: github bootstrap <token>"}
    user = github_user(token)
    if not user.get("ok"):
        return {"ok": False, "error": "token invalid", "detail": user}
    path = _token_path()
    path.write_text(token + "\n", encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    meta = {
        "version": 1,
        "updated": _ts(),
        "bot_login": user.get("login"),
        "bot_id": user.get("id"),
        "token_fingerprint": _token_fingerprint(token),
        "token_path": str(path),
        "owner": OWNER,
        "repos": list(DEFAULT_REPOS),
        "ready": user.get("login", "").lower() == BOT_LOGIN.lower(),
    }
    _meta_path().write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return {"ok": True, "login": user.get("login"), "fingerprint": meta["token_fingerprint"], "path": str(path)}


def status_report() -> dict[str, Any]:
    owner_user = github_user(_owner_token())
    bot_user = github_user(_bot_token()) if _bot_token() else {"ok": False, "error": "no bot token"}
    repos = [collaborator_state(r) for r in DEFAULT_REPOS]
    gh_cli = shutil.which("gh") is not None
    meta_file = _meta_path()
    meta = {}
    if meta_file.is_file():
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            meta = {}
    ready = (
        bot_user.get("ok")
        and bot_user.get("login", "").lower() == BOT_LOGIN.lower()
        and any(r.get("state") == "active" for r in repos)
    )
    return {
        "updated": _ts(),
        "owner": OWNER,
        "bot_login": BOT_LOGIN,
        "gh_cli": gh_cli,
        "owner_auth": owner_user,
        "bot_auth": bot_user,
        "repos": repos,
        "meta_path": str(meta_file),
        "token_on_field": _token_path().is_file(),
        "ready_to_ship": ready,
        "pending_accept": [r for r in repos if r.get("state") == "pending"],
        "meta": meta,
    }


def format_status(report: dict[str, Any]) -> str:
    lines = ["=== Hostess7 GitHub API ==="]
    lines.append(f"Owner: {report.get('owner')} · Bot: {report.get('bot_login')}")
    owner = report.get("owner_auth") or {}
    if owner.get("ok"):
        lines.append(f"Owner auth: {owner.get('login')} (gh CLI / env)")
    else:
        lines.append(f"Owner auth: MISSING — run: gh auth login -h github.com -p https -w")
    bot = report.get("bot_auth") or {}
    if bot.get("ok"):
        lines.append(f"Bot auth: {bot.get('login')} · token on field drive")
    else:
        lines.append("Bot auth: waiting — accept invite + github bootstrap <PAT>")
    lines.append("")
    lines.append("Repos:")
    for r in report.get("repos") or []:
        state = r.get("state", "?")
        extra = ""
        if state == "pending" and r.get("invite"):
            extra = f" · invite #{r['invite'].get('id')}"
        lines.append(f"  {r.get('repo')}: {state}{extra}")
    pending = report.get("pending_accept") or []
    if pending:
        lines.append("")
        lines.append(f"Accept invites as @{report.get('bot_login')}:")
        lines.append(f"  https://github.com/notifications")
        lines.append(f"  https://github.com/{report.get('owner')}/Hostess7/invitations")
    if report.get("ready_to_ship"):
        lines.append("")
        lines.append("READY — Hostess7 can ship (Field 1 sync → git push).")
    else:
        lines.append("")
        lines.append("NOT READY — complete invite accept + bootstrap token.")
    lines.append(f"Field meta: {report.get('meta_path')}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hostess7 GitHub invite + auth")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status", help="Owner + bot auth and collaborator state")
    inv = sub.add_parser("invite", help="Invite bot to Owner repos (needs gh auth as Owner)")
    inv.add_argument("repos", nargs="*", help="Repo names (default: Hostess7,NEXUS-Shield,...)")
    boot = sub.add_parser("bootstrap", help="Store bot PAT on field drive (0600)")
    boot.add_argument("token", nargs="?", help="PAT (or HOSTESS7_GITHUB_TOKEN env)")
    args = parser.parse_args(argv)

    if args.cmd == "status":
        report = status_report()
        print(format_status(report))
        print(f"METRIC github_ready={1 if report.get('ready_to_ship') else 0}")
        print(f"METRIC github_pending={len(report.get('pending_accept') or [])}")
        print("OK github-status")
        return 0

    if args.cmd == "invite":
        repos = list(args.repos) if args.repos else list(DEFAULT_REPOS)
        doc = invite_all(repos)
        for row in doc.get("repos") or []:
            mark = "OK" if row.get("ok") else "FAIL"
            state = row.get("state") or row.get("error")
            print(f"{mark} {row.get('repo')}: {state}")
        print("")
        print(f"Accept as @{BOT_LOGIN}: https://github.com/{OWNER}/Hostess7/invitations")
        print(f"Saved: {_meta_path()}")
        ok = all(r.get("ok") for r in doc.get("repos") or [])
        print("OK github-invite" if ok else "FAIL github-invite")
        return 0 if ok else 1

    if args.cmd == "bootstrap":
        result = bootstrap_token(args.token)
        if not result.get("ok"):
            print(f"FAIL {result.get('error')}", file=sys.stderr)
            if result.get("detail"):
                print(json.dumps(result["detail"], indent=2), file=sys.stderr)
            return 1
        print(f"Bot token stored for {result.get('login')} · fp={result.get('fingerprint')}")
        print(f"Path: {result.get('path')} (mode 0600)")
        print("OK github-bootstrap")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())