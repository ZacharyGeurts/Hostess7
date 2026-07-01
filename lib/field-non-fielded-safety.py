#!/usr/bin/env pythong
"""Non-fielded safety — no field-in-field, no drive hotspots before whole-system field.

Doctrine:
  1. H7 / .zac / WRDT / WRZC tails must be restored (defielded) before publish or convert.
  2. Portable nexus-field snapshots stay on host mirror until underlay commit — never on TEAM drive early.
  3. Scan/convert must never pack nexus-field/, zac/, or nested portable system copies.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
SG = Path(os.environ.get("SG_ROOT", str(INSTALL.parent.parent)))
LOCK = STATE / "field-underlay-lock.json"
HOST_MIRROR_NAME = ".nexus-field-drive"

# Paths that must never be WRDT-packed (nested field hotspots)
DENY_REL_PARTS = frozenset({
    "nexus-field",
    ".nexus-field-drive",
    "zac",
    ".zac",
    ".git",
    "node_modules",
    "__pycache__",
    ".cache",
    "shadow",
    "sealed",
})

# File suffixes / names that are already field archives — never double-field
FIELD_ARCHIVE_SUFFIXES = (".zac", ".h7")
FIELD_TAIL_MAGICS = (b"WRZC", b"WRDT", b"ZAC7", b"FLD1")
H7_TEXTBOOK_MAGICS = (b"H7B\x01", b"H7B\x02")


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


def underlay_committed() -> bool:
    lock = _load(LOCK, {})
    if lock.get("committed"):
        return True
    if os.environ.get("NEXUS_FIELD_UNDERLAY_COMMITTED", "").strip().lower() in ("1", "true", "yes"):
        return True
    return False


def publish_requires_defield() -> bool:
    return os.environ.get("NEXUS_FIELD_PUBLISH_REQUIRES_DEFIELD", "1").strip().lower() not in (
        "0", "false", "no", "off",
    )


def state_redirect_allowed() -> bool:
    if os.environ.get("NEXUS_FIELD_DRIVE_STATE_REDIRECT", "").strip().lower() in ("1", "true", "yes"):
        return True
    return underlay_committed()


def host_mirror_root() -> Path:
    return INSTALL / HOST_MIRROR_NAME


def publish_field_root(selected: Path | None = None) -> Path:
    """Where nexus-field/ is written — host mirror until commit, then operator drive."""
    if not underlay_committed():
        return host_mirror_root()
    if selected and selected.is_dir():
        return selected
    return host_mirror_root()


def is_legitimate_h7_textbook(path: Path) -> bool:
    """Lossless H7B library books under textbooks/ — not WRDT/ZAC field archives."""
    try:
        head = path.read_bytes()[:4]
    except OSError:
        return False
    if head not in H7_TEXTBOOK_MAGICS:
        return False
    try:
        return "textbooks" in path.resolve().parts
    except OSError:
        return False


def is_field_archive_path(path: Path) -> bool:
    name = path.name.lower()
    if name.endswith(".zac"):
        return True
    if name.endswith(".h7"):
        if is_legitimate_h7_textbook(path):
            return False
        try:
            head = path.read_bytes()[:4]
            if head in H7_TEXTBOOK_MAGICS:
                return False
        except OSError:
            pass
        return True
    return False


def is_denied_rel_path(path: Path) -> str | None:
    try:
        parts = path.resolve().parts
    except OSError as exc:
        return str(exc)
    for part in parts:
        if part in DENY_REL_PARTS:
            return f"nested field path: {part}"
        if part.endswith(".zac"):
            return "zac archive on drive"
    if is_field_archive_path(path):
        return f"field archive: {path.name.lower()}"
    return None


def file_has_field_tail(path: Path) -> str | None:
    try:
        head = path.read_bytes()[:16]
    except OSError:
        return None
    for magic in FIELD_TAIL_MAGICS:
        if head.startswith(magic):
            return magic.decode("ascii", errors="replace")
    return None


def scan_local_field_tails(roots: list[Path] | None = None) -> dict[str, Any]:
    """Lightweight scan for disguised tails without World_Redata."""
    if roots is None:
        roots = []
        h7 = Path(os.environ.get("HOSTESS7_ROOT", str(SG / "Hostess7")))
        team = Path(os.environ.get("HOSTESS7_TEAM_FIELD", str(h7 / "cache" / "fieldstorage")))
        for p in (STATE, INSTALL / "data", team, h7 / "zac"):
            if p.is_dir():
                roots.append(p)
    hits: list[dict[str, Any]] = []
    scanned = 0
    for root in roots:
        if not root.is_dir():
            continue
        try:
            for path in root.rglob("*"):
                if not path.is_file():
                    continue
                if is_denied_rel_path(path):
                    continue
                scanned += 1
                if scanned > 8000:
                    break
                fmt = file_has_field_tail(path)
                if fmt:
                    hits.append({"path": str(path), "format": fmt})
        except OSError:
            continue
    return {
        "ok": True,
        "scanned_roots": [str(r) for r in roots],
        "field_tail_hits": len(hits),
        "hits": hits[:48],
    }


def defield_audit(*, via_converter: bool = True) -> dict[str, Any]:
    """All scan roots must have zero restorable tails before publish/convert/commit."""
    panel_path = STATE / "field-drive-converter-panel.json"
    panel = _load(panel_path, {})
    restore_totals = (panel.get("restore_totals") or {})
    restorable = int(restore_totals.get("restorable_files") or -1)

    wrdt_restorable = restorable
    if via_converter and restorable < 0:
        conv = INSTALL / "lib" / "field-drive-converter.py"
        if conv.is_file():
            try:
                proc = subprocess.run(
                    [sys.executable, str(conv), "scan-restore"],
                    capture_output=True,
                    text=True,
                    timeout=240,
                    env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
                )
                rep = json.loads(proc.stdout or "{}")
                totals = (rep.get("plan") or {}).get("totals") or {}
                wrdt_restorable = int(totals.get("restorable_files") or 0)
            except (subprocess.SubprocessError, json.JSONDecodeError, OSError):
                wrdt_restorable = -1

    local = scan_local_field_tails()
    nested_on_mirror = 0
    mirror = host_mirror_root() / "nexus-field" / "system"
    if mirror.is_dir():
        nested_on_mirror = sum(1 for _ in mirror.rglob("*") if _.is_file())

    drive_nested: list[str] = []
    if not underlay_committed():
        h7 = Path(os.environ.get("HOSTESS7_ROOT", str(SG / "Hostess7")))
        team = Path(os.environ.get("HOSTESS7_TEAM_FIELD", str(h7 / "cache" / "fieldstorage")))
        kilroy = Path(os.environ.get("KILROY_FIELD_ROOT", "/media/default/KILROY_FIELD"))
        seen: set[str] = set()
        for root in (team, h7 / "cache" / "fieldstorage", kilroy):
            try:
                resolved = root.resolve()
            except OSError:
                continue
            if resolved == host_mirror_root().resolve():
                continue
            nf = root / "nexus-field" / "system"
            if nf.is_dir():
                key = str(nf.resolve())
                if key not in seen:
                    seen.add(key)
                    drive_nested.append(key)

    defield_ok = (
        wrdt_restorable == 0
        and int(local.get("field_tail_hits") or 0) == 0
        and not drive_nested
    )
    # Host mirror (.nexus-field-drive) is the allowed pre-commit publish target — never block on mirror files.
    ok = defield_ok

    return {
        "schema": "field-non-fielded-audit/v1",
        "updated": _now(),
        "ok": ok,
        "defield_ok": defield_ok,
        "restorable_files": wrdt_restorable,
        "field_tail_hits": local.get("field_tail_hits"),
        "underlay_committed": underlay_committed(),
        "host_mirror_only": not underlay_committed(),
        "nested_mirror_system_files": nested_on_mirror,
        "nested_nexus_field_on_drives": drive_nested,
        "local_scan": local,
        "doctrine": "No fielded files or nested nexus-field on drives before whole-system field.",
    }


def gate_publish(*, op: str = "publish") -> dict[str, Any]:
    if not publish_requires_defield():
        return {"ok": True, "skipped": "defield_gate_disabled"}
    audit = defield_audit()
    if underlay_committed() and audit.get("defield_ok"):
        return {"ok": True, **audit}
    if audit.get("defield_ok"):
        return {"ok": True, **audit}
    err = "non_fielded_required"
    if audit.get("nested_nexus_field_on_drives"):
        err = "nested_field_on_drive"
    return {
        "ok": False,
        "error": err,
        "op": op,
        "doctrine": (
            "No field files on drives until whole-system field. "
            "Publish uses host mirror (.nexus-field-drive) only. "
            "Restore WRDT/WRZC/ZAC/H7 tails via Drive Converter → restore out first."
        ),
        **audit,
    }


def gate_convert(*, op: str = "convert") -> dict[str, Any]:
    audit = defield_audit()
    if audit.get("defield_ok"):
        return {"ok": True, **audit}
    return {
        "ok": False,
        "error": "defield_required_before_convert",
        "op": op,
        "doctrine": "Defield all tails first — never field-in-field.",
        **audit,
    }


def gate_commit() -> dict[str, Any]:
    audit = defield_audit()
    if not audit.get("defield_ok"):
        return {
            "ok": False,
            "error": "defield_required_before_commit",
            "doctrine": "Commit blocked until zero restorable field tails in scan roots.",
            **audit,
        }
    return {"ok": True, **audit}


def _nested_drive_field_dirs() -> list[Path]:
    """Portable nexus-field/system copies that must not live on TEAM/KILROY before commit."""
    if underlay_committed():
        return []
    h7 = Path(os.environ.get("HOSTESS7_ROOT", str(SG / "Hostess7")))
    team = Path(os.environ.get("HOSTESS7_TEAM_FIELD", str(h7 / "cache" / "fieldstorage")))
    kilroy = Path(os.environ.get("KILROY_FIELD_ROOT", "/media/default/KILROY_FIELD"))
    mirror = host_mirror_root().resolve()
    found: list[Path] = []
    seen: set[str] = set()
    for root in (team, h7 / "cache" / "fieldstorage", kilroy):
        try:
            resolved = root.resolve()
        except OSError:
            continue
        if resolved == mirror:
            continue
        nf = root / "nexus-field"
        if nf.is_dir():
            key = str(nf.resolve())
            if key not in seen:
                seen.add(key)
                found.append(nf)
    return found


def purge_nested_drive_field(*, apply: bool = False) -> dict[str, Any]:
    """Quarantine legacy nexus-field trees on drives — host mirror is the only pre-commit publish target."""
    nested = _nested_drive_field_dirs()
    if not nested:
        return {
            "ok": True,
            "purged": [],
            "doctrine": "No nested nexus-field on drives.",
            "host_mirror": str(host_mirror_root()),
        }
    if underlay_committed():
        return {
            "ok": False,
            "error": "underlay_committed",
            "doctrine": "Post-commit drive field is operator-owned — manual cleanup only.",
            "nested": [str(p) for p in nested],
        }
    quarantine = STATE / "nested-field-quarantine"
    quarantine.mkdir(parents=True, exist_ok=True)
    moved: list[dict[str, str]] = []
    for src in nested:
        stamp = _now().replace(":", "").replace("-", "")
        dst = quarantine / f"{src.parent.name}-nexus-field-{stamp}"
        if apply:
            try:
                if dst.exists():
                    shutil.rmtree(dst, ignore_errors=True)
                shutil.move(str(src), str(dst))
                moved.append({"from": str(src), "to": str(dst)})
            except OSError as exc:
                return {
                    "ok": False,
                    "error": "purge_failed",
                    "detail": str(exc),
                    "nested": [str(p) for p in nested],
                    "moved": moved,
                }
        else:
            moved.append({"from": str(src), "to": str(dst), "dry_run": True})
    audit = defield_audit()
    ok = bool(apply and audit.get("defield_ok"))
    if not apply:
        ok = False
    return {
        "ok": ok,
        "apply": apply,
        "dry_run": not apply,
        "error": None if ok else "nested_field_on_drive",
        "purged": moved,
        "nested_count": len(nested),
        "quarantine": str(quarantine),
        "defield_audit": audit,
        "doctrine": (
            "Pre-commit publish uses host mirror only (.nexus-field-drive). "
            "Run purge-nested-drive --apply to quarantine stray drive copies."
        ),
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "audit").strip().lower()
    apply = "--apply" in sys.argv
    if cmd in ("audit", "json", "defield"):
        out = defield_audit()
    elif cmd == "gate-publish":
        out = gate_publish()
    elif cmd == "gate-convert":
        out = gate_convert()
    elif cmd == "gate-commit":
        out = gate_commit()
    elif cmd in ("purge-nested", "purge-nested-drive"):
        out = purge_nested_drive_field(apply=apply)
    elif cmd == "status":
        out = {
            "underlay_committed": underlay_committed(),
            "host_mirror": str(host_mirror_root()),
            "publish_requires_defield": publish_requires_defield(),
            "state_redirect_allowed": state_redirect_allowed(),
        }
    else:
        print(json.dumps({
            "error": "usage: field-non-fielded-safety.py "
            "[audit|gate-publish|gate-convert|gate-commit|purge-nested-drive|status] [--apply]",
        }))
        return 2
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())