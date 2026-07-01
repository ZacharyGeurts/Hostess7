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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/nexus-release-finalize.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Pre-deploy hardening check — run on a clean test VM before production install.
# Keeps underlay/boot attachment non-destructive and marker-driven.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=/dev/null
source "${ROOT}/lib/nexus-common.sh"

usage() {
  cat <<'EOF'
Usage: nexus-release-finalize.sh [--version VER] [--dry-run] [--skip-pack] [--help]

Run before hard-drive deployment:
  1. Boot-path hardening checks (static grep/syntax)
  2. Re-pack source tarball with tight exclusions
  3. Post-pack leak verification + MANIFEST.sha256
  4. Boot marker smoke test (first → refresh, no training viewer on refresh)

  --version VER   Override NEXUS_VERSION (default: lib/nexus-common.sh)
  --dry-run       Print planned steps only
  --skip-pack     Skip pack-release.sh (verify dist/ only)
  --help          Show this help
EOF
}

DRY_RUN=0
SKIP_PACK=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    -n|--dry-run) DRY_RUN=1; shift ;;
    --skip-pack) SKIP_PACK=1; shift ;;
    -v|--version)
      [[ $# -ge 2 ]] || { echo "--version requires a value" >&2; exit 1; }
      NEXUS_VERSION="$2"
      shift 2
      ;;
    *) echo "unknown option: $1" >&2; usage >&2; exit 1 ;;
  esac
done

VER="${NEXUS_VERSION}"
DIST="${ROOT}/dist"
PKG="${DIST}/nexus-shield-${VER}-source.tar.gz"

echo "=== 1. Boot path hardening checks ==="
bash -n "${ROOT}/lib/nexus-boot-impl.sh"
bash -n "${ROOT}/scripts/nexus-boot-impl.sh"
grep -q 'nexus_boot_impl_validate_install_root' "${ROOT}/lib/nexus-boot-impl.sh"
grep -q 'nexus_boot_impl_script_trusted' "${ROOT}/lib/nexus-boot-impl.sh"
grep -q 'nexus_boot_impl_rotate_log' "${ROOT}/lib/nexus-boot-impl.sh"
grep -q 'nexus_boot_impl_resolve_python' "${ROOT}/lib/nexus-boot-impl.sh"
! grep -q 'nexus_boot_impl_training_viewer' <(sed -n '/^nexus_boot_impl_refresh/,/^}/p' "${ROOT}/lib/nexus-boot-impl.sh")
grep -q 'INTEGRITY_VERIFY_FAILED' "${ROOT}/lib/nexus-boot-impl.sh"
echo "PASS: boot-impl hardening present"

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "dry-run: would pack ${VER}, verify tarball, run boot marker test"
  exit 0
fi

echo "=== 2. Pack release archives ==="
if [[ "$SKIP_PACK" -eq 0 ]]; then
  export NEXUS_VERSION="$VER"
  bash "${ROOT}/scripts/pack-release.sh"
else
  echo "skip-pack: using existing dist/"
fi

echo "=== 3. Post-pack verification ==="
[[ -f "$PKG" ]] || { echo "FAIL: missing ${PKG}" >&2; exit 1; }
if tar -tzf "$PKG" | grep -qE '(first-boot\.complete|amouranth_engine\.log|\.git/)'; then
  echo "FAIL: forbidden files leaked" >&2
  exit 1
fi
echo "PASS: clean tarball"
[[ -f "${DIST}/MANIFEST.sha256" ]] && echo "PASS: MANIFEST.sha256 present"

echo "=== 4. Boot marker smoke test ==="
tmp_state="$(mktemp -d)"
trap 'rm -rf "$tmp_state"' EXIT
NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" NEXUS_BOOT_IMPL=1 \
  NEXUS_FRONT_HOOK=0 NEXUS_SELF_DEFENSE=0 \
  bash "${ROOT}/scripts/nexus-boot-impl.sh" >/dev/null 2>&1
[[ -f "${tmp_state}/first-boot.complete" ]]
grep -q 'mode=first' "${tmp_state}/boot-impl.last"
NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" NEXUS_BOOT_IMPL=1 \
  NEXUS_FRONT_HOOK=0 NEXUS_SELF_DEFENSE=0 NEXUS_TRAINING_VIEWER_BOOT=1 \
  bash "${ROOT}/scripts/nexus-boot-impl.sh" >/dev/null 2>&1
grep -q 'mode=refresh' "${tmp_state}/boot-impl.last"
echo "PASS: first → refresh marker cycle"

echo "=== DONE (${VER}) ==="
echo "Manual VM checks still recommended:"
echo "  - no /etc/default/grub or kernel cmdline changes"
echo "  - only /usr/local/lib/nexus-shield and /var/lib/nexus-shield touched"
echo "  - panel at :9477/field; mouse/keyboard/WiFi unaffected"