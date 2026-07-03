#!/usr/bin/env bash
# interface_guard — nftables inet kill-switch baseline (idempotent, reversible)
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../lib/common.sh"

NFT_TABLE="inet ammo_guard"
NFT_CHAIN_IN="input"
NFT_CHAIN_FWD="forward"
NFT_CHAIN_OUT="output"
KILL_SWITCH_FILE="${AMMO_STATE_DIR}/killswitch.on"

cmd_guard_apply() {
  command -v nft >/dev/null 2>&1 || {
    ammo_log 'nft not installed — iptables baseline only (sg_net_harden)'
    return 0
  }
  ammo_log 'nft interface guard — idempotent apply'
  if nft list table $NFT_TABLE &>/dev/null; then
    ammo_log 'nft table ammo_guard already present'
    return 0
  fi
  ammo_sudo nft -f - <<'EOF'
table inet ammo_guard {
  chain input {
    type filter hook input priority 0; policy drop;
    iif "lo" accept
    ct state established,related accept
  }
  chain forward {
    type filter hook forward priority 0; policy drop;
  }
  chain output {
    type filter hook output priority 0; policy accept;
  }
}
EOF
  ammo_health_note 'nft ammo_guard applied'
}

cmd_killswitch_on() {
  command -v nft >/dev/null 2>&1 || {
    ammo_log 'killswitch: nft missing — tightening iptables OUTPUT'
    if command -v iptables >/dev/null 2>&1; then
      ammo_sudo iptables -P OUTPUT DROP
      ammo_sudo iptables -A OUTPUT -o lo -j ACCEPT
      ammo_sudo iptables -A OUTPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
    fi
    ammo_ensure_state
    date -Is 2>/dev/null >"$KILL_SWITCH_FILE" || echo on >"$KILL_SWITCH_FILE"
    ammo_violation 'killswitch engaged (iptables fallback)'
    return 0
  }
  cmd_guard_apply
  ammo_sudo nft add rule inet ammo_guard output oif "lo" accept 2>/dev/null || true
  ammo_sudo nft add rule inet ammo_guard output ct state established,related accept 2>/dev/null || true
  ammo_sudo nft chain inet ammo_guard output '{ policy drop; }' 2>/dev/null || true
  ammo_ensure_state
  date -Is 2>/dev/null >"$KILL_SWITCH_FILE" || echo on >"$KILL_SWITCH_FILE"
  ammo_violation 'killswitch engaged (nft output drop)'
}

cmd_killswitch_off() {
  rm -f "$KILL_SWITCH_FILE" 2>/dev/null || true
  if command -v nft >/dev/null 2>&1 && nft list table $NFT_TABLE &>/dev/null; then
    ammo_sudo nft chain inet ammo_guard output '{ policy accept; }' 2>/dev/null || true
  fi
  if command -v iptables >/dev/null 2>&1; then
    ammo_sudo iptables -P OUTPUT ACCEPT 2>/dev/null || true
  fi
  ammo_health_note 'killswitch released'
}

cmd_guard_status() {
  ammo_log '=== interface guard status ==='
  if command -v nft >/dev/null 2>&1; then
    nft list table $NFT_TABLE 2>/dev/null | head -20 || echo 'nft ammo_guard: not loaded'
  else
    echo 'nft: not installed'
  fi
  [[ -f "$KILL_SWITCH_FILE" ]] && echo "killswitch: ON ($(cat "$KILL_SWITCH_FILE"))" || echo 'killswitch: off'
  command -v iptables >/dev/null && iptables -S OUTPUT 2>/dev/null | head -3 || true
}

cmd_guard_dry_run() {
  ammo_log 'DRY-RUN interface_guard — no changes'
  command -v nft >/dev/null && echo 'nft: available' || echo 'nft: missing'
  [[ -f "$KILL_SWITCH_FILE" ]] && echo 'killswitch would stay ON' || echo 'killswitch would stay off'
}

main() {
  local mode="${1:-apply}"
  case "$mode" in
    apply|guard) cmd_guard_apply ;;
    killswitch|airgap) cmd_killswitch_on ;;
    release|off) cmd_killswitch_off ;;
    status) cmd_guard_status ;;
    dry-run|test) cmd_guard_dry_run ;;
    *) cmd_guard_apply ;;
  esac
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi