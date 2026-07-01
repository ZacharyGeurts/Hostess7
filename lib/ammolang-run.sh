#!/usr/bin/env bash
# AmmoLang script router — ALL field tasks run here (hang guard · freeze assist · kit Grok16).
set -euo pipefail

_LIB="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${_LIB}/ammolang-kit-env.sh"

ROOT="${NEXUS_INSTALL_ROOT}"
export TDIR="${TDIR:-${HOME}/.grok/projects/home-default-Desktop-SG/terminals}"
export AML_GITHUB_TRANSPORT="${AML_GITHUB_TRANSPORT:-mcp_secure}"
export G16_MONITOR_HEARTBEAT_SEC="${G16_MONITOR_HEARTBEAT_SEC:-8}"

# Secure GitHub MCP — default AmmoLang transport (not raw TCP)
MCP_ENV="${HOME}/.config/sg/github-mcp.env"
if [[ -f "$MCP_ENV" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$MCP_ENV"
  set +a
  export GH_TOKEN="${GH_TOKEN:-${GITHUB_MCP_TOKEN:-}}"
fi

ammolang_run_py() {
  printf '%s' "${NEXUS_PYTHONG}"
}

route="${1:-tasks}"
shift || true
extra=("$@")

# Universal boundary — pass target + args to protective AML shell
if [[ -n "$route" && "$route" != "tasks" && "$route" != "list" && "$route" != "assist" ]]; then
  export AML_BOUNDARY_TARGET="${route}"
  if [[ ${#extra[@]} -gt 0 ]]; then
    export AML_BOUNDARY_ARGS_JSON="$(printf '%s\n' "${extra[@]}" | python3 -c 'import json,sys; print(json.dumps([l.rstrip("\n") for l in sys.stdin]))' 2>/dev/null || echo '[]')"
  else
    export AML_BOUNDARY_ARGS_JSON="${AML_BOUNDARY_ARGS_JSON:-[]}"
  fi
  if [[ "$route" == "exec" || "$route" == "boundary" || "$route" == "any" || "$route" == "run" ]]; then
    [[ ${#extra[@]} -gt 0 ]] && export AML_BOUNDARY_TARGET="${extra[0]}"
    if [[ ${#extra[@]} -gt 1 ]]; then
      export AML_BOUNDARY_ARGS_JSON="$(printf '%s\n' "${extra[@]:1}" | python3 -c 'import json,sys; print(json.dumps([l.rstrip("\n") for l in sys.stdin]))' 2>/dev/null || echo '[]')"
    else
      export AML_BOUNDARY_ARGS_JSON="[]"
    fi
  fi
fi

PY="$(ammolang_run_py)"
BUILD="${ROOT}/lib/field-ammolang-build.py"
MONSTER="${ROOT}/lib/field-monster-launch.sh"
[[ -f "$BUILD" ]] || { echo "ammolang-run: missing field-ammolang-build.py" >&2; exit 1; }

# Beta 4 operator hold — blocks full release + library prep until cleared
if [[ "$route" == "beta4_release" || "$route" == "beta4_library_prep" ]]; then
  if [[ "${BETA4_FORCE_RELEASE:-}" != "1" ]]; then
    _HOLD_RC=0
    _HOLD_JSON="$("$PY" "$ROOT/lib/field-beta4-ready.py" hold_status 2>/dev/null)" || _HOLD_RC=$?
    if [[ "$_HOLD_RC" -eq 2 ]]; then
      echo "ammolang-run: Beta 4 HELD ($route) — python3 lib/field-beta4-ready.py resume" >&2
      echo "$_HOLD_JSON" >&2
      exit 2
    fi
  fi
fi

monster_exec() {
  local label="$1"
  shift
  if [[ -x "$MONSTER" ]] && [[ "${MONSTER_SHELL:-1}" != "0" ]]; then
    exec "$MONSTER" --label "$label" -- "$@"
  fi
  exec "$@"
}

if [[ "$route" == "tasks" || "$route" == "list" ]]; then
  monster_exec "ammolang:tasks" "$PY" "$BUILD" tasks
fi

if [[ "$route" == "assist" ]]; then
  monster_exec "ammolang:assist" "$PY" "$BUILD" assist "${extra[@]:-all}"
fi

dry=()
[[ " ${extra[*]} " == *" --dry "* ]] && dry=(--dry)

export PYTHONUNBUFFERED=1

monster_exec "ammolang:${route}" "$PY" "$BUILD" task "$route" "${extra[@]}" "${dry[@]}"