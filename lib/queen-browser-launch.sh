#!/bin/bash
# Queen Browser launch entrypoint — product identity: Queen Browser (Field Gecko).
# Delegates to fieldfox-launch.sh path for historical callers; no host-browser branding.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ROOT="${NEXUS_INSTALL_ROOT:-$ROOT}"
exec bash "${ROOT}/lib/fieldfox-launch.sh" "$@"
