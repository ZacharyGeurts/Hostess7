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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/paranoia-mode.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Paranoia mode — OFF first: detect who/what, log ALL forensics, disable on approval, re-enable from log.

NEXUS_PARANOIA_STATE="${NEXUS_PARANOIA_STATE:-${NEXUS_STATE_DIR}/paranoia.state}"
NEXUS_PARANOIA_INCIDENTS="${NEXUS_PARANOIA_INCIDENTS:-${NEXUS_STATE_DIR}/paranoia-incidents.jsonl}"
NEXUS_PARANOIA_DEDUP="${NEXUS_PARANOIA_DEDUP:-${NEXUS_STATE_DIR}/paranoia-dedup.tsv}"

# Meta-vectors that must not feed correlation loops or auto-block without forensic targets.
NEXUS_PARANOIA_META_VECTORS=(C2_CORRELATION)

nexus_paranoia_enabled() {
  [[ "${NEXUS_PARANOIA_MODE:-0}" == "1" ]]
}

nexus_paranoia_blocking_enabled() {
  nexus_paranoia_enabled && [[ "${NEXUS_PARANOIA_BLOCK:-0}" == "1" ]]
}

nexus_paranoia_is_meta_vector() {
  local vector="$1" v
  for v in "${NEXUS_PARANOIA_META_VECTORS[@]}"; do
    [[ "$vector" == "$v" ]] && return 0
  done
  return 1
}

nexus_paranoia_init() {
  nexus_ensure_dirs 2>/dev/null || mkdir -p "$(dirname "$NEXUS_PARANOIA_INCIDENTS")" 2>/dev/null || true
  if [[ ! -f "$NEXUS_PARANOIA_INCIDENTS" ]]; then
    if [[ "$(id -u)" -eq 0 ]]; then
      : >"$NEXUS_PARANOIA_INCIDENTS"
    else
      touch "$NEXUS_PARANOIA_INCIDENTS" 2>/dev/null || true
    fi
  fi
  if [[ ! -f "$NEXUS_PARANOIA_DEDUP" && "$(id -u)" -eq 0 ]]; then
    printf 'ts\tvector\tdetail_hash\n' >"$NEXUS_PARANOIA_DEDUP"
  fi
  if [[ ! -f "$NEXUS_PARANOIA_STATE" && "$(id -u)" -eq 0 ]]; then
    printf 'mode=1\nblock=0\nautosanitize_override=0\nupdated=%s\n' \
      "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" >"$NEXUS_PARANOIA_STATE"
  fi
  if [[ "$(id -u)" -eq 0 ]]; then
    chmod 640 "$NEXUS_PARANOIA_INCIDENTS" "$NEXUS_PARANOIA_STATE" "$NEXUS_PARANOIA_DEDUP" 2>/dev/null || true
    chown root:nexus "$NEXUS_PARANOIA_INCIDENTS" "$NEXUS_PARANOIA_STATE" "$NEXUS_PARANOIA_DEDUP" 2>/dev/null || true
  fi
}

nexus_paranoia_read_block() {
  grep '^block=' "$NEXUS_PARANOIA_STATE" 2>/dev/null | cut -d= -f2
}

nexus_paranoia_set_block() {
  local on="${1:-0}" ts mode
  nexus_paranoia_init
  ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  mode="$(grep '^mode=' "$NEXUS_PARANOIA_STATE" 2>/dev/null | cut -d= -f2)"
  mode="${mode:-1}"
  if [[ "$on" == "1" || "$on" == "true" || "$on" == "on" ]]; then
    printf 'mode=%s\nblock=1\nautosanitize_override=0\nupdated=%s\n' "$mode" "$ts" >"${NEXUS_PARANOIA_STATE}.tmp" \
      && mv "${NEXUS_PARANOIA_STATE}.tmp" "$NEXUS_PARANOIA_STATE"
    nexus_log "INFO" "paranoia" "PARANOIA_BLOCK_ON — disable after forensic log"
  else
    printf 'mode=%s\nblock=0\nautosanitize_override=0\nupdated=%s\n' "$mode" "$ts" >"${NEXUS_PARANOIA_STATE}.tmp" \
      && mv "${NEXUS_PARANOIA_STATE}.tmp" "$NEXUS_PARANOIA_STATE"
    nexus_log "INFO" "paranoia" "PARANOIA_BLOCK_OFF — detect and log only"
  fi
}

