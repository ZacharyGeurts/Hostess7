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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/run-release-gates-2.0.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# AmmoOS 2.0.0 release gates — NewLatest canonical tree only; no hang.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export NEXUS_INSTALL_ROOT="$ROOT"
export SG_ROOT="${SG_ROOT:-$(cd "$ROOT/.." && pwd)}"
export PATH="${SG_ROOT}/PythonG/bin:${PATH:-/usr/bin:/bin}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-/tmp/nexus-release-gates-$$}"
export G16_TEST_TIMEOUT_SEC="${G16_TEST_TIMEOUT_SEC:-90}"
mkdir -p "$NEXUS_STATE_DIR"

PASS=0
FAIL=0

gate() {
  local name="$1"
  shift
  echo "[gate] $name"
  if timeout "${G16_TEST_TIMEOUT_SEC}" "$@"; then
    echo "PASS: $name"
    PASS=$((PASS + 1))
  else
    echo "FAIL: $name (exit $?)"
    FAIL=$((FAIL + 1))
  fi
}

gate "ammoos version 2.0.0" grep -q '"version": "2.0.0"' "$ROOT/data/ammoos-version.json"
gate "thermal manager block" pythong "$ROOT/lib/field-thermal-manager-block.py" json
gate "thermal manager OCR Final_Eye" bash -c "pythong '$ROOT/lib/field-thermal-manager-block.py' ocr | grep -q '\"ok\": true'"
gate "final ear block" pythong "$ROOT/lib/field-final-ear-block.py" json
gate "final ear OCR Final_Eye" bash -c "pythong '$ROOT/lib/field-final-ear-block.py' ocr | grep -q '\"ok\": true'"
gate "final mouth block" pythong "$ROOT/lib/field-final-mouth-block.py" json
gate "final mouth OCR Final_Eye" bash -c "pythong '$ROOT/lib/field-final-mouth-block.py' ocr | grep -q '\"ok\": true'"
gate "rtx canvas block" pythong "$ROOT/lib/field-rtx-canvas-block.py" json
gate "queen canvas renderer" pythong "$ROOT/Queen/lib/queen-canvas-renderer.py" json
gate "field stack queen_canvas" bash -c "pythong '$ROOT/lib/field-stack-layer.py' json | grep -q queen_canvas"
gate "ammoos blocks publish" bash -c "pythong '$ROOT/lib/field-ammoos-blocks.py' publish | grep -q '\"ok\"'"
gate "incorporated Final_Mouth in NewLatest" test -d "$ROOT/Final_Mouth"
gate "incorporated OBS-Field in NewLatest" test -d "$ROOT/OBS-Field"
gate "incorporated GIMP-Field in NewLatest" test -d "$ROOT/GIMP-Field"
gate "incorporated ammosecurity in NewLatest" test -d "$ROOT/ammosecurity"
gate "final mouth block after incorporate" pythong "$ROOT/lib/field-final-mouth-block.py" json
gate "thermal guard" bash -c "pythong '$ROOT/lib/field-thermal-guard.py' json | grep -q headroom_pct"
if [[ "${NEXUS_PANEL_LIVE:-0}" == "1" ]]; then
  gate "panel OCR validate (live)" pythong "$ROOT/scripts/panel-ocr-validate.py"
else
  gate "panel OCR thermal HTML + Final_Eye" bash -c "pythong '$ROOT/lib/field-thermal-manager-block.py' ocr | grep -q '\"ok\": true'"
  gate "panel OCR script present" test -f "$ROOT/scripts/panel-ocr-validate.py"
fi

echo "---"
echo "Release gates: $PASS passed, $FAIL failed"
[[ "$FAIL" -eq 0 ]]