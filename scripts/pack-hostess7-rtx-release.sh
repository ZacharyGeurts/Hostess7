#!/usr/bin/env bash
# Pack RTX-supported executables for Hostess7 GitHub release (multi-platform).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
_parent="$(cd "$ROOT/.." && pwd)"
if [[ -z "${NEXUS_INSTALL_ROOT:-}" ]]; then
  if [[ "$_parent" == */NewLatest || -f "$_parent/lib/nexus-common.sh" ]]; then
    NL="$_parent"
  elif [[ -d "$_parent/NewLatest" ]]; then
    NL="$_parent/NewLatest"
  else
    NL="$_parent"
  fi
else
  NL="${NEXUS_INSTALL_ROOT}"
fi
export NEXUS_INSTALL_ROOT="$NL"
export SG_ROOT="${SG_ROOT:-$(cd "$NL/.." && pwd)}"
# shellcheck source=hostess7-version.sh
source "$ROOT/scripts/hostess7-version.sh"
export GROK16_ROOT="${GROK16_ROOT:-$NL/Grok16}"
export AMOURANTHRTX_ROOT="${AMOURANTHRTX_ROOT:-$SG_ROOT/AMOURANTHRTX}"
export QUEEN_ROOT="${QUEEN_ROOT:-$NL/Queen}"

VER="$HOSTESS7_VERSION"
TAG="v${VER}"
DIST="${ROOT}/dist"
MANIFEST="${ROOT}/data/hostess7-rtx-executables.json"
BUILD="${BUILD_RTX:-0}"
PUSH="${PUSH_RTX:-0}"
PLATFORMS="${RTX_PLATFORMS:-all}"

log() { printf '[hostess7-rtx-release] %s\n' "$*"; }

resolve_first() {
  local p
  for p in "$@"; do
    [[ -n "$p" && -f "$p" && -x "$p" ]] && { printf '%s\n' "$p"; return 0; }
  done
  return 1
}

try_build() {
  [[ "$BUILD" == "1" ]] || return 0
  log "build RTX stack (G16_RTX_GATE_FORCE=1)"
  export G16_RTX_GATE_FORCE="${G16_RTX_GATE_FORCE:-1}"
  export GROK16_FIELD_PROFILE="${GROK16_FIELD_PROFILE:-queen_rtx}"
  if [[ -x "$NL/Queen/scripts/g16-build.sh" ]]; then
    bash "$NL/Queen/scripts/g16-build.sh" queen-rtx 2>&1 | tail -20 || \
      bash "$NL/Queen/scripts/g16-build.sh" build 2>&1 | tail -20 || log "WARN g16-build partial"
  fi
  if [[ -x "$NL/scripts/integrate-amouranthrtx.sh" ]]; then
    bash "$NL/scripts/integrate-amouranthrtx.sh" --build 2>&1 | tail -12 || log "WARN integrate partial"
  fi
  if command -v pythong >/dev/null 2>&1 && [[ -f "$NL/Queen/lib/queen-forge.py" ]]; then
    pythong "$NL/Queen/lib/queen-forge.py" run rtx 2>&1 | tail -15 || log "WARN forge rtx partial"
  elif command -v python3 >/dev/null 2>&1 && [[ -f "$NL/Queen/lib/queen-forge.py" ]]; then
    python3 "$NL/Queen/lib/queen-forge.py" run rtx 2>&1 | tail -15 || log "WARN forge rtx partial"
  fi
  if [[ -x "$AMOURANTHRTX_ROOT/kilroy.sh" ]]; then
    bash "$AMOURANTHRTX_ROOT/kilroy.sh" release 2>&1 | tail -10 || log "WARN kilroy release partial"
  fi
}