nexus_paranoia_set_mode() {
  local on="${1:-1}" ts block
  nexus_paranoia_init
  ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  block="$(nexus_paranoia_read_block)"
  block="${block:-0}"
  if [[ "$on" == "1" || "$on" == "true" || "$on" == "on" ]]; then
    printf 'mode=1\nblock=%s\nautosanitize_override=0\nupdated=%s\n' "$block" "$ts" >"${NEXUS_PARANOIA_STATE}.tmp" \
      && mv "${NEXUS_PARANOIA_STATE}.tmp" "$NEXUS_PARANOIA_STATE"
    nexus_log "INFO" "paranoia" "PARANOIA_MODE_ON block=${block}"
  else
    printf 'mode=0\nblock=0\nautosanitize_override=0\nupdated=%s\n' "$ts" >"${NEXUS_PARANOIA_STATE}.tmp" \
      && mv "${NEXUS_PARANOIA_STATE}.tmp" "$NEXUS_PARANOIA_STATE"
    nexus_log "INFO" "paranoia" "PARANOIA_MODE_OFF"
  fi
}

nexus_paranoia_json_escape() {
  printf '%s' "$1" | pythong -c 'import json,sys; print(json.dumps(sys.stdin.read()))' 2>/dev/null \
    || printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g; s/$/\\n/' | tr -d '\n' | sed 's/\\n$//'
}

nexus_paranoia_proc_detail() {
  local pid="${1#pid=}" comm exe user
  [[ "$pid" =~ ^[0-9]+$ ]] || return 0
  [[ -d "/proc/${pid}" ]] || return 0
  comm="$(cat "/proc/${pid}/comm" 2>/dev/null | tr -d '\0')"
  exe="$(readlink -f "/proc/${pid}/exe" 2>/dev/null || echo unknown)"
  user="$(stat -c '%U' "/proc/${pid}" 2>/dev/null || echo unknown)"
  printf 'pid=%s user=%s comm=%s exe=%s' "$pid" "$user" "$comm" "$exe"
}

