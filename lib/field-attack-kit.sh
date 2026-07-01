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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/field-attack-kit.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# NEXUS Field Attack Kit — permanent hostile-host disable + field drive memory.
# Intelligence is a bullet: identify, record, crush. Survives reboot via field storage.

[[ -f "${NEXUS_INSTALL_ROOT}/lib/field-toolkit.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/field-toolkit.sh"
[[ -f "${NEXUS_INSTALL_ROOT}/lib/hardware-destruction.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/hardware-destruction.sh"

NEXUS_FIELD_HOSTILE="${NEXUS_FIELD_HOSTILE:-${NEXUS_STATE_DIR}/field-hostile.tsv}"
NEXUS_FIELD_NOKILL="${NEXUS_FIELD_NOKILL:-${NEXUS_STATE_DIR}/field-nokill.tsv}"
NEXUS_HOSTILE_MEMORY_FILE="${NEXUS_HOSTILE_MEMORY_FILE:-nexus-hostile.jsonl}"
NEXUS_TARGET_DOSSIER_FILE="${NEXUS_TARGET_DOSSIER_FILE:-nexus-target-dossiers.jsonl}"
HOSTESS7_TEAM_FIELD="${HOSTESS7_TEAM_FIELD:-/media/default/HOSTESS7_TEAM/fieldstorage}"

nexus_field_attack_memory_paths() {
  local root="${HOSTESS7_ROOT:-${NEXUS_INSTALL_ROOT:-/usr/local/lib/nexus-shield}/Hostess7}"
  printf '%s\n' \
    "${root}/cache/fieldstorage/brain/security/${NEXUS_HOSTILE_MEMORY_FILE}" \
    "${HOSTESS7_TEAM_FIELD}/brain/security/${NEXUS_HOSTILE_MEMORY_FILE}" \
    "${NEXUS_STATE_DIR}/field-storage/${NEXUS_HOSTILE_MEMORY_FILE}"
}

nexus_field_attack_dossier_paths() {
  local root="${HOSTESS7_ROOT:-${NEXUS_INSTALL_ROOT:-/usr/local/lib/nexus-shield}/Hostess7}"
  printf '%s\n' \
    "${root}/cache/fieldstorage/brain/security/${NEXUS_TARGET_DOSSIER_FILE}" \
    "${HOSTESS7_TEAM_FIELD}/brain/security/${NEXUS_TARGET_DOSSIER_FILE}" \
    "${NEXUS_STATE_DIR}/field-storage/${NEXUS_TARGET_DOSSIER_FILE}"
}

nexus_field_attack_init() {
  mkdir -p "$(dirname "$NEXUS_FIELD_HOSTILE")" 2>/dev/null || true
  [[ -f "$NEXUS_FIELD_HOSTILE" ]] || printf 'ts\tip\tvector\tseverity\treason\tsource\n' >"$NEXUS_FIELD_HOSTILE"
  chmod 640 "$NEXUS_FIELD_HOSTILE" 2>/dev/null || true
  chown root:nexus "$NEXUS_FIELD_HOSTILE" 2>/dev/null || true
  [[ -f "$NEXUS_FIELD_NOKILL" ]] || printf 'ts\tip\tvector\tseverity\treason\tsource\n' >"$NEXUS_FIELD_NOKILL"
  chmod 640 "$NEXUS_FIELD_NOKILL" 2>/dev/null || true
  chown root:nexus "$NEXUS_FIELD_NOKILL" 2>/dev/null || true
  mkdir -p "${NEXUS_STATE_DIR}/field-storage/brain/security" 2>/dev/null || true
}

nexus_field_attack_is_ipv4() {
  [[ "${1:-}" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]
}

nexus_field_attack_is_disabled() {
  local ip="${1:-}"
  [[ -n "$ip" ]] || return 1
  nexus_field_attack_init
  awk -F'\t' -v ip="$ip" 'NR > 1 && $2 == ip { found = 1 } END { exit(found ? 0 : 1) }' \
    "$NEXUS_FIELD_HOSTILE" 2>/dev/null
}

nexus_field_attack_is_nokill() {
  local ip="${1:-}"
  [[ -n "$ip" ]] || return 1
  nexus_field_attack_init
  awk -F'\t' -v ip="$ip" 'NR > 1 && $2 == ip { found = 1 } END { exit(found ? 0 : 1) }' \
    "$NEXUS_FIELD_NOKILL" 2>/dev/null
}

nexus_field_attack_record_field() {
  local ip="$1" vector="$2" severity="$3" reason="$4" source="${5:-attack-kit}" meta="${6:-}"
  local ts path dir entry
  ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date)"
  entry="$(
    TS="$ts" IP="$ip" VECTOR="${vector:-HOSTILE}" SEV="${severity:-high}" \
      REASON="${reason:-field_attack}" SRC="$source" META="${meta:-}" pythong -c '
import json, os
meta = {}
raw = os.environ.get("META", "")
if raw:
    try:
        meta = json.loads(raw)
    except Exception:
        meta = {"note": raw}
print(json.dumps({
    "kind": "nexus_hostile",
    "ts": os.environ["TS"],
    "ip": os.environ["IP"],
    "vector": os.environ["VECTOR"],
    "severity": os.environ["SEV"],
    "reason": os.environ["REASON"],
    "source": os.environ["SRC"],
    "permanent": True,
    "meta": meta,
}, ensure_ascii=False))
' 2>/dev/null
  )" || return 0
  [[ -n "$entry" ]] || return 0

  while IFS= read -r path; do
    [[ -n "$path" ]] || continue
    dir="$(dirname "$path")"
    mkdir -p "$dir" 2>/dev/null || continue
    if [[ -f "$path" ]] && grep -qF "\"ip\": \"${ip}\"" "$path" 2>/dev/null; then
      continue
    fi
    printf '%s\n' "$entry" >>"$path" 2>/dev/null || continue
    chmod 640 "$path" 2>/dev/null || true
    chown root:nexus "$path" 2>/dev/null || chown root:root "$path" 2>/dev/null || true
  done < <(nexus_field_attack_memory_paths)
}

nexus_field_attack_record_dossier_forever() {
  local ip="$1" vector="$2" severity="$3" reason="$4" source="${5:-attack-kit}" dossier="${6:-}"
  local ts path dir entry
  [[ -n "$ip" && -n "$dossier" ]] || return 0
  ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date)"
  entry="$(
    TS="$ts" IP="$ip" VECTOR="${vector:-HOSTILE}" SEV="${severity:-high}" \
      REASON="${reason:-target_kill}" SRC="$source" DOSSIER="$dossier" pythong -c '
import json, os
raw = os.environ.get("DOSSIER", "")
try:
    dossier = json.loads(raw) if raw else {}
except Exception:
    dossier = {"note": raw[:2000]}
print(json.dumps({
    "kind": "nexus_target_dossier",
    "ts": os.environ["TS"],
    "ip": os.environ["IP"],
    "vector": os.environ["VECTOR"],
    "severity": os.environ["SEV"],
    "reason": os.environ["REASON"],
    "source": os.environ["SRC"],
    "permanent": True,
    "dossier": dossier,
}, ensure_ascii=False))
' 2>/dev/null
  )" || return 0
  [[ -n "$entry" ]] || return 0

  while IFS= read -r path; do
    [[ -n "$path" ]] || continue
    dir="$(dirname "$path")"
    mkdir -p "$dir" 2>/dev/null || continue
    printf '%s\n' "$entry" >>"$path" 2>/dev/null || continue
    chmod 640 "$path" 2>/dev/null || true
    chown root:nexus "$path" 2>/dev/null || chown root:root "$path" 2>/dev/null || true
  done < <(nexus_field_attack_dossier_paths)
}

nexus_field_attack_nokill_target() {
  local ip="${1:-}" vector="${2:-HOSTILE}" severity="${3:-high}" reason="${4:-operator_nokill}"
  local source="${5:-attack-kit}"
  [[ -n "$ip" ]] || return 1
  nexus_field_attack_is_ipv4 "$ip" || return 1
  nexus_field_attack_init
  nexus_field_attack_is_nokill "$ip" && {
    nexus_log "INFO" "field-attack-kit" "NOKILL_ALREADY ip=${ip}"
    return 0
  }
  local ts
  ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date)"
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$ts" "$ip" "$vector" "$severity" "$reason" "$source" \
    >>"$NEXUS_FIELD_NOKILL"
  nexus_field_attack_record_field "$ip" "$vector" "$severity" "$reason" "$source" \
    '{"action":"NO_KILL","exempt":true}'
  nexus_log "ALERT" "field-attack-kit" "TARGET_NOKILL ip=${ip} vector=${vector} reason=${reason}"
  return 0
}

nexus_field_attack_kill_target() {
  local ip="${1:-}" vector="${2:-HOSTILE}" severity="${3:-high}" reason="${4:-target_kill}"
  local source="${5:-attack-kit}" dossier="${6:-}"
  [[ -n "$ip" ]] || return 1
  nexus_field_attack_is_nokill "$ip" && {
    nexus_log "ALERT" "field-attack-kit" "KILL_REFUSED_NOKILL ip=${ip}"
    return 1
  }
  # shellcheck source=/dev/null
  source "${NEXUS_INSTALL_ROOT}/lib/friendly-guard.sh"
  local monitor_json=""
  if [[ -n "$dossier" ]]; then
    monitor_json="$(DOSSIER_JSON="$dossier" pythong -c '
import json, os
try:
    d = json.loads(os.environ.get("DOSSIER_JSON", "") or "{}")
except Exception:
    d = {}
m = d.get("monitor")
if m:
    print(json.dumps(m, ensure_ascii=False))
' 2>/dev/null)"
  fi
  if nexus_friendly_guard_refuse_kill "$ip" "$monitor_json"; then
    nexus_log "ALERT" "field-attack-kit" "KILL_REFUSED_FRIENDLY ip=${ip}"
    return 1
  fi
  nexus_field_attack_disable_host "$ip" "$vector" "$severity" "$reason" "$source" "$dossier" || return 1
  local hw_destroy=0
  if [[ -n "$dossier" && "$dossier" != "{}" ]]; then
    hw_destroy="$(DOSSIER_JSON="$dossier" pythong -c '
import json, os, sys
try:
    d = json.loads(os.environ.get("DOSSIER_JSON", "") or "{}")
except Exception:
    sys.exit(0)
if d.get("hardware_destroy") or d.get("action") == "HARDWARE_DESTROY":
    print(1)
' 2>/dev/null || echo 0)"
    nexus_field_attack_record_dossier_forever "$ip" "$vector" "$severity" "$reason" "$source" "$dossier"
  fi
  if [[ "$hw_destroy" == "1" ]] && declare -f nexus_hardware_destroy_target >/dev/null 2>&1; then
    nexus_hardware_destroy_target "$ip" "$dossier" || true
    nexus_log "ALERT" "field-attack-kit" "TARGET_HARDWARE_DESTROYED ip=${ip} vector=${vector}"
  fi
  nexus_log "ALERT" "field-attack-kit" "TARGET_KILLED ip=${ip} vector=${vector} dossier=archived hw=${hw_destroy}"
  return 0
}

