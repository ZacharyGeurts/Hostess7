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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/pack-release.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Pack NEXUS-Shield release archives for GitHub upload.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=/dev/null
source "${ROOT}/lib/nexus-common.sh"

usage() {
  cat <<'EOF'
Usage: pack-release.sh [--version VER] [--dry-run] [--help]

  --version VER   Override NEXUS_VERSION for this pack
  --dry-run       Show what would be packed without creating archives
  --help          Show this help
EOF
}

DRY_RUN=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    -n|--dry-run) DRY_RUN=1; shift ;;
    -v|--version)
      [[ $# -ge 2 ]] || { echo "--version requires a value" >&2; exit 1; }
      NEXUS_VERSION="$2"
      shift 2
      ;;
    *) echo "unknown option: $1" >&2; usage >&2; exit 1 ;;
  esac
done

VER="${NEXUS_VERSION}"
DIST="${ROOT}/dist"
STAGE="${DIST}/nexus-shield-${VER}"
PKG_NAME="nexus-shield-${VER}-source.tar.gz"
INST_NAME="nexus-shield-${VER}-installers.tar.gz"

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "dry-run: would pack ${VER} → ${DIST}/${PKG_NAME}"
  echo "excludes: .git dist cache state .nexus-* Queen/build Queen/vendor Hostess7/cache *.log"
  exit 0
fi

mkdir -p "$DIST"
rm -rf "$STAGE"
mkdir -p "$STAGE"

echo "=== staging ${VER} ==="
rsync -a \
  --exclude='.git' \
  --exclude='.nexus-state' \
  --exclude='.nexus-state-test' \
  --exclude='.nexus-field-drive' \
  --exclude='dist' \
  --exclude='cache' \
  --exclude='state' \
  --exclude='Hostess7/cache' \
  --exclude='Hostess7/zac' \
  --exclude='Queen/build' \
  --exclude='Queen/build-*' \
  --exclude='Queen/vendor' \
  --exclude='Queen/cache' \
  --exclude='Queen/field/sovereign' \
  --exclude='Queen/field-gecko/profile' \
  --exclude='Queen/.venv*' \
  --exclude='Textbook/staging' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.wiki-publish' \
  --exclude='.pages-publish' \
  --exclude='Queen/data/*.log' \
  --exclude='*.log' \
  --exclude='*.jsonl' \
  --exclude='*.img' \
  --exclude='hostess7-training-viewer/viewer.log' \
  --exclude='hostess7-training-viewer/.viewer.pid' \
  --exclude='MANIFEST.sha256.bak' \
  --exclude='AMOURANTHRTX' \
  --exclude='Grok16' \
  --exclude='GrokPy' \
  --exclude='PythonG' \
  --exclude='KILROY' \
  --exclude='Final_Eye' \
  --exclude='Final_Ear' \
  --exclude='ZNEWOCR' \
  --exclude='ZOCR' \
  --exclude='ZNetwork' \
  --exclude='World_Redata' \
  --exclude='World_Repack' \
  --exclude='Field_Primer' \
  --exclude='Spiderweb' \
  "${ROOT}/" "${STAGE}/"

echo "=== source tarball ==="
tar -czf "${DIST}/${PKG_NAME}" -C "${DIST}" "nexus-shield-${VER}"

echo "=== installers tarball ==="
INSTALL_STAGE="${DIST}/nexus-shield-${VER}-installers"
rm -rf "$INSTALL_STAGE"
mkdir -p "$INSTALL_STAGE/scripts" "$INSTALL_STAGE/install"
for f in install-all.sh genius_shield.sh nexus.sh stealth_install.sh install.sh INSTALL-README.md assets/nexus-field.png; do
  [[ -f "${ROOT}/${f}" ]] && cp "${ROOT}/${f}" "$INSTALL_STAGE/"
done
cp -a "${ROOT}/scripts/nexus-boot-impl.sh" "${ROOT}/scripts/wire-stack.sh" \
  "${ROOT}/scripts/migrate-nexus-state.sh" "${ROOT}/scripts/release.sh" \
  "$INSTALL_STAGE/scripts/" 2>/dev/null || true
[[ -d "${ROOT}/install" ]] && cp -a "${ROOT}/install/." "$INSTALL_STAGE/install/"
tar -czf "${DIST}/${INST_NAME}" -C "${DIST}" "nexus-shield-${VER}-installers"

echo "=== post-pack verification ==="
if tar -tzf "${DIST}/${PKG_NAME}" | grep -qE '(first-boot\.complete|amouranth_engine\.log|\.git/)'; then
  echo "FAIL: forbidden files leaked into ${PKG_NAME}" >&2
  exit 1
fi
echo "PASS: source tarball clean"

echo "=== file catalog ==="
CATALOG_NAME="nexus-file-catalog-${VER}.json"
NEXUS_INSTALL_ROOT="$ROOT" pythong "${ROOT}/lib/nexus-file-catalog.py" build "${ROOT}/data/nexus-file-catalog.json" >/dev/null
cp "${ROOT}/data/nexus-file-catalog.json" "${DIST}/${CATALOG_NAME}"
NEXUS_INSTALL_ROOT="$ROOT" pythong "${ROOT}/lib/nxf.py" write "${DIST}/nexus-shield-${VER}.nxf" >/dev/null
cp "${DIST}/nexus-shield-${VER}.nxf" "${ROOT}/nxf/latest.nxf"

(
  cd "$DIST"
  sha256sum "${PKG_NAME}" "${INST_NAME}" "${CATALOG_NAME}" "nexus-shield-${VER}.nxf" >"MANIFEST.sha256"
)
echo "wrote ${DIST}/MANIFEST.sha256"

rm -rf "$STAGE" "$INSTALL_STAGE"

ls -lh "${DIST}/${PKG_NAME}" "${DIST}/${INST_NAME}"
echo "packed: ${DIST}/${PKG_NAME}"
echo "packed: ${DIST}/${INST_NAME}"