nexus_paranoia_infer_targets() {
  local vector="$1" detail="$2" conn ip port proc
  local -a ips procs ports
  while IFS= read -r conn; do
    [[ -n "$conn" ]] || continue
    if [[ "$conn" != *ESTAB* && "$conn" != *ESTABLISHED* ]]; then
      continue
    fi
    ip="$(awk '{print $5}' <<<"$conn" | sed 's/.*://; s/%.*//')"
    [[ -z "$ip" || "$ip" == "*" || "$ip" == "0.0.0.0" ]] && continue
    if declare -f nexus_firewall_is_private_ip >/dev/null 2>&1; then
      nexus_firewall_is_private_ip "$ip" && continue
    fi
    ips+=("$ip")
    proc="$(sed -n 's/.*users:((\"\([^\"]*\)\".*/\1/p' <<<"$conn")"
    [[ -z "$proc" ]] && proc="$(sed -n 's/.*pid=\([0-9]*\).*/\1/p' <<<"$conn")"
    [[ -n "$proc" ]] && procs+=("$proc")
  done <<<"$(nexus_packet_snapshot_connections 2>/dev/null | head -n 120)"

  ip="$(nexus_firewall_parse_ip "$detail" "dst" 2>/dev/null)"
  [[ -z "$ip" ]] && ip="$(nexus_firewall_parse_ip "$detail" "ip" 2>/dev/null)"
  [[ -z "$ip" ]] && port="$(sed -n 's/.*bind=[^:]*:\([0-9]*\).*/\1/p' <<<"$detail")"
  [[ -z "$port" ]] && port="$(sed -n 's/.*new_listener=[^:]*:\([0-9]*\).*/\1/p' <<<"$detail")"

  if [[ -z "$ip" && ${#ips[@]} -gt 0 ]]; then
    ip="${ips[0]}"
  fi

  printf 'primary_ip=%s\nprimary_port=%s\nsuspect_ips=%s\nsuspect_procs=%s\n' \
    "${ip:-}" "${port:-}" "$(printf '%s,' "${ips[@]}" | sed 's/,$//')" \
    "$(printf '%s,' "${procs[@]}" | sed 's/,$//')"
}

nexus_paranoia_gather_forensics() {
  local vector="$1" detail="$2"
  local hostname user corr mode dns targets primary_ip primary_port suspect_ips suspect_procs
  local conn_blob arp_blob proc_blob
  hostname="$(hostname -f 2>/dev/null || hostname)"
  user="$(whoami 2>/dev/null || echo unknown)"
  corr="$(nexus_threat_correlation_score 2>/dev/null || echo 0)"
  mode="$(nexus_vigil_get_mode 2>/dev/null || echo calm)"
  dns="$(nexus_packet_resolv_hash 2>/dev/null || echo none)"
  targets="$(nexus_paranoia_infer_targets "$vector" "$detail")"
  primary_ip="$(grep '^primary_ip=' <<<"$targets" | cut -d= -f2)"
  primary_port="$(grep '^primary_port=' <<<"$targets" | cut -d= -f2)"
  suspect_ips="$(grep '^suspect_ips=' <<<"$targets" | cut -d= -f2)"
  suspect_procs="$(grep '^suspect_procs=' <<<"$targets" | cut -d= -f2)"
  conn_blob="$(nexus_packet_snapshot_connections 2>/dev/null | head -n 80)"
  arp_blob="$(nexus_packet_snapshot_arp 2>/dev/null | head -n 40)"
  proc_blob="$(ps -eo pid,user,comm,args --sort=-%cpu 2>/dev/null | head -n 25)"

  CONN_BLOB="$conn_blob" ARP_BLOB="$arp_blob" PROC_BLOB="$proc_blob" \
  PARANOIA_HOST="$hostname" PARANOIA_USER="$user" PARANOIA_MODE="$mode" \
  PARANOIA_CORR="$corr" PARANOIA_DNS="$dns" PARANOIA_VECTOR="$vector" \
  PARANOIA_DETAIL="$detail" PARANOIA_PIP="$primary_ip" PARANOIA_PPORT="$primary_port" \
  PARANOIA_SIPS="$suspect_ips" PARANOIA_SPROCS="$suspect_procs" \
  pythong -c '
import json, os
def lines(key):
    raw = os.environ.get(key, "")
    return [x for x in raw.splitlines() if x.strip()]
print(json.dumps({
    "hostname": os.environ.get("PARANOIA_HOST", ""),
    "user": os.environ.get("PARANOIA_USER", ""),
    "vigil_mode": os.environ.get("PARANOIA_MODE", ""),
    "correlation_score": int(os.environ.get("PARANOIA_CORR", "0") or 0),
    "dns_hash": os.environ.get("PARANOIA_DNS", ""),
    "primary_ip": os.environ.get("PARANOIA_PIP", ""),
    "primary_port": os.environ.get("PARANOIA_PPORT", ""),
    "suspect_ips": [x for x in os.environ.get("PARANOIA_SIPS", "").split(",") if x],
    "suspect_procs": [x for x in os.environ.get("PARANOIA_SPROCS", "").split(",") if x],
    "connections": lines("CONN_BLOB"),
    "arp": lines("ARP_BLOB"),
    "processes": lines("PROC_BLOB"),
    "vector": os.environ.get("PARANOIA_VECTOR", ""),
    "detail": os.environ.get("PARANOIA_DETAIL", ""),
}))
'
}

nexus_paranoia_should_dedup() {
  local vector="$1" detail="$2" hash now cutoff
  hash="$(printf '%s|%s' "$vector" "$detail" | md5sum 2>/dev/null | cut -c1-16)"
  now="$(date +%s)"
  cutoff=$((now - 90))
  if awk -F'\t' -v h="$hash" -v c="$cutoff" '$3 == h && $1 >= c { found=1 } END { exit !found }' \
    "$NEXUS_PARANOIA_DEDUP" 2>/dev/null; then
    return 0
  fi
  printf '%s\t%s\t%s\n' "$now" "$vector" "$hash" >>"$NEXUS_PARANOIA_DEDUP"
  return 1
}

nexus_paranoia_apply_disable() {
  local id="$1" target="$2" target_type="$3" vector="$4"
  # shellcheck source=/dev/null
  [[ -f "${NEXUS_INSTALL_ROOT}/lib/firewall-sentinel.sh" ]] && \
    source "${NEXUS_INSTALL_ROOT}/lib/firewall-sentinel.sh"

  case "$target_type" in
    ip_in)  nexus_firewall_block_ip in "$target" "${NEXUS_FIREWALL_BLOCK_DURATION:-86400}" "paranoia:${vector}" ;;
    ip_out) nexus_firewall_block_ip out "$target" "${NEXUS_FIREWALL_BLOCK_DURATION:-86400}" "paranoia:${vector}" ;;
    port_in) nexus_firewall_block_port_in "$target" "${NEXUS_FIREWALL_BLOCK_DURATION:-86400}" "paranoia:${vector}" ;;
    *) return 1 ;;
  esac
  nexus_log "ALERT" "paranoia" "DISABLE id=${id} type=${target_type} target=${target} vector=${vector}"
  return 0
}