nexus_field_attack_rekill_target() {
  local ip="${1:-}" vector="${2:-HOSTILE}" severity="${3:-high}" reason="${4:-rekill_validated}"
  local source="${5:-attack-kit}" dossier="${6:-}"
  [[ -n "$ip" ]] || return 1
  nexus_field_attack_is_nokill "$ip" && {
    nexus_log "ALERT" "field-attack-kit" "REKILL_REFUSED_NOKILL ip=${ip}"
    return 1
  }
  # shellcheck source=/dev/null
  source "${NEXUS_INSTALL_ROOT}/lib/friendly-guard.sh"
  local monitor_json=""
  if [[ -n "$dossier" ]]; then
    monitor_json="$(DOSSIER_JSON="$dossier" pythong -c '
import json, os
try:
    d = json.loads(os.environ.get("DOSSIER_JSON", "") or "{}")
except Exception:
    d = {}
m = d.get("monitor")
if m:
    print(json.dumps(m, ensure_ascii=False))
' 2>/dev/null)"
  fi
  if nexus_friendly_guard_refuse_kill "$ip" "$monitor_json"; then
    nexus_log "ALERT" "field-attack-kit" "REKILL_REFUSED_FRIENDLY ip=${ip}"
    return 1
  fi
  nexus_field_attack_init
  if declare -f nexus_firewall_block_ip_forever >/dev/null 2>&1; then
    nexus_firewall_block_ip_forever out "$ip" "${reason}" || true
    nexus_firewall_block_ip_forever in "$ip" "${reason}" || true
  fi
  local ts
  ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date)"
  if ! nexus_field_attack_is_disabled "$ip"; then
    printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$ts" "$ip" "$vector" "$severity" "$reason" "$source" \
      >>"$NEXUS_FIELD_HOSTILE"
  fi
  nexus_field_attack_record_field "$ip" "$vector" "$severity" "$reason" "$source" "$dossier"
  if [[ -n "$dossier" && "$dossier" != "{}" ]]; then
    nexus_field_attack_record_dossier_forever "$ip" "$vector" "$severity" "$reason" "$source" "$dossier"
    if DOSSIER_JSON="$dossier" pythong -c '
