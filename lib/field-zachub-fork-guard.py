#!/usr/bin/env python3
"""AmmoDrive fork guard — no forks, no branches, no unauthorized local clones."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-zachub-fork-guard-doctrine.json"
MANIFEST = INSTALL / "data" / "folder-consolidation-manifest.json"
PANEL = STATE / "field-zachub-fork-guard-panel.json"
LEDGER = STATE / "field-zachub-fork-guard-ledger.jsonl"
OWNER = os.environ.get("GITHUB_ACCOUNT", "ZacharyGeurts")
KEEP_RE = re.compile(os.environ.get("GITHUB_KEEP_BRANCHES", r"^(main|master|gh-pages)$"))
GITHUB_REMOTE_RE = re.compile(r"github\.com[:/]([^/]+)/([^/\s]+)", re.I)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _ledger_append(row: dict[str, Any]) -> dict[str, Any]:
    entry = {"ts": _utc(), **row}
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    reg = _mod("lib/field-endpoint-registry.py", "endpoint_registry")
    if reg and hasattr(reg, "record"):
        try:
            reg.record(
                layer="github",
                kind=str(row.get("kind") or "fork_guard"),
                entity_id=str(row.get("entity_id") or row.get("repo") or "zachub-fork-guard"),
                from_val=row.get("from"),
                to_val=row.get("to"),
                witness="field-zachub-fork-guard",
                reason=str(row.get("reason") or row.get("action") or "fork guard action"),
            )
        except (OSError, TypeError, ValueError):
            pass
    return entry


def _mod(rel: str, name: str) -> Any | None:
    py = INSTALL / rel
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _gh_available() -> bool:
    return shutil.which("gh") is not None


def _gh_json(path: str, *, method: str = "GET", fields: dict[str, str] | None = None, timeout: float = 60.0) -> Any:
    cmd = ["gh", "api", path]
    if method.upper() != "GET":
        cmd.extend(["-X", method.upper()])
    for k, v in (fields or {}).items():
        cmd.extend(["-f", f"{k}={v}"])
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "gh api failed")
    raw = (proc.stdout or "").strip()
    if not raw:
        return None
    return json.loads(raw)


def list_owned_repos() -> list[str]:
    repos: list[str] = []
    page = 1
    while page < 20:
        try:
            batch = _gh_json(f"user/repos?per_page=100&page={page}&affiliation=owner")
        except (RuntimeError, json.JSONDecodeError, subprocess.TimeoutExpired):
            break
        if not isinstance(batch, list) or not batch:
            break
        for doc in batch:
            if isinstance(doc, dict) and doc.get("owner", {}).get("login") == OWNER:
                name = doc.get("name")
                if name:
                    repos.append(str(name))
        if len(batch) < 100:
            break
        page += 1
    return sorted(set(repos))


def list_owned_forks() -> list[str]:
    forks: list[str] = []
    page = 1
    while page < 10:
        try:
            batch = _gh_json(f"user/repos?affiliation=owner&per_page=100&page={page}")
        except (RuntimeError, json.JSONDecodeError, subprocess.TimeoutExpired):
            break
        if not isinstance(batch, list) or not batch:
            break
        for doc in batch:
            if isinstance(doc, dict) and doc.get("fork"):
                full = doc.get("full_name")
                if full:
                    forks.append(str(full))
        if len(batch) < 100:
            break
        page += 1
    return forks


def delete_owned_forks(*, dry: bool = False) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for full in list_owned_forks():
        row = {"action": "delete_fork", "repo": full, "dry": dry}
        if dry:
            actions.append(row)
            _ledger_append({**row, "kind": "fork_delete_dry", "entity_id": full})
            continue
        proc = subprocess.run(
            ["gh", "repo", "delete", full, "--yes"],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        row["ok"] = proc.returncode == 0
        row["stderr"] = (proc.stderr or "").strip()[:240] or None
        actions.append(row)
        _ledger_append({
            **row,
            "kind": "fork_delete",
            "entity_id": full,
            "reason": "owned fork removed — ALL RIGHTS RESERVED",
        })
    return actions


def disable_forking(repo: str, *, dry: bool = False) -> dict[str, Any]:
    row = {"action": "disable_forking", "repo": f"{OWNER}/{repo}", "dry": dry}
    if dry:
        _ledger_append({**row, "kind": "fork_lock_dry", "entity_id": row["repo"]})
        return {**row, "ok": True}
    try:
        _gh_json(f"repos/{OWNER}/{repo}", method="PATCH", fields={"allow_forking": "false"})
        row["ok"] = True
        _ledger_append({
            **row,
            "kind": "fork_lock",
            "entity_id": row["repo"],
            "reason": "forking disabled account-wide",
        })
    except RuntimeError as exc:
        row["ok"] = False
        row["note"] = str(exc)[:240]
        _ledger_append({
            **row,
            "kind": "fork_lock_unavailable",
            "entity_id": row["repo"],
            "reason": "personal public repo — terms + LICENSE enforce",
        })
    return row


def cut_extra_branches(repo: str, *, dry: bool = False) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    try:
        branches = _gh_json(f"repos/{OWNER}/{repo}/branches?per_page=100")
    except (RuntimeError, json.JSONDecodeError, subprocess.TimeoutExpired):
        return actions
    if not isinstance(branches, list):
        return actions
    for doc in branches:
        if not isinstance(doc, dict):
            continue
        br = str(doc.get("name") or "")
        if not br or KEEP_RE.match(br):
            continue
        row = {"action": "delete_branch", "repo": f"{OWNER}/{repo}", "branch": br, "dry": dry}
        if dry:
            actions.append(row)
            _ledger_append({**row, "kind": "branch_cut_dry", "entity_id": f"{OWNER}/{repo}:{br}"})
            continue
        try:
            _gh_json(f"repos/{OWNER}/{repo}/git/refs/heads/{br}", method="DELETE")
            row["ok"] = True
        except RuntimeError as exc:
            row["ok"] = False
            row["error"] = str(exc)[:200]
        actions.append(row)
        _ledger_append({
            **row,
            "kind": "branch_cut",
            "entity_id": f"{OWNER}/{repo}:{br}",
            "reason": "extra branch cut — keep main/master/gh-pages only",
        })
    return actions


def _resolve_local(rel: str) -> Path:
    p = Path(rel)
    if p.is_absolute():
        return p
    if rel.startswith("../"):
        return SG / rel[3:]
    return INSTALL / rel


def _git_remote_owner_repo(path: Path) -> tuple[str, str] | None:
    git = path / ".git"
    if not git.exists():
        return None
    try:
        proc = subprocess.run(
            ["git", "-C", str(path), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        if proc.returncode != 0:
            return None
        m = GITHUB_REMOTE_RE.search(proc.stdout or "")
        if not m:
            return None
        return m.group(1), m.group(2).removesuffix(".git")
    except (OSError, subprocess.TimeoutExpired):
        return None


def _is_publish_clone(path: Path) -> bool:
    name = path.name
    return name.startswith(".pages-") or name.startswith(".profile-")


def scan_local_clones() -> list[dict[str, Any]]:
    doc = _load(DOCTRINE, {})
    manifest = _load(MANIFEST, {})
    findings: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(kind: str, path: Path, **meta: Any) -> None:
        key = f"{kind}:{path}"
        if key in seen:
            return
        seen.add(key)
        findings.append({
            "kind": kind,
            "path": str(path),
            "exists": path.exists() or path.is_symlink(),
            **meta,
        })

    for item in manifest.get("drop_sg_stubs") or []:
        rel = str(item.get("path") or "")
        if not rel:
            continue
        add("drop_sg_stub", _resolve_local(rel), reason=item.get("reason"))

    for item in manifest.get("consume_drop") or []:
        if str(item.get("id") or "") == "nested_newlatest" or str(item.get("path") or "") == "NewLatest":
            add("nested_newlatest", INSTALL / "NewLatest", reason=item.get("reason"))

    drop_clones = manifest.get("drop_publish_clones") or {}
    for pattern in drop_clones.get("glob") or [".pages-*", ".profile-*"]:
        for path in sorted(INSTALL.glob(pattern)):
            if path.is_dir():
                add("publish_clone", path, reason=drop_clones.get("reason"))

    remote_index: dict[str, list[str]] = {}

    def scan_repo_dir(repo_dir: Path) -> None:
        if not repo_dir.is_dir():
            return
        remote = _git_remote_owner_repo(repo_dir)
        if not remote:
            if _is_publish_clone(repo_dir):
                add("publish_clone_git", repo_dir, reason="stale pages publish mirror")
            return
        owner, name = remote
        slug = f"{owner}/{name}"
        remote_index.setdefault(slug, []).append(str(repo_dir))
        if owner == OWNER:
            if _is_publish_clone(repo_dir):
                add("publish_clone_git", repo_dir, slug=slug)
            elif len(remote_index[slug]) > 1:
                add("duplicate_owned_repo", repo_dir, slug=slug, duplicate_of=remote_index[slug][0])
        else:
            add("foreign_remote", repo_dir, slug=slug)

    targeted: list[Path] = [INSTALL]
    if SG.is_dir() and SG.resolve() != INSTALL.resolve():
        targeted.append(SG)
        for name in ("KILROY", "AmmoCode", "Grok16", "data", "compat", "NewLatest"):
            targeted.append(SG / name)
    for item in manifest.get("consume_drop") or []:
        rel = str(item.get("path") or "")
        if rel:
            targeted.append(_resolve_local(rel))
    seen_dirs: set[str] = set()
    for base in targeted:
        if not base.is_dir():
            continue
        key = str(base.resolve())
        if key in seen_dirs:
            continue
        seen_dirs.add(key)
        if (base / ".git").exists():
            scan_repo_dir(base)
        try:
            for child in base.iterdir():
                if not child.is_dir():
                    continue
                if child.name.startswith(".") and not _is_publish_clone(child):
                    if (child / ".git").exists():
                        scan_repo_dir(child)
                    continue
                if _is_publish_clone(child) or (child / ".git").exists():
                    scan_repo_dir(child)
        except OSError:
            pass

    for slug, paths in remote_index.items():
        if len(paths) > 1:
            for p in paths[1:]:
                add("duplicate_repo_tree", Path(p), slug=slug, canonical=paths[0])

    sg_stubs = [SG / "KILROY", SG / "data", SG / "compat", SG / "AmmoCode", SG / "Grok16"]
    for path in sg_stubs:
        if path.exists() and INSTALL.resolve() not in path.resolve().parents:
            canonical = INSTALL / path.name
            if canonical.exists():
                add("sg_stub", path, canonical=str(canonical))

    for route in doc.get("stale_pages_routes") or []:
        add("stale_pages_route", Path(route), virtual=True, rewrite_to=(_load(DOCTRINE).get("sovereign_primary") or {}).get("desktop"))

    return findings


BURN_KINDS = frozenset({
    "publish_clone",
    "publish_clone_git",
    "drop_sg_stub",
    "nested_newlatest",
    "sg_stub",
})

BURN_NEVER = frozenset({
    "NewLatest",
    "Hostess7",
    "lib",
    "panel",
    "data",
    "scripts",
})


def stale_pages_routes() -> list[str]:
    doc = _load(DOCTRINE, {})
    routes = [str(r) for r in (doc.get("stale_pages_routes") or []) if r]
    sweep = _load(INSTALL / "data" / "field-github-planet-sweep-doctrine.json", {})
    for rule in (sweep.get("stale_redirects") or {}).values():
        if not isinstance(rule, dict):
            continue
        for key in ("from_pages", "from"):
            val = rule.get(key)
            if val and str(val).startswith("http"):
                routes.append(str(val))
    seen: set[str] = set()
    out: list[str] = []
    for raw in routes:
        norm = raw.rstrip("/") + "/"
        if norm not in seen:
            seen.add(norm)
            out.append(norm)
    return out


def _burn_safe(path: Path) -> bool:
    try:
        resolved = path.resolve()
    except OSError:
        return False
    if resolved == INSTALL.resolve():
        return False
    if resolved == SG.resolve():
        return False
    if path.name in BURN_NEVER and resolved.parent == INSTALL.resolve():
        return False
    return True


def _burn_path(path: Path, *, kind: str, dry: bool, reason: str) -> dict[str, Any]:
    row = {"action": "burn", "kind": kind, "path": str(path), "dry": dry, "reason": reason}
    if not _burn_safe(path):
        row["ok"] = True
        row["skipped"] = "canonical_protected"
        return row
    if not path.exists() and not path.is_symlink():
        row["ok"] = True
        row["skipped"] = "missing"
        return row
    if dry:
        row["ok"] = True
        _ledger_append({**row, "kind": "burn_dry", "entity_id": str(path)})
        return row
    try:
        if path.is_symlink() or path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)
        row["ok"] = True
        _ledger_append({
            **row,
            "kind": "burn",
            "entity_id": str(path),
            "reason": reason,
        })
    except OSError as exc:
        row["ok"] = False
        row["error"] = str(exc)[:200]
        _ledger_append({
            **row,
            "kind": "burn_failed",
            "entity_id": str(path),
            "reason": str(exc)[:200],
        })
    return row


def burn_stale_local(*, dry: bool = False) -> dict[str, Any]:
    """Burn stale publish clones, SG stubs, and duplicate trees — true source only."""
    burned: list[dict[str, Any]] = []
    qemu_racks = _mod("lib/field-zachub-qemu-racks.py", "zachub_qemu_racks")
    if qemu_racks and hasattr(qemu_racks, "burn_stale_team_qemu"):
        try:
            qemu_burn = qemu_racks.burn_stale_team_qemu(dry_run=dry)
            burned.append({"action": "team_qemu_stubs", **qemu_burn})
        except (OSError, TypeError, ValueError) as exc:
            burned.append({"action": "team_qemu_stubs", "ok": False, "error": str(exc)[:200]})
    consolidate = _mod("lib/field-folder-consolidate.py", "folder_consolidate")
    if consolidate and hasattr(consolidate, "consolidate"):
        try:
            result = consolidate.consolidate(dry=dry)
            burned.append({"action": "consolidate", "ok": result.get("ok"), "dropped": result.get("dropped")})
        except (OSError, TypeError, ValueError) as exc:
            burned.append({"action": "consolidate", "ok": False, "error": str(exc)[:200]})

    for finding in scan_local_clones():
        kind = str(finding.get("kind") or "")
        if kind not in BURN_KINDS or finding.get("virtual"):
            continue
        path = Path(str(finding.get("path") or ""))
        reason = str(finding.get("reason") or "stale clone burned on exit")
        burned.append(_burn_path(path, kind=kind, dry=dry, reason=reason))

    burn_rows = [r for r in burned if r.get("action") == "burn"]
    return {
        "ok": not any(r.get("ok") is False for r in burn_rows),
        "schema": "field-zachub-burn/v1",
        "updated": _utc(),
        "dry_run": dry,
        "burned_count": len(burned),
        "burned": burned[:96],
    }


def load_pin_index() -> dict[str, dict[str, Any]]:
    doc = _load(DOCTRINE, {})
    pins: dict[str, dict[str, Any]] = {}
    port = os.environ.get("NEXUS_THREAT_PANEL_PORT", "9477")
    loopback = f"http://127.0.0.1:{port}"
    sovereign = (doc.get("sovereign_primary") or {}).get("desktop") or f"{loopback}/field"

    def sovereign_pin(name: str, pages_pin: str | None) -> str:
        if name == "Hostess7":
            return f"{loopback}/field"
        if name == "command":
            return f"{loopback}/command/"
        if name == "AmmoOS":
            return f"{loopback}/ammoos/"
        if pages_pin and pages_pin.startswith(loopback):
            return pages_pin
        slug = name.replace("_", "-").lower()
        return f"{loopback}/{slug}/"

    for rel in doc.get("pin_sources") or []:
        src = INSTALL / rel
        data = _load(src, {})
        rows = data.get("favorites") or data.get("repos") or []
        if isinstance(rows, dict):
            for name, row in rows.items():
                if not isinstance(row, dict):
                    continue
                slug = f"{OWNER}/{name}"
                pin = row.get("pin_url") or row.get("pages") or row.get("pages_url")
                pages_pin = pin
                pins[slug] = {
                    "repo": name,
                    "pin_url": sovereign_pin(name, pages_pin),
                    "pages_url": row.get("pages_url") or row.get("pages"),
                    "sovereign_url": sovereign_pin(name, pages_pin),
                    "true_source": "sovereign_loopback",
                    "github": row.get("github") or row.get("url") or f"https://github.com/{slug}",
                }
        elif isinstance(rows, list):
            for row in rows:
                if not isinstance(row, dict):
                    continue
                name = row.get("repo") or row.get("name")
                if not name:
                    continue
                slug = f"{OWNER}/{name}"
                pin = row.get("pin_url") or row.get("pages") or row.get("pages_url")
                pages_pin = pin
                pins[slug] = {
                    "repo": name,
                    "pin_url": sovereign_pin(name, pages_pin),
                    "pages_url": row.get("pages_url") or row.get("pages"),
                    "sovereign_url": sovereign_pin(name, pages_pin),
                    "true_source": "sovereign_loopback",
                    "github": row.get("github") or row.get("url") or f"https://github.com/{slug}",
                }
    return pins


def guard(*, dry: bool = False, use_gh: bool = True, record: bool = True) -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    local = scan_local_clones()
    gh_actions: dict[str, Any] = {
        "available": _gh_available() and use_gh,
        "fork_deletes": [],
        "fork_locks": [],
        "branch_cuts": [],
    }
    if gh_actions["available"]:
        gh_actions["fork_deletes"] = delete_owned_forks(dry=dry)
        for repo in list_owned_repos():
            gh_actions["fork_locks"].append(disable_forking(repo, dry=dry))
            gh_actions["branch_cuts"].extend(cut_extra_branches(repo, dry=dry))
    elif use_gh:
        _ledger_append({
            "kind": "gh_unavailable",
            "entity_id": OWNER,
            "action": "dry_local_only",
            "reason": "gh missing — local scan only",
        })

    counts = {
        "local_findings": len(local),
        "fork_deletes": len(gh_actions["fork_deletes"]),
        "fork_locks": len(gh_actions["fork_locks"]),
        "branch_cuts": len(gh_actions["branch_cuts"]),
        "owned_repos": len(gh_actions["fork_locks"]),
    }
    pins = load_pin_index()
    out = {
        "ok": True,
        "schema": "field-zachub-fork-guard/v1",
        "updated": _utc(),
        "title": doc.get("title"),
        "motto": doc.get("motto"),
        "product": doc.get("product") or "AmmoDrive",
        "owners": ["Grok", "Zac"],
        "owner": OWNER,
        "terms": doc.get("terms"),
        "dry_run": dry,
        "gh_available": gh_actions["available"],
        "fork_policy": doc.get("fork_policy"),
        "sovereign_primary": doc.get("sovereign_primary"),
        "stale_pages_routes": stale_pages_routes(),
        "pin_index": pins,
        "counts": counts,
        "local_findings": local[:96],
        "github_actions": gh_actions,
        "pin_index_count": len(pins),
        "api": doc.get("api"),
        "rewrite": doc.get("rewrite"),
    }
    if record:
        _save(PANEL, out)
        if record and not dry:
            _ledger_append({
                "kind": "guard_run",
                "entity_id": OWNER,
                "action": "guard_complete",
                "reason": f"fork guard run — local={counts['local_findings']} branch_cuts={counts['branch_cuts']}",
                "meta": counts,
            })
    return out


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    dry = "--dry" in sys.argv or cmd == "dry"
    no_gh = "--no-gh" in sys.argv
    no_record = "--no-record" in sys.argv

    if cmd in ("json", "panel", "guard", "dry"):
        out = guard(dry=dry or cmd == "dry", use_gh=not no_gh, record=not no_record)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    if cmd in ("burn", "burn-stale"):
        out = burn_stale_local(dry=dry or "--dry" in sys.argv)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("ok") else 1
    if cmd == "run":
        burn = burn_stale_local(dry=False)
        out = guard(dry=False, use_gh=not no_gh, record=not no_record)
        out["burn"] = burn
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("ok") else 1
    if cmd == "scan":
        out = {"ok": True, "findings": scan_local_clones(), "pin_index": load_pin_index()}
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    if cmd == "status":
        out = {
            "ok": True,
            "gh_available": _gh_available(),
            "owner": OWNER,
            "owned_repos": list_owned_repos() if _gh_available() else [],
            "owned_forks": list_owned_forks() if _gh_available() else [],
            "local_findings": len(scan_local_clones()),
            "panel": str(PANEL),
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "field-zachub-fork-guard.py [json|guard|dry|burn|run|scan|status] [--dry] [--no-gh] [--no-record]",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())