nexus_paranoia_undo_disable() {
  local id="$1" target="$2" target_type="$3"
  # shellcheck source=/dev/null
  [[ -f "${NEXUS_INSTALL_ROOT}/lib/firewall-sentinel.sh" ]] && \
    source "${NEXUS_INSTALL_ROOT}/lib/firewall-sentinel.sh"
  case "$target_type" in
    ip_in)  nexus_firewall_unblock_ip in "$target" ;;
    ip_out) nexus_firewall_unblock_ip out "$target" ;;
    port_in) nexus_firewall_unblock_port_in "$target" ;;
    *) return 1 ;;
  esac
  nexus_log "INFO" "paranoia" "REENABLE id=${id} type=${target_type} target=${target}"
  return 0
}

nexus_paranoia_pick_target() {
  local vector="$1" detail="$2" forensic="$3"
  local ip port target_type=""
  ip="$(nexus_firewall_parse_ip "$detail" "ip")"
  [[ -z "$ip" ]] && ip="$(nexus_firewall_parse_ip "$detail" "dst")"
  [[ -z "$ip" ]] && ip="$(pythong -c "
import json,sys
try:
  d=json.loads(sys.stdin.read())
  print(d.get('primary_ip','') or (d.get('suspect_ips','').split(',')[0] if d.get('suspect_ips') else ''))
except Exception:
  print('')
" <<<"$forensic" 2>/dev/null)"

  port="$(sed -n 's/.*bind=[^:]*:\([0-9]*\).*/\1/p' <<<"$detail")"
  [[ -z "$port" ]] && port="$(sed -n 's/.*new_listener=[^:]*:\([0-9]*\).*/\1/p' <<<"$detail")"
  [[ -z "$port" ]] && port="$(pythong -c "
import json,sys
try:
  d=json.loads(sys.stdin.read())
  print(d.get('primary_port',''))
except Exception:
  print('')
" <<<"$forensic" 2>/dev/null)"

  if [[ -n "$ip" ]]; then
    case "$vector" in
      ARP_SPOOF|PACKET_INJECTION|GATEWAY_SHIFT|CONN_HIJACK|MITM_LISTENER|LISTENER_SURGE|AI_ROGUE_INFRA|AI_AUTOSCAN|AI_LOLBIN_CHAIN)
        target_type="ip_in" ;;
      *)
        target_type="ip_out" ;;
    esac
    printf '%s\t%s' "$target_type" "$ip"
    return 0
  fi
  if [[ -n "$port" && "$port" =~ ^[0-9]+$ ]]; then
    printf 'port_in\t%s' "$port"
    return 0
  fi
  return 1
}

