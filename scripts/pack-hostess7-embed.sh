#!/usr/bin/env bash
# Pack minimal embed tarball — hostess7-<version>-embed.tar.gz
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=hostess7-version.sh
source "$ROOT/scripts/hostess7-version.sh"
OUT="${ROOT}/dist"
NAME="hostess7-${HOSTESS7_VERSION}-embed"
STAGE="$OUT/$NAME"

rm -rf "$STAGE"
mkdir -p "$STAGE" "$OUT"

rsync -a \
  --exclude='.git' \
  --exclude='cache/fieldstorage/brain' \
  --exclude='cache/fieldstorage/textbooks' \
  --exclude='dist' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  "$ROOT/" "$STAGE/"

bash "$ROOT/scripts/verify-embed-install.sh" 2>/dev/null || echo "WARN: embed verify partial (pack continues)"

tar -czf "$OUT/${NAME}.tar.gz" -C "$OUT" "$NAME"
sha256sum "$OUT/${NAME}.tar.gz" >"$OUT/${NAME}.tar.gz.sha256"
echo "packed: $OUT/${NAME}.tar.gz"
cat "$OUT/${NAME}.tar.gz.sha256"