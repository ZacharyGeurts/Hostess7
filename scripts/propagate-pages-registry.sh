#!/usr/bin/env bash
# Instant-export endpoint registry → Hostess7/docs/api/*.json (no full pages-publish).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export NEXUS_INSTALL_ROOT="$ROOT"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-state}"
PY="${PYTHON:-python3}"

log() { printf '[propagate-pages] %s\n' "$*"; }

WITNESS="${1:-propagate-pages-registry.sh}"
if [[ "$WITNESS" == "--push" ]]; then
  WITNESS="propagate-pages-registry.sh"
  PUSH=1
else
  PUSH="${PROPAGATE_PUSH:-0}"
fi
[[ "${2:-}" == "--push" ]] && PUSH=1

log "instant registry → Hostess7/docs/api/"
"$PY" "$ROOT/lib/field-endpoint-registry.py" propagate --witness="$WITNESS"

if [[ "$PUSH" -eq 1 ]]; then
  API_DIR="$ROOT/Hostess7/docs/api"
  if [[ -d "$ROOT/.git" ]] && [[ -d "$API_DIR" ]]; then
    (
      cd "$ROOT"
      git add Hostess7/docs/api/field-endpoint-registry.json \
        Hostess7/docs/api/field-pages-movement.json \
        Hostess7/docs/api/field-endpoint-registry-routes.json \
        Hostess7/docs/api/field-endpoint-registry-ledger.json 2>/dev/null || true
      if git diff --cached --quiet; then
        log "registry API files already committed"
      else
        git -c user.email="gzac5314@users.noreply.github.com" -c user.name="ZacharyGeurts" \
          commit -m "pages: instant endpoint registry propagation"
        if [[ -x "$ROOT/scripts/github-unflake.sh" ]]; then
          "$ROOT/scripts/github-unflake.sh" push main || log "WARN: push skipped"
        else
          git push origin main 2>/dev/null || git push 2>/dev/null || log "WARN: push skipped"
        fi
        log "pushed — Hostess7 Pages Actions will deploy api/ snapshots"
      fi
    )
  fi
fi

log "done — loopback /api/field-endpoint-registry is live; Pages static follows push/CI"