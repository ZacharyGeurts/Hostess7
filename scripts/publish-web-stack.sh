#!/usr/bin/env bash
# Publish web stack starting from Hostess 7 — wiki → H7updater → hubs → profile.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export HOSTESS7_VERSION="${HOSTESS7_VERSION:-2.0.7h}"
export H7UPDATER_VERSION="${H7UPDATER_VERSION:-1.0.0}"
export STACK_VERSION="${STACK_VERSION:-2.0.0-beta5}"
export PROFILE_VERSION="${PROFILE_VERSION:-stack}"

log() { echo "==> $*"; }

log "Hostess 7 wiki"
bash "${ROOT}/scripts/publish-hostess7-wiki.sh"

log "H7updater (stack manifest + Pages)"
bash "${ROOT}/scripts/publish-h7updater-github.sh"

log "Hostess 7 field Pages"
if [[ -x "${ROOT}/Hostess7/scripts/publish-hostess7-pages.sh" ]]; then
  bash "${ROOT}/Hostess7/scripts/publish-hostess7-pages.sh" || true
fi

log "Stack redirect hubs + AmmoOS manual"
bash "${ROOT}/scripts/publish-stack-pages.sh"

log "GitHub profile sync + ZacharyGeurts Pages"
bash "${ROOT}/scripts/sync-github-profile.sh"
bash "${ROOT}/scripts/publish-profile-pages.sh"

log "done — web stack:"
echo "  https://zacharygeurts.github.io/ZacharyGeurts/"
echo "  https://zacharygeurts.github.io/Hostess7/"
echo "  https://zacharygeurts.github.io/H7updater/"
echo "  https://github.com/ZacharyGeurts/Hostess7/wiki"