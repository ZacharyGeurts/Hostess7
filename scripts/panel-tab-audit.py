#!/usr/bin/env pythong
"""Panel tab audit — verify each tab has required API data and DOM anchors before next tab."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(ROOT)))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
PANEL_PORT = int(os.environ.get("NEXUS_THREAT_PANEL_PORT", "9477"))
PANEL_URL = os.environ.get("NEXUS_PANEL_URL", f"https://127.0.0.1:{PANEL_PORT}")

TAB_SPECS: dict[str, dict[str, Any]] = {
    "command": {"keys": ["field_command", "gatekeeper"], "dom": ["command-motto", "command-know"]},
    "us": {"keys": ["us_field"], "dom": ["us-motto", "us-gateway", "us-hostess-profile"]},
    "packets": {"keys": ["gatekeeper"], "dom": ["connections"]},
    "threats": {"keys": ["home_protector", "host_attacks"], "dom": ["home-protector-stats"]},
    "intel": {"keys": ["audio_train", "field_rf"], "dom": ["audio-train-motto"]},
    "signals": {"keys": ["signals_field", "field_antenna", "field_radio"], "dom": ["signals-operator", "signals-antenna-banner", "signals-radio-menu"]},
    "dns": {"keys": ["field_dns"], "dom": ["dns-hero-title", "dns-posture-strip"]},
    "outside": {"keys": ["field_outside_talk"], "dom": ["outside-hero-title"]},
    "library": {"keys": ["h7_library"], "dom": ["library-search"]},
    "system": {"keys": ["settings"], "dom": ["settings-profile"]},
}

PENDING_RE = re.compile(r"^(Loading|Awaiting|Harvesting|Building|Scanning|Pulling)", re.I)


def _read_json_file(fp: Path) -> dict[str, Any] | None:
    if not fp.is_file() or fp.stat().st_size < 32:
        return None
    try:
        doc = json.loads(fp.read_text(encoding="utf-8", errors="replace"))
        return doc if isinstance(doc, dict) and doc else None
    except (OSError, json.JSONDecodeError, PermissionError):
        pass
    try:
        out = subprocess.check_output(
            ["sudo", "-n", "cat", str(fp)],
            stderr=subprocess.DEVNULL,
            timeout=20,
        )
        doc = json.loads(out.decode("utf-8", errors="replace"))
        return doc if isinstance(doc, dict) and doc else None
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError):
        return None


def _load_state_json() -> dict[str, Any] | None:
    for state_dir in (STATE, Path("/var/lib/nexus-shield")):
        doc = _read_json_file(state_dir / "threat-panel.json")
        if doc:
            return doc
    return None


STATE_FRAGMENTS: dict[str, str] = {
    "gatekeeper": "connection-intent.json",
    "field_antenna": "field-antenna-panel.json",
    "field_radio": "field-radio-panel.json",
    "signals_field": "signals-field-panel.json",
    "field_dns": "field-dns-panel.json",
    "home_protector": "home-protector-panel.json",
    "host_attacks": "host-attacks.json",
    "audio_train": "audio-train.json",
    "field_rf": "field-rf-panel.json",
}


def _shell_json(cmd: str, *, timeout: int = 90) -> dict[str, Any] | None:
    env = {**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)}
    try:
        out = subprocess.check_output(
            ["bash", "-c", cmd],
            stderr=subprocess.DEVNULL,
            timeout=timeout,
            env=env,
            cwd=str(INSTALL),
        )
        doc = json.loads(out.decode("utf-8", errors="replace"))
        return doc if isinstance(doc, dict) else None
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError):
        return None


def _assemble_from_state(*, write: bool = True) -> dict[str, Any] | None:
    """Fast path: stitch threat-panel.json from existing state fragments (no RF cycle)."""
    doc: dict[str, Any] = {"updated": "assembled", "panel_ready": True}
    loaded = 0
    for key, rel in STATE_FRAGMENTS.items():
        frag = _read_json_file(STATE / rel)
        if frag:
            doc[key] = frag
            loaded += 1
    for key, cmd in (
        ("field_command", f'pythong "{INSTALL}/lib/field-command.py" json'),
        ("us_field", f'pythong "{INSTALL}/lib/field-us-intel.py" json'),
        ("field_outside_talk", f'pythong "{INSTALL}/lib/field-outside-talk.py" json'),
        (
            "h7_library",
            f'NEXUS_STATE_DIR="{STATE}" NEXUS_INSTALL_ROOT="{INSTALL}" '
            f'pythong "{INSTALL}/lib/h7-library-bridge.py" build',
        ),
        (
            "settings",
            f'source "{INSTALL}/lib/nexus-common.sh" && '
            f'source "{INSTALL}/lib/nexus-settings.sh" && nexus_settings_json',
        ),
    ):
        if key in doc:
            continue
        frag = _shell_json(cmd, timeout=120 if key == "h7_library" else 45)
        if frag:
            doc[key] = frag
            loaded += 1
    if loaded < 4:
        return None
    if write:
        out = STATE / "threat-panel.json"
        try:
            out.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass
    return doc


def _fetch_panel_json() -> dict[str, Any] | None:
    ctx = __import__("ssl").create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = __import__("ssl").CERT_NONE
    for url in (f"{PANEL_URL}/api/field?full=1", f"{PANEL_URL}/api/field"):
        req = urllib.request.Request(url, headers={"User-Agent": "NEXUS-Panel-Tab-Audit"})
        try:
            with urllib.request.urlopen(req, timeout=45, context=ctx) as resp:
                doc = json.loads(resp.read().decode("utf-8", errors="replace"))
                if isinstance(doc, dict) and len(doc) > 2:
                    return doc
        except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, OSError):
            continue
    return _load_state_json()


def _build_local_field() -> dict[str, Any]:
    env = {
        **os.environ,
        "NEXUS_INSTALL_ROOT": str(INSTALL),
        "NEXUS_STATE_DIR": str(STATE),
        "NEXUS_THREAT_PANEL": "1",
        "NEXUS_FIELD_ANTENNA": "1",
        "NEXUS_FIELD_RADIO": "1",
        "NEXUS_SIGNALS_FIELD": "1",
    }
    subprocess.run(
        [
            "bash", "-c",
            (
                f'source "{INSTALL}/lib/nexus-common.sh" && '
                f'source "{INSTALL}/lib/field-antenna.sh" 2>/dev/null; '
                f'source "{INSTALL}/lib/field-radio-catcher.sh" 2>/dev/null; '
                f'source "{INSTALL}/lib/signals-field.sh" 2>/dev/null; '
                f'NEXUS_STATE_DIR="{STATE}" NEXUS_INSTALL_ROOT="{INSTALL}" '
                f'pythong "{INSTALL}/lib/operator-default.py" seed >/dev/null 2>&1; '
                f'nexus_field_antenna_cycle 2>/dev/null; '
                f'source "{INSTALL}/lib/threat-panel.sh" && nexus_threat_panel_publish'
            ),
        ],
        capture_output=True,
        text=True,
        timeout=180,
        env=env,
        cwd=str(INSTALL),
    )
    panel_json = STATE / "threat-panel.json"
    if not panel_json.is_file():
        return {}
    try:
        return json.loads(panel_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _key_ready(data: dict[str, Any], key: str) -> bool:
    val = data.get(key)
    if val is None:
        return False
    if key == "gatekeeper":
        return isinstance(val, dict) and isinstance(val.get("connections"), list)
    if key == "signals_field":
        st = (val.get("stats") or {}) if isinstance(val, dict) else {}
        fr = (val.get("field_radio") or {}) if isinstance(val, dict) else {}
        return isinstance(val, dict) and (
            st.get("pulse_channels", 0) > 0
            or len(val.get("antennas") or []) > 0
            or len(fr.get("station_menu") or []) > 0
        )
    if key == "field_antenna":
        return isinstance(val, dict) and ((val.get("readiness") or {}).get("score") is not None or val.get("schema") == "field-antenna/v1")
    if key == "field_radio":
        return isinstance(val, dict) and len(val.get("station_menu") or []) > 0
    if key == "field_dns":
        return isinstance(val, dict) and (val.get("rfc_matrix") is not None or val.get("schema") == "field-dns/v2")
    if key == "h7_library":
        return isinstance(val, dict) and (val.get("books") is not None or val.get("updated"))
    if isinstance(val, dict):
        return bool(val.get("updated") or val.get("schema") or len(val) > 0)
    if isinstance(val, list):
        return len(val) > 0
    return bool(val)


def _dom_ids_present(html: str, ids: list[str]) -> list[str]:
    missing = []
    for dom_id in ids:
        if not re.search(rf'id=["\']{re.escape(dom_id)}["\']', html):
            missing.append(dom_id)
    return missing


def _ocr_smoke(asset: Path) -> str:
    if not asset.is_file():
        return "missing asset"
    bridge = ROOT / "lib" / "final-eye-h7-ocr.py"
    if bridge.is_file():
        try:
            proc = subprocess.run(
                [sys.executable, str(bridge), "ocr", str(asset)],
                capture_output=True, text=True, timeout=90, check=False,
                env={**os.environ, "NEXUS_INSTALL_ROOT": str(ROOT)},
            )
            doc = json.loads(proc.stdout or "{}")
            text = str(doc.get("text") or doc.get("ocr") or "").strip()
            if text:
                return text[:120]
        except (subprocess.SubprocessError, OSError, json.JSONDecodeError):
            pass
    return ""


def audit_tab(name: str, data: dict[str, Any], html: str) -> tuple[bool, list[str]]:
    spec = TAB_SPECS[name]
    errors: list[str] = []
    for key in spec["keys"]:
        if not _key_ready(data, key):
            errors.append(f"api:{key}")
    missing_dom = _dom_ids_present(html, spec["dom"])
    for dom_id in missing_dom:
        errors.append(f"dom:{dom_id}")
    return not errors, errors


def main() -> int:
    html_path = INSTALL / "panel" / "threat-panel.html"
    html = html_path.read_text(encoding="utf-8", errors="replace") if html_path.is_file() else ""

    data = _fetch_panel_json()
    source = "panel"
    if not data and os.environ.get("NEXUS_PANEL_AUDIT_SKIP_BUILD") != "1":
        data = _assemble_from_state()
        source = "state-assemble"
    if not data and os.environ.get("NEXUS_PANEL_AUDIT_SKIP_BUILD") != "1":
        data = _build_local_field()
        source = "local-build"
    if not data:
        print("TAB AUDIT FAIL: no panel JSON (start panel or run from installed tree)")
        return 1

    avatar = INSTALL / "panel" / "assets" / "amouranth-panel-avatar.png"
    legacy_avatar = INSTALL / "panel" / "assets" / "amouranth-twitch-avatar.png"
    wordmark = INSTALL / "panel" / "assets" / "amouranthrtx-wordmark.svg"
    header_checks = []
    if "amouranth-panel-avatar.png" not in html and "amouranth-twitch-avatar.png" not in html:
        header_checks.append("missing Queen panel avatar in HTML")
    if "amouranthrtx-wordmark.svg" not in html:
        header_checks.append("missing AMOURANTHRTX wordmark in HTML")
    if not avatar.is_file() and not legacy_avatar.is_file():
        header_checks.append("missing amouranth-panel-avatar.png asset")
    if not wordmark.is_file():
        header_checks.append("missing amouranthrtx-wordmark.svg asset")
    ocr_note = _ocr_smoke(avatar)
    if ocr_note:
        print(f"Header avatar OCR smoke: {ocr_note[:80]}")

    fail = 0
    print(f"=== NEXUS Panel Tab Audit (source={source}) ===")
    if header_checks:
        print("HEADER FAIL:", "; ".join(header_checks))
        fail += 1
    else:
        print("HEADER OK — Amouranth Twitch + AMOURANTHRTX wordmark present")

    for tab in TAB_SPECS:
        ok, errs = audit_tab(tab, data, html)
        if ok:
            print(f"TAB {tab}: PASS")
        else:
            print(f"TAB {tab}: FAIL — {', '.join(errs)}")
            fail += 1
            break  # stop at first failing tab (sequential gate)

    if fail:
        print("\nTAB AUDIT FAILED")
        return 1
    print("\nTAB AUDIT PASSED — all tabs have required data")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())