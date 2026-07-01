#!/usr/bin/env bash
# Canonical AmmoLang entry — all operator scripts exec here.
set -euo pipefail
TASK="${1:?usage: ammolang-route.sh TASK [args...]}"
shift
_LIB="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${_LIB}/ammolang-kit-env.sh"
exec bash "${_LIB}/ammolang-run.sh" "$TASK" "$@"