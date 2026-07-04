#!/usr/bin/env bash
# GitHub lanes — probe, configure remotes, push via first working lane.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SECURE="${ROOT}/Hostess7/scripts/hostess7_secure_git.py"
if [[ -f "${HOME}/.config/ammo-shield/github-lane.env" ]]; then
  # shellcheck source=/dev/null
  source "${HOME}/.config/ammo-shield/github-lane.env"
fi
export HOSTESS7_PRESUME_HOSTILE="${HOSTESS7_PRESUME_HOSTILE:-1}"
export HOSTESS7_GIT_TUNNEL="${HOSTESS7_GIT_TUNNEL:-tunnel}"
export HOSTESS7_GIT_SKIP_API_TLS="${HOSTESS7_GIT_SKIP_API_TLS:-1}"
OWNER="${HOSTESS7_GITHUB_OWNER:-ZacharyGeurts}"
REPO="${HOSTESS7_GITHUB_REPO:-Hostess7}"

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

usage() {
  cat <<EOF
github-lanes.sh — all GitHub push lanes for Hostess7

  ./scripts/github-lanes.sh probe          JSON lane probe (SSH :22, tunnel :443, HTTPS, Pages)
  ./scripts/github-lanes.sh setup-remotes  origin + origin-tunnel + origin-https remotes
  ./scripts/github-lanes.sh verify         secure git verify (push posture)
  ./scripts/github-lanes.sh push [branch]  multi-lane push (default: main)
  ./scripts/github-lanes.sh pages-clear     Cancel stuck Pages runs (queue hygiene)
  ./scripts/github-lanes.sh pages-dispatch  Clear stuck + workflow_dispatch Pages deploy

Environment:
  HOSTESS7_GIT_TUNNEL=direct|tunnel   force SSH route
  HOSTESS7_GIT_SKIP_API_TLS=1         skip api.github.com TLS probe (ISP flake)
  GITHUB_TOKEN / HOSTESS7_GITHUB_TOKEN  HTTPS push lane
EOF
}

cmd_probe() {
  ensure_truth_dns
  python3 "$SECURE" lanes
}

cmd_setup_remotes() {
  cd "$ROOT"
  git remote get-url origin >/dev/null 2>&1 \
    && git remote set-url origin "git@github.com:${OWNER}/${REPO}.git" \
    || git remote add origin "git@github.com:${OWNER}/${REPO}.git"
  git remote get-url origin-tunnel >/dev/null 2>&1 \
    && git remote set-url origin-tunnel "ssh://git@ssh.github.com:443/${OWNER}/${REPO}.git" \
    || git remote add origin-tunnel "ssh://git@ssh.github.com:443/${OWNER}/${REPO}.git"
  if [[ -n "${GITHUB_TOKEN:-${HOSTESS7_GITHUB_TOKEN:-}}" ]]; then
    tok="${HOSTESS7_GITHUB_TOKEN:-$GITHUB_TOKEN}"
    git remote get-url origin-https >/dev/null 2>&1 \
      && git remote set-url origin-https "https://x-access-token:${tok}@github.com/${OWNER}/${REPO}.git" \
      || git remote add origin-https "https://x-access-token:${tok}@github.com/${OWNER}/${REPO}.git"
  fi
  echo "remotes:"
  git remote -v | grep -E 'origin|origin-tunnel|origin-https' || git remote -v
}

cmd_verify() {
  ensure_truth_dns
  export HOSTESS7_GIT_SKIP_API_TLS="${HOSTESS7_GIT_SKIP_API_TLS:-1}"
  python3 "$SECURE" verify "$ROOT"
}

cmd_push() {
  local branch="${1:-main}"
  ensure_truth_dns
  export HOSTESS7_GIT_SKIP_API_TLS="${HOSTESS7_GIT_SKIP_API_TLS:-1}"
  cmd_setup_remotes >/dev/null
  python3 "$SECURE" push "$ROOT" --branch "$branch" --remote "git@github.com:${OWNER}/${REPO}.git"
  if git diff-tree --no-commit-id --name-only -r HEAD 2>/dev/null | grep -qE '^Hostess7/docs/|^\.github/workflows/hostess7-pages\.yml'; then
    bash "${ROOT}/scripts/github-pages-queue.sh" cancel-stuck 2>/dev/null || true
    if [[ "${GITHUB_PAGES_AUTO_DISPATCH:-1}" == "1" ]]; then
      bash "${ROOT}/scripts/github-pages-queue.sh" dispatch 2>/dev/null || true
    fi
  fi
}

cmd_pages_clear() {
  bash "${ROOT}/scripts/github-pages-queue.sh" cancel-stuck
}

cmd_pages_dispatch() {
  bash "${ROOT}/scripts/github-pages-queue.sh" dispatch
}

main() {
  local cmd="${1:-probe}"
  shift || true
  case "$cmd" in
    -h|--help|help) usage ;;
    probe|lanes) cmd_probe ;;
    setup|setup-remotes|remotes) cmd_setup_remotes ;;
    verify) cmd_verify ;;
    push) cmd_push "${1:-main}" ;;
    pages-clear|pages_clear) cmd_pages_clear ;;
    pages-dispatch|pages_dispatch) cmd_pages_dispatch ;;
    *)
      echo "unknown: $cmd" >&2
      usage
      exit 1
      ;;
  esac
}

main "$@"