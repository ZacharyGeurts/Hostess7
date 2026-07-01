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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/shutdown-guard.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Shutdown guard — heartbeat, unclean-death detection, scream bloody murder, restart policy.

NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-/var/lib/nexus-shield}"
NEXUS_HEARTBEAT="${NEXUS_HEARTBEAT:-${NEXUS_STATE_DIR}/nexus.heartbeat}"
NEXUS_LAST_ALIVE="${NEXUS_LAST_ALIVE:-${NEXUS_STATE_DIR}/nexus-last-alive.json}"
NEXUS_SHUTDOWN_STATE="${NEXUS_SHUTDOWN_STATE:-${NEXUS_STATE_DIR}/shutdown.state}"
NEXUS_SHUTDOWN_INCIDENTS="${NEXUS_SHUTDOWN_INCIDENTS:-${NEXUS_STATE_DIR}/shutdown-incidents.jsonl}"
NEXUS_SHUTDOWN_CLEAN_FLAG="${NEXUS_SHUTDOWN_CLEAN_FLAG:-${NEXUS_STATE_DIR}/.shutdown-clean}"

nexus_shutdown_guard_enabled() {
  [[ "${NEXUS_SHUTDOWN_GUARD:-1}" == "1" ]]
}

nexus_shutdown_init() {
  mkdir -p "$NEXUS_STATE_DIR" 2>/dev/null || true
  touch "$NEXUS_SHUTDOWN_INCIDENTS" 2>/dev/null || true
  if [[ ! -f "$NEXUS_SHUTDOWN_STATE" && "$(id -u)" -eq 0 ]]; then
    printf 'status=running\npolicy=%s\nupdated=%s\n' \
      "${NEXUS_SHUTDOWN_DEFAULT_POLICY:-block}" "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" >"$NEXUS_SHUTDOWN_STATE"
  fi
  chmod 640 "$NEXUS_HEARTBEAT" "$NEXUS_LAST_ALIVE" "$NEXUS_SHUTDOWN_STATE" \
    "$NEXUS_SHUTDOWN_INCIDENTS" 2>/dev/null || true
  chown root:nexus "$NEXUS_HEARTBEAT" "$NEXUS_LAST_ALIVE" "$NEXUS_SHUTDOWN_STATE" \
    "$NEXUS_SHUTDOWN_INCIDENTS" 2>/dev/null || true
}

nexus_shutdown_mark_clean() {
  nexus_shutdown_init
  printf 'clean=1\nts=%s\npid=%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$$" >"$NEXUS_SHUTDOWN_CLEAN_FLAG"
  printf 'status=clean_stop\nts=%s\npid=%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$$" >"$NEXUS_SHUTDOWN_STATE"
}

nexus_shutdown_journal_hint() {
  journalctl -u nexus-genius.service -n 30 --no-pager 2>/dev/null | tail -15
}

nexus_shutdown_analyze() {
  local forensics="${1:-"{}"}"
  local who="${2:-}"
  local journal="${3:-}"
  local signal="${4:-}"
  local tmp keep=1 script
  NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-/var/lib/nexus-shield}"
  NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-/usr/local/lib/nexus-shield}"
  script="${NEXUS_INSTALL_ROOT}/lib/shutdown-analyze.py"
  if [[ -f "$forensics" ]]; then
    tmp="$forensics"
    keep=0
  else
    tmp="$(mktemp "${NEXUS_STATE_DIR}/sd-analyze.XXXXXX")"
    printf '%s' "$forensics" >"$tmp"
  fi
  pythong "$script" "$tmp" "$who" "$journal" "$signal" 2>/dev/null || printf '{}'
  [[ "$keep" -eq 1 ]] && rm -f "$tmp" 2>/dev/null || true
}

nexus_shutdown_merge_forensics() {
  local raw="${1:-"{}"}"
  local who="${2:-}"
  local journal="${3:-}"
  local signal="${4:-}"
  local analysis tmp_raw tmp_analysis keep=1
  NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-/var/lib/nexus-shield}"
  if [[ -f "$raw" ]]; then
    tmp_raw="$raw"
    keep=0
  else
    tmp_raw="$(mktemp "${NEXUS_STATE_DIR}/sd-merge.XXXXXX")"
    printf '%s' "$raw" >"$tmp_raw"
  fi
  analysis="$(nexus_shutdown_analyze "$tmp_raw" "$who" "$journal" "$signal")"
  tmp_analysis="$(mktemp "${NEXUS_STATE_DIR}/sd-merge.XXXXXX")"
  printf '%s' "$analysis" >"$tmp_analysis"
  SD_RAW_FILE="$tmp_raw" SD_ANALYSIS_FILE="$tmp_analysis" pythong -c '
