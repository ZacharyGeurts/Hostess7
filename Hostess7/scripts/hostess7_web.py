#!/usr/bin/env pythong
"""Hostess7 web — chat UI + API for GitHub Codespaces and local use."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
DOCS = ROOT / "docs"
ZAC = ROOT / "zac"
STORAGE = ROOT / "cache" / "fieldstorage"


def _ensure_brain() -> None:
    marker = STORAGE / "brain" / "superintel"
    if marker.is_dir() and any(marker.rglob("*.json")):
        return
    index = ZAC / "fieldstorage.zac"
    if not index.is_file():
        return
    from field_zac import restore_storage  # noqa: WPS433

    restore_storage(zac_dir=ZAC, storage=STORAGE, verify=True)


def _ask(query: str) -> dict:
    os.environ.setdefault("HOSTESS7_OUTPUT_WINDOW", "1")
    os.environ.setdefault("HOSTESS7_PRO", "1")
    brain = ROOT / "scripts" / "field_superintelligence.py"
    proc = subprocess.run(
        [sys.executable, str(brain), "ask", query],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
        env={**os.environ, "HOSTESS7_WEB": "1"},
    )
    text = (proc.stdout or proc.stderr or "").strip()
    if not text:
        text = "I'm here — try asking about hearing, the library, or law."
    return {"ok": proc.returncode == 0, "text": text, "query": query}


def create_app():
    try:
        from flask import Flask, jsonify, request, send_from_directory
    except ImportError as exc:
        raise SystemExit("Install Flask: pip install flask") from exc

    app = Flask(__name__, static_folder=str(DOCS), static_url_path="")

    @app.route("/")
    def index():
        return send_from_directory(DOCS, "index.html")

    @app.route("/health")
    def health():
        return jsonify({"ok": True, "service": "Hostess7", "owner": "ZacharyGeurts"})

    @app.route("/api/status")
    def status():
        from field_license_status import format_notice, is_demo, license_mode  # noqa: WPS433

        zac_ok = (ZAC / "fieldstorage.zac").is_file()
        brain_ok = (STORAGE / "brain").is_dir()
        return jsonify({
            "ok": True,
            "zac": zac_ok,
            "brain": brain_ok,
            "hearing": True,
            "license_mode": license_mode(),
            "demo": is_demo(),
            "license_notice": format_notice(short=True),
            "library_h7": len(list((STORAGE / "textbooks").glob("*.h7"))) if (STORAGE / "textbooks").is_dir() else 0,
        })

    @app.route("/api/ask", methods=["POST"])
    def api_ask():
        data = request.get_json(silent=True) or {}
        query = str(data.get("query", "") or request.form.get("query", "")).strip()
        if not query:
            return jsonify({"ok": False, "error": "empty query"}), 400
        return jsonify(_ask(query))

    @app.route("/api/hearing")
    def api_hearing():
        from field_hearing_corpus import ensure_corpus, search_hearing  # noqa: WPS433

        ensure_corpus()
        q = request.args.get("q", "hearing listen speak")
        hits = search_hearing(q, limit=8)
        return jsonify({"ok": True, "query": q, "hits": hits})

    @app.route("/api/final-ear")
    def api_final_ear():
        from field_final_ear_bridge import bridge_status, gac1_status, sovereign_sync  # noqa: WPS433

        view = request.args.get("view", "status")
        if view == "gac1":
            return jsonify(gac1_status())
        if view == "sync":
            return jsonify(sovereign_sync())
        return jsonify(bridge_status())

    @app.route("/api/final-ear/identify", methods=["POST"])
    def api_final_ear_identify():
        from field_final_ear_bridge import earball_post, listen_and_identify  # noqa: WPS433

        data = request.get_json(silent=True) or {}
        if data.get("listen"):
            return jsonify(listen_and_identify(seconds=int(data.get("seconds", 6))))
        return jsonify(earball_post({
            "action": "eye_ear_fusion",
            "evidence": data.get("evidence") or {"mouth_correlation": 0.9, "speech_present": True},
            "existence": data.get("existence") or {"correlation": 0.82},
        }))

    @app.route("/api/library/search")
    def api_library():
        from field_library import search_library  # noqa: WPS433

        q = request.args.get("q", "children algebra")
        hits = search_library(q)[:12]
        return jsonify({"ok": True, "query": q, "hits": hits})

    @app.route("/api/world")
    def api_world():
        from field_world_corpus import ensure_corpus, search_world  # noqa: WPS433

        ensure_corpus()
        q = request.args.get("q", "bible fcc botany")
        return jsonify({"ok": True, "query": q, "hits": search_world(q, limit=10)})

    @app.route("/api/videogames")
    def api_videogames():
        from field_videogame_db import ensure_db, search_games  # noqa: WPS433

        ensure_db()
        q = request.args.get("q", "mario zelda")
        return jsonify({"ok": True, "query": q, "hits": search_games(q, limit=12)})

    return app


def main() -> int:
    _ensure_brain()
    port = int(os.environ.get("PORT", os.environ.get("HOSTESS7_WEB_PORT", "8080")))
    host = os.environ.get("HOSTESS7_WEB_HOST", "0.0.0.0")
    app = create_app()
    print(f"Hostess7 web → http://{host}:{port}")
    print("METRIC hostess7_web=1")
    app.run(host=host, port=port, debug=False, threaded=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())