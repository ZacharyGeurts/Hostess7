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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:genius_shield.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# NEXUS-Shield default installer — pure genius heuristics, ultra-stealth, non-intrusive.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-$ROOT}"
export NEXUS_INSTALL_SRC="${NEXUS_INSTALL_SRC:-$ROOT}"
export SG_ROOT="${SG_ROOT:-${ROOT}}"

if [[ "$(id -u)" -ne 0 ]]; then
  if [[ "${NEXUS_ELEVATED_ROOT:-}" == "1" ]]; then
    echo "Elevation incomplete — expected root after admin approval." >&2
    exit 1
  fi
  # shellcheck source=/dev/null
  source "${ROOT}/lib/nexus-elevate.sh"
  nexus_elevate_acquire "$0" "$@"
fi
export NEXUS_ELEVATED_ROOT=1

echo 'Deploying NEXUS-Shield (genius-only, ultra-stealth)...'

INSTALL_USER="${SUDO_USER:-${USER:-}}"
export NEXUS_INSTALL_ROOT=/usr/local/lib/nexus-shield
# shellcheck source=/dev/null
source "${ROOT}/lib/nexus-common.sh"
# shellcheck source=/dev/null
[[ -f "${ROOT}/lib/nexus-update-lock.sh" ]] && source "${ROOT}/lib/nexus-update-lock.sh"
nexus_ensure_group

if declare -f nexus_update_lock_ensure >/dev/null 2>&1; then
  if ! nexus_update_lock_ensure; then
    echo 'NEXUS-Shield update already in progress — github-update.lock held. Wait for panel UPDATE to finish.' >&2
    nexus_update_lock_status >&2 || true
    exit 2
  fi
  trap 'nexus_update_lock_release' EXIT
fi

if command -v apt-get >/dev/null 2>&1; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y -qq inotify-tools tcpdump iproute2 nftables e2fsprogs zenity
fi

declare -f nexus_update_lock_phase >/dev/null 2>&1 && nexus_update_lock_phase stopping_services
systemctl stop nexus-genius.service 2>/dev/null || true
pkill -9 -f 'nexus-daemon.sh' 2>/dev/null || true
pkill -9 -f 'threat-panel-http.py' 2>/dev/null || true
# Orphan shadow/entropy inotify watchers from dead daemons
pkill -9 -f 'inotifywait -m -e modify,create,delete,move' 2>/dev/null || true
sleep 2
pkill -f 'threat-panel-http.py' 2>/dev/null || true
# Clean install — avoid false UNCLEAN_RESTART on intentional redeploy
rm -f /var/lib/nexus-shield/nexus.heartbeat /var/lib/nexus-shield/.shutdown-clean 2>/dev/null || true
: >/var/lib/nexus-shield/shutdown-incidents.jsonl 2>/dev/null || true
printf 'status=clean_install\nts=%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
  >/var/lib/nexus-shield/shutdown.state 2>/dev/null || true
printf 'mode=1\nblock=0\nautosanitize_override=0\nupdated=%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
  >/var/lib/nexus-shield/paranoia.state 2>/dev/null || true

declare -f nexus_update_lock_phase >/dev/null 2>&1 && nexus_update_lock_phase copying_files
install -d -m 750 -o root -g nexus /usr/local/lib/nexus-shield /usr/local/lib/nexus-shield/bin /usr/local/bin
cp -a "${ROOT}/lib" "${ROOT}/config" "${ROOT}/tests" "${ROOT}/panel" "${ROOT}/assets" "${ROOT}/data" /usr/local/lib/nexus-shield/
[[ -d "${ROOT}/install" ]] && cp -a "${ROOT}/install" /usr/local/lib/nexus-shield/
[[ -d "${ROOT}/Queen" ]] && cp -a "${ROOT}/Queen" /usr/local/lib/nexus-shield/
[[ -d "${ROOT}/Hostess7" ]] && cp -a "${ROOT}/Hostess7" /usr/local/lib/nexus-shield/
[[ -d "${ROOT}/hostess7-training-viewer" ]] && cp -a "${ROOT}/hostess7-training-viewer" /usr/local/lib/nexus-shield/
[[ -d "${ROOT}/scripts" ]] && cp -a "${ROOT}/scripts" /usr/local/lib/nexus-shield/
[[ -f "${ROOT}/install-all.sh" ]] && \
  install -m 755 -o root -g nexus "${ROOT}/install-all.sh" /usr/local/lib/nexus-shield/install-all.sh
