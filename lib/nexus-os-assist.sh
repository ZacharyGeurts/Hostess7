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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/nexus-os-assist.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# NEXUS OS assistance — board hooks, native layer, CPU shield, polkit, posture after system install.
set -euo pipefail

nexus_os_assist_log() {
  printf '[%s] os-assist: %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"
}

# Resolve SG / KILROY / Queen after install (never hardcode dev-tree NewLatest paths).
nexus_os_assist_export_paths() {
  local root="${NEXUS_INSTALL_ROOT:-/usr/local/lib/nexus-shield}"
  local state="${NEXUS_STATE_DIR:-/var/lib/nexus-shield}"

  if [[ -f "${root}/lib/sg-paths.sh" ]]; then
    # shellcheck source=/dev/null
    source "${root}/lib/sg-paths.sh"
    export QUEEN_ROOT="${QUEEN_ROOT:-$(sg_paths_queen_root)}"
  elif [[ -d "${root}/Queen" ]]; then
    export QUEEN_ROOT="${QUEEN_ROOT:-${root}/Queen}"
  elif [[ -z "${QUEEN_ROOT:-}" ]]; then
    for q in "${SG_ROOT:-}/Queen" "${SG_ROOT:-}/NewLatest/Queen" "${HOME}/Desktop/SG/Queen" "${HOME}/Desktop/SG/NewLatest/Queen"; do
      [[ -d "$q" ]] && export QUEEN_ROOT="$(cd "$q" && pwd)" && break
    done
  fi

  if [[ -f "${root}/lib/kilroy-resolve.sh" ]]; then
    # shellcheck source=/dev/null
    source "${root}/lib/kilroy-resolve.sh"
    nexus_kilroy_export "${SG_ROOT:-}" 2>/dev/null || true
  fi
  if [[ -z "${KILROY_ROOT:-}" ]]; then
    for kr in "${HOME}/Desktop/KILROY" "${SG_ROOT:-}/../KILROY" "${SG_ROOT:-}/KILROY"; do
      [[ -f "${kr}/scripts/build-kilroy.sh" ]] && export KILROY_ROOT="$(cd "$kr" && pwd)" && break
    done
  fi

  if [[ -z "${SG_ROOT:-}" ]]; then
    if [[ -n "${KILROY_ROOT:-}" ]]; then
      export SG_ROOT="$(cd "${KILROY_ROOT}/.." && pwd)"
    elif [[ -n "${QUEEN_ROOT:-}" ]]; then
      export SG_ROOT="$(cd "${QUEEN_ROOT}/../.." && pwd)"
    else
      for sg in "${HOME}/Desktop/SG" "$(cd "${root}/../../.." 2>/dev/null && pwd)"; do
        [[ -d "${sg}/NewLatest" || -d "${sg}/KILROY" ]] && export SG_ROOT="$(cd "$sg" && pwd)" && break
      done
    fi
  fi

  mkdir -p "$state" 2>/dev/null || true
  pythong - <<'PY' >"${state}/field-paths.json" 2>/dev/null || true
import json, os
from datetime import datetime, timezone
doc = {
    "schema": "field-paths/v1",
    "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "install_root": os.environ.get("NEXUS_INSTALL_ROOT", ""),
    "sg_root": os.environ.get("SG_ROOT", ""),
    "kilroy_root": os.environ.get("KILROY_ROOT", ""),
    "queen_root": os.environ.get("QUEEN_ROOT", ""),
}
print(json.dumps(doc, indent=2))
PY
}

nexus_os_assist_install_polkit() {
  local root="${NEXUS_INSTALL_ROOT:-/usr/local/lib/nexus-shield}"
  export NEXUS_INSTALL_SRC="${NEXUS_INSTALL_SRC:-${root}}"
  # shellcheck source=/dev/null
  [[ -f "${root}/lib/nexus-polkit.sh" ]] && source "${root}/lib/nexus-polkit.sh"
  # shellcheck source=/dev/null
  [[ -f "${root}/../lib/nexus-polkit.sh" ]] && source "${root}/../lib/nexus-polkit.sh"
  if declare -f nexus_polkit_install >/dev/null 2>&1; then
    nexus_polkit_install
    nexus_os_assist_log "field polkit installed (policy + rules + bridge)"
    return 0
  fi
  nexus_os_assist_log "field polkit install skipped (nexus-polkit.sh missing)"
}

nexus_os_assist_board_hooks() {
  local root="${NEXUS_INSTALL_ROOT:-/usr/local/lib/nexus-shield}"
  export NEXUS_INSTALL_ROOT="${root}"
  export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-/var/lib/nexus-shield}"
  nexus_os_assist_export_paths
  mkdir -p "${NEXUS_STATE_DIR}"
  if [[ -f "${root}/lib/front-hook.sh" ]]; then
    # shellcheck source=/dev/null
    source "${root}/lib/front-hook.sh"
    nexus_front_hook_board
  fi
  if [[ -f "${root}/lib/hardware-wire.sh" ]]; then
    # shellcheck source=/dev/null
    source "${root}/lib/hardware-wire.sh"
    nexus_hardware_wire_once 2>/dev/null || true
  fi
  if [[ -f "${root}/lib/admin-window-shield.sh" ]]; then
    # shellcheck source=/dev/null
    source "${root}/lib/admin-window-shield.sh"
    nexus_admin_window_shield_once 2>/dev/null || true
  fi
  nexus_os_assist_log "hooks boarded"
}

