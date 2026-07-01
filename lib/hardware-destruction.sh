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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/hardware-destruction.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# NEXUS Hardware Destruction — full endpoint crush at 100% strike certainty.
# Tears down live sessions, kills hostile monitor-backed processes, isolates LAN
# neighbors, and permanently blocks all wire paths. Runs only after friendly-guard pass.

NEXUS_HW_DESTROY_LOG="${NEXUS_HW_DESTROY_LOG:-${NEXUS_STATE_DIR}/hardware-destroy-log.jsonl}"

nexus_hardware_destroy_init() {
  mkdir -p "$(dirname "$NEXUS_HW_DESTROY_LOG")" 2>/dev/null || true
  touch "$NEXUS_HW_DESTROY_LOG" 2>/dev/null || true
  chmod 640 "$NEXUS_HW_DESTROY_LOG" 2>/dev/null || true
}

nexus_hardware_destroy_is_private_ip() {
  local ip="${1:-}"
  [[ "$ip" =~ ^10\. ]] && return 0
  [[ "$ip" =~ ^192\.168\. ]] && return 0
  [[ "$ip" =~ ^172\.(1[6-9]|2[0-9]|3[0-1])\. ]] && return 0
  [[ "$ip" =~ ^169\.254\. ]] && return 0
  return 1
}

nexus_hardware_destroy_record() {
  local ip="$1" manifest="$2"
  nexus_hardware_destroy_init
  local ts entry
  ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date)"
  entry="$(
    TS="$ts" IP="$ip" MANIFEST="$manifest" pythong -c '
import json, os
raw = os.environ.get("MANIFEST", "") or "{}"
try:
    manifest = json.loads(raw)
except Exception:
    manifest = {"note": raw[:500]}
print(json.dumps({
    "kind": "hardware_destroy",
    "ts": os.environ["TS"],
    "ip": os.environ["IP"],
    "action": "HARDWARE_DESTROY",
    "certainty": 1.0,
    "manifest": manifest,
}, ensure_ascii=False))
' 2>/dev/null
  )" || return 0
  [[ -n "$entry" ]] || return 0
  printf '%s\n' "$entry" >>"$NEXUS_HW_DESTROY_LOG" 2>/dev/null || true
}

nexus_hardware_destroy_teardown_connections() {
  local ip="${1:-}"
  [[ -n "$ip" ]] || return 0
  local count=0 line

  if command -v ss >/dev/null 2>&1; then
    while IFS= read -r line; do
      [[ -n "$line" ]] || continue
      ss -K dst "$ip" dport = "$line" 2>/dev/null && count=$((count + 1)) || true
    done < <(ss -Htan "dst ${ip}" 2>/dev/null | awk '{print $4}' | sed 's/.*://' | sort -u)
    while IFS= read -r line; do
      [[ -n "$line" ]] || continue
      ss -K src "$ip" sport = "$line" 2>/dev/null && count=$((count + 1)) || true
    done < <(ss -Htan "src ${ip}" 2>/dev/null | awk '{print $4}' | sed 's/.*://' | sort -u)
  fi

  if command -v conntrack >/dev/null 2>&1; then
    conntrack -D -d "$ip" 2>/dev/null && count=$((count + 1)) || true
    conntrack -D -s "$ip" 2>/dev/null && count=$((count + 1)) || true
  fi

  nexus_log "ALERT" "hardware-destruction" "CONN_TEARDOWN ip=${ip} actions=${count}"
  printf '%s' "$count"
}

