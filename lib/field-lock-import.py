#!/usr/bin/env pythong
"""Lock import — KeePass, 1Password, Bitwarden, LastPass, browser exports → sovereign vault."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))
DOCTRINE = INSTALL / "data" / "field-lock-import-doctrine.json"
STAGING = STATE / "field-lock-import-staging.json"
VAULT_DIR = STATE / "field-keepass-vault"
IMPORT_DIR = STATE / "field-lock-imports"
IMPORT_LOG = STATE / "field-lock-import.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append_log(row: dict[str, Any]) -> None:
    try:
        with IMPORT_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({**row, "ts": _now()}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _entry(title: str, username: str, password: str, url: str = "", notes: str = "", *, source: str) -> dict[str, Any]:
    return {
        "title": title or "Untitled",
        "username": username,
        "password": password,
        "url": url,
        "notes": notes,
        "source": source,
        "id": hashlib.sha256(f"{title}:{username}:{url}".encode()).hexdigest()[:16],
    }


def _parse_csv_generic(text: str, *, source: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return rows
    fields = {f.lower().strip(): f for f in reader.fieldnames}
    for row in reader:
        title = row.get(fields.get("title", "title") or fields.get("name", "name") or "") or ""
        user = row.get(fields.get("username", "username") or fields.get("login", "login") or "") or ""
        pwd = row.get(fields.get("password", "password") or "") or ""
        url = row.get(fields.get("url", "url") or fields.get("uri", "uri") or "") or ""
        notes = row.get(fields.get("notes", "notes") or fields.get("extra", "extra") or "") or ""
        if user or pwd or url:
            rows.append(_entry(str(title), str(user), str(pwd), str(url), str(notes), source=source))
    return rows


def _parse_lastpass_csv(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        rows.append(_entry(
            row.get("name") or row.get("Name") or "",
            row.get("username") or row.get("Username") or "",
            row.get("password") or row.get("Password") or "",
            row.get("url") or row.get("URL") or "",
            row.get("extra") or row.get("Notes") or "",
            source="lastpass_csv",
        ))
    return [r for r in rows if r.get("username") or r.get("password")]


def _parse_1password_csv(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        rows.append(_entry(
            row.get("Title") or row.get("title") or "",
            row.get("Username") or row.get("username") or "",
            row.get("Password") or row.get("password") or "",
            row.get("URL") or row.get("url") or "",
            row.get("Notes") or row.get("notes") or "",
            source="onepassword_csv",
        ))
    return [r for r in rows if r.get("username") or r.get("password")]


def _parse_bitwarden_json(text: str) -> list[dict[str, Any]]:
    try:
        doc = json.loads(text)
    except json.JSONDecodeError:
        return []
    items = doc if isinstance(doc, list) else (doc.get("items") or [])
    rows: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        login = item.get("login") or {}
        rows.append(_entry(
            str(item.get("name") or ""),
            str(login.get("username") or ""),
            str(login.get("password") or ""),
            str(login.get("uri") or login.get("uris", [{}])[0].get("uri", "") if isinstance(login.get("uris"), list) else ""),
            str(item.get("notes") or ""),
            source="bitwarden_json",
        ))
    return [r for r in rows if r.get("username") or r.get("password")]


def _parse_keepass_xml(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return rows
    for group in root.iter("Group"):
        for entry in group.findall("Entry"):
            vals: dict[str, str] = {}
            for s in entry.findall("String"):
                key = s.find("Key")
                val = s.find("Value")
                if key is not None and val is not None and key.text:
                    vals[key.text] = val.text or ""
            rows.append(_entry(
                vals.get("Title", ""),
                vals.get("UserName", ""),
                vals.get("Password", ""),
                vals.get("URL", ""),
                vals.get("Notes", ""),
                source="keepass_xml",
            ))
    return [r for r in rows if r.get("username") or r.get("password")]


def _detect_format(path: Path, text: str = "") -> str:
    ext = path.suffix.lower()
    if ext == ".kdbx":
        return "kdbx"
    if ext == ".xml" and ("KeePassFile" in text or "<Entry>" in text):
        return "keepass_xml"
    if ext == ".json":
        if "encrypted" in text[:200] or '"items"' in text:
            return "bitwarden_json"
        return "json"
    if ext == ".csv":
        low = text[:500].lower()
        if "username,password,url" in low or "name,url,username" in low:
            return "lastpass_csv"
        if "title,username,password" in low or "title,url,username" in low:
            return "onepassword_csv"
        return "csv_generic"
    if ext == ".enc" and "queen-vault" in path.name:
        return "queen_vault"
    return "unknown"


def _merge_staging(entries: list[dict[str, Any]], *, source_file: str, fmt: str) -> dict[str, Any]:
    staging = _load(STAGING, {"entries": [], "imports": []})
    seen = {e.get("id") for e in staging.get("entries") or []}
    added = 0
    for entry in entries:
        if entry.get("id") in seen:
            continue
        seen.add(entry.get("id"))
        staging.setdefault("entries", []).append(entry)
        added += 1
    staging.setdefault("imports", []).append({
        "file": source_file,
        "format": fmt,
        "added": added,
        "total": len(entries),
        "ts": _now(),
    })
    staging["updated"] = _now()
    staging["entry_count"] = len(staging.get("entries") or [])
    _save(STAGING, staging)
    return staging


def _copy_kdbx(src: Path) -> dict[str, Any]:
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    dest = VAULT_DIR / src.name
    if dest.resolve() != src.resolve():
        shutil.copy2(src, dest)
    _append_log({"action": "import_kdbx", "src": str(src), "dest": str(dest)})
    return {"ok": True, "format": "kdbx", "vault": str(dest), "copied": True}


def _export_staging_csv() -> Path:
    staging = _load(STAGING, {})
    entries = staging.get("entries") or []
    out = IMPORT_DIR / f"lock-import-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.csv"
    IMPORT_DIR.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Title", "UserName", "Password", "URL", "Notes", "Source"])
        for e in entries:
            w.writerow([e.get("title"), e.get("username"), e.get("password"), e.get("url"), e.get("notes"), e.get("source")])
    return out


def _try_keepassxc_cli_import(csv_path: Path, vault: Path) -> dict[str, Any]:
    cli = shutil.which("keepassxc-cli")
    if not cli or not vault.is_file():
        return {"ok": False, "skipped": True, "reason": "keepassxc_cli_or_vault_missing"}
    try:
        proc = subprocess.run(
            [cli, "import", str(csv_path), str(vault)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        return {"ok": proc.returncode == 0, "stdout": (proc.stdout or "")[:200], "stderr": (proc.stderr or "")[:200]}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": str(exc)}


def _bridge_queen_browser() -> dict[str, Any]:
    """Pull staged credentials from queen-browser-import into Lock staging."""
    manifest = _load(STATE / "queen-browser-import.json", {})
    creds = manifest.get("credentials") or manifest.get("passwords") or []
    if not creds:
        drop = STATE / "imports"
        for name in ("passwords.csv", "chrome_passwords.csv", "logins.csv"):
            p = drop / name
            if p.is_file():
                text = p.read_text(encoding="utf-8", errors="replace")
                fmt = _detect_format(p, text)
                if fmt == "csv_generic":
                    entries = _parse_csv_generic(text, source="browser_drop")
                    staging = _merge_staging(entries, source_file=str(p), fmt=fmt)
                    return {"ok": True, "format": fmt, "added": len(entries), "staging": staging.get("entry_count")}
    entries = []
    for row in creds[:512]:
        if not isinstance(row, dict):
            continue
        entries.append(_entry(
            str(row.get("name") or row.get("origin") or ""),
            str(row.get("username") or ""),
            str(row.get("password") or ""),
            str(row.get("origin") or row.get("url") or ""),
            "imported from Queen browser sweep",
            source="queen_browser_import",
        ))
    staging = _merge_staging(entries, source_file="queen-browser-import.json", fmt="queen_browser")
    return {"ok": True, "format": "queen_browser", "added": len(entries), "staging": staging.get("entry_count")}


def _scan_legacy_vaults() -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    patterns = [
        Path.home() / "Documents",
        Path.home(),
        STATE / "field-keepass-vault",
        STATE / "imports",
        Path.home() / ".config" / "keepassxc",
    ]
    for base in patterns:
        if not base.is_dir():
            continue
        try:
            for p in base.rglob("*.kdbx"):
                if p.is_file():
                    found.append({"path": str(p), "name": p.name, "bytes": p.stat().st_size, "mtime": p.stat().st_mtime})
        except OSError:
            continue
    found.sort(key=lambda r: r.get("mtime", 0), reverse=True)
    return found[:32]


def import_file(path: str, *, fmt: str = "") -> dict[str, Any]:
    src = Path(path).expanduser()
    if not src.is_file():
        return {"ok": False, "error": "file_not_found", "path": path}
    text = ""
    if src.suffix.lower() in (".csv", ".xml", ".json", ".txt"):
        text = src.read_text(encoding="utf-8", errors="replace")
    detected = fmt or _detect_format(src, text)
    if detected == "kdbx":
        return _copy_kdbx(src)
    entries: list[dict[str, Any]] = []
    if detected == "keepass_xml":
        entries = _parse_keepass_xml(text)
    elif detected == "bitwarden_json":
        entries = _parse_bitwarden_json(text)
    elif detected == "lastpass_csv":
        entries = _parse_lastpass_csv(text)
    elif detected == "onepassword_csv":
        entries = _parse_1password_csv(text)
    elif detected == "csv_generic":
        entries = _parse_csv_generic(text, source="csv_generic")
    else:
        return {"ok": False, "error": "unsupported_format", "detected": detected}
    IMPORT_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, IMPORT_DIR / src.name)
    staging = _merge_staging(entries, source_file=str(src), fmt=detected)
    csv_out = _export_staging_csv()
    vaults = _scan_legacy_vaults()
    cli_result = {}
    if vaults:
        cli_result = _try_keepassxc_cli_import(csv_out, Path(vaults[0]["path"]))
    _append_log({"action": "import_parse", "format": detected, "entries": len(entries), "file": str(src)})
    return {
        "ok": True,
        "format": detected,
        "entries_parsed": len(entries),
        "staging_count": staging.get("entry_count"),
        "csv_export": str(csv_out),
        "keepassxc_cli": cli_result,
        "hint": "Open Lock → staging entries merged; use KeePassXC import CSV if CLI unavailable",
    }


def import_scan(*, auto_copy_kdbx: bool = False) -> dict[str, Any]:
    vaults = _scan_legacy_vaults()
    copied = []
    if auto_copy_kdbx:
        for v in vaults[:8]:
            r = _copy_kdbx(Path(v["path"]))
            if r.get("ok"):
                copied.append(r.get("vault"))
    browser = _bridge_queen_browser()
    return {
        "schema": "field-lock-import/v1",
        "updated": _now(),
        "ok": True,
        "vaults_found": vaults,
        "vault_count": len(vaults),
        "staging": _load(STAGING, {}),
        "browser_bridge": browser,
        "copied_vaults": copied,
    }


def posture() -> dict[str, Any]:
    staging = _load(STAGING, {})
    return {
        "schema": "field-lock-import/v1",
        "updated": _now(),
        "ok": True,
        "staging_count": staging.get("entry_count", 0),
        "imports": (staging.get("imports") or [])[-8:],
        "formats": list((_load(DOCTRINE, {}).get("formats") or {}).keys()),
        "vault_dir": str(VAULT_DIR),
        "import_dir": str(IMPORT_DIR),
    }


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "posture").strip().lower().replace("-", "_")
    if action in ("posture", "status", "json"):
        return posture()
    if action == "scan":
        return import_scan(auto_copy_kdbx=bool(body.get("auto_copy")))
    if action == "bridge_browser":
        return _bridge_queen_browser()
    if action == "import":
        return import_file(str(body.get("path") or body.get("file") or ""), fmt=str(body.get("format") or ""))
    if action == "export_csv":
        path = _export_staging_csv()
        return {"ok": True, "csv": str(path)}
    if action == "clear_staging":
        _save(STAGING, {"entries": [], "imports": [], "updated": _now(), "entry_count": 0})
        return {"ok": True, "cleared": True}
    return {"ok": False, "error": "unknown_action", "actions": ["scan", "import", "bridge_browser", "export_csv"]}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "posture"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "scan":
        print(json.dumps(import_scan(auto_copy_kdbx="--copy" in sys.argv), ensure_ascii=False, indent=2))
        return 0
    if cmd == "import" and len(sys.argv) > 2:
        print(json.dumps(import_file(sys.argv[2]), ensure_ascii=False, indent=2))
        return 0
    if cmd == "dispatch" and len(sys.argv) > 2:
        try:
            body = json.loads(sys.argv[2])
        except json.JSONDecodeError:
            body = {}
        print(json.dumps(dispatch(body), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"usage": "field-lock-import.py [json|scan|import PATH|dispatch JSON]"}, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())