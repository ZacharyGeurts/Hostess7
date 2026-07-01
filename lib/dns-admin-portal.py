#!/usr/bin/env pythong
"""Hostess 7 DNS Admin Portal — ports 7, 77, 777.

Read-only DNS information for tired engineers. No remote controls.
Standard network equipment room reporting enabled by default when prompted.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
SEED_PATH = INSTALL / "data" / "dns-admin-seed.json"
PORTAL_HTML = INSTALL / "panel" / "assets" / "dns-admin-portal.html"
SESSIONS = STATE / "dns-admin-sessions.json"
SESSION_TTL = int(os.environ.get("NEXUS_DNS_ADMIN_SESSION_TTL", "28800"))

PORTS = [
    int(p.strip())
    for p in os.environ.get("NEXUS_DNS_ADMIN_PORTS", "7,77,777").split(",")
    if p.strip().isdigit()
] or [7, 77, 777]

BLOCKED_PREFIXES = (
    "/api/firewall",
    "/api/attack",
    "/api/nexus/restart",
    "/api/remote",
    "/api/rdp",
    "/api/vnc",
    "/api/ssh",
    "/api/field-toolkit",
    "/api/home-protector/block",
    "/api/pest",
    "/api/paranoia",
    "/api/update/apply",
)

READ_GET = (
    "/",
    "/health",
    "/api/welcome",
    "/api/dns",
    "/api/dns/status",
    "/api/dns/rfc",
    "/api/dns/legal",
    "/api/dns/planetary",
    "/api/dns/roots",
    "/api/equipment-room",
    "/api/field-servers",
    "/api/session",
    "/api/blocked-policy",
)

READ_POST = ("/api/login", "/api/logout", "/api/equipment-room/report", "/api/equipment-room/enable")

_sessions_lock = threading.Lock()
_sessions: dict[str, dict[str, Any]] = {}


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


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


def _seed() -> dict[str, Any]:
    return _load_json(SEED_PATH, {})


def _hostess_admins() -> list[dict[str, Any]]:
    admins = list(_seed().get("admins") or [])
    for rel in (
        "brain/security/dns-admins.json",
        "brain/security/hostess-admins.json",
    ):
        for root in (
            Path(os.environ.get("HOSTESS7_TEAM_FIELD", "/media/default/HOSTESS7_TEAM/fieldstorage")),
            Path(os.environ.get("HOSTESS7_ROOT", str(INSTALL / "Hostess7"))) / "cache" / "fieldstorage",
            STATE / "hostess7-cache" / "fieldstorage",
        ):
            path = root / rel
            if path.is_file():
                doc = _load_json(path, {})
                extra = doc if isinstance(doc, list) else doc.get("admins") or []
                for row in extra:
                    if isinstance(row, dict) and row.get("username"):
                        admins.append(row)
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for a in admins:
        u = str(a.get("username", "")).lower()
        if u and u not in seen:
            seen.add(u)
            out.append(a)
    return out


def _session_secret() -> bytes:
    secret_path = STATE / "dns-admin-secret"
    if secret_path.is_file():
        return secret_path.read_bytes()[:64]
    secret = secrets.token_bytes(32)
    secret_path.write_bytes(secret)
    secret_path.chmod(0o640)
    return secret


def _load_sessions() -> None:
    global _sessions
    raw = _load_json(SESSIONS, {})
    if isinstance(raw, dict):
        _sessions = raw


def _persist_sessions() -> None:
    with _sessions_lock:
        _save_json(SESSIONS, _sessions)


def _prune_sessions() -> None:
    now = time.time()
    with _sessions_lock:
        dead = [k for k, v in _sessions.items() if float(v.get("exp", 0)) < now]
        for k in dead:
            del _sessions[k]


def _make_token(username: str, port: int) -> str:
    tok = secrets.token_urlsafe(24)
    with _sessions_lock:
        _sessions[tok] = {
            "user": username,
            "port": port,
            "exp": time.time() + SESSION_TTL,
            "equipment_room": bool(_seed().get("equipment_room_default_enabled", True)),
            "created": _now(),
        }
    _persist_sessions()
    return tok


def _validate_login(username: str, passkey: str, port: int) -> bool:
    if port not in PORTS:
        return False
    seed = _seed()
    keys = (seed.get("passkeys") or {}).get(str(port)) or []
    if passkey in keys or passkey == str(port):
        pass_ok = True
    else:
        pass_ok = False
    if not pass_ok:
        return False
    user_l = username.strip().lower()
    for admin in _hostess_admins():
        if str(admin.get("username", "")).lower() != user_l:
            continue
        allowed = admin.get("ports") or PORTS
        return port in allowed or not allowed
    return user_l in ("hostess", "engineer", "field", "admin")


def _session_from_cookie(header: str | None) -> dict[str, Any] | None:
    if not header:
        return None
    for part in header.split(";"):
        part = part.strip()
        if part.startswith("nexus-dns-admin="):
            tok = part.split("=", 1)[1].strip()
            with _sessions_lock:
                sess = _sessions.get(tok)
            if sess and float(sess.get("exp", 0)) > time.time():
                return {**sess, "token": tok}
    return None


def _py_json(script: Path, args: list[str]) -> dict[str, Any]:
    if not script.is_file():
        return {"error": "missing", "path": str(script)}
    env = os.environ.copy()
    env["NEXUS_STATE_DIR"] = str(STATE)
    env["NEXUS_INSTALL_ROOT"] = str(INSTALL)
    try:
        proc = subprocess.run(
            [sys.executable, str(script), *args],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            env=env,
        )
        if proc.stdout.strip():
            return json.loads(proc.stdout)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        pass
    return {"error": "exec_failed"}


def _dns_full() -> dict[str, Any]:
    cache = STATE / "field-dns-panel.json"
    if cache.is_file():
        doc = _load_json(cache, {})
        if doc.get("schema") in ("field-dns/v1", "field-dns/v2") or doc.get("rfc_matrix"):
            return doc
    return _py_json(INSTALL / "lib" / "field-dns.py", ["json"])


def _equipment_room(enabled: bool | None = None) -> dict[str, Any]:
    cache = STATE / "equipment-room-panel.json"
    if cache.is_file():
        doc = _load_json(cache, {})
    else:
        doc = _py_json(INSTALL / "lib" / "equipment-room-field.py", ["build"])
    if enabled is not None and "equipment_room_enabled" in doc:
        doc["equipment_room_enabled"] = enabled
    return doc


def _blocked_response(path: str) -> dict[str, Any]:
    seed = _seed()
    for row in seed.get("remote_control_blocked") or []:
        if path.startswith(str(row.get("path_prefix", ""))):
            return {
                "blocked": True,
                "reason": row.get("reason"),
                "policy": "information_only",
                "love": seed.get("welcome", {}).get("love_note"),
            }
    return {
        "blocked": True,
        "reason": "Remote control and mutation forbidden on Hostess 7 DNS admin ports.",
        "policy": "information_only",
        "allowed": "DNS read APIs, equipment room reports, welcome briefing only",
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "NEXUS-DNS-Admin/7.3"

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def _peer_loopback(self) -> bool:
        peer = self.client_address[0] if self.client_address else ""
        return peer in ("127.0.0.1", "::1", "localhost") or str(peer).startswith("127.")

    def _send(self, code: int, body: str, ctype: str = "application/json") -> None:
        if not self._peer_loopback():
            self.send_response(403)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; connect-src 'self' http://127.0.0.1:*; frame-ancestors 'none'; base-uri 'self'",
        )
        self.send_header(
            "Permissions-Policy",
            "camera=(), microphone=(), display-capture=(), clipboard-read=(), geolocation=()",
        )
        self.send_header("X-NEXUS-Policy", "dns-information-only")
        self.send_header("X-Remote-Control", "blocked")
        self.send_header("X-Admin-Shield", "keyboard-hooks-blocked")
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, code: int, payload: Any) -> None:
        self._send(code, json.dumps(payload, ensure_ascii=False), "application/json")

    def _read_body(self) -> dict[str, Any]:
        try:
            n = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            n = 0
        if n <= 0 or n > 65536:
            return {}
        try:
            raw = self.rfile.read(n)
            doc = json.loads(raw.decode("utf-8"))
            return doc if isinstance(doc, dict) else {}
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}

    def _port_hint(self) -> int:
        host = self.headers.get("Host", "")
        m = re.search(r":(\d+)\s*$", host)
        if m:
            return int(m.group(1))
        return int(getattr(self.server, "server_port", 777))

    def _path(self) -> str:
        return urlparse(self.path).path.rstrip("/") or "/"

    def _blocked_path(self, path: str) -> bool:
        for prefix in BLOCKED_PREFIXES:
            if path.startswith(prefix):
                return True
        return False

    def _require_session(self) -> dict[str, Any] | None:
        sess = _session_from_cookie(self.headers.get("Cookie"))
        if sess:
            return sess
        return None

    def do_GET(self) -> None:
        try:
            self._do_get_inner()
        except Exception as exc:
            self._send_json(500, {"error": "handler_fault", "detail": str(exc)[:200]})

    def _do_get_inner(self) -> None:
        _prune_sessions()
        path = self._path()
        port = self._port_hint()

        if self._blocked_path(path):
            self._send_json(403, _blocked_response(path))
            return

        if path == "/health":
            self._send_json(200, {
                "ok": True,
                "service": "Hostess7-DNS-Admin",
                "ports": PORTS,
                "port": port,
                "policy": "information_only",
                "remote_control": "blocked",
            })
            return

        if path in ("/assets/front-hook.js", "/assets/hardware-wire.js", "/assets/smart-wire.js", "/assets/clipboard-wire.js", "/assets/admin-window-shield.js"):
            asset = INSTALL / "panel" / "assets" / path.rsplit("/", 1)[-1]
            if not asset.is_file():
                self._send_json(404, {"error": "asset_missing"})
                return
            ctype = "application/javascript; charset=utf-8"
            self._send(200, asset.read_text(encoding="utf-8"), ctype)
            return

        if path in ("/", "/portal"):
            if not PORTAL_HTML.is_file():
                self._send_json(404, {"error": "portal_html_missing"})
                return
            self._send(200, PORTAL_HTML.read_text(encoding="utf-8"), "text/html; charset=utf-8")
            return

        if path == "/api/welcome":
            seed = _seed()
            self._send_json(200, {
                "schema": "dns-admin-welcome/v1",
                "port": port,
                "mnemonic": (seed.get("port_mnemonic") or {}).get(str(port)),
                "welcome": seed.get("welcome"),
                "admin_ports": seed.get("admin_ports") or PORTS,
                "login_hint": "Hostess 7 admin — username + passkey (try the port number: 7, 77, or 777)",
                "equipment_room_default_enabled": seed.get("equipment_room_default_enabled", True),
            })
            return

        if path == "/api/blocked-policy":
            seed = _seed()
            self._send_json(200, {
                "remote_control_blocked": seed.get("remote_control_blocked"),
                "remote_ports_blocked": seed.get("remote_ports_blocked"),
                "policy": "We never offer remote controls — only information. We relish sharing knowledge.",
            })
            return

        if path == "/api/session":
            sess = self._require_session()
            if not sess:
                self._send_json(401, {"authenticated": False, "port": port})
                return
            self._send_json(200, {
                "authenticated": True,
                "user": sess.get("user"),
                "port": sess.get("port"),
                "equipment_room_enabled": sess.get("equipment_room", True),
                "expires": sess.get("exp"),
            })
            return

        if path.startswith("/api/dns") or path in ("/api/equipment-room", "/api/field-servers"):
            sess = self._require_session()
            if not sess:
                self._send_json(401, {"error": "login_required", "login": "/api/login", "welcome": "/api/welcome"})
                return

        if path == "/api/dns" or path == "/api/dns/full":
            self._send_json(200, _dns_full())
            return
        if path == "/api/dns/status":
            doc = _dns_full()
            self._send_json(200, {
                "running": doc.get("running"),
                "listeners": doc.get("listeners"),
                "stats": doc.get("stats"),
                "resolv": doc.get("resolv"),
                "resolver_policy": doc.get("resolver_policy"),
            })
            return
        if path == "/api/dns/rfc":
            doc = _dns_full()
            self._send_json(200, {"rfc_matrix": doc.get("rfc_matrix"), "rfc_enforced_count": doc.get("planetary", {}).get("rfc_enforced_count")})
            return
        if path == "/api/dns/legal":
            doc = _dns_full()
            self._send_json(200, {"legal_framework": doc.get("legal_framework")})
            return
        if path == "/api/dns/planetary":
            doc = _dns_full()
            self._send_json(200, {"planetary": doc.get("planetary"), "zones": doc.get("zones"), "planetary_security_level": doc.get("planetary_security_level")})
            return
        if path == "/api/dns/roots":
            doc = _dns_full()
            self._send_json(200, {"root_servers": doc.get("root_servers")})
            return
        if path == "/api/equipment-room" or path == "/api/field-servers":
            sess = self._require_session() or {}
            self._send_json(200, _equipment_room(bool(sess.get("equipment_room", True))))
            return

        self._send_json(404, {"error": "not_found", "hint": "DNS information APIs only"})

    def do_POST(self) -> None:
        try:
            self._do_post_inner()
        except Exception as exc:
            self._send_json(500, {"error": "handler_fault", "detail": str(exc)[:200]})

    def _do_post_inner(self) -> None:
        _prune_sessions()
        path = self._path()

        if self._blocked_path(path):
            self._send_json(403, _blocked_response(path))
            return

        if path not in READ_POST:
            self._send_json(403, {
                **_blocked_response(path),
                "message": "POST not allowed — DNS admin portal is read-only except login and equipment room reports.",
            })
            return

        if path == "/api/login":
            body = self._read_body()
            username = str(body.get("username", "")).strip()
            passkey = str(body.get("passkey", "")).strip()
            port = int(body.get("port") or self._port_hint())
            accept_equipment = body.get("accept_equipment_room")
            if not username or not passkey:
                self._send_json(400, {"error": "username_and_passkey_required"})
                return
            if not _validate_login(username, passkey, port):
                self._send_json(401, {
                    "error": "invalid_credentials",
                    "hint": f"Try passkey = port number ({port}) or mnemonic from /api/welcome",
                })
                return
            token = _make_token(username, port)
            if accept_equipment is not False:
                with _sessions_lock:
                    if token in _sessions:
                        _sessions[token]["equipment_room"] = True
                _persist_sessions()
            seed = _seed()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Set-Cookie", f"nexus-dns-admin={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age={SESSION_TTL}")
            self.send_header("X-NEXUS-Policy", "dns-information-only")
            body_out = json.dumps({
                "ok": True,
                "user": username,
                "port": port,
                "mnemonic": (seed.get("port_mnemonic") or {}).get(str(port)),
                "welcome": seed.get("welcome"),
                "equipment_room_enabled": True if accept_equipment is not False else False,
                "remote_control": "never",
            }, ensure_ascii=False).encode("utf-8")
            self.send_header("Content-Length", str(len(body_out)))
            self.end_headers()
            self.wfile.write(body_out)
            return

        if path == "/api/logout":
            sess = _session_from_cookie(self.headers.get("Cookie"))
            if sess and sess.get("token"):
                with _sessions_lock:
                    _sessions.pop(str(sess["token"]), None)
                _persist_sessions()
            self.send_response(200)
            self.send_header("Set-Cookie", "nexus-dns-admin=; Path=/; Max-Age=0")
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
            return

        sess = self._require_session()
        if not sess:
            self._send_json(401, {"error": "login_required"})
            return

        if path == "/api/equipment-room/enable":
            body = self._read_body()
            enabled = body.get("enabled", True) is not False
            tok = str(sess.get("token", ""))
            with _sessions_lock:
                if tok in _sessions:
                    _sessions[tok]["equipment_room"] = enabled
            _persist_sessions()
            self._send_json(200, {"equipment_room_enabled": enabled, "panel": _equipment_room(enabled)})
            return

        if path == "/api/equipment-room/report":
            body = self._read_body()
            if not sess.get("equipment_room", True):
                self._send_json(403, {"error": "equipment_room_not_enabled", "enable": "/api/equipment-room/enable"})
                return
            report = {
                "reporter": sess.get("user"),
                "port": sess.get("port"),
                "checklist": body.get("checklist") or [],
                "legacy_equipment": body.get("legacy_equipment") or [],
                "field_peers": body.get("field_peers") or [],
                "notes": str(body.get("notes", ""))[:4000],
                "room": str(body.get("room", "MDF/IDF"))[:120],
            }
            out = _py_json(INSTALL / "lib" / "equipment-room-field.py", ["report", json.dumps(report)])
            self._send_json(200, {"ok": True, "report": out, "message": "Thank you — report stored locally. No remote actions taken."})
            return

        self._send_json(404, {"error": "not_found"})


def _bind_host() -> str:
    if os.environ.get("NEXUS_DNS_ADMIN_LOOPBACK_ONLY", "1") not in ("0", "false", "no", "off"):
        return "127.0.0.1"
    return "0.0.0.0"


def _serve_port(port: int) -> None:
    host = _bind_host()
    try:
        server = ThreadingHTTPServer((host, port), Handler)
        server.serve_forever()
    except OSError:
        pass


def serve() -> int:
    pid_file = STATE / "dns-admin-portal.pid"
    pid_file.write_text(f"{os.getpid()}\n", encoding="utf-8")
    _load_sessions()
    threads = []
    for port in PORTS:
        t = threading.Thread(target=_serve_port, args=(port,), daemon=True)
        t.start()
        threads.append(t)
    while True:
        time.sleep(3600)


def status() -> dict[str, Any]:
    return {
        "schema": "dns-admin-portal/v1",
        "updated": _now(),
        "ports": PORTS,
        "running": True,
        "policy": "information_only",
        "remote_control": "blocked",
        "sessions": len(_sessions),
    }


def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps(status(), ensure_ascii=False))
        return 0
    cmd = sys.argv[1]
    if cmd == "serve":
        serve()
        return 0
    if cmd == "status":
        _load_sessions()
        print(json.dumps(status(), ensure_ascii=False))
        return 0
    print("usage: dns-admin-portal.py [serve|status]", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())