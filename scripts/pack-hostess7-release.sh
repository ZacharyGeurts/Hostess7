# AmmoLang boundary route — AML_BUILD=1 universal boundary
_aml_find_root() {
  local d="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  while [[ "$d" != "/" ]]; do
    [[ -f "$d/lib/ammolang-run.sh" ]] && echo "$d" && return 0
    d="$(dirname "$d")"
  done
  return 1
}
if [[ "${AML_BUILD:-1}" != "0" ]] && [[ -z "${AML_BOUNDARY_ACTIVE:-}" ]]; then
  _AML_ROOT="$(_aml_find_root 2>/dev/null || true)"
  if [[ -n "$_AML_ROOT" ]]; then
    export AML_BOUNDARY_ACTIVE=1
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/pack-hostess7-release.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Pack Hostess7 1.0 beta archives — full stack (AmmoOS, Grok16, Queen, et al.)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=/dev/null
source "${ROOT}/lib/nexus-common.sh"
nexus_release_host_path

HOSTESS7_VERSION="${HOSTESS7_VERSION:-1.0.0-beta}"
VER="${HOSTESS7_VERSION}"
DIST="${ROOT}/dist"

TAR_ONLY=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    -v|--version) VER="$2"; shift 2 ;;
    --tar-only) TAR_ONLY=1; shift ;;
    *) echo "unknown: $1" >&2; exit 1 ;;
  esac
done

STAGE="${DIST}/hostess7-${VER}"
PKG_NAME="hostess7-${VER}-source.h7e"
INST_NAME="hostess7-${VER}-installers.tar.gz"
WIN_NAME="hostess7-${VER}-windows-x86_64.zip"
MAX_GITHUB_BYTES=$((2 * 1024 * 1024 * 1024))

mkdir -p "$DIST"
log_progress() { echo "[pack $(date +%H:%M:%S)] $*"; }

if [[ "$TAR_ONLY" -eq 1 ]]; then
  [[ -d "$STAGE" ]] || { echo "missing stage ${STAGE} — run full pack first" >&2; exit 1; }
  echo "=== tar-only (stage present) ==="
else
  rm -rf "$STAGE"
  mkdir -p "$STAGE"
  echo "=== staging Hostess7 ${VER} (full stack) ==="
  log_progress "staging tree"
  rsync -a \
  --exclude='.git' \
  --exclude='.pages-hub-*' \
  --exclude='data/combinatronic-visuals' \
  --exclude='data/combinatronic-visuals/**' \
  --exclude='panel/profile-*' \
  --exclude='Grok16/vendor' \
  --exclude='Grok16/vendor/**' \
  --exclude='_archive' \
  --exclude='_archive/**' \
  --exclude='.nexus-field-drive' \
  --exclude='KILROY/build' \
  --exclude='KILROY/build/**' \
  --exclude='.nexus-state' \
  --exclude='.nexus-state-test' \
  --exclude='dist' \
  --exclude='cache' \
  --exclude='state' \
  --exclude='Hostess7/cache' \
  --exclude='Hostess7/zac' \
  --exclude='Queen/vendor' \
  --exclude='Queen/cache' \
  --exclude='Queen/build' \
  --exclude='Queen/build-*' \
  --exclude='Queen/field-gecko/profile' \
  --exclude='Queen/.venv*' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='*.log' \
  --exclude='*.jsonl' \
  --exclude='*.img' \
  --exclude='.wiki-publish' \
  --exclude='.pages-publish' \
  --exclude='.github/workflows/ci.yml' \
  --exclude='.github/workflows/release-v10.yml' \
  --exclude='Hostess7/.github' \
  --exclude='linux-kernel' \
  --exclude='linux-kernel/**' \
  "${ROOT}/" "${STAGE}/"

