#!/usr/bin/env bash
# Hostess 7 AML ingress — secured external access, truth + lie gates
set -euo pipefail
ROOT="${NEXUS_INSTALL_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)}"
export NEXUS_INSTALL_ROOT="$ROOT"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-state}"
export HOSTESS7_OPERATOR=1

panel="$(python3 "$ROOT/lib/hostess7-aml-ingress.py" panel)"
grep -Fq 'hostess7-aml-ingress-panel/v1' <<<"$panel"
grep -Fq 'presume_separate' <<<"$panel"

read="$(python3 "$ROOT/lib/hostess7-aml-ingress.py" read)"
grep -Fq 'hostess7-aml-read/v1' <<<"$read"
grep -Fq 'truth_and_lie' <<<"$read"
grep -Fq 'local_aml' <<<"$read"

discern="$(python3 "$ROOT/lib/hostess7-aml-ingress.py" discern 'universal_boundary protects all NewLatest execution')"
grep -Fq 'truth_score' <<<"$discern"
grep -Fq '"class"' <<<"$discern"

ingress="$(python3 "$ROOT/lib/hostess7-aml-ingress.py" ingress '{"claim":"AML boundary registry has 1042 entries","party":"operator","source":"suite"}')"
grep -Fq 'hostess7-aml-ingress/v1' <<<"$ingress"
grep -Fq 'truth_pass' <<<"$ingress"
grep -Fq 'lie' <<<"$ingress"

echo OK hostess7_aml_ingress_suite