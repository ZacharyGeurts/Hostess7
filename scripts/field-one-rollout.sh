#!/usr/bin/env bash
# Field 1 rollout — test → 10 at a time → double worldwide
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec bash "$ROOT/GrokLab/deploy/field-one-world-bring.sh" "${@:-test}"