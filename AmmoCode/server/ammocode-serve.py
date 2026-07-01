#!/usr/bin/env python3
"""AmmoCode static server + g16 universal compiler API — 2027 hardened."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ammocode_runtime import bundle_root, is_frozen, settings_dir  # noqa: E402
from ddos_guard import GUARD  # noqa: E402

ROOT = bundle_root()
GROK16 = Path(os.environ.get("GROK16_ROOT", ROOT.parent / "Grok16"))
PORT = int(os.environ.get("AMMOCODE_PORT", "9555"))

_collab_mod: Any | None = None
_znetwork_mod: Any | None = None
_network_mod: Any | None = None
_security_mod: Any | None = None
_field_mod: Any | None = None
_settings_mod: Any | None = None
_vault_mod: Any | None = None
_VERSION_CACHE: dict[str, Any] | None = None


def _load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _version_info() -> dict[str, Any]:
    global _VERSION_CACHE
    if _VERSION_CACHE is not None:
        return _VERSION_CACHE
    doc = _load_json(ROOT / "data" / "ammocode-version.json", {})
    _VERSION_CACHE = {
        "upload_version": doc.get("upload_version", "4.9.0"),
        "distro_version": doc.get("distro_version", "5.0.0"),
        "pkgversion": doc.get("pkgversion", "Grok16-5.0.0"),
        "g16_version": doc.get("g16_version", "16.2.0"),
        "codename": doc.get("codename", "2027"),
        "github_tag": (doc.get("github") or {}).get("tag", "v4.9.0"),
    }
    return _VERSION_CACHE


def _load_server_module(attr: str, mod_name: str, filename: str) -> Any | None:
    cache = globals()[attr]
    if cache is not None:
        return cache if cache is not False else None
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(mod_name, ROOT / "server" / filename)
        if spec and spec.loader:
            m = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = m
            spec.loader.exec_module(m)
            globals()[attr] = m
            return m
    except Exception as exc:
        sys.stderr.write(f"{mod_name} load failed: {exc}\n")
    globals()[attr] = False
    return None


def _network() -> Any | None:
    return _load_server_module("_network_mod", "ammocode_network", "ammocode-network.py")


def _znetwork() -> Any | None:
    return _load_server_module("_znetwork_mod", "ammocode_znetwork", "ammocode-znetwork.py")


def _security_mgr() -> Any | None:
    return _load_server_module("_security_mod", "ammocode_security_manage", "ammocode-security-manage.py")


def _field_control() -> Any | None:
    return _load_server_module("_field_mod", "ammocode_field_control", "ammocode-field-control.py")


def _settings() -> Any | None:
    return _load_server_module("_settings_mod", "ammocode_settings", "ammocode-settings.py")


def _memory_vault() -> Any | None:
    return _load_server_module("_vault_mod", "ammocode_memory_vault", "ammocode-memory-vault.py")


def _start_znetwork_hook() -> None:
    if os.environ.get("AMMOCODE_NO_ZNETWORK") == "1":
        return
    fc = _field_control()
    if fc and hasattr(fc, "is_defielded") and fc.is_defielded():
        sys.stderr.write("AmmoCode: defield marker — ZNetwork hook skipped\n")
        return
    mod = _znetwork()
    if not mod or not hasattr(mod, "hook_on_boot"):
        return

    def run() -> None:
        try:
            mod.hook_on_boot()
        except Exception as exc:
            sys.stderr.write(f"znetwork hook thread: {exc}\n")

    threading.Thread(target=run, name="ammocode-znetwork-hook", daemon=True).start()


def _collab() -> Any | None:
    global _collab_mod
    if _collab_mod is not None:
        return _collab_mod
    try:
        import ammocode_collab as m  # type: ignore
        _collab_mod = m
    except ImportError:
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "ammocode_collab", ROOT / "server" / "ammocode-collab.py")
            if spec and spec.loader:
                m = importlib.util.module_from_spec(spec)
                sys.modules[spec.name] = m
                spec.loader.exec_module(m)
                _collab_mod = m
        except Exception as exc:
            sys.stderr.write(f"collab module load failed: {exc}\n")
            _collab_mod = False
    return _collab_mod if _collab_mod is not False else None


def _start_collab_thread() -> None:
    if os.environ.get("AMMOCODE_NO_COLLAB") == "1":
        return
    mod = _collab()
    if not mod or not hasattr(mod, "main_async"):
        return

    def run() -> None:
        import asyncio
        try:
            asyncio.run(mod.main_async())
        except Exception as exc:
            sys.stderr.write(f"collab hub stopped: {exc}\n")

    t = threading.Thread(target=run, name="ammocode-collab", daemon=True)
    t.start()


def _import_mod(name: str, path: Path) -> Any | None:
    if not path.is_file():
        return None
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _universal() -> Any | None:
    return _import_mod("g16_universal", GROK16 / "lib" / "g16-universal-compiler.py")


def _security() -> Any | None:
    return _import_mod("g16_security", GROK16 / "lib" / "g16-code-security.py")


def _combinatorics() -> Any | None:
    return _import_mod("field_combinatorics", GROK16 / "lib" / "field_combinatorics.py")


def _client_ip(handler: SimpleHTTPRequestHandler) -> str:
    fwd = handler.headers.get("X-Forwarded-For", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return handler.address_string().split(":")[0]


def _json(handler: SimpleHTTPRequestHandler, code: int, doc: dict[str, Any]) -> None:
    body = json.dumps(doc, ensure_ascii=False).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _field_posture(surface: str = "") -> dict[str, Any]:
    fc = _field_control()
    if fc and hasattr(fc, "ammocode_posture"):
        return fc.ammocode_posture(str(surface or "plain"))
    doc = _load_json(ROOT / "data" / "ammocode-field-doctrine.json")
    pol = doc.get("policy") or {}
    surf = str(surface or "plain").lower()
    resting = surf in set((doc.get("surfaces") or {}).get("field") or [])
    if resting and pol.get("defield_if_resting_on_field", True):
        return {"posture": "defield", "field": False, "no_subfields": True, "resting_on_field": True}
    return {"posture": "field", "field": True, "no_subfields": True, "resting_on_field": False}


def _discern(path: str, content: str = "", mime: str = "") -> str:
    uni = _universal()
    if uni and hasattr(uni, "discern"):
        return str(uni.discern(path, mime=mime, content=content))
    g16 = GROK16 / "bin" / "g16"
    if g16.is_file() and path:
        try:
            proc = subprocess.run([str(g16), "--g16-discern", path], capture_output=True, text=True, timeout=8)
            if proc.returncode == 0 and proc.stdout.strip():
                return proc.stdout.strip()
        except (OSError, subprocess.TimeoutExpired):
            pass
    doc = _load_json(ROOT / "data" / "languages.json")
    ext = Path(path).suffix.lower()
    exts = {**(doc.get("extensions") or {})}
    inet = ROOT / "data" / "internet-filetypes.json"
    if inet.is_file():
        exts.update(_load_json(inet).get("extensions") or {})
    return str(exts.get(ext, "plaintext"))


def _harden_rewrite(content: str, lang: str) -> dict[str, Any]:
    doc = _load_json(ROOT / "data" / "ammocode-2027-doctrine.json")
    rules = (doc.get("rewrite") or {}).get("harden_rules") or []
    comb = _load_json(ROOT / "data" / "combinatorics-rewrite-patterns.json")
    patterns = list(comb.get("patterns") or []) + [
        {**r, "pattern": r.get("pattern", ""), "langs": r.get("langs", ["*"])}
        for r in rules
    ]
    out = content
    applied: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    blocked = False
    for row in patterns:
        pat = str(row.get("pattern") or "")
        if not pat:
            continue
        langs = row.get("langs")
        if langs and lang and lang not in langs and "*" not in langs:
            continue
        try:
            rx = re.compile(pat, re.IGNORECASE | re.MULTILINE)
        except re.error:
            continue
        if row.get("action") == "block" or row.get("block"):
            for m in rx.finditer(out):
                findings.append({
                    "id": row.get("id"),
                    "line": out[:m.start()].count("\n") + 1,
                    "message": row.get("message", "blocked pattern"),
                    "use_instead": row.get("use_instead"),
                    "severity": row.get("severity", "bad"),
                })
                if row.get("severity") == "critical" or row.get("block"):
                    blocked = True
        rewrite = row.get("rewrite")
        if rewrite and not blocked:
            next_out = rx.sub(str(rewrite), out)
            if next_out != out:
                applied.append({"id": row.get("id"), "use_instead": row.get("use_instead")})
                out = next_out
    return {
        "ok": not blocked,
        "changed": out != content,
        "content": out,
        "applied": applied,
        "findings": findings,
        "blocked": blocked,
        "passes": (doc.get("rewrite") or {}).get("passes", ["registry", "combinatorics", "harden"]),
    }


def _combinatorics_run(profile: str = "belt_2_0") -> dict[str, Any]:
    comb = _combinatorics()
    if comb:
        if hasattr(comb, "fast_cycle"):
            try:
                return {"ok": True, "combinatorics": comb.fast_cycle(profile=profile)}
            except Exception as exc:
                return {"ok": False, "error": str(exc)}
        if hasattr(comb, "combinatoric_tree"):
            try:
                tree = comb.combinatoric_tree()
                return {"ok": True, "combinatorics": {"tree": tree}}
            except Exception as exc:
                return {"ok": False, "error": str(exc)}
    doc = _load_json(ROOT / "data" / "combinatorics-rewrite-patterns.json")
    return {
        "ok": True,
        "combinatorics": {
            "background": True,
            "operator_combinatorics": False,
            "facets": doc.get("facets", []),
            "tree": doc.get("tree", {}),
            "message": "AmmoCode 2027 — combinatorics runs in background",
        },
    }


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_OPTIONS(self) -> None:
        if self.path.rstrip("/") == "/api/ammocode":
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if self.path.rstrip("/") != "/api/ammocode":
            self.send_error(404)
            return
        ip = _client_ip(self)
        try:
            n = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            n = 0
        guard_chk = GUARD.check_request(ip, n)
        if not guard_chk.get("ok"):
            code = 429 if guard_chk.get("error") == "rate_limited" else 403
            _json(self, code, {"ok": False, **guard_chk})
            return
        try:
            body = json.loads(self.rfile.read(n).decode("utf-8") or "{}")
        except (ValueError, json.JSONDecodeError):
            _json(self, 400, {"ok": False, "error": "invalid_json"})
            return
        action = str(body.get("action") or "").strip().lower()
        content = str(body.get("content") or "")
        lang = str(body.get("language") or body.get("lang") or "")
        path = str(body.get("path") or "")
        profile = str(body.get("profile") or "belt_2_0")

        if action == "ping":
            uni = _universal()
            collab_port = int(os.environ.get("AMMOCODE_COLLAB_PORT", "9556"))
            zn = _znetwork()
            zst = zn.status() if zn and hasattr(zn, "status") else {"ok": False}
            ver = _version_info()
            fc = _field_control()
            fpos = fc.ammocode_posture() if fc and hasattr(fc, "ammocode_posture") else _field_posture()
            _json(self, 200, {
                "ok": True, "pong": True,
                "ammocode": True,
                **ver,
                "version": ver["upload_version"],
                "ammocode_field": fpos,
                "defield_active": bool(fc and hasattr(fc, "is_defielded") and fc.is_defielded()),
                "compiler_gui_2027": True,
                "grok16": (GROK16 / "bin" / "g16").is_file(),
                "universal": bool(uni),
                "browser_tab": True,
                "invite_only": True,
                "collab_ws": f"ws://127.0.0.1:{collab_port}",
                "ddos_guard": GUARD.status(),
                "znetwork": zst.get("znetwork") if zst.get("ok") else zst,
                "shield": zst.get("shield") if zst.get("ok") else None,
                "frozen": is_frozen(),
                "replacement_only": True,
                "distribution": _load_json(ROOT / "data" / "ammocode-distribution-doctrine.json", {}),
                "memory_vault": (_memory_vault().vault_status() if _memory_vault() and hasattr(_memory_vault(), "vault_status") else {"ok": False}),
            })
            return

        if action in ("settings_load", "settings_get"):
            st = _settings()
            if st and hasattr(st, "load_settings"):
                imp = body.get("import_local") if isinstance(body.get("import_local"), dict) else None
                _json(self, 200, st.load_settings(import_local=imp))
                return
            _json(self, 503, {"ok": False, "error": "settings_unavailable"})
            return

        if action in ("settings_save", "settings_patch"):
            st = _settings()
            if st and hasattr(st, "save_settings"):
                patch = body.get("patch") if isinstance(body.get("patch"), dict) else body.get("settings") or {}
                _json(self, 200, st.save_settings(patch))
                return
            _json(self, 503, {"ok": False, "error": "settings_unavailable"})
            return

        if action in ("settings_status", "distribution_status"):
            st = _settings()
            if st and hasattr(st, "settings_status"):
                _json(self, 200, st.settings_status())
                return
            _json(self, 503, {"ok": False, "error": "settings_unavailable"})
            return

        if action in ("znetwork_status", "znetwork", "shield_status"):
            zn = _znetwork()
            if zn and hasattr(zn, "status"):
                force = body.get("force") in (True, 1, "1")
                _json(self, 200, zn.status(force=force))
                return
            _json(self, 200, {
                "ok": True,
                "znetwork": {"running": False, "error": "bridge_unavailable"},
                "shield": _load_json(ROOT / "data" / "ammocode-shield-doctrine.json"),
            })
            return

        if action in ("znetwork_hook", "znetwork_attach", "shield_hook"):
            zn = _znetwork()
            if zn and hasattr(zn, "hook_ammocode"):
                out = zn.hook_ammocode()
                zn.invalidate_cache()
                _json(self, 200, out)
                return
            _json(self, 503, {"ok": False, "error": "znetwork_unavailable"})
            return

        if action in ("shield_doctrine",):
            _json(self, 200, {"ok": True, "doctrine": _load_json(ROOT / "data" / "ammocode-shield-doctrine.json")})
            return

        if action == "network_beacon":
            net = _network()
            if net and hasattr(net, "beacon"):
                _json(self, 200, net.beacon(body))
                return
            _json(self, 200, {"ok": True, "ammocode": True, "service": "ammocode"})
            return

        if action in ("network_discover", "discover_hosts"):
            net = _network()
            if net and hasattr(net, "discover"):
                force = body.get("force") in (True, 1, "1")
                _json(self, 200, net.discover(ip, force=force))
                return
            _json(self, 503, {"ok": False, "error": "network_unavailable"})
            return

        if action in ("network_status", "network"):
            net = _network()
            if net and hasattr(net, "network_status"):
                _json(self, 200, net.network_status())
                return
            _json(self, 503, {"ok": False, "error": "network_unavailable"})
            return

        if action in ("host_evaluate", "evaluate_host"):
            net = _network()
            if net and hasattr(net, "evaluate_host"):
                force = body.get("force") in (True, 1, "1")
                _json(self, 200, net.evaluate_host(force=force))
                return
            _json(self, 503, {"ok": False, "error": "network_unavailable"})
            return

        if action in ("rate_host", "threat_rate"):
            net = _network()
            host = str(body.get("host") or body.get("ip") or "")
            if net and hasattr(net, "rate_host") and host:
                _json(self, 200, {"ok": True, "threat": net.rate_host(host)})
                return
            _json(self, 400, {"ok": False, "error": "host_required"})
            return

        if action in ("network_friend_add", "friend_add"):
            net = _network()
            if net:
                _json(self, 200, net.list_manage("add", str(body.get("entry") or ""), "friends"))
                return
            _json(self, 503, {"ok": False, "error": "network_unavailable"})
            return

        if action in ("network_friend_remove", "friend_remove"):
            net = _network()
            if net:
                _json(self, 200, net.list_manage("remove", str(body.get("entry") or ""), "friends"))
                return
            _json(self, 503, {"ok": False, "error": "network_unavailable"})
            return

        if action in ("network_block_add", "block_add"):
            net = _network()
            if net:
                _json(self, 200, net.list_manage("add", str(body.get("entry") or ""), "blocks"))
                return
            _json(self, 503, {"ok": False, "error": "network_unavailable"})
            return

        if action in ("network_block_remove", "block_remove"):
            net = _network()
            if net:
                _json(self, 200, net.list_manage("remove", str(body.get("entry") or ""), "blocks"))
                return
            _json(self, 503, {"ok": False, "error": "network_unavailable"})
            return

        if action == "tunnel_register":
            net = _network()
            if net:
                _json(self, 200, net.tunnel_register(str(body.get("tunnel_id") or "")))
                return
            _json(self, 503, {"ok": False, "error": "network_unavailable"})
            return

        if action == "tunnel_poll":
            net = _network()
            if net:
                _json(self, 200, net.tunnel_poll(
                    str(body.get("tunnel_id") or ""),
                    int(body.get("timeout_ms") or 2000),
                ))
                return
            _json(self, 503, {"ok": False, "error": "network_unavailable"})
            return

        if action == "tunnel_send":
            net = _network()
            if net:
                _json(self, 200, net.tunnel_send(
                    str(body.get("from_id") or body.get("from") or ""),
                    str(body.get("to_id") or body.get("to") or ""),
                    body.get("payload"),
                ))
                return
            _json(self, 503, {"ok": False, "error": "network_unavailable"})
            return

        if action == "tunnel_deliver":
            net = _network()
            if net and hasattr(net, "tunnel_deliver"):
                _json(self, 200, net.tunnel_deliver(
                    str(body.get("from_id") or body.get("from") or ""),
                    str(body.get("tunnel_id") or body.get("to_id") or ""),
                    body.get("payload"),
                ))
                return
            _json(self, 503, {"ok": False, "error": "network_unavailable"})
            return

        if action == "tunnel_connect":
            net = _network()
            if net:
                _json(self, 200, net.tunnel_connect(
                    str(body.get("local_id") or ""),
                    str(body.get("remote_host") or body.get("host") or ""),
                    int(body.get("remote_port") or body.get("port") or 0),
                ))
                return
            _json(self, 503, {"ok": False, "error": "network_unavailable"})
            return

        if action in ("ddos_status", "guard_status"):
            _json(self, 200, GUARD.status())
            return

        if action in ("collab_invite", "create_invite"):
            mod = _collab()
            if mod and hasattr(mod, "create_invite_api"):
                out = mod.create_invite_api(
                    friend_ips=body.get("friend_ips") or [],
                    host_ip=ip,
                )
                _json(self, 200, out)
                return
            _json(self, 503, {"ok": False, "error": "collab_unavailable"})
            return

        if action in ("collab_doctrine", "collab_cursors"):
            if action == "collab_cursors":
                _json(self, 200, {"ok": True, **_load_json(ROOT / "data" / "collab-cursors.json")})
                return
            doc = _load_json(ROOT / "data" / "ammocode-2027-doctrine.json")
            _json(self, 200, {"ok": True, "doctrine": doc})
            return

        if action in ("combinatorics", "combinatorics_run", "comb_cycle"):
            _json(self, 200, _combinatorics_run(profile))
            return

        if action == "discern":
            if not lang and path:
                lang = _discern(path, content, str(body.get("mime") or ""))
            _json(self, 200, {"ok": True, "language": lang or _discern(path, content)})
            return

        if action in ("field_posture", "field"):
            pos = _field_posture(str(body.get("surface") or body.get("host") or "plain"))
            _json(self, 200, {"ok": True, "ammocode_field": pos})
            return

        if action in ("defield", "defield_sg", "sg_defield"):
            fc = _field_control()
            if fc and hasattr(fc, "defield_sg"):
                _json(self, 200, fc.defield_sg(
                    reason=str(body.get("reason") or "api_request"),
                    force=bool(body.get("force")),
                ))
                return
            _json(self, 503, {"ok": False, "error": "field_control_unavailable"})
            return

        if action in ("sg_field_status", "field_status"):
            fc = _field_control()
            if fc and hasattr(fc, "sg_field_status"):
                _json(self, 200, fc.sg_field_status())
                return
            _json(self, 503, {"ok": False, "error": "field_control_unavailable"})
            return

        if action == "security_status":
            sm = _security_mgr()
            if sm and hasattr(sm, "security_status"):
                st = sm.security_status()
                fc = _field_control()
                if fc and hasattr(fc, "sg_field_status"):
                    st["sg_field"] = fc.sg_field_status()
                _json(self, 200, st)
                return
            _json(self, 503, {"ok": False, "error": "security_manage_unavailable"})
            return

        if action in ("security_pin_add", "pin_add"):
            sm = _security_mgr()
            if sm and hasattr(sm, "pin_set"):
                _json(self, 200, sm.pin_set(
                    str(body.get("host") or ""),
                    str(body.get("fingerprint") or ""),
                    label=str(body.get("label") or ""),
                ))
                return
            _json(self, 503, {"ok": False, "error": "security_manage_unavailable"})
            return

        if action in ("security_pin_remove", "pin_remove"):
            sm = _security_mgr()
            if sm and hasattr(sm, "pin_remove"):
                _json(self, 200, sm.pin_remove(str(body.get("host") or "")))
                return
            _json(self, 503, {"ok": False, "error": "security_manage_unavailable"})
            return

        if action in ("verify_beacon", "mitm_check"):
            sm = _security_mgr()
            net = _network()
            host = str(body.get("host") or "")
            beacon = body.get("beacon")
            if not beacon and net and host:
                beacon = net._probe_beacon(host, int(body.get("port") or PORT), 2.0)  # noqa: SLF001
            if sm and hasattr(sm, "verify_beacon"):
                _json(self, 200, sm.verify_beacon(host, beacon or {}))
                return
            _json(self, 503, {"ok": False, "error": "security_manage_unavailable"})
            return

        if action in ("security_scan", "scan", "security"):
            sec = _security()
            base: dict[str, Any] = {"findings": [], "blocked": False}
            if sec and hasattr(sec, "scan"):
                base = sec.scan(content, lang=lang or _discern(path, content), path=path)
            hard = _harden_rewrite(content, lang or _discern(path, content))
            merged_findings = list(base.get("findings") or []) + list(hard.get("findings") or [])
            blocked = bool(base.get("blocked")) or bool(hard.get("blocked"))
            _json(self, 200, {
                "ok": not blocked,
                "scan": {
                    **base,
                    "findings": merged_findings,
                    "finding_count": len(merged_findings),
                    "blocked": blocked,
                    "hardened": True,
                    "combinatorics_patterns": len(hard.get("findings") or []),
                },
                "transparent": True,
            })
            return

        if action in ("insta_rewrite", "rewrite", "harden_rewrite"):
            sec = _security()
            out_content = content
            applied: list[Any] = []
            if sec and hasattr(sec, "insta_rewrite"):
                sec_out = sec.insta_rewrite(content, lang=lang or _discern(path, content))
                if isinstance(sec_out, dict):
                    out_content = sec_out.get("content", out_content)
                    applied.extend(sec_out.get("applied") or [])
            hard = _harden_rewrite(out_content, lang or _discern(path, content))
            if hard.get("blocked"):
                _json(self, 200, {
                    "ok": False,
                    "rewrite": hard,
                    "blocked": True,
                    "message": "Harden rewrite blocked unsafe patterns",
                })
                return
            final = hard.get("content", out_content)
            applied.extend(hard.get("applied") or [])
            _json(self, 200, {
                "ok": True,
                "rewrite": {
                    "changed": final != content,
                    "content": final,
                    "applied": applied,
                    "passes": hard.get("passes"),
                    "hardened": True,
                },
            })
            return

        if action in ("g16_check", "check"):
            uni = _universal()
            if uni and hasattr(uni, "check"):
                out = uni.check(content, lang=lang or _discern(path, content), path=path, profile=profile)
                _json(self, 200, out)
                return
            _json(self, 200, {
                "ok": False,
                "stub": True,
                "error": "compiler_unavailable",
                "message": "g16 universal compiler not loaded — install Grok16 5.0",
                "language": lang,
            })
            return

        if action in ("g16_build", "compile", "build"):
            uni = _universal()
            if uni and hasattr(uni, "compile_source"):
                out = uni.compile_source(content, lang=lang or _discern(path, content), path=path, profile=profile)
                _json(self, 200, out)
                return
            _json(self, 200, {"ok": False, "error": "compiler_unavailable"})
            return

        if action == "compiler_status":
            uni = _universal()
            if uni and hasattr(uni, "status"):
                _json(self, 200, {"ok": True, **uni.status(), "ammocode_2027": True})
                return
            _json(self, 200, {"ok": True, "g16": (GROK16 / "bin" / "g16").is_file(), "ammocode_2027": True})
            return

        if action == "write":
            _json(self, 200, {"ok": True, "message": "write — local editor only in browser tab mode", "language": lang})
            return

        if action.startswith("vault_") or action.startswith("memory_"):
            vault = _memory_vault()
            if vault and hasattr(vault, "handle_api"):
                _json(self, 200, vault.handle_api(action, body))
                return
            _json(self, 200, {"ok": False, "error": "memory_vault_unavailable"})
            return

        _json(self, 400, {"ok": False, "error": "unknown_action", "actions": [
            "ping", "discern", "security_scan", "insta_rewrite", "harden_rewrite",
            "g16_check", "g16_build", "field_posture", "defield_sg", "sg_field_status",
            "security_status", "verify_beacon", "compiler_status", "write",
            "combinatorics", "collab_invite", "collab_cursors", "collab_doctrine", "ddos_status",
            "znetwork_status", "znetwork_hook", "shield_doctrine",
            "network_beacon", "network_discover", "network_status", "host_evaluate",
            "tunnel_register", "tunnel_poll", "tunnel_send", "tunnel_deliver", "tunnel_connect",
            "network_friend_add", "network_block_add",
            "settings_load", "settings_save", "settings_status",
            "vault_status", "vault_encode", "vault_decode", "vault_store", "vault_fetch", "vault_release", "vault_scrub",
        ]})

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


def main() -> int:
    os.chdir(ROOT)
    host = os.environ.get("AMMOCODE_HOST", "127.0.0.1")
    fc = _field_control()
    if fc and hasattr(fc, "auto_defield_if_fielded"):
        try:
            out = fc.auto_defield_if_fielded()
            if out.get("defielded"):
                why = out.get("receipt", {}).get("reason", "")
                was_ac = out.get("receipt", {}).get("ammocode_was_fielded")
                sys.stderr.write(
                    f"AmmoCode: auto-defielded"
                    f"{' (AmmoCode was fielded)' if was_ac else ''}"
                    f" — {why}\n",
                )
        except Exception as exc:
            sys.stderr.write(f"auto-defield: {exc}\n")
    st = _settings()
    if st and hasattr(st, "load_settings"):
        try:
            mig = st.load_settings()
            if mig.get("migrated"):
                sys.stderr.write(
                    f"AmmoCode: settings migrated → schema {mig.get('schema_version')} "
                    f"({mig.get('path')})\n",
                )
        except Exception as exc:
            sys.stderr.write(f"settings migrate: {exc}\n")
    _start_collab_thread()
    _start_znetwork_hook()
    srv = ThreadingHTTPServer((host, PORT), Handler)
    collab_port = os.environ.get("AMMOCODE_COLLAB_PORT", "9556")
    ver = _version_info()
    mode = "secured executable" if is_frozen() else "dev tree"
    print(f"AmmoCode {ver['codename']} — upload {ver['upload_version']} · distro {ver['distro_version']} ({mode})", flush=True)
    if st and hasattr(st, "settings_path"):
        print(f"  settings {st.settings_path()} (signed, replace-exe-only)", flush=True)
    else:
        print(f"  settings {settings_dir()} (signed)", flush=True)
    print(f"  gui  http://{host}:{PORT}/", flush=True)
    print(f"  tab  http://{host}:{PORT}/tab.html", flush=True)
    print(f"  api  http://{host}:{PORT}/api/ammocode", flush=True)
    print(f"  collab ws://{host}:{collab_port} (invite-only)", flush=True)
    print(f"  znet NewLatest ZNetwork bridge (attach-if-running)", flush=True)
    srv.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())