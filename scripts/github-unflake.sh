#!/usr/bin/env bash
# Un-flake GitHub ISP path — presume MITM/hostile; audit DNS, flap, force tunnel lane.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-$ROOT}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-state}"

ensure_truth_dns() {
  if [[ -f "${ROOT}/lib/field-dns.sh" ]]; then
    # shellcheck source=/dev/null
    source "${ROOT}/lib/field-dns.sh"
    nexus_field_dns_enforce_cycle 2>/dev/null || true
  fi
  python3 "${ROOT}/lib/field-dns-resolve.py" ensure >/dev/null 2>&1 || true
}

# Source auto-mitigations if present
if [[ -f "${HOME}/.config/ammo-shield/github-lane.env" ]]; then
  # shellcheck source=/dev/null
  source "${HOME}/.config/ammo-shield/github-lane.env"
fi

usage() {
  cat <<EOF
github-unflake.sh — hostile ISP / MITM posture for GitHub

  ./scripts/github-unflake.sh audit [--apply]   DNS cross-check + flap probe + TLS
  ./scripts/github-unflake.sh push [branch]     audit --apply then multi-lane push
  ./scripts/github-unflake.sh status            lane probe + path panel summary

Defaults when hostile: HOSTESS7_GIT_TUNNEL=tunnel HOSTESS7_GIT_SKIP_API_TLS=1
EOF
}

cmd_audit() {
  local apply=""
  [[ " $* " == *" --apply "* ]] && apply="--apply"
  ensure_truth_dns
  python3 "${ROOT}/lib/field-github-path-harden.py" audit $apply
}

cmd_status() {
  export HOSTESS7_GIT_TUNNEL="${HOSTESS7_GIT_TUNNEL:-tunnel}"
  export HOSTESS7_GIT_SKIP_API_TLS="${HOSTESS7_GIT_SKIP_API_TLS:-1}"
  export HOSTESS7_PRESUME_HOSTILE="${HOSTESS7_PRESUME_HOSTILE:-1}"
  python3 "${ROOT}/lib/field-github-path-harden.py" panel 2>/dev/null | python3 -c "
import json,sys
p=json.load(sys.stdin)
print('verdict:', p.get('verdict'), 'route:', p.get('recommended_route'))
" 2>/dev/null || true
  "${ROOT}/scripts/github-lanes.sh" probe
}

cmd_push() {
  local branch="${1:-main}"
  ensure_truth_dns
  HOSTESS7_PATH_HARDEN_QUICK=1 cmd_audit --apply >/dev/null || true
  export HOSTESS7_GIT_TUNNEL="${HOSTESS7_GIT_TUNNEL:-tunnel}"
  export HOSTESS7_GIT_SKIP_API_TLS="${HOSTESS7_GIT_SKIP_API_TLS:-1}"
  export HOSTESS7_PRESUME_HOSTILE="${HOSTESS7_PRESUME_HOSTILE:-1}"
  "${ROOT}/scripts/github-lanes.sh" push "$branch"
}

main() {
  case "${1:-audit}" in
    -h|--help|help) usage ;;
    audit) shift; cmd_audit "$@" ;;
    status) cmd_status ;;
    push) shift; cmd_push "${1:-main}" ;;
    *) echo "unknown: $1" >&2; usage; exit 1 ;;
  esac
}

main "$@"