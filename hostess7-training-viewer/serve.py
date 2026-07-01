#!/usr/bin/env pythong
"""Hostess 7 Training Viewer — personal side-project server."""
from __future__ import annotations

import json
import mimetypes
import os
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(ROOT.parent)))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", str(INSTALL / ".nexus-state")))
HOSTESS7 = Path(os.environ.get("HOSTESS7_ROOT", str(INSTALL / "Hostess7")))
PORT = int(os.environ.get("H7_TRAINING_VIEWER_PORT", "9488"))
MODELS_FILE = ROOT / "data" / "connected-models.json"

sys.path.insert(0, str(ROOT))
from graph_engine import build_wireframe_graph, probe_model  # noqa: E402


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _tail_jsonl(path: Path, limit: int = 24) -> list[dict[str, Any]]:
    if not path.is_file() or limit <= 0:
        return []
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    except OSError:
        return []
    return rows


def _py_json(module: str, args: list[str], *, timeout: int = 120) -> dict[str, Any]:
    py = INSTALL / "lib" / module
    if not py.is_file():
        return {"ok": False, "error": f"missing_{module}"}
    env = {
        **os.environ,
        "NEXUS_INSTALL_ROOT": str(INSTALL),
        "NEXUS_STATE_DIR": str(STATE),
        "HOSTESS7_ROOT": str(HOSTESS7),
    }
    try:
        proc = subprocess.run(
            [sys.executable, str(py), *args],
            cwd=str(INSTALL),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        out = (proc.stdout or "").strip()
        if out.startswith("{"):
            try:
                doc = json.loads(out)
                doc.setdefault("ok", proc.returncode == 0)
                return doc
            except json.JSONDecodeError:
                pass
        return {"ok": proc.returncode == 0, "stdout": out[:2000], "stderr": (proc.stderr or "")[:800]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout", "module": module}
    except OSError as exc:
        return {"ok": False, "error": str(exc), "module": module}


def load_models_doc() -> dict[str, Any]:
    doc = _load(MODELS_FILE, {})
    if not doc.get("models"):
        doc = {
            "schema": "hostess7-connected-models/v1",
            "models": [],
            "positions": {},
        }
    return doc


def save_model(model: dict[str, Any]) -> dict[str, Any]:
    doc = load_models_doc()
    models: list[dict[str, Any]] = list(doc.get("models") or [])
    mid = str(model.get("id") or "").strip()
    if not mid:
        return {"ok": False, "error": "id_required"}
    replaced = False
    for i, m in enumerate(models):
        if str(m.get("id")) == mid:
            models[i] = {**m, **model, "id": mid}
            replaced = True
            break
    if not replaced:
        models.append(model)
    doc["models"] = models
    from graph_engine import _now as ge_now
    doc["updated"] = ge_now()
    _save(MODELS_FILE, doc)
    probe = probe_model(model, install=INSTALL, state=STATE, hostess7=HOSTESS7)
    return {"ok": True, "model": model, "probe": probe, "replaced": replaced}


def delete_model(model_id: str) -> dict[str, Any]:
    doc = load_models_doc()
    before = len(doc.get("models") or [])
    doc["models"] = [m for m in (doc.get("models") or []) if str(m.get("id")) != model_id]
    if "positions" in doc and model_id in doc["positions"]:
        del doc["positions"][model_id]
    _save(MODELS_FILE, doc)
    return {"ok": True, "deleted": model_id, "removed": before - len(doc["models"])}


def bundle_training_data(*, refresh: bool = False) -> dict[str, Any]:
    sys.path.insert(0, str(INSTALL / "lib"))
    try:
        import hostess7_training_bundle as h7bundle  # type: ignore

        return h7bundle.bundle_training_data(refresh=refresh)
    except Exception:
        pass
    if refresh:
        _py_json("hostess7-training.py", ["assess"], timeout=45)
    models_doc = load_models_doc()
    bundle = {
        "schema": "hostess7-training-viewer/v1",
        "assessment": _py_json("hostess7-training.py", ["assess"], timeout=45),
        "training_panel": _load(STATE / "hostess7-training-panel.json", {}),
        "connected_models_registry": models_doc,
    }
    bundle["wireframe"] = build_wireframe_graph(bundle, models_doc, install=INSTALL, state=STATE, hostess7=HOSTESS7)
    return bundle


class Handler(BaseHTTPRequestHandler):
    server_version = "Hostess7TrainingViewer/1.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("%s - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), fmt % args))

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, doc: Any, *, code: int = 200) -> None:
        self._send(code, json.dumps(doc, ensure_ascii=False, indent=2).encode("utf-8"), "application/json")

    def _read_body(self) -> dict[str, Any]:
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path in ("/", "/index.html"):
            self._send(200, (ROOT / "index.html").read_bytes(), "text/html; charset=utf-8")
            return
        if path.startswith("/assets/"):
            fp = ROOT / path.lstrip("/")
            if fp.is_file():
                ctype = mimetypes.guess_type(str(fp))[0] or "application/octet-stream"
                self._send(200, fp.read_bytes(), ctype)
                return
            self._send(404, b"not found", "text/plain")
            return
        if path == "/api/bundle":
            refresh = "refresh=1" in (parsed.query or "")
            self._json(bundle_training_data(refresh=refresh))
            return
        if path == "/api/graph":
            refresh = "refresh=1" in (parsed.query or "")
            b = bundle_training_data(refresh=refresh)
            self._json(b.get("wireframe") or {})
            return
        if path == "/api/models":
            doc = load_models_doc()
            probed = []
            for m in doc.get("models") or []:
                probed.append({**m, "probe": probe_model(m, install=INSTALL, state=STATE, hostess7=HOSTESS7)})
            self._json({"ok": True, "models": probed, "schema": doc.get("schema")})
            return
        if path == "/api/health":
            self._json({"ok": True, "port": PORT, "state": str(STATE), "install": str(INSTALL)})
            return
        if path == "/api/training-doctrine":
            self._json(_load(INSTALL / "data" / "hostess7-training-doctrine.json", {}))
            return
        self._send(404, b"not found", "text/plain")

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/solidify":
            self._json(_py_json("hostess7-training.py", ["complete", "--skip-omnibus"], timeout=600))
            return
        if path == "/api/assess":
            self._json(_py_json("hostess7-training.py", ["assess"], timeout=60))
            return
        if path == "/api/train-all":
            self._json(_py_json("hostess7-master.py", ["train-all"], timeout=300))
            return
        if path == "/api/train/self-interaction":
            body = self._read_body()
            rounds = int(body.get("rounds") or 6)
            args = ["self-interaction", str(rounds)]
            self._json(_py_json("hostess7-training.py", args, timeout=180))
            return
        if path == "/api/train/iq":
            self._json(_py_json("hostess7-truth-rating.py", ["iq-test"], timeout=300))
            return
        if path.startswith("/api/train/track/"):
            track_id = path.split("/api/train/track/", 1)[-1].strip("/")
            if track_id:
                self._json(_py_json("hostess7-training.py", ["track", track_id], timeout=300))
                return
        if path == "/api/voice/speak":
            body = self._read_body()
            text = str(body.get("text") or body.get("message") or "").strip()
            if text:
                self._json(_py_json("hostess7-voice.py", ["speak", text], timeout=60))
                return
            self._json({"ok": False, "error": "text_required"}, code=400)
            return
        if path == "/api/models":
            body = self._read_body()
            self._json(save_model(body))
            return
        if path == "/api/models/probe":
            body = self._read_body()
            self._json({"ok": True, "probe": probe_model(body, install=INSTALL, state=STATE, hostess7=HOSTESS7)})
            return
        self._send(404, b"not found", "text/plain")

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/models":
            q = parse_qs(parsed.query)
            mid = (q.get("id") or [""])[0]
            if not mid:
                self._json({"ok": False, "error": "id_required"}, code=400)
                return
            self._json(delete_model(str(mid)))
            return
        self._send(404, b"not found", "text/plain")


def main() -> int:
    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(json.dumps({
        "ok": True,
        "url": f"http://127.0.0.1:{PORT}/",
        "state_dir": str(STATE),
        "install_root": str(INSTALL),
    }, ensure_ascii=False), flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())