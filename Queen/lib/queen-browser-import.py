#!/usr/bin/env pythong
"""Queen Browser Import — sweep every host browser, resecure through field gates.

No prompts. Field knows: nexus-jump, gate_nav, web-compat cage, telemetry strip.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

QUEEN = Path(__file__).resolve().parents[1]
STATE = Path(os.environ.get("NEXUS_STATE_DIR", QUEEN / ".nexus-state"))
MANIFEST = STATE / "queen-browser-import.json"
IMPORT_LOG = STATE / "queen-browser-import.jsonl"

MAX_BOOKMARKS = int(os.environ.get("QUEEN_BROWSER_IMPORT_MAX_BOOKMARKS", "480"))
MAX_HISTORY = int(os.environ.get("QUEEN_BROWSER_IMPORT_MAX_HISTORY", "360"))
MAX_TABS = int(os.environ.get("QUEEN_BROWSER_IMPORT_MAX_TABS", "16"))
MAX_CREDENTIALS = int(os.environ.get("QUEEN_BROWSER_IMPORT_MAX_CREDENTIALS", "512"))
AUTO_IMPORT = os.environ.get("QUEEN_BROWSER_AUTO_IMPORT", "1") == "1"
IMPORT_CREDENTIALS = os.environ.get("QUEEN_BROWSER_IMPORT_CREDENTIALS", "1") == "1"
NO_ASK = os.environ.get("QUEEN_BROWSER_IMPORT_NO_ASK", "1") == "1"
IMPORT_DROP_DIR = STATE / "imports"
SCRUB_ROOT = STATE / "browser-scrub"
SCRUB_OTHER = SCRUB_ROOT / "other-browsers"
SCRUB_OLD = SCRUB_ROOT / "old-data"
SCRUB_PRIMARY = SCRUB_ROOT / "primary-browser"

SKIP_SCHEMES = frozenset({"javascript", "vbscript", "jar", "chrome", "about", "moz-extension"})
TELEMETRY_MARKERS = (
    "telemetry", "metrics", "google-analytics", "googletagmanager", "crashlytics",
    "sentry.io", "browser-intake", "incoming.telemetry", "data.microsoft.com",
    "firefox.com/phoenix", "ping-centre", "ads-twitter", "doubleclick.net",
    "adservice.", "analytics.", "tracking.", "beacon.",
)
_HARM_RE = re.compile(
    r"(eval\s*\(|document\.write\s*\(|onerror\s*=|onload\s*=|\.exe\b|cryptominer|coinhive)",
    re.I,
)

BROWSER_SOURCES: list[dict[str, Any]] = [
    {"id": "legacy_gecko", "label": "Legacy gecko profile (pre-Queen)", "roots": ["~/.mozilla/firefox"], "engine": "gecko"},
    {"id": "librewolf", "label": "LibreWolf", "roots": ["~/.librewolf"], "engine": "gecko"},
    {"id": "floorp", "label": "Floorp", "roots": ["~/.floorp"], "engine": "gecko"},
    {"id": "waterfox", "label": "Waterfox", "roots": ["~/.waterfox"], "engine": "gecko"},
    {"id": "chrome", "label": "Chrome", "roots": ["~/.config/google-chrome"], "engine": "chromium"},
    {"id": "chromium", "label": "Chromium", "roots": ["~/.config/chromium"], "engine": "chromium"},
    {"id": "brave", "label": "Brave", "roots": ["~/.config/BraveSoftware/Brave-Browser"], "engine": "chromium"},
    {"id": "edge", "label": "Edge", "roots": ["~/.config/microsoft-edge"], "engine": "chromium"},
    {"id": "vivaldi", "label": "Vivaldi", "roots": ["~/.config/vivaldi"], "engine": "chromium"},
    {"id": "opera", "label": "Opera", "roots": ["~/.config/opera", "~/.var/app/com.opera.Opera/config/opera"], "engine": "chromium"},
    {"id": "opera-gx", "label": "Opera GX", "roots": ["~/.config/opera-gx"], "engine": "chromium"},
    {"id": "ungoogled", "label": "Ungoogled Chromium", "roots": ["~/.config/chromium"], "engine": "chromium"},
]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def _append_log(entry: dict[str, Any]) -> None:
    try:
        STATE.mkdir(parents=True, exist_ok=True)
        with IMPORT_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _load_mod(name: str, rel: str) -> Any | None:
    path = QUEEN / "lib" / rel
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _expand(path: str) -> Path:
    return Path(os.path.expanduser(path)).resolve()


def _host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def _url_key(url: str) -> str:
    return hashlib.sha256((url or "").strip().encode("utf-8")).hexdigest()[:16]


def _sqlite_snapshot(db_path: Path) -> str | None:
    """Snapshot-copy locked browser DBs — fast read without asking the host browser."""
    if not db_path.is_file():
        return None
    fd, tmp = tempfile.mkstemp(suffix=db_path.suffix or ".sqlite")
    os.close(fd)
    try:
        shutil.copy2(db_path, tmp)
        wal = db_path.parent / f"{db_path.name}-wal"
        shm = db_path.parent / f"{db_path.name}-shm"
        if wal.is_file():
            shutil.copy2(wal, f"{tmp}-wal")
        if shm.is_file():
            shutil.copy2(shm, f"{tmp}-shm")
        return tmp
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        return None


def _sqlite_query(db_path: Path, sql: str, params: tuple = ()) -> list[tuple]:
    if not db_path.is_file():
        return []
    conn = None
    tmp: str | None = None
    try:
        tmp = _sqlite_snapshot(db_path)
        target = tmp or str(db_path)
        conn = sqlite3.connect(f"file:{target}?mode=ro", uri=True, timeout=1.0)
        cur = conn.execute(sql, params)
        return list(cur.fetchall())
    except (sqlite3.Error, OSError):
        return []
    finally:
        if conn:
            conn.close()
        if tmp:
            for suffix in ("", "-wal", "-shm"):
                try:
                    os.unlink(f"{tmp}{suffix}")
                except OSError:
                    pass


def _discover_gecko_profiles(root: Path) -> list[Path]:
    profiles_ini = root / "profiles.ini"
    found: list[Path] = []
    if profiles_ini.is_file():
        for line in profiles_ini.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line.startswith("Path="):
                rel = line.split("=", 1)[1].strip()
                p = root / rel
                if p.is_dir():
                    found.append(p)
    if not found:
        found = [p for p in root.iterdir() if p.is_dir() and (p / "places.sqlite").is_file()]
    return found


def _discover_chromium_profiles(root: Path) -> list[Path]:
    found: list[Path] = []
    default = root / "Default"
    if default.is_dir():
        found.append(default)
    for p in sorted(root.glob("Profile *")):
        if p.is_dir():
            found.append(p)
    if not found and (root / "Bookmarks").is_file():
        found.append(root)
    return found


def detect_primary_browser() -> dict[str, Any]:
    """Host default browser — we become Queen; others go to scrub/other-browsers."""
    label = ""
    browser_id = ""
    try:
        proc = subprocess.run(
            ["xdg-settings", "get", "default-web-browser"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if proc.returncode == 0:
            raw = (proc.stdout or "").strip().lower()
            for src in BROWSER_SOURCES:
                if src["id"] in raw or src["label"].lower() in raw:
                    browser_id = src["id"]
                    label = src["label"]
                    break
    except (OSError, subprocess.TimeoutExpired):
        pass
    profiles = discover_profiles()
    if not browser_id and profiles:
        top = max(profiles, key=lambda p: float(p.get("signature_mtime") or 0))
        browser_id = str(top.get("browser_id") or "")
        label = str(top.get("label") or browser_id)
    return {
        "browser_id": browser_id or "unknown",
        "label": label or "Primary",
        "queen_replaces": True,
        "profiles_seen": len(profiles),
    }


def organize_scrub(manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    """Scrub folder: primary-browser · other-browsers · old-data · imports drop."""
    SCRUB_ROOT.mkdir(parents=True, exist_ok=True)
    SCRUB_OTHER.mkdir(parents=True, exist_ok=True)
    SCRUB_OLD.mkdir(parents=True, exist_ok=True)
    SCRUB_PRIMARY.mkdir(parents=True, exist_ok=True)
    primary = detect_primary_browser()
    primary_doc = {
        "schema": "browser-scrub/primary/v1",
        "updated": _now(),
        "primary": primary,
        "manifest": manifest or _load_json(MANIFEST, {}),
        "doctrine": "Queen replaces primary host browser; other profiles archived under other-browsers/",
    }
    _save_json(SCRUB_PRIMARY / "primary.json", primary_doc)
    other_rows: list[dict[str, Any]] = []
    old_rows: list[dict[str, Any]] = []
    for prof in discover_profiles():
        row = dict(prof)
        if str(prof.get("browser_id")) == primary.get("browser_id"):
            _save_json(SCRUB_PRIMARY / f"{prof.get('browser_id')}-{Path(prof['path']).name}.json", row)
        else:
            other_rows.append(row)
            _save_json(SCRUB_OTHER / f"{prof.get('browser_id')}-{Path(prof['path']).name}.json", row)
    if IMPORT_DROP_DIR.is_dir():
        for fp in sorted(IMPORT_DROP_DIR.iterdir()):
            if fp.is_file():
                old_rows.append({"name": fp.name, "path": str(fp), "size": fp.stat().st_size})
    _save_json(SCRUB_OLD / "drop-inventory.json", {"updated": _now(), "files": old_rows})
    return {
        "ok": True,
        "scrub_root": str(SCRUB_ROOT),
        "primary": primary,
        "other_count": len(other_rows),
        "old_drop_count": len(old_rows),
    }


def discover_profiles() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for src in BROWSER_SOURCES:
        for root_s in src["roots"]:
            root = _expand(root_s)
            if not root.is_dir():
                continue
            profiles = (
                _discover_gecko_profiles(root)
                if src["engine"] == "gecko"
                else _discover_chromium_profiles(root)
            )
            for prof in profiles:
                sig = max(
                    (f.stat().st_mtime for f in prof.iterdir() if f.is_file()),
                    default=0.0,
                )
                out.append({
                    "browser_id": src["id"],
                    "label": src["label"],
                    "engine": src["engine"],
                    "path": str(prof),
                    "signature_mtime": sig,
                })
    return out


def _extract_gecko(profile: Path, *, source: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    places = profile / "places.sqlite"
    if places.is_file():
        rows = _sqlite_query(
            places,
            """
            SELECT COALESCE(b.title, ''), p.url, 'bookmark'
            FROM moz_bookmarks b
            JOIN moz_places p ON b.fk = p.id
            WHERE b.type = 1 AND p.url NOT LIKE 'place:%'
            ORDER BY b.dateAdded DESC
            LIMIT ?
            """,
            (MAX_BOOKMARKS,),
        )
        for title, url, kind in rows:
            entries.append({"title": title or url, "url": url, "kind": kind, "source": source})
        hist = _sqlite_query(
            places,
            """
            SELECT COALESCE(title, ''), url, visit_count
            FROM moz_places
            WHERE url NOT LIKE 'place:%' AND visit_count > 0
            ORDER BY last_visit_date DESC
            LIMIT ?
            """,
            (MAX_HISTORY,),
        )
        for title, url, visits in hist:
            entries.append({
                "title": title or url,
                "url": url,
                "kind": "history",
                "source": source,
                "visits": int(visits or 0),
            })
    return entries


def _walk_chromium_bookmarks(node: Any, out: list[dict[str, Any]], *, source: str, limit: int) -> None:
    if len(out) >= limit or not isinstance(node, dict):
        return
    if node.get("type") == "url" and node.get("url"):
        out.append({
            "title": node.get("name") or node.get("url"),
            "url": node["url"],
            "kind": "bookmark",
            "source": source,
        })
    for child in node.get("children") or []:
        _walk_chromium_bookmarks(child, out, source=source, limit=limit)
        if len(out) >= limit:
            return


def _chromium_secret_key(profile_root: Path) -> bytes | None:
    """Linux Chromium/Chrome — decrypt os_crypt key via libsecret."""
    local_state = profile_root / "Local State"
    if not local_state.is_file():
        parent = profile_root.parent
        if (parent / "Local State").is_file():
            local_state = parent / "Local State"
        else:
            return None
    try:
        doc = json.loads(local_state.read_text(encoding="utf-8"))
        enc_key_b64 = (doc.get("os_crypt") or {}).get("encrypted_key") or ""
        if not enc_key_b64:
            return None
        import base64

        enc_key = base64.b64decode(enc_key_b64)
        if enc_key.startswith(b"DPAPI"):
            return None
        try:
            import secretstorage  # type: ignore

            bus = secretstorage.dbus_init()
            collection = secretstorage.get_default_collection(bus)
            collection.unlock()
            passphrase = None
            for label in ("Chrome Safe Storage", "Chromium Safe Storage", "Brave Safe Storage", "Microsoft Edge Safe Storage"):
                for item in collection.search_items({"application": label}):
                    try:
                        passphrase = item.get_secret().decode("utf-8")
                        break
                    except Exception:
                        continue
                if passphrase:
                    break
            if not passphrase:
                return None
            from hashlib import pbkdf2_hmac

            key = pbkdf2_hmac("sha1", passphrase.encode("utf-8"), b"saltysalt", 1, dklen=16)
            proc = subprocess.run(
                [
                    "openssl", "enc", "-d", "-aes-128-cbc", "-K", key.hex(),
                    "-iv", "20" * 16,
                ],
                input=enc_key[3:],
                capture_output=True,
                timeout=10,
            )
            if proc.returncode == 0 and proc.stdout:
                return proc.stdout
        except ImportError:
            pass
        try:
            pw = subprocess.run(
                ["secret-tool", "lookup", "application", "chrome_libsecret_os_crypt_password_v11"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if pw.returncode == 0 and pw.stdout.strip():
                from hashlib import pbkdf2_hmac

                key = pbkdf2_hmac("sha1", pw.stdout.strip().encode("utf-8"), b"saltysalt", 1, dklen=16)
                proc = subprocess.run(
                    ["openssl", "enc", "-d", "-aes-128-cbc", "-K", key.hex(), "-iv", "20" * 16],
                    input=enc_key[3:],
                    capture_output=True,
                    timeout=10,
                )
                if proc.returncode == 0 and proc.stdout:
                    return proc.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
    except (OSError, json.JSONDecodeError, ValueError):
        return None
    return None


def _decrypt_chrome_password(blob: bytes, secret_key: bytes) -> str:
    if not blob:
        return ""
    if blob[:3] == b"v10" or blob[:3] == b"v11":
        nonce = blob[3:15]
        ct = blob[15:-16]
        tag = blob[-16:]
        proc = subprocess.run(
            ["openssl", "enc", "-d", "-aes-128-gcm", "-K", secret_key[:16].hex(), "-iv", nonce.hex()],
            input=ct + tag,
            capture_output=True,
            timeout=5,
        )
        if proc.returncode == 0:
            return proc.stdout.decode("utf-8", errors="replace")
    return ""


def _extract_chromium_logins(profile: Path, *, source: str) -> list[dict[str, Any]]:
    root = profile.parent if (profile / "Login Data").is_file() else profile
    if not (profile / "Login Data").is_file():
        return []
    secret_key = _chromium_secret_key(root)
    if not secret_key:
        return []
    rows = _sqlite_query(
        profile / "Login Data",
        """
        SELECT origin_url, username_value, password_value
        FROM logins
        WHERE username_value IS NOT NULL AND password_value IS NOT NULL
        LIMIT ?
        """,
        (MAX_CREDENTIALS,),
    )
    out: list[dict[str, Any]] = []
    for origin, username, pw_blob in rows:
        if not origin or not username or not pw_blob:
            continue
        password = _decrypt_chrome_password(pw_blob if isinstance(pw_blob, bytes) else bytes(pw_blob), secret_key)
        if not password:
            continue
        out.append({
            "origin": origin,
            "username": username,
            "password": password,
            "source": source,
            "kind": "credential",
        })
    return out


def _extract_gecko_logins(profile: Path, *, source: str) -> list[dict[str, Any]]:
    logins_json = profile / "logins.json"
    if not logins_json.is_file():
        return []
    try:
        doc = json.loads(logins_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    out: list[dict[str, Any]] = []
    for row in doc.get("logins") or []:
        if len(out) >= MAX_CREDENTIALS:
            break
        origin = row.get("hostname") or row.get("formSubmitURL") or row.get("httpRealm") or ""
        username = row.get("encryptedUsername") or row.get("username") or ""
        password = row.get("encryptedPassword") or row.get("password") or ""
        enc_type = int(row.get("encType") or 0)
        if enc_type == 0 and username and password:
            out.append({
                "origin": origin if origin.startswith("http") else f"https://{origin}",
                "username": username,
                "password": password,
                "source": source,
                "kind": "credential",
            })
    return out


def _parse_netscape_bookmarks(text: str, *, source: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("<A "):
            continue
        m_href = re.search(r'HREF="([^"]+)"', line, re.I)
        m_title = re.search(r'>([^<]+)<', line)
        if not m_href:
            continue
        url = m_href.group(1)
        title = (m_title.group(1) if m_title else url).strip()
        out.append({"title": title, "url": url, "kind": "bookmark", "source": source})
        if len(out) >= MAX_BOOKMARKS:
            break
    return out


def _parse_password_csv(text: str, *, source: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) < 2:
        return out
    header = [h.strip().lower() for h in lines[0].split(",")]
    try:
        url_i = header.index("url")
        user_i = header.index("username")
        pass_i = header.index("password")
    except ValueError:
        return out
    for line in lines[1:]:
        parts = line.split(",")
        if len(parts) <= max(url_i, user_i, pass_i):
            continue
        origin = parts[url_i].strip().strip('"')
        username = parts[user_i].strip().strip('"')
        password = parts[pass_i].strip().strip('"')
        if origin and username and password:
            out.append({
                "origin": origin,
                "username": username,
                "password": password,
                "source": source,
                "kind": "credential",
            })
        if len(out) >= MAX_CREDENTIALS:
            break
    return out


def _scan_drop_imports() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    bookmarks: list[dict[str, Any]] = []
    credentials: list[dict[str, Any]] = []
    if not IMPORT_DROP_DIR.is_dir():
        return bookmarks, credentials
    for fp in sorted(IMPORT_DROP_DIR.iterdir()):
        if not fp.is_file():
            continue
        name = fp.name.lower()
        try:
            text = fp.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        src = f"drop:{fp.name}"
        if name.endswith(".html") or name.endswith(".htm"):
            bookmarks.extend(_parse_netscape_bookmarks(text, source=src))
        elif name.endswith(".csv"):
            credentials.extend(_parse_password_csv(text, source=src))
    return bookmarks, credentials


def _import_credentials_to_vault(rows: list[dict[str, Any]]) -> dict[str, Any]:
    vault = _load_mod("queen_vault", "queen-vault.py")
    if vault is None or not hasattr(vault, "import_credentials"):
        return {"ok": False, "error": "vault_missing", "count": 0}
    return vault.import_credentials(rows)


def _extract_chromium(profile: Path, *, source: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    bookmarks = profile / "Bookmarks"
    if bookmarks.is_file():
        try:
            doc = json.loads(bookmarks.read_text(encoding="utf-8"))
            roots = doc.get("roots") or {}
            acc: list[dict[str, Any]] = []
            for key in ("bookmark_bar", "other", "synced"):
                _walk_chromium_bookmarks(roots.get(key), acc, source=source, limit=MAX_BOOKMARKS)
            entries.extend(acc[:MAX_BOOKMARKS])
        except (OSError, json.JSONDecodeError):
            pass
    history_db = profile / "History"
    if history_db.is_file():
        rows = _sqlite_query(
            history_db,
            """
            SELECT url, COALESCE(title, ''), visit_count
            FROM urls
            WHERE url IS NOT NULL AND visit_count > 0
            ORDER BY last_visit_time DESC
            LIMIT ?
            """,
            (MAX_HISTORY,),
        )
        for url, title, visits in rows:
            entries.append({
                "title": title or url,
                "url": url,
                "kind": "history",
                "source": source,
                "visits": int(visits or 0),
            })
    return entries


def _prefilter(url: str) -> tuple[bool, str]:
    u = (url or "").strip()
    if not u or len(u) > 4096:
        return False, "empty_or_oversize"
    try:
        parsed = urlparse(u)
    except Exception:
        return False, "malformed"
    scheme = (parsed.scheme or "").lower()
    if scheme in SKIP_SCHEMES:
        return False, f"skip_scheme:{scheme}"
    if scheme not in ("http", "https", "file", "queen"):
        if not u.startswith("/"):
            return False, f"unsupported_scheme:{scheme or 'none'}"
    blob = u.lower()
    if _HARM_RE.search(blob):
        return False, "harm_heuristic"
    for marker in TELEMETRY_MARKERS:
        if marker in blob:
            return False, f"telemetry:{marker}"
    return True, "ok"


def resecure_entry(entry: dict[str, Any]) -> dict[str, Any] | None:
    url = (entry.get("url") or "").strip()
    ok, reason = _prefilter(url)
    if not ok:
        return None
    gate_mod = _load_mod("queen_gate", "queen-gate.py")
    jump_mod = _load_mod("queen_nexus_jump", "queen-nexus-jump.py")
    compat_mod = _load_mod("queen_web_compat", "queen-web-compat.py")
    gate: dict[str, Any] = {}
    jump: dict[str, Any] = {}
    compat: dict[str, Any] = {}
    if jump_mod and hasattr(jump_mod, "nexus_jump"):
        try:
            jump = jump_mod.nexus_jump(url, compat_mode="auto")
        except Exception as exc:
            jump = {"ok": False, "permit": False, "error": str(exc)}
    if gate_mod and hasattr(gate_mod, "gate_nav"):
        try:
            gate = gate_mod.gate_nav(url)
        except Exception as exc:
            gate = {"permit": False, "error": str(exc)}
    if compat_mod and hasattr(compat_mod, "resolve_profile"):
        try:
            compat = compat_mod.resolve_profile(url, mode="auto")
        except Exception:
            compat = {}
    permit = bool(jump.get("permit", True)) and bool(gate.get("permit", True))
    return {
        "id": f"imp-{_url_key(url)}",
        "title": (entry.get("title") or url)[:200],
        "url": gate.get("url") or jump.get("resolved") or url,
        "kind": entry.get("kind") or "bookmark",
        "source": entry.get("source") or "unknown",
        "visits": int(entry.get("visits") or 0),
        "resecured": True,
        "permit": permit,
        "quarantined": not permit,
        "field_verdict": gate.get("queen_verdict") or jump.get("verdict") or "FIELD_HOLD",
        "iff": jump.get("iff") or gate.get("iff") or "CONTACT_HOSTILE",
        "compat_mode": compat.get("effective_mode") or compat.get("mode") or "auto",
        "compat_era": (compat.get("era") or {}).get("id") or "es2026",
        "nexus_jump": {
            "verdict": jump.get("verdict"),
            "permit": jump.get("permit"),
            "countermeasures_ready": jump.get("countermeasures_ready"),
        },
        "gate": {"permit": gate.get("permit"), "host": _host(url)},
        "prefilter": reason,
        "imported_at": _now(),
    }


def _dedupe_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for e in entries:
        key = _url_key(e.get("url") or "")
        if key in seen:
            continue
        seen.add(key)
        out.append(e)
    return out


def sweep_all(*, apply: bool = True) -> dict[str, Any]:
    t0 = time.monotonic()
    profiles = discover_profiles()
    raw: list[dict[str, Any]] = []
    credential_rows: list[dict[str, Any]] = []
    drop_bm, drop_cred = _scan_drop_imports()
    raw.extend(drop_bm)
    credential_rows.extend(drop_cred)
    for prof in profiles:
        path = Path(prof["path"])
        source = f"{prof['browser_id']}:{path.name}"
        if prof["engine"] == "gecko":
            raw.extend(_extract_gecko(path, source=source))
            if IMPORT_CREDENTIALS:
                credential_rows.extend(_extract_gecko_logins(path, source=source))
        else:
            raw.extend(_extract_chromium(path, source=source))
            if IMPORT_CREDENTIALS:
                credential_rows.extend(_extract_chromium_logins(path, source=source))
    raw = _dedupe_entries(raw)
    secured: list[dict[str, Any]] = []
    dropped = 0
    quarantined = 0
    for entry in raw:
        row = resecure_entry(entry)
        if row is None:
            dropped += 1
            continue
        if row.get("quarantined"):
            quarantined += 1
        secured.append(row)
    bookmarks = [r for r in secured if r.get("kind") == "bookmark"]
    history = sorted(
        [r for r in secured if r.get("kind") == "history"],
        key=lambda x: x.get("visits", 0),
        reverse=True,
    )
    vault_result: dict[str, Any] = {"ok": True, "added": 0, "skipped": 0, "total": 0}
    if IMPORT_CREDENTIALS and credential_rows:
        vault_result = _import_credentials_to_vault(credential_rows)
    manifest = {
        "schema": "queen-browser-import/v2",
        "updated": _now(),
        "no_ask": NO_ASK,
        "auto": AUTO_IMPORT,
        "import_credentials": IMPORT_CREDENTIALS,
        "elapsed_ms": int((time.monotonic() - t0) * 1000),
        "profiles_found": len(profiles),
        "profiles": profiles,
        "raw_count": len(raw),
        "imported_count": len(secured),
        "bookmarks": len(bookmarks),
        "history": len(history),
        "credentials": vault_result.get("total") or vault_result.get("added") or 0,
        "credentials_added": vault_result.get("added") or 0,
        "credentials_encrypted": vault_result.get("encrypted", True),
        "drop_dir": str(IMPORT_DROP_DIR),
        "dropped": dropped,
        "quarantined": quarantined,
        "permitted": len(secured) - quarantined,
        "doctrine": "field_resecure — bookmarks gated · credentials vault-encrypted · telemetry strip",
    }
    _save_json(MANIFEST, manifest)
    _append_log({**manifest, "action": "sweep"})
    result = {
        "ok": True,
        "manifest": manifest,
        "bookmarks": bookmarks,
        "history": history[:MAX_HISTORY],
        "tabs_seed": [r for r in history if r.get("permit")][:MAX_TABS],
        "vault": vault_result,
    }
    if apply:
        result["applied"] = apply_to_browser_state(bookmarks, history, manifest)
    result["primary_browser"] = detect_primary_browser()
    result["scrub"] = organize_scrub(manifest)
    return result


def apply_to_browser_state(
    bookmarks: list[dict[str, Any]],
    history: list[dict[str, Any]],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    browser = _load_mod("queen_browser", "queen-browser.py")
    if browser is None:
        return {"ok": False, "error": "queen_browser_missing"}
    doc = browser.load_state()
    existing = {_url_key(b.get("url") or "") for b in (doc.get("imported_bookmarks") or [])}
    merged_bm: list[dict[str, Any]] = list(doc.get("imported_bookmarks") or [])
    added_bm = 0
    for bm in bookmarks:
        key = _url_key(bm.get("url") or "")
        if key in existing:
            continue
        merged_bm.append({
            "id": bm.get("id") or f"imp-{key}",
            "title": bm.get("title") or bm.get("url"),
            "url": bm.get("url"),
            "source": bm.get("source"),
            "resecured": True,
            "permit": bm.get("permit"),
            "quarantined": bm.get("quarantined"),
            "field_verdict": bm.get("field_verdict"),
        })
        existing.add(key)
        added_bm += 1
    doc["imported_bookmarks"] = merged_bm[:MAX_BOOKMARKS * 4]
    doc["import_manifest"] = manifest
    tabs = list(doc.get("tabs") or [])
    tab_urls = {_url_key(t.get("url") or "") for t in tabs}
    added_tabs = 0
    for row in history:
        if not row.get("permit") or added_tabs >= MAX_TABS:
            continue
        key = _url_key(row.get("url") or "")
        if key in tab_urls:
            continue
        tab = browser._new_tab(row.get("url"), title=(row.get("title") or "Imported")[:80])
        browser._apply_compat(tab, tab["url"], {"compat_mode": row.get("compat_mode") or "auto"})
        tab["imported"] = True
        tab["source"] = row.get("source")
        tab["resecured"] = True
        tabs.append(tab)
        tab_urls.add(key)
        added_tabs += 1
    doc["tabs"] = tabs
    browser.save_state(doc)
    return {"ok": True, "bookmarks_added": added_bm, "tabs_added": added_tabs}


def should_auto_sweep() -> bool:
    if not AUTO_IMPORT:
        return False
    manifest = _load_json(MANIFEST, {})
    if not manifest.get("updated"):
        return True
    profiles = discover_profiles()
    last_sig = {
        p["path"]: p.get("signature_mtime", 0)
        for p in (manifest.get("profiles") or [])
    }
    for prof in profiles:
        if prof.get("signature_mtime", 0) > last_sig.get(prof["path"], 0) + 1.0:
            return True
    return False


def auto_sweep_if_needed() -> dict[str, Any] | None:
    if not should_auto_sweep():
        return None
    return sweep_all(apply=True)


def status_json() -> dict[str, Any]:
    manifest = _load_json(MANIFEST, {"schema": "queen-browser-import/v2"})
    vault = _load_mod("queen_vault", "queen-vault.py")
    vault_status: dict[str, Any] = {}
    if vault is not None and hasattr(vault, "vault_status"):
        try:
            vault_status = vault.vault_status()
        except Exception:
            vault_status = {"ok": False}
    return {
        "schema": "queen-browser-import/v2",
        "auto_import": AUTO_IMPORT,
        "import_credentials": IMPORT_CREDENTIALS,
        "no_ask": NO_ASK,
        "manifest": manifest,
        "profiles_available": discover_profiles(),
        "vault": vault_status,
        "drop_dir": str(IMPORT_DROP_DIR),
        "capabilities": {
            "sweep_all": True,
            "resecure": True,
            "gecko": True,
            "chromium_family": True,
            "field_gates": True,
            "telemetry_strip": True,
            "compat_cage": True,
            "credentials_vault": True,
            "bookmark_html_drop": True,
            "password_csv_drop": True,
            "primary_browser": True,
        },
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "json":
        print(json.dumps(status_json(), ensure_ascii=False))
        return 0
    if cmd in ("sweep", "import", "import_all"):
        out = sweep_all(apply="--no-apply" not in sys.argv)
        print(json.dumps(out, ensure_ascii=False))
        return 0 if out.get("ok") else 1
    if cmd == "auto":
        out = auto_sweep_if_needed()
        print(json.dumps(out or {"ok": True, "skipped": True}, ensure_ascii=False))
        return 0
    if cmd == "discover":
        print(json.dumps({"profiles": discover_profiles()}, ensure_ascii=False))
        return 0
    print(json.dumps({
        "error": "usage: queen-browser-import.py [json|sweep|import_all|auto|discover]",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())