import json, os
from pathlib import Path
fore = {}
analysis = {}
try:
    fore = json.loads(Path(os.environ["SD_RAW_FILE"]).read_text())
except (json.JSONDecodeError, KeyError, OSError):
    pass
try:
    analysis = json.loads(Path(os.environ["SD_ANALYSIS_FILE"]).read_text())
except (json.JSONDecodeError, KeyError, OSError):
    pass
fore["analysis"] = analysis
fore["primary_ip"] = analysis.get("primary_ip", "")
fore["suspect_ips"] = analysis.get("suspect_ips", [])
fore["local_wan_ip"] = analysis.get("local_wan_ip", "") or fore.get("local_wan_ip", "")
fore["killer"] = analysis.get("killer", {})
fore["verdict"] = analysis.get("verdict", "")
fore["confidence"] = analysis.get("confidence", "")
print(json.dumps(fore))
' 2>/dev/null || printf '%s' "$raw"
  [[ "$keep" -eq 1 ]] && rm -f "$tmp_raw" 2>/dev/null || true
  rm -f "$tmp_analysis" 2>/dev/null || true
}

nexus_shutdown_write_incident() {
  local id="$1" ts="$2" signal="$3" who="$4" enriched="$5" journal_hint="$6"
  local tmp_fore tmp_journal
  tmp_fore="$(mktemp "${NEXUS_STATE_DIR}/sd-inc.XXXXXX")"
  tmp_journal="$(mktemp "${NEXUS_STATE_DIR}/sd-inc.XXXXXX")"
  printf '%s' "$enriched" >"$tmp_fore"
  printf '%s' "$journal_hint" >"$tmp_journal"
  SID="$id" STS="$ts" SSIG="$signal" SWHO="$who" \
    SD_FORE_FILE="$tmp_fore" SD_JOURNAL_FILE="$tmp_journal" pythong -c '
import json, os
from pathlib import Path
fore = {}
try:
    fore = json.loads(Path(os.environ["SD_FORE_FILE"]).read_text())
except (json.JSONDecodeError, KeyError, OSError):
    pass
journal = ""
try:
    journal = Path(os.environ["SD_JOURNAL_FILE"]).read_text()
except (KeyError, OSError):
    pass
doc = {
    "id": os.environ["SID"],
    "ts": os.environ["STS"],
    "vector": "SHUTDOWN_ATTACK",
    "severity": "critical",
    "signal": os.environ["SSIG"],
    "who": os.environ["SWHO"],
    "message": "BLOODY MURDER — NEXUS-Shield was shut down unclean. We need to know what hit us.",
    "recommend_policy": "block",
    "journal_hint": journal,
    "acknowledged": False,
    "forensics": fore,
    "analysis": fore.get("analysis", {}),
}
print(json.dumps(doc))
' >>"$NEXUS_SHUTDOWN_INCIDENTS" 2>/dev/null || true
  rm -f "$tmp_fore" "$tmp_journal" 2>/dev/null || true
}

nexus_shutdown_who_killed() {
  local ppid comm exe user hint=""
  ppid="$(ps -o ppid= -p $$ 2>/dev/null | tr -d ' ')"
  if [[ -n "$ppid" && "$ppid" != "1" ]]; then
    comm="$(ps -o comm= -p "$ppid" 2>/dev/null | tr -d ' ')"
    exe="$(readlink -f "/proc/${ppid}/exe" 2>/dev/null || echo unknown)"
    user="$(stat -c '%U' "/proc/${ppid}" 2>/dev/null || echo unknown)"
    hint="ppid=${ppid} comm=${comm} user=${user} exe=${exe}"
  fi
  if command -v journalctl >/dev/null 2>&1; then
    hint="${hint} journal=$(journalctl -u nexus-genius -n 5 --no-pager 2>/dev/null | tr '\n' ' ' | head -c 400)"
  fi
  printf '%s' "$hint"
}

