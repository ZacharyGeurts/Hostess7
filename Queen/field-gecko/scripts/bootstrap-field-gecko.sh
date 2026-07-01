#!/usr/bin/env bash
# Bootstrap stripped Queen Field Engine from upstream gecko source (MPL 2.0).
# Does not download unless --fetch is passed. Documents g16 build lane.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
QUEEN="$(cd "${ROOT}/.." && pwd)"
SG="$(cd "${QUEEN}/../.." && pwd)"
GROK16="${GROK16_ROOT:-${SG}/Grok16}"
TAG="${1:-QUEEN_GECKO_ESR_128}"
UPSTREAM_TAG="${QUEEN_GECKO_UPSTREAM_TAG:-FIREFOX_ESR_128_BASE}"
FETCH=0
if [[ "${1:-}" == "--fetch" ]]; then
  FETCH=1
  TAG="${2:-QUEEN_GECKO_ESR_128}"
  UPSTREAM_TAG="${QUEEN_GECKO_UPSTREAM_TAG:-FIREFOX_ESR_128_BASE}"
fi

SRC="${ROOT}/vendor/mozilla"
BUILD="${ROOT}/build"

cat <<EOF
Queen Field Engine bootstrap
  Queen tag:     ${TAG}
  Upstream tag:  ${UPSTREAM_TAG}
  Vendor dir:    ${SRC}
  g16 root:      ${GROK16}
  License:       MPL-2.0 — offer corresponding source on distribution

Strip goals (AI operator):
  - Telemetry / Normandy / Pocket off at compile where possible
  - Single-window kiosk to Queen Browser shell
  - g16 toolchain for engine compile (future): QUEEN_FIELD_GECKO_BUILD=1
  - Output binary name: queen-browser (never ship third-party browser branding)

EOF

if [[ "${FETCH}" != "1" ]]; then
  echo "Dry run. To clone upstream gecko source:"
  echo "  QUEEN_GECKO_UPSTREAM_TAG=${UPSTREAM_TAG} $0 --fetch ${TAG}"
  echo "Then configure with ./mach bootstrap and wire g16 in build/mozconfig."
  exit 0
fi

mkdir -p "${ROOT}/vendor"
UPSTREAM_REPO="${QUEEN_GECKO_UPSTREAM_REPO:-https://github.com/mozilla/gecko.git}"
if [[ ! -d "${SRC}/.git" ]]; then
  git clone --depth 1 --branch "${UPSTREAM_TAG}" "${UPSTREAM_REPO}" "${SRC}"
fi

mkdir -p "${BUILD}"
cat >"${BUILD}/mozconfig.queen" <<MOZ
# Queen Field Engine — stripped operator build (template)
ac_add_options --enable-application=browser
ac_add_options --disable-telemetry
ac_add_options --disable-default-browser-agent
ac_add_options --disable-maintenance-service
# Wire g16: export CC CXX from Grok16 after mach bootstrap
# Rename output: queen-browser
MOZ

echo "Cloned to ${SRC}. Next: cd ${SRC} && ./mach bootstrap && mach build"
echo "Install as: ${ROOT}/bin/queen-browser"