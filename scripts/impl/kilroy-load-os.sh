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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/impl/kilroy-load-os.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash

# KILROY load OS — board PC core (ZNetwork absorbed), start field stack, launch AmmoOS desktop.
# Queen Browser stays standalone — operator opens :9481/world/browser.html from desktop.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SG="$(cd "${ROOT}/.." && pwd)"
export NEXUS_INSTALL_ROOT="${ROOT}"
export SG_ROOT="${SG}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-${ROOT}/.nexus-state}"
export NEXUS_FIELD_STANDALONE=1

# Stack rewrite env — KILROY owns network; AmmoOS desktop; Queen standalone
export KILROY_PC_CORE=1
export KILROY_ZNETWORK_ABSORBED=1
export KILROY_LOAD_OS=1
export AMMOOS_INSIDE_QUEEN=0
export QUEEN_STANDALONE_BROWSER=1
export AMMOOS_DESKTOP_RTX=AMOURANTHRTX
export NEXUS_AUTO_LAUNCH_QUEEN_BROWSER=0
export NEXUS_FIELD_LAUNCH_BROWSER="${NEXUS_FIELD_LAUNCH_BROWSER:-1}"
export NEXUS_C2_DESKTOP_LAUNCH=1
export NEXUS_BOOT_C2_ONLY=1

PY="$(command -v pythong || command -v python3)"
PANEL_PORT="${NEXUS_THREAT_PANEL_PORT:-9477}"
QUEEN_PORT="${QUEEN_WORLD_PORT:-9481}"

echo "=== KILROY load OS ==="
echo "  Stack: KILROY (ZNetwork absorbed) → AmmoOS + AMOURANTHRTX desktop → Queen standalone"
echo "  Install: ${ROOT}"
echo ""

# Wire siblings (KILROY, AMOURANTHRTX, Grok16, …)
if [[ -x "${ROOT}/scripts/impl/wire-stack.sh" ]]; then
  AML_IMPL=1 bash "${ROOT}/scripts/impl/wire-stack.sh" 2>/dev/null | tail -5 || true
fi

# KILROY PC core — network lane + loopback + C2 markers
if [[ -f "${ROOT}/lib/kilroy-core.sh" ]]; then
  # shellcheck source=/dev/null
  source "${ROOT}/lib/kilroy-core.sh"
  nexus_kilroy_core_board 2>/dev/null || true
  nexus_kilroy_core_network_startup 2>/dev/null || true
fi

# AMOURANTHRTX desktop handlers (SPIR-V, .comp, engine path)
if [[ -x "${ROOT}/scripts/integrate-amouranthrtx.sh" ]]; then
  bash "${ROOT}/scripts/integrate-amouranthrtx.sh" 2>/dev/null | tail -3 || true
fi

# Start panel + Queen + defenses (skip full nexus boot hang when fast)
if curl -sf "http://127.0.0.1:${PANEL_PORT}/field" >/dev/null 2>&1 \
  && curl -sf "http://127.0.0.1:${QUEEN_PORT}/api/status" >/dev/null 2>&1; then
  echo "  Stack already live (panel :${PANEL_PORT}, queen :${QUEEN_PORT})"
else
  if [[ "${KILROY_LOAD_FAST:-0}" == "1" ]] && [[ -x "${ROOT}/scripts/impl/ammoos-direct-start.sh" ]]; then
    AML_IMPL=1 bash "${ROOT}/scripts/impl/ammoos-direct-start.sh"
  else
    AML_IMPL=1 bash "${ROOT}/scripts/impl/start-field-stack.sh" 2>&1 | tail -20 || true
  fi
fi

# Launch AmmoOS desktop (AMOURANTHRTX-backed /field kiosk)
OPEN_PY="${ROOT}/lib/field-queen-browser-open.py"
if [[ -f "$OPEN_PY" ]]; then
  echo ""
  echo "=== Launch AmmoOS desktop ==="
  OUT="$("$PY" "$OPEN_PY" desktop 2>/dev/null || echo '{"ok":false}')"
  if echo "$OUT" | grep -q '"ok": true'; then
    echo "  AmmoOS desktop launched"
    echo "$OUT" | "$PY" -c "import json,sys; d=json.load(sys.stdin); print('  URL:', d.get('url','')); print('  Engine:', d.get('engine',''))" 2>/dev/null || true
  else
    echo "  WARN: desktop launch incomplete — open http://127.0.0.1:${PANEL_PORT}/field" >&2
  fi
fi

echo ""
echo "Surfaces:"
echo "  AmmoOS desktop   http://127.0.0.1:${PANEL_PORT}/field"
echo "  Queen Browser    http://127.0.0.1:${QUEEN_PORT}/world/browser.html  (standalone)"
echo "  KILROY API       http://127.0.0.1:${QUEEN_PORT}/api/kilroy"
echo "  Grok Lab         http://127.0.0.1:${PANEL_PORT}/grok-lab"
