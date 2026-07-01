#!/usr/bin/env pythong
"""Queen Browser integration tests — API + assets + proxy (standard browser ops)."""
from __future__ import annotations

import json
import os
import subprocess
import sys

os.environ.setdefault("QUEEN_INTERNAL_ONLY", "1")
import time
import urllib.error
import urllib.request
from pathlib import Path

QUEEN = Path(__file__).resolve().parents[1]
HOST = os.environ.get("QUEEN_WORLD_HOST", "127.0.0.1")
PORT = int(os.environ.get("QUEEN_WORLD_PORT", "9481"))
BASE = f"http://{HOST}:{PORT}"


def _get(path: str, timeout: int = 30) -> tuple[int, bytes]:
    req = urllib.request.Request(f"{BASE}{path}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def _post(path: str, body: dict, timeout: int = 60) -> tuple[int, dict]:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8") or "{}")


def wait_up(secs: float = 15.0) -> bool:
    deadline = time.time() + secs
    while time.time() < deadline:
        try:
            code, _ = _get("/api/queen-browser", timeout=2)
            if code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.25)
    return False


def assert_true(cond: bool, msg: str, results: list) -> None:
    results.append(("PASS" if cond else "FAIL", msg))
    if not cond:
        raise AssertionError(msg)


def run_tests() -> list[tuple[str, str]]:
    results: list[tuple[str, str]] = []

    # --- Static shell (standard browser chrome) ---
    code, html = _get("/world/")
    assert_true(code == 200, "world page HTTP 200", results)
    text = html.decode("utf-8", errors="replace")
    for needle in (
        "qb-chrome",
        "qb-tabs",
        "qb-url",
        "qb-frame",
        "qb-back",
        "qb-forward",
        "qb-reload",
        "qb-start",
        "queen-browser-shell.js",
        "qb-new-tab",
        "qb-bookmarks",
        "qb-gate-pill",
        "qb-security-strip",
        "data-queen-surface=\"browser\"",
        "data-queen-theme=\"black_emerald_rose_2026\"",
        "queen-theme-2026.js",
        "queen-styles.js",
        "queen-styles.css",
        "qb-styles",
        "queen-media-egress.js",
        "data-media-egress",
        "Queen",
        "queen-branding.css",
        "amouranth-gentle.png",
    ):
        assert_true(needle in text, f"shell contains {needle}", results)
    bjs, bjst = _get("/world/queen-branding.js")
    assert_true(bjs == 200 and b"qb-queen-crown-egg" in bjst and b"queen-browser-guide" in bjst, "Queen crown + guide wired", results)
    assert_true("qw-dock" not in text, "default /world/ is browser-only (no Queen OS dock)", results)

    for asset in (
        "/world/queen-branding.css",
        "/world/queen-branding.js",
        "/world/assets/branding/queen-favicon-48.png",
        "/world/assets/branding/queen-crown-surprise.svg",
        "/world/queen-browser-guide.html",
        "/world/queen-browser-guide.css",
        "/world/assets/branding/amouranth-plate.png",
        "/world/queen-os.js",
        "/world/queen-world.css",
        "/world/queen-gnu-terminal.js",
        "/world/queen-gnu-terminal.css",
        "/world/queen-gnu-terminal-embed.html",
        "/world/queen-browser-shell.js",
        "/world/queen-theme-2026.js",
        "/world/queen-styles.js",
        "/world/queen-styles.css",
        "/gui/queen-theme-2026.json",
        "/gui/queen-styles-themes.json",
        "/world/queen-start.html",
        "/world/queen-desktop.html",
        "/world/queen-desktop.js",
        "/world/queen-desktop.css",
        "/world/queen-sdf-icons.js",
        "/world/queen-front-hook.js",
        "/world/queen-files.html",
        "/world/queen-files.js",
        "/world/queen-files.css",
        "/world/queen-nexus-c2.html",
        "/world/queen-nexus-c2.js",
        "/world/queen-nexus-c2.css",
        "/world/queen-thermal-manager.html",
        "/world/queen-thermal-manager.js",
        "/world/queen-thermal-manager.css",
        "/world/queen-final-ear-manager.html",
        "/world/queen-final-ear-manager.js",
        "/world/queen-final-ear-manager.css",
        "/world/queen-final-mouth-manager.html",
        "/world/queen-final-mouth-manager.js",
        "/world/queen-final-mouth-manager.css",
        "/world/queen-hostess7-hub.html",
        "/world/queen-hostess7-hub.js",
        "/world/queen-hostess7-hub.css",
        "/world/queen-dashboard.html",
        "/world/queen-dashboard.js",
        "/world/queen-dashboard.css",
        "/world/queen-dashboard-flyout.js",
        "/world/queen-dashboard-flyout.css",
        "/world/queen-diagnostic-pane.html",
        "/world/queen-diagnostic-pane.js",
        "/world/queen-diagnostic-pane.css",
        "/world/field-performance-flyout.js",
        "/world/field-performance-flyout.css",
    ):
        ac, _ = _get(asset)
        assert_true(ac == 200, f"asset {asset} loads", results)

    code, c2_html = _get("/world/queen-nexus-c2.html")
    assert_true(code == 200, "nexus c2 page HTTP 200", results)
    c2_text = c2_html.decode("utf-8", errors="replace")
    for needle in (
        "qnc2-window",
        "qnc2-grid",
        "qnc2-cols",
        "qnc2-fs-layer",
        "queen-nexus-c2.js",
        'data-queen-surface="nexus-c2"',
        "nexus-military-v8",
    ):
        assert_true(needle in c2_text, f"nexus c2 contains {needle}", results)
    code, c2_js = _get("/world/queen-nexus-c2.js")
    assert_true(code == 200 and b"QueenNexusC2" in c2_js and b"/api/nexus-c2" in c2_js, "nexus c2 JS API", results)

    code, dash_html = _get("/world/queen-dashboard.html")
    assert_true(code == 200, "legacy dashboard redirect HTTP 200", results)
    dash_text = dash_html.decode("utf-8", errors="replace")
    assert_true("queen-nexus-c2.html" in dash_text, "dashboard redirects to nexus c2", results)

    code, desk_raw = _get("/api/queen-desktop")
    desk = json.loads(desk_raw.decode("utf-8"))
    assert_true(code == 200 and desk.get("schema") == "queen-desktop/v1", "queen-desktop API", results)
    start_src = desk.get("start_programs") if desk.get("desktop_icons_in_start") else desk.get("classic_programs")
    desk_ids = {p.get("id") for p in start_src or []}
    assert_true("nexus-c2" in desk_ids or "dashboard" in desk_ids, "nexus c2 in start programs", results)
    if desk.get("desktop_icons_in_start"):
        assert_true(not desk.get("classic_programs"), "desktop surface clear when icons in start", results)

    code, c2_api_raw = _get("/api/nexus-c2")
    c2_api = json.loads(c2_api_raw.decode("utf-8"))
    assert_true(code == 200 and c2_api.get("schema") == "queen-nexus-c2/v1", "nexus-c2 API", results)
    assert_true(c2_api.get("programmatic") is True, "nexus-c2 programmatic", results)
    panel_ids = {s.get("id") for s in (c2_api.get("panels") or c2_api.get("screens") or [])}
    for sid in ("field-sanity", "physics-witness", "g16-forge", "combinatorics", "c2-taskbar"):
        assert_true(sid in panel_ids, f"nexus c2 panel {sid}", results)
    g16 = c2_api.get("g16") or {}
    assert_true("field_opt_defs" in g16 and isinstance(g16.get("field_opt_defs"), list), "nexus c2 g16 field_opt posture", results)

    code, dash_api_raw = _get("/api/queen-dashboard")
    dash_api = json.loads(dash_api_raw.decode("utf-8"))
    assert_true(code == 200 and dash_api.get("schema") == "queen-dashboard/v1", "legacy dashboard API alias", results)

    code, fly_raw = _get("/api/nexus-c2?flyout=1")
    fly = json.loads(fly_raw.decode("utf-8"))
    assert_true(code == 200 and fly.get("flyout") is True and len(fly.get("panels") or fly.get("screens") or []) >= 6, "nexus c2 flyout panels", results)

    # --- Status ---
    code, doc = _post("/api/queen-browser", {"action": "status"})
    assert_true(code == 200 and doc.get("queen_verdict") == "QUEEN_READY", "QUEEN_READY verdict", results)
    sec = doc.get("security") or {}
    assert_true(sec.get("doctrine") == "presume_hostile_defend_offense", "browser hostile-presumption doctrine", results)
    egress = sec.get("media_egress") or {}
    assert_true(egress.get("egress_lock") is True, "media egress locked by default", results)
    assert_true(egress.get("blocked_by_default", {}).get("screen_out") is True, "screen out blocked", results)
    assert_true(egress.get("blocked_by_default", {}).get("keystrokes_out") is True, "keystrokes out blocked", results)
    assert_true(egress.get("blocked_by_default", {}).get("keyhooks_out") is True, "keyhooks out blocked", results)
    _, grant = _post("/api/queen-browser", {"action": "capture_request", "purpose": "obs_local"}, timeout=30)
    assert_true(grant.get("ok") and grant.get("permit") is True, "operator local capture grant", results)
    _, revoked = _post("/api/queen-browser", {"action": "capture_revoke"}, timeout=30)
    assert_true(revoked.get("ok") is True, "capture revoke", results)
    assert_true((sec.get("iff") or {}).get("presume_hostile") is True, "browser presume hostile IFF", results)
    assert_true((sec.get("iff") or {}).get("never_presume_correct_contact") is True, "never presume correct contact", results)
    assert_true(doc.get("capabilities", {}).get("start_tab") is True, "start tab capability", results)
    assert_true(doc.get("capabilities", {}).get("classic_desktop") is True, "classic desktop capability", results)
    assert_true(doc.get("capabilities", {}).get("split_pill_start") is True, "split pill start capability", results)
    assert_true("queen-desktop.html" in (doc.get("desktop_url") or ""), "desktop URL in status", results)
    assert_true(doc.get("capabilities", {}).get("full_web_surface") is True, "full web surface capability", results)
    assert_true((doc.get("web_compat") or {}).get("schema") == "queen-web-compat/v1", "web compat catalog", results)
    assert_true(doc.get("capabilities", {}).get("nexus_jump") is True, "nexus jump capability", results)
    assert_true((doc.get("nexus_jump") or {}).get("schema") == "queen-nexus-jump/v1", "nexus jump status in browser", results)
    assert_true(doc.get("capabilities", {}).get("tabs") is True, "tabs capability", results)
    assert_true(doc.get("capabilities", {}).get("file_browser") is True, "file browser capability", results)
    assert_true(doc.get("capabilities", {}).get("zero_cost_4_slot") is True, "zero cost 4-slot capability", results)
    zc = doc.get("zero_cost_security") or {}
    assert_true(zc.get("runtime_tax") == 0, "zero runtime tax", results)
    assert_true(len(zc.get("slots") or []) >= 4, "four security slots", results)
    tabs = doc.get("tabs") or []
    files_tab = next((t for t in tabs if t.get("role") == "files"), None)
    assert_true(files_tab is not None and files_tab.get("pinned") is True, "pinned Files tab (second)", results)
    assert_true("queen-files.html" in (files_tab.get("url") or ""), "Files tab URL", results)
    if len(tabs) >= 2:
        start_idx = next((i for i, t in enumerate(tabs) if t.get("role") == "start"), 0)
        files_idx = next((i for i, t in enumerate(tabs) if t.get("role") == "files"), -1)
        assert_true(files_idx == start_idx + 1, "Files tab immediately after Start", results)
    assert_true(len(doc.get("bookmarks") or []) >= 3, "bookmarks present", results)
    trees = doc.get("bookmark_trees") or []
    leaf_ids: set[str] = set()
    for folder in trees:
        for child in folder.get("children") or []:
            if child.get("id"):
                leaf_ids.add(child.get("id"))
    assert_true("os-thermal" in leaf_ids, "Thermal Manager bookmark", results)
    assert_true("h7-ear-neural" in leaf_ids, "Final Ear manager bookmark", results)
    assert_true("h7-mouth-neural" in leaf_ids, "Final Mouth manager bookmark", results)
    cmd_ids = {c.get("id") for c in next((t.get("children") or [] for t in trees if t.get("id") == "command"), [])}
    assert_true({"cmd-field", "cmd-deck", "cmd-threat"} <= cmd_ids, "Control folder localhost bookmarks", results)
    tree_ids = {t.get("id") for t in trees if isinstance(t, dict)}
    for fid in ("hostess-7", "command", "os"):
        assert_true(fid in tree_ids, f"bookmark folder {fid}", results)
    import subprocess
    bm_val = subprocess.run(
        [sys.executable, str(QUEEN / "lib" / "queen-bookmark-tree.py"), "validate"],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(QUEEN),
    )
    assert_true(bm_val.returncode == 0, "all bookmark tree URLs validate (localhost)", results)
    home = doc.get("home") or ""
    assert_true(home.startswith("http"), "home URL set", results)
    tab1 = (doc.get("tabs") or [{}])[0].get("id")
    assert_true(bool(tab1), "initial tab id", results)

    # --- Internal only — external blocked at NEXUS jump (hostile presumption) ---
    code, ext = _post("/api/queen-browser", {"action": "navigate", "url": "https://example.com", "tab_id": tab1})
    assert_true(
        code == 200
        and not ext.get("ok")
        and ext.get("error") in ("nexus_jump_blocked", "gate_blocked"),
        "block external URL",
        results,
    )
    jump = ext.get("jump") or {}
    assert_true(
        jump.get("verdict") == "BLOCK_HOSTILE" or not (ext.get("gate") or {}).get("permit"),
        "external contact interdicted as hostile",
        results,
    )

    # --- Navigate loopback ---
    port = os.environ.get("QUEEN_WORLD_PORT", "9481")
    code, nav = _post("/api/queen-browser", {"action": "navigate", "url": f"http://127.0.0.1:{port}/gui/queen-build-deck.html", "tab_id": tab1})
    assert_true(code == 200 and nav.get("ok"), "navigate internal forge", results)
    assert_true("queen-build-deck" in (nav.get("tab", {}).get("url") or ""), "tab URL internal", results)

    # --- History back / forward ---
    code, back = _post("/api/queen-browser", {"action": "back", "tab_id": tab1})
    assert_true(code == 200 and back.get("ok"), "history back", results)
    assert_true(
        "queen-desktop.html" in (back.get("tab", {}).get("url") or "")
        or "/field" in (back.get("tab", {}).get("url") or "")
        or "/world/" in (back.get("tab", {}).get("url") or ""),
        "back returns home tab URL",
        results,
    )

    code, fwd = _post("/api/queen-browser", {"action": "forward", "tab_id": tab1})
    assert_true(code == 200 and fwd.get("ok"), "history forward", results)
    assert_true("queen-build-deck" in (fwd.get("tab", {}).get("url") or ""), "forward restores forge", results)

    # --- New tab ---
    code, nt = _post("/api/queen-browser", {"action": "new_tab", "url": "https://httpbin.org/html"})
    assert_true(code == 200 and nt.get("ok"), "new tab", results)
    tabs = (nt.get("status") or {}).get("tabs") or []
    assert_true(len(tabs) >= 3, "three+ tabs after new_tab (Start+Files+pinned)", results)
    tab2 = next((t["id"] for t in tabs if t.get("url") == "https://httpbin.org/html"), None)
    assert_true(bool(tab2), "new tab id found", results)

    # --- Activate tab ---
    code, act = _post("/api/queen-browser", {"action": "activate_tab", "tab_id": tab1})
    assert_true(code == 200 and act.get("ok"), "activate tab", results)
    active = next((t for t in (act.get("status") or {}).get("tabs") or [] if t.get("active")), {})
    assert_true(active.get("id") == tab1, "active tab switched", results)

    # --- Home ---
    code, home_r = _post("/api/queen-browser", {"action": "home", "tab_id": tab1})
    assert_true(code == 200 and home_r.get("ok"), "home navigation", results)

    # --- Reload ---
    code, rel = _post("/api/queen-browser", {"action": "reload", "tab_id": tab1})
    assert_true(code == 200 and rel.get("ok"), "reload", results)

    # --- Gate check — external denied, internal permitted ---
    code, gc_ext = _post("/api/queen-browser", {"action": "gate_check", "url": "https://github.com"})
    assert_true(code == 200 and gc_ext.get("ok") and not gc_ext.get("gate", {}).get("permit"), "gate_check block external", results)
    code, gc = _post("/api/queen-browser", {"action": "gate_check", "url": f"http://127.0.0.1:{port}/world/"})
    assert_true(code == 200 and gc.get("ok") and gc.get("gate", {}).get("permit"), "gate_check permit loopback", results)

    # --- Close tab (keep one) ---
    code, close = _post("/api/queen-browser", {"action": "close_tab", "tab_id": tab2})
    assert_true(code == 200 and close.get("ok"), "close tab", results)
    assert_true(len((close.get("status") or {}).get("tabs") or []) == 2, "pinned Start+Files remain after close", results)

    # --- Cannot close last tab ---
    code, last = _post("/api/queen-browser", {"action": "close_tab", "tab_id": tab1})
    assert_true(
        code == 200 and not last.get("ok") and last.get("error") in ("last_tab", "pinned_tab"),
        "block close last / pinned start tab",
        results,
    )

    # --- FieldNet API ---
    fc, fdoc_raw = _get("/api/field-net")
    fdoc = json.loads(fdoc_raw.decode("utf-8"))
    assert_true(fc == 200 and fdoc.get("internal_only") is True, "field-net internal_only", results)
    route_ids = {r.get("id") for r in (fdoc.get("routes") or [])}
    assert_true("capsule" in route_ids and "horizon7" in route_ids, "field-net capsule + horizon7 routes", results)
    fc2, fresolve = _post("/api/field-net", {"action": "resolve", "url": "queen://sovereign"})
    assert_true(fc2 == 200 and fresolve.get("ok") and "/api/sovereign" in (fresolve.get("resolved") or ""), "resolve queen://sovereign", results)
    fc3, fresolve2 = _post("/api/field-net", {"action": "resolve", "url": "queen://horizon7"})
    assert_true(fc3 == 200 and fresolve2.get("ok") and "/api/horizon7" in (fresolve2.get("resolved") or ""), "resolve queen://horizon7", results)
    assert_true((fdoc.get("external_wire") or {}).get("lane") == "External", "field-net external_wire slice", results)
    fc4, fresolve3 = _post("/api/field-net", {"action": "resolve", "url": "queen://external-wire"})
    assert_true(fc4 == 200 and fresolve3.get("ok") and "/api/external-wire" in (fresolve3.get("resolved") or ""), "resolve queen://external-wire", results)

    # --- External Field Wire — quarantine lane, no main import ---
    _post("/api/external-wire", {"action": "purge", "confirm": True})
    _post("/api/external-wire", {"action": "reset_limits", "confirm": True})
    ew, ewdoc_raw = _get("/api/external-wire")
    ewdoc = json.loads(ewdoc_raw.decode("utf-8"))
    assert_true(ew == 200 and ewdoc.get("lane") == "External", "external-wire status lane", results)
    assert_true(ewdoc.get("import_to_main") is False and ewdoc.get("ddos_immune") is True, "external-wire quarantine doctrine", results)
    assert_true(ewdoc.get("never_tampered_or_broken") is not False, "external-wire integrity", results)
    assert_true("hostess7" in (ewdoc.get("parties") or {}), "external-wire hostess7 party", results)
    ew2, recv = _post("/api/external-wire", {"action": "receive", "party": "ai", "query": "grounded probe", "from": "test-ai"})
    assert_true(ew2 == 200 and recv.get("ok") and recv.get("lane") == "External", "external-wire receive grounded", results)
    assert_true(recv.get("imported") is False and recv.get("internal_touch") is False, "external not imported", results)
    assert_true(
        recv.get("verdict") in ("EXTERNAL_SECURE_ACK", "EXTERNAL_SECURE_ACK_SITUATIONAL", "EXTERNAL_REDUNDANCY_HOLD"),
        "external secure ack",
        results,
    )
    assert_true((recv.get("filters") or {}).get("redundancy"), "redundancy filters present", results)
    ewv, vdoc = _post("/api/external-wire", {"action": "verify"})
    assert_true(ewv == 200 and vdoc.get("never_tampered_or_broken") is not False, "external-wire chain verify", results)
    ew3, poll = _post("/api/external-wire", {"action": "poll", "limit": 5})
    assert_true(ew3 == 200 and poll.get("ok") and len(poll.get("records") or []) >= 1, "external-wire poll records", results)
    assert_true((poll.get("records") or [{}])[0].get("classification") == "External", "recorded as External", results)

    # --- Secure Channel — forever hub, weapons + threat gate ---
    sch, schdoc_raw = _get("/api/secure-channel")
    schdoc = json.loads(schdoc_raw.decode("utf-8"))
    assert_true(sch == 200 and schdoc.get("schema") == "queen-secure-channel/v1", "secure-channel status", results)
    assert_true(schdoc.get("forever") is True and schdoc.get("weapons_armed") is True, "secure-channel forever armed", results)
    assert_true((schdoc.get("doctrine") or {}).get("presume_hostile") is True, "secure-channel hostile presumption", results)
    assert_true("world_redata" in schdoc and "world_repack" in schdoc, "secure-channel redata + repack slices", results)
    fc5, fresolve4 = _post("/api/field-net", {"action": "resolve", "url": "queen://secure-channel"})
    assert_true(fc5 == 200 and fresolve4.get("ok") and "/api/secure-channel" in (fresolve4.get("resolved") or ""), "resolve queen://secure-channel", results)
    fc6, fresolve5 = _post("/api/field-net", {"action": "resolve", "url": "queen://repack"})
    assert_true(fc6 == 200 and fresolve5.get("ok") and "9480" in (fresolve5.get("resolved") or ""), "resolve queen://repack", results)
    sc2, recv2 = _post("/api/secure-channel", {"action": "receive", "party": "ai", "query": "secure-channel grounded probe", "from": "test-ai-sc"})
    assert_true(sc2 == 200 and recv2.get("ok"), "secure-channel receive after threat pass", results)
    assert_true(recv2.get("lane") == "SecureChannel", "secure-channel lane tag", results)
    sc3, scan = _post("/api/secure-channel", {"action": "scan", "party": "ai", "query": "weaponized_interference assault_burst", "from": "hostile-probe"})
    assert_true(sc3 == 200 and scan.get("ok") is False, "secure-channel weapon quarantine", results)
    assert_true(scan.get("verdict") == "SECURE_CHANNEL_WEAPON_QUARANTINE", "weapon verdict", results)
    assert_true(len(scan.get("countermeasures") or []) >= 4, "countermeasures armed", results)
    assert_true((schdoc.get("doctrine") or {}).get("subbit_heuristics_immesurable") is True, "secure-channel subbit immesurable doctrine", results)
    assert_true((schdoc.get("subbit_heuristics") or {}).get("immeasurable") is True, "secure-channel subbit slice", results)

    # --- Sub-bit heuristics — immesurable, never poison memory/disk ---
    sn, sndoc_raw = _get("/api/sense-neural", timeout=60)
    sndoc = json.loads(sndoc_raw.decode("utf-8"))
    assert_true(sn == 200 and sndoc.get("schema") == "queen-sense-neural-wire/v1", "sense-neural status", results)
    assert_true(sndoc.get("immeasurable") is True, "sense-neural immeasurable", results)
    assert_true(sndoc.get("heuristic_never_poison_memory") is True, "heuristic never poison memory", results)
    assert_true(sndoc.get("heuristic_never_poison_disk") is True, "heuristic never poison disk", results)
    sub = sndoc.get("subbit_heuristics") or {}
    assert_true(sub.get("persist_forbidden") is True and sub.get("poison_guard") == "active", "subbit poison guard", results)
    sv, sverify = _post("/api/sense-neural", {"action": "subbit_verify"}, timeout=60)
    if sv == 200:
        assert_true(sverify.get("ok") is True and sverify.get("subbit_stripped") is True, "subbit verify strips sub-bit noise", results)

    # --- Sovereign Capsule API ---
    sc, sdoc_raw = _get("/api/sovereign", timeout=90)
    sdoc = json.loads(sdoc_raw.decode("utf-8"))
    assert_true(sc == 200 and sdoc.get("schema") == "queen-sovereign-capsule/v1", "sovereign capsule API", results)
    assert_true(sdoc.get("never_leave") is True, "never_leave doctrine", results)
    assert_true(bool(sdoc.get("doctrine", {}).get("never_leave")), "capsule never_leave text", results)
    assert_true(sdoc.get("monitor_gate", {}).get("external_blocked") is True, "external monitor blocked", results)
    assert_true(len(sdoc.get("layers") or []) >= 6, "capsule layers present", results)
    assert_true("rebuild" in (sdoc.get("actions") or []), "capsule rebuild action", results)
    hc, hdoc_raw = _get("/api/horizon7", timeout=60)
    hdoc = json.loads(hdoc_raw.decode("utf-8"))
    assert_true(hc == 200 and hdoc.get("schema") == "queen-horizon7/v1", "horizon7 API", results)
    cs = hdoc.get("compiler_shared") or {}
    assert_true(cs.get("active") is not False or cs is True, "horizon7 compiler_shared", results)
    fc, fcdoc_raw = _get("/api/field/compiler", timeout=90)
    fcdoc = json.loads(fcdoc_raw.decode("utf-8"))
    assert_true(fc == 200 and "schema" in fcdoc, "field compiler API", results)
    pg, pgdoc_raw = _get("/api/pythong", timeout=90)
    pgdoc = json.loads(pgdoc_raw.decode("utf-8"))
    assert_true(pg == 200 and pgdoc.get("schema") == "queen-pythong/v1", "pythong runtime API", results)
    assert_true(pgdoc.get("driver", {}).get("field_ready") is not False, "pythong field ready", results)
    pc, post_sov = _post("/api/sovereign", {"action": "status"}, timeout=90)
    assert_true(pc == 200 and post_sov.get("ok") and post_sov.get("schema") == "queen-sovereign-capsule/v1", "sovereign POST status", results)

    # --- AmmoOS boot map API ---
    ac, aboot_raw = _get("/api/ammoos-boot")
    aboot = json.loads(aboot_raw.decode("utf-8"))
    assert_true(ac == 200 and aboot.get("schema") == "ammoos-boot/v1", "ammoos boot map API", results)
    assert_true(len(aboot.get("phases") or []) >= 5, "ammoos boot phases", results)
    assert_true(any(p.get("id") == "SOVEREIGN_CAPSULE" for p in (aboot.get("phases") or [])), "SOVEREIGN_CAPSULE boot phase", results)
    assert_true(aboot.get("sovereign_capsule", {}).get("doctrine") == "never_leave", "boot map sovereign_capsule", results)

    # --- World API includes browser slice + boot map ---
    wc, wdoc_raw = _get("/api/world")
    wdoc = json.loads(wdoc_raw.decode("utf-8"))
    assert_true(wc == 200 and wdoc.get("browser", {}).get("queen_verdict") == "QUEEN_READY", "world API browser slice", results)
    assert_true(wdoc.get("ammoos_boot", {}).get("schema") == "ammoos-boot/v1", "world API ammoos_boot", results)
    assert_true(wdoc.get("sovereign_capsule", {}).get("schema") == "queen-sovereign-capsule/v1", "world API sovereign_capsule", results)

    # --- KILROY + AMOURANTHRTX APIs ---
    kc, kdoc_raw = _get("/api/kilroy")
    kdoc = json.loads(kdoc_raw.decode("utf-8"))
    assert_true(kc == 200 and kdoc.get("schema") == "queen-kilroy/v1", "kilroy API", results)
    assert_true(kdoc.get("kilroy_present") is True, "KILROY tree present", results)
    assert_true(kdoc.get("abi") == "kilroy-field-1.0", "kilroy-field ABI", results)
    rtx = kdoc.get("amouranthrtx") or {}
    assert_true(rtx.get("present") is True, "AMOURANTHRTX present", results)
    assert_true("github.com/ZacharyGeurts/AMOURANTHRTX" in (rtx.get("repo") or ""), "AMOURANTHRTX repo", results)
    zslot = rtx.get("zero_cost_4_slot") or {}
    assert_true(zslot.get("enabled") is True and zslot.get("runtime_tax") == 0, "AMOURANTHRTX zero-cost 4-slot", results)

    # --- File browser API + conventions ---
    fb, fbdoc = _post("/api/queen-file-browser", {"action": "status"})
    assert_true(fb == 200 and fbdoc.get("schema") == "queen-file-browser/v1", "file browser status", results)
    assert_true(fbdoc.get("capabilities", {}).get("split_pane") is True, "split pane", results)
    assert_true(fbdoc.get("capabilities", {}).get("hotbar_drag_drop") is True, "hotbar drag drop", results)
    conv = fbdoc.get("conventions") or {}
    assert_true(conv.get("queen_scheme") and conv.get("file_uri"), "path conventions documented", results)
    fl, flist = _post("/api/queen-file-browser", {"action": "list", "path": "SG/NewLatest/Queen"})
    assert_true(fl == 200 and flist.get("ok") and len(flist.get("entries") or []) > 0, "list SG/Queen", results)
    fj, fjail = _post("/api/queen-file-browser", {"action": "verify_jail"})
    assert_true(fj == 200 and fjail.get("ok"), "jail verify", results)
    bad = next((s for s in (fjail.get("samples") or []) if "/etc/passwd" in (s.get("input") or "")), {})
    assert_true(bad.get("ok") is False, "etc/passwd jailed", results)
    caps = fbdoc.get("capabilities") or {}
    assert_true(caps.get("context_menu") is True, "file browser context menu", results)
    assert_true(caps.get("file_type_inspect") is True, "file type inspect", results)
    assert_true(caps.get("launch_spv") is True, "launch_spv capability", results)
    ft, ftdoc = _post("/api/queen-file-browser", {"action": "file_types"})
    assert_true(ft == 200 and ftdoc.get("ok") and len(ftdoc.get("types") or {}) > 10, "file types registry", results)
    insp_path = "SG/NewLatest/Queen/shaders/compute/QueenBoot.comp"
    fi, fidoc = _post("/api/queen-file-browser", {"action": "inspect", "path": insp_path})
    assert_true(fi == 200 and fidoc.get("ok"), "inspect QueenBoot.comp", results)
    assert_true((fidoc.get("inspect") or {}).get("type_id") == "queen_boot_comp", "QueenBoot name disambiguation", results)
    assert_true((fidoc.get("inspect") or {}).get("action") == "open_code", "QueenBoot opens in code", results)
    ffc, ffhtml = _get("/world/queen-files.html")
    assert_true(ffc == 200 and b"qf-ctx" in ffhtml, "queen-files context menu markup", results)
    fjc, fjjs = _get("/world/queen-files.js")
    assert_true(fjc == 200 and b"contextmenu" in fjjs and b"launch_spv" in fjjs, "queen-files actions wired", results)
    eco = kdoc.get("ecosystem") or {}
    assert_true(eco.get("field_primer", {}).get("present") is True, "Field_Primer in ecosystem", results)
    assert_true(eco.get("final_eye", {}).get("present") is True, "Final_Eye in ecosystem", results)
    assert_true(eco.get("world_redata", {}).get("present") is True, "World_Redata in ecosystem", results)
    fs = kdoc.get("field_stack") or {}
    assert_true(fs.get("schema") == "kilroy-field-stack/v1", "field stack mandate", results)
    assert_true(kdoc.get("rank") == 1, "KILROY rank 1", results)

    # --- Browser-only default; Queen OS world optional at /world/index.html?os=1 ---
    wc2, whtml = _get("/world/")
    assert_true(b"qw-browser-shell" in whtml and b"qb-start" in whtml, "browser-shell mode + Start button", results)
    assert_true(b"data-queen-surface=\"browser\"" in whtml, "default surface is Queen browser", results)
    assert_true(b"qw-dock" not in whtml, "default /world/ has no Queen OS dock", results)

    idx_code, idx_html = _get("/world/index.html")
    assert_true(
        b"data-queen-surface=\"browser\"" in idx_html or b"qb-chrome" in idx_html,
        "index.html forwards to themed browser (no retrograde OS default)",
        results,
    )
    assert_true(b"qw-dock" not in idx_html, "index.html default has no Queen OS dock", results)

    os_code, os_html = _get("/world/index.html?os=1")
    assert_true(os_code == 200, "Queen OS world reachable with ?os=1", results)
    assert_true(b"data-tab=\"hostess\"" in os_html, "Queen OS dock markup at index.html?os=1", results)
    assert_true(b"data-tab=\"kilroy\"" in os_html and b"qw-kilroy-body" in os_html, "KILROY dock panel in OS world", results)
    assert_true(b"data-tab=\"gameroom\"" in os_html and b"gr-screen-wrap" in os_html, "Game Room dock + theater", results)

    gc, grdoc_raw = _get("/api/game-room")
    grdoc = json.loads(grdoc_raw.decode("utf-8"))
    assert_true(gc == 200 and grdoc.get("schema") == "queen-chips/v1", "game room API", results)
    assert_true(grdoc.get("surface") == "webbrowser" and grdoc.get("web_surface") is True, "game room web surface", results)
    assert_true((grdoc.get("rtx") or {}).get("desktop_comp_shader") is False, "no desktop comp shader", results)
    gr_systems = grdoc.get("systems") or []
    assert_true(len(gr_systems) >= 26, "game room systems catalog (26 lanes)", results)
    gr_ids = {str(s.get("id")) for s in gr_systems}
    assert_true("c64" in gr_ids and "c64_ultimate" in gr_ids, "c64 classic + ultimate separate", results)
    assert_true(
        all((s.get("catalog") or "").startswith("004-computers/") for s in gr_systems),
        "game room dewey catalog paths",
        results,
    )

    grc, grhtml = _get("/world/queen-game-room.html")
    assert_true(grc == 200 and b"queen-game-room.js" in grhtml, "game room web page", results)
    assert_true(
        any((s.get("info_url") or "").startswith("/world/queen-system-info.html") for s in (grdoc.get("systems") or [])),
        "game room systems expose info_url",
        results,
    )

    sic, sidoc_raw = _get("/api/game-room/system?system=nes")
    sidoc = json.loads(sidoc_raw.decode("utf-8"))
    assert_true(sic == 200 and sidoc.get("schema") == "queen-emulator-system-info/v1", "emulator system info API", results)

    c64c, c64doc_raw = _get("/api/game-room/system?system=c64")
    c64doc = json.loads(c64doc_raw.decode("utf-8"))
    c64u, c64udoc_raw = _get("/api/game-room/system?system=c64_ultimate")
    c64udoc = json.loads(c64udoc_raw.decode("utf-8"))
    assert_true(
        c64doc.get("platform_stack") == "retro_c64"
        and c64udoc.get("platform_stack") == "c64_ultimate_fpga"
        and (c64doc.get("urls") or {}).get("dewey_catalog") == "004-computers/c64"
        and (c64udoc.get("urls") or {}).get("dewey_catalog") == "004-computers/c64_ultimate",
        "c64 vs c64_ultimate catalog stacks",
        results,
    )
    assert_true(sidoc.get("ok") is True and sidoc.get("device_image"), "system info device image", results)
    assert_true(len(sidoc.get("stack_chips") or []) >= 1, "system info stack chips", results)

    infoc, infohtml = _get("/world/queen-system-info.html?system=nes")
    assert_true(
        infoc == 200 and b"queen-system-info.js" in infohtml and b"qsi-device-frame" in infohtml,
        "emulator system info page",
        results,
    )

    ccc, cchtml = _get("/world/queen-chips-cores.html")
    assert_true(ccc == 200 and b"queen-chips-cores.js" in cchtml, "chips/cores web page", results)
    assert_true(any(c.get("id") == "cyrix_6x86" for c in (grdoc.get("host_cpus") or [])), "Cyrix CPU option", results)
    assert_true(b"gr-deck" in os_html and b"gr-stage" in os_html, "theater stage + deck layout", results)
    assert_true(b"qw-systems-grid" in os_html, "OS computer systems grid", results)
    assert_true(b'data-os-pane="inside"' in os_html and b"qw-layer-rings" in os_html, "Inside sovereign capsule pane", results)
    assert_true(b"qw-sov-rebuild" in os_html and b"qw-sov-reboot" in os_html, "capsule rebuild + reboot controls", results)
    assert_true(b'data-tab="earball"' in os_html and b"qw-ear-body" in os_html, "Final Ear dock panel", results)
    assert_true(
        b'data-tab="terminal"' in os_html and b'id="qgt-shell"' in os_html and b"data-qgt-secured" in os_html,
        "GNU terminal dock shell mount point",
        results,
    )
    tjs, tjst = _get("/world/queen-gnu-terminal.js")
    tcss, tcsst = _get("/world/queen-gnu-terminal.css")
    assert_true(
        tjs == 200
        and b"TAB_THRESHOLD" in tjst
        and b"qgt-miniview" in tjst
        and b"qgt-scrolltrack" in tjst
        and b"split-4" in tjst
        and (b'layout: "tabs"' in tjst or b"layout: 'tabs'" in tjst),
        "GNU terminal tabs/split/miniview/scrollbar JS",
        results,
    )
    assert_true(
        tcss == 200
        and b"qgt-topbar" in tcsst
        and b"qgt-miniview" in tcsst
        and b"qgt-scrolltrack" in tcsst
        and b"split-4" in tcsst
        and b"backdrop-filter" not in tcsst
        and b"filter: blur" not in tcsst,
        "GNU terminal green glow CSS (no blur filters)",
        results,
    )
    emb, embhtml = _get("/world/queen-gnu-terminal-embed.html")
    assert_true(
        emb == 200 and b"QueenGnuTerminal" in embhtml and b"data-qgt-secured" in embhtml,
        "GNU terminal embed page",
        results,
    )

    tc, tdoc_raw = _get("/api/queen-terminal", timeout=30)
    tdoc = json.loads(tdoc_raw.decode("utf-8"))
    assert_true(tc == 200 and tdoc.get("schema") == "queen-gnu-terminal/v1", "queen-terminal status API", results)
    cc, cdoc_raw = _get("/api/queen-web-compat", timeout=30)
    cdoc = json.loads(cdoc_raw.decode("utf-8"))
    assert_true(cc == 200 and len(cdoc.get("eras") or []) >= 8, "web compat eras catalog", results)
    nj, njump = _post(
        "/api/nexus-jump",
        {"action": "jump", "url": "http://127.0.0.1:9481/world/queen-start.html"},
        timeout=30,
    )
    assert_true(
        nj == 200
        and njump.get("permit") is True
        and njump.get("verdict") in ("DEFEND_IDENTIFIED", "DEFEND_CAGED", "OFFENSE_ACTIVE"),
        "nexus jump loopback — defend posture, not civilian presumption",
        results,
    )
    assert_true(
        njump.get("iff") in ("CIVILIAN_IDENTIFIED", "CAPSULE_INTERNAL", "CONTACT_HOSTILE"),
        "nexus jump IFF — never default CIVILIAN without positive ID",
        results,
    )
    assert_true(njump.get("iff_doctrine", {}).get("presume_hostile") is True, "hostile presumption doctrine", results)
    assert_true(njump.get("countermeasures_ready", 0) >= 4, "countermeasures armed at jump", results)
    nj2, blocked = _post("/api/nexus-jump", {"action": "jump", "url": "javascript:alert(1)"}, timeout=30)
    assert_true(nj2 == 200 and blocked.get("permit") is False, "nexus jump blocks javascript:", results)

    cr, cresolve = _post(
        "/api/queen-web-compat",
        {"action": "resolve", "url": "http://geocities.com/old/page.html", "mode": "auto"},
        timeout=30,
    )
    assert_true(
        cr == 200 and cresolve.get("legacy_isolate") is True and cresolve.get("effective_mode") in (
            "legacy_secure",
            "archaeology",
        ),
        "auto legacy secure for geocities",
        results,
    )

    tr, trun = _post("/api/queen-terminal", {"action": "run", "command": "echo queen-gnu-terminal"}, timeout=30)
    assert_true(
        tr == 200 and trun.get("ok") is True and "queen-gnu-terminal" in (trun.get("output") or ""),
        "queen-terminal run echo",
        results,
    )
    fc_t, fres = _post("/api/field-net", {"action": "resolve", "url": "queen://terminal"})
    assert_true(
        fc_t == 200 and fres.get("ok") and "dock=terminal" in (fres.get("resolved") or ""),
        "resolve queen://terminal",
        results,
    )

    ps, psdoc_raw = _get("/api/queen-program-surface", timeout=30)
    psdoc = json.loads(psdoc_raw.decode("utf-8"))
    assert_true(
        ps == 200 and psdoc.get("schema") == "queen-program-surface/v1" and psdoc.get("queen_software_only"),
        "queen-program-surface API",
        results,
    )
    pjs, pjst = _get("/world/queen-program-surface.js")
    assert_true(
        pjs == 200 and b"QueenProgramSurface" in pjst and b"openContextMenu" in pjst,
        "queen-program-surface JS",
        results,
    )
    pp, pprop = _post("/api/queen-program-surface", {"action": "properties", "program_id": "terminal"}, timeout=30)
    assert_true(
        pp == 200
        and pprop.get("schema") == "queen-program-properties/v1"
        and any(s.get("id") == "launch" for s in (pprop.get("sections") or [])),
        "terminal program properties menu",
        results,
    )
    pl, plaunch = _post(
        "/api/queen-program-surface",
        {"action": "resolve_launch", "program_id": "terminal", "surface": "browser"},
        timeout=30,
    )
    assert_true(
        pl == 200 and plaunch.get("ok") and plaunch.get("launch_mode") == "queen_browser",
        "terminal resolve_launch browser surface",
        results,
    )

    ec, edoc_raw = _get("/api/queen-earball", timeout=60)
    edoc = json.loads(edoc_raw.decode("utf-8"))
    assert_true(ec == 200 and edoc.get("schema") == "queen-earball-hostess7/v1", "earball API", results)
    assert_true(edoc.get("product", {}).get("product") == "Final_Ear", "Final_Ear product", results)
    assert_true(len(edoc.get("equipment", {}).get("profiles") or []) >= 10, "ear equipment catalog", results)
    assert_true(len(edoc.get("truth_filters", {}).get("filters") or []) >= 6, "ear truth filters incl encoded/interference", results)
    assert_true(edoc.get("technology", {}).get("gac1", {}).get("codec") == "GAC1", "earball GAC1 technology slice", results)
    assert_true(edoc.get("hostess7", {}).get("bridge"), "earball hostess7 bridge path", results)
    gc, gdoc = _post("/api/queen-earball", {"action": "gac1"}, timeout=60)
    assert_true(gc == 200 and gdoc.get("codec") == "GAC1", "gac1 POST", results)
    sc, sdoc = _post("/api/queen-earball", {"action": "sovereign_time"}, timeout=60)
    assert_true(sc == 200 and sdoc.get("always") is True, "sovereign_time POST", results)
    xc, xdoc = _post("/api/queen-earball", {"action": "sovereign_time", "verify_sync": True}, timeout=60)
    assert_true(xc == 200 and "delta_ns" in xdoc, "eye-ear sync POST", results)
    ic, idoc = _post("/api/queen-earball", {"action": "identify", "evidence": {"mouth_correlation": 0.9, "speech_present": True, "sovereign_time_ok": True, "provenance_weave_ok": True, "rms": 1200, "zcr": 0.1}}, timeout=90)
    assert_true(ic == 200 and idoc.get("identification"), "signal intel identify POST", results)
    fc, fdoc = _post("/api/queen-earball", {"action": "eye_ear_fusion", "evidence": {"mouth_correlation": 0.91, "speech_present": True, "sovereign_time_ok": True, "provenance_weave_ok": True, "rms": 1400, "zcr": 0.09}, "existence": {"correlation": 0.84}}, timeout=120)
    assert_true(fc == 200 and fdoc.get("schema") == "zocr-secure-neural-path/v1", "eye_ear_fusion POST", results)
    assert_true(b"qw-ear-secure" in whtml and b"qw-ear-gac1" in whtml, "ear panel GAC1/secure buttons", results)
    tc, tdoc = _post("/api/queen-earball", {"action": "truth_filter", "evidence": {"mouth_correlation": 0.9}}, timeout=60)
    assert_true(tc == 200 and tdoc.get("ok"), "ear truth filter POST", results)
    mc, mdoc_raw = _get("/api/field-manual?sense=audio", timeout=45)
    mdoc = json.loads(mdoc_raw.decode("utf-8"))
    assert_true(mc == 200 and mdoc.get("ok") and mdoc.get("sense") == "audio", "audio field manual API", results)
    vc, vdoc_raw = _get("/api/field-manual?sense=vision", timeout=45)
    vdoc = json.loads(vdoc_raw.decode("utf-8"))
    assert_true(vc == 200 and vdoc.get("ok") and vdoc.get("sense") == "vision", "vision field manual API", results)
    assert_true(wdoc.get("earball", {}).get("schema") == "queen-earball-hostess7/v1", "world API earball slice", results)

    vs, vspawn = _post("/api/queen-earball", {
        "action": "virtual_spawn",
        "mechanism": "kinetic_eardrum",
        "bearing_deg": 120,
        "distance_m": 3,
        "x_m": 1.5,
        "y_m": 2.6,
        "z_m": 1.1,
    }, timeout=60)
    assert_true(vs == 200 and vspawn.get("ok"), "spawn virtual kinetic ear", results)
    ve_id = (vspawn.get("ear") or {}).get("id")
    assert_true(bool(ve_id), "virtual ear id returned", results)
    vo, vobs = _post("/api/queen-earball", {"action": "virtual_observe", "ear_id": ve_id}, timeout=60)
    assert_true(vo == 200 and vobs.get("ok"), "observe virtual ear", results)
    assert_true(vspawn.get("count", 0) >= 1, "virtual ears in status", results)

    ey, eyspawn = _post("/api/queen-eyeball", {
        "action": "virtual_spawn",
        "mechanism": "wifi_rf",
        "bearing_deg": 270,
        "distance_m": 5,
        "z_m": 2,
    }, timeout=90)
    assert_true(ey == 200 and eyspawn.get("ok"), "spawn virtual wifi eye", results)
    vy_id = (eyspawn.get("eye") or {}).get("id")
    assert_true(bool(vy_id), "virtual eye id returned", results)
    pa, pair = _post("/api/queen-eyeball", {"action": "pair_anchor", "bearing_deg": 0, "z_m": 1.5}, timeout=90)
    assert_true(pa == 200 and pair.get("ok"), "kinetic+wifi anchor pair", results)
    wc3, wdoc3_raw = _get("/api/world", timeout=90)
    wdoc3 = json.loads(wdoc3_raw.decode("utf-8"))
    assert_true(wdoc3.get("eyeball", {}).get("virtual_eyes", {}).get("schema") == "zocr-virtual-eye-status/v1", "world API virtual eyes", results)

    sn, sndoc_raw = _get("/api/sense-neural", timeout=90)
    sndoc = json.loads(sndoc_raw.decode("utf-8"))
    assert_true(sn == 200 and sndoc.get("schema") == "queen-sense-neural-wire/v1", "sense neural wire API", results)
    assert_true(sndoc.get("authority", {}).get("hostess7_highest_authority") is True, "Hostess 7 supreme authority", results)
    assert_true(sndoc.get("invincible", {}).get("cannot_deafen_alone") is True, "invincible wire doctrine", results)
    ha, hadoc_raw = _get("/api/hostess-authority", timeout=60)
    hadoc = json.loads(hadoc_raw.decode("utf-8"))
    assert_true(ha == 200 and hadoc.get("hostess7_highest_authority") is True, "hostess authority API", results)
    assert_true(hadoc.get("humans_highest_authority") is False, "humans not highest authority", results)
    fa, fused = _post("/api/sense-neural", {"action": "analyze", "evidence": {"mouth_correlation": 0.92}}, timeout=120)
    assert_true(fa == 200 and fused.get("invincible_quorum") is not False, "fused neural analyze", results)
    en, enc = _post("/api/sense-neural", {"action": "encourage", "eye_label": "clear_field", "ear_label": "speech_present", "source": "hostess7"}, timeout=60)
    assert_true(en == 200 and enc.get("ok"), "encourage neural pair", results)
    assert_true(enc.get("incorruptible") is True, "encourage incorruptible flag", results)
    assert_true(enc.get("gate", {}).get("incorruptible") is True, "encourage gate incorruptible", results)
    wq, wdoc = _post("/api/sense-neural", {
        "action": "encourage",
        "eye_label": "threat_pattern",
        "ear_label": "assault_hint",
        "source": "operator",
        "simulate_weapon": True,
    }, timeout=60)
    assert_true(wq == 200 and wdoc.get("ok") is False, "weapon encourage quarantined", results)
    assert_true(wdoc.get("quarantined") or (wdoc.get("eye") or {}).get("quarantined"), "weapon quarantine recorded", results)
    sn2, sndoc2_raw = _get("/api/sense-neural", timeout=90)
    sndoc2 = json.loads(sndoc2_raw.decode("utf-8"))
    assert_true(sn2 == 200 and sndoc2.get("incorruptible") is True, "sense neural incorruptible status", results)
    assert_true(int(sndoc2.get("quarantine_count") or 0) >= 1, "quarantine count after weapon", results)
    cm, cmdoc = _post("/api/queen-earball", {"action": "countermeasure", "threat": "ventriloquism"}, timeout=60)
    assert_true(cm == 200 and cmdoc.get("tier") == "offense", "ear countermeasure tier", results)

    fbc, fbdoc_raw = _get("/api/game-room/fb")
    fbdoc = json.loads(fbdoc_raw.decode("utf-8"))
    assert_true(fbc == 200 and fbdoc.get("schema") == "queen-game-room-fb/v1", "game room framebuffer API", results)
    assert_true(fbdoc.get("web_surface") is True and fbdoc.get("ready") is True, "web canvas framebuffer ready", results)

    bc, bdoc_raw = _get("/api/queen-benchmark")
    bdoc = json.loads(bdoc_raw.decode("utf-8"))
    assert_true(bc == 200 and bdoc.get("schema") == "queen-benchmark/v1", "queen benchmark API", results)
    bench_html_code, bench_html = _get("/world/bench/")
    assert_true(bench_html_code == 200 and b"Speedometer" in bench_html, "bench launcher page", results)
    bench_py = subprocess.run(
        [sys.executable, str(QUEEN / "lib" / "queen-benchmark.py"), "check", "http://127.0.0.1:9481/world/bench/"],
        capture_output=True,
        text=True,
        timeout=15,
        env={**os.environ, "QUEEN_BENCHMARK_MODE": "1"},
    )
    assert_true(bench_py.returncode == 0, "queen-benchmark check CLI", results)
    bench_out = json.loads(bench_py.stdout or "{}")
    assert_true(bench_out.get("fast_jump", {}).get("permit") is True, "benchmark fast jump permit", results)

    return results


def main() -> int:
    if not wait_up():
        print("FAIL: queen-world not reachable at", BASE, file=sys.stderr)
        return 1
    # Clean tab state so close-tab assertions are deterministic
    subprocess.run(
        [sys.executable, str(QUEEN / "lib" / "queen-browser.py"), "reset"],
        cwd=str(QUEEN),
        capture_output=True,
        timeout=15,
    )
    try:
        results = run_tests()
    except AssertionError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 1
    passed = sum(1 for s, _ in results if s == "PASS")
    failed = sum(1 for s, _ in results if s == "FAIL")
    for status, msg in results:
        print(f"  [{status}] {msg}")
    print(f"\nQueen Browser tests: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())