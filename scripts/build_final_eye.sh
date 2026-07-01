# AmmoLang boundary route — AML_BUILD=1 universal boundary
_aml_find_root() {
  local d="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  while [[ "$d" != "/" ]]; do
    [[ -f "$d/lib/ammolang-run.sh" ]] && echo "$d" && return 0
    d="$(dirname "$d")"
  done
  return 1
}
if [[ "${AML_BUILD:-1}" != "0" ]] && [[ -z "${AML_BOUNDARY_ACTIVE:-}" ]]; then
  _AML_ROOT="$(_aml_find_root 2>/dev/null || true)"
  if [[ -n "$_AML_ROOT" ]]; then
    export AML_BOUNDARY_ACTIVE=1
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/build_final_eye.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# AmmoLang subfolder route — AML_BUILD=1 (default)
_aml_find_root() {
  local d="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  while [[ "$d" != "/" ]]; do
    [[ -f "$d/lib/ammolang-run.sh" ]] && echo "$d" && return 0
    d="$(dirname "$d")"
  done
  return 1
}
if [[ "${AML_BUILD:-1}" != "0" ]]; then
  _AML_ROOT="$(_aml_find_root 2>/dev/null || true)"
  if [[ -n "$_AML_ROOT" ]]; then
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" final_eye_build "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

# Package Final_Eye v0.9 for GitHub — ZOCR + GrokMediaFormat
set -euo pipefail
SG="$(cd "$(dirname "$0")/.." && pwd)"
PACK="$SG/Final_Eye-packaging"
DEST="$SG/Final_Eye"
ZOCR="$SG/ZOCR"
GMF="$SG/GrokMediaFormat"
STAGE="$(mktemp -d)"

mkdir -p "$PACK/docs"

rsync -a \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  --exclude 'out/' \
  --exclude '*.png' \
  --exclude 'manifest.jsonl' \
  --exclude 'data/server.log' \
  --exclude 'data/poll.log' \
  --exclude 'data/*.pid' \
  --exclude 'data/*-ledger.jsonl' \
  --exclude 'data/vision-session.jsonl' \
  --exclude 'data/video-index.jsonl' \
  --exclude 'data/stream-index.jsonl' \
  --exclude 'data/stream-chain.jsonl' \
  --exclude 'data/neural-analysis.jsonl' \
  --exclude 'data/eye-teach.jsonl' \
  --exclude 'data/vigilance-log.jsonl' \
  --exclude 'data/pattern-security.jsonl' \
  "$ZOCR/" "$STAGE/"

rsync -a --exclude '__pycache__' --exclude 'tests/__pycache__' "$GMF/" "$STAGE/GrokMediaFormat/"

for f in VERSION .gitignore README.md CHANGELOG.md LICENSE requirements.txt; do
  [[ -f "$PACK/$f" ]] && cp "$PACK/$f" "$STAGE/$f"
done
[[ -d "$PACK/docs" ]] && cp -a "$PACK/docs/." "$STAGE/docs/"

: >"$STAGE/data/vision-session.jsonl"
echo '{"running":false,"profile":"idle"}' >"$STAGE/data/video-active.json"

chmod +x "$STAGE/start.sh" "$STAGE/tests/run_tests.sh" 2>/dev/null || true
rm -rf "$DEST"
mv "$STAGE" "$DEST"
echo "Built $DEST"
