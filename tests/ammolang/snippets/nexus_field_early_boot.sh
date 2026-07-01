#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/nexus-field-early-boot.sh" ]]
  [[ -x "${ROOT}/scripts/nexus-field-early-boot.sh" ]]
  grep -q 'nexus_field_early_boot_run' "${ROOT}/lib/nexus-field-early-boot.sh"
  grep -q 'nexus_field_early_kilroy_unified' "${ROOT}/lib/nexus-field-early-boot.sh"
  grep -q 'nexus_boot_impl_underlay_early' "${ROOT}/lib/nexus-boot-impl.sh"
  grep -q 'early_boot_before_guest_os' "${ROOT}/data/field-underlay-doctrine.json"
  grep -q 'kilroy_kernel_first' "${ROOT}/data/field-underlay-doctrine.json"
  grep -q 'nexus-field-early' "${ROOT}/scripts/field-mint-boot-ready.sh"
  grep -q 'nexus-field-early-boot.sh' "${ROOT}/scripts/field-mint-boot-ready.sh"
  tmp_state="$(mktemp -d)"
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" NEXUS_ZNETWORK_NO_SUDO=1 \
    ZNETWORK_FAST=1 NEXUS_FIELD_EARLY_TIMEOUT=45 NEXUS_FRONT_HOOK=1 NEXUS_SELF_DEFENSE=0 \
    bash "${ROOT}/scripts/nexus-field-early-boot.sh" >/dev/null 2>&1 || true
  [[ -f "${tmp_state}/field-underlay-early.json" ]]
  grep -q 'kilroy_kernel' "${tmp_state}/field-underlay-early.json"
  grep -q 'unified_device_field' "${tmp_state}/field-underlay-early.json"
  grep -q 'guest_field_grant' "${tmp_state}/field-underlay-early.json"
  rm -rf "$tmp_state"
