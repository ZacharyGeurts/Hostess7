#!/usr/bin/env bash
# Rsync with size + transfer rate logging for world-node deploys.
set -euo pipefail

world_rsync_log() {
  printf '[c2-kilroy-deploy] %s\n' "$*"
}

world_rsync_human_rate() {
  local bps="${1:-0}"
  if [[ ! "$bps" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
    printf '?'
    return
  fi
  awk -v b="$bps" 'BEGIN{
    split("B/s KB/s MB/s GB/s", u, " ");
    i=1; while (b>=1024 && i<4) { b/=1024; i++ }
    if (b>=100) printf "%.0f %s", b, u[i];
    else if (b>=10) printf "%.1f %s", b, u[i];
    else printf "%.2f %s", b, u[i];
  }'
}

# world_rsync_run LABEL SRC DST [extra rsync opts...]
world_rsync_run() {
  local label="$1" src="$2" dst="$3"
  shift 3
  local extra=("$@")
  local log="${WORLD_NODE_RSYNC_LOG:-${NEXUS_STATE_DIR:-}/world-rsync.log}"
  local port="${WORLD_RSYNC_PORT:-?}"
  local node="${WORLD_RSYNC_NODE:-?}"

  mkdir -p "$(dirname "$log")" 2>/dev/null || true

  local human bytes
  if [[ -d "$src" ]]; then
    human="$(du -sh "$src" 2>/dev/null | awk '{print $1}' || echo '?')"
    bytes="$(du -sb "$src" 2>/dev/null | awk '{print $1}' || echo 0)"
  elif [[ -f "$src" ]]; then
    human="$(du -sh "$src" 2>/dev/null | awk '{print $1}' || echo '?')"
    bytes="$(stat -c%s "$src" 2>/dev/null || echo 0)"
  else
    human="?"
    bytes=0
  fi

  world_rsync_log "rsync START $label — source $human (${bytes} bytes) -> :${port} ($node)"
  {
    echo ""
    echo "=== $(date -u '+%Y-%m-%dT%H:%M:%SZ') $label $node :$port size=$human (${bytes}B) ==="
  } >>"$log"

  local start=$SECONDS
  local bwlimit=()
  [[ -n "${GROK_LAB_RSYNC_BWLIMIT:-}" ]] && bwlimit=(--bwlimit="${GROK_LAB_RSYNC_BWLIMIT}")

  set +e
  rsync -a --delete-after --info=progress2 --stats \
    "${bwlimit[@]}" \
    -e "$(world_ssh_rsync_e "$port" "$SSH_KEY")" \
    "${extra[@]}" \
    "$src" "$dst" 2>&1 | tee -a "$log" | while IFS= read -r line; do
      [[ -z "$line" ]] && continue
      if [[ "$line" =~ ^[[:space:]]*[0-9,]+ ]] || [[ "$line" == *"rsync:"* ]] \
        || [[ "$line" == *"error"* ]] || [[ "$line" == *"Total"* ]] || [[ "$line" == *"sent "* ]]; then
        world_rsync_log "$label: $line"
      fi
    done
  local rc=${PIPESTATUS[0]}
  set -e

  local elapsed=$((SECONDS - start))
  local rate_line sent_bps human_rate
  rate_line="$(grep -E 'sent [0-9,]+ bytes.*bytes/sec' "$log" 2>/dev/null | tail -1 || true)"
  if [[ -n "$rate_line" ]]; then
    sent_bps="$(echo "$rate_line" | sed -n 's/.* \([0-9,]*\.[0-9]*\) bytes\/sec.*/\1/p' | tr -d ',')"
    human_rate="$(world_rsync_human_rate "$sent_bps")"
  else
    human_rate="?"
  fi
  local total_xfer total_human
  total_xfer="$(grep 'Total bytes sent:' "$log" 2>/dev/null | tail -1 | awk '{print $4}' | tr -d ',' || echo 0)"
  total_human="$(numfmt --to=iec-i --suffix=B "$total_xfer" 2>/dev/null || echo "${total_xfer}B")"

  if [[ "$rc" -eq 0 ]]; then
    world_rsync_log "rsync DONE $label — ${elapsed}s, sent $total_human (${total_xfer}B), avg $human_rate"
  else
    world_rsync_log "rsync FAIL $label — exit $rc after ${elapsed}s (see $log)"
  fi
  return "$rc"
}