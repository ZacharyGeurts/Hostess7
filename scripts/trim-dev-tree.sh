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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/trim-dev-tree.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Trim NewLatest dev cruft before release — GitHub-friendly tarball sizes.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
AGGRESSIVE="${TRIM_AGGRESSIVE:-0}"

echo "=== trim-dev-tree @ ${ROOT} ==="

rm -f "${ROOT}/amouranth_engine.log" \
  "${ROOT}/Queen/amouranth_engine.log" \
  "${ROOT}/Queen/.queen-browser.log" \
  "${ROOT}/MANIFEST.sha256.bak" \
  "${ROOT}/hostess7-training-viewer/viewer.log" \
  "${ROOT}/hostess7-training-viewer/.viewer.pid" 2>/dev/null || true

rm -rf \
  "${ROOT}/state" \
  "${ROOT}/.nexus-state" \
  "${ROOT}/.nexus-state-test" \
  "${ROOT}/.nexus-field-drive" \
  "${ROOT}/cache" \
  "${ROOT}/Textbook/staging" \
  "${ROOT}/Queen/field-gecko/profile" \
  "${ROOT}/Queen/.venv-browser" \
  "${ROOT}/Queen/.venv-test" \
  "${ROOT}/Hostess7/cache" \
  "${ROOT}/Hostess7/zac" 2>/dev/null || true

# Stale pack staging (keep dist/*.tar.gz)
for stale in "${ROOT}"/dist/nexus-shield-*/; do
  [[ -d "$stale" ]] || continue
  case "$stale" in
    *-installers/) continue ;;
    *-source.tar.gz) continue ;;
  esac
  if [[ "$stale" == "${ROOT}/dist/nexus-shield-"*"/" ]]; then
    rm -rf "$stale"
    echo "removed stale staging: $stale"
  fi
done

if [[ "$AGGRESSIVE" == "1" ]]; then
  echo "=== aggressive trim (rebuild artifacts) ==="
  rm -rf \
    "${ROOT}/Queen/build" \
    "${ROOT}/Queen/build-"* \
    "${ROOT}/Queen/vendor" \
    "${ROOT}/Queen/cache" \
    "${ROOT}/Queen/field/sovereign" 2>/dev/null || true
fi

echo "=== post-trim size ==="
du -sh "${ROOT}" 2>/dev/null || true
echo "done — run: scripts/pack-release.sh"