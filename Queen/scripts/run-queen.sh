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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:Queen/scripts/run-queen.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Launch Queen sovereign RTX browser — everything inside Queen tree.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NEXUS_ROOT="$(cd "$ROOT/.." && pwd)"
SG="$(cd "$ROOT/../.." && pwd)"
_state_explicit=0
[[ -n "${NEXUS_STATE_DIR:-}" ]] && _state_explicit=1
_state_saved="${NEXUS_STATE_DIR:-}"
# shellcheck source=/dev/null
source "${NEXUS_ROOT}/lib/nexus-common.sh"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-${NEXUS_ROOT}}"
export NEXUS_FIELD_STANDALONE=1
nexus_init_runtime_paths
if [[ "$_state_explicit" -eq 1 ]]; then
  export NEXUS_STATE_DIR="$_state_saved"
fi
unset _state_explicit _state_saved

export SG_ROOT="${SG_ROOT:-$SG}"
export PATH="${SG}/GrokPy/bin:${SG}/PythonG/bin:${ROOT}/bin:${ROOT}/scripts:${PATH}"
export GPY16_ROOT="${GPY16_ROOT:-${SG}/GrokPy}"
PY="${ROOT}/scripts/queen-py"
BIN="${ROOT}/build/rtx/bin/Linux/queen-browser"
FINAL_EYE="${FINAL_EYE_ROOT:-${SG}/Final_Eye}"
FINAL_EAR="${FINAL_EAR_ROOT:-${SG}/Final_Ear}"
FINAL_EYE_PORT="${ZOCR_PORT:-${FINAL_EYE_PORT:-9479}}"
export QUEEN_ROOT="${ROOT}"
export FINAL_EYE_ROOT="${FINAL_EYE}"
export FINAL_EAR_ROOT="${FINAL_EAR}"
export QUEEN_SOVEREIGN=1
export NEXUS_QUEEN_SOVEREIGN=1
export QUEEN_BROWSER_ONLY="${QUEEN_BROWSER_ONLY:-1}"
export QUEEN_NO_OS_BROWSER="${QUEEN_NO_OS_BROWSER:-1}"
export NEXUS_FIELD_BROWSER_QUEEN="${NEXUS_FIELD_BROWSER_QUEEN:-1}"
export ZNETWORK_RELAYER="${ZNETWORK_RELAYER:-1}"
export ZNETWORK_INTERNET_PIPE_TARGET="${ZNETWORK_INTERNET_PIPE_TARGET:-100}"
export ZNETWORK_MODE="${ZNETWORK_MODE:-ACTIVE}"
export QUEEN_WORLD_ONLY=1
export NEXUS_EMBED_PANEL_IN_ENGINE="${NEXUS_EMBED_PANEL_IN_ENGINE:-0}"
export QUEEN_WORLD_PORT="${QUEEN_WORLD_PORT:-9481}"
export QUEEN_BENCHMARK_MODE="${QUEEN_BENCHMARK_MODE:-0}"
export QUEEN_INLINE_BROWSER="${QUEEN_INLINE_BROWSER:-1}"
export QUEEN_FAST_STATUS="${QUEEN_FAST_STATUS:-1}"
export QUEEN_STATUS_CACHE_SEC="${QUEEN_STATUS_CACHE_SEC:-5}"
if [[ "${QUEEN_BENCHMARK_MODE}" == "1" ]]; then
  export NEXUS_FIELD_THERMAL_GUARD=0
  export QUEEN_ALLOW_EXTERNAL_URLS=1
  export QUEEN_STATUS_CACHE_SEC="${QUEEN_STATUS_CACHE_SEC:-60}"
fi
export QUEEN_BROWSER_URL="${QUEEN_BROWSER_URL:-http://127.0.0.1:${QUEEN_WORLD_PORT}/world/browser.html}"
export NEXUS_PANEL_AUTO_OPEN=0
export NEXUS_NO_TRAY=1
export QUEEN_GROK_BUILD=1
export QUEEN_GROK_BUILD_SECURE=1
export NEXUS_AI_SECURE_CHANNEL=1
export QUEEN_AI_TELEMETRY_OK=1
export QUEEN_FIELD_GPU=1
export HOSTESS7_ROOT="${HOSTESS7_ROOT:-${SG}/Hostess7}"
export HOSTESS7_AI_PRIMARY="${HOSTESS7_AI_PRIMARY:-1}"
export HOSTESS7_AI_COMMUNIQUE="${HOSTESS7_AI_COMMUNIQUE:-1}"
export HOSTESS7_SUPERINTEL="${HOSTESS7_SUPERINTEL:-1}"
export GROK16_ROOT="${GROK16_ROOT:-${SG}/Grok16}"
if [[ -f "${ROOT}/../lib/kilroy-resolve.sh" ]]; then
  # shellcheck source=/dev/null
  source "${ROOT}/../lib/kilroy-resolve.sh"
  nexus_kilroy_export "$SG" 2>/dev/null || export KILROY_ROOT="${SG}/KILROY"
