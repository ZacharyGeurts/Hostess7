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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/firewall-trust.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Firewall trust — permanent operator-authorized peers (panel click + Hostess7 field memory).

NEXUS_FIREWALL_TRUSTED="${NEXUS_FIREWALL_TRUSTED:-${NEXUS_STATE_DIR}/firewall-trusted.tsv}"
# shellcheck source=/dev/null
[[ -f "$(dirname "${BASH_SOURCE[0]}")/sg-paths.sh" ]] && source "$(dirname "${BASH_SOURCE[0]}")/sg-paths.sh"
sg_paths_export_defaults 2>/dev/null || true
HOSTESS7_TEAM_FIELD="${HOSTESS7_TEAM_FIELD:-$(sg_paths_hostess7_team_field 2>/dev/null)}"
NEXUS_TRUST_MEMORY_FILE="${NEXUS_TRUST_MEMORY_FILE:-nexus-trusted.jsonl}"

nexus_firewall_trust_init() {
  mkdir -p "$(dirname "$NEXUS_FIREWALL_TRUSTED")" 2>/dev/null || true
  [[ -f "$NEXUS_FIREWALL_TRUSTED" ]] || printf 'ts\tdirection\tip\tlabel\tsource\n' >"$NEXUS_FIREWALL_TRUSTED"
  chmod 640 "$NEXUS_FIREWALL_TRUSTED" 2>/dev/null || true
  chown root:nexus "$NEXUS_FIREWALL_TRUSTED" 2>/dev/null || true
}

nexus_firewall_trust_memory_paths() {
  local root="${HOSTESS7_ROOT:-$(sg_paths_hostess7_root 2>/dev/null)}"
  printf '%s\n' \
    "${root}/cache/fieldstorage/brain/security/${NEXUS_TRUST_MEMORY_FILE}" \
    "${HOSTESS7_TEAM_FIELD}/brain/security/${NEXUS_TRUST_MEMORY_FILE}"
}

nexus_firewall_trust_is_ipv4() {
  [[ "${1:-}" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]
}

nexus_firewall_trust_normalize_direction() {
  case "${1:-both}" in
    in|out|both) printf '%s' "$1" ;;
    *) printf 'both' ;;
  esac
}

nexus_firewall_is_trusted() {
  local ip="${1:-}" direction="${2:-both}"
  [[ -n "$ip" ]] || return 1
  nexus_firewall_trust_init
  direction="$(nexus_firewall_trust_normalize_direction "$direction")"
  if [[ "$direction" == "both" ]]; then
    awk -F'\t' -v ip="$ip" '
      NR > 1 && $3 == ip && ($2 == "in" || $2 == "out" || $2 == "both") { found = 1 }
      END { exit(found ? 0 : 1) }
    ' "$NEXUS_FIREWALL_TRUSTED" 2>/dev/null
    return $?
  fi
  awk -F'\t' -v ip="$ip" -v dir="$direction" '
    NR > 1 && $3 == ip && ($2 == dir || $2 == "both") { found = 1 }
    END { exit(found ? 0 : 1) }
    ' "$NEXUS_FIREWALL_TRUSTED" 2>/dev/null
}

nexus_firewall_trust_hostess_record() {
  local ip="$1" direction="$2" label="$3" source="${4:-nexus-panel}"
  local ts path dir
  ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date)"
  local entry
  entry="$(
    TS="$ts" IP="$ip" DIR="$direction" LABEL="${label:-}" SRC="$source" pythong -c '
