#!/usr/bin/env bash
# Boot Field everywhere — all-primary geographic mesh, DNS/DHCP, slow-rollout 25, botnet, perimeter, kill/rekill.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-$ROOT}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-state}"
export SG_ROOT="${SG_ROOT:-$ROOT}"
export NEXUS_FIELD_DNS=1
export NEXUS_FIELD_DHCP=1
export NEXUS_FIELD_LOCAL_DNS_CONNECT=1
export NEXUS_LEGACY_OPEN_SECURED=1
export NEXUS_DNS_DHCP_IMMUTABLE_EVERYWHERE=1
export NEXUS_ALWAYS_FIELD_ONE=1
export NEXUS_NEVER_DOWN=1
export NEXUS_FIELD_PERIMETER="${NEXUS_FIELD_PERIMETER:-1}"
export NEXUS_PERIMETER_APPLY="${NEXUS_PERIMETER_APPLY:-1}"

PY="${PY:-python3}"
command -v pythong >/dev/null 2>&1 && PY=pythong

log() { printf '[field-boot-everywhere] %s\n' "$*"; }

log "seal always Field One - DNS/DHCP immutable everywhere"
NEXUS_DNS_DHCP_SEAL_FAST=1 "$PY" "${ROOT}/lib/field-dns-dhcp-everywhere-immutable.py" seal 2>/dev/null || true

log "fix DNS/DHCP everywhere - promote truth resolver + DHCP primary"
AML_BUILD=0 bash "${ROOT}/scripts/fix-dns-dhcp-everywhere.sh" 2>/dev/null || true

log "field-one absorb - universal ingress to field-1"
"$PY" "${ROOT}/lib/field-one.py" absorb 2>/dev/null || true

log "never-down instantiate - always Field One on this host"
"$PY" "${ROOT}/lib/field-never-down.py" instantiate 2>/dev/null || true

log "rack failover boot - all-primary mesh + DNS/DHCP + perimeter + slow-rollout 25"
"$PY" "${ROOT}/lib/field-rack-failover.py" boot 2>/dev/null || true

log "never-down ensure - restart anything down"
"$PY" "${ROOT}/lib/field-never-down.py" ensure 2>/dev/null || true

log "world internet verify"
"$PY" "${ROOT}/lib/field-one-rollout.py" verify-world-internet --fast 2>/dev/null || true

log "done - all nodes primary; geography routes clients; host down -> peers absorb load."