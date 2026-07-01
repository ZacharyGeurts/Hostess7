#!/usr/bin/env bash
# Pack minimal embed tarball — hostess7-1.0.7e-embed.tar.gz
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${ROOT}/dist"
NAME="hostess7-1.0.7e-embed"
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

tar -czf "$OUT/${NAME}.tar.gz" -C "$OUT" "$NAME"
sha256sum "$OUT/${NAME}.tar.gz" >"$OUT/${NAME}.tar.gz.sha256"
echo "packed: $OUT/${NAME}.tar.gz"
cat "$OUT/${NAME}.tar.gz.sha256"