import json, os
print(json.dumps({
    "kind": "nexus_trust",
    "ts": os.environ["TS"],
    "ip": os.environ["IP"],
    "direction": os.environ["DIR"],
    "label": os.environ["LABEL"],
    "source": os.environ["SRC"],
    "permanent": True,
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
  done < <(nexus_firewall_trust_memory_paths)
}

nexus_firewall_trust_sync_to_memory() {
  local ts direction ip label source
  nexus_firewall_trust_init
  while IFS=$'\t' read -r ts direction ip label source; do
    [[ -n "$ip" ]] || continue
    nexus_firewall_trust_is_ipv4 "$ip" || continue
    nexus_firewall_trust_hostess_record "$ip" "$direction" "${label:-}" "${source:-nexus-sync}"
  done < <(tail -n +2 "$NEXUS_FIREWALL_TRUSTED" 2>/dev/null)
}

nexus_firewall_trust_sync_from_memory() {
  local path line ip direction label ts source
  nexus_firewall_trust_init
  while IFS= read -r path; do
    [[ -f "$path" ]] || continue
    while IFS= read -r line; do
      [[ -n "$line" ]] || continue
      read -r ip direction label ts source < <(
        pythong -c '
import json, sys
try:
    o = json.loads(sys.stdin.read())
except Exception:
    sys.exit(0)
if o.get("kind") != "nexus_trust" or o.get("revoked"):
    sys.exit(0)
ip = o.get("ip", "")
direction = o.get("direction", "both") or "both"
label = o.get("label", "") or ""
ts = o.get("ts", "") or ""
source = o.get("source", "hostess7-memory") or "hostess7-memory"
print(ip, direction, label, ts, source)
' <<<"$line" 2>/dev/null
      )
      [[ -n "$ip" ]] || continue
      nexus_firewall_trust_is_ipv4 "$ip" || continue
      nexus_firewall_is_trusted "$ip" "$direction" && continue
      direction="$(nexus_firewall_trust_normalize_direction "$direction")"
      [[ -n "$ts" ]] || ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date)"
      printf '%s\t%s\t%s\t%s\t%s\n' "$ts" "$direction" "$ip" "${label:-}" "${source:-hostess7-memory}" \
        >>"$NEXUS_FIREWALL_TRUSTED"
    done <"$path"
  done < <(nexus_firewall_trust_memory_paths)
}

nexus_firewall_trust_apply_nft() {
  [[ "${NEXUS_FIREWALL:-1}" == "1" ]] || return 0
  declare -f nexus_firewall_available >/dev/null 2>&1 || return 0
  nexus_firewall_available || return 0
  local ip direction
  while IFS=$'\t' read -r _ direction ip _ _; do
    [[ -n "$ip" ]] || continue
    nexus_firewall_trust_is_ipv4 "$ip" || continue
    case "$direction" in
      in|both)
        nft add element inet "${NEXUS_FIREWALL_TABLE}" trusted_in "{ ${ip} }" 2>/dev/null || true
        ;;
    esac
    case "$direction" in
      out|both)
        nft add element inet "${NEXUS_FIREWALL_TABLE}" trusted_out "{ ${ip} }" 2>/dev/null || true
        ;;
    esac
  done < <(tail -n +2 "$NEXUS_FIREWALL_TRUSTED" 2>/dev/null)
}

nexus_firewall_trust_reload() {
  nexus_firewall_trust_init
  nexus_firewall_trust_sync_to_memory
  nexus_firewall_trust_apply_nft
}

nexus_firewall_authorize_ip() {
  local ip="${1:-}" direction="${2:-out}" label="${3:-}" source="${4:-nexus-panel}"
  [[ -n "$ip" ]] || return 1
  nexus_firewall_trust_is_ipv4 "$ip" || return 1
  direction="$(nexus_firewall_trust_normalize_direction "$direction")"

  if declare -f nexus_firewall_is_sacred_ip >/dev/null 2>&1 && nexus_firewall_is_sacred_ip "$ip"; then
    nexus_log "INFO" "firewall-trust" "AUTHORIZE sacred ip=${ip} (always allowed)"
    return 0
  fi

  nexus_firewall_trust_init
  if nexus_firewall_is_trusted "$ip" "$direction"; then
    nexus_log "INFO" "firewall-trust" "AUTHORIZE already trusted ip=${ip} dir=${direction}"
    return 0
  fi

  local ts
  ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date)"
  printf '%s\t%s\t%s\t%s\t%s\n' "$ts" "$direction" "$ip" "${label:-}" "$source" >>"$NEXUS_FIREWALL_TRUSTED"

  if declare -f nexus_firewall_unblock_ip >/dev/null 2>&1; then
    case "$direction" in
      in) nexus_firewall_unblock_ip in "$ip" ;;
      out) nexus_firewall_unblock_ip out "$ip" ;;
      both)
        nexus_firewall_unblock_ip in "$ip"
        nexus_firewall_unblock_ip out "$ip"
        ;;
    esac
  fi

  nexus_firewall_trust_apply_nft
  nexus_firewall_trust_hostess_record "$ip" "$direction" "${label:-}" "$source"
  nexus_log "ALERT" "firewall-trust" "AUTHORIZE_PERMANENT ip=${ip} dir=${direction} label=${label:-—}"
  return 0
}

