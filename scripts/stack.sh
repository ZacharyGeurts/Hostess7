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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/stack.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Field stack router — AmmoLang only (kit Grok16 · lib/ammolang-run.sh).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
AML="${ROOT}/lib/ammolang-route.sh"

cmd="${1:-help}"
shift || true

case "$cmd" in
  update|publish)     exec bash "$AML" stack_update "$@" ;;
  build)              exec bash "$AML" build "$@" ;;
  wire)               exec bash "$AML" wire_stack "$@" ;;
  start|full)         exec bash "$AML" stack_start "$@" ;;
  fast|direct)        exec bash "$AML" stack_fast "$@" ;;
  restart)
    if [[ "${1:-}" == "--full" ]]; then
      shift || true
      bash "$AML" stack_restart "$@" || true
      exec bash "$AML" stack_start "$@"
    fi
    exec bash "$AML" stack_restart "$@"
    ;;
  mint-ready|mint)    exec bash "$AML" mint_boot_ready "$@" ;;
  pre-reboot|test)    exec bash "$AML" mint_pre_reboot "$@" ;;
  early)              exec bash "$AML" early_boot "$@" ;;
  boot-sim|boot)      exec bash "$AML" boot_simulate "$@" ;;
  boot-qemu|qemu)     exec bash "$AML" boot_qemu_test "$@" ;;
  znetwork)
    echo "NOTE: ZNetwork absorbed into KILROY PC core — use: stack.sh kilroy core" >&2
    exec bash "$AML" integrate_znetwork "$@"
    ;;
  kilroy)
    sub="${1:-status}"
    shift || true
    if [[ "$sub" == "core" ]]; then
      # shellcheck source=/dev/null
      source "${ROOT}/lib/ammolang-kit-env.sh"
      # shellcheck source=/dev/null
      source "${ROOT}/lib/nexus-common.sh"
      nexus_init_runtime_paths
      # shellcheck source=/dev/null
      source "${ROOT}/lib/kilroy-core.sh"
      nexus_kilroy_core_board
      exit 0
    fi
    case "$sub" in
      build|make) exec bash "$AML" kilroy_build "$@" ;;
      *)          exec bash "$AML" kilroy_bzimage "$@" ;;
    esac
    ;;
  load-os|loados)     exec bash "$AML" load_os "$@" ;;
  bzimage)
    sub="${1:-status}"
    shift || true
    case "$sub" in
      build|make) exec bash "$AML" kilroy_build "$@" ;;
      *)          exec bash "$AML" kilroy_bzimage "$@" ;;
    esac
    ;;
  aml|ammolang)       exec bash "$AML" "${1:-tasks}" "${@:2}" ;;
  help|-h|--help)
    cat <<EOF
Field stack — AmmoLang only (./lib/ammolang-run.sh)

  build         Master kit build (wire · gates · stack · boot · QEMU)
  update        Full stack_update (tests · mint · GitHub)
  wire          Wire SG siblings into NewLatest
  start|full    Full stack (panel + Queen + Final_Eye)
  fast|direct   Panel + Queen only
  restart       Fast restart; restart --full for full stack
  mint-ready    Mint boot units + autostart
  pre-reboot    Pre-reboot health (mint_pre_reboot)
  early         Early boot dry-run
  boot-sim      Boot simulation receipt
  boot-qemu     Boot order + QEMU + zpics OCR
  kilroy        KILROY bzImage · kilroy core — board
  load-os       KILROY load OS desktop
  aml <task>    Any registered task (aml.sh tasks)

Entry: lib/ammolang-run.sh · Kit: Grok16 + PythonG + AmmoLang library/
EOF
    ;;
  *)
    echo "Unknown: $cmd — run: stack.sh help" >&2
    exit 1
    ;;
esac