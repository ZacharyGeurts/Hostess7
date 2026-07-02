#!/usr/bin/env pythong
"""ZAC7 — lossless Field drive archive for Hostess7 SuperIntelligence.

Pack entire cache/fieldstorage/ into GitHub-friendly .zac shards; restore losslessly.
Format: ZAC7 header + zlib(tar) per data shard; index shard holds JSON manifest + checksums.
Brain JSON/text files are FLD1-precompressed inside the tar (field_fly_codec) — invisible on restore.

  pythong scripts/field_zac.py pack [--out zac] [--max-mb 48]
  pythong scripts/field_zac.py restore [--from zac] [--index fieldstorage.zac]
  pythong scripts/field_zac.py verify [--from zac]
  pythong scripts/field_zac.py list [--from zac]
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import struct
import sys
import tarfile
import zlib
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
from typing import Any, BinaryIO, Iterator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from field_fly_codec import fly_pack, fly_unpack, is_fly, should_fly_path  # noqa: E402

STORAGE = Path(os.environ.get("HOSTESS7_STORAGE", str(ROOT / "cache" / "fieldstorage")))
DEFAULT_OUT = ROOT / "zac"
DEFAULT_INDEX = "fieldstorage.zac"
WORLD_REDATA = ROOT.parent / "World_Redata"

# Runtime-only blobs — never ship in GitHub zac shards (brain + library only)
ZAC_SKIP_NAMES = frozenset({
    "team_drive.img",
    "field_wave.persist",
    "persist_qa.bin",
})
ZAC_SKIP_PREFIXES = ("bench_",)

# FLD1 at pack-time only for files ≤ this — huge jsonl stays raw (lossless, fast repack)
FLY_PACK_MAX_BYTES = 2 * 1024 * 1024
DEFAULT_JOBS = max(2, min(16, (os.cpu_count() or 4)))

MAGIC = b"ZAC7"
VERSION = 1
HEADER_SIZE = 64
KIND_INDEX = 0
KIND_DATA = 1

_STRUCT_HEADER = struct.Struct("<4sHHIIQQ32s")


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_header(
    fp: BinaryIO,
    *,
    kind: int,
    shard_id: int,
    shard_total: int,
    uncompressed: int,
    compressed: bytes,
    payload_hash: str,
) -> None:
    header = _STRUCT_HEADER.pack(
        MAGIC,
        VERSION,
        kind,
        shard_id,
        shard_total,
        uncompressed,
        len(compressed),
        bytes.fromhex(payload_hash),
    )
    assert len(header) == HEADER_SIZE
    fp.write(header)
    fp.write(compressed)


def _read_header(fp: BinaryIO) -> dict[str, Any]:
    raw = fp.read(HEADER_SIZE)
    if len(raw) != HEADER_SIZE:
        raise ValueError("truncated ZAC7 header")
    magic, version, kind, shard_id, shard_total, uncompressed, compressed_size, payload_hash = (
        _STRUCT_HEADER.unpack(raw)
    )
    if magic != MAGIC:
        raise ValueError(f"not a ZAC7 file (magic={magic!r})")
    if version != VERSION:
        raise ValueError(f"unsupported ZAC7 version {version}")
    payload = fp.read(compressed_size)
    if len(payload) != compressed_size:
        raise ValueError("truncated ZAC7 payload")
    digest = payload_hash.hex()
    try:
        body = zlib.decompress(payload)
    except zlib.error as exc:
        raise ValueError(f"zlib decompress failed: {exc}") from exc
    if len(body) != uncompressed:
        raise ValueError(f"uncompressed size mismatch: expected {uncompressed}, got {len(body)}")
    if _sha256(body) != digest:
        raise ValueError(f"payload checksum mismatch on shard {shard_id}")
    return {
        "kind": kind,
        "shard_id": shard_id,
        "shard_total": shard_total,
        "body": body,
        "compressed_size": compressed_size,
        "uncompressed_size": uncompressed,
    }


def _should_pack(rel: str) -> bool:
    name = Path(rel).name
    if name in ZAC_SKIP_NAMES:
        return False
    if any(name.startswith(p) for p in ZAC_SKIP_PREFIXES):
        return False
    return True


def _iter_storage_files(storage: Path) -> Iterator[Path]:
    if not storage.is_dir():
        return
    for path in sorted(storage.rglob("*")):
        if path.is_file():
            rel = _rel_path(storage, path)
            if _should_pack(rel):
                yield path


def _rel_path(storage: Path, path: Path) -> str:
    return path.relative_to(storage).as_posix()


def _tar_add_bytes(tar: tarfile.TarFile, arcname: str, data: bytes) -> None:
    info = tarfile.TarInfo(name=arcname)
    info.size = len(data)
    tar.addfile(info, io.BytesIO(data))


def _read_storage_bytes(src: Path) -> bytes:
    """Read file — transparent FLD1 unpack if already fly-compressed on disk."""
    raw = src.read_bytes()
    return fly_unpack(raw) if is_fly(raw) else raw


def _pack_storage_bytes(src: Path, *, fly_max: int = FLY_PACK_MAX_BYTES) -> tuple[bytes, bool]:
    """Read file for tar — reuse on-disk FLD1; only fly-pack small brain JSON."""
    raw = src.read_bytes()
    if is_fly(raw):
        return raw, True
    if should_fly_path(src) and len(raw) <= fly_max:
        packed = fly_pack(raw)
        return packed, is_fly(packed)
    return raw, False


def _build_tar_bytes(entries: list[tuple[str, bytes]]) -> tuple[bytes, int]:
    buf = io.BytesIO()
    fly_count = 0
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for arcname, data in entries:
            if is_fly(data):
                fly_count += 1
            _tar_add_bytes(tar, arcname, data)
    return buf.getvalue(), fly_count


def _pack_file_entry(path: Path, storage: Path, *, fly_max: int) -> dict[str, Any]:
    rel = _rel_path(storage, path)
    st = path.stat()
    data, flew = _pack_storage_bytes(path, fly_max=fly_max)
    return {
        "path": rel,
        "size": len(data),
        "logical_size": st.st_size,
        "source_size": st.st_size,
        "source_mtime_ns": st.st_mtime_ns,
        "sha256": _sha256(data),
        "fly": flew,
        "data": data,
    }


def _pack_files_parallel(
    paths: list[Path],
    storage: Path,
    *,
    jobs: int,
    fly_max: int,
) -> list[dict[str, Any]]:
    if len(paths) <= 2 or jobs <= 1:
        return [_pack_file_entry(p, storage, fly_max=fly_max) for p in paths]

    worker = partial(_pack_file_entry, storage=storage, fly_max=fly_max)
    out: list[dict[str, Any] | None] = [None] * len(paths)
    # Thread pool: mostly read_bytes I/O; avoids pickling huge blobs across processes
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        futures = {pool.submit(worker, p): i for i, p in enumerate(paths)}
        for fut in as_completed(futures):
            out[futures[fut]] = fut.result()
    return [e for e in out if e is not None]


def _build_shard_task(
    idx: int,
    entries: list[tuple[str, bytes]],
    *,
    zlib_level: int,
) -> tuple[int, bytes, int, bytes, str]:
    body, fly_n = _build_tar_bytes(entries)
    compressed, digest = _compress(body, level=zlib_level)
    return idx, body, fly_n, compressed, digest


def _build_shards_parallel(
    shards_entries: list[list[tuple[str, bytes]]],
    *,
    jobs: int,
    zlib_level: int,
) -> list[tuple[int, bytes, int, bytes, str]]:
    if len(shards_entries) <= 1 or jobs <= 1:
        return [
            _build_shard_task(i + 1, entries, zlib_level=zlib_level)
            for i, entries in enumerate(shards_entries)
        ]

    results: list[tuple[int, bytes, int, bytes, str] | None] = [None] * len(shards_entries)
    with ProcessPoolExecutor(max_workers=min(jobs, len(shards_entries))) as pool:
        futures = {
            pool.submit(_build_shard_task, i + 1, entries, zlib_level=zlib_level): i
            for i, entries in enumerate(shards_entries)
        }
        for fut in as_completed(futures):
            results[futures[fut]] = fut.result()
    return [r for r in results if r is not None]


def _extract_tar(body: bytes, storage: Path) -> list[str]:
    written: list[str] = []
    with tarfile.open(fileobj=io.BytesIO(body), mode="r:") as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            extracted = tar.extractfile(member)
            if extracted is None:
                continue
            data = extracted.read()
            dest = storage / member.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            # FLD1 shard members stay fly-compressed on disk — read paths decompress on fly
            dest.write_bytes(data)
            written.append(member.name)
    return written


def _compress(body: bytes, *, level: int = 1) -> tuple[bytes, str]:
    compressed = zlib.compress(body, level=level)
    return compressed, _sha256(body)


def _write_shard(
    path: Path,
    *,
    kind: int,
    shard_id: int,
    shard_total: int,
    body: bytes,
    zlib_level: int = 1,
) -> dict[str, Any]:
    compressed, digest = _compress(body, level=zlib_level)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as fp:
        _write_header(
            fp,
            kind=kind,
            shard_id=shard_id,
            shard_total=shard_total,
            uncompressed=len(body),
            compressed=compressed,
            payload_hash=digest,
        )
    return {
        "path": path.name,
        "kind": kind,
        "shard_id": shard_id,
        "files": 0,
        "uncompressed_bytes": len(body),
        "compressed_bytes": len(compressed),
        "sha256": digest,
    }


def _ledger_mark_zac_files(storage: Path, zac_ref: str) -> int:
    """Annotate World_Redata ledger — one WRDT1 pass per file; ZAC note only after."""
    ledger_py = WORLD_REDATA / "redata" / "ledger.py"
    if not ledger_py.is_file():
        return 0
    import sys

    wr = str(WORLD_REDATA)
    if wr not in sys.path:
        sys.path.insert(0, wr)
    from redata.ledger import mark_zac_converted  # noqa: WPS433

    count = 0
    for path in _iter_storage_files(storage):
        mark_zac_converted(path, zac_ref=zac_ref)
        count += 1
    return count


def _try_load_manifest(out_dir: Path, index_name: str) -> dict[str, Any] | None:
    index_path = out_dir / index_name
    if not index_path.is_file():
        return None
    try:
        return _load_index(index_path)
    except (OSError, ValueError):
        return None


def _storage_unchanged(storage: Path, old: dict[str, Any] | None) -> bool:
    """Fast skip — compare source size+mtime against last manifest."""
    if not old:
        return False
    prev = {e["path"]: e for e in old.get("files", [])}
    seen = 0
    for path in _iter_storage_files(storage):
        seen += 1
        rel = _rel_path(storage, path)
        entry = prev.get(rel)
        if not entry:
            return False
        st = path.stat()
        if entry.get("source_size", entry.get("logical_size")) != st.st_size:
            return False
        mtime = entry.get("source_mtime_ns")
        if mtime is not None and mtime != st.st_mtime_ns:
            return False
    return seen == len(prev) and seen > 0


def _preflight_non_fielded(storage: Path) -> None:
    """Refuse ZAC pack while WRDT/WRZC tails remain — no field-on-field."""
    if os.environ.get("NEXUS_ZAC_SKIP_DEFIELD", "").strip().lower() in ("1", "true", "yes"):
        return
    safety = ROOT.parent / "NewLatest" / "lib" / "field-non-fielded-safety.py"
    if not safety.is_file():
        safety = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield")) / "lib" / "field-non-fielded-safety.py"
    if safety.is_file():
        import subprocess
        proc = subprocess.run(
            [sys.executable, str(safety), "gate-convert"],
            capture_output=True,
            text=True,
            timeout=180,
            env={**os.environ, "HOSTESS7_ROOT": str(ROOT), "HOSTESS7_TEAM_FIELD": str(storage)},
        )
        try:
            rep = json.loads(proc.stdout or "{}")
        except json.JSONDecodeError:
            rep = {}
        if not rep.get("ok"):
            raise ValueError(
                "ZAC7 pack blocked — defield all WRDT/WRZC/ZAC tails first (non-fielded safety). "
                f"restorable={rep.get('restorable_files')} tails={rep.get('field_tail_hits')}"
            )
    if (WORLD_REDATA / "redata" / "cli.py").is_file():
        import subprocess
        proc = subprocess.run(
            [sys.executable, str(WORLD_REDATA / "redata" / "cli.py"), "scan-restorable", str(storage)],
            capture_output=True,
            text=True,
            timeout=120,
            env={**os.environ, "PYTHONPATH": str(WORLD_REDATA)},
        )
        try:
            rep = json.loads(proc.stdout or "{}")
            if int(rep.get("restorable_files") or 0) > 0:
                raise ValueError(
                    f"ZAC7 pack blocked — {rep['restorable_files']} restorable field tails under {storage}"
                )
        except json.JSONDecodeError:
            pass


def pack_storage(
    storage: Path = STORAGE,
    out_dir: Path = DEFAULT_OUT,
    *,
    max_shard_bytes: int = 18 * 1024 * 1024,
    index_name: str = DEFAULT_INDEX,
    fast: bool = True,
    force: bool = False,
    jobs: int = DEFAULT_JOBS,
    fly_max_bytes: int = FLY_PACK_MAX_BYTES,
) -> dict[str, Any]:
    """Pack fieldstorage into index + data .zac shards."""
    if not storage.is_dir():
        raise FileNotFoundError(f"storage missing: {storage}")
    _preflight_non_fielded(storage)

    old = None if force else _try_load_manifest(out_dir, index_name)
    if _storage_unchanged(storage, old):
        return {
            "action": "pack",
            "skipped": True,
            "storage": str(storage),
            "out_dir": str(out_dir),
            "index": index_name,
            "total_files": old.get("total_files", 0) if old else 0,
            "total_bytes": old.get("total_bytes", 0) if old else 0,
            "data_shards": len(old.get("shards", [])) if old else 0,
            "fly_files": old.get("fly_files", 0) if old else 0,
            "compressed_bytes": sum(s.get("compressed_bytes", 0) for s in old.get("shards", [])) if old else 0,
            "shards": old.get("shards", []) if old else [],
        }

    zlib_level = 1 if fast else 9
    paths = list(_iter_storage_files(storage))
    if not paths:
        raise ValueError(f"no files under {storage}")

    packed = _pack_files_parallel(paths, storage, jobs=jobs, fly_max=fly_max_bytes)
    files_meta: list[dict[str, Any]] = []
    shard_payloads: list[tuple[str, bytes]] = []
    for entry in packed:
        data = entry.pop("data")
        shard_payloads.append((entry["path"], data))
        files_meta.append(entry)

    shards_entries: list[list[tuple[str, bytes]]] = [[]]
    shard_sizes: list[int] = [0]

    for meta, (rel, data) in zip(files_meta, shard_payloads, strict=True):
        size = meta["size"]
        if shard_sizes[-1] + size > max_shard_bytes and shards_entries[-1]:
            shards_entries.append([])
            shard_sizes.append(0)
        shards_entries[-1].append((rel, data))
        shard_sizes[-1] += size
        meta["shard"] = len(shards_entries)

    shard_total = len(shards_entries) + 1  # data shards + index
    shard_records: list[dict[str, Any]] = []

    built = _build_shards_parallel(shards_entries, jobs=jobs, zlib_level=zlib_level)
    built.sort(key=lambda row: row[0])
    total_fly = 0
    for idx, body, fly_n, compressed, digest in built:
        total_fly += fly_n
        shard_name = f"fieldstorage-{idx:04d}.zac"
        shard_path = out_dir / shard_name
        shard_path.parent.mkdir(parents=True, exist_ok=True)
        with shard_path.open("wb") as fp:
            _write_header(
                fp,
                kind=KIND_DATA,
                shard_id=idx,
                shard_total=shard_total,
                uncompressed=len(body),
                compressed=compressed,
                payload_hash=digest,
            )
        entries = shards_entries[idx - 1]
        rec = {
            "path": shard_name,
            "kind": KIND_DATA,
            "shard_id": idx,
            "files": len(entries),
            "file_paths": [e[0] for e in entries],
            "uncompressed_bytes": len(body),
            "compressed_bytes": len(compressed),
            "sha256": digest,
        }
        shard_records.append(rec)

    manifest = {
        "format": "zac7",
        "version": VERSION,
        "created": _ts(),
        "project": "Hostess7",
        "storage_root": "cache/fieldstorage",
        "total_files": len(files_meta),
        "total_bytes": sum(m["size"] for m in files_meta),
        "max_shard_bytes": max_shard_bytes,
        "fly_codec": "FLD1",
        "fly_files": total_fly,
        "shards": shard_records,
        "files": files_meta,
    }
    index_body = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")
    index_rec = _write_shard(
        out_dir / index_name,
        kind=KIND_INDEX,
        shard_id=0,
        shard_total=shard_total,
        body=index_body,
        zlib_level=zlib_level,
    )
    index_rec["files"] = len(files_meta)

    ledger_marked = _ledger_mark_zac_files(storage, zac_ref=index_name)
    report = {
        "action": "pack",
        "storage": str(storage),
        "out_dir": str(out_dir),
        "index": index_name,
        "total_files": len(files_meta),
        "total_bytes": manifest["total_bytes"],
        "data_shards": len(shard_records),
        "fly_files": total_fly,
        "ledger_zac_marked": ledger_marked,
        "compressed_bytes": sum(s["compressed_bytes"] for s in shard_records) + index_rec["compressed_bytes"],
        "shards": [index_rec, *shard_records],
    }
    return report


def _load_index(index_path: Path) -> dict[str, Any]:
    with index_path.open("rb") as fp:
        parsed = _read_header(fp)
    if parsed["kind"] != KIND_INDEX:
        raise ValueError(f"{index_path.name} is not a ZAC7 index shard")
    manifest = json.loads(parsed["body"].decode("utf-8"))
    if manifest.get("format") != "zac7":
        raise ValueError("invalid manifest format")
    return manifest


def restore_storage(
    zac_dir: Path = DEFAULT_OUT,
    *,
    index_name: str = DEFAULT_INDEX,
    storage: Path = STORAGE,
    verify: bool = True,
) -> dict[str, Any]:
    """Restore fieldstorage from .zac shards."""
    index_path = zac_dir / index_name
    if not index_path.is_file():
        raise FileNotFoundError(f"index missing: {index_path}")

    manifest = _load_index(index_path)
    storage.mkdir(parents=True, exist_ok=True)

    restored: list[str] = []
    for shard in manifest.get("shards", []):
        shard_path = zac_dir / shard["path"]
        if not shard_path.is_file():
            raise FileNotFoundError(f"shard missing: {shard_path}")
        with shard_path.open("rb") as fp:
            parsed = _read_header(fp)
        if parsed["kind"] != KIND_DATA:
            raise ValueError(f"{shard_path.name} is not a data shard")
        restored.extend(_extract_tar(parsed["body"], storage))

    if verify:
        verify_report = verify_storage(zac_dir=zac_dir, index_name=index_name, storage=storage)
        if not verify_report["ok"]:
            raise ValueError("restore verification failed — checksum mismatch")

    return {
        "action": "restore",
        "storage": str(storage),
        "from": str(zac_dir),
        "index": index_name,
        "total_files": manifest.get("total_files", 0),
        "restored_paths": len(restored),
        "total_bytes": manifest.get("total_bytes", 0),
    }


def verify_storage(
    zac_dir: Path = DEFAULT_OUT,
    *,
    index_name: str = DEFAULT_INDEX,
    storage: Path = STORAGE,
) -> dict[str, Any]:
    """Verify on-disk fieldstorage matches ZAC7 manifest."""
    index_path = zac_dir / index_name
    manifest = _load_index(index_path)
    mismatches: list[dict[str, Any]] = []
    missing: list[str] = []

    for entry in manifest.get("files", []):
        rel = entry["path"]
        dest = storage / rel
        if not dest.is_file():
            missing.append(rel)
            continue
        digest = _sha256_file(dest)
        if digest != entry["sha256"]:
            mismatches.append({"path": rel, "expected": entry["sha256"], "actual": digest})

    return {
        "action": "verify",
        "ok": not mismatches and not missing,
        "total_files": len(manifest.get("files", [])),
        "missing": missing,
        "mismatches": mismatches,
    }


def list_archive(
    zac_dir: Path = DEFAULT_OUT,
    *,
    index_name: str = DEFAULT_INDEX,
) -> dict[str, Any]:
    """List contents of a ZAC7 archive."""
    manifest = _load_index(zac_dir / index_name)
    return {
        "action": "list",
        "index": index_name,
        "created": manifest.get("created"),
        "total_files": manifest.get("total_files"),
        "total_bytes": manifest.get("total_bytes"),
        "data_shards": len(manifest.get("shards", [])),
        "files": manifest.get("files", []),
    }


def _format_bytes(n: int) -> str:
    for unit in ("B", "KiB", "MiB", "GiB"):
        if n < 1024 or unit == "GiB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024
    return f"{n} B"


def _print_report(report: dict[str, Any]) -> None:
    action = report.get("action")
    if action == "pack":
        if report.get("skipped"):
            print(f"ZAC7 pack skipped — no changes ({report['total_files']} files, {_format_bytes(report['total_bytes'])})")
            print(f"  out: {report['out_dir']}")
            print("  tip: touch a brain file or use --force to repack")
            return
        print(f"ZAC7 pack OK — {report['total_files']} files, {_format_bytes(report['total_bytes'])}")
        print(f"  out: {report['out_dir']}")
        print(f"  index: {report['index']}")
        print(f"  data shards: {report['data_shards']}")
        print(f"  compressed: {_format_bytes(report['compressed_bytes'])}")
        if report.get("fly_files"):
            print(f"  FLD1 inner: {report['fly_files']} brain files pre-compressed in tar")
        for shard in report.get("shards", []):
            if shard.get("kind") == KIND_INDEX:
                continue
            print(f"    {shard['path']}: {shard['files']} files, {_format_bytes(shard['compressed_bytes'])}")
    elif action == "restore":
        print(f"ZAC7 restore OK — {report['restored_paths']} paths → {report['storage']}")
        print(f"  from: {report['from']}/{report['index']}")
        print(f"  total: {_format_bytes(report['total_bytes'])}")
    elif action == "verify":
        status = "OK" if report["ok"] else "FAIL"
        print(f"ZAC7 verify {status} — {report['total_files']} files")
        if report.get("missing"):
            print(f"  missing: {len(report['missing'])}")
            for p in report["missing"][:8]:
                print(f"    - {p}")
        if report.get("mismatches"):
            print(f"  mismatches: {len(report['mismatches'])}")
            for m in report["mismatches"][:8]:
                print(f"    - {m['path']}")
    elif action == "list":
        print(f"ZAC7 archive — {report['total_files']} files, {_format_bytes(report['total_bytes'])}")
        print(f"  created: {report.get('created')}")
        print(f"  shards: {report.get('data_shards')}")
        for entry in report.get("files", [])[:20]:
            print(f"    {entry['path']}  ({_format_bytes(entry['size'])})")
        if report["total_files"] > 20:
            print(f"    … +{report['total_files'] - 20} more")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hostess7 ZAC7 field drive pack/restore")
    sub = parser.add_subparsers(dest="cmd", required=True)

    pack_p = sub.add_parser("pack", help="Pack cache/fieldstorage to .zac shards")
    pack_p.add_argument("--storage", type=Path, default=STORAGE)
    pack_p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    pack_p.add_argument("--index", default=DEFAULT_INDEX)
    pack_p.add_argument("--max-mb", type=int, default=48, help="Max uncompressed bytes per data shard")
    pack_p.add_argument("--fast", action="store_true", default=True, help="Fast zlib + skip if unchanged (default)")
    pack_p.add_argument("--full", action="store_true", help="Full zlib level 9 compression")
    pack_p.add_argument("--force", action="store_true", help="Repack even when storage unchanged")
    pack_p.add_argument("--jobs", type=int, default=DEFAULT_JOBS, help="Parallel workers (default: CPU count)")
    pack_p.add_argument(
        "--fly-max-mb",
        type=int,
        default=FLY_PACK_MAX_BYTES // (1024 * 1024),
        help="Max MiB for FLD1 at pack-time (larger files ship raw)",
    )

    restore_p = sub.add_parser("restore", help="Restore cache/fieldstorage from .zac shards")
    restore_p.add_argument("--from", dest="zac_dir", type=Path, default=DEFAULT_OUT)
    restore_p.add_argument("--index", default=DEFAULT_INDEX)
    restore_p.add_argument("--storage", type=Path, default=STORAGE)
    restore_p.add_argument("--no-verify", action="store_true")

    verify_p = sub.add_parser("verify", help="Verify storage matches manifest")
    verify_p.add_argument("--from", dest="zac_dir", type=Path, default=DEFAULT_OUT)
    verify_p.add_argument("--index", default=DEFAULT_INDEX)
    verify_p.add_argument("--storage", type=Path, default=STORAGE)

    list_p = sub.add_parser("list", help="List archive contents")
    list_p.add_argument("--from", dest="zac_dir", type=Path, default=DEFAULT_OUT)
    list_p.add_argument("--index", default=DEFAULT_INDEX)

    args = parser.parse_args(argv)

    try:
        if args.cmd == "pack":
            report = pack_storage(
                args.storage,
                args.out,
                max_shard_bytes=args.max_mb * 1024 * 1024,
                index_name=args.index,
                fast=not args.full,
                force=args.force,
                jobs=max(1, args.jobs),
                fly_max_bytes=max(1, args.fly_max_mb) * 1024 * 1024,
            )
        elif args.cmd == "restore":
            report = restore_storage(
                args.zac_dir,
                index_name=args.index,
                storage=args.storage,
                verify=not args.no_verify,
            )
        elif args.cmd == "verify":
            report = verify_storage(args.zac_dir, index_name=args.index, storage=args.storage)
        elif args.cmd == "list":
            report = list_archive(args.zac_dir, index_name=args.index)
        else:
            return 1
    except (OSError, ValueError, FileNotFoundError) as exc:
        print(f"ZAC7 error: {exc}", file=sys.stderr)
        return 1

    _print_report(report)
    if args.cmd == "verify" and not report.get("ok"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())