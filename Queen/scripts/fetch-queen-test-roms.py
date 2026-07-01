#!/usr/bin/env python3
"""Fetch legal/homebrew Queen Game Room test ROMs into assets/dos/incoming/{system}/."""
from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

QUEEN = Path(__file__).resolve().parents[1]
NEXUS = Path(os.environ.get("NEXUS_INSTALL_ROOT", QUEEN.parent))
MANIFEST = QUEEN / "data" / "queen-test-roms.json"
RTX = Path(os.environ.get("AMOURANTHRTX_ROOT", NEXUS.parent / "AMOURANTHRTX"))


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _incoming_roots() -> list[Path]:
    roots = [
        NEXUS / "assets" / "dos" / "incoming",
        RTX / "assets" / "dos" / "incoming",
        QUEEN / "build" / "rtx" / "bin" / "Kilroy" / "assets" / "dos" / "incoming",
    ]
    out: list[Path] = []
    seen: set[str] = set()
    for r in roots:
        key = str(r)
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def _fetch(url: str, timeout: int = 60) -> bytes | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Queen-Test-ROM-Fetch/1"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print(f"  skip {url}: {exc}", file=sys.stderr)
        return None


def main() -> int:
    doc = json.loads(MANIFEST.read_text(encoding="utf-8"))
    systems = doc.get("systems") or {}
    results: list[dict] = []
    for sys_id, spec in systems.items():
        dest_name = str(spec.get("filename") or f"{sys_id}-test.bin")
        sources = spec.get("sources") or []
        fallback = spec.get("fallback")
        data: bytes | None = None
        used_url = ""
        for src in sources:
            url = str(src.get("url") or "")
            if not url:
                continue
            blob = _fetch(url)
            if not blob or len(blob) < 16:
                continue
            expect = str(src.get("sha256") or "")
            if expect and _sha256(blob) != expect:
                print(f"  sha mismatch {sys_id} {url}", file=sys.stderr)
                continue
            data = blob
            used_url = url
            if src.get("save_as"):
                dest_name = str(src["save_as"])
            break
        if not data and fallback:
            for root in _incoming_roots():
                hit = root / sys_id / fallback
                if hit.is_file():
                    data = hit.read_bytes()
                    used_url = f"fallback:{hit}"
                    dest_name = fallback
                    break
        row = {"system": sys_id, "ok": bool(data), "filename": dest_name, "url": used_url}
        if data:
            for root in _incoming_roots():
                d = root / sys_id
                d.mkdir(parents=True, exist_ok=True)
                out = d / dest_name
                out.write_bytes(data)
                row.setdefault("written", []).append(str(out))
        results.append(row)
        print(json.dumps(row))
    ok_n = sum(1 for r in results if r.get("ok"))
    print(json.dumps({"schema": "queen-test-roms-fetch/v1", "ok": ok_n > 0, "fetched": ok_n, "total": len(results)}))
    return 0 if ok_n else 1


if __name__ == "__main__":
    raise SystemExit(main())