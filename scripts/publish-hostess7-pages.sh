#!/usr/bin/env bash
# Publish Hostess7 full stack → GitHub Pages gh-pages branch.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
H7="${ROOT}/Hostess7/scripts/publish-hostess7-pages.sh"

if [[ -x "$H7" ]]; then
  exec bash "$H7" "$@"
fi

echo "Missing ${H7}" >&2
exit 1