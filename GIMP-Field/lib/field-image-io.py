#!/usr/bin/env pythong
"""AmmoOS Image field I/O — WRDT/WRZC/ZAC7/FLD/plate decode with CPU and RTX paths."""
from __future__ import annotations

import importlib.util
import json
import os
import struct
import sys
import tempfile
import zlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

SG = Path(os.environ.get("SG_ROOT", Path(__file__).resolve().parents[2]))
WR = Path(os.environ.get("WORLD_REDATA_ROOT", SG / "World_Redata"))
_SG_PATHS_LIB = Path(__file__).resolve().parents[2] / "lib"
if str(_SG_PATHS_LIB) not in sys.path:
    sys.path.insert(0, str(_SG_PATHS_LIB))
from sg_paths import grok16_root

GROK16 = grok16_root()
RTX_CACHE = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "ammoos-rtx-gate"
RTX_PERMIT_FILE = RTX_CACHE / "permit"

WRDT_MAGIC = b"WRDT"
WRZC_MAGIC = b"WRZC"
ZAC7_MAGIC = b"ZAC7"
HEADER = 52


def _env_rtx_force() -> bool:
    return os.environ.get("G16_RTX_GATE_FORCE", "").lower() in ("1", "true", "yes")


def _cache_rtx_permit() -> bool:
    return RTX_PERMIT_FILE.is_file()


def _write_rtx_permit(permit: bool) -> None:
    RTX_CACHE.mkdir(parents=True, exist_ok=True)
    if permit:
        RTX_PERMIT_FILE.write_text("1\n", encoding="utf-8")
    elif RTX_PERMIT_FILE.is_file():
        RTX_PERMIT_FILE.unlink()


def _gate_rtx_permit() -> bool:
    gate = GROK16 / "forge" / "rtx_gate.py"
    if not gate.is_file():
        return False
    try:
        spec = importlib.util.spec_from_file_location("rtx_gate", gate)
        if not spec or not spec.loader:
            return False
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return bool(mod.profile_allowed("queen_rtx"))
    except Exception:
        return False


def _rtx_permit(*, sync_cache: bool = True) -> bool:
    if _env_rtx_force():
        if sync_cache:
            _write_rtx_permit(True)
        return True
    if _cache_rtx_permit():
        return True
    permit = _gate_rtx_permit()
    if sync_cache:
        _write_rtx_permit(permit)
    return permit


def active_profile() -> str:
    return "queen_rtx" if _rtx_permit() else "field_opt"


def _sha256(data: bytes) -> bytes:
    import hashlib
    return hashlib.sha256(data).digest()


def sniff(blob: bytes) -> str:
    if len(blob) < 4:
        return "unknown"
    m = blob[:4]
    if m == WRDT_MAGIC:
        return "wrdt"
    if m == WRZC_MAGIC:
        return "wrzc"
    if m == ZAC7_MAGIC:
        return "zac7"
    if blob[:2] == b"\x89P":
        return "png"
    if blob[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if blob[:4] == b"RIFF" and len(blob) > 11 and blob[8:12] == b"WEBP":
        return "webp"
    return "unknown"


def _wrdt_unpack_cpu(blob: bytes) -> bytes:
    if blob[:4] != WRDT_MAGIC or len(blob) < HEADER:
        raise ValueError("not_wrdt")
    ver, method, _flags, orig, pay_len = struct.unpack_from("<BBHQI", blob, 4)
    if ver != 1:
        raise ValueError("bad_wrdt_version")
    digest = blob[20:HEADER]
    payload = blob[HEADER : HEADER + pay_len]
    if method == 0:
        body = payload
    elif method == 1:
        body = zlib.decompress(payload)
    else:
        raise ValueError(f"bad_method_{method}")
    if len(body) != orig or _sha256(body) != digest:
        raise ValueError("wrdt_integrity_fail")
    return body


def _wrdt_unpack_rtx(blob: bytes) -> bytes:
    """Batch-friendly path — parallel digest verify + single-shot zlib."""
    if blob[:4] != WRDT_MAGIC or len(blob) < HEADER:
        raise ValueError("not_wrdt")
    ver, method, _flags, orig, pay_len = struct.unpack_from("<BBHQI", blob, 4)
    if ver != 1:
        raise ValueError("bad_wrdt_version")
    digest = blob[20:HEADER]
    payload = blob[HEADER : HEADER + pay_len]
    if method == 0:
        body = payload
    elif method == 1:
        body = zlib.decompress(payload, wbits=15)
    else:
        raise ValueError("bad_method")
    if len(body) != orig:
        raise ValueError("wrdt_integrity_fail")
    with ThreadPoolExecutor(max_workers=min(4, os.cpu_count() or 2)) as pool:
        fut = pool.submit(_sha256, body)
        if fut.result() != digest:
            raise ValueError("wrdt_integrity_fail")
    return body


def _wrdt_wrap(method: int, raw: bytes, payload: bytes) -> bytes:
    return (
        WRDT_MAGIC
        + struct.pack("<BBHQI", 1, method, 0, len(raw), len(payload))
        + _sha256(raw)
        + payload
    )


def pack_wrdt(raw: bytes, *, min_gain: float = 1.0, force: bool = False) -> bytes | None:
    if not raw:
        return None
    core = WR / "redata" / "core.py"
    if core.is_file() and not force:
        wr_root = str(WR)
        if wr_root not in sys.path:
            sys.path.insert(0, wr_root)
        spec = importlib.util.spec_from_file_location("redata_core", core)
        mod = importlib.util.module_from_spec(spec)
        assert spec and spec.loader and spec.name
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
        packed = mod.redata_pack(raw, min_gain=min_gain)
        if packed:
            return packed

    candidates: list[tuple[int, bytes]] = [(0, raw)]
    if len(raw) >= 16:
        z = zlib.compress(raw, 1)
        if len(z) < len(raw):
            candidates.append((1, z))
    method, payload = min(candidates, key=lambda item: len(item[1]))
    wrapped = _wrdt_wrap(method, raw, payload)
    if not force and len(wrapped) >= len(raw) * min_gain:
        return None
    return wrapped


def export_wrdt(inner_path: str, out_path: str) -> dict[str, Any]:
    inner = Path(inner_path)
    out = Path(out_path)
    raw = inner.read_bytes()
    packed = pack_wrdt(raw, force=True)
    out.write_bytes(packed)
    return {
        "ok": True,
        "kind": "wrdt",
        "profile": active_profile(),
        "inner": sniff(raw),
        "out": str(out),
        "bytes": len(packed),
    }


def unpack_field(blob: bytes, *, path: str = "") -> dict[str, Any]:
    kind = sniff(blob)
    if path:
        low = path.lower()
        if low.endswith(".fld"):
            kind = "fld"
        elif "plate.json" in low or low.endswith("-plate.json"):
            kind = "plate"
        elif low.endswith(".ammo") or (low.endswith(".obj") and b"mtllib" not in blob[:4096].lower()):
            kind = "ammo"
        elif low.endswith(".h7snap") or low.endswith(".field-snap"):
            kind = "h7"

    rtx = _rtx_permit()
    profile = "queen_rtx" if rtx else "field_opt"

    try:
        if kind == "wrdt":
            body = _wrdt_unpack_rtx(blob) if rtx else _wrdt_unpack_cpu(blob)
            inner = sniff(body)
            return {"ok": True, "kind": "wrdt", "profile": profile, "inner": inner, "body": body, "size": len(body)}
        if kind == "wrzc":
            wrzc_py = WR / "redata" / "disguise.py"
            if wrzc_py.is_file():
                spec = importlib.util.spec_from_file_location("disguise", wrzc_py)
                mod = importlib.util.module_from_spec(spec)
                assert spec and spec.loader
                spec.loader.exec_module(mod)
                body = mod.disguise_unpack(blob)
            else:
                raise ValueError("wrzc_backend_missing")
            return {"ok": True, "kind": "wrzc", "profile": profile, "inner": sniff(body), "body": body, "size": len(body)}
        if kind == "zac7":
            zac_py = WR / "redata" / "zac_single.py"
            if zac_py.is_file():
                sys.path.insert(0, str(WR))
                from redata.zac_single import unpack_single
                body, _name = unpack_single(blob)
            else:
                raise ValueError("zac7_backend_missing")
            return {"ok": True, "kind": "zac7", "profile": profile, "inner": sniff(body), "body": body, "size": len(body)}
        if kind == "fld":
            text = blob.decode("utf-8", errors="replace")
            return {"ok": True, "kind": "fld", "profile": profile, "text": text[:12000], "preview": "text_raster"}
        if kind == "plate":
            doc = json.loads(blob.decode("utf-8", errors="replace"))
            return {"ok": True, "kind": "plate", "profile": profile, "plate": doc, "preview": "plate_card"}
        if kind == "ammo":
            head = blob[:8000].decode("utf-8", errors="replace")
            return {"ok": True, "kind": "ammo", "profile": profile, "text": head, "preview": "metadata"}
        if kind == "h7":
            doc = json.loads(blob.decode("utf-8", errors="replace"))
            return {"ok": True, "kind": "h7", "profile": profile, "snap": doc, "preview": "snap_card"}
    except Exception as exc:
        return {"ok": False, "kind": kind, "profile": profile, "error": str(exc)}

    return {"ok": False, "error": "unsupported", "kind": kind, "profile": profile}


def write_temp_image(body: bytes, inner: str) -> str | None:
    ext = {"png": ".png", "jpeg": ".jpg", "webp": ".webp"}.get(inner, ".bin")
    if inner not in ("png", "jpeg", "webp", "unknown"):
        ext = ".png" if body[:4] == b"\x89PNG" else ".bin"
    fd, path = tempfile.mkstemp(suffix=ext, prefix="ammoos-field-")
    os.close(fd)
    Path(path).write_bytes(body)
    return path


def dispatch_file(path: str) -> dict[str, Any]:
    p = Path(path)
    blob = p.read_bytes()
    doc = unpack_field(blob, path=str(p))
    if not doc.get("ok"):
        return doc
    body = doc.get("body")
    if body:
        inner = doc.get("inner") or sniff(body)
        doc["temp_image"] = write_temp_image(body, inner) if inner in ("png", "jpeg", "webp") else None
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "rtx":
        permit = _rtx_permit(sync_cache=True)
        print(json.dumps({"permit": permit, "profile": active_profile(), "cache": str(RTX_PERMIT_FILE)}, ensure_ascii=False))
        return 0
    if cmd == "dispatch" and len(sys.argv) > 2:
        print(json.dumps(dispatch_file(sys.argv[2]), ensure_ascii=False))
        return 0
    if cmd == "unpack" and len(sys.argv) > 2:
        blob = Path(sys.argv[2]).read_bytes()
        print(json.dumps(unpack_field(blob, path=sys.argv[2]), ensure_ascii=False))
        return 0
    if cmd == "export" and len(sys.argv) > 3:
        print(json.dumps(export_wrdt(sys.argv[2], sys.argv[3]), ensure_ascii=False))
        return 0
    if cmd == "pack" and len(sys.argv) > 2:
        raw = Path(sys.argv[2]).read_bytes()
        packed = pack_wrdt(raw)
        if len(sys.argv) > 3:
            Path(sys.argv[3]).write_bytes(packed or raw)
        print(json.dumps({"ok": bool(packed), "bytes": len(packed) if packed else 0}, ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: field-image-io.py [rtx|dispatch PATH|unpack PATH|export INNER OUT|pack INNER [OUT]]"}, ensure_ascii=False))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())