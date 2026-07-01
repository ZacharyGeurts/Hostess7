#!/usr/bin/env python3
"""Generate thin GitHub Pages stubs that link to canonical AmmoOS manual pages."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

INSTALL = Path(__file__).resolve().parents[1]
HUB_DOC = INSTALL / "data" / "ammoos-pages-hub.json"
sys.path.insert(0, str(INSTALL / "lib"))
import page_github_chrome as gh_chrome  # noqa: E402


def load_hub() -> dict[str, Any]:
    return json.loads(HUB_DOC.read_text(encoding="utf-8"))


def canonical_url(hub: dict[str, Any], repo_entry: dict[str, Any]) -> str:
    base = str(hub.get("canonical_base") or "https://zacharygeurts.github.io/AmmoOS/").rstrip("/") + "/"
    page = str(repo_entry.get("ammoos_page") or "index.html")
    return base + page


def hub_index_html(hub: dict[str, Any], name: str, entry: dict[str, Any], *, version: str = "") -> str:
    github = str(entry.get("github") or f"https://github.com/ZacharyGeurts/{name}")
    title = str(entry.get("title") or name)
    blurb = str(entry.get("blurb") or "Documentation lives in the AmmoOS manual.")
    manual = canonical_url(hub, entry)
    stack = str(hub.get("canonical_base") or "").rstrip("/") + "/" + str(hub.get("stack_hub_page") or "stack-hub.html")
    ver = f" · {version}" if version else ""
    label = github.replace("https://github.com/", "")
    ammoos_repo = str(hub.get("canonical_repo") or "https://github.com/ZacharyGeurts/AmmoOS")
    release_tag = str(hub.get("release_tag") or "v2.0.0-beta4")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title} — AmmoOS manual</title>
  <meta http-equiv="refresh" content="4;url={manual}" />
  <link rel="canonical" href="{manual}" />
  <meta name="description" content="{title} — canonical docs in AmmoOS manual" />
  <style>{gh_chrome.chrome_css()}
    body {{ font-family: system-ui, sans-serif; max-width: 46rem; margin: 0 auto; padding: 1rem 1.25rem 2rem; background: #0a0c12; color: #e8edf7; }}
    .lead {{ border-left: 3px solid #22c55e; padding-left: 1rem; margin: 1.25rem 0; }}
    .cta {{ display: inline-block; margin: 0.5rem 0.75rem 0.5rem 0; padding: 0.55rem 1rem; border-radius: 8px; background: #14532d; color: #bbf7d0; text-decoration: none; font-weight: 600; }}
    .cta:hover {{ background: #166534; }}
    .meta {{ color: #94a3b8; font-size: 0.92rem; }}
  </style>
</head>
<body>
{gh_chrome.hub_chrome_top(github, sibling_label=label, ammoos_repo=ammoos_repo, release_tag=release_tag)}
  <h1>{title}</h1>
  <p class="lead">{blurb}</p>
  <p class="meta">This repo&apos;s GitHub Pages is a <strong>redirect hub</strong>. <strong>Source code</strong> for the full stack lives in <a href="{ammoos_repo}">AmmoOS</a>. Documentation is maintained once in the <a href="{hub.get('canonical_base')}">AmmoOS manual</a>{ver}.</p>
  <p>
    <a class="cta" href="{ammoos_repo}">Clone AmmoOS (canonical code)</a>
    <a class="cta" href="{manual}">Open manual → {entry.get('ammoos_page', 'index.html')}</a>
    <a class="cta" href="{stack}">Stack hub</a>
  </p>
  <p class="meta">Auto-redirecting in 4 seconds…</p>
{gh_chrome.hub_chrome_bottom(github, sibling_label=label, ammoos_repo=ammoos_repo, version=version)}
</body>
</html>
"""


def write_hub_dir(out_dir: Path, name: str, entry: dict[str, Any], hub: dict[str, Any], *, version: str = "") -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    html = hub_index_html(hub, name, entry, version=version)
    (out_dir / "index.html").write_text(html, encoding="utf-8")
    return out_dir / "index.html"


def write_all_hubs(stage_root: Path, *, version: str = "", only: list[str] | None = None) -> list[str]:
    hub = load_hub()
    written: list[str] = []
    targets = only or list((hub.get("repos") or {}).keys())
    for name in targets:
        entry = (hub.get("repos") or {}).get(name)
        if not entry or name == "AmmoOS":
            continue
        write_hub_dir(stage_root / name, name, entry, hub, version=version)
        written.append(name)
    return written


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Generate AmmoOS-linked hub pages")
    ap.add_argument("--out", default=str(INSTALL / ".pages-hub-staging"))
    ap.add_argument("--repo", action="append", dest="repos")
    ap.add_argument("--version", default="")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    hub = load_hub()
    if args.list:
        for name, entry in sorted((hub.get("repos") or {}).items()):
            print(f"{name}\t{canonical_url(hub, entry)}")
        return 0
    written = write_all_hubs(Path(args.out), version=args.version, only=args.repos)
    print(json.dumps({"ok": True, "written": written, "out": args.out}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())