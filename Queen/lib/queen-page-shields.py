#!/usr/bin/env pythong
"""Queen page shields — user block rules, ad-space fingerprints, cosmetic CSS."""
from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

QUEEN = Path(__file__).resolve().parents[1]
STATE = Path(os.environ.get("NEXUS_STATE_DIR", QUEEN / ".nexus-state"))
SHIELDS_PATH = STATE / "queen-page-shields.json"

AD_HOST_FRAGMENTS = (
    "doubleclick.net", "googlesyndication.com", "googleadservices.com", "adservice.google",
    "taboola.com", "outbrain.com", "adnxs.com", "amazon-adsystem.com", "moatads.com",
    "scorecardresearch.com", "quantserve.com", "zedo.com", "criteo.com", "pubmatic.com",
    "rubiconproject.com", "openx.net", "media.net", "adform.net", "smartadserver.com",
)

AD_TOKEN_RE = re.compile(
    r"(^|[^a-z])(ad[s]?|advert|sponsor|promo|banner|taboola|outbrain|adsbygoogle|"
    r"commercial|affiliate|interstitial|popup-ad|ad-slot|ad-container|ad-wrapper)([^a-z]|$)",
    re.I,
)

RANDOM_CLASS_RE = re.compile(r"^[a-z]{0,3}[0-9a-f]{5,}$|^[0-9a-f]{8,}$|^[a-z]{1,2}[0-9]{4,}$", re.I)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load() -> dict[str, Any]:
    try:
        return json.loads(SHIELDS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save(doc: dict[str, Any]) -> None:
    SHIELDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = SHIELDS_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(SHIELDS_PATH)


def _default_doc() -> dict[str, Any]:
    return {
        "schema": "queen-page-shields/v1",
        "motto": "Right-click · never see again · structural fingerprints beat random class names",
        "updated": _now(),
        "policy": {
            "auto_proxy_external": True,
            "block_random_class_ads": True,
            "persist_host_rules": True,
        },
        "rules": [],
        "stats": {"blocked": 0, "rules": 0},
    }


def ensure_doc() -> dict[str, Any]:
    doc = _load()
    if not doc.get("schema"):
        doc = _default_doc()
        _save(doc)
    return doc


def _host_key(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def _rule_id() -> str:
    return f"shield-{uuid.uuid4().hex[:12]}"


def _stable_classes(classes: list[str] | None) -> list[str]:
    out: list[str] = []
    for c in classes or []:
        c = str(c).strip()
        if not c or RANDOM_CLASS_RE.match(c):
            continue
        if len(c) > 48:
            continue
        out.append(c)
    return out[:6]


def normalize_fingerprint(fp: dict[str, Any] | None) -> dict[str, Any]:
    fp = dict(fp or {})
    fp["tag"] = str(fp.get("tag") or "*").lower()
    fp["stable_classes"] = _stable_classes(fp.get("stable_classes") or fp.get("classes") or [])
    fp["structural_path"] = str(fp.get("structural_path") or fp.get("path") or "")
    fp["width_bucket"] = int(fp.get("width_bucket") or fp.get("w") or 0)
    fp["height_bucket"] = int(fp.get("height_bucket") or fp.get("h") or 0)
    fp["role"] = str(fp.get("role") or "")
    fp["ad_signals"] = list(fp.get("ad_signals") or [])
    if fp.get("id") and not RANDOM_CLASS_RE.match(str(fp["id"])):
        fp["stable_id"] = str(fp["id"])
    else:
        fp.pop("stable_id", None)
    return fp


def _fingerprint_hash(fp: dict[str, Any], host: str) -> str:
    blob = json.dumps({"host": host, **normalize_fingerprint(fp)}, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def add_rule(
    *,
    url: str = "",
    host: str = "",
    kind: str = "element",
    selector: str = "",
    fingerprint: dict[str, Any] | None = None,
    label: str = "",
    ad_space: bool = False,
    scope: str = "site",
) -> dict[str, Any]:
    doc = ensure_doc()
    host = (host or _host_key(url)).lower()
    if not host and scope != "global":
        return {"ok": False, "error": "host_required"}
    fp = normalize_fingerprint(fingerprint)
    rule: dict[str, Any] = {
        "id": _rule_id(),
        "kind": kind,
        "scope": scope,
        "host": host,
        "selector": selector.strip(),
        "fingerprint": fp,
        "label": label or (f"Blocked {fp.get('tag') or 'element'} on {host}" if host else "Global block"),
        "ad_space": bool(ad_space),
        "created": _now(),
        "hits": 0,
    }
    if ad_space:
        rule["kind"] = "ad_space"
        if not rule["label"].lower().startswith("ad"):
            rule["label"] = f"Ad space — {rule['label']}"
    h = _fingerprint_hash(fp, host)
    for existing in doc.get("rules") or []:
        if existing.get("host") == host and _fingerprint_hash(existing.get("fingerprint") or {}, host) == h:
            return {"ok": True, "duplicate": True, "rule": existing, "doc": doc_summary(doc)}
    doc.setdefault("rules", []).append(rule)
    doc["updated"] = _now()
    doc["stats"] = {"blocked": doc["stats"].get("blocked", 0), "rules": len(doc["rules"])}
    _save(doc)
    return {"ok": True, "rule": rule, "doc": doc_summary(doc)}


def remove_rule(rule_id: str) -> dict[str, Any]:
    doc = ensure_doc()
    before = len(doc.get("rules") or [])
    doc["rules"] = [r for r in doc.get("rules") or [] if r.get("id") != rule_id]
    if len(doc["rules"]) == before:
        return {"ok": False, "error": "not_found", "id": rule_id}
    doc["updated"] = _now()
    doc["stats"]["rules"] = len(doc["rules"])
    _save(doc)
    return {"ok": True, "removed": rule_id, "doc": doc_summary(doc)}


def list_rules(*, host: str = "", url: str = "") -> dict[str, Any]:
    doc = ensure_doc()
    h = (host or _host_key(url)).lower()
    rules = doc.get("rules") or []
    if h:
        rules = [r for r in rules if r.get("scope") == "global" or r.get("host") == h]
    return {"ok": True, "host": h, "rules": rules, "doc": doc_summary(doc)}


def doc_summary(doc: dict[str, Any] | None = None) -> dict[str, Any]:
    doc = doc or ensure_doc()
    return {
        "schema": doc.get("schema"),
        "updated": doc.get("updated"),
        "policy": doc.get("policy"),
        "stats": doc.get("stats"),
        "count": len(doc.get("rules") or []),
    }


def _css_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _selector_from_rule(rule: dict[str, Any]) -> str | None:
    sel = str(rule.get("selector") or "").strip()
    if sel:
        return sel
    fp = rule.get("fingerprint") or {}
    parts: list[str] = []
    tag = str(fp.get("tag") or "*")
    sid = fp.get("stable_id")
    if sid:
        parts.append(f"{tag}#{_css_escape(str(sid))}")
    else:
        stable = fp.get("stable_classes") or []
        if stable:
            parts.append(tag + "".join(f".{_css_escape(c)}" for c in stable[:3]))
        elif fp.get("structural_path"):
            parts.append(str(fp["structural_path"]))
        else:
            return None
    return parts[0] if parts else None


def cosmetic_css(*, host: str = "", url: str = "") -> str:
    doc = ensure_doc()
    h = (host or _host_key(url)).lower()
    lines = [
        "/* Queen page shields — user blocks + ad-space fingerprints */",
        "[data-queen-shielded]{display:none!important;visibility:hidden!important;",
        "height:0!important;max-height:0!important;overflow:hidden!important;",
        "pointer-events:none!important;opacity:0!important;}",
    ]
    for rule in doc.get("rules") or []:
        if rule.get("scope") != "global" and h and rule.get("host") != h:
            continue
        sel = _selector_from_rule(rule)
        if not sel:
            continue
        lines.append(f"{sel}, {sel} iframe, {sel} [data-ad], {sel} [data-ad-slot] {{")
        lines.append("  display:none!important;visibility:hidden!important;")
        lines.append("  height:0!important;max-height:0!important;overflow:hidden!important;")
        lines.append("  pointer-events:none!important;}")
        fp = rule.get("fingerprint") or {}
        w = int(fp.get("width_bucket") or 0)
        ht = int(fp.get("height_bucket") or 0)
        if w > 0 and ht > 0 and rule.get("ad_space"):
            tol = 20
            lines.append(
                f"iframe[width=\"{w}\"][height=\"{ht}\"], "
                f"div[style*=\"width: {w}px\"][style*=\"height: {ht}px\"] {{"
            )
            lines.append("  display:none!important;}")
    for frag in AD_HOST_FRAGMENTS:
        lines.append(f'iframe[src*="{frag}"], a[href*="{frag}"] {{display:none!important;}}')
    return "\n".join(lines) + "\n"


def match_payload(*, url: str = "", host: str = "") -> dict[str, Any]:
    doc = ensure_doc()
    h = (host or _host_key(url)).lower()
    rules = [r for r in doc.get("rules") or [] if r.get("scope") == "global" or r.get("host") == h]
    return {
        "ok": True,
        "host": h,
        "policy": doc.get("policy"),
        "rules": rules,
        "css": cosmetic_css(host=h),
        "ad_hosts": list(AD_HOST_FRAGMENTS),
        "ad_tokens": AD_TOKEN_RE.pattern,
    }


def record_hit(rule_id: str) -> dict[str, Any]:
    doc = ensure_doc()
    for rule in doc.get("rules") or []:
        if rule.get("id") == rule_id:
            rule["hits"] = int(rule.get("hits") or 0) + 1
            rule["last_hit"] = _now()
            doc["stats"]["blocked"] = int(doc["stats"].get("blocked") or 0) + 1
            doc["updated"] = _now()
            _save(doc)
            return {"ok": True, "rule_id": rule_id, "hits": rule["hits"]}
    return {"ok": False, "error": "not_found"}


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")
    if action in ("status", "json", "shields"):
        doc = ensure_doc()
        return {"ok": True, **doc_summary(doc), "rules": doc.get("rules") or []}
    if action in ("list", "rules", "list_rules"):
        return list_rules(host=str(body.get("host") or ""), url=str(body.get("url") or ""))
    if action in ("match", "payload", "for_page"):
        return match_payload(url=str(body.get("url") or ""), host=str(body.get("host") or ""))
    if action in ("css", "cosmetic_css"):
        return {
            "ok": True,
            "css": cosmetic_css(url=str(body.get("url") or ""), host=str(body.get("host") or "")),
        }
    if action in ("add", "block", "block_element", "never_again"):
        return add_rule(
            url=str(body.get("url") or ""),
            host=str(body.get("host") or ""),
            kind=str(body.get("kind") or "element"),
            selector=str(body.get("selector") or ""),
            fingerprint=body.get("fingerprint") or {},
            label=str(body.get("label") or ""),
            ad_space=body.get("ad_space") is True or body.get("kind") == "ad_space",
            scope=str(body.get("scope") or "site"),
        )
    if action in ("block_ad", "block_ad_space", "never_see_ad"):
        return add_rule(
            url=str(body.get("url") or ""),
            host=str(body.get("host") or ""),
            kind="ad_space",
            selector=str(body.get("selector") or ""),
            fingerprint=body.get("fingerprint") or {},
            label=str(body.get("label") or "Ad space — never again"),
            ad_space=True,
            scope=str(body.get("scope") or "site"),
        )
    if action in ("remove", "unblock", "delete_rule"):
        return remove_rule(str(body.get("rule_id") or body.get("id") or ""))
    if action == "hit":
        return record_hit(str(body.get("rule_id") or ""))
    if action in ("set_policy", "policy"):
        doc = ensure_doc()
        pol = dict(doc.get("policy") or {})
        for key in ("auto_proxy_external", "block_random_class_ads", "persist_host_rules"):
            if key in body:
                pol[key] = body[key] is not False if isinstance(body[key], bool) else body[key]
        doc["policy"] = pol
        doc["updated"] = _now()
        _save(doc)
        return {"ok": True, "policy": pol, "doc": doc_summary(doc)}
    return {"ok": False, "error": "unknown_action", "action": action}


def main() -> int:
    import sys
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "json":
        doc = ensure_doc()
        print(json.dumps({"ok": True, **doc}, ensure_ascii=False))
        return 0
    if cmd == "dispatch":
        raw = sys.stdin.read()
        body = json.loads(raw) if raw.strip() else {}
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    if cmd == "css":
        host = sys.argv[2] if len(sys.argv) > 2 else ""
        print(cosmetic_css(host=host))
        return 0
    print(json.dumps(dispatch({"action": cmd}), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())