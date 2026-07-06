#!/usr/bin/env python3
"""Planet GitHub sweep — stale trick, canonical indexes, true DNS/DHCP rows."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-github-planet-sweep-doctrine.json"
PANEL = STATE / "field-github-planet-sweep-panel.json"
INDEX = STATE / "field-github-planet-index.json"
OWNER = "ZacharyGeurts"
CANONICAL_RE = re.compile(r'rel="canonical"\s+href="([^"]+)"', re.I)
REFRESH_RE = re.compile(r'content="\s*\d+;\s*url=([^"]+)"', re.I)
REDIRECT_HUB_RE = re.compile(r"redirect hub|AmmoOS manual|canonical docs", re.I)
FIRED_PAGE_RE = re.compile(r"FIRED|route destroyed|Stale field route", re.I)


def _canonical_desktop(doc: dict[str, Any] | None = None, *, prefer: str = "pages") -> str:
    doc = doc or _load(DOCTRINE, {})
    raw = doc.get("canonical_desktop")
    if isinstance(raw, dict):
        if prefer == "sovereign":
            return str(raw.get("sovereign") or raw.get("primary") or raw.get("pages") or "")
        return str(raw.get("pages") or raw.get("sovereign") or raw.get("primary") or "")
    sovereign = doc.get("sovereign_primary")
    if isinstance(sovereign, dict):
        sovereign = sovereign.get("panel") or sovereign.get("desktop") or sovereign.get("primary")
    if prefer == "sovereign" and sovereign:
        return str(sovereign)
    return str(raw or sovereign or "")


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


def _gh_json(path: str, *, timeout: float = 60.0) -> Any:
    proc = subprocess.run(
        ["gh", "api", path],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "gh api failed")
    return json.loads(proc.stdout or "null")


def _gh_all_repos() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page = 1
    while page < 20:
        try:
            batch = _gh_json(f"users/{OWNER}/repos?per_page=100&page={page}&sort=updated")
        except (RuntimeError, json.JSONDecodeError, subprocess.TimeoutExpired):
            break
        if not isinstance(batch, list) or not batch:
            break
        for doc in batch:
            if isinstance(doc, dict):
                rows.append({
                    "slug": doc.get("full_name") or f"{OWNER}/{doc.get('name')}",
                    "name": doc.get("name"),
                    "archived": bool(doc.get("archived")),
                    "html_url": doc.get("html_url"),
                    "default_branch": doc.get("default_branch") or "main",
                    "has_pages": bool(doc.get("has_pages")),
                    "description": doc.get("description") or "",
                    "source": "gh_api",
                })
        if len(batch) < 100:
            break
        page += 1
    return rows


def _pages_url(repo_name: str) -> str:
    return f"https://{OWNER.lower()}.github.io/{repo_name}/"


def _catalog_from_hub(catalog: dict[str, dict[str, Any]]) -> None:
    hub = _load(INSTALL / "data" / "ammoos-pages-hub.json", {})
    for key, spec in (hub.get("repos") or {}).items():
        if not isinstance(spec, dict):
            continue
        slug = f"{OWNER}/{key}"
        pages = str(spec.get("pages_url") or spec.get("url") or _pages_url(key)).strip()
        git = str(spec.get("git_repo") or spec.get("github") or f"https://github.com/{slug}").strip()
        catalog[slug] = {
            **catalog.get(slug, {}),
            "slug": slug,
            "name": key,
            "repo_url": git if git.startswith("https://github.com") else f"https://github.com/{slug}",
            "pages_url": pages,
            "pages_mode": spec.get("pages_mode") or "redirect_hub",
            "canonical_manual": str(hub.get("canonical_base") or "") + str(spec.get("ammoos_page") or ""),
            "title": spec.get("title") or key,
            "pages_mirror": spec.get("pages_mirror"),
            "source": "ammoos-pages-hub",
        }


def _catalog_from_old_projects(catalog: dict[str, dict[str, Any]]) -> None:
    doc = _load(INSTALL / "Hostess7/data/hostess7-old-projects.json", {})
    for proj in [doc.get("main_project")] + list(doc.get("old_projects") or []):
        if not isinstance(proj, dict):
            continue
        repo = str(proj.get("repo") or "").strip()
        if not repo.startswith("https://github.com/"):
            continue
        slug = repo.replace("https://github.com/", "")
        name = slug.split("/", 1)[-1]
        catalog[slug] = {
            **catalog.get(slug, {}),
            "slug": slug,
            "name": name,
            "repo_url": repo,
            "pages_url": str(proj.get("pages") or _pages_url(name)),
            "title": proj.get("name") or name,
            "tag": proj.get("tag"),
            "source": "hostess7-old-projects",
        }


def _catalog_from_favorites(catalog: dict[str, dict[str, Any]]) -> None:
    fav = _load(INSTALL / "docs" / "github-favorites.json", {})
    for row in fav.get("favorites") or []:
        if not isinstance(row, dict):
            continue
        repo = str(row.get("repo") or row.get("name") or "").strip()
        if not repo:
            continue
        slug = repo if "/" in repo else f"{OWNER}/{repo}"
        catalog[slug] = {
            **catalog.get(slug, {}),
            "slug": slug,
            "name": slug.split("/", 1)[-1],
            "repo_url": row.get("repo_url") or f"https://github.com/{slug}",
            "pages_url": row.get("pages_url") or row.get("pin_url") or _pages_url(slug.split("/", 1)[-1]),
            "title": row.get("tag") or slug,
            "source": "github-favorites",
        }


def _catalog_from_stack_index(catalog: dict[str, dict[str, Any]]) -> None:
    idx = _load(INSTALL / "H7updater/data/h7updater-stack-index.json", {})
    for ent in idx.get("entries") or []:
        if not isinstance(ent, dict):
            continue
        slug = str(ent.get("github") or "").strip()
        if not slug:
            continue
        name = slug.split("/", 1)[-1]
        catalog[slug] = {
            **catalog.get(slug, {}),
            "slug": slug,
            "name": name,
            "repo_url": ent.get("repo_url") or f"https://github.com/{slug}",
            "pages_url": ent.get("pages_url") or _pages_url(name),
            "title": ent.get("name") or ent.get("role") or name,
            "source": "h7updater-stack-index",
        }


def build_catalog(*, use_gh: bool = True) -> dict[str, dict[str, Any]]:
    catalog: dict[str, dict[str, Any]] = {}
    _catalog_from_hub(catalog)
    _catalog_from_old_projects(catalog)
    _catalog_from_favorites(catalog)
    _catalog_from_stack_index(catalog)
    if use_gh:
        for row in _gh_all_repos():
            slug = str(row.get("slug") or "")
            if not slug:
                continue
            name = slug.split("/", 1)[-1]
            catalog[slug] = {
                **catalog.get(slug, {}),
                **row,
                "repo_url": row.get("html_url") or f"https://github.com/{slug}",
                "pages_url": catalog.get(slug, {}).get("pages_url") or _pages_url(name),
            }
    doc = _load(DOCTRINE, {})
    runtime = set(doc.get("runtime_repos") or [])
    runtime.add("AmmoOS")
    for slug, row in catalog.items():
        name = row.get("name") or slug.split("/", 1)[-1]
        if row.get("pages_mode"):
            continue
        if name == "AmmoOS":
            row["pages_mode"] = "canonical_manual"
        elif name in runtime:
            row["pages_mode"] = "runtime"
        else:
            row["pages_mode"] = "redirect_hub"
    return catalog


def _fetch_html(url: str, *, timeout: float = 6.0) -> tuple[int | None, str]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FieldPlanetSweep/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(65536).decode("utf-8", errors="replace")
            return resp.status, body
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read(8192).decode("utf-8", errors="replace")
        except OSError:
            body = ""
        return exc.code, body
    except (urllib.error.URLError, OSError, TimeoutError):
        return None, ""


def _canonical_from_html(body: str) -> str | None:
    m = CANONICAL_RE.search(body or "")
    if m:
        return m.group(1).strip()
    m = REFRESH_RE.search(body or "")
    if m:
        return m.group(1).strip()
    return None


def _stale_rule(slug: str, path_suffix: str = "") -> dict[str, Any] | None:
    doc = _load(DOCTRINE, {})
    redirects = doc.get("stale_redirects") or {}
    key = f"{slug}{path_suffix}" if path_suffix else slug
    rule = redirects.get(key) or redirects.get(slug)
    return rule if isinstance(rule, dict) else None


def _analyze_repo(slug: str, row: dict[str, Any], *, probe: bool = True) -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    name = row.get("name") or slug.split("/", 1)[-1]
    pages_url = str(row.get("pages_url") or _pages_url(name)).rstrip("/") + "/"
    repo_url = str(row.get("repo_url") or f"https://github.com/{slug}")
    pages_mode = str(row.get("pages_mode") or "redirect_hub")
    stale_rule = _stale_rule(slug)
    out: dict[str, Any] = {
        "slug": slug,
        "name": name,
        "repo_url": repo_url,
        "pages_url": pages_url,
        "pages_mode": pages_mode,
        "archived": bool(row.get("archived")),
        "canonical_pages": pages_url,
        "canonical_repo": repo_url,
        "stale": False,
        "stale_kind": None,
        "redirect_to": None,
        "ingress": doc.get("ingress_policy") or "quarantine_not_kill",
    }
    if stale_rule:
        out.update({
            "stale": True,
            "stale_kind": stale_rule.get("kind") or "repo_fired",
            "redirect_to": stale_rule.get("to"),
            "canonical_pages": stale_rule.get("to") or _canonical_desktop(doc, prefer="sovereign"),
            "witness": stale_rule.get("witness"),
            "reason": stale_rule.get("reason"),
            "refire": bool(stale_rule.get("refire")),
        })
        return out

    manual = str(row.get("canonical_manual") or doc.get("canonical_manual") or "")
    if pages_mode == "redirect_hub":
        out["canonical_pages"] = manual or pages_url
    if not probe:
        return out

    status, body = _fetch_html(pages_url)
    out["pages_status"] = status
    out["pages_live"] = bool(status and status < 400)
    canon = _canonical_from_html(body)
    if canon:
        out["html_canonical"] = canon

    # Runtime surfaces stay live — never infer stale from page HTML.
    if pages_mode in ("runtime", "canonical_manual"):
        out["running"] = out["pages_live"]
        return out

    if body and FIRED_PAGE_RE.search(body):
        out["fired"] = True
        out["stale_kind"] = "repo_fired"
        out["redirect_to"] = canon or out.get("canonical_pages")
        return out

    if status and status >= 400:
        out["stale"] = True
        out["stale_kind"] = "pages_missing"
        out["redirect_to"] = manual or doc.get("canonical_manual")
    elif body and not REDIRECT_HUB_RE.search(body):
        out["stale"] = True
        out["stale_kind"] = "not_redirect_hub"
        out["redirect_to"] = manual or doc.get("canonical_manual")
    elif canon and manual and not canon.rstrip("/").startswith(manual.rstrip("/").split("/")[0]):
        out["stale"] = True
        out["stale_kind"] = "wrong_canonical"
        out["redirect_to"] = manual or canon
    return out


def _dns_index_rows(catalog: dict[str, dict[str, Any]], analyzed: list[dict[str, Any]]) -> list[dict[str, Any]]:
    doc = _load(DOCTRINE, {})
    truth = str(doc.get("truth_dns") or "127.0.0.1")
    rows: list[dict[str, Any]] = []
    for dom in ("github.com", "api.github.com", "raw.githubusercontent.com", "github.io"):
        rows.append({
            "kind": "dns",
            "name": dom,
            "type": "A" if dom != "github.io" else "CNAME",
            "value": truth if dom != "github.io" else f"{OWNER.lower()}.github.io",
            "authority": "hostess7_truth",
            "ttl": 300,
            "scope": "planet",
        })
    seen: set[str] = set()
    for item in analyzed:
        slug = item.get("slug") or ""
        name = item.get("name") or slug.split("/", 1)[-1]
        host = f"{name.lower()}.github.field"
        if host in seen:
            continue
        seen.add(host)
        canon = str(item.get("canonical_pages") or item.get("pages_url") or "")
        rows.append({
            "kind": "dns",
            "name": host,
            "type": "CNAME",
            "value": canon.replace("https://", "").rstrip("/") or f"{OWNER.lower()}.github.io/{name}",
            "authority": "hostess7_truth",
            "ttl": 300,
            "repo_slug": slug,
            "stale": bool(item.get("stale")),
            "redirect_to": item.get("redirect_to"),
        })
    return rows


def _dhcp_index_rows(analyzed: list[dict[str, Any]]) -> list[dict[str, Any]]:
    doc = _load(DOCTRINE, {})
    dns_opt = list(doc.get("dhcp_dns_option") or ["127.0.0.1"])
    rows: list[dict[str, Any]] = []
    for i, item in enumerate(analyzed):
        slug = str(item.get("slug") or "")
        rows.append({
            "kind": "dhcp",
            "lease_id": f"github-{slug.replace('/', '-')}",
            "mac": f"02:00:5e:7f:{(i >> 8) & 0xff:02x}:{i & 0xff:02x}",
            "ip": f"10.47.{(i >> 8) & 0xff}.{max(2, i & 0xff)}",
            "dns": dns_opt,
            "hostname": (item.get("name") or "repo").lower(),
            "repo_slug": slug,
            "canonical_pages": item.get("canonical_pages"),
            "authority": "hostess7",
            "quarantine": False,
            "ingress_policy": doc.get("ingress_policy") or "quarantine_not_kill",
            "absorbed": True,
        })
    return rows


def re_fire_enabled() -> bool:
    doc = _load(DOCTRINE, {})
    rf = doc.get("re_fire") or {}
    if rf.get("never_disable"):
        return True
    if os.environ.get("NEXUS_REFIRE_DISABLE", "").strip().lower() in ("1", "yes", "on"):
        return False
    return bool(rf.get("enabled", True))


def _refire_targets(analyzed: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    doc = _load(DOCTRINE, {})
    rf = doc.get("re_fire") or {}
    redirects = doc.get("stale_redirects") or {}
    targets: list[dict[str, Any]] = []
    seen: set[str] = set()
    for slug in rf.get("targets") or []:
        slug = str(slug)
        if slug in seen:
            continue
        seen.add(slug)
        rule = redirects.get(slug) or {}
        targets.append({
            "slug": slug,
            "to": rule.get("to") or _canonical_desktop(doc, prefer="sovereign"),
            "refire": bool(rule.get("refire", True)),
        })
    if analyzed:
        for item in analyzed:
            if not item.get("refire"):
                continue
            slug = str(item.get("slug") or "")
            if slug in seen:
                continue
            seen.add(slug)
            targets.append({
                "slug": slug,
                "to": item.get("redirect_to") or _canonical_desktop(doc, prefer="sovereign"),
                "refire": True,
            })
    return targets


def refire_stale(*, execute: bool = False, analyzed: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """RE-FIRE stale routes — wipe gh-pages tombstone, archive. Enabled; never_disable."""
    doc = _load(DOCTRINE, {})
    rf = doc.get("re_fire") or {}
    enabled = re_fire_enabled()
    targets = _refire_targets(analyzed)
    script = INSTALL / str(rf.get("module") or "scripts/fire-field-repo.sh")
    mode = str(rf.get("mode") or "refire")
    results: list[dict[str, Any]] = []

    for t in targets:
        slug = str(t.get("slug") or "")
        repo = slug.split("/", 1)[-1] if "/" in slug else slug
        canonical = str(t.get("to") or _canonical_desktop(doc, prefer="sovereign") or "")
        row: dict[str, Any] = {
            "slug": slug,
            "repo": repo,
            "canonical": canonical,
            "refire": True,
            "executed": False,
        }
        if execute and enabled and script.is_file():
            env = {
                **os.environ,
                "NEXUS_INSTALL_ROOT": str(INSTALL),
                "NEXUS_STATE_DIR": str(STATE),
                "FIELD_GITHUB_REPO": slug,
                "HOSTESS7_CANONICAL_DESKTOP": canonical,
            }
            try:
                proc = subprocess.run(
                    ["bash", str(script), mode],
                    cwd=str(INSTALL),
                    capture_output=True,
                    text=True,
                    timeout=180,
                    env=env,
                    check=False,
                )
                row["executed"] = proc.returncode == 0
                row["rc"] = proc.returncode
                row["stdout"] = (proc.stdout or "")[-800:]
                if proc.returncode != 0:
                    row["stderr"] = (proc.stderr or "")[-400:]
            except (OSError, subprocess.TimeoutExpired) as exc:
                row["error"] = str(exc)[:200]
        results.append(row)

    if execute and results:
        reg = _mod("lib/field-endpoint-registry.py", "endpoint_registry")
        if reg and hasattr(reg, "record"):
            for row in results:
                if not row.get("executed"):
                    continue
                try:
                    reg.record(
                        layer="pages",
                        kind="repo_fired",
                        entity_id=row["slug"],
                        from_val=f"https://{OWNER.lower()}.github.io/{row['repo']}/",
                        to_val=row.get("canonical"),
                        witness="re-fire",
                        reason="RE-FIRE — stale route destroyed; canonical only",
                    )
                except (OSError, TypeError, ValueError):
                    pass
            if hasattr(reg, "propagate_pages"):
                try:
                    reg.propagate_pages(witness="re-fire")
                except (OSError, TypeError):
                    pass

    return {
        "ok": enabled,
        "schema": "field-github-planet-refire/v1",
        "updated": _utc(),
        "re_fire": {
            "enabled": enabled,
            "never_disable": bool(rf.get("never_disable")),
            "execute": execute,
            "module": str(script.relative_to(INSTALL)) if script.is_file() else str(rf.get("module")),
            "mode": mode,
            "target_count": len(results),
            "executed_count": sum(1 for r in results if r.get("executed")),
        },
        "targets": results,
    }


def _record_stale_fixes(analyzed: list[dict[str, Any]], *, witness: str = "field-github-planet-sweep") -> int:
    reg = _mod("lib/field-endpoint-registry.py", "endpoint_registry")
    if not reg or not hasattr(reg, "record"):
        return 0
    recorded = 0
    for item in analyzed:
        if not item.get("stale") or not item.get("redirect_to"):
            continue
        slug = str(item.get("slug") or "")
        try:
            reg.record(
                layer="pages",
                kind=str(item.get("stale_kind") or "relocate"),
                entity_id=slug,
                from_val=item.get("pages_url"),
                to_val=item.get("redirect_to"),
                witness=item.get("witness") or witness,
                reason=str(item.get("reason") or f"planet sweep stale fix — {item.get('stale_kind')}"),
            )
            recorded += 1
        except (OSError, TypeError, ValueError):
            pass
    if recorded and hasattr(reg, "propagate_pages"):
        try:
            reg.propagate_pages(witness=witness)
        except (OSError, TypeError):
            pass
    return recorded


def sweep(
    *,
    probe: bool = True,
    record_fixes: bool = True,
    use_gh: bool = True,
    refire: bool = False,
) -> dict[str, Any]:
    catalog = build_catalog(use_gh=use_gh)
    analyzed = [_analyze_repo(slug, row, probe=probe) for slug, row in sorted(catalog.items())]
    stale = [x for x in analyzed if x.get("stale")]
    dns_rows = _dns_index_rows(catalog, analyzed)
    dhcp_rows = _dhcp_index_rows(analyzed)
    recorded = _record_stale_fixes(stale) if record_fixes and stale else 0

    doc = _load(DOCTRINE, {})
    refire_out = refire_stale(execute=refire, analyzed=stale) if re_fire_enabled() else None

    scale: dict[str, Any] = {}
    try:
        scale = (_mod("lib/field-world-dns-dhcp-scale.py", "world_scale") or type("", (), {}))
        if hasattr(scale, "build_scale"):
            scale = scale.build_scale()
        else:
            scale = {}
    except Exception:
        scale = _load(STATE / "field-world-dns-dhcp-scale-panel.json", {})

    index_doc = {
        "schema": "field-github-planet-index/v1",
        "updated": _utc(),
        "owner": OWNER,
        "repo_count": len(analyzed),
        "stale_count": len(stale),
        "dns_record_count": len(dns_rows),
        "dhcp_lease_count": len(dhcp_rows),
        "repos": analyzed,
        "dns_index": dns_rows,
        "dhcp_index": dhcp_rows,
    }
    _save(INDEX, index_doc)

    out = {
        "ok": True,
        "schema": "field-github-planet-sweep/v1",
        "updated": _utc(),
        "title": doc.get("title"),
        "motto": doc.get("motto"),
        "boss": doc.get("boss", "hostess7"),
        "ingress_policy": doc.get("ingress_policy"),
        "truth_dns": doc.get("truth_dns"),
        "counts": {
            "repos_cataloged": len(analyzed),
            "stale_detected": len(stale),
            "stale_recorded": recorded,
            "dns_index_rows": len(dns_rows),
            "dhcp_index_rows": len(dhcp_rows),
            "runtime_repos": sum(1 for x in analyzed if x.get("pages_mode") == "runtime"),
            "redirect_hubs": sum(1 for x in analyzed if x.get("pages_mode") == "redirect_hub"),
        },
        "stale_repos": stale[:48],
        "github_index": index_doc,
        "true_dns_dhcp": {
            "dns_authority": "hostess7_truth",
            "dhcp_authority": "hostess7",
            "dns_option_6": doc.get("truth_dns"),
            "never_kill_ingress": True,
            "quarantine_stale": True,
            "planet_scope": True,
        },
        "world_scale": scale.get("current") if isinstance(scale, dict) else {},
        "re_fire": refire_out.get("re_fire") if refire_out else {"enabled": re_fire_enabled(), "never_disable": True},
        "refire_targets": (refire_out or {}).get("targets") or [],
        "api": doc.get("api"),
    }
    _save(PANEL, out)
    return out


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    fast = "--no-probe" in sys.argv or "--fast" in sys.argv
    no_gh = "--no-gh" in sys.argv
    no_record = "--no-record" in sys.argv

    do_refire = cmd in ("refire", "re-fire", "re_fire") or "--refire" in sys.argv

    if cmd in ("json", "panel", "sweep"):
        out = sweep(
            probe=not fast,
            record_fixes=not no_record,
            use_gh=not no_gh,
            refire=do_refire,
        )
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    if do_refire:
        panel_data = _load(PANEL, {})
        stale = panel_data.get("stale_repos") or []
        if not stale:
            stale = [x for x in (sweep(probe=fast, record_fixes=False, use_gh=not no_gh).get("stale_repos") or [])]
        out = refire_stale(execute=True, analyzed=stale)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("ok") else 1
    if cmd == "index":
        out = _load(INDEX, {})
        if not out.get("repos"):
            out = sweep(probe=not fast, record_fixes=False, use_gh=not no_gh).get("github_index") or {}
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    if cmd == "catalog":
        print(json.dumps({"repos": list(build_catalog(use_gh=not no_gh).values())}, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "field-github-planet-sweep.py [json|sweep|refire|index|catalog] [--fast|--no-probe] [--no-gh] [--no-record] [--refire]",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())