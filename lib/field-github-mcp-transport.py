#!/usr/bin/env pythong
"""AmmoLang secure GitHub transport — MCP token + gh CLI, richer than raw TCP/urllib."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parent.parent))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
CONFIG_PATH = INSTALL / "data" / "field-ammolang-mcp-layer.json"
MCP_LAYER = INSTALL / "data" / "ammoos-mcp-layer.json"
PANEL = STATE / "field-ammolang-github-mcp.json"
SCHEMA = "github-mcp-transport/v1"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _expand(path_str: str) -> Path:
    return Path(os.path.expanduser(path_str)).resolve()


def load_config() -> dict[str, Any]:
    doc = _read_json(CONFIG_PATH, {})
    if not doc:
        doc = {
            "schema": SCHEMA,
            "default_transport": "mcp_secure",
            "owner": "ZacharyGeurts",
        }
    layer = _read_json(INSTALL / str(doc.get("mcp_layer") or "data/ammoos-mcp-layer.json"), {})
    doc["mcp_stdio"] = str(INSTALL / str(layer.get("stdio") or "scripts/github-mcp-stdio.sh"))
    doc["mcp_env"] = str(_expand(str(layer.get("env_file") or "~/.config/sg/github-mcp.env")))
    doc["mcp_binary"] = str(_expand(str(layer.get("binary") or "~/.local/bin/github-mcp-server")))
    return doc


def _load_mcp_env() -> dict[str, str]:
    cfg = load_config()
    env_path = Path(cfg.get("mcp_env") or "")
    out: dict[str, str] = {}
    if not env_path.is_file():
        return out
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def _gh_env() -> dict[str, str]:
    env = {**os.environ}
    mcp = _load_mcp_env()
    env.update(mcp)
    token = mcp.get("GITHUB_MCP_TOKEN") or env.get("GH_TOKEN") or ""
    if token:
        env["GH_TOKEN"] = token
        env["GITHUB_TOKEN"] = token
    return env


def mcp_ready() -> dict[str, Any]:
    cfg = load_config()
    mcp_env = Path(cfg.get("mcp_env") or "")
    binary = Path(cfg.get("mcp_binary") or "")
    gh = shutil.which("gh")
    token = _load_mcp_env().get("GITHUB_MCP_TOKEN") or os.environ.get("GH_TOKEN") or ""
    mode = "unconfigured"
    ready = False
    if token and mcp_env.is_file() and binary.is_file():
        mode = "mcp_secure"
        ready = bool(gh)
    elif gh:
        mode = "gh_cli"
        ready = True
    return {
        "ready": ready,
        "mode": mode,
        "owner": cfg.get("owner") or "ZacharyGeurts",
        "grok_mcp_server": cfg.get("grok_mcp_server") or "grok_com_github",
        "env_file": str(mcp_env),
        "binary_present": binary.is_file(),
        "gh_present": bool(gh),
        "token_present": bool(token),
    }


def resolve_transport(preferred: str | None = None) -> str:
    pref = (preferred or os.environ.get("AML_GITHUB_TRANSPORT") or load_config().get("default_transport") or "mcp_secure").strip().lower()
    status = mcp_ready()
    order = load_config().get("fallback_order") or ["mcp_secure", "gh_cli", "tcp"]
    if pref in order:
        order = [pref] + [x for x in order if x != pref]
    for mode in order:
        if mode == "mcp_secure" and status.get("ready") and status.get("mode") == "mcp_secure":
            return "mcp_secure"
        if mode == "gh_cli" and status.get("gh_present"):
            return "gh_cli"
        if mode == "tcp":
            return "tcp"
    return "tcp"


def _parse_rate_limit(stderr: str) -> int | None:
    m = re.search(r"x-ratelimit-remaining:\s*(\d+)", stderr, re.I)
    return int(m.group(1)) if m else None


def gh_api(path: str, *, method: str = "GET", timeout: int = 30) -> dict[str, Any]:
    """GitHub REST via gh — same scoped token as secure MCP."""
    t0 = time.perf_counter()
    cmd = ["gh", "api", path]
    if method.upper() != "GET":
        cmd.extend(["-X", method.upper()])
    cmd.extend(["--include"])
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=_gh_env())
    latency_ms = int((time.perf_counter() - t0) * 1000)
    body = proc.stdout or ""
    header, _, payload = body.partition("\r\n\r\n")
    if not payload and "\n\n" in body:
        header, _, payload = body.partition("\n\n")
    try:
        data = json.loads(payload.strip() or "{}")
    except json.JSONDecodeError:
        data = {"raw": payload[:4000]}
    auth = "mcp_token" if _load_mcp_env().get("GITHUB_MCP_TOKEN") else "gh_oauth"
    return {
        "ok": proc.returncode == 0,
        "transport": resolve_transport(),
        "auth_mode": auth,
        "latency_ms": latency_ms,
        "rate_limit_remaining": _parse_rate_limit((header or "") + (proc.stderr or "")),
        "status_code": proc.returncode,
        "path": path,
        "data": data,
        "error": (proc.stderr or "").strip()[:500] if proc.returncode != 0 else None,
    }


def tcp_fetch_json(url: str, timeout: int = 12) -> dict[str, Any]:
    t0 = time.perf_counter()
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "AmmoLang-GitHub-TCP"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        return {
            "ok": True,
            "transport": "tcp",
            "auth_mode": "anonymous",
            "latency_ms": int((time.perf_counter() - t0) * 1000),
            "url": url,
            "data": data,
            "warning": "TCP/IP fallback — use secure MCP for scoped auth and richer metadata",
        }
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError, OSError) as exc:
        return {
            "ok": False,
            "transport": "tcp",
            "auth_mode": "anonymous",
            "latency_ms": int((time.perf_counter() - t0) * 1000),
            "url": url,
            "error": str(exc)[:300],
        }


def tcp_fetch_text(url: str, timeout: int = 12) -> dict[str, Any]:
    t0 = time.perf_counter()
    req = urllib.request.Request(url, headers={"User-Agent": "AmmoLang-GitHub-TCP"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8", errors="replace")
        return {
            "ok": True,
            "transport": "tcp",
            "auth_mode": "anonymous",
            "latency_ms": int((time.perf_counter() - t0) * 1000),
            "url": url,
            "text": text,
            "warning": "TCP/IP fallback — use secure MCP for scoped auth",
        }
    except (urllib.error.URLError, OSError) as exc:
        return {
            "ok": False,
            "transport": "tcp",
            "latency_ms": int((time.perf_counter() - t0) * 1000),
            "url": url,
            "error": str(exc)[:300],
        }


def _norm_repo(repo: str, owner: str | None = None) -> str:
    repo = repo.strip()
    if "/" in repo:
        return repo
    own = owner or load_config().get("owner") or "ZacharyGeurts"
    return f"{own}/{repo}"


def repo_site_info(repo: str) -> dict[str, Any]:
    full = _norm_repo(repo)
    cfg = load_config()
    sites = cfg.get("github_sites") or {}
    name = full.split("/", 1)[-1]
    site = sites.get(name) or sites.get(full) or {}
    pages = site.get("pages") or f"https://zacharygeurts.github.io/{name}/"
    wiki = site.get("wiki")
    html = f"https://github.com/{full}"
    api = gh_api(f"repos/{full}") if resolve_transport() != "tcp" else tcp_fetch_json(f"https://api.github.com/repos/{full}")
    repo_doc = api.get("data") if api.get("ok") else {}
    has_pages = bool(repo_doc.get("has_pages")) if isinstance(repo_doc, dict) else None
    summary = [
        f"repo {full}",
        f"github side {html}",
        f"pages site {pages}" + (" (live)" if has_pages else " (catalog)"),
    ]
    if wiki:
        summary.append(f"wiki {wiki}")
    return {
        "schema": SCHEMA,
        "repo": full,
        "html_url": html,
        "pages_url": pages,
        "wiki_url": wiki,
        "has_pages": has_pages,
        "description": (repo_doc or {}).get("description") if isinstance(repo_doc, dict) else None,
        "stargazers_count": (repo_doc or {}).get("stargazers_count") if isinstance(repo_doc, dict) else None,
        "default_branch": (repo_doc or {}).get("default_branch") if isinstance(repo_doc, dict) else "main",
        "transport": api.get("transport"),
        "auth_mode": api.get("auth_mode"),
        "latency_ms": api.get("latency_ms"),
        "summary_lines": summary,
        "ok": True,
    }


def repo_file_text(repo: str, path: str, ref: str = "main") -> dict[str, Any]:
    full = _norm_repo(repo)
    transport = resolve_transport()
    if transport != "tcp":
        api = gh_api(f"repos/{full}/contents/{path}?ref={ref}")
        if api.get("ok") and isinstance(api.get("data"), dict):
            import base64

            enc = api["data"].get("content") or ""
            try:
                text = base64.b64decode(enc).decode("utf-8", errors="replace")
            except Exception:
                text = ""
            return {
                "ok": bool(text),
                "repo": full,
                "path": path,
                "ref": ref,
                "sha": api["data"].get("sha"),
                "size": api["data"].get("size"),
                "text": text,
                "transport": api.get("transport"),
                "auth_mode": api.get("auth_mode"),
                "latency_ms": api.get("latency_ms"),
                "summary_lines": [f"fetch {full}:{path}@{ref} via {api.get('transport')} ({len(text)} bytes)"],
            }
        return {**api, "ok": False, "repo": full, "path": path}
    url = f"https://raw.githubusercontent.com/{full}/{ref}/{path}"
    raw = tcp_fetch_text(url)
    return {
        "ok": raw.get("ok", False),
        "repo": full,
        "path": path,
        "ref": ref,
        "text": raw.get("text") or "",
        "transport": "tcp",
        "warning": raw.get("warning"),
        "summary_lines": [f"fetch {full}:{path}@{ref} via tcp ({len(raw.get('text') or '')} bytes)"],
        "error": raw.get("error"),
    }


def repo_latest_release(repo: str) -> dict[str, Any]:
    full = _norm_repo(repo)
    transport = resolve_transport()
    if transport != "tcp":
        api = gh_api(f"repos/{full}/releases/latest")
        rel = api.get("data") if api.get("ok") else {}
        tag = str((rel or {}).get("tag_name") or "")
        ver = tag.lstrip("v")
        summary = [
            f"release {tag or 'none'} on {full}",
            f"published {(rel or {}).get('published_at') or '—'}",
            f"via {api.get('transport')} auth={api.get('auth_mode')} {api.get('latency_ms')}ms",
        ]
        return {
            "ok": api.get("ok", False),
            "repo": full,
            "latest": ver or None,
            "tag_name": tag or None,
            "release_url": (rel or {}).get("html_url") or f"https://github.com/{full}/releases/latest",
            "release_notes": ((rel or {}).get("body") or "").strip()[:2000],
            "published_at": (rel or {}).get("published_at"),
            "transport": api.get("transport"),
            "auth_mode": api.get("auth_mode"),
            "latency_ms": api.get("latency_ms"),
            "rate_limit_remaining": api.get("rate_limit_remaining"),
            "summary_lines": summary,
            "source": "releases/latest",
        }
    api = tcp_fetch_json(f"https://api.github.com/repos/{full}/releases/latest")
    rel = api.get("data") if api.get("ok") else {}
    tag = str((rel or {}).get("tag_name") or "")
    return {
        "ok": api.get("ok", False),
        "repo": full,
        "latest": tag.lstrip("v") or None,
        "tag_name": tag or None,
        "release_url": (rel or {}).get("html_url"),
        "transport": "tcp",
        "warning": api.get("warning"),
        "summary_lines": [f"release {tag or 'none'} via tcp"],
    }


def check_repo(repo: str) -> dict[str, Any]:
    full = _norm_repo(repo)
    rel = repo_latest_release(full)
    site = repo_site_info(full)
    lines = list(rel.get("summary_lines") or []) + list(site.get("summary_lines") or [])
    return {
        "schema": SCHEMA,
        "ok": bool(rel.get("ok") or site.get("ok")),
        "repo": full,
        "latest": rel.get("latest"),
        "release_url": rel.get("release_url"),
        "site": site,
        "release": rel,
        "transport": rel.get("transport") or site.get("transport"),
        "summary_lines": lines,
    }


def _parse_spec(spec: str) -> dict[str, str]:
    out: dict[str, str] = {}
    parts = spec.split()
    if parts:
        out["verb"] = parts[0].lower()
    for part in parts[1:]:
        if ":" in part:
            k, v = part.split(":", 1)
            out[k.lower()] = v
    return out


def dispatch_action(spec: str) -> dict[str, Any]:
    parsed = _parse_spec(spec)
    verb = parsed.get("verb") or "check"
    repo = parsed.get("repo") or "ZacharyGeurts/AmmoOS"
    if verb == "fetch":
        return repo_file_text(repo, parsed.get("path") or "README.md", parsed.get("ref") or "main")
    if verb == "site":
        return repo_site_info(repo)
    if verb == "releases":
        return repo_latest_release(repo)
    if verb == "repos":
        q = parsed.get("q") or f"user:{load_config().get('owner') or 'ZacharyGeurts'}"
        transport = resolve_transport()
        if transport != "tcp":
            api = gh_api(f"search/repositories?q={urllib.parse.quote(q)}&per_page=8")
            items = (api.get("data") or {}).get("items") if api.get("ok") else []
            return {
                "ok": api.get("ok", False),
                "query": q,
                "count": len(items or []),
                "repos": [
                    {"full_name": r.get("full_name"), "html_url": r.get("html_url"), "description": r.get("description")}
                    for r in (items or [])[:8]
                    if isinstance(r, dict)
                ],
                "transport": api.get("transport"),
                "summary_lines": [f"search {q} → {len(items or [])} repos via {api.get('transport')}"],
            }
        return {"ok": False, "error": "repos search requires mcp_secure or gh_cli"}
    return check_repo(repo)


def publish_panel(*, refresh: bool = False) -> dict[str, Any]:
    if PANEL.is_file() and not refresh:
        return {"ok": True, "panel": _read_json(PANEL)}
    cfg = load_config()
    status = mcp_ready()
    sample = check_repo("ZacharyGeurts/AmmoOS")
    panel = {
        "schema": "field-ammolang-github-mcp/v1",
        "updated": _now(),
        "default_transport": cfg.get("default_transport"),
        "active_transport": resolve_transport(),
        "mcp_status": status,
        "grok_mcp_server": cfg.get("grok_mcp_server"),
        "github_sites": cfg.get("github_sites"),
        "sample_check": {k: sample.get(k) for k in ("repo", "latest", "transport", "summary_lines")},
        "motto": cfg.get("motto"),
    }
    _write_json(PANEL, panel)
    return {"ok": True, "panel": panel}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip().lower()
    if cmd in ("status", "panel", "json"):
        print(json.dumps(publish_panel(refresh="--refresh" in sys.argv).get("panel"), ensure_ascii=False, indent=2))
        return 0
    if cmd == "ready":
        print(json.dumps(mcp_ready(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "check":
        repo = sys.argv[2] if len(sys.argv) > 2 else "ZacharyGeurts/AmmoOS"
        doc = check_repo(repo)
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 0 if doc.get("ok") else 1
    if cmd == "site":
        repo = sys.argv[2] if len(sys.argv) > 2 else "AmmoOS"
        doc = repo_site_info(repo)
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 0 if doc.get("ok") else 1
    if cmd == "dispatch":
        spec = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "check repo:ZacharyGeurts/AmmoOS"
        doc = dispatch_action(spec)
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 0 if doc.get("ok") else 1
    print(json.dumps({
        "error": "usage",
        "hint": "field-github-mcp-transport.py [status|ready|check REPO|site REPO|dispatch SPEC]",
    }, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())