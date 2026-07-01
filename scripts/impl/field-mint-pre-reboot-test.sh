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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/impl/field-mint-pre-reboot-test.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Pre-reboot readiness — host boot chain to Mint desktop (no full run-tests.sh).
# Simulates: early layer → genius → autostart → guest OS landing → F9 posture.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
export NEXUS_INSTALL_ROOT="${ROOT}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-${ROOT}/.nexus-field-drive/nexus-field/state}"
export SG_ROOT="${SG_ROOT:-$(cd "${ROOT}/.." && pwd)}"
export PATH="${ROOT}/PythonG/bin:${PATH}"
export KILROY_ROOT="${KILROY_ROOT:-${ROOT}/KILROY}"

PASS=0
FAIL=0
WARN=0

_ok() { echo "  PASS: $*"; PASS=$((PASS + 1)); }
_fail() { echo "  FAIL: $*" >&2; FAIL=$((FAIL + 1)); }
_warn() { echo "  WARN: $*" >&2; WARN=$((WARN + 1)); }

echo "=== Field Mint Pre-Reboot Test ==="
echo "  root: ${ROOT}"
echo "  state: ${NEXUS_STATE_DIR}"
echo ""

echo "--- Executables ---"
for f in \
  "${ROOT}/lib/nexus-daemon.sh" \
  "${ROOT}/scripts/nexus-field-early-boot.sh" \
  "${ROOT}/scripts/impl/field-mint-boot-ready.sh"; do
  if [[ -x "$f" ]]; then _ok "$(basename "$f") executable"; else _fail "$(basename "$f") not executable"; fi
done

echo "--- systemd ---"
if command -v systemctl >/dev/null 2>&1; then
  for unit in nexus-field-early.service nexus-genius.service; do
    st="$(systemctl is-active "$unit" 2>/dev/null || true)"
    en="$(systemctl is-enabled "$unit" 2>/dev/null || true)"
    if [[ "$st" == "active" || "$st" == "exited" ]]; then
      _ok "${unit} active (${st})"
    else
      _fail "${unit} not active (${st})"
    fi
    [[ "$en" == "enabled" ]] && _ok "${unit} enabled" || _warn "${unit} not enabled (${en})"
  done
  if grep -q 'Before=.*display-manager' /etc/systemd/system/nexus-field-early.service 2>/dev/null; then
    _ok "early service Before display-manager"
  else
    _warn "early service ordering — check Before=display-manager"
  fi
else
  _warn "systemctl unavailable"
fi

echo "--- Early boot dry-run (90s cap) ---"
if command -v timeout >/dev/null 2>&1; then
  if timeout 90s env NEXUS_ZNETWORK_NO_SUDO=1 ZNETWORK_FAST=1 NEXUS_FIELD_EARLY_TIMEOUT=60 \
    bash "${ROOT}/scripts/nexus-field-early-boot.sh" >/dev/null 2>&1; then
    _ok "nexus-field-early-boot.sh"
  else
    _fail "nexus-field-early-boot.sh (timeout or error)"
  fi
else
  _warn "timeout command missing — skip early dry-run"
fi
marker="${NEXUS_STATE_DIR}/field-underlay-early.json"
if [[ -f "$marker" ]]; then
  _ok "field-underlay-early.json"
  if grep -q '"kilroy_network_lane"' "$marker" 2>/dev/null \
    || grep -q '"kilroy_pc_core"' "$marker" 2>/dev/null; then
    _ok "early marker kilroy network lane"
  else
    _warn "early marker missing kilroy_network_lane"
  fi
  if grep -q '"kilroy_nexus_c2"' "$marker" 2>/dev/null \
    || grep -q '"nexus_c2_inside_kilroy"' "$marker" 2>/dev/null; then
    _ok "early marker kilroy nexus c2"
  else
    _warn "early marker missing kilroy_nexus_c2"
  fi
else
  _fail "field-underlay-early.json missing"
fi

echo "--- Genius / HTTP ---"
if [[ -f "${NEXUS_STATE_DIR}/first-boot.complete" ]]; then
  _ok "first-boot.complete (refresh boot path)"
else
  _warn "first-boot.complete missing — first genius start may be slow"
fi
curl -sf --max-time 5 "http://127.0.0.1:9477/field" >/dev/null 2>&1 && _ok "panel :9477" || _fail "panel :9477 down"
curl -sf --max-time 5 "http://127.0.0.1:9481/api/status" >/dev/null 2>&1 && _ok "queen :9481" || _fail "queen :9481 down"

echo "--- Unified device field ---"
if pythong "${ROOT}/lib/field-unified-device.py" board 2>/dev/null | grep -q '"one_field": true'; then
  _ok "unified device board"
else
  _fail "unified device board"
fi
if [[ -f "${NEXUS_STATE_DIR}/field-unified-device.json" ]]; then
  _ok "field-unified-device.json"
else
  _fail "field-unified-device.json missing"
fi

echo "--- Defield / publish ---"
if pythong "${ROOT}/lib/field-non-fielded-safety.py" audit 2>/dev/null | grep -q '"defield_ok": true'; then
  _ok "defield audit clean"
