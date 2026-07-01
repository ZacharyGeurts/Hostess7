#!/usr/bin/env pythong
"""Round-trip tests for AmmoOS field image I/O."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SG = Path(__file__).resolve().parents[2]
IO = SG / "GIMP-Field" / "lib" / "field-image-io.py"


def _load():
    spec = importlib.util.spec_from_file_location("field_image_io", IO)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_wrdt_roundtrip():
    io = _load()
    raw = b"\x89PNG\r\n\x1a\n" + b"Field Technology " * 200
    packed = io.pack_wrdt(raw, force=True)
    assert packed and packed[:4] == b"WRDT"
    doc = io.unpack_field(packed)
    assert doc["ok"] and doc["body"] == raw


def test_dispatch_profile():
    io = _load()
    raw = b"\xff\xd8\xff" + b"jpeg-body" * 50
    packed = io.pack_wrdt(raw, force=True)
    assert packed
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "sample.wrdt"
        path.write_bytes(packed)
        doc = io.dispatch_file(str(path))
        assert doc["ok"]
        assert doc.get("temp_image")
        assert Path(doc["temp_image"]).is_file()


def test_cli_rtx_json():
    proc = subprocess.run(
        [sys.executable, str(IO), "rtx"],
        capture_output=True,
        text=True,
        env={**os.environ, "SG_ROOT": str(SG), "G16_RTX_GATE_FORCE": "0"},
    )
    assert proc.returncode == 0
    doc = json.loads(proc.stdout)
    assert "permit" in doc and "profile" in doc


if __name__ == "__main__":
    test_wrdt_roundtrip()
    test_dispatch_profile()
    test_cli_rtx_json()
    print("ok")