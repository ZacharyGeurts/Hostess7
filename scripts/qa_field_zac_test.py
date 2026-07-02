#!/usr/bin/env pythong
"""QA: ZAC7 pack → wipe → restore → verify round-trip."""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from field_zac import pack_storage, restore_storage, verify_storage  # noqa: E402

STORAGE = ROOT / "cache" / "fieldstorage"


def fail(msg: str) -> int:
    print(f"FAIL {msg}", file=sys.stderr)
    return 1


def main() -> int:
    if not STORAGE.is_dir() or not any(STORAGE.rglob("*")):
        print("SKIP qa_field_zac — no fieldstorage to pack")
        return 0

    with tempfile.TemporaryDirectory(prefix="zac-qa-") as tmp:
        zac_dir = Path(tmp) / "zac"
        report = pack_storage(STORAGE, zac_dir, max_shard_bytes=8 * 1024 * 1024)
        if report["total_files"] < 1:
            return fail("pack produced zero files")

        probe = next(STORAGE.rglob("brain/areas/manifest.json"), None)
        probe_data = probe.read_bytes() if probe and probe.is_file() else None

        shutil.rmtree(STORAGE)
        STORAGE.mkdir(parents=True)

        restore_storage(zac_dir, storage=STORAGE)
        verify = verify_storage(zac_dir, storage=STORAGE)
        if not verify["ok"]:
            return fail(f"verify failed: missing={len(verify['missing'])} mismatch={len(verify['mismatches'])}")

        if probe_data is not None and probe.is_file():
            if probe.read_bytes() != probe_data:
                return fail("probe file bytes differ after round-trip")

    print(f"OK field zac round-trip {report['total_files']} files {report['data_shards']} shards")
    print("METRIC qa_field_zac=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())