nexus_shutdown_record_death() {
  local signal="${1:-UNKNOWN}"
  [[ -f "$NEXUS_SHUTDOWN_CLEAN_FLAG" ]] && return 0
  nexus_shutdown_init
  local ts who forensic id
  ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  who="$(nexus_shutdown_who_killed)"
  local journal_hint forensic enriched
  journal_hint="$(nexus_shutdown_journal_hint | head -c 1200)"
  enriched="$(nexus_shutdown_merge_forensics "$NEXUS_LAST_ALIVE" "$who" "$journal_hint" "$signal")"
  id="sd-$(date +%s)-$(printf '%s' "$signal" | md5sum 2>/dev/null | cut -c1-8)"

  nexus_shutdown_write_incident "$id" "$ts" "$signal" "$who" "$enriched" "$journal_hint"

  printf 'status=KILLED\nsignal=%s\nts=%s\nwho=%s\nincident=%s\n' "$signal" "$ts" "$who" "$id" >"$NEXUS_SHUTDOWN_STATE"
  nexus_alert "shutdown-guard" "BLOODY_MURDER signal=${signal} who=${who} incident=${id}"
  if declare -f nexus_paranoia_on_threat >/dev/null 2>&1; then
    nexus_paranoia_on_threat "SHUTDOWN_ATTACK" critical "signal=${signal} who=${who} incident=${id}"
  fi
}

nexus_shutdown_trap_handler() {
  local sig="$1"
  nexus_shutdown_record_death "$sig"
  exit 0
}

nexus_shutdown_install_traps() {
  nexus_shutdown_guard_enabled || return 0
  trap 'nexus_shutdown_trap_handler SIGTERM' TERM
  trap 'nexus_shutdown_trap_handler SIGINT' INT
  trap 'nexus_shutdown_trap_handler SIGHUP' HUP
}

nexus_shutdown_heartbeat() {
  nexus_shutdown_guard_enabled || return 0
  nexus_shutdown_init
  local ts conn
  ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  conn="$(nexus_packet_snapshot_connections 2>/dev/null | head -n 60)"
  printf 'pid=%s\nts=%s\n' "$$" "$ts" >"$NEXUS_HEARTBEAT"

  local arp_blob proc_blob
  arp_blob="$(nexus_packet_snapshot_arp 2>/dev/null | head -n 30)"
  proc_blob="$(ps -eo pid,user,comm,args --sort=-%cpu 2>/dev/null | head -n 20)"
  local_wan="$(ip -4 route get 1.1.1.1 2>/dev/null | awk '/src/ {print $7; exit}')"
  CONN_BLOB="$conn" ARP_BLOB="$arp_blob" PROC_BLOB="$proc_blob" HB_WAN="${local_wan:-}" \
    HB_TS="$ts" HB_PID="$$" pythong -c '
import json, os
from datetime import datetime, timezone
def lines(key):
    return [x for x in os.environ.get(key, "").splitlines() if x.strip()]
print(json.dumps({
    "pid": int(os.environ.get("HB_PID", "0") or 0),
    "ts": os.environ.get("HB_TS", ""),
    "hostname": __import__("socket").gethostname(),
    "local_wan_ip": os.environ.get("HB_WAN", ""),
    "connections": lines("CONN_BLOB"),
    "arp": lines("ARP_BLOB"),
    "processes": lines("PROC_BLOB"),
    "recorded": datetime.now(timezone.utc).isoformat(),
}))
' >"${NEXUS_LAST_ALIVE}.tmp" 2>/dev/null && mv -f "${NEXUS_LAST_ALIVE}.tmp" "$NEXUS_LAST_ALIVE"

  rm -f "$NEXUS_SHUTDOWN_CLEAN_FLAG" 2>/dev/null || true
  if grep -q '^status=KILLED' "$NEXUS_SHUTDOWN_STATE" 2>/dev/null; then
    printf 'status=running\nrecovered_ts=%s\n' "$ts" >>"$NEXUS_SHUTDOWN_STATE"
  else
    printf 'status=running\nupdated=%s\npid=%s\n' "$ts" "$$" >"$NEXUS_SHUTDOWN_STATE"
  fi
}

