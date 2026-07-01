#!/usr/bin/env pythong
"""Hostess profile — operator name, address, URLs, business/person/family for US page."""
from __future__ import annotations

import json
import os
import re
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
PROFILE = STATE / "hostess-profile.json"

KINDS = frozenset({"person", "business", "family"})


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        import importlib.util
        _p = Path(__file__).resolve().parent / "sovereign-clock.py"
        _s = importlib.util.spec_from_file_location("sovereign_clock", _p)
        if not _s or not _s.loader:
            raise ImportError("sovereign-clock.py missing")
        _SOVEREIGN_CLOCK_MOD = importlib.util.module_from_spec(_s)
        _s.loader.exec_module(_SOVEREIGN_CLOCK_MOD)
    return _SOVEREIGN_CLOCK_MOD.utc_z()


_SOVEREIGN_CLOCK_MOD = None



def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _norm_url(raw: str) -> str:
    s = str(raw or "").strip()
    if not s:
        return ""
    if not re.match(r"^https?://", s, re.I):
        s = "https://" + s
    try:
        p = urlparse(s)
        if not p.netloc:
            return ""
        return f"{p.scheme}://{p.netloc}{p.path or ''}".rstrip("/")
    except ValueError:
        return ""


def _operator_default() -> dict[str, Any]:
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "operator_default", INSTALL / "lib" / "operator-default.py",
        )
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.load_default()
    except Exception:
        pass
    return {}


def default_profile() -> dict[str, Any]:
    host = socket.gethostname()
    od = _operator_default()
    urls = []
    for u in od.get("urls") or []:
        nu = _norm_url(str(u))
        if nu:
            urls.append(nu)
    return {
        "schema": "hostess-profile/v1",
        "updated": _now(),
        "display_name": str(od.get("display_name") or "")[:120],
        "address": str(od.get("address") or "")[:240],
        "profile_kind": "person",
        "urls": urls[:64],
        "host_machine": {
            "hostname": host,
            "fqdn": socket.getfqdn(),
            "explicit_label": f"This host · {host}",
            "remember": bool(od.get("remember", True)),
        },
        "notes": "",
    }


def load_profile() -> dict[str, Any]:
    doc = _load_json(PROFILE, {})
    if not doc.get("schema") or (not doc.get("display_name") and not doc.get("address")):
        try:
            import importlib.util

            spec = importlib.util.spec_from_file_location(
                "operator_default", INSTALL / "lib" / "operator-default.py",
            )
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                doc = mod.seed_hostess_profile()
        except Exception:
            doc = default_profile() if not doc.get("schema") else doc
    if not doc.get("schema"):
        doc = default_profile()
    base = default_profile()
    for key in ("display_name", "address", "profile_kind", "urls", "notes"):
        if doc.get(key) not in (None, ""):
            base[key] = doc[key]
    if isinstance(doc.get("host_machine"), dict):
        base["host_machine"] = {**base["host_machine"], **doc["host_machine"]}
    base["updated"] = doc.get("updated") or _now()
    if base.get("profile_kind") not in KINDS:
        base["profile_kind"] = "person"
    urls = []
    for u in base.get("urls") or []:
        if isinstance(u, str):
            nu = _norm_url(u)
            if nu and nu not in urls:
                urls.append(nu)
        elif isinstance(u, dict):
            nu = _norm_url(str(u.get("url") or ""))
            if nu and nu not in urls:
                urls.append(nu)
    base["urls"] = urls[:64]
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "host_security_tier", INSTALL / "lib" / "host-security-tier.py",
        )
        if spec and spec.loader:
            tier_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(tier_mod)
            return tier_mod.enrich_profile(base)
    except Exception:
        pass
    return base


def save_profile(body: dict[str, Any]) -> dict[str, Any]:
    cur = load_profile()
    kind = str(body.get("profile_kind") or cur.get("profile_kind") or "person").lower()
    if kind not in KINDS:
        kind = "person"
    urls_in = body.get("urls")
    urls: list[str] = list(cur.get("urls") or [])
    if isinstance(urls_in, list):
        urls = []
        for u in urls_in:
            nu = _norm_url(str(u.get("url") if isinstance(u, dict) else u))
            if nu:
                urls.append(nu)
    out = {
        **cur,
        "display_name": str(body.get("display_name") or cur.get("display_name") or "").strip()[:120],
        "address": str(body.get("address") or cur.get("address") or "").strip()[:240],
        "profile_kind": kind,
        "urls": urls[:64],
        "notes": str(body.get("notes") or cur.get("notes") or "").strip()[:500],
        "updated": _now(),
    }
    hm = dict(out.get("host_machine") or {})
    hm["hostname"] = socket.gethostname()
    hm["fqdn"] = socket.getfqdn()
    hm["explicit_label"] = str(
        body.get("host_label")
        or hm.get("explicit_label")
        or f"This host · {hm['hostname']}"
    )[:160]
    hm["remember"] = True
    out["host_machine"] = hm
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "host_security_tier", INSTALL / "lib" / "host-security-tier.py",
        )
        if spec and spec.loader:
            tier_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(tier_mod)
            out = tier_mod.enrich_profile(out)
            tier_mod.publish_tier(out)
    except Exception:
        pass
    _save_json(PROFILE, out)
    return out


def attach_to_us_field(doc: dict[str, Any]) -> dict[str, Any]:
    prof = load_profile()
    ident = dict(doc.get("identity") or {})
    ident["hostess_profile"] = {
        "display_name": prof.get("display_name"),
        "address": prof.get("address"),
        "profile_kind": prof.get("profile_kind"),
        "url_count": len(prof.get("urls") or []),
    }
    ident["host_machine"] = prof.get("host_machine") or {}
    doc["identity"] = ident
    doc["hostess_profile"] = prof
    doc["host_machine_explicit"] = prof.get("host_machine") or {}
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "host_security_tier", INSTALL / "lib" / "host-security-tier.py",
        )
        if spec and spec.loader:
            tier_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(tier_mod)
            doc = tier_mod.attach_to_us_field(doc)
    except Exception:
        pass
    return doc


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "json":
        print(json.dumps(load_profile(), ensure_ascii=False))
        return 0
    if cmd == "save" and len(sys.argv) >= 3:
        body = json.loads(sys.argv[2])
        print(json.dumps(save_profile(body), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: hostess-profile.py [json|save JSON]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())