nexus_firewall_revoke_trust() {
  local ip="${1:-}" direction="${2:-both}"
  [[ -n "$ip" ]] || return 1
  direction="$(nexus_firewall_trust_normalize_direction "$direction")"
  nexus_firewall_trust_init
  awk -F'\t' -v ip="$ip" -v dir="$direction" '
    NR == 1 { print; next }
    $3 == ip && ($2 == dir || $2 == "both" || dir == "both") { next }
    { print }
  ' "$NEXUS_FIREWALL_TRUSTED" >"${NEXUS_FIREWALL_TRUSTED}.tmp" 2>/dev/null \
    && mv -f "${NEXUS_FIREWALL_TRUSTED}.tmp" "$NEXUS_FIREWALL_TRUSTED"

  if declare -f nexus_firewall_available >/dev/null 2>&1 && nexus_firewall_available; then
    case "$direction" in
      in|both) nft delete element inet "${NEXUS_FIREWALL_TABLE}" trusted_in "{ ${ip} }" 2>/dev/null || true ;;
    esac
    case "$direction" in
      out|both) nft delete element inet "${NEXUS_FIREWALL_TABLE}" trusted_out "{ ${ip} }" 2>/dev/null || true ;;
    esac
  fi

  local ts entry
  ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date)"
  entry="$(
    TS="$ts" IP="$ip" DIR="$direction" pythong -c '
import json, os
print(json.dumps({
    "kind": "nexus_trust",
    "ts": os.environ["TS"],
    "ip": os.environ["IP"],
    "direction": os.environ["DIR"],
    "revoked": True,
    "source": "nexus-revoke",
}, ensure_ascii=False))
' 2>/dev/null
  )" || true
  if [[ -n "$entry" ]]; then
    local path dir
    while IFS= read -r path; do
      [[ -n "$path" ]] || continue
      dir="$(dirname "$path")"
      mkdir -p "$dir" 2>/dev/null || continue
      printf '%s\n' "$entry" >>"$path" 2>/dev/null || true
    done < <(nexus_firewall_trust_memory_paths)
  fi
  nexus_log "INFO" "firewall-trust" "REVOKE_TRUST ip=${ip} dir=${direction}"
}

nexus_firewall_trust_json() {
  nexus_firewall_trust_init
  local first=1 line ts direction ip label source esc
  printf '['
  while IFS=$'\t' read -r ts direction ip label source; do
    [[ -n "$ip" ]] || continue
    esc="$(printf '%s' "${label:-}" | sed 's/\\/\\\\/g; s/"/\\"/g')"
    [[ "$first" -eq 1 ]] || printf ','
    first=0
    printf '{"ts":"%s","direction":"%s","ip":"%s","label":"%s","source":"%s"}' \
      "$ts" "$direction" "$ip" "$esc" "${source:-}"
  done < <(tail -n +2 "$NEXUS_FIREWALL_TRUSTED" 2>/dev/null)
  printf ']'
}

nexus_firewall_trust_count() {
  nexus_firewall_trust_init
  tail -n +2 "$NEXUS_FIREWALL_TRUSTED" 2>/dev/null | wc -l | tr -d ' '
}