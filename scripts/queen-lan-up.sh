#!/usr/bin/env bash
# Queen LAN — 192.168.47.1 for retro/world DHCP DNS option 6 (not loopback).
set -euo pipefail

QUEEN_DEV="${NEXUS_QUEEN_LAN_DEV:-dummy-queen}"
QUEEN_IP="${NEXUS_QUEEN_LAN_DNS:-192.168.47.1}"
QUEEN_CIDR="${NEXUS_QUEEN_LAN_CIDR:-24}"

log() { printf '[queen-lan] %s\n' "$*"; }

if ip -4 addr show dev "$QUEEN_DEV" 2>/dev/null | grep -q "${QUEEN_IP}/"; then
  log "${QUEEN_IP} already on ${QUEEN_DEV}"
  exit 0
fi

if ! ip link show "$QUEEN_DEV" &>/dev/null; then
  log "create ${QUEEN_DEV}"
  ip link add "$QUEEN_DEV" type dummy
fi

ip link set "$QUEEN_DEV" up
if ! ip -4 addr show dev "$QUEEN_DEV" | grep -q "${QUEEN_IP}/"; then
  ip addr add "${QUEEN_IP}/${QUEEN_CIDR}" dev "$QUEEN_DEV"
fi

log "queen LAN ready — ${QUEEN_IP}/${QUEEN_CIDR} on ${QUEEN_DEV}"
log "retro/world DHCP DNS option 6 → ${QUEEN_IP} (not 127.0.0.1)"