nexus_hardware_destroy_kill_sessions() {
  local dossier="${1:-}"
  [[ -n "$dossier" ]] || { printf '0'; return 0; }

  if ! declare -f nexus_pest_kill_pid >/dev/null 2>&1; then
    [[ -f "${NEXUS_INSTALL_ROOT}/lib/pest-arsenal.sh" ]] && # shellcheck source=/dev/null
      source "${NEXUS_INSTALL_ROOT}/lib/pest-arsenal.sh"
  fi
  declare -f nexus_pest_kill_pid >/dev/null 2>&1 || { printf '0'; return 0; }

  local killed
  killed="$(
    DOSSIER_JSON="$dossier" pythong -c '
import json, os, subprocess, sys

try:
    d = json.loads(os.environ.get("DOSSIER_JSON", "") or "{}")
except Exception:
    sys.exit(0)

pids = set()
mon = d.get("monitor") if isinstance(d.get("monitor"), dict) else {}
for key in ("pid", "our_pid", "local_pid"):
    try:
        val = int(mon.get(key) or 0)
        if val > 2:
            pids.add(val)
    except (TypeError, ValueError):
        pass
for sess in d.get("monitor_sessions") or []:
    if not isinstance(sess, dict):
        continue
    for key in ("pid", "our_pid", "local_pid"):
        try:
            val = int(sess.get(key) or 0)
            if val > 2:
                pids.add(val)
        except (TypeError, ValueError):
            pass
intel = d.get("intel") if isinstance(d.get("intel"), dict) else {}
proc = str(intel.get("process") or mon.get("process") or "")
if proc and "/" in proc:
    try:
        out = subprocess.check_output(["pgrep", "-f", proc.split("/")[-1]], text=True, timeout=3)
        for line in out.splitlines():
            try:
                val = int(line.strip())
                if val > 2:
                    pids.add(val)
            except ValueError:
                pass
    except Exception:
        pass
print(" ".join(str(p) for p in sorted(pids)))
' 2>/dev/null
  )"

  local pid count=0
  for pid in $killed; do
    [[ "$pid" =~ ^[0-9]+$ ]] || continue
    if nexus_pest_kill_pid "$pid" "hardware_destroy"; then
      count=$((count + 1))
    fi
  done
  nexus_log "ALERT" "hardware-destruction" "SESSION_KILL count=${count}"
  printf '%s' "$count"
}

nexus_hardware_destroy_block_flows() {
  local ip="${1:-}" ports_blob="${2:-}"
  [[ -n "$ip" ]] || return 0
  declare -f nexus_firewall_block_flow >/dev/null 2>&1 || { printf '0'; return 0; }
  local port count=0
  for port in $ports_blob; do
    [[ "$port" =~ ^[0-9]+$ ]] || continue
    nexus_firewall_block_flow out "$ip" "$port" "${NEXUS_FIREWALL_BLOCK_FOREVER:-3153600000}" "hardware_destroy" && count=$((count + 1)) || true
    nexus_firewall_block_flow in "$ip" "$port" "${NEXUS_FIREWALL_BLOCK_FOREVER:-3153600000}" "hardware_destroy" && count=$((count + 1)) || true
  done
  printf '%s' "$count"
}

nexus_hardware_destroy_lan_isolate() {
  local ip="${1:-}" mac="${2:-}"
  [[ -n "$ip" ]] || return 0
  nexus_hardware_destroy_is_private_ip "$ip" || return 0
  local actions=0

  if command -v ip >/dev/null 2>&1; then
    while IFS= read -r line; do
      [[ -n "$line" ]] || continue
      ip neigh del "$ip" dev "$line" 2>/dev/null && actions=$((actions + 1)) || true
    done < <(ip -o link show 2>/dev/null | awk -F': ' '{print $2}' | grep -v '^lo$' || true)
  fi

  if [[ -n "$mac" ]] && command -v arp >/dev/null 2>&1; then
    arp -d "$ip" 2>/dev/null && actions=$((actions + 1)) || true
  fi

  if declare -f nexus_firewall_block_ip_forever >/dev/null 2>&1; then
    nexus_firewall_block_ip_forever in "$ip" "hardware_destroy_lan" && actions=$((actions + 1)) || true
    nexus_firewall_block_ip_forever out "$ip" "hardware_destroy_lan" && actions=$((actions + 1)) || true
  fi

  nexus_log "ALERT" "hardware-destruction" "LAN_ISOLATE ip=${ip} mac=${mac:-none} actions=${actions}"
  printf '%s' "$actions"
}

