#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Regenerate apt Packages indices for Hostess7 Field tree.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
POOL="$HERE/pool/main"
BIN="$HERE/dists/field/main/binary-amd64"
mkdir -p "$POOL" "$BIN"

if command -v dpkg-scanpackages >/dev/null; then
  (cd "$HERE" && dpkg-scanpackages -m pool/main /dev/null >"$BIN/Packages")
else
  # Minimal empty index if no debs yet
  : >"$BIN/Packages"
  if compgen -G "$POOL/*/*.deb" >/dev/null || compgen -G "$POOL/*.deb" >/dev/null; then
    echo "WARN: dpkg-scanpackages missing; install dpkg-dev to index debs" >&2
  fi
fi
gzip -9 -c "$BIN/Packages" >"$BIN/Packages.gz"
# Release file (unsigned bootstrap; apt source uses trusted=yes)
cat >"$HERE/dists/field/Release" <<EOF
Origin: Hostess7
Label: Hostess7 Field
Suite: field
Codename: field
Architectures: amd64
Components: main
Description: Hostess 7 Field packages for Spear — sole apt origin
Date: $(date -Ru)
EOF
echo "regen OK → $BIN/Packages ($(wc -l <"$BIN/Packages") lines)"
