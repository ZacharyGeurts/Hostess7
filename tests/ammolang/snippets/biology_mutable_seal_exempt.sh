#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/nexus-biology-mutable.sh"
# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/nexus-executable-seal.sh"

test_path="${NEXUS_INSTALL_ROOT}/Hostess7/cache/fieldstorage/brain/biology/corpus.json"
nexus_path_is_biology_mutable "$test_path"

train_path="${NEXUS_STATE_DIR}/hostess7-full-train-progress.json"
nexus_path_is_biology_mutable "$train_path"

panel_path="${NEXUS_STATE_DIR}/hostess7-biology-panel.json"
nexus_path_is_biology_mutable "$panel_path"

lib_path="${NEXUS_INSTALL_ROOT}/lib/nexus-common.sh"
! nexus_path_is_biology_mutable "$lib_path"

nexus_executable_paths | while IFS= read -r exe; do
  [[ -n "$exe" ]] || continue
  ! nexus_path_is_biology_mutable "$exe"
done