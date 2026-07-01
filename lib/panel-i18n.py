#!/usr/bin/env pythong
"""Panel i18n — language registry, IP locale detection, remembered preference."""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
PREF_FILE = STATE / "panel-language.json"
_i18n_env = os.environ.get("NEXUS_I18N_DIR", "").strip()
I18N_ROOT = Path(_i18n_env) if _i18n_env else (INSTALL / "data" / "i18n")
LANG_FILE = I18N_ROOT / "languages.json"
COUNTRY_FILE = I18N_ROOT / "country-locales.json"
MESSAGES_DIR = I18N_ROOT / "messages"
DEFAULT_LOCALE = "en-US"


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


def _lang_base(code: str) -> str:
    return str(code or "").split("-")[0].lower()


def load_languages() -> list[dict[str, Any]]:
    doc = _load_json(LANG_FILE, {"languages": []})
    langs = list(doc.get("languages") or [])
    if not langs:
        return [{"code": DEFAULT_LOCALE, "name": "American English", "native": "English (US)", "rtl": False}]
    en_us = [x for x in langs if x.get("code") == DEFAULT_LOCALE]
    rest = sorted(
        [x for x in langs if x.get("code") != DEFAULT_LOCALE],
        key=lambda x: str(x.get("name") or x.get("code") or "").lower(),
    )
    return (en_us[:1] or [{"code": DEFAULT_LOCALE, "name": "American English", "native": "English (US)", "rtl": False}]) + rest


def _locale_meta(code: str) -> dict[str, Any]:
    for row in load_languages():
        if row.get("code") == code:
            return row
    return {"code": code, "name": code, "native": code, "rtl": False}


def _country_locale(country_code: str) -> str:
    doc = _load_json(COUNTRY_FILE, {"map": {}, "default": DEFAULT_LOCALE})
    cc = str(country_code or "").upper()[:2]
    locale = (doc.get("map") or {}).get(cc) or doc.get("default") or DEFAULT_LOCALE
    codes = {x.get("code") for x in load_languages()}
    if locale in codes:
        return locale
    base = _lang_base(locale)
    for c in codes:
        if _lang_base(c) == base:
            return c
    return DEFAULT_LOCALE


def _fetch_egress_geo() -> dict[str, Any] | None:
    req = urllib.request.Request(
        "http://ip-api.com/json/?fields=status,country,countryCode,regionName,city,lat,lon,query",
        headers={"User-Agent": "NEXUS-Shield-Panel-I18n"},
    )
    try:
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, OSError):
        return None
    if data.get("status") != "success":
        return None
    return data


def detect_locale_from_ip() -> dict[str, Any]:
    geo = _fetch_egress_geo()
    if not geo:
        return {
            "code": DEFAULT_LOCALE,
            "source": "default",
            "country_code": "",
            "country": "",
            "city": "",
            "egress_ip": "",
            "detected_at": _now(),
        }
    cc = str(geo.get("countryCode") or "").upper()
    code = _country_locale(cc)
    return {
        "code": code,
        "source": "detected",
        "country_code": cc,
        "country": geo.get("country") or "",
        "region": geo.get("regionName") or "",
        "city": geo.get("city") or "",
        "egress_ip": geo.get("query") or "",
        "lat": geo.get("lat"),
        "lon": geo.get("lon"),
        "detected_at": _now(),
    }


def load_preference() -> dict[str, Any]:
    doc = _load_json(PREF_FILE, {})
    if not doc:
        return {
            "code": "",
            "remember": True,
            "user_set": False,
            "source": "unset",
            "updated": None,
        }
    return doc


def _user_locked(doc: dict[str, Any]) -> bool:
    return bool(doc.get("user_set")) or str(doc.get("source") or "") == "user"