nexus_paranoia_on_threat() {
  local vector="$1" severity="$2" detail="$3"
  nexus_paranoia_enabled || return 0
  nexus_paranoia_init
  nexus_paranoia_should_dedup "$vector" "$detail" && return 0
  local trust_ip=""
  if declare -f nexus_firewall_parse_ip >/dev/null 2>&1; then
    trust_ip="$(nexus_firewall_parse_ip "$detail" "dst" 2>/dev/null)"
    [[ -z "$trust_ip" ]] && trust_ip="$(nexus_firewall_parse_ip "$detail" "ip" 2>/dev/null)"
  fi
  if [[ -n "$trust_ip" ]] && declare -f nexus_firewall_is_trusted >/dev/null 2>&1 \
    && nexus_firewall_is_trusted "$trust_ip" "both"; then
    return 0
  fi

  local id ts forensic target_line target_type target disabled block_phase
  ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  id="par-$(date +%s)-$(printf '%s' "${vector}_${detail}" | md5sum 2>/dev/null | cut -c1-8)"
  forensic="$(nexus_paranoia_gather_forensics "$vector" "$detail")"
  disabled="false"
  target=""
  target_type="none"
  block_phase="log_only"

  if nexus_paranoia_blocking_enabled; then
    if target_line="$(nexus_paranoia_pick_target "$vector" "$detail" "$forensic")"; then
      target_type="${target_line%%$'\t'*}"
      target="${target_line#*$'\t'}"
      if nexus_paranoia_apply_disable "$id" "$target" "$target_type" "$vector"; then
        disabled="true"
        block_phase="auto_disabled"
      fi
    fi
  fi

  pythong -c '
import json, os, sys
print(json.dumps({
    "id": os.environ["PID"],
    "ts": os.environ["PTS"],
    "vector": os.environ["PVEC"],
    "severity": os.environ["PSEV"],
    "detail": os.environ["PDET"],
    "disabled": os.environ["PDIS"] == "true",
    "reenabled": False,
    "block_phase": os.environ["PPHASE"],
    "block_target": os.environ.get("PTGT", ""),
    "block_type": os.environ.get("PTYPE", "none"),
    "forensics": json.loads(os.environ["PFORE"]),
}))
' PID="$id" PTS="$ts" PVEC="$vector" PSEV="$severity" PDET="$detail" PDIS="$disabled" \
   PPHASE="$block_phase" PTGT="$target" PTYPE="$target_type" PFORE="$forensic" >>"$NEXUS_PARANOIA_INCIDENTS"

  nexus_log "ALERT" "paranoia" "INCIDENT id=${id} vector=${vector} severity=${severity} phase=${block_phase} target=${target:-none} detail=${detail}"
}

nexus_paranoia_disable_incident() {
  local id="$1" line forensic vector detail target_line target_type target
  [[ -n "$id" ]] || return 1
  line="$(grep -F "\"id\":\"${id}\"" "$NEXUS_PARANOIA_INCIDENTS" 2>/dev/null | tail -1)"
  [[ -n "$line" ]] || return 1
  grep -q '"disabled":true' <<<"$line" && return 0

  forensic="$(pythong -c "
import json,sys
d=json.loads(sys.stdin.read())
print(json.dumps(d.get('forensics',{})))
" <<<"$line" 2>/dev/null)"
  vector="$(pythong -c "import json,sys; print(json.loads(sys.stdin.read()).get('vector',''))" <<<"$line" 2>/dev/null)"
  detail="$(pythong -c "import json,sys; print(json.loads(sys.stdin.read()).get('detail',''))" <<<"$line" 2>/dev/null)"

  target_line="$(nexus_paranoia_pick_target "$vector" "$detail" "$forensic")" || return 1
  target_type="${target_line%%$'\t'*}"
  target="${target_line#*$'\t'}"
  nexus_paranoia_apply_disable "$id" "$target" "$target_type" "$vector" || return 1

  local tmp="${NEXUS_PARANOIA_INCIDENTS}.tmp"
  pythong -c "
import json,sys
id=sys.argv[1]
target=sys.argv[2]
tt=sys.argv[3]
for line in open(sys.argv[4]):
    line=line.strip()
    if not line: continue
    d=json.loads(line)
    if d.get('id')==id:
        d['disabled']=True
        d['reenabled']=False
        d['block_phase']='manual_disabled'
        d['block_target']=target
        d['block_type']=tt
    print(json.dumps(d))
