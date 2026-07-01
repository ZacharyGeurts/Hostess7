#!/usr/bin/env pythong
"""Queen bookmark tree — folder flatten, search, default Hostess 7 / Command / OS."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

QUEEN = Path(__file__).resolve().parents[1]
TREES_PATH = QUEEN / "data" / "queen-bookmark-trees.json"


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def default_trees() -> list[dict[str, Any]]:
    doc = _load(TREES_PATH, {})
    trees = doc.get("trees") or []
    return [t for t in trees if isinstance(t, dict)]


def flatten_bar(trees: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Top-level bookmark bar — folders as flyout roots."""
    out: list[dict[str, Any]] = []
    for node in trees:
        if not isinstance(node, dict):
            continue
        if node.get("kind") == "folder":
            out.append({
                "id": node.get("id"),
                "kind": "folder",
                "title": node.get("title") or node.get("id"),
                "icon": node.get("icon"),
                "children": list(node.get("children") or []),
            })
        elif node.get("url"):
            out.append({**node, "kind": node.get("kind") or "bookmark"})
    return out


def _walk(nodes: list[dict[str, Any]], query: str, acc: list[dict[str, Any]]) -> None:
    q = query.lower()
    for node in nodes:
        if not isinstance(node, dict):
            continue
        title = str(node.get("title") or "")
        hint = str(node.get("hint") or "")
        if node.get("kind") == "folder":
            if q in title.lower():
                acc.append({**node, "kind": "folder"})
            _walk(list(node.get("children") or []), query, acc)
            continue
        if node.get("url") and (q in title.lower() or q in hint.lower() or q in str(node.get("url", "")).lower()):
            acc.append({**node, "kind": "bookmark"})


def search_tree(trees: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    q = (query or "").strip()
    if not q:
        return flatten_bar(trees)
    acc: list[dict[str, Any]] = []
    _walk(trees, q, acc)
    return acc


def _collect_bookmarks(trees: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for node in trees:
        if not isinstance(node, dict):
            continue
        if node.get("kind") == "folder":
            for child in node.get("children") or []:
                if isinstance(child, dict) and child.get("url"):
                    out.append(child)
        elif node.get("url"):
            out.append(node)
    return out


def _localhost_url(url: str) -> bool:
    u = (url or "").strip()
    if not u:
        return False
    if u.startswith("queen://"):
        return True
    if u.startswith("/"):
        return True
    try:
        from urllib.parse import urlparse
        host = (urlparse(u).hostname or "").lower()
    except Exception:
        return False
    return host in ("127.0.0.1", "localhost", "::1") or host.startswith("127.")


def validate_bookmarks(*, timeout: float = 8.0) -> dict[str, Any]:
    """HTTP-check every tree bookmark — loopback pages only."""
    import urllib.error
    import urllib.request

    trees = default_trees()
    rows = _collect_bookmarks(trees)
    world_port = int(__import__("os").environ.get("QUEEN_WORLD_PORT", "9481"))
    world_base = f"http://127.0.0.1:{world_port}"
    checked: list[dict[str, Any]] = []
    for bm in rows:
        raw = str(bm.get("url") or "")
        probe = raw.split("#")[0]
        if probe.startswith("/"):
            probe = world_base + probe
        ok = False
        status: int | None = None
        err = ""
        if not _localhost_url(raw):
            err = "non_localhost"
        else:
            try:
                req = urllib.request.Request(probe, method="GET")
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    status = int(resp.status)
                    ok = 200 <= status < 400
            except urllib.error.HTTPError as exc:
                status = int(exc.code)
                err = f"http_{status}"
            except Exception as exc:
                err = str(exc)
        checked.append({
            "id": bm.get("id"),
            "title": bm.get("title"),
            "url": raw,
            "probe": probe,
            "ok": ok,
            "status": status,
            "error": err or None,
        })
    fails = [c for c in checked if not c.get("ok")]
    return {
        "schema": "queen-bookmark-validate/v1",
        "ok": len(fails) == 0,
        "total": len(checked),
        "passed": len(checked) - len(fails),
        "failed": len(fails),
        "bookmarks": checked,
        "failures": fails,
    }


def posture() -> dict[str, Any]:
    trees = default_trees()
    return {
        "schema": "queen-bookmark-tree/v1",
        "trees": trees,
        "folder_count": sum(1 for t in trees if t.get("kind") == "folder"),
        "bookmark_count": sum(len(t.get("children") or []) for t in trees if t.get("kind") == "folder"),
    }


def main() -> int:
    import sys
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "json":
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("validate", "check"):
        out = validate_bookmarks()
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("ok") else 1
    print(json.dumps({"error": "usage: queen-bookmark-tree.py [json|validate]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())