echo "=== materialize stack siblings ==="
STACK_SYMLINKS=(
  AMOURANTHRTX Grok16 GrokPy PythonG KILROY Final_Eye Final_Ear GrokLab
  ZNEWOCR ZOCR ZNetwork World_Redata World_Repack Field_Primer Spiderweb
)
for name in "${STACK_SYMLINKS[@]}"; do
  link="${STAGE}/${name}"
  [[ -L "$link" ]] || continue
  target="$(readlink -f "$link" 2>/dev/null || true)"
  [[ -n "$target" && -d "$target" ]] || continue
  echo "  ${name} <- ${target}"
  rm -f "$link"
  mkdir -p "$link"
  RSYNC_EX=(
    --exclude='.git' --exclude='build' --exclude='build-cmake' --exclude='cache'
    --exclude='vendor' --exclude='.venv*' --exclude='__pycache__' --exclude='*.pyc'
  )
  copied=0
  if rsync -a "${RSYNC_EX[@]}" "${target}/" "${link}/" 2>/dev/null; then
    copied=1
  elif [[ "$name" == "KILROY" && -n "${SUDO_PASS:-}" ]]; then
    printf '%s\n' "$SUDO_PASS" | sudo -S rsync -a "${RSYNC_EX[@]}" "${target}/" "${link}/" && copied=1
    printf '%s\n' "$SUDO_PASS" | sudo -S chown -R "$(id -un):$(id -gn)" "${link}" 2>/dev/null || true
  elif [[ "$name" == "KILROY" ]]; then
    sudo rsync -a "${RSYNC_EX[@]}" "${target}/" "${link}/" 2>/dev/null && copied=1
    sudo chown -R "$(id -un):$(id -gn)" "${link}" 2>/dev/null || true
  fi
  if [[ "$copied" -eq 0 ]]; then
    rsync -a --ignore-errors "${RSYNC_EX[@]}" "${target}/" "${link}/" || true
  fi
done

if [[ -f "${STAGE}/README-HOSTESS7.md" ]]; then
  cp "${STAGE}/README-HOSTESS7.md" "${STAGE}/README.md"
fi
if [[ -f "${ROOT}/LICENSE-HOSTESS7" ]]; then
  cp "${ROOT}/LICENSE-HOSTESS7" "${STAGE}/LICENSE"
fi
fi

echo "=== prune stage blobs >95MB (GitHub file limit) ==="
while IFS= read -r -d '' blob; do
  log_progress "drop ${blob#"${STAGE}/"}"
  rm -f "$blob"
done < <(find "$STAGE" -type f -size +95M -print0 2>/dev/null || true)

echo "=== source H7e archive ==="
rm -f "${DIST}/hostess7-${VER}-source.tar.gz" "${DIST}/hostess7-${VER}-source.h7" \
  "${DIST}/${PKG_NAME}"
log_progress "H7e pack (tar + zlib)"
log_progress "AI progress → ${NEXUS_STATE_DIR:-${ROOT}/.nexus-state}/field-compression-progress.json"
export FIELD_TECH_NO_FIELD=1
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-${ROOT}/.nexus-state}"
python3 - <<PY
import json
from pathlib import Path
from importlib.util import module_from_spec, spec_from_file_location

root = Path("${ROOT}")
dist = Path("${DIST}")
ver = "${VER}"
stage = dist / f"hostess7-{ver}"
spec = spec_from_file_location("field_h7_format", root / "lib" / "field-h7-format.py")
mod = module_from_spec(spec)
spec.loader.exec_module(mod)
out = mod.pack_folder_h7e(
    stage,
    dist / f"hostess7-{ver}-source.h7e",
    meta={"product": "Hostess7", "version": ver, "channel": "release", "release_role": "hostess7_source"},
)
print(json.dumps(out, indent=2))
if not out.get("ok"):
    raise SystemExit(1)
PY
PKG_BYTES=$(stat -c%s "${DIST}/${PKG_NAME}" 2>/dev/null || echo 0)
if [[ "$PKG_BYTES" -gt "$MAX_GITHUB_BYTES" ]]; then
  echo "WARN: ${PKG_NAME} is ${PKG_BYTES} bytes — exceeds GitHub 2GiB release asset limit" >&2
else
  log_progress "source H7e done ($(du -h "${DIST}/${PKG_NAME}" | awk '{print $1}') — under 2GiB)"
fi

