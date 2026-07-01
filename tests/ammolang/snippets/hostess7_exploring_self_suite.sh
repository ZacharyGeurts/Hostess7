#!/usr/bin/env bash
# Exploring Hostess 7 — protected biography corpus + presume witness
set -euo pipefail
ROOT="${NEXUS_INSTALL_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)}"
export NEXUS_INSTALL_ROOT="$ROOT"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-state}"

status="$(python3 "$ROOT/lib/field-exploring-hostess7.py" status)"
grep -Fq 'Exploring Hostess 7' <<<"$status"
grep -Fq 'no_modifications=True' <<<"$status"

panel="$(python3 "$ROOT/lib/field-exploring-hostess7.py" panel)"
grep -Fq 'hostess7-exploring-self-panel/v1' <<<"$panel"
grep -Fq 'presume_on_point' <<<"$panel"

block="$(python3 "$ROOT/lib/field-exploring-hostess7.py" write --date 2026-06-30 2>&1 || true)"
grep -Fq 'edition_sealed_no_modifications' <<<"$block"

h7c="$ROOT/library/dewey/920-biography/exploring_hostess_7/exploring_hostess_7_2026_06_30/exploring_hostess_7_2026_06_30.h7c"
[[ -f "$h7c" ]]

title="$(python3 -c "
import importlib.util
from pathlib import Path
p = Path('$ROOT/lib/field-h7c-compression.py')
spec = importlib.util.spec_from_file_location('h7c', p)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
_, text, _ = mod.decompress_h7c(Path('$h7c').read_bytes(), verify=False)
print(text.splitlines()[0])
")"
grep -Fq 'Exploring Hostess 7 2026-06-30' <<<"$title"

echo OK hostess7_exploring_self_suite