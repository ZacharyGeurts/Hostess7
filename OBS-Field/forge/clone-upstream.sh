#!/usr/bin/env bash
# Clone OBS Studio upstream for field rewrite / NVENC hardening
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
UP="${OBS_UPSTREAM_DIR:-$ROOT/upstream/obs-studio}"
REF="${OBS_UPSTREAM_REF:-30.0.2}"
mkdir -p "$(dirname "$UP")"
if [[ -d "$UP/.git" ]]; then
  git -C "$UP" fetch --tags origin
  git -C "$UP" checkout "$REF" 2>/dev/null || git -C "$UP" checkout "refs/tags/$REF"
else
  git clone --depth 1 --branch "$REF" https://github.com/obsproject/obs-studio.git "$UP" 2>/dev/null \
    || git clone --depth 1 https://github.com/obsproject/obs-studio.git "$UP"
fi
echo "upstream: $UP @ $(git -C "$UP" describe --tags --always 2>/dev/null || echo "$REF")"