nexus_os_assist_field_polkit() {
  local root="${NEXUS_INSTALL_ROOT:-/usr/local/lib/nexus-shield}"
  local py="${root}/lib/field-polkit.py"
  [[ -f "$py" ]] || return 0
  NEXUS_INSTALL_ROOT="${root}" NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-/var/lib/nexus-shield}" \
    pythong "$py" board 2>/dev/null || pythong "$py" json >/dev/null || true
  nexus_os_assist_log "field polkit boarded"
}

nexus_os_assist_cpu_hardening() {
  local root="${NEXUS_INSTALL_ROOT:-/usr/local/lib/nexus-shield}"
  local py="${root}/lib/cpu-vulnerability-shield.py"
  [[ -f "$py" ]] || return 0
  NEXUS_INSTALL_ROOT="${root}" NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-/var/lib/nexus-shield}" \
    NEXUS_CPU_VULN_APPLY=1 \
    pythong "$py" board 2>/dev/null || pythong "$py" json >/dev/null || true
  nexus_os_assist_log "cpu vulnerability shield boarded"
}

nexus_os_assist_native_layer() {
  local root="${NEXUS_INSTALL_ROOT:-/usr/local/lib/nexus-shield}"
  local py="${root}/lib/native-layer.py"
  [[ -f "$py" ]] || return 0
  nexus_os_assist_export_paths
  NEXUS_INSTALL_ROOT="${root}" NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-/var/lib/nexus-shield}" \
  SG_ROOT="${SG_ROOT:-}" KILROY_ROOT="${KILROY_ROOT:-}" QUEEN_ROOT="${QUEEN_ROOT:-}" \
    pythong "$py" board 2>/dev/null || true
  nexus_os_assist_log "native layer boarded"
}

nexus_os_assist_root_sovereign() {
  local root="${NEXUS_INSTALL_ROOT:-/usr/local/lib/nexus-shield}"
  nexus_os_assist_export_paths
  local py="${QUEEN_ROOT:-${root}/Queen}/lib/queen-root-sovereign.py"
  [[ -f "$py" ]] || return 0
  pythong "$py" seal 2>/dev/null || true
  nexus_os_assist_log "root sovereign covenant sealed"
}

nexus_os_assist_perimeter() {
  local root="${NEXUS_INSTALL_ROOT:-/usr/local/lib/nexus-shield}"
  [[ -f "${root}/lib/field-perimeter-shield.sh" ]] || return 0
  # shellcheck source=/dev/null
  source "${root}/lib/field-perimeter-shield.sh"
  nexus_perimeter_shield_board
  nexus_os_assist_log "field perimeter boarded"
}

nexus_os_assist_desktop_entries() {
  local root="${NEXUS_INSTALL_ROOT:-/usr/local/lib/nexus-shield}"
  local user="${1:-${SUDO_USER:-$USER}}"
  [[ -n "$user" && "$user" != "root" ]] || return 0
  if [[ -f "${root}/lib/installer.sh" ]]; then
    # shellcheck source=/dev/null
    source "${root}/lib/installer.sh"
    nexus_install_linux_desktop_user "$root" "$user"
    nexus_os_assist_log "desktop entry nexus-field for ${user}"
  fi
}

nexus_os_assist_deploy_extras() {
  local src="${1:-}"
  local dest="${NEXUS_INSTALL_ROOT:-/usr/local/lib/nexus-shield}"
  [[ -n "$src" && -d "$src" ]] || return 0
  install -d -m 755 "${dest}/install" "${dest}/scripts"
  [[ -d "${src}/install" ]] && cp -a "${src}/install" "${dest}/" 2>/dev/null || true
  [[ -d "${src}/scripts" ]] && cp -a "${src}/scripts/." "${dest}/scripts/" 2>/dev/null || true
  if [[ -d "${src}/Queen" ]]; then
    rm -rf "${dest}/Queen" 2>/dev/null || true
    cp -a "${src}/Queen" "${dest}/"
  fi
  for f in install-all.sh nexus.sh; do
    [[ -f "${src}/${f}" ]] && install -m 755 "${src}/${f}" "${dest}/${f}" 2>/dev/null || true
  done
  nexus_os_assist_log "payload extras deployed (Queen, scripts, install, launcher)"
}