import json, os, sys
try:
    d = json.loads(os.environ.get("DOSSIER_JSON", "") or "{}")
except Exception:
    sys.exit(0)
if d.get("hardware_destroy") or d.get("action") == "HARDWARE_DESTROY":
    sys.exit(0)
sys.exit(1)
' 2>/dev/null; then
      declare -f nexus_hardware_destroy_target >/dev/null 2>&1 && nexus_hardware_destroy_target "$ip" "$dossier" || true
    fi
  fi
  nexus_log "ALERT" "field-attack-kit" "TARGET_REKILLED ip=${ip} vector=${vector} reason=${reason}"
  return 0
}

nexus_field_attack_disable_host() {
  local ip="${1:-}" vector="${2:-HOSTILE}" severity="${3:-high}" reason="${4:-field_attack_kit}"
  local source="${5:-attack-kit}" meta="${6:-}"
  if [[ -z "$meta" && -n "${NEXUS_ATTACK_META:-}" && -f "${NEXUS_ATTACK_META}" ]]; then
    meta="$(cat "${NEXUS_ATTACK_META}" 2>/dev/null || echo '{}')"
  fi
  [[ -n "$meta" ]] || meta='{}'
  [[ -n "$ip" ]] || return 1
  nexus_field_attack_is_ipv4 "$ip" || return 1

  # shellcheck source=/dev/null
  source "${NEXUS_INSTALL_ROOT}/lib/friendly-guard.sh"
  local monitor_json=""
  if [[ -n "$meta" ]]; then
    monitor_json="$(META_JSON="$meta" pythong -c '
import json, os
try:
    d = json.loads(os.environ.get("META_JSON", "") or "{}")
except Exception:
    d = {}
m = d.get("monitor")
if m:
    print(json.dumps(m, ensure_ascii=False))
' 2>/dev/null)"
  fi
  if nexus_friendly_guard_refuse_kill "$ip" "$monitor_json"; then
    nexus_log "ALERT" "field-attack-kit" "KILL_REFUSED_FRIENDLY ip=${ip}"
    return 1
  fi

  nexus_field_attack_init
  nexus_field_attack_is_disabled "$ip" && {
    nexus_log "INFO" "field-attack-kit" "DISABLE_ALREADY ip=${ip}"
    return 0
  }

  if declare -f nexus_firewall_block_ip_forever >/dev/null 2>&1; then
    nexus_firewall_block_ip_forever out "$ip" "${reason}" || true
    nexus_firewall_block_ip_forever in "$ip" "${reason}" || true
  fi

  local ts
  ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date)"
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$ts" "$ip" "$vector" "$severity" "$reason" "$source" \
    >>"$NEXUS_FIELD_HOSTILE"
  nexus_field_attack_record_field "$ip" "$vector" "$severity" "$reason" "$source" "$meta"
  nexus_field_attack_every_kill_rekill "$ip" "$vector" "$severity" "${reason}" "$source" || true
  nexus_log "ALERT" "field-attack-kit" "HOST_DISABLED_PERMANENT ip=${ip} vector=${vector} reason=${reason}"
  return 0
}

