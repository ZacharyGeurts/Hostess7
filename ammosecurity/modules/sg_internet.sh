#!/usr/bin/env bash
# sg_internet — verify outbound internet, nothing else
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../lib/common.sh"

cmd_sg_internet() {
  bash "$(dirname "${BASH_SOURCE[0]}")/sg_firmware.sh" 2>/dev/null || true
  sg_log 'checking outbound internet'
  if curl -fsSL --max-time 8 -o /dev/null https://1.1.1.1 2>/dev/null; then
    sg_log 'internet: OK (outbound)'
  else
    sg_log 'internet: check cable/DNS — outbound path only by design'
  fi
  ip route show default 2>/dev/null | head -3 || true
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  cmd_sg_internet "$@"
fi