else
  _warn "defield audit not clean — check tails before physical fielding"
fi

echo "--- Mint desktop autostart (post-login) ---"
AUTOSTART="${HOME:-/home/default}/.config/autostart"
for desk in nexus-underlay-hotkey.desktop nexus-panel-tray.desktop; do
  [[ -f "${AUTOSTART}/${desk}" ]] && _ok "autostart ${desk}" || _warn "autostart ${desk} missing"
done

echo "--- F9 stack posture (dry — no desktop launch) ---"
f9_doc="${ROOT}/lib/field-queen-browser-open.py"
if grep -q 'ammoos_role.*normal_desktop\|queen_role.*web_browser\|ammoos_desktop' "$f9_doc" 2>/dev/null; then
  _ok "F9 surfaces: Queen=browser, AmmoOS=desktop"
else
  _warn "F9 surface roles not found in field-queen-browser-open.py"
fi
[[ -f "${ROOT}/data/kilroy-boot-services.json" ]] && _ok "kilroy-boot-services doctrine" || _warn "boot services doctrine missing"
[[ -f "${ROOT}/data/field-dhcp-seed.json" ]] && _ok "field-dhcp-seed table" || _warn "dhcp seed missing"
for seed in dns-multipoint-seed.json dns-admin-seed.json dns-legal-rfc-seed.json; do
  [[ -f "${ROOT}/data/${seed}" ]] && _ok "dns table ${seed}" || _warn "dns table ${seed} missing"
done
if pythong "${ROOT}/lib/kilroy-boot-services.py" verify 2>/dev/null | grep -q '"all_present": true'; then
  _ok "DNS tables verified"
else
  _warn "DNS tables verify incomplete"
fi
[[ -f "${ROOT}/data/f9-sovereign-hook-doctrine.json" ]] && _ok "f9-sovereign-hook doctrine" || _warn "f9 doctrine missing"
[[ -f "${ROOT}/lib/kilroy-loopback.py" ]] && _ok "kilroy-loopback module" || _warn "kilroy-loopback missing"
if [[ -f "${NEXUS_STATE_DIR}/kilroy-loopback.json" ]]; then
  grep -q '"loopback_authority": "127.0.0.1"' "${NEXUS_STATE_DIR}/kilroy-loopback.json" 2>/dev/null \
    && _ok "kilroy loopback 127.0.0.1 stamped" || _warn "kilroy loopback marker incomplete"
else
  _warn "kilroy-loopback.json not stamped — run: stack.sh kilroy core"
fi
curl -sf --max-time 3 http://127.0.0.1:9477/field >/dev/null 2>&1 && _ok "F9 prerequisite panel up" || _warn "panel down for F9"

echo "--- Guest OS path (Mint desktop emulator) ---"
if systemctl is-active display-manager.service 2>/dev/null | grep -q active; then
  _ok "display-manager active (Mint login path live)"
elif systemctl is-active lightdm.service 2>/dev/null | grep -q active; then
  _ok "lightdm active"
else
  _warn "display-manager not active now — will start on reboot"
fi
if command -v cinnamon-session >/dev/null 2>&1 || [[ -d /usr/share/cinnamon ]]; then
  _ok "Cinnamon desktop present"
else
  _warn "Cinnamon not detected — guest may be different DE"
fi
posture="$(pythong "${ROOT}/lib/field-underlay.py" json 2>/dev/null || echo '{}')"
echo "$posture" | grep -q 'passthrough' && _ok "underlay passthrough (GRUB safe)" || _warn "underlay posture"
echo "$posture" | grep -q '"committed": false' && _ok "underlay not committed" || _warn "underlay may be committed"

echo "--- KILROY bzImage (kernel path — optional for Mint graft) ---"
if bash "${ROOT}/scripts/field-kilroy-bzimage.sh" status >/dev/null 2>&1; then
  _ok "KILROY bzImage present"
  command -v qemu-system-x86_64 >/dev/null 2>&1 && _ok "qemu-system-x86_64 installed" || _warn "qemu not installed"
else
  _warn "KILROY bzImage not built — Mint graft OK; run: ./scripts/stack.sh kilroy build"
fi
if [[ -d /media/default/KILROY_FIELD ]]; then
  _ok "KILROY_FIELD mount — tristate virtual-test available"
else
  _warn "KILROY_FIELD not mounted — skip tristate-virtual-kilroy-field.sh"
fi

echo ""
echo "=== Summary ==="
echo "  PASS=${PASS}  FAIL=${FAIL}  WARN=${WARN}"
if [[ "$FAIL" -eq 0 ]]; then
  echo "  READY: reboot → GRUB/Mint unchanged → early layer → login → Mint desktop → F9"
  echo "  After reboot verify: systemctl is-active nexus-field-early nexus-genius"
  echo "  Router:   ./scripts/stack.sh help
  Monitor:  ./lib/ammolang-run.sh mint_pre_reboot"
echo "  Hostess7: cd ${SG_ROOT}/NewLatest/Hostess7 && ./Hostess7.sh stack status"
  exit 0
fi
echo "  NOT READY — fix FAIL items before reboot" >&2
exit 1