nexus_field_attack_sync_from_memory() {
  local path line ip vector severity reason ts source
  nexus_field_attack_init
  while IFS= read -r path; do
    [[ -f "$path" ]] || continue
    while IFS= read -r line; do
      [[ -n "$line" ]] || continue
      read -r ip vector severity reason ts source < <(
        pythong -c '
import json, sys
try:
    o = json.loads(sys.stdin.read())
except Exception:
    sys.exit(0)
if o.get("kind") != "nexus_hostile" or o.get("revoked"):
    sys.exit(0)
print(
    o.get("ip", ""),
    o.get("vector", "HOSTILE"),
    o.get("severity", "high"),
    o.get("reason", "field_memory"),
    o.get("ts", ""),
    o.get("source", "field-drive"),
)
' <<<"$line" 2>/dev/null
      )
      [[ -n "$ip" ]] || continue
      nexus_field_attack_is_ipv4 "$ip" || continue
      nexus_field_attack_is_disabled "$ip" && continue
      [[ -n "$ts" ]] || ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date)"
      printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$ts" "$ip" "$vector" "$severity" "$reason" "${source:-field-drive}" \
        >>"$NEXUS_FIELD_HOSTILE"
      if declare -f nexus_firewall_block_ip_forever >/dev/null 2>&1; then
        nexus_firewall_block_ip_forever out "$ip" "${reason}" || true
        nexus_firewall_block_ip_forever in "$ip" "${reason}" || true
      fi
    done <"$path"
  done < <(nexus_field_attack_memory_paths)
}

nexus_field_attack_apply_registry() {
  [[ "${NEXUS_FIELD_ATTACK_KIT:-1}" == "1" ]] || return 0
  nexus_field_attack_init
  local _ ip vector severity reason source
  while IFS=$'\t' read -r _ ip vector severity reason source; do
    [[ -n "$ip" ]] || continue
    nexus_field_attack_is_ipv4 "$ip" || continue
    if declare -f nexus_firewall_block_ip_forever >/dev/null 2>&1; then
      nexus_firewall_block_ip_forever out "$ip" "${reason:-field_registry}" || true
      nexus_firewall_block_ip_forever in "$ip" "${reason:-field_registry}" || true
    fi
  done < <(tail -n +2 "$NEXUS_FIELD_HOSTILE" 2>/dev/null)
  nexus_field_attack_forever_kill_enforce >/dev/null 2>&1 || true
}

nexus_field_attack_autokill_certain() {
  command -v pythong >/dev/null 2>&1 || return 1
  local script="${NEXUS_INSTALL_ROOT}/lib/field-attack-kit.py"
  [[ -f "$script" ]] || return 1
  NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
    pythong "$script" autokill-certain 2>/dev/null
}

