#!/usr/bin/env pythong
"""Export GitHub brain API snapshots for Pages — never touches sovereign brain."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT.parent
DOCS = ROOT / "docs"
API = DOCS / "api"
sys.path.insert(0, str(ROOT / "src"))

from hostess7.github_brain import ask_mirror, status_mirror  # noqa: E402
from hostess7.h7_io import read_json as h7_read_json  # noqa: E402


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write(name: str, doc: Any) -> Path:
    API.mkdir(parents=True, exist_ok=True)
    out = API / name
    out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return out


def _export_health() -> dict[str, Any]:
    return {
        "ok": True,
        "service": "Hostess7-GitHub-Brain",
        "owner": "ZacharyGeurts",
        "pages": True,
        "lane": "github-mirror",
        "mode": "github-brain-mirror",
        "writes_to_sovereign": False,
    }


def _export_status() -> dict[str, Any]:
    st = status_mirror()
    panel_path = API / "status.json"
    if panel_path.is_file():
        try:
            panel = h7_read_json(panel_path)
            if isinstance(panel, dict) and (
                panel.get("field") is not None or panel.get("mode") == "pages-surfaces"
            ):
                merged = {**panel, "brain_mirror": st, "exported": _ts()}
                return merged
        except Exception:
            pass
    st["exported"] = _ts()
    return st


def _export_brain() -> dict[str, Any]:
    manifest_path = DOCS / "github-brain" / "manifest.json"
    if manifest_path.is_file():
        doc = h7_read_json(manifest_path)
        doc["pages"] = True
        return doc
    return {"ok": True, "schema": "hostess7-github-brain/v1", "lane": "github-mirror", "pages": True}


def _export_status_full() -> dict[str, Any]:
    st = _export_status()
    mirror_path = DOCS / "github-brain" / "mirror.json"
    if mirror_path.is_file():
        st["mirror"] = h7_read_json(mirror_path)
    st["sovereign_note"] = "Loopback ./Hostess7.sh boot uses sovereign brain — not modified by Pages chat."
    return st


def _export_search_index(name: str, static_name: str, q: str) -> dict[str, Any]:
    """Read-only index from published github-brain corpus domains."""
    corpus_path = DOCS / "github-brain" / "corpus.json"
    if not corpus_path.is_file():
        return {"ok": True, "query": q, "hits": [], "lane": "github-mirror"}
    corpus = h7_read_json(corpus_path)
    tokens = [t for t in q.lower().split() if len(t) > 2]
    hits = []
    for c in corpus.get("chunks") or []:
        if c.get("domain") != name and name not in (c.get("tags") or []):
            continue
        hay = f"{c.get('title', '')} {c.get('text', '')}".lower()
        if any(t in hay for t in tokens):
            hits.append({"title": c.get("title"), "source": c.get("source"), "excerpt": c.get("text", "")[:240]})
    return {"ok": True, "query": q, "hits": hits[:24], "lane": "github-mirror", "exported": _ts()}


def _export_ask_seeds() -> dict[str, Any]:
    seeds = (
        "What do you want first?",
        "human UI hub BSP ironclad",
        "what tasks should the assistant do",
        "KILROY field stack boot order",
        "truth floor and neural guardian",
        "hearing and speech for Hostess7",
        "English grammar training",
        "github brain isolation policy",
    )
    answers = []
    for q in seeds:
        res = ask_mirror(q)
        answers.append({"query": q, "text": res.get("text", ""), "ok": res.get("ok"), "lane": "github-mirror"})
    return {"ok": True, "schema": "hostess7-github-ask-seeds/v1", "lane": "github-mirror", "answers": answers, "exported": _ts()}


def _run_install_json(rel: str, args: list[str] | None = None, *, timeout: int = 120) -> dict[str, Any]:
    script = INSTALL / rel
    if not script.is_file():
        return {}
    env = {**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "HOSTESS7_ROOT": str(ROOT)}
    try:
        proc = subprocess.run(
            [sys.executable, str(script), *(args or ["json"])],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(INSTALL),
            env=env,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            doc = json.loads(proc.stdout)
            if isinstance(doc, dict):
                return doc
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        pass
    return {}


def _ammodrive_pages_doc(
    doc: dict[str, Any],
    *,
    api: str,
    legacy_apis: list[str],
    schema_suffix: str,
) -> dict[str, Any]:
    out = dict(doc)
    base_schema = str(out.get("schema") or schema_suffix)
    if base_schema.startswith("field-zachub"):
        out["schema"] = base_schema.replace("field-zachub", "ammodrive", 1)
    out["product"] = out.get("product") or "AmmoDrive"
    out["pages"] = True
    out["lane"] = "github-mirror"
    out["writes_to_sovereign"] = False
    out["sovereign_brain_unhooked"] = True
    out["pages_read_only"] = True
    out["api"] = api
    out["canonical_api"] = api
    out["api_aliases"] = legacy_apis
    out["loopback_upgrade"] = "http://127.0.0.1:9477"
    out["exported"] = _ts()
    return out


def _export_ammodrive() -> list[str]:
    """Publish AmmoDrive static API snapshots — read-only on GitHub Pages."""
    branding_path = INSTALL / "data" / "ammodrive-branding.json"
    branding = h7_read_json(branding_path) if branding_path.is_file() else {}
    pairs: list[tuple[str, str, str, list[str], str]] = (
        (
            "ammodrive-cloud.json",
            "ammodrive-cloud.json",
            "/api/ammodrive-cloud",
            ["/api/field-ammodrive-cloud"],
            "lib/ammodrive-cloud.py",
        ),
        (
            "field-global-servers.json",
            "field-global-servers.json",
            "/api/field-global-servers",
            ["/api/global-servers"],
            "lib/field-global-servers.py",
        ),
        (
            "field-zachub-storage.json",
            "ammodrive-storage.json",
            "/api/ammodrive-storage",
            ["/api/field-zachub-storage", "/api/zachub-storage"],
            "lib/field-zachub-storage.py",
        ),
        (
            "field-zachub-qemu-racks.json",
            "ammodrive-qemu-racks.json",
            "/api/ammodrive-qemu-racks",
            ["/api/field-zachub-qemu-racks", "/api/zachub-qemu-racks"],
            "lib/field-zachub-qemu-racks.py",
        ),
        (
            "field-zachub-fork-guard.json",
            "ammodrive-fork-guard.json",
            "/api/ammodrive-fork-guard",
            ["/api/field-zachub-fork-guard", "/api/zachub-fork-guard"],
            "lib/field-zachub-fork-guard.py",
        ),
    )
    files: list[str] = []
    storage: dict[str, Any] = {}
    racks: dict[str, Any] = {}
    fork: dict[str, Any] = {}
    for src_name, dst_name, api, legacy, script_rel in pairs:
        src_path = API / src_name
        doc: dict[str, Any] = {}
        if src_path.is_file():
            try:
                doc = h7_read_json(src_path)
            except Exception:
                doc = {}
        if not doc:
            doc = _run_install_json(script_rel)
        if not doc:
            continue
        enriched = _ammodrive_pages_doc(doc, api=api, legacy_apis=legacy, schema_suffix=dst_name)
        files.append(_write(dst_name, enriched).name)
        if "storage" in dst_name:
            storage = enriched
        elif "qemu" in dst_name:
            racks = enriched
        elif "fork" in dst_name:
            fork = enriched
    totals = racks.get("storage_totals") if isinstance(racks.get("storage_totals"), dict) else {}
    if not totals:
        obd = racks.get("one_big_drive") if isinstance(racks.get("one_big_drive"), dict) else {}
        if obd:
            totals = {
                "logical_gb": obd.get("logical_gb"),
                "effective_gb_with_redundancy": obd.get("effective_gb_with_redundancy"),
                "rack_count": obd.get("rack_count"),
                "combined_h7_addressable_gb": obd.get("logical_gb"),
                "protocol": obd.get("protocol") or "field-h7s-fs",
            }
    public = {
        "schema": "ammodrive-public/v1",
        "ok": True,
        "product": branding.get("product") or storage.get("product") or "AmmoDrive",
        "legacy_product": branding.get("legacy_product") or "ZacHub",
        "tagline": branding.get("tagline"),
        "motto": branding.get("motto") or storage.get("motto") or racks.get("motto"),
        "pages": True,
        "lane": "github-mirror",
        "canonical_root": "https://zacharygeurts.github.io/Hostess7/",
        "desktop": "https://zacharygeurts.github.io/Hostess7/desktop/",
        "apis": {
            "public": "/api/ammodrive-public",
            "cloud": "/api/ammodrive-cloud",
            "storage": "/api/ammodrive-storage",
            "qemu_racks": "/api/ammodrive-qemu-racks",
            "fork_guard": "/api/ammodrive-fork-guard",
        },
        "the_new_cloud": True,
        "protocol": "h7r/1",
        "api_aliases": branding.get("api_aliases") or [],
        "security": {
            "internet_isolated": bool(racks.get("internet_isolated", True)),
            "outside_internet": False,
            "storage_plane": "sovereign_loopback_only",
            "pages_read_only": True,
            "sovereign_brain_unhooked": True,
            "writes_to_sovereign": False,
            "ironclad_gate": True,
            "loopback_upgrade": "http://127.0.0.1:9477",
            "motto": "Super secure from outside internet — Pages serves read-only mirror; live stack on loopback.",
        },
        "storage_totals": totals,
        "rack_count": len(racks.get("slots") or racks.get("racks_provisioned") or []),
        "owners": branding.get("owners") or storage.get("owners") or ["Grok", "Zac"],
        "exported": _ts(),
    }
    if fork:
        public["fork_guard"] = {
            "ok": fork.get("ok"),
            "pins": len((fork.get("pins") or fork.get("source_pins") or {})),
            "stale_routes": len((fork.get("stale_routes") or {})),
        }
    files.append(_write("ammodrive-public.json", public).name)
    docs_data = DOCS / "data"
    docs_data.mkdir(parents=True, exist_ok=True)
    if branding_path.is_file():
        shutil.copy2(branding_path, docs_data / "ammodrive-branding.json")
    return files


def _export_ammonet_dns() -> list[str]:
    files: list[str] = []
    doc = _run_install_json("lib/ammonet-dns-zones.py", ["panel"], timeout=25)
    if not doc:
        doctrine_path = INSTALL / "data" / "ammonet-dns-zones.json"
        if doctrine_path.is_file():
            try:
                doc = h7_read_json(doctrine_path)
                doc["ok"] = True
                doc["zone_count"] = len(doc.get("zones") or [])
                doc["record_count"] = sum(len(z.get("records") or []) for z in (doc.get("zones") or []))
            except Exception:
                doc = {}
    if doc:
        doc["pages"] = True
        doc["lane"] = "github-mirror"
        doc["sole_dns_authority"] = bool(doc.get("sole_dns_authority", True))
        doc["exported"] = _ts()
        files.append(_write("ammonet-dns-zones.json", doc).name)
    return files


def _export_field_one() -> list[str]:
    files: list[str] = []
    state = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
    pairs = (
        ("field-one-absorb-panel.json", "field-one-absorb.json", "lib/field-one.py", ["absorb"]),
        ("field-one-rollout-panel.json", "field-one-rollout.json", "lib/field-one-rollout.py", ["json"]),
        ("field-sovereign-ipv4-enforce-panel.json", "field-sovereign-ipv4-enforce.json", None, None),
        ("field-rescue-ingress-panel.json", "field-rescue-ingress.json", None, None),
    )
    for src_name, dst_name, script_rel, args in pairs:
        doc: dict[str, Any] = {}
        src = state / src_name
        if src.is_file():
            try:
                doc = h7_read_json(src)
            except Exception:
                doc = {}
        if not doc and script_rel and args:
            doc = _run_install_json(script_rel, args, timeout=120)
        if not doc:
            continue
        doc["pages"] = True
        doc["lane"] = "github-mirror"
        doc["exported"] = _ts()
        files.append(_write(dst_name, doc).name)
    test_doc = _run_install_json("lib/field-one-rollout.py", ["test"], timeout=60)
    if test_doc:
        test_doc["pages"] = True
        test_doc["lane"] = "github-mirror"
        test_doc["exported"] = _ts()
        files.append(_write("field-one-rollout-test.json", test_doc).name)
    one_json = _run_install_json("lib/field-one.py", ["json"], timeout=30)
    if one_json:
        one_json["pages"] = True
        one_json["lane"] = "github-mirror"
        one_json["exported"] = _ts()
        files.append(_write("field-one.json", one_json).name)
    return files


def _export_truth_keepalive() -> list[str]:
    files: list[str] = []
    panel_path = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state")) / "field-truth-keepalive-panel.json"
    if panel_path.is_file():
        try:
            doc = h7_read_json(panel_path)
        except Exception:
            doc = {}
    else:
        doc = _run_install_json("lib/field-truth-keepalive.py", ["json"], timeout=30)
    if doc:
        doc["pages"] = True
        doc["lane"] = "github-mirror"
        doc["exported"] = _ts()
        files.append(_write("field-truth-keepalive.json", doc).name)
    return files


def _export_operator_x() -> None:
    import subprocess

    env = {**os.environ, "HOSTESS7_ROOT": str(ROOT), "NEXUS_INSTALL_ROOT": str(ROOT.parent)}
    for script, args, out_name in (
        ("hostess7-x-comments.py", ["open"], "operator-x-comments.json"),
        ("hostess7-x-straight-shot.py", ["rip"], "hostess7-x-straight-shot.json"),
        ("hostess7-x-sso-fix.py", ["repair"], "hostess7-x-sso-fix.json"),
        ("hostess7-x-profile-fix.py", ["repair"], "hostess7-x-profile-fix.json"),
        ("hostess7-x-producer.py", ["produce"], "hostess7-x-producer.json"),
        ("hostess7-field-status-update.py", ["build"], "hostess7-field-status-update.json"),
        ("hostess7-google-youtube-open.py", ["open"], "operator-google-youtube-open.json"),
        ("hostess7-google-youtube-open.py", ["open"], "operator-youtube-comments.json"),
        ("hostess7-google-youtube-open.py", ["open"], "operator-google-open.json"),
        ("hostess7-censorship-exposure.py", ["expose"], "operator-censorship-exposure.json"),
        ("hostess7-censorship-clear-worldwide.py", ["clear"], "hostess7-censorship-clear-worldwide.json"),
    ):
        py = ROOT.parent / "lib" / script
        if not py.is_file():
            continue
        proc = subprocess.run(
            [sys.executable, str(py), *args],
            capture_output=True,
            text=True,
            timeout=60,
            env=env,
            cwd=str(ROOT.parent),
        )
        if proc.returncode == 0 and proc.stdout.strip():
            try:
                doc = json.loads(proc.stdout)
                _write(out_name, doc)
            except json.JSONDecodeError:
                pass


def export_all(*, full: bool = True) -> dict[str, Any]:
    os.environ.setdefault("HOSTESS7_ROOT", str(ROOT))
    _export_operator_x()
    files: list[str] = []
    files.append(_write("health.json", _export_health()).name)
    files.append(_write("status.json", _export_status()).name)
    files.append(_write("brain.json", _export_brain()).name)
    files.append(_write("status-full.json", _export_status_full()).name)
    if full:
        files.append(_write("hearing-index.json", _export_search_index("hearing", "hearing", "hearing listen speak")).name)
        files.append(_write("world-index.json", _export_search_index("world", "world", "bible law nature")).name)
        files.append(_write("library-index.json", _export_search_index("library", "library", "children algebra")).name)
        files.append(_write("videogames-index.json", _export_search_index("videogames", "videogames", "mario zelda")).name)
        files.append(_write("ask-seeds.json", _export_ask_seeds()).name)
    files.extend(_export_ammodrive())
    files.extend(_export_ammonet_dns())
    files.extend(_export_field_one())
    files.extend(_export_truth_keepalive())
    total = sum((API / f).stat().st_size for f in files if (API / f).is_file())
    return {"ok": True, "lane": "github-mirror", "api_dir": str(API), "files": files, "bytes": total, "exported": _ts()}


def main() -> int:
    full = "--lite" not in sys.argv
    doc = export_all(full=full)
    print(json.dumps(doc, indent=2))
    print(f"METRIC pages_api_export={len(doc.get('files', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())