nexus_shutdown_startup_check() {
  nexus_shutdown_guard_enabled || return 0
  nexus_shutdown_init
  [[ -f "$NEXUS_SHUTDOWN_CLEAN_FLAG" ]] && rm -f "$NEXUS_SHUTDOWN_CLEAN_FLAG" && return 0

  local old_pid="" old_ts="" alive=0
  if [[ -f "$NEXUS_HEARTBEAT" ]]; then
    old_pid="$(grep '^pid=' "$NEXUS_HEARTBEAT" 2>/dev/null | cut -d= -f2)"
    old_ts="$(grep '^ts=' "$NEXUS_HEARTBEAT" 2>/dev/null | cut -d= -f2)"
    if [[ -n "$old_pid" && "$old_pid" =~ ^[0-9]+$ ]] && kill -0 "$old_pid" 2>/dev/null; then
      alive=1
    fi
  fi

  if [[ "$alive" -eq 0 && -f "$NEXUS_HEARTBEAT" ]]; then
    local ts who forensic id last journal_hint
    journal_hint="$(nexus_shutdown_journal_hint | head -c 1200)"
    # Systemd stop/restart during maintenance — not an external attack
    if grep -qE 'Stopping nexus-genius|Stopped nexus-genius' <<<"$journal_hint" 2>/dev/null; then
      nexus_log "INFO" "shutdown-guard" "startup_check: systemd maintenance restart prior_pid=${old_pid}"
      rm -f "$NEXUS_HEARTBEAT" 2>/dev/null || true
      printf 'status=running\nmaintenance_restart=1\nrecovered_ts=%s\npid=%s\n' \
        "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$$" >"$NEXUS_SHUTDOWN_STATE"
      return 0
    fi
    if grep -q '^status=clean_install' "$NEXUS_SHUTDOWN_STATE" 2>/dev/null \
      || grep -q '^status=clean_stop' "$NEXUS_SHUTDOWN_STATE" 2>/dev/null; then
      rm -f "$NEXUS_HEARTBEAT" 2>/dev/null || true
      return 0
    fi
    ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    who="prior_pid=${old_pid:-unknown} last_ts=${old_ts:-unknown} startup_check"
    local enriched
    enriched="$(nexus_shutdown_merge_forensics "$NEXUS_LAST_ALIVE" "$who" "$journal_hint" "UNCLEAN_RESTART")"
    id="sd-startup-$(date +%s)"
    nexus_shutdown_write_incident "$id" "$ts" "UNCLEAN_RESTART" "$who" "$enriched" "$journal_hint"
    printf 'status=KILLED\nsignal=UNCLEAN_RESTART\nts=%s\nwho=%s\nincident=%s\n' "$ts" "$who" "$id" >"$NEXUS_SHUTDOWN_STATE"
    nexus_alert "shutdown-guard" "BLOODY_MURDER UNCLEAN_RESTART prior_pid=${old_pid} last_ts=${old_ts}"
    if declare -f nexus_paranoia_on_threat >/dev/null 2>&1; then
      nexus_paranoia_on_threat "SHUTDOWN_ATTACK" critical "UNCLEAN_RESTART prior_pid=${old_pid}"
    fi
  fi
}

