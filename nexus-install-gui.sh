#!/usr/bin/env bash
# Deprecated — use ./nexus.sh --underlay (NEXUS Field OS).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
exec "${ROOT}/nexus.sh" --underlay "$@"