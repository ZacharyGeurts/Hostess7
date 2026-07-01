#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/nexus-update.py" ]]
  [[ -f "${ROOT}/lib/nexus-file-catalog.py" ]]
  [[ -f "${ROOT}/lib/nexus-incremental-update.py" ]]
  [[ -x "${ROOT}/lib/nexus-update-apply.sh" ]]
  grep -q '/api/update/check' "${ROOT}/lib/threat-panel-http.py"
  grep -q '/api/update/apply' "${ROOT}/lib/threat-panel-http.py"
  grep -q '/api/update/sudo-prompt' "${ROOT}/lib/threat-panel-http.py"
  grep -q '/api/nexus/catalog' "${ROOT}/lib/threat-panel-http.py"
  grep -q '_spawn_nexus_update_apply' "${ROOT}/lib/threat-panel-http.py"
  grep -q 'github-update.lock' "${ROOT}/lib/nexus-update-lock.py"
  grep -q '_resolve_nexus_source_root' "${ROOT}/lib/threat-panel-http.py"
  grep -q 'NEXUS_UPDATE_TARBALL_URL' "${ROOT}/lib/nexus-update-apply.sh"
  grep -q 'NEXUS_UPDATE_APPLY_VIA' "${ROOT}/lib/nexus-update-apply.sh"
  grep -q '_apply_incremental' "${ROOT}/lib/nexus-update-apply.sh"
  grep -q 'download_tarball' "${ROOT}/lib/nexus-update-apply.sh"
  grep -q 'install-all.sh' "${ROOT}/lib/nexus-update-apply.sh"
  grep -q 'NEXUS_UPDATE_MODE' "${ROOT}/config/nexus.conf"
  grep -q 'source_tarball' "${ROOT}/lib/nexus-update.py"
  grep -q 'nexus-upgrade-btn' "${ROOT}/panel/threat-panel.html"
  grep -q 'nexus-restart-btn' "${ROOT}/panel/threat-panel.html"
  grep -q 'promptUpdateSudo' "${ROOT}/panel/threat-panel.html"
  grep -q '"incremental"' "${ROOT}/nxf/latest.nxf"
out=$("$PY" "${ROOT}/lib/nexus-file-catalog.py" stats 2>/dev/null || true); grep -q '"file_count"'
  ! grep -q 'window.open(data.release_url' "${ROOT}/panel/threat-panel.html"
out=$("$PY" "${ROOT}/lib/nexus-update.py" 2>/dev/null || true); grep -q '"current"'
out=$("$PY" "${ROOT}/lib/nexus-update.py" 2>/dev/null || true); grep -q 'release_tarball'
  NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$ROOT" \
    "$PY" - <<'PY'
import importlib.util
import os
from pathlib import Path
root = Path(os.environ["NEXUS_INSTALL_ROOT"])
spec = importlib.util.spec_from_file_location("tph", root / "lib" / "threat-panel-http.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
src = mod._resolve_nexus_source_root()
assert src and ((src / "install-all.sh").is_file() or (src / "stealth_install.sh").is_file()), src
PY
