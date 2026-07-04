#!/usr/bin/env python3
"""AmmoDrive H7 storage — provision HOSTESS7_TEAM fieldstorage, mirror GitHub truth local."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-zachub-storage-doctrine.json"
PANEL = STATE / "field-zachub-storage-panel.json"
FAVORITES = INSTALL / "docs" / "github-favorites.json"
H7_DOCS = INSTALL / "Hostess7" / "docs"

TEAM = Path(os.environ.get("HOSTESS7_TEAM_FIELD", "/media/default/HOSTESS7_TEAM1/fieldstorage"))
TEAM_H7 = Path(os.environ.get("HOSTESS7_TEAM_H7_FIELD", "/media/default/HOSTESS7_TEAM/fieldstorage"))
QUBES = Path(os.environ.get("FIELD_QUBES_MOUNT", "/media/default/FIELD_QUBES"))
HOST_MIRROR = INSTALL / ".nexus-field-drive" / "nexus-field"

LIGHT_SYNC_NAMES = frozenset({
    "README.md", "README", "README.txt", "VERSION", "LICENSE", "LICENSE.md",
    "CHANGELOG.md", "RELEASE.md", "MANIFEST.sha256", "package.json", "Cargo.toml",
    "pyproject.toml", "CMakeLists.txt", "go.mod",
})


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


def _human_gb(n: int) -> float:
    return round(n / (1024 ** 3), 2)


def doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {})


def sg_root() -> Path:
    return INSTALL.resolve()


def _sibling_source(row: dict[str, Any]) -> Path | None:
    name = str(row.get("name") or "")
    if not name:
        return None
    env_key = str(row.get("env") or f"{name.upper()}_ROOT")
    env = os.environ.get(env_key, "").strip()
    if env:
        p = Path(env).expanduser()
        if p.is_dir():
            return p.resolve()
    inst = sg_root()
    if row.get("nested"):
        nested = inst / name
        if nested.is_dir():
            return nested.resolve()
    parent = inst.parent
    for candidate in (inst if name == "NewLatest" else None, inst / name, parent / name):
        if candidate and candidate.is_dir():
            return candidate.resolve()
    return None


def storage_bases() -> list[Path]:
    doc = doctrine()
    paths = doc.get("paths") or {}
    bases: list[Path] = []
    for raw in paths.get("team_mounts") or []:
        bases.append(Path(str(raw)))
    qf = paths.get("qubes_fieldstorage")
    if qf:
        bases.append(Path(str(qf)))
    bases.extend([TEAM, TEAM_H7, QUBES / "fieldstorage", HOST_MIRROR])
    seen: set[str] = set()
    out: list[Path] = []
    for b in bases:
        key = str(b)
        if key in seen:
            continue
        seen.add(key)
        out.append(b)
    return out


def _hundred_x_cfg() -> dict[str, Any]:
    gh = doctrine().get("github") or {}
    return gh.get("hundred_x") if isinstance(gh.get("hundred_x"), dict) else {}


def _hundred_x_active(argv: list[str] | None = None) -> bool:
    args = argv if argv is not None else sys.argv
    if "--100x" in args or os.environ.get("ZACHUB_100X", "").strip().lower() in ("1", "yes", "true"):
        return True
    return bool(_hundred_x_cfg().get("enabled"))


def primary_storage_bases(*, max_bases: int = 2, hundred_x: bool = False) -> list[Path]:
    """Writable mounts for provision — avoid fan-out copy to every witness root."""
    if hundred_x or _hundred_x_active():
        team = Path(os.environ.get("HOSTESS7_TEAM_FIELD", "/media/default/HOSTESS7_TEAM1/fieldstorage"))
        try:
            team.mkdir(parents=True, exist_ok=True)
            probe = team / ".zachub-write-probe"
            probe.write_text("ok\n", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return [team]
        except OSError:
            pass
        max_bases = 1
    picked: list[Path] = []
    for base in storage_bases():
        try:
            base.mkdir(parents=True, exist_ok=True)
            probe = base / ".zachub-write-probe"
            probe.write_text("ok\n", encoding="utf-8")
            probe.unlink(missing_ok=True)
        except OSError:
            continue
        picked.append(base)
        if len(picked) >= max_bases:
            break
    return picked or storage_bases()[:1]


def layout_paths(base: Path) -> dict[str, Path]:
    doc = doctrine()
    p = doc.get("paths") or {}
    truth = str(p.get("github_truth_subdir") or "zachub-github-truth")
    siblings = str(p.get("sg_siblings_subdir") or "zachub-sg-siblings")
    manifest = str(p.get("manifest_subdir") or "zachub-manifest")
    world = str(p.get("world_publish_subdir") or "world-publish")
    racks = str(p.get("racks_subdir") or "racks")
    root = base
    if base.name == "nexus-field":
        root = base
    elif base.name not in ("fieldstorage", "FIELD_QUBES") and "fieldstorage" not in str(base):
        root = base / "fieldstorage" if not (base / "fieldstorage").is_dir() else base
    return {
        "base": root,
        "github_truth": root / truth,
        "sg_siblings": root / siblings,
        "manifest": root / manifest,
        "world_publish": root / world,
        "racks": root / racks,
    }


def zachub_truth_roots() -> list[Path]:
    """Export targets for world + GitHub truth (used by field-github-isolation)."""
    doc = doctrine()
    sub = str((doc.get("paths") or {}).get("github_truth_subdir") or "zachub-github-truth")
    roots: list[Path] = []
    for base in storage_bases():
        if base.name == "nexus-field":
            roots.append(base / sub)
        elif base.is_dir() or not base.exists():
            layout = layout_paths(base)
            roots.append(layout["github_truth"])
    seen: set[str] = set()
    out: list[Path] = []
    for r in roots:
        key = str(r)
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def _product_name() -> str:
    doc = doctrine()
    branding = doc.get("branding") or {}
    return str(branding.get("product") or doc.get("product") or "AmmoDrive")


def _github_owner() -> str:
    gh = doctrine().get("github") or {}
    return str(gh.get("owner") or "ZacharyGeurts")


def all_github_repo_names(*, owner: str | None = None) -> list[str]:
    owner = owner or _github_owner()
    try:
        proc = subprocess.run(
            ["gh", "repo", "list", owner, "--limit", "200", "--json", "name,isFork"],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if proc.returncode != 0:
            return []
        rows = json.loads(proc.stdout or "[]")
        return [
            str(r.get("name") or "").strip()
            for r in rows
            if r.get("name") and not r.get("isFork")
        ]
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return []


def _git_clone_or_pull(url: str, dst: Path, *, depth: int | None = 1) -> dict[str, Any]:
    if (dst / ".git").is_dir():
        proc = subprocess.run(
            ["git", "-C", str(dst), "fetch", "--all", "--prune", "--tags"],
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        return {
            "action": "fetch",
            "ok": proc.returncode == 0,
            "path": str(dst),
            "head": _git_head(dst),
            "stderr": (proc.stderr or "").strip()[:240] if proc.returncode else "",
        }
    dst.parent.mkdir(parents=True, exist_ok=True)
    args = ["git", "clone"]
    if depth and depth > 0:
        args.extend(["--depth", str(depth)])
    args.extend([url, str(dst)])
    proc = subprocess.run(args, capture_output=True, text=True, timeout=900, check=False)
    return {
        "action": "clone",
        "ok": proc.returncode == 0,
        "path": str(dst),
        "head": _git_head(dst) if proc.returncode == 0 else None,
        "stderr": (proc.stderr or "").strip()[:240] if proc.returncode else "",
    }


def capacity_report(*, mount: str | None = None) -> dict[str, Any]:
    doc = doctrine()
    cap = doc.get("capacity") or {}
    mnt = mount or str(cap.get("team_primary_mount") or cap.get("nvme_mount") or "/")
    try:
        usage = shutil.disk_usage(mnt)
    except OSError as exc:
        return {"ok": False, "error": str(exc), "mount": mnt}
    reserve_pct = float(cap.get("reserve_pct") or 0.91)
    reserve = int(cap.get("zachub_reserve_gb") or 0)
    if reserve <= 0:
        reserve = int(_human_gb(usage.total) * reserve_pct)
    free_gb = _human_gb(usage.free)
    zachub_used = 0
    for base in primary_storage_bases(max_bases=2):
        layout = layout_paths(base)
        for key in ("github_truth", "sg_siblings", "manifest"):
            p = layout[key]
            if not p.is_dir():
                continue
            try:
                proc = subprocess.run(
                    ["du", "-sb", str(p)],
                    capture_output=True,
                    text=True,
                    timeout=12,
                    check=False,
                )
                if proc.returncode == 0:
                    zachub_used += int((proc.stdout or "0").split()[0])
                    continue
            except (OSError, subprocess.TimeoutExpired, ValueError):
                pass
            try:
                for row in p.glob("*"):
                    if row.is_file():
                        zachub_used += row.stat().st_size
            except OSError:
                pass
    used_gb = _human_gb(zachub_used)
    budget_left = round(max(0.0, min(reserve, free_gb) - used_gb), 2)
    pct_of_reserve = round((used_gb / reserve) * 100, 1) if reserve else 0.0
    return {
        "ok": True,
        "schema": "field-zachub-capacity/v1",
        "updated": _utc(),
        "mount": mnt,
        "product": _product_name(),
        "team": {
            "total_gb": _human_gb(usage.total),
            "used_gb": _human_gb(usage.used),
            "free_gb": free_gb,
        },
        "nvme": {
            "total_gb": _human_gb(usage.total),
            "used_gb": _human_gb(usage.used),
            "free_gb": free_gb,
        },
        "zachub": {
            "reserve_gb": reserve,
            "used_gb": used_gb,
            "budget_remaining_gb": budget_left,
            "pct_of_reserve": pct_of_reserve,
            "within_budget": used_gb <= reserve,
        },
        "branding": doc.get("branding") or {},
    }


def _git_head(path: Path) -> str | None:
    if not (path / ".git").exists():
        return None
    try:
        proc = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        if proc.returncode == 0:
            return (proc.stdout or "").strip() or None
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def _fired_repos() -> frozenset[str]:
    guard_doc = _load(INSTALL / "data" / "field-zachub-fork-guard-doctrine.json", {})
    return frozenset(str(r) for r in (guard_doc.get("fired_repos") or ["field"]) if r)


def burn_stale_truth(*, write: bool = True, dry_run: bool = False) -> dict[str, Any]:
    """Remove fired/stale repo trees from AmmoDrive truth — sovereign local source only."""
    fired = _fired_repos()
    burned: list[dict[str, Any]] = []
    for base in primary_storage_bases():
        layout = layout_paths(base)
        truth = layout["github_truth"]
        if not truth.is_dir():
            continue
        for repo_dir in sorted(truth.iterdir()):
            if not repo_dir.is_dir():
                continue
            name = repo_dir.name
            if name not in fired:
                continue
            row = {"repo": name, "path": str(repo_dir), "reason": "fired repo — burned on exit"}
            if dry_run or not write:
                row["dry"] = True
                burned.append(row)
                continue
            try:
                shutil.rmtree(repo_dir)
                row["ok"] = True
                burned.append(row)
            except OSError as exc:
                burned.append({**row, "ok": False, "error": str(exc)[:200]})
    return {
        "ok": all(r.get("ok", True) for r in burned if not r.get("dry")),
        "schema": "field-zachub-burn-truth/v1",
        "updated": _utc(),
        "dry_run": dry_run,
        "fired_repos": sorted(fired),
        "burned_count": len(burned),
        "burned": burned,
    }


_SYNC_IGNORE = shutil.ignore_patterns(
    ".git", "__pycache__", "node_modules", "target", "build", "dist", "*.o", "*.a",
    ".pages-*", ".profile-*",
)


def _light_sync(
    src: Path,
    dst: Path,
    *,
    dry_run: bool = False,
    full: bool = False,
    hundred_x: bool = False,
) -> list[str]:
    copied: list[str] = []
    if not src.is_dir():
        return copied
    if hundred_x and full and not dry_run:
        dst.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst, dirs_exist_ok=True, ignore=_SYNC_IGNORE)
        return [str(dst)]
    if not dry_run:
        dst.mkdir(parents=True, exist_ok=True)
    for item in sorted(src.iterdir()):
        if item.name.startswith(".") and item.name not in (".gitignore",):
            continue
        if item.is_file() and (item.name in LIGHT_SYNC_NAMES or item.suffix in (".md", ".json", ".txt")):
            hit = dst / item.name
            if dry_run:
                copied.append(str(hit))
            else:
                shutil.copy2(item, hit)
                copied.append(str(hit))
        elif full and item.is_dir() and item.name in ("bin", "lib", "data", "docs", "scripts", "config"):
            sub_dst = dst / item.name
            if dry_run:
                copied.append(str(sub_dst))
            else:
                shutil.copytree(item, sub_dst, dirs_exist_ok=True, ignore=_SYNC_IGNORE)
                copied.append(str(sub_dst))
    return copied


def _parallel_clone_jobs(
    jobs: list[tuple[str, str, Path, int]],
    *,
    parallel: int,
) -> list[dict[str, Any]]:
    if not jobs:
        return []
    workers = max(1, min(parallel, len(jobs)))
    out: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(_git_clone_or_pull, url, dst, depth=depth): repo
            for repo, url, dst, depth in jobs
        }
        for fut in as_completed(futures):
            repo = futures[fut]
            try:
                row = fut.result()
            except Exception as exc:
                row = {"ok": False, "repo": repo, "error": str(exc)[:200]}
            out.append({"repo": repo, **row})
    return out


def mirror_github_truth(
    *,
    write: bool = True,
    dry_run: bool = False,
    full: bool = False,
    hundred_x: bool = False,
) -> dict[str, Any]:
    doc = doctrine()
    fav_doc = _load(FAVORITES, {})
    favorites = list(fav_doc.get("favorites") or [])
    gh_cfg = doc.get("github") or {}
    hx = _hundred_x_cfg() if hundred_x or _hundred_x_active() else {}
    hundred_x = hundred_x or bool(hx)
    owner = _github_owner()
    product = _product_name()
    if gh_cfg.get("mirror_all_repos"):
        known = {str(f.get("repo") or f.get("name") or "") for f in favorites}
        for name in all_github_repo_names(owner=owner):
            if name and name not in known:
                favorites.append({
                    "star": True,
                    "name": name,
                    "repo": name,
                    "tag": "github mirror",
                    "url": f"https://github.com/{owner}/{name}",
                })
                known.add(name)
    written: list[str] = []
    errors: list[str] = []
    repo_manifests: list[dict[str, Any]] = []
    clones: list[dict[str, Any]] = []

    port = os.environ.get("NEXUS_THREAT_PANEL_PORT", "9477")
    sovereign_base = f"http://127.0.0.1:{port}"
    clone_depth = int(hx.get("clone_depth") if hundred_x and hx.get("clone_depth") is not None else gh_cfg.get("clone_depth") or 1)
    clone_parallel = int(hx.get("clone_parallel") or 12) if hundred_x else 1
    clone_on_full = bool(gh_cfg.get("clone_on_full", True))
    fired = _fired_repos()
    clone_jobs: list[tuple[str, str, Path, int]] = []
    pending_manifests: list[dict[str, Any]] = []

    for base in primary_storage_bases(hundred_x=hundred_x):
        layout = layout_paths(base)
        truth = layout["github_truth"]
        if dry_run:
            written.append(str(truth))
            continue
        if not write:
            continue
        try:
            truth.mkdir(parents=True, exist_ok=True)
            fav_copy = {
                **fav_doc,
                "zachub": True,
                "sovereign_base": sovereign_base,
                "product": product,
                "owners": ["Grok", "Zac"],
            }
            (truth / "github-favorites.json").write_text(
                json.dumps(fav_copy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
            )
            written.append(str(truth / "github-favorites.json"))

            for fav in favorites:
                repo = str(fav.get("repo") or fav.get("name") or "").strip()
                if not repo or repo in fired:
                    continue
                repo_dir = truth / repo
                repo_dir.mkdir(parents=True, exist_ok=True)
                manifest = {
                    "schema": "zachub-github-truth-repo/v1",
                    "updated": _utc(),
                    "product": product,
                    "owners": ["Grok", "Zac"],
                    "repo": repo,
                    "favorite": fav,
                    "sovereign": {
                        "panel": f"{sovereign_base}/field",
                        "api": f"{sovereign_base}/api/",
                        "zachub_storage": f"{sovereign_base}/api/field-zachub-storage",
                    },
                    "github_role": doc.get("github_role"),
                }
                src = _sibling_source({"name": repo, "repo": repo})
                if not src and repo == "Hostess7":
                    src = INSTALL
                has_local = bool(src and src.is_dir())
                if has_local:
                    manifest["local_source"] = str(src)
                    manifest["true_source"] = "local-mirror"
                    manifest["git_head"] = _git_head(src)
                    _light_sync(
                        src,
                        repo_dir / "local-mirror",
                        dry_run=False,
                        full=full or hundred_x,
                        hundred_x=hundred_x and bool(hx.get("full_local_sync", True)),
                    )
                if full and clone_on_full and write and not dry_run and not has_local:
                    clone_url = f"https://github.com/{owner}/{repo}.git"
                    if hundred_x and clone_parallel > 1:
                        clone_jobs.append((repo, clone_url, repo_dir / "git-clone", clone_depth))
                        pending_manifests.append(manifest)
                    else:
                        clone_row = _git_clone_or_pull(
                            clone_url,
                            repo_dir / "git-clone",
                            depth=clone_depth,
                        )
                        manifest["git_clone"] = clone_row
                        clones.append({"repo": repo, **clone_row})
                (repo_dir / "manifest.json").write_text(
                    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
                )
                written.append(str(repo_dir / "manifest.json"))
                repo_manifests.append({"repo": repo, "path": str(repo_dir)})

            index = {
                "schema": "zachub-github-truth-index/v1",
                "updated": _utc(),
                "product": product,
                "owners": ["Grok", "Zac"],
                "motto": doc.get("motto"),
                "repo_count": len(repo_manifests),
                "repos": repo_manifests,
                "sovereign_primary": doc.get("sovereign_primary") or {},
                "capacity": capacity_report(),
            }
            (truth / "index.json").write_text(
                json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
            )
            written.append(str(truth / "index.json"))
        except OSError as exc:
            errors.append(f"{truth}: {exc}")

    if clone_jobs and write and not dry_run:
        parallel_rows = _parallel_clone_jobs(clone_jobs, parallel=clone_parallel)
        by_repo = {r["repo"]: r for r in parallel_rows}
        clones.extend(parallel_rows)
        for manifest in pending_manifests:
            repo = str(manifest.get("repo") or "")
            if repo in by_repo:
                manifest["git_clone"] = by_repo[repo]

    return {
        "ok": not errors or bool(written),
        "schema": "field-zachub-github-truth/v1",
        "updated": _utc(),
        "dry_run": dry_run,
        "hundred_x": hundred_x,
        "written_count": len(written),
        "written": written[:48],
        "errors": errors,
        "repo_count": len(favorites),
        "clone_count": len(clones),
        "clone_parallel": clone_parallel if hundred_x else 1,
        "clones": clones[:32],
    }


def sync_sg_siblings(
    *,
    write: bool = True,
    dry_run: bool = False,
    full: bool = False,
    hundred_x: bool = False,
) -> dict[str, Any]:
    doc = doctrine()
    rows = list(doc.get("sg_siblings") or [])
    synced: list[dict[str, Any]] = []
    skipped: list[str] = []
    errors: list[str] = []

    hundred_x = hundred_x or _hundred_x_active()
    for base in primary_storage_bases(hundred_x=hundred_x):
        layout = layout_paths(base)
        sib_root = layout["sg_siblings"]
        if dry_run:
            synced.append({"base": str(sib_root), "dry_run": True})
            continue
        if write and not dry_run:
            sib_root.mkdir(parents=True, exist_ok=True)

        for row in rows:
            name = str(row.get("name") or "")
            src = _sibling_source(row)
            if not src or not src.is_dir():
                skipped.append(name)
                continue
            dst = sib_root / name
            try:
                if dry_run:
                    synced.append({"name": name, "src": str(src), "dst": str(dst)})
                    continue
                if write:
                    copied = _light_sync(
                        src,
                        dst,
                        dry_run=False,
                        full=full or hundred_x,
                        hundred_x=hundred_x,
                    )
                    manifest = {
                        "schema": "zachub-sg-sibling/v1",
                        "updated": _utc(),
                        "name": name,
                        "repo": row.get("repo"),
                        "source": str(src),
                        "destination": str(dst),
                        "git_head": _git_head(src),
                        "copied": copied[:24],
                        "product": _product_name(),
                        "owners": ["Grok", "Zac"],
                    }
                    (dst / "zachub-sync-manifest.json").write_text(
                        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
                    )
                    synced.append(manifest)
            except OSError as exc:
                errors.append(f"{name}: {exc}")

    return {
        "ok": not errors or bool(synced),
        "schema": "field-zachub-sg-sync/v1",
        "updated": _utc(),
        "dry_run": dry_run,
        "synced_count": len(synced),
        "synced": synced[:32],
        "skipped": skipped,
        "errors": errors,
    }


def provision_layout(*, write: bool = True, dry_run: bool = False) -> dict[str, Any]:
    doc = doctrine()
    created: list[str] = []
    bases_report: list[dict[str, Any]] = []

    for raw_base in primary_storage_bases(max_bases=3):
        layout = layout_paths(raw_base)
        base = layout["base"]
        row = {"base": str(base), "paths": {k: str(v) for k, v in layout.items() if k != "base"}}
        bases_report.append(row)
        if dry_run:
            for key in ("github_truth", "sg_siblings", "manifest", "world_publish", "racks"):
                created.append(str(layout[key]))
            continue
        if not write:
            continue
        try:
            for key in ("github_truth", "sg_siblings", "manifest", "world_publish", "racks"):
                p = layout[key]
                p.mkdir(parents=True, exist_ok=True)
                created.append(str(p))
            stamp = layout["manifest"] / "provision.json"
            stamp.write_text(json.dumps({
                "schema": "zachub-provision-stamp/v1",
                "updated": _utc(),
                "product": _product_name(),
                "owners": ["Grok", "Zac"],
                "base": str(base),
                "layout": {k: str(v) for k, v in layout.items()},
            }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            created.append(str(stamp))
        except OSError as exc:
            row["error"] = str(exc)

    return {
        "ok": True,
        "schema": "field-zachub-provision-layout/v1",
        "updated": _utc(),
        "dry_run": dry_run,
        "branding": doc.get("branding") or {},
        "bases": bases_report,
        "created_count": len(created),
        "created": created[:48],
    }


def provision(
    *,
    write: bool = True,
    dry_run: bool = False,
    full: bool = False,
    hundred_x: bool = False,
) -> dict[str, Any]:
    hundred_x = hundred_x or _hundred_x_active()
    if hundred_x:
        full = True
    burn = burn_stale_truth(write=write and not dry_run, dry_run=dry_run)
    layout = provision_layout(write=write, dry_run=dry_run)
    mirror = mirror_github_truth(
        write=write and not dry_run,
        dry_run=dry_run,
        full=full,
        hundred_x=hundred_x,
    )
    siblings = sync_sg_siblings(
        write=write and not dry_run,
        dry_run=dry_run,
        full=full,
        hundred_x=hundred_x,
    )
    cap = capacity_report()

    out = {
        "ok": layout.get("ok") and mirror.get("ok") and siblings.get("ok"),
        "schema": "field-zachub-storage/v1",
        "updated": _utc(),
        "product": _product_name(),
        "owners": ["Grok", "Zac"],
        "motto": doctrine().get("motto"),
        "dry_run": dry_run,
        "full": full,
        "hundred_x": hundred_x,
        "burn_stale": burn,
        "layout": layout,
        "github_truth": mirror,
        "sg_siblings": siblings,
        "capacity": cap,
        "zachub_truth_roots": [str(p) for p in zachub_truth_roots()],
    }
    if write and not dry_run:
        _save(PANEL, out)
        api_dst = H7_DOCS / "api" / "field-zachub-storage.json"
        api_dst.parent.mkdir(parents=True, exist_ok=True)
        api_dst.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def panel(*, write: bool = True) -> dict[str, Any]:
    cached = _load(PANEL, {})
    if cached.get("schema") == "field-zachub-storage/v1":
        cached["capacity"] = capacity_report()
        return cached
    return provision(write=write, dry_run=True)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    dry_run = "--dry-run" in sys.argv or os.environ.get("ZACHUB_DRY_RUN", "").strip() in ("1", "yes")
    full = "--full" in sys.argv or "--100x" in sys.argv
    hundred_x = _hundred_x_active()

    if cmd in ("json", "panel", "status"):
        print(json.dumps(panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("capacity", "report"):
        print(json.dumps(capacity_report(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("layout", "provision-layout"):
        print(json.dumps(provision_layout(dry_run=dry_run), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("mirror", "github-truth"):
        print(json.dumps(mirror_github_truth(dry_run=dry_run), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("sync", "siblings"):
        print(json.dumps(sync_sg_siblings(dry_run=dry_run), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("provision", "apply"):
        print(json.dumps(
            provision(dry_run=dry_run, full=full, hundred_x=hundred_x),
            ensure_ascii=False,
            indent=2,
        ))
        return 0
    if cmd == "roots":
        print(json.dumps({"roots": [str(p) for p in zachub_truth_roots()]}, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "field-zachub-storage.py [json|provision|capacity|mirror|sync|roots] [--dry-run] [--full] [--100x]",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())