nexus_shutdown_recent_json() {
  local limit="${1:-10}"
  SD_INCIDENTS="$NEXUS_SHUTDOWN_INCIDENTS" SD_LIMIT="$limit" pythong <<'PYEOF' 2>/dev/null || printf '[]'
import json, os, re, subprocess
from collections import Counter
from pathlib import Path

PRIVATE4 = re.compile(r"^(127\.|10\.|192\.168\.|169\.254\.|172\.(1[6-9]|2[0-9]|3[0-1])\.)")

def is_private(ip):
    if not ip or ip in ("*", "0.0.0.0", "::1"):
        return True
    if ":" in ip:
        return ip.startswith("fe80:") or ip.startswith("fd") or ip == "::1"
    return bool(PRIVATE4.match(ip))

def parse_endpoint(field):
    field = (field or "").strip()
    if not field:
        return "", ""
    if field.startswith("["):
        m = re.match(r"\[([^\]]+)\]:(\d+)", field)
        return (m.group(1), m.group(2)) if m else ("", "")
    if ":" in field:
        host, _, port = field.rpartition(":")
        if "%" in host:
            host = host.split("%", 1)[0]
        return host, port
    if "%" in field:
        field = field.split("%", 1)[0]
    return field, ""

def parse_conn(line):
    parts = line.split()
    if len(parts) < 5:
        return None
    proto, state = parts[0], parts[1]
    local, remote = parts[4], parts[5] if len(parts) > 5 else ""
    proc = ""
    m = re.search(r'users:\(\(\"([^\"]+)\"', line)
    if m:
        proc = m.group(1)
    else:
        m = re.search(r"pid=(\d+)", line)
        if m:
            proc = "pid=" + m.group(1)
    lip, lport = parse_endpoint(local)
    rip, rport = parse_endpoint(remote)
    return {"proto": proto, "state": state, "local_ip": lip, "local_port": lport,
            "remote_ip": rip, "remote_port": rport, "proc": proc}

def analyze(fore, who, journal, signal):
    peers = {}
    listeners = []
    local_ips = Counter()
    local_v4 = Counter()
    local_v6 = Counter()
    for raw in fore.get("connections", []):
        row = parse_conn(raw)
        if not row:
            continue
        lip = row["local_ip"]
        if lip and not is_private(lip):
            local_ips[lip] += 1
            (local_v6 if ":" in lip else local_v4)[lip] += 1
        if row["state"] == "LISTEN":
            listeners.append({"bind": row["local_ip"] or "*", "port": row["local_port"], "proc": row["proc"]})
            continue
        if row["state"] not in ("ESTAB", "ESTABLISHED"):
            continue
        rip, rport = row["remote_ip"], row["remote_port"]
        if not rip or is_private(rip):
            continue
        ent = peers.setdefault(rip, {"ip": rip, "ports": set(), "count": 0, "procs": set()})
        ent["count"] += 1
        if rport:
            ent["ports"].add(rport)
        if row["proc"]:
            ent["procs"].add(row["proc"])
    ranked = []
    for ip, ent in peers.items():
        ports = sorted(ent["ports"], key=lambda x: int(x) if x.isdigit() else 0)
        procs = sorted(ent["procs"])
        score = ent["count"] * 2 + (5 if len(ports) > 3 else 0)
        ranked.append({"ip": ip, "score": score, "connections": ent["count"], "ports": ports[:8], "procs": procs[:6]})
    ranked.sort(key=lambda x: (-x["score"], -x["connections"], x["ip"]))
    killer = {"signal": signal or "", "source": "", "detail": ""}
    jm = re.search(r"Killing process ([0-9]+) \(([^)]+)\) with signal (\w+)", journal)
    if jm:
        killer.update({"source": "systemd", "pid": jm.group(1), "process": jm.group(2), "signal": jm.group(3), "detail": jm.group(0)})
    elif "SIGKILL" in journal or "status=9/KILL" in journal:
        killer.update({"source": "journal", "signal": "SIGKILL", "detail": "systemd forced SIGKILL"})
    local_wan_ip = fore.get("local_wan_ip") or (local_v4.most_common(1)[0][0] if local_v4 else "")
    local_ipv6 = local_v6.most_common(1)[0][0] if local_v6 else ""
    gateway_ip = ""
    for arp_line in fore.get("arp", []):
        gm = re.search(r"^([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)\s", arp_line)
        if gm:
            gateway_ip = gm.group(1)
            break
    primary = ranked[0]["ip"] if ranked else ""
    primary_v4 = next((r["ip"] for r in ranked if "." in r["ip"]), primary)
    verdict = []
    if local_wan_ip:
        verdict.append("This machine (WAN): " + local_wan_ip)
    if killer.get("source"):
        verdict.append("Killer: " + killer["source"] + " / " + killer.get("signal", "?"))
    if primary_v4:
        verdict.append("Top remote peer: " + primary_v4)
    elif primary:
        verdict.append("Top remote peer: " + primary)
    else:
        verdict.append("No public remote peer — likely local kill")
    return {
        "primary_ip": primary_v4 or primary,
        "suspect_ips": [r["ip"] for r in ranked[:12]],
        "egress_peers": ranked[:12],
        "listeners": listeners[:10],
        "local_ip": local_wan_ip,
        "local_wan_ip": local_wan_ip,
        "local_ipv6": local_ipv6,
        "local_ips": [k for k, _ in local_ips.most_common(4)],
        "gateway_ip": gateway_ip,
        "killer": killer,
        "confidence": "high" if primary else "low",
        "verdict": ". ".join(verdict),
    }

p = Path(os.environ.get("SD_INCIDENTS", ""))
rows = []
if p.is_file():
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            doc = json.loads(line)
        except json.JSONDecodeError:
            continue
        fore = doc.get("forensics") or {}
        analysis = fore.get("analysis") or {}
        if not analysis.get("local_wan_ip"):
            analysis = analyze(fore, doc.get("who", ""), doc.get("journal_hint", ""), doc.get("signal", ""))
            fore["analysis"] = analysis
            fore["primary_ip"] = analysis.get("primary_ip", "")
            fore["suspect_ips"] = analysis.get("suspect_ips", [])
            fore["local_wan_ip"] = analysis.get("local_wan_ip", "")
            fore["killer"] = analysis.get("killer", {})
            fore["verdict"] = analysis.get("verdict", "")
            doc["forensics"] = fore
            doc["analysis"] = analysis
        rows.append(doc)
print(json.dumps(rows[-int(os.environ.get("SD_LIMIT", "10")):]))
PYEOF
}

