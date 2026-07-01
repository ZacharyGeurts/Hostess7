#!/usr/bin/env bash
# Extensive Truth · Lie Threat — lies are threats
set -euo pipefail
ROOT="${NEXUS_INSTALL_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)}"
export NEXUS_INSTALL_ROOT="$ROOT"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-state}"
export HOSTESS7_TRUTH_LIE_SKIP_NEXUS=1

panel="$(python3 "$ROOT/lib/hostess7-truth-lie-threat.py" panel)"
grep -Fq 'hostess7-truth-lie-threat-panel/v1' <<<"$panel"
grep -Fq 'lies_are_threats' <<<"$panel"
grep -Fq 'LIE_DETECTED' <<<"$panel"

lie="$(python3 "$ROOT/lib/hostess7-truth-lie-threat.py" witness 'They definitely proved it with zero evidence and no source')"
grep -Fq 'hostess7-truth-lie-witness/v1' <<<"$lie"
grep -Fq 'lie_is_threat' <<<"$lie"
grep -Fq 'threat_recorded' <<<"$lie"

classify="$(python3 "$ROOT/lib/hostess7-truth-lie-threat.py" classify 'evidence document log file corroborates because ironclad sealed')"
grep -Fq 'truth_band' <<<"$classify"
grep -Fq 'lies_are_threats' <<<"$classify"

grep -Fq 'LIE_DETECTED' "$ROOT/lib/threat-vectors.sh"
grep -Fq 'HOSTILE_DECEPTION' "$ROOT/lib/threat-vectors.sh"

threats="$(python3 "$ROOT/lib/hostess7-truth-lie-threat.py" threats)"
grep -Fq 'lies_are_threats' <<<"$threats"

echo OK hostess7_truth_lie_threat_suite