candidate_paths() {
  local exe_id="$1" bin_subdir="$2" os="$3"
  local win_suffix=""
  [[ "$os" == "windows" ]] && win_suffix=".exe"

  case "$exe_id" in
    queen-browser)
      printf '%s\n' \
        "$NL/Queen/build/rtx/bin/${bin_subdir}/queen-browser${win_suffix}" \
        "$NL/Queen/build/bin/${bin_subdir}/queen-browser${win_suffix}" \
        "$NL/Queen/bin/queen-browser${win_suffix}"
      if [[ "$bin_subdir" == "Linux" ]]; then
        printf '%s\n' "$NL/Queen/field/sovereign/queen/bin/queen-browser"
      fi
      ;;
    amouranth_engine)
      printf '%s\n' \
        "$NL/Queen/build/rtx/bin/${bin_subdir}/amouranth_engine${win_suffix}" \
        "$NL/Queen/build/bin/${bin_subdir}/amouranth_engine${win_suffix}"
      ;;
    AMOURANTHRTX)
      printf '%s\n' \
        "$NL/Queen/build/rtx/bin/${bin_subdir}/AMOURANTHRTX${win_suffix}" \
        "$NL/Queen/build/bin/${bin_subdir}/AMOURANTHRTX${win_suffix}" \
        "$AMOURANTHRTX_ROOT/build-release/bin/Kilroy/AMOURANTHRTX${win_suffix}" \
        "$AMOURANTHRTX_ROOT/build/bin/Kilroy/AMOURANTHRTX${win_suffix}" \
        "$AMOURANTHRTX_ROOT/build/bin/${bin_subdir}/AMOURANTHRTX${win_suffix}"
      ;;
  esac
}

copy_shaders() {
  local stage="$1"
  mkdir -p "$stage/assets/shaders/compute"
  for dir in \
    "$AMOURANTHRTX_ROOT/assets/shaders/compute" \
    "$NL/Queen/assets/shaders/compute" \
    "$NL/Queen/build/rtx/assets/shaders/compute"; do
    [[ -d "$dir" ]] || continue
    cp -a "$dir/"*.spv "$stage/assets/shaders/compute/" 2>/dev/null || true
  done
}

write_bootstrap() {
  local stage="$1" platform_id="$2" os="$3" arch="$4"
  mkdir -p "$stage/bootstrap" "$stage/doctrine"
  cat >"$stage/bootstrap/build-rtx.sh" <<'BOOT'
#!/usr/bin/env bash
# Build Hostess7 RTX executables on this platform.
set -euo pipefail
export G16_RTX_GATE_FORCE=1
export GROK16_FIELD_PROFILE=queen_rtx
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
echo "[rtx-bootstrap] clone full stack, then:"
echo "  git clone https://github.com/ZacharyGeurts/Hostess7.git"
echo "  cd Hostess7 && ./Hostess7.sh boot"
echo "  ./Hostess7.sh queen-field-build rtx"
echo "  ./Hostess7.sh rtx-release pack"
BOOT
  chmod +x "$stage/bootstrap/build-rtx.sh"

  if [[ "$os" == "windows" ]]; then
    cat >"$stage/bootstrap/build-rtx.ps1" <<'PS1'
# Hostess7 RTX — Windows bootstrap
$env:G16_RTX_GATE_FORCE = "1"
$env:GROK16_FIELD_PROFILE = "queen_rtx"
Write-Host "Option A: WSL2 — extract hostess7-*-rtx-linux-gnu-x86_64.tar.gz and run ./bin/queen-browser"
Write-Host "Option B: Native — clone Hostess7, run queen-field-build rtx in MSYS2/WSL g16 toolchain"
PS1
    [[ -f "$NL/stealth.ps1" ]] && cp "$NL/stealth.ps1" "$stage/bootstrap/"
  fi

  for doc in \
    "$NL/Queen/data/field-rtx-sovereign.json" \
    "$NL/data/vulkan-os-doctrine.json" \
    "$NL/data/nexus-g16-compile-doctrine.json"; do
    [[ -f "$doc" ]] && cp "$doc" "$stage/doctrine/"
  done
  [[ -f "$MANIFEST" ]] && cp "$MANIFEST" "$stage/doctrine/hostess7-rtx-executables.json"
}

