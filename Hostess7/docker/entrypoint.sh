#!/usr/bin/env bash
set -euo pipefail

export HOSTESS7_WAR_PROFILE="${HOSTESS7_WAR_PROFILE:-1}"
export HOSTESS7_LICENSE_MODE="${HOSTESS7_LICENSE_MODE:-war}"

if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; then
  export HOSTESS7_RTX_DETECTED=1
  echo "[hostess7] RTX GPU detected"
else
  export HOSTESS7_RTX_DETECTED=0
fi

python -m hostess7.cohesion iq >/dev/null 2>&1 || true
exec "$@"