[[ -f "${ROOT}/stealth_install.sh" ]] && \
  install -m 755 -o root -g nexus "${ROOT}/stealth_install.sh" /usr/local/lib/nexus-shield/stealth_install.sh
mkdir -p /usr/local/lib/nexus-shield/scripts
install -m 755 -o root -g nexus "${ROOT}/scripts/play-wimk-ota.sh" /usr/local/lib/nexus-shield/scripts/play-wimk-ota.sh 2>/dev/null || true
install -m 755 -o root -g nexus "${ROOT}/scripts/wire-stack.sh" /usr/local/lib/nexus-shield/scripts/wire-stack.sh 2>/dev/null || true
install -m 755 -o root -g nexus "${ROOT}/scripts/nexus-boot-impl.sh" /usr/local/lib/nexus-shield/scripts/nexus-boot-impl.sh 2>/dev/null || true
install -m 755 -o root -g nexus "${ROOT}/scripts/migrate-nexus-state.sh" /usr/local/lib/nexus-shield/scripts/migrate-nexus-state.sh 2>/dev/null || true
[[ -d "${ROOT}/plugins" ]] && cp -a "${ROOT}/plugins" /usr/local/lib/nexus-shield/
chmod 755 "${ROOT}/lib/threat-panel-http.py" "${ROOT}/lib/shutdown-analyze.py" \
  "${ROOT}/lib/connection-gatekeeper.py" "${ROOT}/lib/vector-intel.py" "${ROOT}/lib/angel-dossier.py" \
  "${ROOT}/lib/fair-ad-guardian.py" "${ROOT}/lib/host-attack-map.py" "${ROOT}/lib/geo-intel-standards.py" \
  "${ROOT}/lib/field-attack-kit.py" "${ROOT}/lib/friendly-guard.py" "${ROOT}/lib/target-bleed.py" \
  "${ROOT}/lib/host-identity.py" "${ROOT}/lib/sdf-assets.py" "${ROOT}/lib/field-us-intel.py" "${ROOT}/lib/packet-permission.py" \
  "${ROOT}/lib/nexus-update.py" "${ROOT}/lib/honorability-db.py" "${ROOT}/lib/browser-awareness.py" \
  "${ROOT}/lib/geo-distance.py" "${ROOT}/lib/operator-location.py" \
  "${ROOT}/lib/field-rf-sentinel.py" "${ROOT}/lib/police-agency-db.py" \
  "${ROOT}/lib/field-command.py" "${ROOT}/lib/gov-intel-db.py" "${ROOT}/lib/program-tags-db.py" \
  "${ROOT}/lib/nexus-update-lock.py" "${ROOT}/lib/field-toolkit-db.py" "${ROOT}/lib/nexus-plugins.py" \
  "${ROOT}/lib/terror-spiderweb.py" "${ROOT}/lib/existence-identity.py" \
  "${ROOT}/lib/human-registry.py" "${ROOT}/lib/safe-signal-touch.py" "${ROOT}/lib/audio-train.py" "${ROOT}/lib/pet-signal-guard.py" \
  "${ROOT}/lib/home-protector.py" "${ROOT}/lib/heavyboi-importer.py" \
  "${ROOT}/lib/signals-field.py" "${ROOT}/lib/fcc-signal-lookup.py" \
  "${ROOT}/lib/field-antenna-orchestrator.py" "${ROOT}/lib/field-antenna-catch.py" "${ROOT}/lib/field-radio-catcher.py" \
  "${ROOT}/lib/field-wave-tuner.py" "${ROOT}/lib/field-wave-engine.py" "${ROOT}/lib/field-signal-reader.py" \
  "${ROOT}/lib/field-antenna-prototype.py" "${ROOT}/lib/field-spectrum-demod.py" "${ROOT}/lib/field-instability.py" \
  "${ROOT}/lib/field-world-placement.py" "${ROOT}/lib/field-generator-triangulator.py" \
  "${ROOT}/lib/field-crosstalk.py" \
  "${ROOT}/lib/field-tri-receive.py" \
  "${ROOT}/lib/field-material-discern.py" "${ROOT}/lib/gps-precision.py" \
  "${ROOT}/lib/precision-field.py" "${ROOT}/lib/operator-default.py" "${ROOT}/lib/panel-i18n.py" "${ROOT}/lib/hostess-profile.py" "${ROOT}/lib/host-security-tier.py" \
  "${ROOT}/lib/field-dns.py" "${ROOT}/lib/dns-planetary-security.py" \
  "${ROOT}/lib/field-outside-talk.py" "${ROOT}/lib/field-outside-asm.c" \
  "${ROOT}/lib/field-wave-asm.c" \
  "${ROOT}/lib/field-drive-system.py" \
  "${ROOT}/lib/dns-admin-portal.py" "${ROOT}/lib/equipment-room-field.py" \
  "${ROOT}/lib/dns-multipoint-identity.py" 2>/dev/null || true