nexus_os_assist_write_report() {
  local root="${NEXUS_INSTALL_ROOT:-/usr/local/lib/nexus-shield}"
  local state="${NEXUS_STATE_DIR:-/var/lib/nexus-shield}"
  local report="${state}/install-report.json"
  mkdir -p "$state"
  pythong - <<'PY' >"$report" 2>/dev/null || true
import json, os, subprocess, sys
from pathlib import Path
root = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
state = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
doc = {"schema": "nexus-install-report/v1", "install_root": str(root)}
for name, script in (
    ("native_layer", "native-layer.py"),
    ("cpu_vulnerability", "cpu-vulnerability-shield.py"),
    ("ai_integration", "ai-integration-hook.py"),
    ("field_underlay", "field-underlay.py"),
    ("tristate_installer", "field-underlay-switch.py"),
    ("field_perimeter", "field-perimeter-shield.py"),
):
    p = root / "lib" / script
    if p.is_file():
        try:
            proc = subprocess.run([sys.executable, str(p), "json"], capture_output=True, text=True, timeout=30,
                                  env={**os.environ, "NEXUS_INSTALL_ROOT": str(root), "NEXUS_STATE_DIR": str(state),
                                       "NEXUS_PROBE_DEPTH": "1"})
            doc[name] = json.loads(proc.stdout or "{}")
        except Exception as exc:
            doc[name] = {"error": str(exc)}
doc["field_polkit"] = {}
fp = root / "lib" / "field-polkit.py"
if fp.is_file():
    try:
        proc = subprocess.run([sys.executable, str(fp), "json"], capture_output=True, text=True, timeout=20,
                              env={**os.environ, "NEXUS_INSTALL_ROOT": str(root), "NEXUS_STATE_DIR": str(state),
                                   "NEXUS_PROBE_DEPTH": "1"})
        doc["field_polkit"] = json.loads(proc.stdout or "{}")
    except Exception as exc:
        doc["field_polkit"] = {"error": str(exc)}
doc["polkit"] = Path("/usr/share/polkit-1/actions/com.nexus.field.policy").is_file()
doc["service_active"] = subprocess.run(["systemctl", "is-active", "nexus-genius.service"],
                                       capture_output=True, text=True).stdout.strip()
print(json.dumps(doc, indent=2))
PY
  nexus_os_assist_log "report ${report}"
}

nexus_os_assist_drive_converter() {
  local root="${NEXUS_INSTALL_ROOT:-/usr/local/lib/nexus-shield}"
  local py="${root}/lib/field-drive-converter.py"
  [[ -f "$py" ]] || return 0
  nexus_os_assist_export_paths
  NEXUS_INSTALL_ROOT="${root}" NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-/var/lib/nexus-shield}" \
    SG_ROOT="${SG_ROOT:-}" KILROY_FIELD_ROOT="${KILROY_FIELD_ROOT:-/media/default/KILROY_FIELD}" \
    pythong "$py" audit 2>/dev/null || true
  NEXUS_INSTALL_ROOT="${root}" NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-/var/lib/nexus-shield}" \
    SG_ROOT="${SG_ROOT:-}" KILROY_FIELD_ROOT="${KILROY_FIELD_ROOT:-/media/default/KILROY_FIELD}" \
    pythong "$py" scan 2>/dev/null || true
  nexus_os_assist_log "drive converter audit+scan (dry-run, in-place plan)"
}

nexus_os_assist_underlay_switch() {
  local root="${NEXUS_INSTALL_ROOT:-/usr/local/lib/nexus-shield}"
  [[ -f "${root}/lib/field-underlay-switch.sh" ]] || return 0
  # shellcheck source=/dev/null
  source "${root}/lib/field-underlay-switch.sh"
  nexus_underlay_switch_board
  if [[ -n "${SUDO_USER:-}" && "${SUDO_USER}" != "root" ]]; then
    nexus_underlay_hotkey_install "${SUDO_USER}"
  fi
  nexus_os_assist_log "tristate installer + F9 hotkey"
}

nexus_os_assist_all() {
  local src="${1:-${NEXUS_INSTALL_SRC:-}}"
  nexus_os_assist_export_paths
  nexus_os_assist_install_polkit
  nexus_os_assist_deploy_extras "$src"
  nexus_os_assist_field_polkit
  nexus_os_assist_board_hooks
  nexus_os_assist_native_layer
  nexus_os_assist_cpu_hardening
  nexus_os_assist_perimeter
  nexus_os_assist_root_sovereign
  if [[ -f "${root}/lib/field-operator.sh" ]]; then
    # shellcheck source=/dev/null
    source "${root}/lib/field-operator.sh"
    nexus_field_operator_once 2>/dev/null || true
    nexus_os_assist_log "operator iron plate boarded"
  fi
  nexus_os_assist_drive_converter
  nexus_os_assist_underlay_switch
  nexus_os_assist_desktop_entries "${SUDO_USER:-${INSTALL_USER:-$USER}}"
  nexus_os_assist_write_report
  nexus_os_assist_log "complete"
}