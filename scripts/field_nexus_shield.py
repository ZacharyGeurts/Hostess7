#!/usr/bin/env pythong
"""Hostess 7 — NEXUS-Shield control, verify, update, and panel access."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

NEXUS_INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
NEXUS_SOURCE = Path(os.environ.get(
    "NEXUS_SHIELD_SOURCE",
    str(ROOT.parent if ROOT.parent.name == "NewLatest" else ROOT.parent / "NewLatest"),
))
NEXUS_STATE = Path(os.environ.get(
    "NEXUS_STATE_DIR",
    str(NEXUS_SOURCE / ".nexus-field-drive" / "nexus-field" / "state"),
))
NEXUS_CLI = Path("/usr/local/bin/nexus")
NEXUS_GROUP = "nexus"


def _run(cmd: list[str], *, cwd: Path | None = None, timeout: int = 120) -> dict[str, Any]:
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return {
        "rc": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
        "ok": proc.returncode == 0,
    }


def _sg_nexus(args: list[str]) -> dict[str, Any]:
    return _run(["sg", NEXUS_GROUP, "-c", "nexus " + " ".join(args)])


def _installed() -> bool:
    try:
        if (NEXUS_INSTALL / "lib" / "nexus-daemon.sh").is_file():
            return True
    except OSError:
        pass
    svc = _run(["systemctl", "is-active", "nexus-genius.service"])
    return svc["stdout"] == "active" or NEXUS_CLI.is_file()


def status() -> int:
    print("=== NEXUS-Shield (Hostess 7 operator) ===")
    print(f"install_root: {NEXUS_INSTALL} ({'present' if _installed() else 'missing'})")
    print(f"source_tree:  {NEXUS_SOURCE} ({'present' if NEXUS_SOURCE.is_dir() else 'missing'})")
    print(f"state_dir:    {NEXUS_STATE} ({'present' if NEXUS_STATE.is_dir() else 'missing'})")
    daemon = NEXUS_SOURCE / "lib" / "nexus-daemon.sh"
    if daemon.is_file():
        import os
        print(f"nexus-daemon.sh: {'executable' if os.access(daemon, os.X_OK) else 'NOT EXECUTABLE — chmod +x'}")
    early = _run(["systemctl", "is-active", "nexus-field-early.service"])
    svc = _run(["systemctl", "is-active", "nexus-genius.service"])
    print(f"service: nexus-field-early.service → {early['stdout'] or early['stderr'] or 'unknown'}")
    print(f"service: nexus-genius.service → {svc['stdout'] or svc['stderr'] or 'unknown'}")
    for url, label in (
        ("http://127.0.0.1:9477/field", "panel"),
        ("http://127.0.0.1:9481/api/status", "queen"),
    ):
        rep = _run(["curl", "-sf", url], timeout=5)
        print(f"{label}: {'up' if rep['ok'] else 'down'}")
    marker = NEXUS_STATE / "field-underlay-early.json"
    if marker.is_file():
        print(f"early_boot_marker: {marker}")
    if _installed():
        rep = _sg_nexus(["status"])
        if rep["stdout"]:
            print(rep["stdout"])
        elif rep["stderr"]:
            print(rep["stderr"], file=sys.stderr)
        else:
            print("hint: sg nexus -c 'nexus status' (add user to group nexus)")
    else:
        print("hint: bash scripts/field-mint-boot-ready.sh from NewLatest checkout")
    print("stack: ./Hostess7.sh stack status · ./Hostess7.sh stack-learn")
    print("METRIC nexus_shield=1")
    healthy = svc["stdout"] == "active" or early["stdout"] in ("active", "exited")
    return 0 if healthy else 1


def verify() -> int:
    if not _installed():
        print("FAIL nexus not installed", file=sys.stderr)
        return 1
    rep = _sg_nexus(["verify"])
    print(rep["stdout"] or rep["stderr"])
    print("METRIC nexus_verify=1" if rep["ok"] else "METRIC nexus_verify=0")
    return 0 if rep["ok"] else 1


def panel() -> int:
    port = os.environ.get("NEXUS_THREAT_PANEL_PORT", "9477")
    url = f"https://127.0.0.1:{port}/"
    print(f"Threat panel (secured): {url}")
    _run(["xdg-open", url], timeout=5)
    return 0


def test_suite() -> int:
    tests = NEXUS_INSTALL / "tests" / "run-tests.sh"
    if not tests.is_file() and NEXUS_SOURCE.is_dir():
        tests = NEXUS_SOURCE / "tests" / "run-tests.sh"
    if not tests.is_file():
        print("FAIL no test suite found", file=sys.stderr)
        return 1
    rep = _run(["bash", str(tests)], cwd=tests.parent.parent, timeout=180)
    print(rep["stdout"])
    if rep["stderr"]:
        print(rep["stderr"], file=sys.stderr)
    return 0 if rep["ok"] else 1


def update(*, apply: bool = False) -> int:
    src_install = NEXUS_SOURCE / "stealth_install.sh"
    if not src_install.is_file():
        print(f"FAIL missing installer: {src_install}", file=sys.stderr)
        return 1
    if not apply:
        print(
            "BLOCKED: NEXUS update requires sudo execution.\n"
            "Run: HOSTESS7_EXEC=1 ./Hostess7.sh nexus update --apply",
            file=sys.stderr,
        )
        return 1
    if os.environ.get("HOSTESS7_EXEC") != "1":
        print("BLOCKED set HOSTESS7_EXEC=1 for apply", file=sys.stderr)
        return 1
    if os.geteuid() != 0:
        rep = _run(["sudo", "bash", str(src_install)], cwd=NEXUS_SOURCE, timeout=300)
    else:
        rep = _run(["bash", str(src_install)], cwd=NEXUS_SOURCE, timeout=300)
    print(rep["stdout"])
    if rep["stderr"]:
        print(rep["stderr"], file=sys.stderr)
    return 0 if rep["ok"] else 1


def trust_list() -> int:
    paths = [
        ROOT / "cache" / "fieldstorage" / "brain" / "security" / "nexus-trusted.jsonl",
        Path("/media/default/HOSTESS7_TEAM/fieldstorage/brain/security/nexus-trusted.jsonl"),
        Path("/var/lib/nexus-shield/firewall-trusted.tsv"),
    ]
    for p in paths:
        print(f"--- {p} ---")
        if not p.is_file():
            print("(missing)")
            continue
        text = p.read_text(encoding="utf-8", errors="replace").strip()
        print(text[-4000:] if len(text) > 4000 else text or "(empty)")
    return 0


def trust_authorize(ip: str, direction: str = "out", label: str = "") -> int:
    script = NEXUS_INSTALL / "lib" / "firewall-trust.sh"
    if not script.is_file():
        print("FAIL firewall-trust.sh missing — reinstall NEXUS", file=sys.stderr)
        return 1
    inner = (
        f"source {NEXUS_INSTALL}/lib/nexus-common.sh && "
        f"source {NEXUS_INSTALL}/lib/firewall-sentinel.sh && "
        f"source {script} && "
        f"nexus_firewall_authorize_ip '{ip}' '{direction}' '{label}' 'hostess7-cli'"
    )
    rep = _run(["bash", "-c", inner], timeout=20)
    print(rep["stdout"] or rep["stderr"])
    return 0 if rep["ok"] else 1


def corroborate() -> int:
    manifest = NEXUS_INSTALL / "MANIFEST.sha256"
    if not manifest.is_file():
        print("FAIL manifest missing", file=sys.stderr)
        return 1
    import hashlib
    digest = hashlib.sha256(manifest.read_bytes()).hexdigest()[:16]
    rep = _run([
        sys.executable,
        str(ROOT / "scripts" / "field_superintelligence.py"),
        "truth",
        f"NEXUS-Shield manifest {digest} integrity corroboration",
    ], cwd=ROOT, timeout=60)
    print(rep["stdout"][-2000:] if rep["stdout"] else rep["stderr"])
    return 0 if rep["ok"] else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hostess7 NEXUS-Shield control")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status", help="Service + firewall + panel URL")
    sub.add_parser("verify", help="Integrity + seal check")
    sub.add_parser("panel", help="Open HTTPS threat panel")
    sub.add_parser("test", help="Run NEXUS test suite")
    sub.add_parser("corroborate", help="Hostess7 truth corroboration on manifest")
    sub.add_parser("trust-list", help="Show permanent connection authorizations")
    trust = sub.add_parser("trust-authorize", help="Permanently authorize a peer IP")
    trust.add_argument("ip")
    trust.add_argument("--direction", default="out", choices=["in", "out", "both"])
    trust.add_argument("--label", default="")
    upd = sub.add_parser("update", help="Plan or apply NEXUS reinstall")
    upd.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)

    if args.cmd == "status":
        return status()
    if args.cmd == "verify":
        return verify()
    if args.cmd == "panel":
        return panel()
    if args.cmd == "test":
        return test_suite()
    if args.cmd == "corroborate":
        return corroborate()
    if args.cmd == "trust-list":
        return trust_list()
    if args.cmd == "trust-authorize":
        return trust_authorize(args.ip, args.direction, args.label)
    if args.cmd == "update":
        return update(apply=args.apply)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())