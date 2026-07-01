#!/usr/bin/env pythong
"""Field Drive System — whole NEXUS on portable field storage; talk with minimal browser.

Layout on HOSTESS7 TEAM fieldstorage:
  nexus-field/
    manifest.json
    system/     portable install snapshot (lib, panel, data, config)
    state/      live runtime state when drive is primary
    talk/inbox  command drops
    talk/outbox responses
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))


def _host_state_dir() -> Path:
    """Live state source for publish/sync — prefer writable NEXUS_STATE_DIR over prod paths."""
    explicit = os.environ.get("NEXUS_HOST_STATE_DIR", "").strip()
    if explicit:
        return Path(explicit)
    env_raw = os.environ.get("NEXUS_STATE_DIR", "").strip()
    env_state = Path(env_raw) if env_raw else None
    canonical = Path("/var/lib/nexus-shield")
    if env_state and _safe_is_dir(env_state):
        try:
            if os.access(env_state, os.R_OK | os.W_OK):
                return env_state
        except OSError:
            pass
    if canonical.is_dir():
        try:
            if os.access(canonical, os.R_OK):
                return canonical
        except OSError:
            pass
    if env_state:
        return env_state
    return canonical
def _sg_paths():
    import importlib.util
    py = Path(__file__).resolve().parent / "sg_paths.py"
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location("sg_paths", py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_sp = _sg_paths()
HOSTESS7_ROOT = Path(os.environ.get("HOSTESS7_ROOT", str(_sp.hostess7_root() if _sp else "Hostess7")))
HOSTESS7_TEAM = Path(os.environ.get("HOSTESS7_TEAM_FIELD", str(_sp.hostess7_team_field() if _sp else HOSTESS7_ROOT / "cache" / "fieldstorage")))
VERSION = os.environ.get("NEXUS_VERSION", "7.5.0")

NEXUS_FIELD_NAME = "nexus-field"
# Whole system = GUI (panel + assets). Backend lib stays on host; GUI snapshot travels on drive.
GUI_DIRS = ("panel", "assets")
SYSTEM_DIRS = ("lib", "panel", "data", "config", "bin", "assets")
TOOL_DIRS = ("lib/bin",)
SELECTED_FILE = "field-drive-selected.json"
STATE_GLOBS = (
    "threat-panel.json",
    "field-*-panel.json",
    "field-outside-talk-*.jsonl",
    "field-outside-talk-*.json",
    "firewall*.tsv",
    "firewall.state",
    "vigil.state",
    "connection-intent.json",
    "gatekeeper-enforce.sig",
    "packet-field.json",
    "packet-field.ring.jsonl",
    "settings.override",
    "nexus-trusted.jsonl",
    "field-hostile.tsv",
)


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        import importlib.util
        _p = Path(__file__).resolve().parent / "sovereign-clock.py"
        _s = importlib.util.spec_from_file_location("sovereign_clock", _p)
        if not _s or not _s.loader:
            raise ImportError("sovereign-clock.py missing")
        _SOVEREIGN_CLOCK_MOD = importlib.util.module_from_spec(_s)
        _s.loader.exec_module(_SOVEREIGN_CLOCK_MOD)
    return _SOVEREIGN_CLOCK_MOD.utc_z()


_SOVEREIGN_CLOCK_MOD = None



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


def _selected_drive_path() -> Path | None:
    for base in (_host_state_dir(), HOSTESS7_TEAM / NEXUS_FIELD_NAME / "state"):
        doc = _load_json(base / SELECTED_FILE, {})
        raw = str(doc.get("path") or "").strip()
        if raw:
            p = Path(raw)
            if p.is_dir():
                return p
    return None


def _safe_is_dir(path: Path) -> bool:
    try:
        return path.is_dir()
    except OSError:
        return False


def _safe_is_file(path: Path) -> bool:
    try:
        return path.is_file()
    except OSError:
        return False


def _safe_glob_count(root: Path, pattern: str) -> int:
    try:
        if not _safe_is_dir(root):
            return 0
        return len(list(root.glob(pattern)))
    except OSError:
        return 0


def field_roots() -> list[Path]:
    """Single live field-tech root first — no redundant Hostess7 cache mirrors."""
    roots: list[Path] = []
    mirror = INSTALL / ".nexus-field-drive"
    if _safe_is_dir(mirror):
        roots.append(mirror)
    sel = _selected_drive_path()
    if sel and _safe_is_dir(sel) and sel not in roots:
        roots.append(sel)
    if _safe_is_dir(HOSTESS7_TEAM) and HOSTESS7_TEAM not in roots:
        roots.append(HOSTESS7_TEAM)
    state_store = _host_state_dir() / "field-storage"
    if _safe_is_dir(state_store) and state_store not in roots:
        roots.append(state_store)
    media = Path("/media")
    if _safe_is_dir(media):
        try:
            mounts = sorted(media.iterdir())
        except OSError:
            mounts = []
        for mount in mounts:
            if not _safe_is_dir(mount):
                continue
            for candidate in (
                mount / "fieldstorage",
                mount / "HOSTESS7_TEAM" / "fieldstorage",
            ):
                if _safe_is_dir(candidate) and candidate not in roots:
                    roots.append(candidate)
    return roots or [HOSTESS7_TEAM]


def discover_all_drives() -> list[dict[str, Any]]:
    """All mounted field drives — NEXUS GUI can interface with any of them."""
    seen: set[str] = set()
    drives: list[dict[str, Any]] = []

    def _add(root: Path, label: str, source: str) -> None:
        try:
            resolved = str(root.resolve())
        except OSError:
            resolved = str(root)
        if not _safe_is_dir(root) or resolved in seen:
            return
        seen.add(resolved)
        nf = root / NEXUS_FIELD_NAME
        gui_on_drive = _safe_is_file(nf / "system" / "panel" / "threat-panel.html")
        drives.append({
            "id": hashlib.sha256(resolved.encode()).hexdigest()[:12],
            "path": resolved,
            "label": label,
            "source": source,
            "has_brain": _safe_is_dir(root / "brain"),
            "has_nexus_field": _safe_is_dir(nf),
            "has_gui_on_drive": gui_on_drive,
            "nexus_field": str(nf) if _safe_is_dir(nf) else "",
            "textbooks_h7": _safe_glob_count(root / "textbooks", "**/*.h7"),
            "gui_entry": "/field",
            "talk_entry": "/field-talk",
        })

    for root in field_roots():
        name = root.name
        if "HOSTESS7" in str(root) or root == HOSTESS7_TEAM:
            _add(root, "HOSTESS7 TEAM", "team")
        elif "cache" in str(root):
            _add(root, "Hostess7 cache", "cache")
        elif "field-storage" in str(root):
            _add(root, "Local mirror", "state")
        else:
            _add(root, name or "fieldstorage", "discovered")

    sel = _selected_drive_path()
    active_id = ""
    if sel:
        try:
            active_id = hashlib.sha256(str(sel.resolve()).encode()).hexdigest()[:12]
        except OSError:
            pass
    for d in drives:
        d["selected"] = d["id"] == active_id
    return drives


def _non_fielded():
    spec = importlib.util.spec_from_file_location(
        "field_non_fielded_safety", INSTALL / "lib" / "field-non-fielded-safety.py",
    )
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def primary_field_root() -> Path:
    sel = _selected_drive_path()
    if sel:
        return sel
    for root in field_roots():
        if _safe_is_file(root / NEXUS_FIELD_NAME / "manifest.json"):
            return root
        if _safe_is_dir(root / "brain"):
            return root
    return HOSTESS7_TEAM


def publish_field_root() -> Path:
    """Host mirror until underlay commit — never drop field files on TEAM drive early."""
    nf = _non_fielded()
    if nf:
        return nf.publish_field_root(_selected_drive_path())
    return INSTALL / ".nexus-field-drive"


def select_drive(path: str) -> dict[str, Any]:
    raw = str(path or "").strip()
    if not raw:
        return {"ok": False, "error": "missing_path"}
    target = Path(raw)
    if not target.is_dir():
        return {"ok": False, "error": "not_a_directory", "path": raw}
    doc = {
        "path": str(target.resolve()),
        "selected_at": _now(),
        "label": target.name,
    }
    _save_json(_host_state_dir() / SELECTED_FILE, doc)
    nf = target / NEXUS_FIELD_NAME / "state"
    if nf.is_dir():
        _save_json(nf / SELECTED_FILE, doc)
    return {"ok": True, **doc, "drives": discover_all_drives()}


def nexus_field_base(*, for_publish: bool = False) -> Path:
    root = publish_field_root() if for_publish else primary_field_root()
    return root / NEXUS_FIELD_NAME


def system_dir(*, for_publish: bool = False) -> Path:
    return nexus_field_base(for_publish=for_publish) / "system"


def state_dir(*, for_publish: bool = False) -> Path:
    return nexus_field_base(for_publish=for_publish) / "state"


def talk_inbox() -> Path:
    return nexus_field_base() / "talk" / "inbox"


def talk_outbox() -> Path:
    return nexus_field_base() / "talk" / "outbox"


def ensure_layout(*, for_publish: bool = False) -> Path:
    base = nexus_field_base(for_publish=for_publish)
    for sub in ("system", "state", "talk/inbox", "talk/outbox", "run"):
        (base / sub).mkdir(parents=True, exist_ok=True)
    return base


def drive_mounted() -> bool:
    root = primary_field_root()
    return root.is_dir() and os.access(root, os.W_OK | os.R_OK)


def field_drive_active() -> bool:
    nf = _non_fielded()
    if nf and not nf.state_redirect_allowed() and os.environ.get("NEXUS_FIELD_DRIVE_ACTIVE") != "1":
        return False
    return os.environ.get("NEXUS_FIELD_DRIVE_ACTIVE") == "1" or (
        state_dir().is_dir() and os.environ.get("NEXUS_FIELD_DRIVE", "1") == "1"
        and (nexus_field_base() / "active.json").is_file()
    )


def _file_sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""


def _count_tree(root: Path) -> tuple[int, int]:
    files = 0
    total = 0
    if not root.is_dir():
        return 0, 0
    for p in root.rglob("*"):
        if p.is_file():
            files += 1
            try:
                total += p.stat().st_size
            except OSError:
                pass
    return files, total


def _ignore_copy(_dir: str, names: list[str]) -> set[str]:
    skip = {
        ".git", "__pycache__", ".pyc", "node_modules", ".tmp",
        "profile-ammoos-desktop", "profile-queen", "profile-field",
    }
    return {
        n for n in names
        if n in skip or n.endswith(".pyc") or n.startswith("profile-")
    }


def _chmod_writable(path: Path) -> None:
    try:
        path.chmod(path.stat().st_mode | 0o200)
    except OSError:
        pass


def _safe_copy_file(src: str, dst: str) -> None:
    """Copy one file; overwrite read-only destinations, skip unreadable sources."""
    src_p, dst_p = Path(src), Path(dst)
    try:
        if not src_p.is_file() or not os.access(src_p, os.R_OK):
            return
        dst_p.parent.mkdir(parents=True, exist_ok=True)
        if dst_p.exists():
            _chmod_writable(dst_p)
        shutil.copy2(src, dst)
    except OSError:
        pass


def _safe_copytree(src: Path, dst: Path) -> None:
    """Best-effort tree copy — skip dangling symlinks, locks, and permission failures."""
    if dst.exists():
        for existing in dst.rglob("*"):
            if existing.is_file():
                _chmod_writable(existing)
    try:
        shutil.copytree(
            src,
            dst,
            dirs_exist_ok=True,
            ignore=_ignore_copy,
            ignore_dangling_symlinks=True,
            copy_function=_safe_copy_file,
        )
    except shutil.Error as exc:
        pending = list(exc.args[0]) if exc.args else []
        for src_p, dst_p, msg in pending:
            if "Permission denied" not in str(msg):
                raise
            try:
                _chmod_writable(Path(dst_p))
                _safe_copy_file(str(src_p), str(dst_p))
            except OSError:
                pass


def _sync_state_globs(host_state: Path, st_dst: Path) -> list[str]:
    """Mirror live state files onto field mirror — skip unreadable prod-only paths."""
    state_files: list[str] = []
    if not _safe_is_dir(host_state):
        return state_files
    st_dst.mkdir(parents=True, exist_ok=True)
    for pattern in STATE_GLOBS:
        try:
            matches = list(host_state.glob(pattern))
        except OSError:
            continue
        for src in matches:
            if not _safe_is_file(src):
                continue
            try:
                if not os.access(src, os.R_OK):
                    continue
            except OSError:
                continue
            dst = st_dst / src.name
            before = dst.stat().st_size if _safe_is_file(dst) else -1
            _safe_copy_file(str(src), str(dst))
            if _safe_is_file(dst):
                try:
                    after = dst.stat().st_size
                except OSError:
                    after = -1
                if after >= 0 and (before != after or before < 0):
                    state_files.append(src.name)
    return state_files


def _gate_publish(op: str) -> dict[str, Any] | None:
    nf = _non_fielded()
    if not nf:
        return None
    gate = nf.gate_publish(op=op)
    return gate if not gate.get("ok") else None


def publish_tools(*, full: bool = False) -> dict[str, Any]:
    """Copy ported field tools (lib/bin) onto field drive — no system deps."""
    blocked = _gate_publish("publish_tools")
    if blocked:
        return blocked
    base = ensure_layout(for_publish=True)
    tools_dst = base / "tools"
    if full and tools_dst.exists():
        shutil.rmtree(tools_dst, ignore_errors=True)
    tools_dst.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for rel in TOOL_DIRS:
        src = INSTALL / rel
        if not src.is_dir():
            continue
        for item in src.iterdir():
            if not item.is_file():
                continue
            dst = tools_dst / item.name
            shutil.copy2(item, dst)
            try:
                dst.chmod(0o755)
            except OSError:
                pass
            copied.append(item.name)
    reg_src = INSTALL / "data" / "field-tools-registry.json"
    if reg_src.is_file():
        shutil.copy2(reg_src, base / "field-tools-registry.json")
    return {
        "ok": bool(copied),
        "artifact": "tools",
        "tools_dir": str(tools_dst),
        "copied": copied,
        "count": len(copied),
    }


def publish_gui(*, full: bool = False) -> dict[str, Any]:
    """Publish whole GUI (panel + assets) to field drive — the portable system face."""
    blocked = _gate_publish("publish_gui")
    if blocked:
        return blocked
    base = ensure_layout(for_publish=True)
    sys_dst = system_dir(for_publish=True)
    gui_dst = sys_dst / "panel"
    assets_dst = sys_dst / "assets"
    copied_gui: list[str] = []
    for name in GUI_DIRS:
        src = INSTALL / name
        if not src.is_dir():
            continue
        dst = sys_dst / name
        if full and dst.exists():
            shutil.rmtree(dst, ignore_errors=True)
        _safe_copytree(src, dst)
        copied_gui.append(name)
    gui_ok = (gui_dst / "threat-panel.html").is_file()
    return {
        "ok": gui_ok,
        "artifact": "gui",
        "gui_panel": str(gui_dst / "threat-panel.html"),
        "gui_assets": str(assets_dst),
        "copied_gui": copied_gui,
        "gui_files": _count_tree(gui_dst)[0] + _count_tree(assets_dst)[0],
    }


def publish_system(*, full: bool = False) -> dict[str, Any]:
    """Mirror GUI + supporting install + state onto field drive."""
    blocked = _gate_publish("publish_system")
    if blocked:
        return blocked
    base = ensure_layout(for_publish=True)
    sys_dst = system_dir(for_publish=True)
    st_dst = state_dir(for_publish=True)

    gui_result = publish_gui(full=full)
    tools_result = publish_tools(full=full)

    copied_dirs: list[str] = []
    for name in SYSTEM_DIRS:
        src = INSTALL / name
        if not src.is_dir() and name != "bin":
            continue
        dst = sys_dst / name
        if full and dst.exists():
            shutil.rmtree(dst, ignore_errors=True)
        if src.is_dir():
            _safe_copytree(src, dst)
            copied_dirs.append(name)
        elif src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied_dirs.append(name)

    for extra in ("MANIFEST.sha256", "nexus.sh", "genius_shield.sh"):
        src = INSTALL / extra
        if src.is_file():
            shutil.copy2(src, sys_dst / extra)

    state_files = _sync_state_globs(_host_state_dir(), st_dst)

    sys_files, sys_bytes = _count_tree(sys_dst)
    st_files, st_bytes = _count_tree(st_dst)

    nf = _non_fielded()
    manifest = {
        "schema": "field-drive-system/v1",
        "updated": _now(),
        "version": VERSION,
        "hostess_version": os.environ.get("HOSTESS_VERSION", "7"),
        "install_root": str(INSTALL),
        "field_root": str(publish_field_root()),
        "host_mirror_only": bool(nf and not nf.underlay_committed()),
        "non_fielded_gate": bool(nf and nf.publish_requires_defield()),
        "nexus_field": str(base),
        "system_dir": str(sys_dst),
        "state_dir": str(st_dst),
        "system_files": sys_files,
        "system_bytes": sys_bytes,
        "state_files": st_files,
        "state_bytes": st_bytes,
        "copied_dirs": copied_dirs,
        "state_synced": state_files,
        "whole_system": "gui",
        "gui": gui_result,
        "tools": tools_result,
        "tools_dir": tools_result.get("tools_dir"),
        "gui_url": "/field",
        "talk_url": "/field-talk",
        "talk_api": "/api/field-drive/talk",
        "drives": discover_all_drives(),
    }
    _save_json(base / "manifest.json", manifest)
    _save_json(base / "active.json", {
        "active": True,
        "since": _now(),
        "state_dir": str(st_dst),
        "primary": True,
    })
    _save_json(base / "run" / "last-publish.json", manifest)
    return {"ok": True, **manifest}


def sync_state_only() -> dict[str, Any]:
    """Lightweight cycle — state files only (host mirror until underlay commit)."""
    base = ensure_layout(for_publish=True)
    st_dst = state_dir(for_publish=True)
    st_dst.mkdir(parents=True, exist_ok=True)
    state_files = _sync_state_globs(_host_state_dir(), st_dst)
    return {"ok": True, "synced": state_files, "count": len(state_files), "ts": _now()}


def _outside_mod() -> Any:
    spec = importlib.util.spec_from_file_location("field_outside_talk", INSTALL / "lib" / "field-outside-talk.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _env_with_field_state() -> dict[str, str]:
    env = os.environ.copy()
    st = state_dir()
    if st.is_dir():
        env["NEXUS_FIELD_DRIVE_STATE"] = str(st)
        env["NEXUS_STATE_DIR"] = str(st)
    return env


def talk(payload: dict[str, Any]) -> dict[str, Any]:
    """Unified talk — CLI, inbox files, minimal browser."""
    op = str(payload.get("op") or payload.get("action") or "status").strip().lower()
    ensure_layout()

    if op in ("status", "ping"):
        return build_status()

    if op in ("publish", "sync_system", "sync"):
        full = payload.get("full") in (True, 1, "1", "true", "yes")
        if op == "sync" and not full:
            return sync_state_only()
        return publish_system(full=full)

    if op in ("connect", "outside_connect"):
        os.environ.update(_env_with_field_state())
        mod = _outside_mod()
        result = mod.outside_connect(payload)
        _write_outbox(result, op)
        sync_state_only()
        return result

    if op == "probe":
        os.environ.update(_env_with_field_state())
        mod = _outside_mod()
        result = mod.outside_probe(payload)
        _write_outbox(result, op)
        return result

    if op == "disconnect":
        os.environ.update(_env_with_field_state())
        mod = _outside_mod()
        return mod.outside_disconnect(payload)

    if op == "process_inbox":
        return process_inbox()

    if op in ("select_drive", "select"):
        return select_drive(str(payload.get("path") or payload.get("drive") or ""))

    if op == "drives":
        return {"ok": True, "drives": discover_all_drives()}

    if op == "publish_gui":
        return publish_gui(full=payload.get("full") in (True, 1, "1", "true", "yes"))

    if op in ("publish_tools", "tools"):
        return publish_tools(full=payload.get("full") in (True, 1, "1", "true", "yes"))

    if op == "hardware":
        spec = importlib.util.spec_from_file_location(
            "field_hardware_probe", INSTALL / "lib" / "field-hardware-probe.py",
        )
        mod = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(mod)
        return mod.probe_all()

    return {"ok": False, "error": "unknown_op", "op": op}


def _write_outbox(result: dict[str, Any], op: str) -> None:
    oid = str(result.get("session_id") or uuid.uuid4())[:16]
    row = {"id": oid, "op": op, "ts": _now(), **result}
    _save_json(talk_outbox() / f"{oid}.json", row)


def process_inbox() -> dict[str, Any]:
    inbox = talk_inbox()
    processed: list[dict[str, Any]] = []
    for path in sorted(inbox.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            path.unlink(missing_ok=True)
            continue
        result = talk(payload)
        processed.append({"file": path.name, "ok": result.get("ok"), "op": payload.get("op")})
        done = inbox.parent / "processed"
        done.mkdir(exist_ok=True)
        try:
            path.rename(done / path.name)
        except OSError:
            path.unlink(missing_ok=True)
    return {"ok": True, "processed": processed, "count": len(processed)}


def build_status() -> dict[str, Any]:
    base = nexus_field_base()
    manifest = _load_json(base / "manifest.json", {})
    active = _load_json(base / "active.json", {})
    outside_panel: dict[str, Any] = {}
    opanel = state_dir() / "field-outside-talk-panel.json"
    if _safe_is_file(opanel):
        outside_panel = _load_json(opanel, {})
    threat = _load_json(state_dir() / "threat-panel.json", {})
    host_state = _host_state_dir()
    if not threat and _safe_is_file(host_state / "threat-panel.json"):
        threat = _load_json(host_state / "threat-panel.json", {})

    nf = _non_fielded()
    audit = nf.defield_audit() if nf else {}
    index_now: dict[str, Any] = {}
    timeshift: dict[str, Any] = {}
    try:
        import importlib.util
        for mod_name, rel in (
            ("field_drive_indexer", "field-drive-indexer.py"),
            ("field_timeshift", "field-timeshift.py"),
        ):
            py = Path(__file__).resolve().parent / rel
            if not py.is_file():
                continue
            spec = importlib.util.spec_from_file_location(mod_name, py)
            if not spec or not spec.loader:
                continue
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if mod_name == "field_drive_indexer" and hasattr(mod, "now_snapshot"):
                index_now = mod.now_snapshot()
            if mod_name == "field_timeshift" and hasattr(mod, "status"):
                timeshift = mod.status()
    except Exception:
        pass
    return {
        "schema": "field-drive-system/v1",
        "updated": _now(),
        "version": VERSION,
        "drive_mounted": drive_mounted(),
        "field_root": str(primary_field_root()),
        "publish_root": str(publish_field_root()),
        "host_mirror_only": bool(nf and not nf.underlay_committed()),
        "non_fielded_audit": audit,
        "nexus_field": str(base),
        "active": bool(active.get("active")),
        "whole_system": manifest.get("whole_system") or "gui",
        "whole_system_on_drive": bool(manifest.get("gui") or manifest.get("whole_system")),
        "gui_on_drive": bool((manifest.get("gui") or {}).get("ok")),
        "manifest": manifest,
        "drives": discover_all_drives(),
        "selected_drive": _load_json(_host_state_dir() / SELECTED_FILE, {}),
        "gui_url": "/field",
        "talk_url": "/field-talk",
        "talk": {
            "inbox": str(talk_inbox()),
            "outbox": str(talk_outbox()),
            "inbox_pending": len(list(talk_inbox().glob("*.json"))) if talk_inbox().is_dir() else 0,
        },
        "state_dir": str(state_dir()) if state_dir().is_dir() else str(_host_state_dir()),
        "host_state_dir": str(_host_state_dir()),
        "firewall": threat.get("firewall") or outside_panel.get("firewall"),
        "field_outside_talk": {
            "tools": len(outside_panel.get("tools") or []),
            "sessions": len(outside_panel.get("recent_sessions") or []),
            "asm_ready": (outside_panel.get("hardening") or {}).get("asm_ready"),
        },
        "panel_url": f"http://127.0.0.1:{os.environ.get('NEXUS_THREAT_PANEL_PORT', '9477')}/field",
        "talk_panel_url": f"http://127.0.0.1:{os.environ.get('NEXUS_THREAT_PANEL_PORT', '9477')}/field-talk",
        "field_index": index_now,
        "timeshift": timeshift,
    }


def _panel_cache_path() -> Path:
    sd = state_dir()
    if _safe_is_dir(sd):
        try:
            if os.access(sd, os.W_OK):
                return sd / "field-drive-panel.json"
        except OSError:
            pass
    host = _host_state_dir()
    if _safe_is_dir(host):
        try:
            if os.access(host, os.W_OK):
                return host / "field-drive-panel.json"
        except OSError:
            pass
    tmp = Path(os.environ.get("TMPDIR", "/tmp")) / "nexus-field-drive-panel.json"
    return tmp


def build_panel() -> dict[str, Any]:
    doc = build_status()
    try:
        _save_json(_panel_cache_path(), doc)
    except OSError:
        pass
    return doc


def panel_json() -> dict[str, Any]:
    """Always live status — no stale disk cache mirror."""
    return build_status()


def main() -> int:
    import sys

    if len(sys.argv) < 2:
        print("usage: field-drive-system.py [status|publish|sync|talk JSON|inbox|json|build]", file=sys.stderr)
        return 1
    cmd = sys.argv[1]
    if cmd == "status":
        print(json.dumps(build_status(), ensure_ascii=False))
        return 0
    if cmd == "publish":
        full = "--full" in sys.argv
        print(json.dumps(publish_system(full=full), ensure_ascii=False))
        return 0
    if cmd == "sync":
        print(json.dumps(sync_state_only(), ensure_ascii=False))
        return 0
    if cmd == "inbox":
        print(json.dumps(process_inbox(), ensure_ascii=False))
        return 0
    if cmd == "build":
        print(json.dumps(build_panel(), ensure_ascii=False))
        return 0
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    if cmd == "talk":
        raw = sys.argv[2] if len(sys.argv) > 2 else "{}"
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {}
        print(json.dumps(talk(payload), ensure_ascii=False))
        return 0
    print("usage: field-drive-system.py [status|publish|sync|talk JSON|inbox|json|build]", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())