#!/usr/bin/env pythong
"""Verify Richard Stallman GitHub identity and GNU project anchors — Ironclad + Hostess7 witness."""
from __future__ import annotations

import importlib.util
import json
import os
import ssl
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-gnu-identity-doctrine.json"
PANEL = STATE / "field-gnu-identity-panel.json"

RMS_EXPECTED_ID = 10550344
RMS_EXPECTED_LOGINS = frozenset({"rms", "RMS"})


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _save_atomic(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _import_py(path: Path, name: str) -> Any | None:
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _github_user(login: str) -> dict[str, Any]:
    url = f"https://api.github.com/users/{login}"
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "Hostess7-GNU-Identity-Verify",
        },
    )
    token = os.environ.get("GITHUB_TOKEN", "").strip() or os.environ.get("GH_TOKEN", "").strip()
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=12, context=ctx) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError) as exc:
        return {"ok": False, "error": str(exc)[:200]}


def _gnu_head(host: str) -> dict[str, Any]:
    url = f"https://{host}/"
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Hostess7-GNU-Identity-Verify"})
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            return {"ok": True, "status": resp.status, "host": host}
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        return {"ok": False, "host": host, "error": str(exc)[:120]}


def _ironclad_witness() -> dict[str, Any]:
    ic = _import_py(INSTALL / "lib" / "ironclad-field-sanity.py", "ironclad_field_sanity")
    cite = ""
    if ic and hasattr(ic, "cite_field_sanity"):
        try:
            cite = ic.cite_field_sanity(2) or ""
        except Exception:
            pass
    return {"meld_citation": "ironclad:gnu_identity:1", "field_sanity_cite": cite or "ironclad:field_sanity:2"}


def verify_rms_github() -> dict[str, Any]:
    doc = _github_user("rms")
    if doc.get("ok") is False or not doc.get("id"):
        doc = _github_user("RMS")
    if doc.get("ok") is False:
        return {"ok": False, "verified": False, "reason": "github_api_unreachable", "detail": doc}
    gid = doc.get("id")
    login = str(doc.get("login") or "")
    verified = gid == RMS_EXPECTED_ID and login in RMS_EXPECTED_LOGINS
    return {
        "ok": True,
        "verified": verified,
        "login": login,
        "github_id": gid,
        "expected_id": RMS_EXPECTED_ID,
        "name": doc.get("name"),
        "html_url": doc.get("html_url"),
        "reason": "id_match" if verified else "id_mismatch",
    }


def verify_gnu_hosts() -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    hosts = list((doctrine.get("gnu") or {}).get("canonical_hosts") or ["www.gnu.org", "gnu.org"])
    checks = [_gnu_head(h) for h in hosts]
    live = [c for c in checks if c.get("ok")]
    return {
        "ok": bool(live),
        "verified": len(live) >= 1,
        "hosts_checked": hosts,
        "live": live,
        "checks": checks,
    }


def verify_all(*, write: bool = False) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    rms = verify_rms_github()
    gnu = verify_gnu_hosts()
    iron = _ironclad_witness()
    verified = bool(rms.get("verified")) and bool(gnu.get("verified"))
    out = {
        "ok": True,
        "schema": "field-gnu-identity-verify/v1",
        "verified": verified,
        "at": _now(),
        "rms": rms,
        "gnu": gnu,
        "ironclad": iron,
        "dedication": doctrine.get("rms") or {},
        "preapprove_eligible": verified,
        "repo": (doctrine.get("repos") or {}).get("gnueol_terminal"),
    }
    if write:
        _save_atomic(PANEL, out)
    return out


def invite_rms_collaborator(*, dry_run: bool = False) -> dict[str, Any]:
    """Invite verified RMS as read collaborator — requires gh CLI and prior verify."""
    doc = verify_all(write=False)
    if not doc.get("verified"):
        return {"ok": False, "error": "rms_not_verified", "verify": doc}
    repo = str((doc.get("repo") or "ZacharyGeurts/GNUEOLTerminal"))
    permission = str(((doc.get("dedication") or {}).get("collaborator_permission")) or "read")
    if dry_run:
        login = str((doc.get("rms") or {}).get("login") or "RMS")
        return {"ok": True, "dry_run": True, "repo": repo, "login": login, "permission": permission}
    import subprocess

    login = str((doc.get("rms") or {}).get("login") or "RMS")
    proc = subprocess.run(
        ["gh", "api", f"repos/{repo}/collaborators/{login}", "-X", "PUT", "-f", f"permission={permission}"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    ok = proc.returncode == 0
    note = "Invitation sent — RMS must accept on GitHub"
    if not ok and "not a user" in ((proc.stdout or "") + (proc.stderr or "")):
        note = (
            "Identity verified (id 10550344) but GitHub collaborator API rejects this account — "
            "honor RMS via public dedication; manual contact if read access is needed"
        )
    return {
        "ok": ok,
        "verified_identity": bool(doc.get("verified")),
        "repo": repo,
        "login": login,
        "permission": permission,
        "stdout": (proc.stdout or "")[:400],
        "stderr": (proc.stderr or "")[:400],
        "note": note,
    }


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "json":
        print(json.dumps(verify_all(write=True), ensure_ascii=False, indent=2))
        return 0
    if cmd == "rms":
        print(json.dumps(verify_rms_github(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "gnu":
        print(json.dumps(verify_gnu_hosts(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "invite":
        dry = "--dry" in sys.argv
        print(json.dumps(invite_rms_collaborator(dry_run=dry), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: field-gnu-identity-verify.py [json|rms|gnu|invite [--dry]]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())