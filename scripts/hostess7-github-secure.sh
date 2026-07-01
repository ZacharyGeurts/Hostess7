#!/usr/bin/env bash
# Hostess7 secure GitHub — verify route, push, or full publish (replaces plain HTTPS git)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SECURE="${ROOT}/scripts/hostess7_secure_git.py"
CMD="${1:-verify}"

export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-$(cd "$ROOT/.." && pwd)}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-${NEXUS_INSTALL_ROOT}/.nexus-state}"

case "$CMD" in
  verify|route|audit)
    shift || true
    exec pythong "$SECURE" "$CMD" "$@"
    ;;
  push)
    shift
    DIR="${1:-${HOSTESS7_SECURE_PUBLISH_DIR:-${NEXUS_INSTALL_ROOT}/dist/hostess7-github-publish}}"
    shift || true
    pythong "$SECURE" verify
    exec pythong "$SECURE" push "$DIR" "$@"
    ;;
  publish|release)
    shift
    exec bash "${ROOT}/scripts/hostess7-github-publish.sh" "$@"
    ;;
  clone)
    shift
    DEST="${1:?usage: hostess7-github-secure.sh clone DEST [--remote URL]}"
    shift
    pythong "$SECURE" verify
    exec pythong "$SECURE" clone "$DEST" "$@"
    ;;
  -h|--help|help)
    cat <<'EOF'
Hostess7 secure git — pinned GitHub SSH keys, MITM-resistant

  ./Hostess7.sh github-secure verify     Match keys, DNS, anti-redirect/hook audit
  ./Hostess7.sh github-secure audit [DIR]  Scan git config/hooks for hijacks
  ./Hostess7.sh github-secure route        Pick direct :22 or tunnel :443
  ./Hostess7.sh github-secure publish      Stage Hostess7 + push + Pages
  ./Hostess7.sh github-secure push [DIR]   Push staged repo (--branch --remote --tag)
  ./Hostess7.sh github-secure clone DEST   Clone via pinned SSH

  HOSTESS7_GIT_TUNNEL=direct|tunnel — force route
EOF
    ;;
  *)
    echo "unknown: $CMD (try verify|route|publish|push|clone)" >&2
    exit 1
    ;;
esac