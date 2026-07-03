#!/usr/bin/env bash
# Publish web stack starting from Hostess 7 — wiki → H7updater → hubs → profile.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export HOSTESS7_VERSION="${HOSTESS7_VERSION:-3.0.7-beta5}"
export H7UPDATER_VERSION="${H7UPDATER_VERSION:-1.0.0}"
export STACK_VERSION="${STACK_VERSION:-3.0.7-beta5}"
export GNUEOL_TERMINAL_VERSION="${GNUEOL_TERMINAL_VERSION:-3.0.7-beta5}"
export PROFILE_VERSION="${PROFILE_VERSION:-stack}"

log() { echo "==> $*"; }

log "Kill preflight — secure kill · anti-hook · RE-KILL caches"
bash "${ROOT}/scripts/publish-kill-preflight.sh" || true

log "Hostess 7 wiki"
bash "${ROOT}/scripts/publish-hostess7-wiki.sh"

log "H7updater (stack manifest + Pages)"
bash "${ROOT}/scripts/publish-h7updater-github.sh"

log "GNUEOLTerminal — full GNU Technical wiki + RTX terminal"
bash "${ROOT}/scripts/publish-gnueol-terminal-github.sh" --push || true

log "Hostess 7 full stack Pages"
bash "${ROOT}/scripts/publish-hostess7-pages.sh" || true

log "NEXUS C2 basement — /command/"
bash "${ROOT}/scripts/publish-command-pages.sh" || true

log "AmmoCode editor Pages"
bash "${ROOT}/scripts/publish-ammocode-pages.sh" || true

log "KILROY online test Pages"
bash "${ROOT}/scripts/publish-kilroy-pages.sh" || true

log "Stack redirect hubs + AmmoOS manual"
bash "${ROOT}/scripts/publish-stack-pages.sh"

log "GitHub profile sync + ZacharyGeurts Pages"
bash "${ROOT}/scripts/sync-github-profile.sh"
bash "${ROOT}/scripts/publish-profile-pages.sh"

log "done — web stack:"
echo "  https://zacharygeurts.github.io/ZacharyGeurts/"
echo "  https://zacharygeurts.github.io/Hostess7/     (full stack)"
echo "  https://zacharygeurts.github.io/AmmoCode/     (editor)"
echo "  https://zacharygeurts.github.io/KILROY/        (online test)"
echo "  https://zacharygeurts.github.io/H7updater/"
echo "  https://github.com/ZacharyGeurts/Hostess7/wiki"