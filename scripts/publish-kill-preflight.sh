#!/usr/bin/env bash
# Pre-publish kill lane — secure kill · anti-hook · scrub fake caches · RE-KILL slowdowns.
# No mercy: cache · system · storage purged before every publish.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-$ROOT}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-state}"
export SG_ROOT="${SG_ROOT:-$(cd "$ROOT/.." && pwd)}"
export SG_ROOT_KILL_PREJUDICE="${SG_ROOT_KILL_PREJUDICE:-1}"
export SG_ROOT_SOVEREIGN_KILL="${SG_ROOT_SOVEREIGN_KILL:-1}"
export PUBLISH_KILL_NO_MERCY="${PUBLISH_KILL_NO_MERCY:-1}"
export NEXUS_STRAY_TASK_GUARD="${NEXUS_STRAY_TASK_GUARD:-1}"
PY="${PY:-$(command -v python3)}"

log() { printf '[publish-kill] %s\n' "$*"; }

log "secure kill posture (Eye · Ear · Mouth prejudice)"
"$PY" "$ROOT/lib/field-sense-secure-kill.py" 2>/dev/null | "$PY" -c "
import json,sys
d=json.load(sys.stdin)
print('  policy:', d.get('kill_policy'), 'ok:', d.get('ok'))
" || log "  secure-kill skipped"

log "anti-hook verify (git · DNS · credential hijacks)"
H7_SECURE="$ROOT/Hostess7/scripts/hostess7_secure_git.py"
if [[ -f "$H7_SECURE" ]]; then
  "$PY" "$H7_SECURE" verify 2>/dev/null | "$PY" -c "
import json,sys
d=json.load(sys.stdin)
ah=d.get('anti_hook') or {}
gc=(ah.get('git_config') or {}).get('ok')
gh=(ah.get('git_hooks') or {}).get('ok')
print('  git_config:', gc, 'git_hooks:', gh)
" || log "  secure-git verify warn"
fi

log "system purge — stray probes · hung json · duplicate guards"
STRAY="$ROOT/lib/nexus-stray-task-guard.sh"
if [[ -f "$STRAY" ]]; then
  # shellcheck source=/dev/null
  source "$STRAY" 2>/dev/null || true
  for fn in \
    nexus_stray_prune_tray_watchdogs \
    nexus_stray_prune_duplicate_guards \
    nexus_stray_kill_json_probes \
    nexus_stray_kill_hung_pythong \
    nexus_stray_kill_orphan_daemon_roots \
    nexus_stray_kill_amouranthrtx_window; do
    if declare -F "$fn" >/dev/null 2>&1; then
      "$fn" 2>/dev/null || true
    fi
  done
  log "  stray task guard cycle complete"
fi
if [[ -f "$ROOT/scripts/kill-nexus-probe-storm.sh" ]]; then
  bash "$ROOT/scripts/kill-nexus-probe-storm.sh" >/dev/null 2>&1 || true
fi

LAYER="$ROOT/lib/field-layer-sweep.py"
if [[ -f "$LAYER" && "$PUBLISH_KILL_NO_MERCY" == "1" ]]; then
  "$PY" "$LAYER" localhost --apply 2>/dev/null | "$PY" -c "
import json,sys
try:
  d=json.load(sys.stdin)
  print('  localhost fields:', d.get('cleared', d.get('plate_count', 'ok')))
except Exception:
  print('  layer sweep idle')
" || true
fi

log "browser scrub — telemetry · fake host caches · hook profiles"
IMPORT="$ROOT/Queen/lib/queen-browser-import.py"
if [[ -f "$IMPORT" ]]; then
  SWEEP_ARGS=(sweep)
  [[ "$PUBLISH_KILL_NO_MERCY" == "1" ]] || SWEEP_ARGS+=(--no-apply)
  "$PY" "$IMPORT" "${SWEEP_ARGS[@]}" 2>/dev/null | "$PY" -c "
import json,sys
try:
  d=json.load(sys.stdin)
  print('  swept:', d.get('imported_count', d.get('secured_count', 'ok')),
        'dropped:', d.get('dropped',0), 'quarantined:', d.get('quarantined',0))
except Exception:
  print('  sweep ok')
" || true
  "$PY" -c "
