#!/usr/bin/env bash
# Truth DNS table hygiene — clean (safe) vs clear (destructive, i-know required).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-$ROOT}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-state}"

usage() {
  cat <<EOF
dns-clean-tables.sh — we are the DNS servers

  ./scripts/dns-clean-tables.sh clean     safe hygiene (default) — expire stale, reconcile
  ./scripts/dns-clean-tables.sh clear       DESTRUCTIVE wipe — requires I_KNOW_DNS_CLEAR=1

Clean: tail logs, expire stale shard/probe rows, enforce resolv, rebuild panels.
Clear: truncate logs, remove probe caches, flush stub — only when you know.
EOF
}

run_clean() {
  if [[ -f "${ROOT}/lib/field-dns.sh" ]]; then
    # shellcheck source=/dev/null
    source "${ROOT}/lib/field-dns.sh"
    nexus_field_dns_enforce_cycle 2>/dev/null || true
  fi
  python3 "${ROOT}/lib/field-dns-table-clean.py" clean
}

run_clear() {
  if [[ "${I_KNOW_DNS_CLEAR:-}" != "1" ]]; then
    echo "REFUSED: clear is destructive. Export I_KNOW_DNS_CLEAR=1 only if you know what you are doing." >&2
    exit 2
  fi
  local extra=(--i-know)
  [[ " $* " == *" --dhcp "* ]] && extra+=(--dhcp-leases)
  python3 "${ROOT}/lib/field-dns-table-clean.py" clear "${extra[@]}"
}

case "${1:-clean}" in
  -h|--help|help) usage ;;
  clean) run_clean ;;
  clear) shift || true; run_clear "$@" ;;
  *)
    echo "unknown: $1 (use clean or clear)" >&2
    usage
    exit 1
    ;;
esac