chmod 755 "${ROOT}/lib/pest-arsenal.sh" "${ROOT}/lib/vector-scour.sh" "${ROOT}/lib/angel-dossier.sh" \
  "${ROOT}/lib/human-registry.sh" "${ROOT}/lib/audio-train.sh" "${ROOT}/lib/home-protector.sh" "${ROOT}/lib/signals-field.sh" "${ROOT}/lib/field-antenna.sh" "${ROOT}/lib/field-radio-catcher.sh" "${ROOT}/lib/field-antenna-launcher.sh" "${ROOT}/scripts/field-antenna-test.sh" "${ROOT}/scripts/field-wave-hardware.sh" "${ROOT}/lib/field-dns.sh" "${ROOT}/lib/field-outside-talk.sh" "${ROOT}/lib/field-outside-asm.sh" "${ROOT}/lib/field-wave-asm.sh" "${ROOT}/lib/field-drive-system.sh" "${ROOT}/lib/dns-admin-portal.sh" "${ROOT}/lib/human-dossier.sh" "${ROOT}/lib/field-us-intel.sh" "${ROOT}/lib/gatekeeper-enforce.sh" "${ROOT}/lib/host-attack.sh" \
  "${ROOT}/lib/field-attack-kit.sh" "${ROOT}/lib/friendly-guard.sh" "${ROOT}/lib/host-map-trash.sh" \
  "${ROOT}/lib/honorability.sh" "${ROOT}/lib/field-rf-sentinel.sh" "${ROOT}/lib/police-agency.sh" \
  "${ROOT}/lib/field-command.sh" "${ROOT}/lib/gov-intel.sh" "${ROOT}/lib/program-tags.sh" \
  "${ROOT}/lib/nexus-update-lock.sh" "${ROOT}/lib/nexus-update-apply.sh" "${ROOT}/lib/field-toolkit.sh" "${ROOT}/lib/hardware-destruction.sh" 2>/dev/null || true