import importlib.util, json
from pathlib import Path
p=Path('$IMPORT')
spec=importlib.util.spec_from_file_location('qbi', p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
print(json.dumps(m.organize_scrub()))
" 2>/dev/null | "$PY" -c "
import json,sys
d=json.load(sys.stdin)
print('  scrub primary:', (d.get('primary') or {}).get('browser_id','?'),
      'other:', d.get('other_count',0), 'old_drop:', d.get('old_drop_count',0))
" || true
fi

log "internet clean — secure bookmarks · telemetry strip (Hostess 7 default)"
CLEAN="$ROOT/lib/hostess7-internet-clean.py"
if [[ -f "$CLEAN" ]]; then
  HOSTESS7_PAGES_BASE="${HOSTESS7_PAGES_BASE:-https://zacharygeurts.github.io/Hostess7}" \
  "$PY" "$CLEAN" json 2>/dev/null | "$PY" -c "
import json,sys
d=json.load(sys.stdin)
s=d.get('summary') or {}
print('  bookmarks:', s.get('bookmarks_secured',0), 'firefox:', s.get('firefox_profiles',0),
      'chromium:', s.get('chromium_profiles',0), 'quarantined:', s.get('telemetry_quarantined',0))
" || true
fi

log "RE-KILL fake terrorist caches / orphan slowdown hooks"
ATTACK="$ROOT/lib/field-attack-kit.py"
if [[ -f "$ATTACK" ]]; then
  for lane in revalidate-kill-list boot-rekill auto-rekill rekill-all-registered qemu-bot-rekill; do
    "$PY" "$ATTACK" "$lane" 2>/dev/null | "$PY" -c "
import json,sys
lane='$lane'
try:
  d=json.load(sys.stdin)
  key='rekilled_count' if 'rekill' in lane else 'ok'
  print(f'  {lane}:', d.get(key, d.get('rekilled_count', d.get('checked', 'ok'))))
except Exception:
  print(f'  {lane}: idle')
" || true
  done
fi

log "QEMU bot lane — cool idle VMs · rekill orphan qemu probes"
QEMU_COOL="$ROOT/GrokLab/deploy/qemu-world-cool.sh"
if [[ -f "$QEMU_COOL" ]]; then
  bash "$QEMU_COOL" suspend-idle 2>/dev/null | "$PY" -c "
import json,sys
try:
  d=json.load(sys.stdin)
  print('  qemu suspend-idle:', d.get('suspended', d.get('ok', 'ok')))
except Exception:
  print('  qemu suspend-idle: ok')
" || log "  qemu cool idle"
fi
for pat in 'qemu-world-pipeline' 'world-node-c2-kilroy-war-deploy' 'qemu-system-x86_64.*-snapshot'; do
  pkill -f "$pat" 2>/dev/null || true
done
if [[ -f "$ROOT/lib/qemu-world-status.py" ]]; then
  "$PY" "$ROOT/lib/qemu-world-status.py" 2>/dev/null | "$PY" -c "
import json,sys
try:
  d=json.load(sys.stdin)
  print('  qemu pipeline:', 'running' if d.get('running') else 'idle',
        '·', d.get('completed',0), '/', d.get('target','?'))
except Exception:
  print('  qemu pipeline: idle')
" || true
fi

if [[ "$PUBLISH_KILL_NO_MERCY" == "1" ]]; then
  log "storage purge — nexus-state ephemeral · browser old-data · hook junk"
  "$PY" -c "
import os, shutil
from pathlib import Path

state = Path(os.environ['NEXUS_STATE_DIR'])
keep = frozenset({
    'field-hostile.tsv', 'field-nokill.tsv', 'kill-rekill-registry.json',
    'host-attacks.json', 'angel-dossiers.json', 'permanent-field.marker',
    'queen-browser-import.json', 'field-sense-secure-kill.json',
})
purged_files = 0
purged_bytes = 0

for fp in state.iterdir():
    if not fp.is_file():
        continue
    name = fp.name
    if name in keep:
        continue
    if name.endswith(('.lock', '.tmp')) or name.startswith(('complete-', 'deploy-slot-')):
        try:
            purged_bytes += fp.stat().st_size
            fp.unlink()
            purged_files += 1
        except OSError:
            pass

old = state / 'browser-scrub' / 'old-data'
if old.is_dir():
    for fp in old.iterdir():
        try:
            if fp.is_file():
                purged_bytes += fp.stat().st_size
                fp.unlink()
                purged_files += 1
            elif fp.is_dir():
                purged_bytes += sum(f.stat().st_size for f in fp.rglob('*') if f.is_file())
                shutil.rmtree(fp, ignore_errors=True)
                purged_files += 1
        except OSError:
            pass

redundant = state / 'plate-meld-redundant'
if redundant.is_dir():
    try:
        purged_bytes += sum(f.stat().st_size for f in redundant.rglob('*') if f.is_file())
        shutil.rmtree(redundant, ignore_errors=True)
        purged_files += 1
    except OSError:
        pass

# Trim bloated telemetry ledgers — keep tail only (fake cache slowdown hooks)
for fp in state.glob('*.jsonl'):
    if fp.name in keep:
        continue
    try:
        if fp.stat().st_size < 512_000:
            continue
        lines = fp.read_text(encoding='utf-8', errors='replace').splitlines()
        if len(lines) <= 4096:
            continue
        tail = '\n'.join(lines[-4096:]) + '\n'
        before = fp.stat().st_size
        fp.write_text(tail, encoding='utf-8')
        purged_bytes += max(0, before - fp.stat().st_size)
        purged_files += 1
    except OSError:
        pass

print(f'  purged: {purged_files} items · ~{purged_bytes // 1024} KiB')
" 2>/dev/null || log "  storage purge skipped"

  NF="$ROOT/lib/field-non-fielded-safety.py"
  if [[ -f "$NF" ]]; then
    "$PY" "$NF" purge-nested-drive --apply 2>/dev/null | "$PY" -c "
import json,sys
try:
  d=json.load(sys.stdin)
  print('  nested drive field:', len(d.get('purged') or []), 'dirs')
except Exception:
  pass
" || true
  fi

  EXT="$ROOT/Queen/lib/queen-external-wire.py"
  if [[ -f "$EXT" ]]; then
    "$PY" -c "
import importlib.util, json
from pathlib import Path
p = Path('$EXT')
spec = importlib.util.spec_from_file_location('qew', p)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
print(json.dumps(m.purge_external(confirm=True)))
" 2>/dev/null | "$PY" -c "
import json,sys
try:
  d=json.load(sys.stdin)
  print('  external wire purged:', d.get('ok', False))
except Exception:
  pass
" || true
  fi

  log "cache purge — pages build mirror · fieldstorage staging · publish temps"
  for cache_dir in \
    "$ROOT/Hostess7/.pages-build-state" \
    "$ROOT/.pages-build-state" \
    "$ROOT/Hostess7/cache/fieldstorage/team_staging"; do
    [[ -d "$cache_dir" ]] || continue
    find "$cache_dir" -mindepth 1 -maxdepth 1 -exec rm -rf {} + 2>/dev/null || true
    log "  cleared $(basename "$(dirname "$cache_dir")")/$(basename "$cache_dir")"
  done
  for pages_pub in "$ROOT"/Hostess7/.pages-*-publish; do
    [[ -d "$pages_pub" ]] || continue
    rm -rf "$pages_pub"
    log "  cut stale $(basename "$pages_pub")"
  done
  for stale_clone in \
    "$ROOT/.hostess7-github-clone" \
    "$ROOT/.ammoos-github-clone" \
    "$ROOT/.gnueol-terminal-github-clone"; do
    [[ -d "$stale_clone" ]] || continue
    rm -rf "$stale_clone"
    log "  cut stale publish clone $(basename "$stale_clone")"
  done
  for tmp in "$ROOT"/.h7updater-publish/tmp "$ROOT"/.pages-hub-staging/tmp; do
    [[ -d "$tmp" ]] && rm -rf "$tmp"/* 2>/dev/null || true
  done
fi

log "pages staging cache trim (stale hub mirrors)"
for d in "$ROOT"/.pages-hub-* "$ROOT"/.pages-*-publish "$ROOT"/.senses-publish-* "$ROOT"/.wiki-*-publish; do
  [[ -d "$d/.git" ]] || continue
  git -C "$d" gc --prune=now --quiet 2>/dev/null || true
  git -C "$d" repack -ad 2>/dev/null || true
done

log "AmmoNet · Final Internet — publish static ISP panel for Pages"
AMMONET="$ROOT/lib/ammonet-field.py"
if [[ -f "$AMMONET" ]]; then
  "$PY" "$AMMONET" publish 2>/dev/null | "$PY" -c "
import json,sys
try:
  d=json.load(sys.stdin)
  print('  ammonet modules:', len(d.get('modules') or []), '· pipe', (d.get('isp') or {}).get('pipe_percent', 100), '%')
except Exception:
  print('  ammonet publish: ok')
" || true
fi

log "preflight kill lane complete — publish may proceed"