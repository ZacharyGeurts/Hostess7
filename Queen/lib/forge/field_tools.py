"""Queen Forge — Field Kernel + one-sovereign-field packaging."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from forge.engine import ForgeContext, ForgeEngine, ForgeResult
from forge.field_paths import (
    field_status,
    field_storage_root,
    kernel_artifacts,
    kilroy_root,
    sg_root,
    substrate_root,
)
from forge.common import fail_result, ok_result, rtx_bin, rtx_ready

SOVEREIGN_BUNDLE_NAME = "queen-sovereign-bundle.json"
SOVEREIGN_BUNDLE_SCHEMA = "queen-sovereign-bundle/v1"


def _guarded_json(path: Path, doc: dict[str, Any], engine: ForgeEngine) -> bool:
    queen = Path(__file__).resolve().parents[2]
    nexus = sg_root(queen)
    gate_py = nexus / "NewLatest" / "lib" / "field-no-file-gate.py"
    if not gate_py.is_file():
        path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
        return True
    import importlib.util

    spec = importlib.util.spec_from_file_location("field_no_file_gate_ft", gate_py)
    if not spec or not spec.loader:
        return False
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    rep = mod.guarded_write_json(path, doc)
    if not rep.get("ok"):
        engine.log(f"BLOCKED field file poison: {path.name} — {rep.get('reason')}")
        return False
    return True


def _run_script(engine: ForgeEngine, script: Path, *, env: dict[str, str] | None = None) -> int:
    if not script.is_file():
        engine.log(f"MISSING script: {script}")
        return 127
    return engine.run_stream(["bash", str(script)], cwd=script.parent.parent, env=env)


def check_field_substrate(ctx: ForgeContext) -> bool:
    sub = substrate_root(ctx.queen)
    if not sub:
        return False
    return (sub / "kernel" / "rtx").is_dir() or (sub / "arch" / "x86" / "entry" / "rtx_field.S").is_file()


def run_field_substrate(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    engine.log("=== forge:field_substrate — KILROY become-substrate ===")
    script = kilroy_root(ctx.queen) / "scripts" / "kilroy-become-substrate.sh"
    if not script.is_file():
        return fail_result(engine, "field_substrate", f"missing {script}")
    rc = _run_script(engine, script, env={**ctx.env(), "SG_ROOT": str(sg_root(ctx.queen))})
    return ok_result(engine, "field_substrate") if rc == 0 else fail_result(engine, "field_substrate", "substrate sync failed", rc)


def check_field_kernel(ctx: ForgeContext) -> bool:
    return kernel_artifacts(ctx.queen)["bzImage"] is not None


def run_field_kernel(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    engine.log("=== forge:field_kernel — KILROY Field OS bzImage ===")
    script = kilroy_root(ctx.queen) / "scripts" / "build-kilroy.sh"
    if not script.is_file():
        return fail_result(engine, "field_kernel", f"missing {script}")
    env = {
        **ctx.env(),
        "SG_ROOT": str(sg_root(ctx.queen)),
        "GROK_IMAGE": "0",  # boot image is separate tool
        "JOBS": str(ctx.jobs),
    }
    if not check_field_substrate(ctx):
        run_field_substrate(ctx, engine)
    rc = _run_script(engine, script, env=env)
    return ok_result(engine, "field_kernel", str(kilroy_root(ctx.queen) / "build" / "bzImage")) if rc == 0 \
        else fail_result(engine, "field_kernel", "kernel build failed", rc)


def check_field_boot(ctx: ForgeContext) -> bool:
    arts = kernel_artifacts(ctx.queen)
    return arts["grok_img"] is not None or arts["grok_iso"] is not None


def run_field_boot(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    engine.log("=== forge:field_boot — Grok secure boot image ===")
    if not check_field_kernel(ctx):
        r = run_field_kernel(ctx, engine)
        if not r.ok:
            return r
    script = kilroy_root(ctx.queen) / "scripts" / "grok-mkimage.sh"
    if not script.is_file():
        return fail_result(engine, "field_boot", f"missing {script}")
    rc = _run_script(engine, script, env={**ctx.env(), "SG_ROOT": str(sg_root(ctx.queen))})
    return ok_result(engine, "field_boot") if rc == 0 else fail_result(engine, "field_boot", "grok image failed", rc)


def check_field_rootfs(ctx: ForgeContext) -> bool:
    return kernel_artifacts(ctx.queen)["rootfs_staging"] is not None


def run_field_rootfs(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    engine.log("=== forge:field_rootfs — KILROY production rootfs ===")
    script = kilroy_root(ctx.queen) / "rootfs" / "build-production-rootfs.sh"
    if not script.is_file():
        return fail_result(engine, "field_rootfs", f"missing {script}")
    rc = _run_script(engine, script, env={**ctx.env(), "SG_ROOT": str(sg_root(ctx.queen))})
    return ok_result(engine, "field_rootfs") if rc == 0 else fail_result(engine, "field_rootfs", "rootfs failed", rc)


def check_field_package(ctx: ForgeContext) -> bool:
    manifest = ctx.queen / "field" / "sovereign" / SOVEREIGN_BUNDLE_NAME
    if not manifest.is_file():
        return False
    try:
        doc = json.loads(manifest.read_text(encoding="utf-8"))
        return doc.get("sealed") is True and (ctx.queen / "field" / "sovereign" / "kernel" / "bzImage").is_file()
    except (OSError, json.JSONDecodeError):
        return False


def _copy_tree(engine: ForgeEngine, src: Path, dst: Path) -> None:
    if not src.exists():
        return
    if src.is_file():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        engine.log(f"  copy {dst.name}")
        return
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, symlinks=True, ignore_dangling_symlinks=True)
    engine.log(f"  tree {src.name}/ → {dst}")


def run_field_package(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    engine.log("=== forge:field_package — one sovereign field ===")
    root = ctx.queen
    out = root / "field" / "sovereign"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    arts = kernel_artifacts(root)
    bz = arts["bzImage"]
    if not bz:
        engine.log("kernel missing — building field_kernel")
        r = run_field_kernel(ctx, engine)
        if not r.ok:
            return r
        bz = kernel_artifacts(root)["bzImage"]
    if not bz:
        return fail_result(engine, "field_package", "no bzImage")

    # kernel + boot
    kdir = out / "kernel"
    kdir.mkdir(parents=True)
    shutil.copy2(bz, kdir / "bzImage")
    engine.log(f"  kernel/bzImage ← {bz}")
    if arts["grok_img"]:
        boot = out / "boot"
        boot.mkdir(parents=True, exist_ok=True)
        shutil.copy2(arts["grok_img"], boot / "grok-kilroy.img")
    if arts["grok_iso"]:
        boot = out / "boot"
        boot.mkdir(parents=True, exist_ok=True)
        shutil.copy2(arts["grok_iso"], boot / "grok-kilroy.iso")

    # rootfs slice
    if not check_field_rootfs(ctx):
        run_field_rootfs(ctx, engine)
    staging = kernel_artifacts(root)["rootfs_staging"]
    if staging:
        _copy_tree(engine, staging, out / "rootfs")

    # Queen browser + secure stack
    queen_pkg = out / "queen"
    queen_pkg.mkdir(parents=True)
    for sub in ("gui", "data", "lib", "config", "plugins", "shaders", "world", "AmmoOS"):
        src = root / sub
        if src.exists():
            _copy_tree(engine, src, queen_pkg / sub)
    engine.log("  panel/ excluded — legacy NEXUS :9477 not in sovereign bundle")

    # Materialize NEXUS field defenses + weapons (real files, not host symlinks)
    nexus = sg_root(root) / "NewLatest"
    nexus_lib = queen_pkg / "lib"
    nexus_lib.mkdir(parents=True, exist_ok=True)
    for name in (
        "trust-strike-engine.py",
        "field-attack-kit.py",
        "field-attack-kit.sh",
        "kill-detect.py",
        "kill-detect.sh",
        "host-attack.sh",
        "host-attack-map.py",
        "heaven-hell.py",
        "sovereign-time.py",
        "connection-gatekeeper.py",
        "field-queen-browser.py",
        "queen_field_nexus.py",
        "packet-field.py",
        "field-dns.py",
    ):
        src = nexus / "lib" / name
        dst = nexus_lib / name
        if src.is_file():
            try:
                if src.resolve() == dst.resolve():
                    engine.log(f"  ok nexus weapon {name} (already linked)")
                    continue
            except OSError:
                pass
            if dst.is_symlink():
                dst.unlink()
            shutil.copy2(src, dst)
            engine.log(f"  nexus weapon {name}")
    stack_manifest = nexus / "data" / "field-stack-manifest.json"
    if stack_manifest.is_file():
        dst_data = queen_pkg / "data"
        dst_data.mkdir(parents=True, exist_ok=True)
        shutil.copy2(stack_manifest, dst_data / "field-stack-manifest.json")
    nexus_conf = nexus / "config" / "nexus.conf"
    if nexus_conf.is_file():
        dst_cfg = queen_pkg / "config"
        dst_cfg.mkdir(parents=True, exist_ok=True)
        shutil.copy2(nexus_conf, dst_cfg / "nexus.conf")
    bin_path = rtx_bin(ctx)
    if bin_path:
        bindir = queen_pkg / "bin"
        bindir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(bin_path, bindir / "queen-browser")
        bindir.joinpath("queen-browser").chmod(0o755)
        engine.log(f"  queen/bin/queen-browser ← {bin_path}")
    else:
        engine.log("  WARN: queen-browser not built — package kernel-only")

    # Active Hostess 7 — smart brain comes with (symlink to canonical SG/Hostess7)
    h7_src = sg_root(root) / "Hostess7"
    h7_pkg = out / "hostess7"
    if h7_src.is_dir():
        if h7_pkg.exists():
            if h7_pkg.is_symlink():
                h7_pkg.unlink()
            else:
                shutil.rmtree(h7_pkg)
        h7_pkg.symlink_to(h7_src.resolve())
        engine.log(f"  hostess7 → {h7_src} (active brain, lossless)")
        brain_link = queen_pkg / "hostess7"
        if not brain_link.exists():
            brain_link.symlink_to(Path("..") / "hostess7")
            engine.log("  queen/hostess7 → ../hostess7")

    secure = out / "secure"
    secure.mkdir(parents=True)
    for f in (
        "field-queen-gates-seed.json",
        "grok-build-mandate.json",
        "field-rtx-sovereign.json",
        "queen-boot-mandate.json",
        "queen-brain-manifest.json",
        "queen-forge-manifest.json",
        "queen-field-manifest.json",
        "ammoos-boot-map.json",
        "queen-field-net.json",
    ):
        src = root / "data" / f
        if src.is_file():
            shutil.copy2(src, secure / f)

    # SG pointers for field operators
    paths_doc = field_status(root)
    (out / "paths.json").write_text(json.dumps(paths_doc, indent=2), encoding="utf-8")

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    manifest = {
        "schema": SOVEREIGN_BUNDLE_SCHEMA,
        "title": "Queen Sovereign Bundle — kernel + browser + secure stack",
        "motto": "One field. Field Kernel. Queen browser. All gates held.",
        "sealed": True,
        "stamped": stamp,
        "sg_root": str(sg_root(root)),
        "kilroy_root": str(kilroy_root(root)),
        "field_storage": paths_doc.get("field_storage"),
        "layout": {
            "kernel": "kernel/bzImage",
            "boot": "boot/grok-kilroy.img",
            "rootfs": "rootfs/",
            "queen": "queen/",
            "hostess7": "hostess7/",
            "secure": "secure/",
        },
        "hostess7_root": str(h7_src) if h7_src.is_dir() else None,
        "cmdline": "root=/dev/ram0 rw init=/init console=ttyS0 kilroy.field=1 grok.security=strict",
        "secure_channel": True,
        "components": {
            "field_kernel": "KILROY 7.1.1-kilroy — CONFIG_RTX_FIELD_DIE",
            "queen_browser": "queen/bin/queen-browser",
            "grok_build": "secure/grok-build-mandate.json",
            "gates": "secure/field-queen-gates-seed.json",
        },
        "runtime": paths_doc.get("runtime"),
    }
    # Field Technology ZAC + textbook pointers (best-effort)
    tb = sg_root(root) / "NewLatest" / "Textbook"
    zac = tb / "field-technology-v5.zac"
    field_books = out / "fieldstorage" / "textbooks"
    field_books.mkdir(parents=True, exist_ok=True)
    if zac.is_file():
        shutil.copy2(zac, field_books / "field-technology-v5.zac")
        engine.log(f"  fieldstorage/textbooks/field-technology-v5.zac")
    for extra in ("size-comparison.json", "build-summary.json"):
        src = tb / extra
        if src.is_file():
            shutil.copy2(src, field_books / extra)

    bundle_path = out / SOVEREIGN_BUNDLE_NAME
    if not _guarded_json(bundle_path, manifest, engine):
        return fail_result(engine, "field_package", "sovereign bundle blocked — field file poison")
    engine.log(f"=== SOVEREIGN BUNDLE SEALED: {out} ===")
    return ok_result(engine, "field_package", str(out))


def check_field_publish(ctx: ForgeContext) -> bool:
    storage = field_storage_root(ctx.queen)
    if not storage:
        return False
    published = storage / "queen-field" / "sovereign" / SOVEREIGN_BUNDLE_NAME
    return published.is_file()


def run_field_publish(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    engine.log("=== forge:field_publish — field drive ===")
    if not check_field_package(ctx):
        r = run_field_package(ctx, engine)
        if not r.ok:
            return r
    storage = field_storage_root(ctx.queen)
    if not storage:
        return fail_result(engine, "field_publish", "no field storage drive found — set HOSTESS7_TEAM_FIELD")
    src = ctx.queen / "field" / "sovereign"
    dst = storage / "queen-field" / "sovereign"
    if dst.exists():
        shutil.rmtree(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dst)
    engine.log(f"  published → {dst}")

    # nexus-field pointer for operators
    nexus_field = storage / "nexus-field"
    nexus_field.mkdir(parents=True, exist_ok=True)
    link_manifest = {
        "schema": "queen-field-link/v1",
        "queen_field": str(dst),
        "queen_root": str(ctx.queen),
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    (nexus_field / "queen-field-link.json").write_text(
        json.dumps(link_manifest, indent=2), encoding="utf-8"
    )
    engine.log(f"=== FIELD PUBLISHED: {dst} ===")
    return ok_result(engine, "field_publish", str(dst))


def run_field(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    """Full sovereign field: kernel + queen + package."""
    engine.log("=== forge:field — full sovereign field pipeline ===")
    inside_ok = (ctx.queen / ".queen-inside").is_file() and (ctx.queen / "panel").exists()
    if not inside_ok:
        from forge.tools import run_inside  # lazy — avoid import cycle at module load
        run_inside(ctx, engine)
    for step, fn in (
        ("field_substrate", run_field_substrate),
        ("field_kernel", run_field_kernel),
        ("field_boot", run_field_boot),
        ("field_rootfs", run_field_rootfs),
    ):
        tool = fn.__name__.replace("run_", "")
        checker = globals().get(f"check_{tool}")
        if checker and checker(ctx):
            engine.log(f"SKIP {tool} — ready")
            continue
        r = fn(ctx, engine)
        if not r.ok and tool in ("field_substrate", "field_kernel"):
            return r
        if not r.ok:
            engine.log(f"WARN {tool} failed — continuing package with available artifacts")

    if not rtx_ready(ctx):
        from forge.tools import run_rtx
        r = run_rtx(ctx, engine)
        if not r.ok:
            engine.log("WARN rtx build failed — packaging kernel without queen-browser")

    return run_field_package(ctx, engine)


FIELD_TOOLS = {
    "field_substrate": ("KILROY substrate sync", "field", run_field_substrate, check_field_substrate,
                        "KILROY/scripts/kilroy-become-substrate.sh"),
    "field_kernel": ("Build Field Kernel bzImage", "field", run_field_kernel, check_field_kernel,
                     "KILROY/scripts/build-kilroy.sh"),
    "field_boot": ("Grok secure boot image", "field", run_field_boot, check_field_boot,
                   "KILROY/scripts/grok-mkimage.sh"),
    "field_rootfs": ("KILROY production rootfs", "field", run_field_rootfs, check_field_rootfs,
                     "KILROY/rootfs/build-production-rootfs.sh"),
    "field_package": ("Seal one sovereign field", "field", run_field_package, check_field_package, None),
    "field_publish": ("Publish to field drive", "field", run_field_publish, check_field_publish, None),
    "field": ("Full field pipeline", "field", run_field, check_field_package, None),
}

FIELD_ORDER = ["field_substrate", "field_kernel", "field_boot", "field_rootfs", "rtx", "field_package"]