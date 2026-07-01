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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/kill-nexus-probe-storm.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Kill circular json probe storm — safe to run anytime.
set -euo pipefail
python3 <<'PY'
import os, signal, subprocess, time
patterns = (
    "NewLatest/lib/native-layer.py json",
    "NewLatest/lib/field-substrate-takeover.py json",
    "NewLatest/lib/field-underlay.py json",
    "/usr/local/lib/nexus-shield/lib/native-layer.py json",
    "/usr/local/lib/nexus-shield/lib/field-substrate-takeover.py json",
)
for rnd in range(4):
    out = subprocess.check_output(["ps", "-eo", "pid=,args="], text=True)
    killed = 0
    for line in out.splitlines():
        parts = line.split(None, 1)
        if len(parts) < 2:
            continue
        pid_s, cmd = parts
        if any(p in cmd for p in patterns):
            try:
                os.kill(int(pid_s), signal.SIGKILL)
                killed += 1
            except ProcessLookupError:
                pass
    print("round", rnd, "killed", killed)
    time.sleep(0.25)
PY