pack_platform() {
  local platform_id="$1" os="$2" arch="$3" format="$4" bin_subdir="$5" rtx_tier="$6"
  local pkg="hostess7-${VER}-rtx-${platform_id}"
  local stage="${DIST}/${pkg}"
  local asset=""
  local found=0
  local mode="bootstrap"

  rm -rf "$stage"
  mkdir -p "$stage/bin" "$stage/assets/shaders/compute"

  local exe_id path dest name
  for exe_id in queen-browser amouranth_engine AMOURANTHRTX; do
    path=""
    while IFS= read -r cand; do
      [[ -z "$cand" ]] && continue
      if [[ -f "$cand" ]]; then
        if [[ -x "$cand" ]] || [[ "$os" == "windows" ]]; then
          path="$cand"
          break
        fi
      fi
    done < <(candidate_paths "$exe_id" "$bin_subdir" "$os")

    if [[ -n "$path" ]]; then
      if [[ "$os" == "windows" ]]; then
        name="${exe_id}.exe"
        [[ "$exe_id" == "queen-browser" ]] && name="queen-browser.exe"
      else
        name="$exe_id"
      fi
      dest="$stage/bin/$name"
      cp -a "$path" "$dest"
      chmod +x "$dest" 2>/dev/null || true
      found=$((found + 1))
      log "  packed ${platform_id}: ${name}"
    fi
  done

  copy_shaders "$stage"
  write_bootstrap "$stage" "$platform_id" "$os" "$arch"

  if [[ "$found" -gt 0 ]]; then
    mode="native"
  elif [[ "$rtx_tier" == "primary" ]]; then
    log "ERROR: ${platform_id} requires queen-browser — none found"
    return 1
  fi

  python3 - <<PY
import hashlib, json, os
from datetime import datetime, timezone
from pathlib import Path

stage = Path("${stage}")
bins = sorted(stage.glob("bin/*"))
files = []
for b in bins:
    if not b.is_file():
        continue
    h = hashlib.sha256(b.read_bytes()).hexdigest()
    files.append({
        "id": b.name,
        "path": f"bin/{b.name}",
        "bytes": b.stat().st_size,
        "sha256": h,
    })
shaders = sorted(stage.glob("assets/shaders/compute/*.spv"))
doc = {
    "schema": "hostess7-rtx-release/v1",
    "version": "${VER}",
    "tag": "${TAG}",
    "lane": "rtx-executables",
    "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "platform": "${platform_id}",
    "os": "${os}",
    "arch": "${arch}",
    "mode": "${mode}",
    "rtx_support": True,
    "requires_rtx_gpu_on_build": False,
    "files": files,
    "shader_count": len(shaders),
    "run": {
        "queen": "./bin/queen-browser --queen" if "${os}" != "windows" else r".\\bin\\queen-browser.exe --queen",
        "field_die": "./bin/AMOURANTHRTX",
        "panel": "http://127.0.0.1:9481/world/browser.html",
        "bootstrap": "./bootstrap/build-rtx.sh",
    },
}
(stage / "manifest.json").write_text(json.dumps(doc, indent=2) + "\\n", encoding="utf-8")
print(json.dumps({"platform": "${platform_id}", "mode": "${mode}", "binaries": len(files)}, indent=2))
PY

  cat >"$stage/README-RTX.txt" <<EOF
Hostess7 ${VER} — RTX executables (${platform_id})
====================================================
Mode: ${mode} | NVIDIA RTX / Intel Arc / AMD via SPIR-V (queen_rtx)

EOF
  if [[ "$mode" == "native" ]]; then
    cat >>"$stage/README-RTX.txt" <<EOF
  Extract and run:
    ./bin/queen-browser --queen
  Panel: http://127.0.0.1:9481/world/browser.html

EOF
  else
    cat >>"$stage/README-RTX.txt" <<EOF
  Bootstrap kit — build on target with RTX-capable GPU:
    ./bootstrap/build-rtx.sh
  Or clone Hostess7 and: ./Hostess7.sh queen-field-build rtx
  Windows WSL2: use linux-gnu-x86_64 RTX tarball.

EOF
  fi
  cat >>"$stage/README-RTX.txt" <<EOF
GitHub brain: https://zacharygeurts.github.io/Hostess7/
Full sovereign: git clone + ./Hostess7.sh boot
EOF

  if [[ "$format" == "zip" ]]; then
    asset="${DIST}/${pkg}.zip"
    rm -f "$asset"
    if command -v zip >/dev/null 2>&1; then
      (cd "$DIST" && zip -qr "$asset" "$pkg")
    else
      log "ERROR: zip required for ${platform_id}"
      return 1
    fi
  else
    asset="${DIST}/${pkg}.tar.gz"
    rm -f "$asset"
    (cd "$DIST" && tar -czf "$asset" "$pkg")
  fi
  sha256sum "$asset" >"${asset}.sha256"
  log "packed ${asset} ($(du -h "$asset" | awk '{print $1}')) mode=${mode}"
  printf '%s\n' "$asset"
}

