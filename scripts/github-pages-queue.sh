#!/usr/bin/env bash
# GitHub Pages queue — cancel-in-progress stays false in workflow; we clear stuck runs here.
set -euo pipefail

REPO_SLUG="${HOSTESS7_GITHUB_REPO_SLUG:-ZacharyGeurts/Hostess7}"
WORKFLOW="${PAGES_WORKFLOW:-hostess7-pages.yml}"
STUCK_MIN="${PAGES_STUCK_MIN:-18}"
PENDING_MAX_MIN="${PAGES_PENDING_MAX_MIN:-25}"
WAIT_SLOT_SEC="${PAGES_WAIT_SLOT_SEC:-90}"

log() { printf '[pages-queue] %s\n' "$*"; }

_pages_py() {
  python3 - "$REPO_SLUG" "$WORKFLOW" "$STUCK_MIN" "$PENDING_MAX_MIN" <<'PY'
import json, subprocess, sys
from datetime import datetime, timezone

repo, workflow, stuck_min, pending_max = sys.argv[1:5]
stuck_min = int(stuck_min)
pending_max = int(pending_max)

def gh(*args):
    p = subprocess.run(
        ["gh", *args, "--repo", repo],
        capture_output=True, text=True, errors="replace",
    )
    return p

def list_runs():
    p = gh(
        "run", "list", f"--workflow={workflow}",
        "--json", "databaseId,status,conclusion,createdAt,displayTitle,event",
        "--limit", "20",
    )
    if p.returncode != 0:
        return []
    try:
        return json.loads(p.stdout or "[]")
    except json.JSONDecodeError:
        return []

def cancel(rid):
    gh("run", "cancel", str(rid))

now = datetime.now(timezone.utc)
runs = list_runs()
active = [r for r in runs if r.get("status") in ("in_progress", "queued", "waiting", "pending")]
out = {"cancelled": [], "kept": [], "active": len(active)}

for r in active:
    rid = r["databaseId"]
    st = r.get("status", "")
    created = datetime.fromisoformat(r["createdAt"].replace("Z", "+00:00"))
    age = (now - created).total_seconds() / 60
    title = (r.get("displayTitle") or "")[:70]
    do_cancel = False
    reason = ""
    if st == "in_progress" and age >= stuck_min:
        do_cancel = True
        reason = f"stuck in_progress {age:.0f}m"
    elif st in ("queued", "waiting", "pending") and age >= pending_max:
        do_cancel = True
        reason = f"stale {st} {age:.0f}m"
    if do_cancel:
        cancel(rid)
        out["cancelled"].append({"id": rid, "reason": reason, "title": title})
    else:
        out["kept"].append({"id": rid, "status": st, "age_min": round(age, 1), "title": title})

print(json.dumps(out, ensure_ascii=False))
PY
}

github_pages_cancel_stuck() {
  _pages_py | python3 -c "
import json,sys
d=json.load(sys.stdin)
for c in d.get('cancelled',[]):
    print(f\"cancel {c['id']}: {c['reason']} — {c['title']}\")
for k in d.get('kept',[]):
    print(f\"keep   {k['id']}: {k['status']} {k['age_min']}m — {k['title']}\")
print(f\"active={d.get('active',0)} cancelled={len(d.get('cancelled',[]))}\")
"
}

github_pages_has_young_runner() {
  _pages_py | python3 -c "
import json,sys
d=json.load(sys.stdin)
for k in d.get('kept',[]):
    if k.get('status')=='in_progress':
        sys.exit(0)
sys.exit(1)
"
}

github_pages_wait_slot() {
  local tries="${1:-12}"
  local n=0
  while (( n < tries )); do
    github_pages_cancel_stuck || true
    if ! github_pages_has_young_runner; then
      log "slot open — no young in_progress runner"
      return 0
    fi
    n=$((n + 1))
    log "young runner active — wait ${WAIT_SLOT_SEC}s (${n}/${tries})"
    sleep "$WAIT_SLOT_SEC"
  done
  log "WARN: slot still busy after ${tries} waits — dispatch may queue"
  return 0
}

github_pages_dispatch() {
  command -v gh >/dev/null 2>&1 || { log "gh missing"; return 1; }
  github_pages_wait_slot "${PAGES_WAIT_TRIES:-8}"
  local url
  url="$(gh workflow run "$WORKFLOW" --ref main --repo "$REPO_SLUG" 2>&1 | tail -1)"
  log "dispatched ${WORKFLOW} → ${url}"
}

github_pages_status() {
  gh run list --workflow="$WORKFLOW" --repo "$REPO_SLUG" --limit 5 2>/dev/null || true
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  case "${1:-}" in
    cancel-stuck|clear) github_pages_cancel_stuck ;;
    wait-slot) github_pages_wait_slot "${2:-12}" ;;
    dispatch) github_pages_dispatch ;;
    status) github_pages_status ;;
    -h|--help|help)
      cat <<EOF
github-pages-queue.sh — queue hygiene (workflow cancel-in-progress: false)

  cancel-stuck   Cancel in_progress >${STUCK_MIN}m, pending >${PENDING_MAX_MIN}m
  wait-slot      Clear stuck, wait for slot
  dispatch       wait-slot + workflow_dispatch
  status         List recent runs
EOF
      ;;
    *)
      echo "usage: github-pages-queue.sh {cancel-stuck|wait-slot|dispatch|status}" >&2
      exit 1
      ;;
  esac
fi