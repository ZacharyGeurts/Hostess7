#!/usr/bin/env bash
# NEXUS Field macOS installer — Applications bundle + ZNetwork build
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
# shellcheck source=/dev/null
source "${ROOT}/lib/installer.sh"
echo "NEXUS Field macOS installer…"
nexus_install_check_deps || exit 1
nexus_install_portable "$ROOT"
echo "Open: ${HOME}/Applications/NEXUS-Field.app"