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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/impl/wire-stack.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Wire SG stack siblings into NewLatest — one operational tree.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PARENT="$(cd "${ROOT}/.." && pwd)"

STACK=(
  AMOURANTHRTX
  AmmoCode
  Grok16
  GrokPy
  PythonG
  KILROY
  Final_Eye
  Final_Ear
  Final_Mouth
  World_Redata
  World_Repack
  Field_Primer
  Field_Research
  Spiderweb
  GIMP
  GIMP-Field
  OBS-Field
  OBS-FieldVoiceFilter
  KeePass-Field
  GDB-Field
  ammosecurity
  Kill-Grok-Orphans
)

wired=0
skipped=0
missing=0

for name in "${STACK[@]}"; do
  target="${PARENT}/${name}"
  link="${ROOT}/${name}"
  if [[ -L "$link" ]]; then
    echo "skip  ${name} (symlink exists -> $(readlink "$link"))"
    skipped=$((skipped + 1))
    continue
  fi
  if [[ -e "$link" && ! -L "$link" ]]; then
    echo "skip  ${name} (real directory in NewLatest — not replacing)"
    skipped=$((skipped + 1))
    continue
  fi
  if [[ ! -e "$target" ]]; then
    echo "miss  ${name} (no ${target})"
    missing=$((missing + 1))
    continue
  fi
  ln -sfn "$target" "$link"
  echo "link  ${name} -> ${target}"
  wired=$((wired + 1))
done

# Training viewer lives inside NewLatest
if [[ ! -d "${ROOT}/hostess7-training-viewer" && -d "${PARENT}/hostess7-training-viewer" ]]; then
  mv "${PARENT}/hostess7-training-viewer" "${ROOT}/"
  echo "move  hostess7-training-viewer -> NewLatest/"
  wired=$((wired + 1))
fi
if [[ -d "${ROOT}/hostess7-training-viewer" && ! -e "${PARENT}/hostess7-training-viewer" ]]; then
  ln -sfn "${ROOT}/hostess7-training-viewer" "${PARENT}/hostess7-training-viewer"
  echo "link  ../hostess7-training-viewer (compat)"
fi

# Legacy SG/Hostess7 -> NewLatest/Hostess7
if [[ ! -e "${PARENT}/Hostess7" ]]; then
  ln -sfn "${ROOT}/Hostess7" "${PARENT}/Hostess7"
  echo "link  ../Hostess7 -> NewLatest/Hostess7"
fi

echo "--- wired=${wired} skipped=${skipped} missing=${missing} root=${ROOT}"