nexus_field_attack_autokill_needs_die() {
  command -v pythong >/dev/null 2>&1 || return 1
  local script="${NEXUS_INSTALL_ROOT}/lib/field-attack-kit.py"
  [[ -f "$script" ]] || return 1
  NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
    pythong "$script" autokill-needs-die 2>/dev/null
}

nexus_field_attack_forever_kill_enforce() {
  command -v pythong >/dev/null 2>&1 || return 1
  local script="${NEXUS_INSTALL_ROOT}/lib/field-attack-kit.py"
  [[ -f "$script" ]] || return 1
  NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
    pythong "$script" forever-kill-enforce 2>/dev/null
}

nexus_field_attack_crush_hot() {
  command -v pythong >/dev/null 2>&1 || return 1
  local script="${NEXUS_INSTALL_ROOT}/lib/field-attack-kit.py"
  [[ -f "$script" ]] || return 1
  NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
    pythong "$script" crush-hot 2>/dev/null
}

nexus_field_attack_every_kill_rekill() {
  local ip="${1:-}" vector="${2:-HOSTILE}" severity="${3:-high}" reason="${4:-every_kill_rekill}"
  local source="${5:-attack-kit}"
  [[ -n "$ip" ]] || return 0
  local py script
  py="$(nexus_field_attack_resolve_python 2>/dev/null || true)"
  script="${NEXUS_INSTALL_ROOT}/lib/field-attack-kit.py"
  [[ -n "$py" && -f "$script" ]] || return 0
  NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
    "$py" "$script" register-rekill "$ip" "$vector" "$severity" "$reason" >/dev/null 2>&1 || true
  nexus_field_attack_rekill_target "$ip" "$vector" "$severity" "every_kill_rekill:${reason}" "$source" \
    '{"rekill":true,"every_kill_rekill":true,"action":"REKILL"}' || true
}

nexus_field_attack_auto_rekill() {
  [[ "$(nexus_settings_get NEXUS_FIELD_AUTO_REKILL 2>/dev/null || echo "${NEXUS_FIELD_AUTO_REKILL:-1}")" == "1" ]] || return 0
  local py script
  py="$(nexus_field_attack_resolve_python 2>/dev/null || true)"
  script="${NEXUS_INSTALL_ROOT}/lib/field-attack-kit.py"
  [[ -n "$py" && -f "$script" ]] || return 1
  NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
    "$py" "$script" rekill-all-registered 2>/dev/null || true
  NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
    "$py" "$script" auto-rekill 2>/dev/null
}

# Constant RE-KILL cycle — runs while hostile registry has entries (killed C2 / bad shit).
# Throttled by default; kill-detect harm-signature changes bypass throttle.
nexus_field_attack_rekill_cycle() {
  local force="${1:-0}"
  [[ "${NEXUS_FIELD_ATTACK_KIT:-1}" == "1" ]] || return 0
  [[ "$(nexus_settings_get NEXUS_FIELD_AUTO_REKILL 2>/dev/null || echo "${NEXUS_FIELD_AUTO_REKILL:-1}")" == "1" ]] || return 0
  local hostile_count
  hostile_count="$(nexus_field_attack_count 2>/dev/null || echo 0)"
  [[ "${hostile_count:-0}" -gt 0 ]] || return 0
  if [[ "$force" != "1" ]]; then
    local interval="${NEXUS_FIELD_REKILL_INTERVAL:-60}"
    local stamp="${NEXUS_STATE_DIR}/rekill-cycle.stamp"
    local now last
    now="$(date +%s 2>/dev/null || echo 0)"
    last="$(cat "$stamp" 2>/dev/null || echo 0)"
    if [[ "$now" -gt 0 && "$last" -gt 0 && $((now - last)) -lt "$interval" ]]; then
      return 0
    fi
    printf '%s' "$now" >"$stamp" 2>/dev/null || true
  fi
  nexus_field_attack_auto_rekill >/dev/null 2>&1 || true
  nexus_field_attack_forever_kill_enforce >/dev/null 2>&1 || true
}