nexus_shutdown_status_json() {
  nexus_shutdown_init
  local status signal who incident killed
  status="$(grep '^status=' "$NEXUS_SHUTDOWN_STATE" 2>/dev/null | tail -1 | cut -d= -f2)"
  signal="$(grep '^signal=' "$NEXUS_SHUTDOWN_STATE" 2>/dev/null | tail -1 | cut -d= -f2)"
  who="$(grep '^who=' "$NEXUS_SHUTDOWN_STATE" 2>/dev/null | tail -1 | cut -d= -f2-)"
  incident="$(grep '^incident=' "$NEXUS_SHUTDOWN_STATE" 2>/dev/null | tail -1 | cut -d= -f2)"
  killed="false"
  [[ "$status" == "KILLED" ]] && killed="true"
  printf '{"killed":%s,"status":"%s","signal":"%s","who":"%s","incident":"%s","recommend_policy":"block","incidents":' \
    "$killed" "${status:-running}" "${signal:-}" "$(printf '%s' "$who" | sed 's/"/\\"/g')" "${incident:-}"
  nexus_shutdown_recent_json 5
  printf '}'
}

nexus_shutdown_restart() {
  local policy="${1:-block}" offender="${2:-}"
  nexus_shutdown_mark_clean
  # shellcheck source=/dev/null
  [[ -f "${NEXUS_INSTALL_ROOT}/lib/paranoia-mode.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/paranoia-mode.sh"
  # shellcheck source=/dev/null
  [[ -f "${NEXUS_INSTALL_ROOT}/lib/firewall-sentinel.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/firewall-sentinel.sh"

  case "$policy" in
    block|blocked|1|true|on)
      if declare -f nexus_paranoia_set_block >/dev/null 2>&1; then
        nexus_paranoia_set_block 1
      fi
      if [[ -n "$offender" && "$offender" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        if declare -f nexus_firewall_is_sacred_ip >/dev/null 2>&1 && nexus_firewall_is_sacred_ip "$offender"; then
          nexus_log "WARN" "shutdown-guard" "BLOCK_REFUSED sacred offender=${offender}"
        else
          nexus_firewall_block_ip out "$offender" "${NEXUS_FIREWALL_BLOCK_DURATION:-86400}" "SHUTDOWN_ATTACK" 2>/dev/null || true
        fi
      fi
      printf 'policy=block\n' >>"$NEXUS_SHUTDOWN_STATE"
      ;;
    *)
      if declare -f nexus_paranoia_set_block >/dev/null 2>&1; then
        nexus_paranoia_set_block 0
      fi
      printf 'policy=permissive\n' >>"$NEXUS_SHUTDOWN_STATE"
      ;;
  esac

  nexus_log "ALERT" "shutdown-guard" "RESTART policy=${policy} offender=${offender:-none}"
  if command -v systemctl >/dev/null 2>&1; then
    systemctl reset-failed nexus-genius.service 2>/dev/null || true
    if systemctl restart nexus-genius.service 2>/dev/null; then
      return 0
    fi
    systemctl start nexus-genius.service 2>/dev/null && return 0
  fi
  return 1
}

nexus_shutdown_ack() {
  local id="${1:-}"
  [[ -n "$id" ]] || return 1
  local tmp="${NEXUS_SHUTDOWN_INCIDENTS}.tmp"
  pythong -c "
import json, sys
id=sys.argv[1]
for line in open(sys.argv[2]):
    line=line.strip()
    if not line: continue
    d=json.loads(line)
    if d.get('id')==id:
        d['acknowledged']=True
    print(json.dumps(d))
" "$id" "$NEXUS_SHUTDOWN_INCIDENTS" >"$tmp" 2>/dev/null && mv "$tmp" "$NEXUS_SHUTDOWN_INCIDENTS"
  printf 'status=acknowledged\nincident=%s\n' "$id" >>"$NEXUS_SHUTDOWN_STATE"
  return 0
}