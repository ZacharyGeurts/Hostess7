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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/nexus-stray-task-guard.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Stray task guard — prune duplicate watchdogs, kill probe/json stragglers each vigil.

nexus_stray_guard_enabled() {
  [[ "${NEXUS_STRAY_TASK_GUARD:-1}" == "1" ]]
}

nexus_stray_guard_stamp() {
  printf '%s' "${NEXUS_STATE_DIR}/nexus-stray-task-guard.stamp"
}

nexus_stray_guard_due() {
  local stamp interval now last
  stamp="$(nexus_stray_guard_stamp)"
  interval="${NEXUS_STRAY_GUARD_INTERVAL:-30}"
  now="$(date +%s)"
  last=0
  [[ -f "$stamp" ]] && last="$(cat "$stamp" 2>/dev/null || echo 0)"
  [[ $((now - last)) -ge interval ]]
}

nexus_stray_guard_mark() {
  date +%s >"$(nexus_stray_guard_stamp)" 2>/dev/null || true
}

nexus_stray_prune_tray_watchdogs() {
  [[ -f "${NEXUS_INSTALL_ROOT}/lib/panel-tray.sh" ]] || return 0
  # shellcheck source=/dev/null
  source "${NEXUS_INSTALL_ROOT}/lib/panel-tray.sh"
  declare -f nexus_panel_tray_watchdog_prune >/dev/null 2>&1 || return 0
  local keep=""
  [[ -f "${NEXUS_STATE_DIR}/panel-tray-watchdog.pid" ]] && \
    keep="$(cat "${NEXUS_STATE_DIR}/panel-tray-watchdog.pid" 2>/dev/null || true)"
  nexus_panel_tray_watchdog_prune "$keep"
  nexus_panel_tray_prune_duplicates ""
}

nexus_stray_kill_json_probes() {
  local script="${NEXUS_INSTALL_ROOT}/../scripts/kill-nexus-probe-storm.sh"
  [[ -f "$script" ]] || script="${NEXUS_INSTALL_ROOT}/scripts/kill-nexus-probe-storm.sh"
  [[ -f "$script" ]] || return 0
  bash "$script" >/dev/null 2>&1 || true
}

nexus_stray_prune_duplicate_guards() {
  python3 <<'PY' || true
import os, signal, subprocess

def prune(substr, keep=1):
    out = subprocess.check_output(["ps", "-eo", "pid=,args="], text=True)
    hits = []
    for line in out.splitlines():
        parts = line.split(None, 1)
        if len(parts) < 2:
            continue
        pid, cmd = int(parts[0]), parts[1]
        if substr in cmd and "python3 <<" not in cmd:
            hits.append(pid)
    if len(hits) <= keep:
        return
    hits.sort()
    for pid in hits[keep:]:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

for pat in (
    "queen-root-sovereign.py guard",
    "queen-field-virus.py guard",
    "field-queen-browser.py json",
):
    prune(pat, 1)
PY
}

nexus_stray_kill_hung_pythong() {
  local max_age="${NEXUS_STRAY_PYTHONG_MAX_AGE:-90}"
  python3 <<PY || true
import os, signal, subprocess
max_age = int("${max_age}")
patterns = (
    "native-layer.py json",
    "field-substrate-takeover.py json",
    "field-underlay.py json",
    "field-panel-parallel.py",
    "field-firmware-threat-removal.py",
    "field-kernel-meld.py",
    "field-plate-meld.py",
)
out = subprocess.check_output(["ps", "-eo", "pid=,etimes=,args="], text=True)
killed = 0
for line in out.splitlines():
    parts = line.split(None, 2)
    if len(parts) < 3:
        continue
    pid_s, etime_s, cmd = parts
    if "pythong" not in cmd and "python3" not in cmd:
        continue
    if not any(p in cmd for p in patterns):
        continue
    try:
        et = int(etime_s)
        pid = int(pid_s)
    except ValueError:
        continue
    if et < max_age or pid <= 1:
        continue
    try:
        os.kill(pid, signal.SIGKILL)
        killed += 1
    except ProcessLookupError:
        pass
if killed:
    print("killed_hung", killed)
PY
}

nexus_stray_kill_orphan_daemon_roots() {
  local -a roots=()
  local pid ppid
  while IFS= read -r line; do
    [[ -n "$line" ]] || continue
    pid="${line%% *}"
    ppid="$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d ' ')"
    [[ "$ppid" == "1" ]] && roots+=("$pid")
  done < <(pgrep -f '/nexus-daemon\.sh' 2>/dev/null || true)
  if [[ ${#roots[@]} -le 1 ]]; then
    return 0
  fi
  local keep="${roots[0]}"
  if command -v systemctl >/dev/null 2>&1; then
    local main
    main="$(systemctl show -p MainPID --value nexus-genius.service 2>/dev/null || true)"
    [[ -n "$main" && "$main" != "0" ]] && keep="$main"
  fi
  for pid in "${roots[@]}"; do
    [[ "$pid" == "$keep" ]] && continue
    kill "$pid" 2>/dev/null || true
    sleep 0.1
    kill -9 "$pid" 2>/dev/null || true
  done
}

nexus_stray_kill_amouranthrtx_window() {
  local retire="${NEXUS_INSTALL_ROOT}/lib/amouranthrtx-window-retire.sh"
  [[ -f "$retire" ]] || return 0
  # shellcheck source=/dev/null
  source "$retire"
  declare -f amouranthrtx_window_retire_cycle >/dev/null 2>&1 || return 0
  amouranthrtx_window_retire_cycle
}

nexus_stray_task_guard_cycle() {
  nexus_stray_guard_enabled || return 0
  nexus_stray_guard_due || return 0
  nexus_stray_prune_tray_watchdogs
  nexus_stray_prune_duplicate_guards
  nexus_stray_kill_json_probes
  nexus_stray_kill_hung_pythong
  nexus_stray_kill_orphan_daemon_roots
  nexus_stray_kill_amouranthrtx_window
  nexus_stray_guard_mark
}