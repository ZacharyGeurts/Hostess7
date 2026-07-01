#!/usr/bin/env pythong
"""NEXUS C2 — programmatic panel catalog for Queen OS + field monitor wall."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

QUEEN = Path(__file__).resolve().parents[1]
SG = QUEEN.parent.parent
PANELS = QUEEN / "data" / "queen-nexus-c2-panels.json"
G16_TOOLCHAIN = QUEEN / "data" / "g16-toolchain.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _world_base() -> str:
    port = os.environ.get("QUEEN_WORLD_PORT", "9481")
    return f"http://127.0.0.1:{port}"


def _panel_base() -> str:
    port = os.environ.get("NEXUS_THREAT_PANEL_PORT", "9477")
    return f"http://127.0.0.1:{port}"


def _g16_posture() -> dict[str, Any]:
    tc = _load(G16_TOOLCHAIN, {})
    profile = tc.get("profiles") or {}
    field_opt = profile.get("field_opt") or {}
    g16_bin = Path(tc.get("prefix") or grok16_root()) / "bin" / "g16"
    ready = g16_bin.is_file() and os.access(g16_bin, os.X_OK)
    build_script = QUEEN / "scripts" / "g16-build.sh"
    status_doc: dict[str, Any] = {}
    if build_script.is_file():
        try:
            proc = subprocess.run(
                ["bash", str(build_script), "status"],
                capture_output=True,
                text=True,
                timeout=20,
                cwd=str(QUEEN),
                env={**os.environ, "GROK16_ROOT": str(tc.get("root") or grok16_root())},
            )
            raw = proc.stdout or ""
            candidates: list[dict[str, Any]] = []
            depth = 0
            buf: list[str] = []
            for ch in raw:
                if ch == "{":
                    if depth == 0:
                        buf = ["{"]
                    else:
                        buf.append(ch)
                    depth += 1
                elif ch == "}":
                    if depth > 0:
                        buf.append(ch)
                        depth -= 1
                        if depth == 0:
                            try:
                                candidates.append(json.loads("".join(buf)))
                            except json.JSONDecodeError:
                                pass
                            buf = []
                elif depth > 0:
                    buf.append(ch)
            for doc in reversed(candidates):
                if doc.get("binary") or doc.get("product") == "Grok16 Field Build (g16 + Ninja)":
                    status_doc = doc
                    break
            if not status_doc and candidates:
                status_doc = candidates[-1]
        except (subprocess.TimeoutExpired, OSError):
            status_doc = {"ok": False, "error": "g16_status_failed"}
    return {
        "ready": ready,
        "g16_version": tc.get("g16_version") or tc.get("dumpversion"),
        "profile": os.environ.get("GROK16_FIELD_PROFILE") or status_doc.get("profile") or "field_opt",
        "field_opt_flags": (field_opt.get("cxx_flags") or [])[:6],
        "field_opt_defs": field_opt.get("definitions") or [],
        "link_lto": any("lto" in str(f) for f in (field_opt.get("link_flags") or [])),
        "build_status": status_doc,
    }


def _resolve_panel(screen: dict[str, Any]) -> dict[str, Any]:
    world = _world_base()
    panel = _panel_base()
    out = {**screen}
    kind = screen.get("kind") or "page"
    use_panel = bool(screen.get("panel"))
    thumb = screen.get("panel_thumbnail", True)
    chromeless = bool(screen.get("chromeless"))
    base = panel if use_panel else world

    if kind == "api":
        api = str(screen.get("api") or "").strip()
        if api:
            q = f"api={quote(api, safe='/')}"
            if use_panel:
                q += "&panel=1"
            if chromeless or thumb:
                q += "&chromeless=1"
            refresh = screen.get("refresh")
            if refresh:
                q += f"&refresh={int(refresh)}"
            title = screen.get("name") or screen.get("id") or "panel"
            q += f"&title={quote(str(title))}"
            out["url"] = f"{world}/world/queen-diagnostic-pane.html?{q}"
            out["fetch_url"] = f"{base}{api}" if api.startswith("/") else api
        else:
            out["url"] = f"{world}/world/queen-nexus-c2.html"
    elif screen.get("url"):
        u = str(screen["url"]).strip()
        if u.startswith("http"):
            out["url"] = u
        elif u.startswith("/"):
            out["url"] = (panel if use_panel and not u.startswith("/world/") and not u.startswith("/gui/") else world) + u
        else:
            out["url"] = f"{world}/{u}"
    else:
        out["url"] = f"{world}/world/queen-nexus-c2.html"

    out["drag_url"] = out.get("url") or out.get("fetch_url") or ""
    out["panel_thumbnail"] = thumb
    out["chromeless"] = chromeless or (kind == "api" and thumb)
    return out


def nexus_c2_posture(*, flyout: bool = False, legacy_schema: str | None = None) -> dict[str, Any]:
    doc = _load(PANELS, {"panels": [], "categories": []})
    raw = doc.get("panels") or []
    panels = [_resolve_panel(s) for s in raw]
    if flyout:
        pinned = [s for s in panels if s.get("pinned")]
        panels = pinned if pinned else panels[:12]
    g16 = _g16_posture()
    world = _world_base()
    schema = legacy_schema or "queen-nexus-c2/v1"
    return {
        "schema": schema,
        "ts": _now(),
        "ok": True,
        "flyout": flyout,
        "title": doc.get("title") or "NEXUS C2",
        "motto": doc.get("motto") or "",
        "theme": doc.get("theme") or "nexus_military_v8",
        "panel_thumbnail_default": doc.get("panel_thumbnail_default", True),
        "default_columns": doc.get("default_columns") or "auto",
        "flyout_columns": int(doc.get("flyout_columns") or 3),
        "categories": doc.get("categories") or [],
        "panels": panels,
        "screens": panels,
        "g16": g16,
        "c2_url": f"{world}/world/queen-nexus-c2.html",
        "dashboard_url": f"{world}/world/queen-nexus-c2.html",
        "flyout_mode": "taskbar_hover",
        "programmatic": True,
    }


def monitor_panels(*, pinned_only: bool = True) -> list[dict[str, Any]]:
    doc = _load(PANELS, {"panels": []})
    raw = doc.get("panels") or []
    rows = [_resolve_panel(s) for s in raw]
    if pinned_only:
        rows = [r for r in rows if r.get("pinned")]
    out: list[dict[str, Any]] = []
    for row in rows:
        url = row.get("url") or row.get("drag_url")
        if not url:
            continue
        out.append({
            "id": row.get("id"),
            "title": row.get("name") or row.get("id"),
            "url": url,
            "panel_thumbnail": row.get("panel_thumbnail", True),
            "chromeless": row.get("chromeless", False),
        })
    return out


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")
    if action in ("status", "json", "posture"):
        return {"ok": True, **nexus_c2_posture()}
    if action in ("flyout", "flyout_panels", "flyout_screens"):
        return {"ok": True, **nexus_c2_posture(flyout=True)}
    if action == "monitor":
        return {"ok": True, "panels": monitor_panels(pinned_only=body.get("pinned", True) is not False)}
    if action == "g16_check":
        g16 = _g16_posture()
        ok = g16.get("ready") and bool(g16.get("field_opt_defs"))
        return {"ok": ok, "g16": g16, "verdict": "G16_FIELD_OPT_READY" if ok else "G16_CHECK_HOLD"}
    return {"ok": False, "error": "unknown_action", "action": action}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "json":
        print(json.dumps(nexus_c2_posture(), ensure_ascii=False))
        return 0
    if cmd == "flyout":
        print(json.dumps(nexus_c2_posture(flyout=True), ensure_ascii=False))
        return 0
    if cmd == "monitor":
        print(json.dumps({"ok": True, "panels": monitor_panels()}, ensure_ascii=False))
        return 0
    if cmd == "dispatch":
        raw = sys.stdin.read()
        body = json.loads(raw) if raw.strip() else {}
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    print(json.dumps(dispatch({"action": cmd}), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())