def resolve_locale() -> dict[str, Any]:
    """Apply IP detection only when operator has not set or changed language yet."""
    pref = load_preference()
    if _user_locked(pref) and pref.get("code"):
        meta = _locale_meta(str(pref["code"]))
        return {**pref, **meta, "locked": True}

    if pref.get("code") and str(pref.get("source")) in ("detected", "default", "unset"):
        meta = _locale_meta(str(pref["code"]))
        return {**pref, **meta, "locked": False}

    if pref.get("code"):
        meta = _locale_meta(str(pref["code"]))
        return {**pref, **meta, "locked": _user_locked(pref)}

    detected = detect_locale_from_ip()
    out = {
        "code": detected["code"],
        "remember": True,
        "user_set": False,
        "source": detected.get("source") or "detected",
        "country_code": detected.get("country_code") or "",
        "country": detected.get("country") or "",
        "region": detected.get("region") or "",
        "city": detected.get("city") or "",
        "egress_ip": detected.get("egress_ip") or "",
        "detected_at": detected.get("detected_at"),
        "updated": _now(),
    }
    if out.get("remember"):
        _save_json(PREF_FILE, out)
    meta = _locale_meta(out["code"])
    return {**out, **meta, "locked": False}


def set_language(code: str, remember: bool = True) -> dict[str, Any]:
    code = str(code or "").strip()
    codes = {x.get("code") for x in load_languages()}
    if code not in codes:
        return {"ok": False, "error": "unknown_locale", "code": code}
    cur = load_preference()
    out = {
        **cur,
        "code": code,
        "remember": bool(remember),
        "user_set": True,
        "source": "user",
        "updated": _now(),
    }
    _save_json(PREF_FILE, out)
    meta = _locale_meta(code)
    msgs = load_messages(code)
    return {
        "ok": True,
        **out,
        **meta,
        "messages": msgs,
        "locked": True,
        "pack_path": str(MESSAGES_DIR / f"{code}.json"),
        "fallback_path": str(MESSAGES_DIR / f"{DEFAULT_LOCALE}.json"),
    }


def load_messages(code: str) -> dict[str, str]:
    base = _load_json(MESSAGES_DIR / f"{DEFAULT_LOCALE}.json", {"strings": {}})
    strings = dict((base.get("strings") or {}))
    if code and code != DEFAULT_LOCALE:
        loc = _load_json(MESSAGES_DIR / f"{code}.json", {})
        if not loc.get("strings"):
            base_code = _lang_base(code)
            for path in MESSAGES_DIR.glob("*.json"):
                if _lang_base(path.stem) == base_code and path.stem != DEFAULT_LOCALE:
                    loc = _load_json(path, {})
                    break
        strings.update(loc.get("strings") or {})
    return strings


def catalog_paths() -> dict[str, str]:
    return {
        "i18n_root": str(I18N_ROOT),
        "languages_file": str(LANG_FILE),
        "country_locales_file": str(COUNTRY_FILE),
        "messages_dir": str(MESSAGES_DIR),
        "preference_file": str(PREF_FILE),
    }


def panel_json() -> dict[str, Any]:
    active = resolve_locale()
    code = str(active.get("code") or DEFAULT_LOCALE)
    return {
        "schema": "panel-language/v1",
        "updated": active.get("updated") or _now(),
        "active": {
            "code": code,
            "name": active.get("name") or _locale_meta(code).get("name"),
            "native": active.get("native") or _locale_meta(code).get("native"),
            "rtl": bool(active.get("rtl")),
            "source": active.get("source") or "unset",
            "user_set": bool(active.get("user_set")),
            "remember": bool(active.get("remember", True)),
            "locked": bool(active.get("locked")),
            "country_code": active.get("country_code") or "",
            "country": active.get("country") or "",
            "city": active.get("city") or "",
            "egress_ip": active.get("egress_ip") or "",
        },
        "default_locale": DEFAULT_LOCALE,
        "languages": load_languages(),
        "messages": load_messages(code),
        "paths": catalog_paths(),
    }


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    if cmd == "detect":
        print(json.dumps(detect_locale_from_ip(), ensure_ascii=False))
        return 0
    if cmd == "paths":
        print(json.dumps(catalog_paths(), ensure_ascii=False))
        return 0
    if cmd == "set" and len(sys.argv) >= 3:
        code = sys.argv[2]
        remember = True
        if len(sys.argv) >= 4:
            try:
                body = json.loads(sys.argv[3])
                code = str(body.get("code") or code)
                remember = bool(body.get("remember", True))
            except json.JSONDecodeError:
                remember = sys.argv[3].lower() in ("1", "true", "yes")
        print(json.dumps(set_language(code, remember), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: panel-i18n.py [json|detect|paths|set CODE [JSON]]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())