nexus_field_attack_autokill() {
  [[ "$(nexus_settings_get NEXUS_ATTACK_KIT_AUTO_CRUSH 2>/dev/null || echo "${NEXUS_ATTACK_KIT_AUTO_CRUSH:-1}")" == "1" ]] || return 0
  nexus_field_attack_autokill_needs_die >/dev/null 2>&1 || nexus_field_attack_autokill_certain >/dev/null 2>&1 || true
  nexus_field_attack_auto_rekill >/dev/null 2>&1 || true
  nexus_field_attack_forever_kill_enforce >/dev/null 2>&1 || true
}

# Back-compat alias
nexus_field_attack_auto_crush() {
  nexus_field_attack_autokill
}

nexus_field_attack_resolve_python() {
  local py=""
  if declare -f nexus_resolve_pythong >/dev/null 2>&1; then
    py="$(nexus_resolve_pythong 2>/dev/null || true)"
  fi
  [[ -n "$py" && -x "$py" ]] || py="$(command -v pythong 2>/dev/null || true)"
  [[ -n "$py" && -x "$py" ]] || py="$(command -v python3 2>/dev/null || true)"
  [[ -n "$py" && -x "$py" ]] || return 1
  printf '%s' "$py"
}

nexus_field_attack_revalidate_kill_list() {
  [[ "${NEXUS_FIELD_ATTACK_KIT:-1}" == "1" ]] || return 0
  local py script
  py="$(nexus_field_attack_resolve_python)" || return 1
  script="${NEXUS_INSTALL_ROOT}/lib/field-attack-kit.py"
  [[ -f "$script" ]] || return 1
  nexus_field_attack_init
  nexus_field_attack_sync_from_memory || true
  NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
    "$py" "$script" revalidate-kill-list 2>/dev/null
}

# Boot hook — revalidate kill list + RE-KILL validated same-host returners immediately.
nexus_field_attack_boot_rekill() {
  [[ "${NEXUS_FIELD_ATTACK_KIT:-1}" == "1" ]] || return 0
  [[ "$(nexus_settings_get NEXUS_FIELD_AUTO_REKILL 2>/dev/null || echo "${NEXUS_FIELD_AUTO_REKILL:-1}")" == "1" ]] || return 0
  local py script
  py="$(nexus_field_attack_resolve_python)" || return 1
  script="${NEXUS_INSTALL_ROOT}/lib/field-attack-kit.py"
  [[ -f "$script" ]] || return 1
  nexus_field_attack_init
  nexus_field_attack_sync_from_memory || true
  export NEXUS_BOOT_REKILL=1
  NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
    "$py" "$script" boot-rekill 2>/dev/null || {
    nexus_field_attack_revalidate_kill_list || true
    nexus_field_attack_apply_registry || true
    nexus_field_attack_rekill_cycle 1
  }
  nexus_log "ALERT" "field-attack-kit" "BOOT_REKILL complete"
}

nexus_field_attack_install_autokill() {
  [[ "${NEXUS_FIELD_ATTACK_KIT:-1}" == "1" ]] || return 0
  nexus_field_attack_init
  if declare -f nexus_host_attack_publish >/dev/null 2>&1; then
    nexus_host_attack_publish >/dev/null 2>&1 || true
  elif [[ -f "${NEXUS_INSTALL_ROOT}/lib/host-attack-map.py" ]]; then
    NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
      pythong "${NEXUS_INSTALL_ROOT}/lib/host-attack-map.py" build >/dev/null 2>&1 || true
  fi
  nexus_field_attack_sync_from_memory || true
  nexus_field_attack_boot_rekill || true
  nexus_field_attack_autokill || true
  nexus_log "ALERT" "field-attack-kit" "INSTALL_AUTOKILL complete"
}

nexus_field_attack_publish() {
  [[ "${NEXUS_FIELD_ATTACK_KIT:-1}" == "1" ]] || return 0
  nexus_field_attack_sync_from_memory
  nexus_field_attack_apply_registry
}