chmod 555 /usr/local/lib/nexus-shield/lib/friendly-guard.py /usr/local/lib/nexus-shield/lib/friendly-guard.sh 2>/dev/null || true
chmod 755 /usr/local/lib/nexus-shield/lib/*.py 2>/dev/null || true
chmod -R a+rX /usr/local/lib/nexus-shield/data 2>/dev/null || true
# Field Outside ASM — minimal egress probe (field-fast, no shell deps)
if [[ -f /usr/local/lib/nexus-shield/lib/field-outside-asm.sh ]]; then
  # shellcheck source=/dev/null
  source /usr/local/lib/nexus-shield/lib/nexus-common.sh
  NEXUS_INSTALL_ROOT=/usr/local/lib/nexus-shield
  # shellcheck source=/dev/null
  source /usr/local/lib/nexus-shield/lib/field-outside-asm.sh
  nexus_field_outside_asm_build 2>/dev/null || true
fi
# Field Wave ASM — field-fast RTL-SDR USB probe
if [[ -f /usr/local/lib/nexus-shield/lib/field-wave-asm.sh ]]; then
  # shellcheck source=/dev/null
  source /usr/local/lib/nexus-shield/lib/field-wave-asm.sh
  nexus_field_wave_asm_build 2>/dev/null || true
  pythong /usr/local/lib/nexus-shield/lib/field-wave-engine.py ensure 2>/dev/null || true
fi
install -m 750 -o root -g nexus "${ROOT}/bin/nexus" /usr/local/lib/nexus-shield/bin/nexus
install -m 750 -o root -g nexus "${ROOT}/bin/nexus" /usr/local/bin/nexus
install -m 755 -o root -g nexus "${ROOT}/nexus.sh" /usr/local/bin/nexus.sh
chmod 755 "${ROOT}/nexus.sh" 2>/dev/null || true
install -m 750 -o root -g nexus "${ROOT}/lib/nexus-daemon.sh" /usr/local/lib/nexus-shield/lib/
mkdir -p /var/lib/nexus-shield/shadow /var/lib/nexus-shield/behavior /var/lib/nexus-shield/hostess7-cache
if [[ -f "${ROOT}/scripts/migrate-nexus-state.sh" ]]; then
  NEXUS_STATE_DIR=/var/lib/nexus-shield NEXUS_INSTALL_ROOT="${ROOT}" \
    bash "${ROOT}/scripts/migrate-nexus-state.sh" 2>/dev/null || true
fi
touch /var/log/nexus-alerts.log
NEXUS_INSTALL_ROOT=/usr/local/lib/nexus-shield NEXUS_STATE_DIR=/var/lib/nexus-shield \
  pythong /usr/local/lib/nexus-shield/lib/operator-default.py seed 2>/dev/null || true

# Ship canonical config (paranoia + shutdown guard included)
install -m 640 -o root -g nexus "${ROOT}/config/nexus.conf" /usr/local/lib/nexus-shield/config/nexus.conf
cp "${ROOT}/config/device-whitelist.conf" /usr/local/lib/nexus-shield/config/

# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/self-defense.sh"
declare -f nexus_update_lock_phase >/dev/null 2>&1 && nexus_update_lock_phase signing
nexus_sign_manifest /usr/local/lib/nexus-shield/MANIFEST.sha256
# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/seal-vault.sh"
# ZNetwork — build + ship binary for startup Yes/No/Skip dialog
ZN_SRC="$(cd "${ROOT}/ZNetwork" 2>/dev/null && pwd)"
[[ -d "$ZN_SRC" ]] || ZN_SRC="$(cd "${SG_ROOT:-${ROOT}/..}/NewLatest/ZNetwork" 2>/dev/null && pwd)"
if [[ -d "$ZN_SRC" ]]; then
  install -d -m 755 /usr/local/lib/nexus-shield/bin /usr/local/lib/nexus-shield/znetwork/data
  cp -a "${ZN_SRC}/scripts" /usr/local/lib/nexus-shield/znetwork/ 2>/dev/null || true
  [[ -f "${ZN_SRC}/data/review-checklist.json" ]] && \
    install -m 644 "${ZN_SRC}/data/review-checklist.json" /usr/local/lib/nexus-shield/znetwork/data/ 2>/dev/null || true
  if command -v cmake >/dev/null 2>&1; then
    (cd "$ZN_SRC" && cmake -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build) 2>/dev/null || true
    [[ -x "${ZN_SRC}/build/znetwork" ]] && \
      install -m 755 "${ZN_SRC}/build/znetwork" /usr/local/lib/nexus-shield/bin/znetwork
  fi
  if [[ -f /usr/local/lib/nexus-shield/config/nexus.conf ]]; then
    sed -i 's|^ZNETWORK_ROOT=.*|ZNETWORK_ROOT=/usr/local/lib/nexus-shield/znetwork|' \
      /usr/local/lib/nexus-shield/config/nexus.conf 2>/dev/null || true
    grep -q '^ZNETWORK_BIN=' /usr/local/lib/nexus-shield/config/nexus.conf 2>/dev/null || \
      printf '\nZNETWORK_BIN=/usr/local/lib/nexus-shield/bin/znetwork\n' \
        >>/usr/local/lib/nexus-shield/config/nexus.conf
  fi
fi


# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/znetwork-field.sh"
nexus_seal_refresh
nexus_znetwork_publish 2>/dev/null || true
nexus_apply_permissions

# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/shadow-reality.sh"
nexus_shadow_init
nexus_apply_permissions

# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/network-lockdown.sh"
nexus_network_lockdown

# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/firewall-sentinel.sh"
# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/firewall-trust.sh"
nexus_firewall_takeover || {
  echo 'NEXUS firewall takeover failed — check nftables.' >&2
  exit 1
}
# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/self-access.sh"
# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/firewall-trust.sh"
nexus_firewall_ensure_self_access || true
# Clear false-positive CDN blocks that can kill normal internet egress
declare -f nexus_firewall_flush_blocks >/dev/null 2>&1 && nexus_firewall_flush_blocks
# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/panel-launch.sh"
nexus_panel_install_desktop

# Everyday profile — email/YouTube/browsing defaults (no auto-block, light watchers)
# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/nexus-settings.sh"
nexus_settings_apply_consumer_defaults
nexus_host_extreme_apply_if_eligible || true

H7_ROOT=""
for _h7 in "${NEXUS_INSTALL_ROOT}/Hostess7" "${SG_ROOT}/NewLatest/Hostess7" "${SG_ROOT}/Hostess7" "${ROOT}/Hostess7" "${HOME}/Desktop/SG/NewLatest/Hostess7"; do
  [[ -d "$_h7" ]] && H7_ROOT="$(cd "$_h7" && pwd)" && break
done
unset _h7
H7_BIND_RO=""
H7_BIND_RW=""
if [[ -n "$H7_ROOT" ]]; then
  H7_BIND_RO="BindReadOnlyPaths=-${H7_ROOT}"
  H7_BIND_RW="BindPaths=/var/lib/nexus-shield/hostess7-cache:${H7_ROOT}/cache"
fi

cat >/etc/systemd/system/nexus-genius.service <<EOF
[Unit]
Description=NEXUS-Shield Genius Layer (ultra-stealth, event-driven)
After=network.target
StartLimitIntervalSec=300
StartLimitBurst=5

[Service]
Type=simple
Environment=NEXUS_INSTALL_ROOT=/usr/local/lib/nexus-shield
Environment=SG_ROOT=${SG_ROOT}
ExecStartPre=/usr/local/lib/nexus-shield/scripts/nexus-boot-impl.sh
ExecStart=/usr/local/lib/nexus-shield/lib/nexus-daemon.sh
ExecStop=/bin/bash -c 'source /usr/local/lib/nexus-shield/lib/nexus-common.sh; source /usr/local/lib/nexus-shield/lib/shutdown-guard.sh 2>/dev/null; nexus_shutdown_mark_clean 2>/dev/null; pkill -9 -f threat-panel-http.py 2>/dev/null; pkill -9 -f queen-world.py 2>/dev/null; pkill -9 -f dns-admin-portal.py 2>/dev/null; pkill -9 -P \$MAINPID 2>/dev/null; exit 0'
KillMode=control-group
TimeoutStopSec=8
Restart=on-failure
RestartSec=10
Nice=19
IOSchedulingClass=idle
CPUQuota=5%
MemoryMax=256M
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/var/lib/nexus-shield /var/log/nexus-alerts.log
${H7_BIND_RO}
${H7_BIND_RW}
AmbientCapabilities=CAP_NET_ADMIN CAP_NET_RAW CAP_NET_BIND_SERVICE
CapabilityBoundingSet=CAP_NET_ADMIN CAP_NET_RAW CAP_NET_BIND_SERVICE CAP_DAC_OVERRIDE CAP_SETGID CAP_SETUID CAP_SYS_ADMIN
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable nexus-genius.service
systemctl reset-failed nexus-genius.service 2>/dev/null || true
systemctl restart nexus-genius.service

sleep 8
# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/firewall-sentinel.sh"
# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/lockdown-first.sh"
nexus_lockdown_first_apply || true

# Auto-kill on install — sync field hostile registry, crush hot, RE-KILL validated same-host attackers
# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/host-attack.sh" 2>/dev/null || true
# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/field-attack-kit.sh"
nexus_field_attack_install_autokill || true
[[ -f "${NEXUS_INSTALL_ROOT}/lib/field-war-hardening.sh" ]] && {
  # shellcheck source=/dev/null
  source "${NEXUS_INSTALL_ROOT}/lib/field-war-hardening.sh"
  nexus_field_war_harden || true
}

# First-install boot impl — wire stack, migrate, meld; marks first-boot.complete
export NEXUS_BOOT_FORCE_FIRST=1
NEXUS_INSTALL_ROOT=/usr/local/lib/nexus-shield NEXUS_STATE_DIR=/var/lib/nexus-shield \
  SG_ROOT="${SG_ROOT}" bash /usr/local/lib/nexus-shield/scripts/nexus-boot-impl.sh 2>/dev/null || true
unset NEXUS_BOOT_FORCE_FIRST

declare -f nexus_update_lock_phase >/dev/null 2>&1 && nexus_update_lock_phase starting_service
if ! systemctl is-active --quiet nexus-genius.service; then
  echo 'NEXUS-Shield install finished, but nexus-genius.service failed to start.' >&2
  echo 'Check: systemctl status nexus-genius.service' >&2
  exit 1
fi

chown -R root:nexus /var/lib/nexus-shield 2>/dev/null || true
chmod 640 /var/lib/nexus-shield/vigil.state /var/lib/nexus-shield/threat-panel.json 2>/dev/null || true

if [[ -n "$INSTALL_USER" && "$INSTALL_USER" != "root" ]]; then
  usermod -aG nexus "$INSTALL_USER" 2>/dev/null || true
  echo "Added ${INSTALL_USER} to group nexus."
  echo "Log out/in (or: sg nexus -c 'nexus status') — no further sudo needed."
fi

# Board hooks, polkit, perimeter, tristate installer, desktop entries.
if [[ -f "${NEXUS_INSTALL_ROOT}/lib/nexus-os-assist.sh" ]]; then
  export NEXUS_PERIMETER_APPLY="${NEXUS_PERIMETER_APPLY:-1}"
  # shellcheck source=/dev/null
  source "${NEXUS_INSTALL_ROOT}/lib/nexus-os-assist.sh"
  nexus_os_assist_all "${ROOT}"
fi

echo "NEXUS-Shield v${NEXUS_VERSION:-2.0.1} active — panel http://127.0.0.1:9477/field (browser opens on startup)."
echo "Launcher: nexus.sh  |  Tristate: nexus.sh --underlay"
echo 'Start menu / taskbar: NEXUS Field Command Center'
echo 'License: NEXUS-Shield = MIT. AMOURANTHRTX (Field Die) = GPL v3 or commercial — not MIT-free.'
echo 'Profile: Packet permission v4.0 — DPI knows intent; harmful sections blocked; good flows pass.'
echo 'First-run lockdown applied — trust recommended connections in panel or: nexus trust <ip>'