nexus_hardware_destroy_target() {
  local ip="${1:-}" dossier="${2:-}"
  [[ -n "$ip" ]] || return 1

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
    nexus_log "ALERT" "hardware-destruction" "DESTROY_REFUSED_FRIENDLY ip=${ip}"
    return 1
  fi

  local meta mac ports_blob conn_killed proc_killed flow_blocks lan_actions manifest
  meta="$(
    DOSSIER_JSON="${dossier:-"{}"}" IP="$ip" pythong -c '
import json, os
try:
    d = json.loads(os.environ.get("DOSSIER_JSON", "") or "{}")
except Exception:
    d = {}
intel = d.get("intel") if isinstance(d.get("intel"), dict) else {}
geo = d.get("geo") if isinstance(d.get("geo"), dict) else {}
mon = d.get("monitor") if isinstance(d.get("monitor"), dict) else {}
ports = set()
for raw in d.get("target_ports") or []:
    try:
        ports.add(int(raw))
    except (TypeError, ValueError):
        pass
try:
    ports.add(int(mon.get("remote_port") or 0))
except (TypeError, ValueError):
    pass
for sess in d.get("monitor_sessions") or []:
    if isinstance(sess, dict):
        try:
            ports.add(int(sess.get("remote_port") or 0))
        except (TypeError, ValueError):
            pass
c2 = {3004, 3005, 4444, 4443, 5555, 6006, 6606, 7001, 7002, 8808, 9002, 9003, 1337, 31337}
ports = sorted(p for p in ports if p > 0) or sorted(c2)
print(json.dumps({
    "mac": intel.get("mac") or d.get("mac") or "",
    "ports": ports,
    "wire_scope": (d.get("wire_point") or {}).get("scope", ""),
    "lan_device": bool((d.get("wire_point") or {}).get("lan_device")),
}, ensure_ascii=False))
' 2>/dev/null
  )" || meta='{}'

  mac="$(META_JSON="$meta" pythong -c 'import json,os; print(json.loads(os.environ.get("META_JSON","{}") or "{}").get("mac",""))' 2>/dev/null)"
  ports_blob="$(META_JSON="$meta" pythong -c 'import json,os; print(" ".join(str(p) for p in json.loads(os.environ.get("META_JSON","{}") or "{}").get("ports",[])))' 2>/dev/null)"

  conn_killed="$(nexus_hardware_destroy_teardown_connections "$ip")"
  proc_killed="$(nexus_hardware_destroy_kill_sessions "$dossier")"
  flow_blocks="$(nexus_hardware_destroy_block_flows "$ip" "$ports_blob")"
  lan_actions=0
  if nexus_hardware_destroy_is_private_ip "$ip"; then
    lan_actions="$(nexus_hardware_destroy_lan_isolate "$ip" "$mac")"
  fi

  manifest="$(
    IP="$ip" CONN="$conn_killed" PROC="$proc_killed" FLOW="$flow_blocks" LAN="$lan_actions" \
      pythong -c '
import json, os
print(json.dumps({
    "ip": os.environ["IP"],
    "action": "HARDWARE_DESTROY",
    "certainty": 1.0,
    "connections_teardown": int(os.environ.get("CONN") or 0),
    "processes_killed": int(os.environ.get("PROC") or 0),
    "flow_blocks": int(os.environ.get("FLOW") or 0),
    "lan_isolate_actions": int(os.environ.get("LAN") or 0),
}, ensure_ascii=False))
' 2>/dev/null
  )"

  nexus_hardware_destroy_record "$ip" "$manifest"
  nexus_log "ALERT" "hardware-destruction" "TARGET_DESTROYED ip=${ip} manifest=${manifest}"
  return 0
}