" "$id" "$target" "$target_type" "$NEXUS_PARANOIA_INCIDENTS" >"$tmp" 2>/dev/null \
    && mv "$tmp" "$NEXUS_PARANOIA_INCIDENTS"
  return 0
}

nexus_paranoia_reenable_incident() {
  local id="$1" line target target_type
  [[ -n "$id" ]] || return 1
  line="$(grep -F "\"id\":\"${id}\"" "$NEXUS_PARANOIA_INCIDENTS" 2>/dev/null | tail -1)"
  [[ -n "$line" ]] || return 1

  target="$(pythong -c "import json,sys; d=json.loads(sys.stdin.read()); print(d.get('block_target',''))" <<<"$line" 2>/dev/null)"
  target_type="$(pythong -c "import json,sys; d=json.loads(sys.stdin.read()); print(d.get('block_type',''))" <<<"$line" 2>/dev/null)"
  [[ -n "$target" && "$target_type" != "none" ]] || return 1
  nexus_paranoia_undo_disable "$id" "$target" "$target_type" || return 1

  local tmp="${NEXUS_PARANOIA_INCIDENTS}.tmp"
  pythong -c "
import json,sys
id=sys.argv[1]
for line in open(sys.argv[2]):
    line=line.strip()
    if not line: continue
    d=json.loads(line)
    if d.get('id')==id:
        d['disabled']=False
        d['reenabled']=True
        d['block_phase']='reenabled'
    print(json.dumps(d))
" "$id" "$NEXUS_PARANOIA_INCIDENTS" >"$tmp" 2>/dev/null \
    && mv "$tmp" "$NEXUS_PARANOIA_INCIDENTS"
  return 0
}

nexus_paranoia_recent_json() {
  local limit="${1:-20}"
  pythong -c "
import json
from pathlib import Path
p=Path('${NEXUS_PARANOIA_INCIDENTS}')
rows=[]
if p.is_file():
    for line in p.read_text().splitlines():
        line=line.strip()
        if not line: continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            pass
rows=rows[-int('${limit}'):]
print(json.dumps(rows))
" 2>/dev/null || printf '[]'
}

nexus_paranoia_status_json() {
  nexus_paranoia_init
  local mode block updated
  mode="$(grep '^mode=' "$NEXUS_PARANOIA_STATE" 2>/dev/null | cut -d= -f2)"
  block="$(nexus_paranoia_read_block)"
  updated="$(grep '^updated=' "$NEXUS_PARANOIA_STATE" 2>/dev/null | cut -d= -f2)"
  printf '{"enabled":%s,"block":%s,"updated":"%s","incidents_path":"%s"}' \
    "$( [[ "${mode:-0}" == "1" ]] && echo true || echo false )" \
    "$( [[ "${block:-0}" == "1" ]] && echo true || echo false )" \
    "${updated:-}" "$NEXUS_PARANOIA_INCIDENTS"
}

nexus_paranoia_panel_json() {
  pythong -c "
import json
from pathlib import Path
state=Path('${NEXUS_PARANOIA_STATE}')
mode=block=updated=''
if state.is_file():
    for line in state.read_text().splitlines():
        if line.startswith('mode='): mode=line.split('=',1)[1]
        if line.startswith('block='): block=line.split('=',1)[1]
        if line.startswith('updated='): updated=line.split('=',1)[1]
inc=[]
p=Path('${NEXUS_PARANOIA_INCIDENTS}')
if p.is_file():
    for line in p.read_text().splitlines():
        line=line.strip()
        if not line: continue
        try: inc.append(json.loads(line))
        except json.JSONDecodeError: pass
print(json.dumps({
    'enabled': mode=='1',
    'block': block=='1',
    'updated': updated,
    'incidents_path': '${NEXUS_PARANOIA_INCIDENTS}',
    'incidents': inc[-30:],
}, separators=(',', ':')))
" 2>/dev/null || printf '{"enabled":false,"block":false,"incidents":[]}'
}