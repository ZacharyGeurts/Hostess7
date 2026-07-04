#!/usr/bin/env bash
# Field HDMI audio — bind NVIDIA HDMI on stack boot (pro-audio profile).
set -euo pipefail

nexus_field_hdmi_audio_boot() {
  [[ "${NEXUS_FIELD_HDMI_AUDIO:-1}" == "1" ]] || return 0
  local py="${NEXUS_INSTALL_ROOT}/lib/field-hdmi-audio-driver.py"
  [[ -f "$py" ]] || return 0
  command -v pactl >/dev/null 2>&1 || return 0
  local runner="python3"
  command -v pythong >/dev/null 2>&1 && runner="pythong"
  NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" \
    "$runner" "$py" auto >>"${NEXUS_STATE_DIR}/field-hdmi-audio.log" 2>&1 || true
}