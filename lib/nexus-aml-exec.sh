#!/bin/bash
# Canonical sub-invocation — always route through AmmoLang boundary (AML_BUILD=1).
# Never use AML_IMPL=1 or AML_BUILD=0 to bypass the protective shell.

nexus_aml_root() {
  if [[ -n "${NEXUS_INSTALL_ROOT:-}" && -f "${NEXUS_INSTALL_ROOT}/lib/ammolang-run.sh" ]]; then
    printf '%s' "${NEXUS_INSTALL_ROOT}"
    return 0
  fi
  local d
  d="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  printf '%s' "$d"
}

nexus_aml_exec() {
  local root target
  root="$(nexus_aml_root)"
  target="${1:?nexus_aml_exec: target required}"
  shift || true
  case "$target" in
    route:*|task:*)
      bash "${root}/lib/ammolang-run.sh" "${target#*:}" "$@"
      ;;
    script:*|py:*)
      bash "${root}/lib/ammolang-run.sh" exec "$target" "$@"
      ;;
    *)
      bash "${root}/lib/ammolang-run.sh" exec "$target" "$@"
      ;;
  esac
}