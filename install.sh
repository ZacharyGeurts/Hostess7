#!/usr/bin/env bash
# NEXUS Field Installer — NXF-driven portable or system install.
#
#   ./install.sh              Portable — no password, start menu icon
#   ./install.sh --system     Full install — UAC-style Allow, then OS admin auth once
#   curl -fsSL …/install-remote.sh | bash   GitHub one-liner
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

MODE="portable"
for arg in "$@"; do
  case "$arg" in
    --system|--full|-s) MODE="system" ;;
    --from-github|--github|-g) exec bash "${ROOT}/lib/nxf-install.sh" --from-github --mode "$MODE" ;;
    --help|-h)
      cat <<'EOF'
NEXUS Field Installer (NXF)

  ./install.sh              Portable install (recommended)
                            · No admin password
                            · Start menu shortcut · Queen browser shell

  ./install.sh --system     Full system install (Linux)
                            · One admin approval · systemd + Tristate F9

  ./install.sh --from-github
                            Fetch latest.nxf + source tarball from GitHub

  install-remote.sh         curl | bash one-liner from GitHub main

  After install:
    ./Queen/scripts/run-queen.sh   Queen web browser (9481)
    ./nexus.sh                     NEXUS field panel (9477)

Needs: python3, curl
EOF
      exit 0
      ;;
  esac
done

exec bash "${ROOT}/lib/nxf-install.sh" --mode "$MODE" "$@"