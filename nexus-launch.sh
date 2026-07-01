#!/usr/bin/env bash
# Deprecated — use nexus.sh (single launcher).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
exec "${ROOT}/nexus.sh" "$@"