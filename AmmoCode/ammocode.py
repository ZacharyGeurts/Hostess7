#!/usr/bin/env python3
"""AmmoCode — simple, safe, secure code editor (NEXUS C2 · G16)."""
from __future__ import annotations

import importlib.util
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SG = os.environ.get("SG_ROOT", os.path.dirname(ROOT))
os.environ.setdefault("SG_ROOT", SG)
os.environ.setdefault("NEXUS_INSTALL_ROOT", os.environ.get("NEXUS_INSTALL_ROOT", os.path.join(SG, "AmmoOS")))
_nl = os.path.join(SG, "NewLatest")
_default_g16 = os.path.join(_nl, "Grok16") if os.path.isdir(os.path.join(_nl, "Grok16")) else os.path.join(SG, "NewLatest", "Grok16")
os.environ.setdefault("GROK16_ROOT", os.environ.get("GROK16_ROOT", _default_g16))

SERVER = os.path.join(ROOT, "server")
STACK = os.path.join(SERVER, "ammocode-stack-serve.py")
LEGACY = os.path.join(SERVER, "ammocode-serve.py")


def _load_serve():
    serve_path = STACK if os.environ.get("AMMOCODE_LEGACY") != "1" else LEGACY
    if not os.path.isfile(serve_path):
        serve_path = LEGACY
    sys.path.insert(0, SERVER)
    spec = importlib.util.spec_from_file_location("ammocode_serve", serve_path)
    if not spec or not spec.loader:
        raise RuntimeError(f"cannot load serve module: {serve_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


if __name__ == "__main__":
    if "--check" in sys.argv or "-c" in sys.argv:
        mod = _load_serve()
        nexus = os.environ["NEXUS_INSTALL_ROOT"]
        grok = os.environ["GROK16_ROOT"]
        doc = {
            "ok": True,
            "ammocode_root": ROOT,
            "sg_root": SG,
            "nexus_install_root": nexus,
            "grok16_root": grok,
            "serve": STACK if os.path.isfile(STACK) else LEGACY,
            "index": os.path.join(ROOT, "index.html"),
            "g16_bin": os.path.join(grok, "bin", "g16"),
        }
        print(json.dumps(doc, indent=2))
        raise SystemExit(0)
    raise SystemExit(_load_serve().main())