else
  export KILROY_ROOT="${KILROY_ROOT:-${SG}/../KILROY}"
  [[ -f "${KILROY_ROOT}/scripts/build-kilroy.sh" ]] || export KILROY_ROOT="${SG}/KILROY"
fi
export AMOURANTHRTX_ROOT="${AMOURANTHRTX_ROOT:-${SG}/AMOURANTHRTX}"
export QUEEN_INTERNAL_ONLY="${QUEEN_INTERNAL_ONLY:-1}"
export QUEEN_INSTANT_BROWSER="${QUEEN_INSTANT_BROWSER:-1}"
export NEXUS_RETIRE_AMOURANTHRTX_WINDOW="${NEXUS_RETIRE_AMOURANTHRTX_WINDOW:-1}"
export QUEEN_RETIRE_RTX_WINDOW="${QUEEN_RETIRE_RTX_WINDOW:-1}"
export QUEEN_RTX_CHROME="${QUEEN_RTX_CHROME:-0}"
if [[ -f "${NEXUS_ROOT}/lib/amouranthrtx-window-retire.sh" ]]; then
  # shellcheck source=/dev/null
  source "${NEXUS_ROOT}/lib/amouranthrtx-window-retire.sh"
  declare -f amouranthrtx_window_retire_cycle >/dev/null 2>&1 && amouranthrtx_window_retire_cycle || true
fi
export QUEEN_DISPLAY_REFRESH="${QUEEN_DISPLAY_REFRESH:-120}"
export NEXUS_FIELD_BROWSER_QUEEN="${NEXUS_FIELD_BROWSER_QUEEN:-0}"
export FINAL_EYE_ASSIST="${FINAL_EYE_ASSIST:-1}"
export FINAL_EYE_LOW_END="${FINAL_EYE_LOW_END:-1}"

# Final_Eye v1.1 assist tenant on :9479 (bounded, Teach authority)
if [[ -d "${FINAL_EYE}" && -f "${FINAL_EYE}/gui/app.py" ]]; then
  if ! curl -sf "http://127.0.0.1:${FINAL_EYE_PORT}/api/health" >/dev/null 2>&1; then
    echo "Starting Final_Eye v1.1 on :${FINAL_EYE_PORT}…"
    nohup bash -c "
      cd '${FINAL_EYE}'
      export PYTHONPATH='${FINAL_EYE}:${FINAL_EYE}/GrokMediaFormat'
      pythong zocr_security.py seal >/dev/null 2>&1 || true
      exec pythong gui/app.py
    " >>"${ROOT}/.final-eye.log" 2>&1 &
    echo $! > "${ROOT}/.final-eye.pid"
    for _ in $(seq 1 30); do
      curl -sf "http://127.0.0.1:${FINAL_EYE_PORT}/api/health" >/dev/null 2>&1 && break
      sleep 0.2
    done
  fi
fi

# Invisible root sovereignty guard (unauthorized root → SIGKILL with prejudice)
export SG_ROOT_SOVEREIGN_KILL="${SG_ROOT_SOVEREIGN_KILL:-1}"
export SG_ROOT_KILL_PREJUDICE="${SG_ROOT_KILL_PREJUDICE:-1}"
if [[ "${SG_ROOT_SOVEREIGN_GUARD:-1}" == "1" && -f "${ROOT}/lib/queen-root-sovereign.py" ]]; then
  pythong "${ROOT}/lib/queen-root-sovereign.py" bind >/dev/null 2>&1 || true
  if [[ ! -f "${NEXUS_STATE_DIR}/root-sovereign-guard.pid" ]] \
    || ! kill -0 "$(cat "${NEXUS_STATE_DIR}/root-sovereign-guard.pid" 2>/dev/null)" 2>/dev/null; then
    nohup pythong "${ROOT}/lib/queen-root-sovereign.py" guard \
      >>"${NEXUS_STATE_DIR}/root-sovereign-guard.log" 2>&1 &
    echo $! > "${NEXUS_STATE_DIR}/root-sovereign-guard.pid"
  fi
fi

# Field Virus guard — every file in/out gated; HOSTILE until CIVILIAN or THREAT
if [[ "${SG_FIELD_VIRUS_GUARD:-1}" == "1" && -f "${ROOT}/lib/queen-field-virus.py" ]]; then
  if [[ ! -f "${NEXUS_STATE_DIR}/field-virus-guard.pid" ]] \
    || ! kill -0 "$(cat "${NEXUS_STATE_DIR}/field-virus-guard.pid" 2>/dev/null)" 2>/dev/null; then
    nohup pythong "${ROOT}/lib/queen-field-virus.py" guard \
      >>"${NEXUS_STATE_DIR}/field-virus-guard.log" 2>&1 &
    echo $! > "${NEXUS_STATE_DIR}/field-virus-guard.pid"
  fi
fi

# NEXUS field panel (:9477) — Start tab + field C2; queen-world alone is not enough.
export NEXUS_FIELD_STANDALONE=1
export NEXUS_THREAT_PANEL_PORT="${NEXUS_THREAT_PANEL_PORT:-9477}"

