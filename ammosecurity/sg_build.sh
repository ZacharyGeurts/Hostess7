#!/usr/bin/env bash
# sg_build.sh — internet + no bullshit. SG firmware layer.
set -euo pipefail

SG_VERSION=9
SG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SG_ROOT/lib/common.sh"

usage() {
  cat <<EOF
sg_build.sh v${SG_VERSION}

No security tools. No hacking tools. Internet out. No bullshit.

  ./sg_build.sh -Action All          firmware + internet + clean
  ./sg_build.sh -Action Firmware     purge AV/hacking tools, internet-only firewall
  ./sg_build.sh -Action Internet     outbound check
  ./sg_build.sh -Action Clean        desktop + service bullshit removal
  ./sg_build.sh -Action Status

Legacy: ammo.sh / michigan.sh forward here.
EOF
}

cmd_status() {
  [[ -f /var/lib/sg_build/firmware-layer ]] && sg_log "firmware: $(cat /var/lib/sg_build/firmware-layer 2>/dev/null)"
  ip route show default 2>/dev/null || true
  ss -tlnp 2>/dev/null | head -8 || true
}

ACTION='Help'
WORLD_N=''
M="$SG_ROOT/modules"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -Action) ACTION="${2:-Help}"; shift 2 ;;
    -N) WORLD_N="${2:-}"; shift 2 ;;
    -h|--help) ACTION='Help'; shift ;;
    *) shift ;;
  esac
done

case "$ACTION" in
  All|Firmware|TrustNobody|Antivirus)
    bash "$M/sg_firmware.sh"
    bash "$M/sg_internet.sh"
    bash "$M/sg_no_bullshit.sh"
    ;;
  Internet|Net)  bash "$M/sg_internet.sh" ;;
  Clean|World)   bash "$M/sg_no_bullshit.sh" ;;
  Status)        cmd_status ;;
  Help|*)        usage ;;
esac