write_platform_index() {
  python3 - <<PY
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path

root = Path("${ROOT}")
dist = Path("${DIST}")
ver = "${VER}"
src = json.loads((root / "data/hostess7-rtx-executables.json").read_text(encoding="utf-8"))
assets = []
for pattern in (f"hostess7-{ver}-rtx-*.tar.gz", f"hostess7-{ver}-rtx-*.zip"):
    for path in sorted(dist.glob(pattern)):
        data = path.read_bytes()
        stem = path.name
        for ext in (".tar.gz", ".zip"):
            if stem.endswith(ext):
                stem = stem[: -len(ext)]
                break
        assets.append({
            "file": path.name,
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "platform": stem.replace(f"hostess7-{ver}-rtx-", ""),
        })
out = {
    "schema": "hostess7-rtx-platform-index/v1",
    "version": ver,
    "tag": f"v{ver}",
    "released_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "requires_rtx_gpu_on_build": False,
    "platforms": src.get("platforms", []),
    "assets": assets,
}
idx = dist / f"hostess7-{ver}-rtx-platforms.json"
idx.write_text(json.dumps(out, indent=2) + "\\n", encoding="utf-8")
print(f"wrote {idx.name} ({len(assets)} assets)")
PY
}

pack_all() {
  mkdir -p "$DIST"
  local packed=0
  local platform_id os arch format bin_subdir rtx_tier
  local assets=()

  python3 - <<PY >"${DIST}/.rtx-platforms.tsv"
import json
from pathlib import Path
src = json.loads(Path("${MANIFEST}").read_text(encoding="utf-8"))
filter_p = "${PLATFORMS}"
for p in src.get("platforms", []):
    if filter_p != "all" and p["id"] not in filter_p.split(","):
        continue
    print("\t".join([
        p["id"], p["os"], p["arch"], p["format"],
        p.get("bin_subdir", "Linux"), p.get("rtx_tier", "bootstrap"),
    ]))
PY

  while IFS=$'\t' read -r platform_id os arch format bin_subdir rtx_tier; do
    [[ -z "$platform_id" ]] && continue
    log "platform ${platform_id}"
    if asset="$(pack_platform "$platform_id" "$os" "$arch" "$format" "$bin_subdir" "$rtx_tier")"; then
      assets+=("$asset")
      packed=$((packed + 1))
    fi
  done < "${DIST}/.rtx-platforms.tsv"
  rm -f "${DIST}/.rtx-platforms.tsv"

  write_platform_index
  if [[ "$packed" -eq 0 ]]; then
    log "ERROR: no platform packs produced"
    return 1
  fi
  log "packed ${packed} platform(s)"
}

upload_release() {
  [[ "$PUSH" == "1" ]] || { log "set PUSH_RTX=1 to upload"; return 0; }
  local notes="${ROOT}/RELEASE-${VER}-RTX.md"
  [[ -f "$notes" ]] || notes="${ROOT}/RELEASE-RTX.md"
  local uploads=()
  local f
  for f in "${DIST}"/hostess7-${VER}-rtx-*.{tar.gz,zip}; do
    [[ -f "$f" ]] && uploads+=("$f" "${f}.sha256")
  done
  [[ -f "${DIST}/hostess7-${VER}-rtx-platforms.json" ]] && uploads+=("${DIST}/hostess7-${VER}-rtx-platforms.json")
  if [[ ${#uploads[@]} -eq 0 ]]; then
    log "ERROR: nothing to upload"
    return 1
  fi
  if gh release view "$TAG" --repo ZacharyGeurts/Hostess7 >/dev/null 2>&1; then
    log "upload to existing ${TAG}"
    gh release upload "$TAG" "${uploads[@]}" --repo ZacharyGeurts/Hostess7 --clobber
    [[ -f "$notes" ]] && gh release edit "$TAG" --repo ZacharyGeurts/Hostess7 --notes-file "$notes" 2>/dev/null || true
  else
    log "create release ${TAG}"
    gh release create "$TAG" --repo ZacharyGeurts/Hostess7 --title "Hostess7 ${VER}" --notes-file "$notes" "${uploads[@]}"
  fi
  log "release → https://github.com/ZacharyGeurts/Hostess7/releases/tag/${TAG}"
}

try_build
pack_all
upload_release
log "done"