#!/usr/bin/env pythong
"""Property tests — scoring heat bounds + efficient store Merkle chain."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))

import importlib.util


def _load_module(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "lib" / rel)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


_score = _load_module("score_engine_bridge", "score-engine-bridge.py")

try:
    from hypothesis import given, strategies as st

    HAS_HYPOTHESIS = True
except ImportError:
    HAS_HYPOTHESIS = False


class ScoreHeatTests(unittest.TestCase):
    def test_python_fallback_bounded(self) -> None:
        out = _score.score_ip("10.0.0.1", [10.0] * 10)
        self.assertLessEqual(out["heat"], 1.0)
        self.assertGreaterEqual(out["heat"], 0.0)

    def test_crush_at_threshold(self) -> None:
        os.environ["NEXUS_HEAT_CRUSH_THRESHOLD"] = "0.7"
        out = _score.score_ip("10.0.0.2", [9.0] * 10)
        self.assertTrue(out["auto_crush"])


class StoreTests(unittest.TestCase):
    def test_append_chain(self) -> None:
        import efficient_store as es

        with tempfile.TemporaryDirectory() as tmp:
            os.environ["NEXUS_STATE_DIR"] = tmp
            es.STORE_ROOT = Path(tmp) / "field-store"
            es.CHAIN_FILE = es.STORE_ROOT / "merkle-chain.jsonl"
            a = es.append_record("test", {"x": 1})
            b = es.append_record("test", {"x": 2})
            self.assertNotEqual(a["hash"], b["hash"])
            self.assertEqual(b["parent"], a["hash"])


if HAS_HYPOTHESIS:

    @given(st.lists(st.floats(min_value=0, max_value=10), min_size=1, max_size=10))
    def test_axes_always_bounded(axes: list[float]) -> None:
        out = _score.score_ip("127.0.0.1", axes)
        assert 0.0 <= out["heat"] <= 1.0


if __name__ == "__main__":
    unittest.main()