nexus_field_attack_publish_deep() {
  [[ "${NEXUS_FIELD_ATTACK_KIT:-1}" == "1" ]] || return 0
  nexus_field_attack_publish
  nexus_field_attack_auto_crush
}

nexus_field_attack_count() {
  nexus_field_attack_init
  awk 'NR > 1 && $2 != "" { c++ } END { print c + 0 }' "$NEXUS_FIELD_HOSTILE" 2>/dev/null
}

nexus_field_attack_nokill_count() {
  nexus_field_attack_init
  awk 'NR > 1 && $2 != "" { c++ } END { print c + 0 }' "$NEXUS_FIELD_NOKILL" 2>/dev/null
}

nexus_field_attack_json() {
  nexus_field_attack_init
  local count field_paths=0 p
  count="$(nexus_field_attack_count)"
  local nokill_count
  nokill_count="$(nexus_field_attack_nokill_count)"
  while IFS= read -r p; do
    [[ -f "$p" ]] && field_paths=$((field_paths + 1))
  done < <(nexus_field_attack_memory_paths)

  printf '{'
  printf '"motto":"Hell goes to Hell — Hell Kit severs wire, regional disable, human threat sweep. 100%% PINPOINT CERTAIN hardware-destroys forever on field drive.",'
  printf '"enabled":%s,' "${NEXUS_FIELD_ATTACK_KIT:-1}"
  printf '"auto_crush":%s,' "$(nexus_settings_get NEXUS_ATTACK_KIT_AUTO_CRUSH 2>/dev/null || echo 0)"
  printf '"disabled_count":%s,' "${count:-0}"
  printf '"nokill_count":%s,' "${nokill_count:-0}"
  printf '"field_paths_ready":%s,' "$field_paths"
  printf '"standards":["IEEE-802-OUI","RFC7483-RDAP","GeoIP","Field-Memory","Trust-Strike-Engine"],'
  local trust_json="{}"
  if [[ -s "${NEXUS_STATE_DIR}/trust-strike-summary.json" ]]; then
    trust_json="$(pythong -c "import json,sys; json.dump(json.load(open(sys.argv[1])), sys.stdout)" \
      "${NEXUS_STATE_DIR}/trust-strike-summary.json" 2>/dev/null || echo '{}')"
  elif [[ -f "${NEXUS_INSTALL_ROOT}/lib/trust-strike-engine.py" ]]; then
    trust_json="$(NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
      pythong "${NEXUS_INSTALL_ROOT}/lib/trust-strike-engine.py" summary 2>/dev/null || echo '{}')"
  fi
  printf '"trust_strike":%s,' "${trust_json:-"{}"}"
  printf '"hosts":['
  local first=1 ts ip vector severity reason source
  while IFS=$'\t' read -r ts ip vector severity reason source; do
    [[ -n "$ip" ]] || continue
    [[ "$first" -eq 1 ]] || printf ','
    first=0
    printf '{"ts":"%s","ip":"%s","vector":"%s","severity":"%s","reason":"%s","source":"%s","permanent":true}' \
      "$ts" "$ip" "$vector" "$severity" "${reason:-}" "${source:-}"
  done < <(tail -n +2 "$NEXUS_FIELD_HOSTILE" 2>/dev/null | tail -n 40)
  printf '],'
  printf '"field_toolkit":'
  if declare -f nexus_field_toolkit_json >/dev/null 2>&1; then
    nexus_field_toolkit_json
  else
    printf '{}'
  fi
  printf ',"hostile_ai":'
  if [[ -f "${NEXUS_INSTALL_ROOT}/lib/hostile-ai-destroy.py" ]]; then
    NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
      pythong "${NEXUS_INSTALL_ROOT}/lib/hostile-ai-destroy.py" json 2>/dev/null || printf '{}'
  else
    printf '{}'
  fi
  printf '}'
}