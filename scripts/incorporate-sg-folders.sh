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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/incorporate-sg-folders.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Incorporate SG root folders into NewLatest (canonical AmmoOS), then remove SG copies.
# Consulted: Hostess7 neural stack, ironclad-doctrine, CHIPS/sense-package wire model.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SG="$(cd "${ROOT}/.." && pwd)"

MOVE=(
  Final_Mouth
  KeePass-Field
  GDB-Field
  Field_Research
  Kill-Grok-Orphans
  GIMP-Field
  OBS-Field
  GIMP
)

log() { echo "[incorporate] $*"; }

move_into_newlatest() {
  local name="$1"
  local src="${SG}/${name}"
  local dst="${ROOT}/${name}"
  if [[ ! -e "$src" ]]; then
    log "skip ${name} (no SG copy)"
    return 0
  fi
  if [[ -e "$dst" ]]; then
    if [[ -L "$dst" ]]; then
      rm -f "$dst"
    else
      log "skip ${name} (already in NewLatest)"
      return 0
    fi
  fi
  mv "$src" "$dst"
  log "move  ${name} -> NewLatest/"
}

# ammosecurity: merge Security extras first
if [[ -d "${SG}/Security" && -d "${SG}/ammosecurity" ]]; then
  for f in README.md LICENSE AMMOSECURITY_V2_DESIGN.md secure_clipboard.sh secure_clipboard.ps1 install_clipboard.sh sclipd.c; do
    if [[ -f "${SG}/Security/${f}" && ! -f "${SG}/ammosecurity/${f}" ]]; then
      cp -a "${SG}/Security/${f}" "${SG}/ammosecurity/${f}"
      log "merge Security/${f} -> ammosecurity/"
    fi
  done
  rm -rf "${SG}/Security"
  log "delete Security/ (merged into ammosecurity)"
fi
move_into_newlatest ammosecurity

# OBS-FieldVoiceFilter: replace partial NewLatest stub with full SG tree
if [[ -d "${SG}/OBS-FieldVoiceFilter" ]]; then
  if [[ -d "${ROOT}/OBS-FieldVoiceFilter" && ! -L "${ROOT}/OBS-FieldVoiceFilter" ]]; then
    rm -rf "${ROOT}/OBS-FieldVoiceFilter"
    log "remove partial NewLatest/OBS-FieldVoiceFilter"
  fi
  move_into_newlatest OBS-FieldVoiceFilter
fi

for name in "${MOVE[@]}"; do
  move_into_newlatest "$name"
done

# Retired stubs / duplicates (no runtime stack)
for doomed in Latest ZNetwork ammo GrokMediaFormat BarbieGirl bin compat; do
  target="${SG}/${doomed}"
  [[ -e "$target" ]] || continue
  if [[ "$doomed" == "bin" || "$doomed" == "compat" ]]; then
    if [[ -z "$(ls -A "$target" 2>/dev/null)" ]]; then
      rmdir "$target" 2>/dev/null || rm -rf "$target"
      log "delete empty ${doomed}/"
      continue
    fi
  fi
  rm -rf "$target"
  log "delete ${doomed}/ (stub or superseded)"
done

# AmmoOS publish tree: drop stale backups and duplicate stack copies (keep .git product shell)
if [[ -d "${SG}/AmmoOS" ]]; then
  for bak in "${SG}/AmmoOS"/Queen.bak-*; do
    [[ -d "$bak" ]] || continue
    rm -rf "$bak"
    log "delete AmmoOS/$(basename "$bak")"
  done
  for dup in Grok16 Final_Eye ZNEWOCR KILROY AMOURANTHRTX Field_Primer ZOCR World_Redata ZNetwork; do
    p="${SG}/AmmoOS/${dup}"
    [[ -e "$p" && ! -L "$p" ]] || continue
    rm -rf "$p"
    log "delete AmmoOS duplicate ${dup}/"
  done
  if [[ -d "${SG}/AmmoOS/NewLatest" ]]; then
    rm -rf "${SG}/AmmoOS/NewLatest"
    log "delete nested AmmoOS/NewLatest/"
  fi
  # Wire publish mirror to canonical siblings
  (cd "${SG}/AmmoOS" && for name in "${MOVE[@]}" ammosecurity OBS-FieldVoiceFilter; do
    [[ -d "${ROOT}/${name}" ]] || continue
    ln -sfn "../NewLatest/${name}" "$name" 2>/dev/null || true
  done)
fi

log "done root=${ROOT}"