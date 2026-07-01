#!/usr/bin/env python3
"""AmmoCode Stack — lean Grok16 editor server (gut 2027 bloat)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import urllib.parse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SG = Path(os.environ.get("SG_ROOT", ROOT.parent))
ND = ROOT / "server" / "ammocode-nondestructive.py"


def _resolve_nexus() -> Path:
    env = Path(os.environ.get("NEXUS_INSTALL_ROOT", ""))
    for candidate in (env, SG / "AmmoOS", SG / "NewLatest", ROOT.parent / "AmmoOS"):
        if candidate.is_dir() and (candidate / "lib" / "threat-panel-http.py").is_file():
            return candidate
    return env if env.is_dir() else SG / "AmmoOS"


NEXUS = _resolve_nexus()
_SG_PATHS_LIB = Path(__file__).resolve().parents[2] / "lib"
if str(_SG_PATHS_LIB) not in sys.path:
    sys.path.insert(0, str(_SG_PATHS_LIB))
from sg_paths import grok16_root

GROK16 = grok16_root()
PORT = int(os.environ.get("AMMOCODE_PORT", "9555"))
FILETYPES = NEXUS / "lib" / "field-programming-filetypes.py"
PROFILE = os.environ.get("G16_BENCH_PROFILE", "belt_2_0")

_uni: Any | None = None
_ft: Any | None = None
_nd: Any | None = None
_ic_api: Any | None = None


def _import_py(path: Path, name: str) -> Any | None:
    if not path.is_file():
        return None
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def universal() -> Any | None:
    global _uni
    if _uni is None:
        _uni = _import_py(GROK16 / "lib" / "g16-universal-compiler.py", "g16_uni")
    return _uni


def filetypes() -> Any | None:
    global _ft
    if _ft is None:
        _ft = _import_py(FILETYPES, "field_ft")
    return _ft


def nondestructive() -> Any | None:
    global _nd
    if _nd is None:
        _nd = _import_py(ND, "ammocode_nd")
    return _nd


def ironclad_api() -> Any | None:
    global _ic_api
    if _ic_api is None:
        for cand in (
            NEXUS / "lib" / "ironclad-secure-api.py",
            SG / "NewLatest" / "lib" / "ironclad-secure-api.py",
        ):
            _ic_api = _import_py(cand, "ironclad_secure_api")
            if _ic_api:
                break
    return _ic_api


def _json(handler: SimpleHTTPRequestHandler, code: int, doc: dict) -> None:
    body = json.dumps(doc, ensure_ascii=False).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _safe_read(path: str) -> dict[str, Any]:
    nd = nondestructive()
    if nd and hasattr(nd, "assert_read"):
        blocked = nd.assert_read(path)
        if blocked:
            return blocked
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        return {"ok": False, "error": "not_found"}
    ft = filetypes()
    if ft and hasattr(ft, "read_text_file"):
        return ft.read_text_file(str(p))
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return {"ok": False, "error": str(exc)}
    lang = ft.discern(str(p)) if ft else "plaintext"
    return {"ok": True, "path": str(p), "content": text, "language": lang, "size": len(text), "encoding": "utf-8", "era": "modern"}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_OPTIONS(self) -> None:
        if self.path.startswith("/api/"):
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            return
        self.send_error(404)

    def do_GET(self) -> None:
        if self.path.rstrip("/") == "/api/filetypes":
            p = NEXUS / "data" / "field-programming-filetypes.json"
            if p.is_file():
                _json(self, 200, {"ok": True, **json.loads(p.read_text(encoding="utf-8"))})
                return
            _json(self, 404, {"ok": False, "error": "filetypes_missing"})
            return
        if self.path.rstrip("/") in ("/api/toolbar", "/api/ammocode/toolbar"):
            p = ROOT / "data" / "ammocode-toolbar-doctrine.json"
            if p.is_file():
                _json(self, 200, {"ok": True, **json.loads(p.read_text(encoding="utf-8"))})
                return
            _json(self, 404, {"ok": False, "error": "toolbar_missing"})
            return
        if self.path.rstrip("/") in ("/api/syntax-themes", "/api/ammocode/syntax-themes"):
            p = ROOT / "data" / "ammocode-syntax-themes.json"
            custom = ROOT / "data" / "custom-syntax-themes.json"
            doc = json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}
            if custom.is_file():
                try:
                    extra = json.loads(custom.read_text(encoding="utf-8"))
                    for key in ("editor_themes", "syntax_themes"):
                        if isinstance(extra.get(key), dict):
                            doc.setdefault(key, {}).update(extra[key])
                except json.JSONDecodeError:
                    pass
            _json(self, 200, {"ok": True, **doc})
            return
        if self.path.rstrip("/") in ("/api/settings", "/api/ammocode/settings"):
            sp = ROOT / "server" / "ammocode-settings.py"
            mod = _import_py(sp, "ac_settings")
            if mod and hasattr(mod, "load_settings"):
                _json(self, 200, mod.load_settings())
                return
            _json(self, 200, {"ok": True, "settings": {}})
            return
        if self.path.startswith("/api/read?"):
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            path = (qs.get("path") or [""])[0]
            _json(self, 200, _safe_read(path))
            return
        return super().do_GET()

    def do_POST(self) -> None:
        if not self.path.rstrip("/").startswith("/api/ammocode"):
            self.send_error(404)
            return
        try:
            n = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            n = 0
        try:
            body = json.loads(self.rfile.read(n).decode("utf-8") or "{}")
        except json.JSONDecodeError:
            _json(self, 400, {"ok": False, "error": "invalid_json"})
            return

        ic = ironclad_api()
        if ic and hasattr(ic, "gate_request"):
            peer = self.client_address[0] if self.client_address else ""
            try:
                verdict = ic.gate_request(
                    peer=str(peer), path=self.path.split("?", 1)[0], method="POST", body=body,
                )
                if not verdict.get("ok"):
                    _json(self, int(verdict.get("code") or 403), verdict)
                    return
            except Exception:
                pass

        action = str(body.get("action") or "").lower()
        nd = nondestructive()
        if nd and hasattr(nd, "assert_api_action"):
            blocked = nd.assert_api_action(action)
            if blocked:
                _json(self, 403, blocked)
                return
        path = str(body.get("path") or "")
        content = str(body.get("content") or "")
        lang = str(body.get("language") or body.get("lang") or "")
        profile = str(body.get("profile") or PROFILE)
        uni = universal()
        ft = filetypes()

        if action == "ping":
            ver = {}
            vp = ROOT / "data" / "ammocode-version.json"
            if vp.is_file():
                ver = json.loads(vp.read_text(encoding="utf-8"))
            nd_doc = nd.status() if nd and hasattr(nd, "status") else {"nondestructive": True}
            _json(self, 200, {
                "ok": True,
                "ammocode": True,
                "stack": True,
                "codename": ver.get("codename", "Stack"),
                "version": ver.get("distro_version", "6.1.0"),
                "grok16": (GROK16 / "bin" / "g16").is_file(),
                "filetypes_db": (NEXUS / "data" / "field-programming-filetypes.json").is_file(),
                "extensions": len(json.loads((NEXUS / "data" / "field-programming-filetypes.json").read_text()).get("extensions", {})) if (NEXUS / "data" / "field-programming-filetypes.json").is_file() else 0,
                **{k: v for k, v in nd_doc.items() if k != "ok"},
            })
            return

        if action == "discern":
            if ft:
                lang = ft.discern(path, mime=str(body.get("mime") or ""), content=content)
            elif uni:
                lang = uni.discern(path, mime=str(body.get("mime") or ""), content=content)
            _json(self, 200, {"ok": True, "language": lang})
            return

        if action == "read_file":
            _json(self, 200, _safe_read(path))
            return

        if action in ("g16_check", "check"):
            if uni:
                _json(self, 200, uni.check(content, lang=lang or (ft.discern(path) if ft else ""), path=path, profile=profile))
                return
            _json(self, 503, {"ok": False, "error": "g16_unavailable"})
            return

        if action in ("g16_build", "compile", "build"):
            if uni:
                _json(self, 200, uni.compile_source(content, lang=lang or (ft.discern(path) if ft else ""), path=path, profile=profile))
                return
            _json(self, 503, {"ok": False, "error": "g16_unavailable"})
            return

        if action in ("g16_run", "run"):
            if path and nd and hasattr(nd, "assert_run"):
                blocked = nd.assert_run(path)
                if blocked:
                    _json(self, 403, blocked)
                    return
            if path and ft:
                _json(self, 200, ft.run_path(path, profile=profile))
                return
            if uni and hasattr(uni, "run_file") and path:
                _json(self, 200, uni.run_file(path, lang=lang, profile=profile))
                return
            _json(self, 503, {"ok": False, "error": "run_unavailable"})
            return

        if action == "compiler_status":
            if uni:
                _json(self, 200, {"ok": True, **uni.status(), "ammocode_stack": True})
                return
            _json(self, 200, {"ok": True, "g16": (GROK16 / "bin" / "g16").is_file()})
            return

        if action in ("settings_load", "settings_get"):
            sp = ROOT / "server" / "ammocode-settings.py"
            mod = _import_py(sp, "ac_settings")
            if mod and hasattr(mod, "load_settings"):
                imp = body.get("import_local") if isinstance(body.get("import_local"), dict) else None
                _json(self, 200, mod.load_settings(import_local=imp))
                return
            _json(self, 503, {"ok": False, "error": "settings_unavailable"})
            return

        if action in ("settings_save", "settings_patch"):
            sp = ROOT / "server" / "ammocode-settings.py"
            mod = _import_py(sp, "ac_settings")
            if mod and hasattr(mod, "save_settings"):
                patch = body.get("patch") if isinstance(body.get("patch"), dict) else body.get("settings") or {}
                _json(self, 200, mod.save_settings(patch))
                return
            _json(self, 503, {"ok": False, "error": "settings_unavailable"})
            return

        if action == "settings_status":
            sp = ROOT / "server" / "ammocode-settings.py"
            mod = _import_py(sp, "ac_settings")
            if mod and hasattr(mod, "settings_status"):
                _json(self, 200, mod.settings_status())
                return
            _json(self, 503, {"ok": False, "error": "settings_unavailable"})
            return

        _json(self, 400, {
            "ok": False,
            "error": "unknown_action",
            "actions": [
                "ping", "discern", "read_file", "g16_check", "g16_build", "g16_run",
                "compiler_status", "settings_load", "settings_save", "settings_status",
            ],
        })

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


def main() -> int:
    os.chdir(ROOT)
    host = os.environ.get("AMMOCODE_HOST", "127.0.0.1")
    httpd = ThreadingHTTPServer((host, PORT), Handler)
    print(f"AmmoCode Stack http://{host}:{PORT}/", flush=True)
    print(f"  g16: {GROK16 / 'bin' / 'g16'}", flush=True)
    print(f"  api: http://{host}:{PORT}/api/ammocode", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())