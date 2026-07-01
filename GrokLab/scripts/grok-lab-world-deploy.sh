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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:GrokLab/scripts/grok-lab-world-deploy.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Grok AI Lab — deploy full stack to free VMs worldwide (SSH + bundle).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NL="${NEXUS_INSTALL_ROOT:-$(cd "$ROOT/.." && pwd)}"
SG="${SG_ROOT:-$(cd "$NL/.." && pwd)}"
STATE="${NEXUS_STATE_DIR:-$NL/.nexus-state}"
PY="${GROK_LAB_PY:-python3}"
CMD="${1:-status}"

export SG_ROOT="$SG"
export NEXUS_INSTALL_ROOT="$NL"
export NEXUS_STATE_DIR="$STATE"
export GROK_LAB_ROOT="$ROOT"

log() { printf '[grok-lab-world] %s\n' "$*"; }

case "$CMD" in
  pack)
    log "Packing world node bundle…"
    "$PY" "$NL/lib/grok-lab-world.py" pack
    ;;
  bootstrap|bootstrap-local)
    log "Bootstrap local sovereign node (world perimeter home)…"
    bash "$ROOT/deploy/world-node-bootstrap.sh" --installed --region local --node-id node-local
    ;;
  launch-qemu)
    log "Launch QEMU free VM world nodes (us + eu on :2222 :2223)…"
    bash "$ROOT/deploy/qemu-world-launch.sh"
    ;;
  deploy)
    log "Deploy to all enabled nodes in GrokLab/deploy/world-nodes.json"
    if [[ ! -f "$ROOT/deploy/dist/grok-lab-node-bundle.tar.gz" ]]; then
      log "Packing bundle first…"
      "$PY" "$NL/lib/grok-lab-world.py" pack
    else
      export GROK_LAB_SKIP_PACK=1
      log "Using existing bundle ($(du -h "$ROOT/deploy/dist/grok-lab-node-bundle.tar.gz" | cut -f1))"
    fi
    "$PY" "$NL/lib/grok-lab-world.py" deploy
    ;;
  verify)
    "$PY" "$NL/lib/grok-lab-world.py" status
    curl -sf --connect-timeout 2 http://127.0.0.1:9479/api/stream/status 2>/dev/null | "$PY" -m json.tool 2>/dev/null | head -20 || true
    ;;
  world-boot)
    bash "$0" launch-qemu
    bash "$0" pack
    bash "$0" deploy
    bash "$0" verify
    ;;
  status)
    "$PY" "$NL/lib/grok-lab-world.py" status
    ;;
  providers)
    cat "$ROOT/deploy/free-vm-providers.json" | "$PY" -m json.tool 2>/dev/null || cat "$ROOT/deploy/free-vm-providers.json"
    ;;
  cloudflare|cloudflare-arm)
    log "Arm Cloudflare tunnel on local sanctuary…"
    export GROK_LAB_NODE_ID=node-local GROK_LAB_NODE_REGION=local
    bash "$ROOT/deploy/cloudflare-world-tunnel.sh"
    ;;
  cloudflare-propagate|cloudflare-deploy)
    log "Propagate Cloudflare perimeter to all world nodes…"
    bash "$ROOT/deploy/cloudflare-world-propagate.sh"
    ;;
  init-nodes)
    if [[ ! -f "$ROOT/deploy/world-nodes.json" ]]; then
      cp "$ROOT/deploy/world-nodes.example.json" "$ROOT/deploy/world-nodes.json"
      log "Created $ROOT/deploy/world-nodes.json from example"
    else
      log "world-nodes.json already exists"
    fi
    ;;
  *)
    echo "Usage: grok-lab-world-deploy.sh {init-nodes|pack|launch-qemu|bootstrap|deploy|verify|world-boot|status|providers|cloudflare|cloudflare-propagate}" >&2
    exit 1
    ;;
esac