#!/usr/bin/env bash
# Clone KeePassXC upstream for field rewrite / cross-platform hardening
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
UP="${KEEPASS_UPSTREAM_DIR:-$ROOT/upstream/keepassxc}"
REF="${KEEPASS_UPSTREAM_REF:-2.7.6}"
mkdir -p "$(dirname "$UP")"
if [[ -d "$UP/.git" ]]; then
  git -C "$UP" fetch --tags origin
  git -C "$UP" checkout "$REF" 2>/dev/null || git -C "$UP" checkout "refs/tags/$REF"
else
  git clone --depth 1 --branch "$REF" https://github.com/keepassxreboot/keepassxc.git "$UP"
fi
echo "upstream: $UP @ $REF"