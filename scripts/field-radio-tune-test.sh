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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/field-radio-tune-test.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Field antenna catch test — cycle antenna, catch 83.1 MHz OTA from Gladstone UP Michigan.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export NEXUS_ROOT="$ROOT"
export NEXUS_INSTALL_ROOT="$ROOT"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-/var/lib/nexus-shield}"
export NEXUS_FIELD_CATCH_MHZ="${NEXUS_FIELD_CATCH_MHZ:-83.1}"

mkdir -p "$NEXUS_STATE_DIR"

echo "=== Field Antenna Catch Test — ${NEXUS_FIELD_CATCH_MHZ} MHz UP Michigan ==="
echo "State: $NEXUS_STATE_DIR"

NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$ROOT" \
  pythong "$ROOT/lib/operator-default.py" seed >/dev/null

echo "--- Antenna cycle ---"
NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$ROOT" NEXUS_FIELD_CATCH_MHZ="$NEXUS_FIELD_CATCH_MHZ" \
  pythong "$ROOT/lib/field-antenna-orchestrator.py" launch 3 >/dev/null || true

NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$ROOT" \
  pythong "$ROOT/lib/field-antenna-orchestrator.py" test > "$NEXUS_STATE_DIR/.tune-antenna.json"

echo "--- Radio build ---"
NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$ROOT" \
  pythong "$ROOT/lib/field-radio-catcher.py" build > "$NEXUS_STATE_DIR/.tune-radio.json"

echo "--- Catch ${NEXUS_FIELD_CATCH_MHZ} MHz via field antenna ---"
NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$ROOT" NEXUS_FIELD_CATCH_MHZ="$NEXUS_FIELD_CATCH_MHZ" \
  pythong "$ROOT/lib/field-antenna-orchestrator.py" catch "{\"freq_mhz\":${NEXUS_FIELD_CATCH_MHZ},\"station_id\":\"field-catch-831\"}" \
  > "$NEXUS_STATE_DIR/.tune-result.json"

NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$ROOT" \
  pythong "$ROOT/lib/signals-field.py" build > "$NEXUS_STATE_DIR/.tune-signals.json"

FAIL=0
NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_FIELD_CATCH_MHZ="$NEXUS_FIELD_CATCH_MHZ" pythong - <<'PY' || FAIL=1
import json, os, sys
from pathlib import Path

state = Path(os.environ["NEXUS_STATE_DIR"])
target = float(os.environ.get("NEXUS_FIELD_CATCH_MHZ", "83.1"))
antenna = json.loads((state / ".tune-antenna.json").read_text())
radio = json.loads((state / ".tune-radio.json").read_text())
catch = json.loads((state / ".tune-result.json").read_text())
signals = json.loads((state / ".tune-signals.json").read_text())

errors = []
if not antenna.get("blaster_ready"):
    errors.append(f"blaster_ready=false score={antenna.get('score')}")

catch831 = None
for st in radio.get("all_legal_stations") or []:
    if st.get("id") == "field-catch-831" or abs(float(st.get("freq_mhz") or 0) - target) < 0.05:
        catch831 = st
        break
if not catch831:
    errors.append(f"{target} MHz field-catch-831 not in registry build")
elif not catch831.get("tunable"):
    errors.append(f"83.1 not tunable dist={catch831.get('distance_km')} reach={catch831.get('reach_km')}")
elif catch831.get("catch_method") != "field_antenna_ota":
    errors.append("catch_method not field_antenna_ota")

if not catch.get("ok"):
    errors.append(f"catch failed: {catch.get('error') or catch}")
elif abs(float(catch.get("freq_mhz") or 0) - target) > 0.05:
    errors.append(f"caught wrong freq: {catch.get('freq_mhz')}")
elif not catch.get("antenna_locked") and not catch.get("caught"):
    errors.append("antenna not locked on 83.1")
elif catch.get("method") != "field_antenna_ota":
    errors.append("catch method not field_antenna_ota")

vhf_local = [s for s in (radio.get("station_menu") or []) if s.get("band") == "vhf" or s.get("catch_target")]
if not any(abs(float(s.get("freq_mhz") or 0) - target) < 0.05 for s in vhf_local + (radio.get("station_menu") or [])):
    errors.append(f"{target} not in station menu from Gladstone GPS")

fcc_master = radio.get("fcc_master") or {}
if int(fcc_master.get("total_records") or 0) < 5:
    errors.append(f"fcc master too small: {fcc_master.get('total_records')}")

if errors:
    print("CATCH TEST FAIL:", "; ".join(errors))
    sys.exit(1)

print(
    f"CATCH TEST PASS — {target} MHz · locked={catch.get('antenna_locked')} "
    f"signal={catch.get('signal_strength_pct')}% bearing={catch.get('bearing_deg')}° "
    f"fcc_stored={fcc_master.get('total_records')} blaster={antenna.get('blaster_ready')}"
)
PY

rm -f "$NEXUS_STATE_DIR/.tune-antenna.json" "$NEXUS_STATE_DIR/.tune-radio.json" \
  "$NEXUS_STATE_DIR/.tune-result.json" "$NEXUS_STATE_DIR/.tune-signals.json"

if [[ "$FAIL" -ne 0 ]]; then
  echo "Field antenna catch test FAILED"
  exit 1
fi
echo "Field antenna catch test PASSED"
exit 0