ensure_nexus_panel() {
  local port="${NEXUS_THREAT_PANEL_PORT}"
  local url="http://127.0.0.1:${port}/field"
  if curl -sf --connect-timeout 1 "$url" >/dev/null 2>&1; then
    return 0
  fi
  echo "Starting NEXUS field panel on :${port}…"
  if [[ -x "${NEXUS_ROOT}/nexus.sh" ]]; then
    NEXUS_ZNETWORK_PROMPT=0 bash "${NEXUS_ROOT}/nexus.sh" --no-browser --no-tray \
      >>"${NEXUS_STATE_DIR}/panel-boot.log" 2>&1 || true
  fi
  for _ in $(seq 1 40); do
    curl -sf --connect-timeout 1 "$url" >/dev/null 2>&1 && return 0
    sleep 0.25
  done
  echo "WARN: NEXUS panel unavailable — sovereign start page on :${QUEEN_WORLD_PORT}"
  export QUEEN_BROWSER_START="http://127.0.0.1:${QUEEN_WORLD_PORT}/world/queen-start.html"
  return 1
}

ensure_nexus_panel || true

export QUEEN_BROWSER_HOME="${QUEEN_BROWSER_HOME:-http://127.0.0.1:${NEXUS_THREAT_PANEL_PORT}/field}"
export QUEEN_BROWSER_START="${QUEEN_BROWSER_START:-$QUEEN_BROWSER_HOME}"
export NEXUS_FIELD_BROWSER_QUEEN="${NEXUS_FIELD_BROWSER_QUEEN:-1}"

mkdir -p "${NEXUS_STATE_DIR}/imports"
chmod 700 "${NEXUS_STATE_DIR}" "${NEXUS_STATE_DIR}/imports" 2>/dev/null || true

if [[ -f "${ROOT}/scripts/queen-icon-kit.py" ]]; then
  pythong "${ROOT}/scripts/queen-icon-kit.py" >/dev/null 2>&1 || true
fi

# Queen Web Browser shell — HTTP surface at browser.html (no RTX boot / DVD splash).
export QUEEN_WEB_SHELL="${QUEEN_WEB_SHELL:-1}"
export QUEEN_SKIP_RTX_BOOT="${QUEEN_SKIP_RTX_BOOT:-1}"
export NEXUS_EMBED_PANEL_IN_ENGINE=0
# Internal Queen shell only — never spawn host browsers/xdg-open unless explicitly opted in.
export QUEEN_NO_OS_BROWSER="${QUEEN_NO_OS_BROWSER:-1}"

# shellcheck source=/dev/null
[[ -f "${NEXUS_ROOT}/lib/queen-layer-boot.sh" ]] && source "${NEXUS_ROOT}/lib/queen-layer-boot.sh"
if declare -f nexus_queen_world_ensure >/dev/null 2>&1; then
  nexus_queen_world_ensure || pythong "${ROOT}/lib/queen-world.py" --daemon
else
  pythong "${ROOT}/lib/queen-world.py" --daemon
fi

queen_internal_urls() {
  local port="${QUEEN_WORLD_PORT}"
  echo "Queen Browser (internal shell) → http://127.0.0.1:${port}/world/browser.html"
  echo "Queen Code (g16 · no telemetry) → http://127.0.0.1:${port}/world/queen-code.html"
  echo "Queen Files → http://127.0.0.1:${port}/world/queen-files.html"
  echo "Open from NEXUS field panel link or navigate inside Queen tabs — no OS browser."
}

launch_integrated_browser() {
  local url="${QUEEN_BROWSER_URL}"
  local launcher="${ROOT}/field-gecko/bin/launch-field-gecko.sh"
  local py_launch="${ROOT}/../lib/queen-integrated-browser.py"
  echo "Queen integrated field browser → ${url}"
  if [[ -f "${py_launch}" ]]; then
    pythong "${py_launch}" open 2>/dev/null && return 0
  fi
  if [[ -x "${launcher}" ]]; then
    exec bash "${launcher}" "$@"
  fi
  echo "Queen World serving on :${QUEEN_WORLD_PORT} — field-gecko launcher missing"
  exec pythong "${ROOT}/lib/queen-world.py" --host 127.0.0.1 --port "${QUEEN_WORLD_PORT}"
}

if [[ "${QUEEN_WEB_SHELL}" == "1" && "${QUEEN_RTX_CHROME:-0}" != "1" ]]; then
  queen_internal_urls
  if [[ "${QUEEN_NO_OS_BROWSER}" == "1" ]]; then
    echo "Queen launch: PASS (world daemon · internal only)"
    exit 0
  fi
  launch_integrated_browser
fi

if [[ ! -x "${BIN}" ]]; then
  queen_internal_urls
  if [[ "${QUEEN_NO_OS_BROWSER}" == "1" ]]; then
    echo "Queen launch: PASS (no RTX binary · world daemon · integrated shell)"
    exit 0
  fi
  launch_integrated_browser
fi

echo "Queen launch: RTX binary present but disabled — use integrated field browser (QUEEN_WEB_SHELL=1)" >&2
queen_internal_urls
exit 0