echo "=== installers tarball ==="
INSTALL_STAGE="${DIST}/hostess7-${VER}-installers"
rm -rf "$INSTALL_STAGE"
mkdir -p "$INSTALL_STAGE/scripts"
for f in install-all.sh genius_shield.sh nexus.sh stealth_install.sh install.sh stealth.ps1 INSTALL-README.md assets/nexus-field.png README.md; do
  [[ -f "${STAGE}/${f}" ]] && cp "${STAGE}/${f}" "$INSTALL_STAGE/"
done
cp -a "${STAGE}/scripts/hostess7-"*.sh "${STAGE}/scripts/pack-hostess7-release.sh" \
  "${STAGE}/scripts/ammoos-unpack-source.sh" \
  "${STAGE}/scripts/wire-stack.sh" "${STAGE}/scripts/nexus-boot-impl.sh" \
  "$INSTALL_STAGE/scripts/" 2>/dev/null || true
cp -f "${ROOT}/scripts/ammoos-unpack-source.sh" "${ROOT}/scripts/field-h7e-extract.sh" \
  "${ROOT}/scripts/pack-hostess7-release.sh" \
  "$INSTALL_STAGE/scripts/" 2>/dev/null || true
mkdir -p "$INSTALL_STAGE/lib"
cp -f "${ROOT}/lib/field-h7-format.py" "$INSTALL_STAGE/lib/"
chmod +x "$INSTALL_STAGE/scripts/ammoos-unpack-source.sh" 2>/dev/null || true
[[ -d "${STAGE}/install" ]] && cp -a "${STAGE}/install/." "$INSTALL_STAGE/install/"
tar -czf "${DIST}/${INST_NAME}" -C "${DIST}" "hostess7-${VER}-installers"

if command -v zip >/dev/null 2>&1 && [[ -f "${STAGE}/stealth.ps1" ]]; then
  echo "=== windows zip ==="
  WIN_STAGE="${DIST}/hostess7-${VER}-windows"
  rm -rf "$WIN_STAGE"
  mkdir -p "$WIN_STAGE"
  cp "${STAGE}/stealth.ps1" "${STAGE}/README.md" "${STAGE}/INSTALL-README.md" "$WIN_STAGE/" 2>/dev/null || true
  cp -a "${STAGE}/scripts/ammoos-launch-verify.sh" "$WIN_STAGE/" 2>/dev/null || true
  (cd "$WIN_STAGE" && zip -qr "${DIST}/${WIN_NAME}" .)
fi

echo "=== platform manifest ==="
python3 - <<PY
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path("${ROOT}")
dist = Path("${DIST}")
ver = "${VER}"
src = json.loads((root / "data/hostess7-platform-release.json").read_text(encoding="utf-8"))
src["version"] = ver
src["tag"] = f"v{ver}"
src["released_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
out = dist / f"hostess7-{ver}-platforms.json"
out.write_text(json.dumps(src, indent=2) + "\\n", encoding="utf-8")

lines = [
    f"# Hostess 7 {ver} — platform bootstrap matrix",
    "",
    f"**Tag:** \`v{ver}\` · **Model:** source bootstrap per platform",
    "",
    "Hostess 7 ships **full stack source + installers** — AmmoOS, Grok16, Queen, KILROY wired.",
    "",
    "## Quick start (Linux x86_64)",
    "",
    "\`\`\`bash",
    f"./scripts/field-h7e-extract.sh hostess7-{ver}-source.h7e",
    f"cd hostess7-{ver}",
    "./scripts/wire-stack.sh",
    "sudo ./install-all.sh",
    "./Hostess7/Hostess7.sh on",
    "\`\`\`",
    "",
    "## Platforms",
    "",
    "| ID | OS | Arch | Bootstrap |",
    "|----|-----|------|-----------|",
]
for p in src.get("platforms", []):
    boot = p.get("bootstrap", {})
    boot_s = ", ".join(f"{k}={v}" for k, v in boot.items() if not isinstance(v, dict))
    lines.append(f"| {p['id']} | {p['os']} | {p['arch']} | {boot_s} |")
(dist / f"hostess7-{ver}-PLATFORMS.md").write_text("\\n".join(lines) + "\\n", encoding="utf-8")
print(f"wrote {out.name}")
PY

echo "=== pack complete ==="
ls -lh "${DIST}"/hostess7-${VER}* 2>/dev/null || true