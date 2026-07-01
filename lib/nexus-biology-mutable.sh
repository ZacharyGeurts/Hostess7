#!/bin/bash
# Biology-mutable paths — training, brain expansion, Hostess 7 internal biology never sealed/locked/restored.

NEXUS_BIOLOGY_MUTABLE_DOCTRINE="${NEXUS_BIOLOGY_MUTABLE_DOCTRINE:-${NEXUS_INSTALL_ROOT}/data/hostess7-biology-mutable-paths-doctrine.json}"

nexus_biology_mutable_prefixes() {
  local root="${NEXUS_INSTALL_ROOT}"
  printf '%s\n' \
    "${root}/.nexus-state" \
    "${root}/.nexus-field-drive" \
    "${root}/cache" \
    "${root}/state" \
    "${root}/Hostess7/cache" \
    "${root}/Hostess7/zac" \
    "${root}/Hostess7/data/runtime" \
    "${root}/Queen/cache" \
    "${root}/hostess7-training-viewer/runtime"
}

nexus_biology_mutable_segments() {
  printf '%s\n' \
    fieldstorage \
    team_staging \
    training \
    brain \
    biology \
    ingest \
    solidify \
    agents7
}

nexus_path_is_biology_mutable() {
  local path="$1" prefix seg base
  [[ -n "$path" && -n "${NEXUS_INSTALL_ROOT:-}" ]] || return 1

  if [[ "$path" != /* ]]; then
    path="${NEXUS_INSTALL_ROOT}/${path#./}"
  fi

  while IFS= read -r prefix; do
    [[ -n "$prefix" ]] || continue
    [[ "$path" == "$prefix" || "$path" == "$prefix/"* ]] && return 0
  done < <(nexus_biology_mutable_prefixes)

  while IFS= read -r seg; do
    [[ -n "$seg" ]] || continue
    [[ "$path" == *"/${seg}/"* || "$path" == *"/${seg}" ]] && return 0
  done < <(nexus_biology_mutable_segments)

  base="${path##*/}"
  case "$base" in
    hostess7-full-train-progress.json|nexus-executable-seal.json) return 0 ;;
    hostess7-*-panel.json) return 0 ;;
  esac

  return 1
}

nexus_filter_biology_mutable_paths() {
  local path
  while IFS= read -r path; do
    [[ -n "$path" ]] || continue
    nexus_path_is_biology_mutable "$path" && continue
    printf '%s\n' "$path"
  done
}