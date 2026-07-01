#!/usr/bin/env python3
"""Grok16 language test matrix — secure-chamber compile/run per language; build log to output window."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent))
PANEL = INSTALL / "panel"
LOG_PATH = STATE / "g16-language-test-log.jsonl"
STATUS_PATH = STATE / "g16-language-test-status.json"
WINDOW_PORT = int(os.environ.get("G16_TEST_WINDOW_PORT", "9488"))

_RUN_LOCK = threading.Lock()
_RUNNING = False


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _h7s_read_json(path: Path, default: Any = None) -> Any:
    fs_py = INSTALL / "lib" / "field-h7s-fs.py"
    if path.suffix.lower() == ".json" and fs_py.is_file():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("_h7s_fs_io", fs_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "read_json"):
                    return mod.read_json(path, default=default)
        except Exception:
            pass
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}

def _load(path: Path, default: Any = None) -> Any:
    return _h7s_read_json(path, default=default)


def _grok16_root() -> Path:
    env = os.environ.get("GROK16_ROOT", "").strip()
    if env:
        return Path(env)
    for cand in (INSTALL / "Grok16", SG / "Grok16", SG / "NewLatest" / "Grok16"):
        if cand.is_dir():
            return cand.resolve()
    return (INSTALL / "Grok16").resolve()


GROK16 = _grok16_root()
EXAMPLES = GROK16 / "examples" / "languages"


def _import_mod(path: Path, name: str) -> Any | None:
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _secure_chamber() -> Any | None:
    return _import_mod(INSTALL / "lib" / "g16-secure-chamber.py", "g16_sec_test")


def _universal_compiler() -> Any | None:
    return _import_mod(GROK16 / "lib" / "g16-universal-compiler.py", "g16_uni_test")


def _append_log(line: dict[str, Any]) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(line, ensure_ascii=False) + "\n")


def _emit(kind: str, text: str, *, lang: str = "", data: Any = None) -> None:
    _append_log({
        "ts": _now(),
        "kind": kind,
        "lang": lang,
        "text": text,
        "data": data,
    })


def _save_status(doc: dict[str, Any]) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    tmp = STATUS_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(STATUS_PATH)


def discover_matrix() -> list[dict[str, Any]]:
    g16_doc = _load(GROK16 / "data" / "grok16-languages.json", {})
    langs = g16_doc.get("languages") or {}
    rows: list[dict[str, Any]] = []
    for lang_id in sorted(langs.keys()):
        row = langs[lang_id]
        folder = EXAMPLES / lang_id
        hello: Path | None = None
        if folder.is_dir():
            launch = folder / f"{lang_id}.launch"
            if launch.is_file():
                manifest = _load(launch, {})
                entry = manifest.get("entry")
                if entry and (folder / str(entry)).is_file():
                    hello = folder / str(entry)
            if not hello:
                for p in sorted(folder.glob("hello.*")):
                    if p.is_file():
                        hello = p
                        break
        rows.append({
            "lang": lang_id,
            "driver": row.get("driver"),
            "secure_chamber": row.get("secure_chamber", True),
            "sample": str(hello) if hello else None,
            "has_sample": bool(hello),
        })
    return rows


def _format_result(label: str, result: dict[str, Any]) -> list[str]:
    lines = [f"  [{label}] ok={result.get('ok')} blocked={result.get('blocked')}"]
    for key in ("error", "message", "hint", "compiler", "runner", "chamber"):
        if result.get(key):
            lines.append(f"    {key}: {result[key]}")
    if result.get("stdout"):
        lines.append("    --- stdout ---")
        for ln in str(result["stdout"]).splitlines()[:40]:
            lines.append(f"    | {ln}")
    if result.get("stderr"):
        lines.append("    --- stderr ---")
        for ln in str(result["stderr"]).splitlines()[:40]:
            lines.append(f"    | {ln}")
    sec = result.get("security") or result.get("compile", {}).get("security") if isinstance(result.get("compile"), dict) else None
    if isinstance(sec, dict) and sec.get("findings"):
        lines.append(f"    security_findings: {len(sec.get('findings') or [])}")
    return lines


def test_language(lang_id: str, *, sample: str | None = None) -> dict[str, Any]:
    """Full build lane for one language — check, compile, run in secure chamber."""
    sec = _secure_chamber()
    uni = _universal_compiler()
    sample_path = Path(sample) if sample else None
    if not sample_path or not sample_path.is_file():
        folder = EXAMPLES / lang_id
        if folder.is_dir():
            for p in sorted(folder.glob("hello.*")):
                sample_path = p
                break
    log_lines: list[str] = []
    result: dict[str, Any] = {
        "lang": lang_id,
        "sample": str(sample_path) if sample_path else None,
        "ok": False,
        "check": None,
        "compile": None,
        "run": None,
    }

    def log(msg: str, kind: str = "build") -> None:
        log_lines.append(msg)
        _emit(kind, msg, lang=lang_id)

    log(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    log(f"GROK16 TEST · {lang_id}")
    log(f"sample: {sample_path or '—'}")

    if not sample_path or not sample_path.is_file():
        log("SKIP — no hello sample in examples/languages/", "warn")
        result["ok"] = False
        result["error"] = "no_sample"
        return {**result, "log": log_lines}

    content = sample_path.read_text(encoding="utf-8", errors="replace")

    if uni and hasattr(uni, "discern"):
        discerned = uni.discern(str(sample_path), content=content)
        log(f"[discern] path → {discerned}")
        result["discerned"] = discerned

    if uni and hasattr(uni, "check"):
        log("[check] g16-universal-compiler.check …")
        chk = uni.check(content, lang=lang_id, path=str(sample_path))
        result["check"] = chk
        for ln in _format_result("check", chk):
            log(ln)
        if chk.get("blocked"):
            result["ok"] = False
            result["error"] = "security_blocked"
            return {**result, "log": log_lines}

    if sec and hasattr(sec, "compile_source"):
        log("[compile] g16-secure-chamber.compile_source …")
        comp = sec.compile_source(content, lang=lang_id, path=str(sample_path))
        result["compile"] = comp
        for ln in _format_result("compile", comp):
            log(ln)

    if sec and hasattr(sec, "run_path"):
        log("[run] g16-secure-chamber.run_path …")
        run = sec.run_path(str(sample_path), lang=lang_id)
        result["run"] = run
        for ln in _format_result("run", run):
            log(ln)
        result["ok"] = bool(run.get("ok")) or bool(run.get("gate_only"))
        if run.get("blocked"):
            result["ok"] = False
            result["error"] = "run_blocked"
        elif run.get("error") and not run.get("gate_only"):
            result["error"] = run.get("error")
    elif uni and hasattr(uni, "run_file"):
        log("[run] g16-universal-compiler.run_file …")
        run = uni.run_file(str(sample_path), lang=lang_id)
        result["run"] = run
        for ln in _format_result("run", run):
            log(ln)
        result["ok"] = bool(run.get("ok"))

    status = "PASS" if result.get("ok") else "FAIL"
    log(f"═══ {lang_id} · {status} ═══", "ok" if result.get("ok") else "err")
    return {**result, "log": log_lines}


def run_all(*, on_progress: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    global _RUNNING
    with _RUN_LOCK:
        if _RUNNING:
            return {"ok": False, "error": "already_running"}
        _RUNNING = True

    LOG_PATH.unlink(missing_ok=True)
    matrix = discover_matrix()
    t0 = time.perf_counter()
    _emit("meta", f"Grok16 language test matrix — {len(matrix)} languages", lang="")
    _save_status({
        "schema": "g16-language-test-status/v1",
        "updated": _now(),
        "running": True,
        "total": len(matrix),
        "done": 0,
        "passed": 0,
        "failed": 0,
    })

    results: list[dict[str, Any]] = []
    passed = failed = 0
    try:
        for i, row in enumerate(matrix, 1):
            lang = row["lang"]
            _emit("meta", f"[{i}/{len(matrix)}] starting {lang} …", lang=lang)
            rep = test_language(lang, sample=row.get("sample"))
            results.append(rep)
            if rep.get("ok"):
                passed += 1
            else:
                failed += 1
            status_doc = {
                "schema": "g16-language-test-status/v1",
                "updated": _now(),
                "running": True,
                "total": len(matrix),
                "done": i,
                "passed": passed,
                "failed": failed,
                "current": lang,
            }
            _save_status(status_doc)
            if on_progress:
                on_progress(status_doc)
    finally:
        _RUNNING = False

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    summary = {
        "schema": "g16-language-test-matrix/v1",
        "updated": _now(),
        "ok": failed == 0,
        "total": len(matrix),
        "passed": passed,
        "failed": failed,
        "elapsed_ms": elapsed_ms,
        "grok16_root": str(GROK16),
        "results": [{k: v for k, v in r.items() if k != "log"} for r in results],
    }
    _save_status({**summary, "running": False, "schema": "g16-language-test-status/v1"})
    _emit("meta", f"DONE — {passed} passed · {failed} failed · {elapsed_ms}ms", lang="")
    _emit("summary", json.dumps(summary, ensure_ascii=False), lang="", data=summary)
    return summary


def read_log(*, offset: int = 0) -> dict[str, Any]:
    lines: list[dict[str, Any]] = []
    if not LOG_PATH.is_file():
        return {"ok": True, "offset": 0, "lines": [], "eof": True}
    raw = LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
    for i, ln in enumerate(raw):
        if i < offset:
            continue
        try:
            lines.append(json.loads(ln))
        except json.JSONDecodeError:
            lines.append({"kind": "raw", "text": ln, "ts": _now()})
    return {
        "ok": True,
        "offset": offset,
        "next_offset": offset + len(lines),
        "lines": lines,
        "status": _load(STATUS_PATH, {}),
    }


def launch_browser(*, port: int = WINDOW_PORT) -> dict[str, Any]:
    url = f"http://127.0.0.1:{port}/?autostart=1"
    opened = False
    try:
        opened = bool(webbrowser.open_new(url))
    except OSError:
        opened = False
    return {"ok": True, "url": url, "webbrowser": opened, "port": port}


class _WindowHandler(BaseHTTPRequestHandler):
    server_version = "G16BuildOutput/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def _send_json(self, code: int, payload: Any) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str) -> None:
        if not path.is_file():
            self.send_error(404)
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _api_path(self, path: str) -> str:
        if path.startswith("/api/g16/language-test/"):
            return path[len("/api/g16/language-test") :]
        return path

    def do_GET(self) -> None:
        path = self._api_path(urlparse(self.path).path)
        qs = parse_qs(urlparse(self.path).query)
        if path in ("/", "/g16-build-output", "/g16-build-output.html"):
            self._send_file(PANEL / "g16-build-output.html", "text/html; charset=utf-8")
            return
        if path == "/assets/g16-build-output.js":
            self._send_file(PANEL / "assets" / "g16-build-output.js", "application/javascript; charset=utf-8")
            return
        if path in ("/api/status", "/status"):
            st = _load(STATUS_PATH, {})
            st["running"] = _RUNNING
            self._send_json(200, {"ok": True, "status": st})
            return
        if path in ("/api/log", "/log"):
            offset = int((qs.get("offset") or ["0"])[0])
            self._send_json(200, read_log(offset=offset))
            return
        if path in ("/api/matrix", "/matrix"):
            self._send_json(200, {"ok": True, "matrix": discover_matrix()})
            return
        self.send_error(404)

    def do_POST(self) -> None:
        path = self._api_path(urlparse(self.path).path)
        if path in ("/api/start", "/start"):
            if _RUNNING:
                self._send_json(200, {"ok": True, "started": False, "message": "already_running"})
                return

            def _bg() -> None:
                run_all()

            threading.Thread(target=_bg, daemon=True).start()
            self._send_json(200, {"ok": True, "started": True})
            return
        self.send_error(404)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


def run_window_server(*, port: int = WINDOW_PORT, autostart_delay: float = 1.2) -> int:
    """Launch output window, then stream full build log for every language."""
    STATE.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", port), _WindowHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    launch_browser(port=port)
    time.sleep(autostart_delay)
    _emit("meta", f"Output window open — http://127.0.0.1:{port}/", lang="")
    summary = run_all()
    _emit("meta", "Build matrix complete — window may stay open for review.", lang="")
    try:
        while thread.is_alive():
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    server.shutdown()
    return 0 if summary.get("ok") else 1


def run_compiler_test(*, halt: bool = True, langs: list[str] | None = None) -> dict[str, Any]:
    harness = _import_mod(INSTALL / "lib" / "g16-compiler-test-harness.py", "g16_matrix_harness")
    if not harness or not hasattr(harness, "run_harness"):
        return {"ok": False, "error": "g16_compiler_test_harness_missing"}
    return harness.run_harness(langs=langs, halt=halt)


def run_bench(*, quick: bool = False) -> dict[str, Any]:
    bench_py = INSTALL / "lib" / "g16-compiler-bench.py"
    mod = _import_mod(bench_py, "g16_matrix_bench")
    if not mod or not hasattr(mod, "run_bench"):
        return {"ok": False, "error": "g16_compiler_bench_missing"}
    langs = None
    if quick:
        matrix = mod.discover_bench_matrix()
        langs = [r["lang"] for r in matrix if r.get("has_sample")][:8]
    return mod.run_bench(langs=langs)


def posture() -> dict[str, Any]:
    st = _load(STATUS_PATH, {})
    matrix = discover_matrix()
    return {
        "schema": "g16-language-test-matrix/v1",
        "updated": _now(),
        "grok16_root": str(GROK16),
        "languages": len(matrix),
        "with_samples": sum(1 for r in matrix if r.get("has_sample")),
        "running": _RUNNING,
        "status": st,
        "log": str(LOG_PATH),
        "window_port": WINDOW_PORT,
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "posture").strip().lower()
    if cmd in ("posture", "status", "json"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "matrix":
        print(json.dumps({"ok": True, "matrix": discover_matrix()}, ensure_ascii=False, indent=2))
        return 0
    if cmd == "log":
        offset = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        print(json.dumps(read_log(offset=offset), ensure_ascii=False, indent=2))
        return 0
    if cmd == "test" and len(sys.argv) > 2:
        print(json.dumps(test_language(sys.argv[2]), ensure_ascii=False, indent=2))
        return 0
    if cmd == "run":
        summary = run_all()
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0 if summary.get("ok") else 1
    if cmd == "bench":
        doc = run_bench(quick="--quick" in sys.argv)
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 0 if doc.get("ok") else 1
    if cmd == "harness":
        halt = "--no-halt" not in sys.argv
        langs = [a for a in sys.argv[2:] if not a.startswith("--")]
        doc = run_compiler_test(halt=halt, langs=langs or None)
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 0 if doc.get("ok") else 1
    if cmd == "exploring-books":
        harness = _import_mod(INSTALL / "lib" / "g16-compiler-test-harness.py", "g16_books")
        if not harness:
            print(json.dumps({"ok": False, "error": "harness_missing"}, indent=2))
            return 1
        doc = harness.ensure_exploring_books()
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 0 if doc.get("ok") else 1
    if cmd == "window":
        port = int(sys.argv[2]) if len(sys.argv) > 2 else WINDOW_PORT
        return run_window_server(port=port)
    if cmd == "serve":
        port = int(sys.argv[2]) if len(sys.argv) > 2 else WINDOW_PORT
        server = ThreadingHTTPServer(("127.0.0.1", port), _WindowHandler)
        print(json.dumps({"ok": True, "url": f"http://127.0.0.1:{port}/", "port": port}, indent=2), flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            server.shutdown()
        return 0
    print(json.dumps({
        "error": "usage",
        "cmds": ["posture", "matrix", "window [port]", "serve [port]", "run", "bench [--quick]", "harness [--no-halt] [LANG...]", "exploring-books", "test LANG", "log [offset]"],
    }, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())