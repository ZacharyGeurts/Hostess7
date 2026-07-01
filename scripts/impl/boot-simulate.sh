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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/impl/boot-simulate.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Boot simulation — preempt conditions before KILROY reboot.
set -euo pipefail

_IMPL_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SG="$(cd "${SG_ROOT:-$(cd "${_IMPL_ROOT}/.." && pwd)}" && pwd)"
NL="${NEXUS_INSTALL_ROOT:-${_IMPL_ROOT}}"
STATE="${NEXUS_STATE_DIR:-$NL/.nexus-state}"
KILROY="${KILROY_ROOT:-$NL/KILROY}"
RECEIPT="$STATE/boot-simulation-receipt.json"
PY="$(command -v pythong || command -v python3)"
ESP="${GROK_ESP:-/boot/efi}"
FAIL=0
FIXES=()
BLOCKERS=()

log() { printf '[boot-sim] %s\n' "$*"; }
pass() { log "PASS: $*"; }
fail() { log "FAIL: $*"; FAIL=1; BLOCKERS+=("$*"); }
fix() { log "FIX: $*"; FIXES+=("$*"); }

export SG_ROOT="$SG" NEXUS_INSTALL_ROOT="$NL" NEXUS_STATE_DIR="$STATE" KILROY_ROOT="$KILROY"

ROOT_DEV="$(findmnt -n -o SOURCE / 2>/dev/null || true)"
ROOT_UUID="$(findmnt -n -o UUID / 2>/dev/null || blkid -s UUID -o value "$ROOT_DEV" 2>/dev/null || true)"
ROOT_FSTYPE="$(findmnt -n -o FSTYPE / 2>/dev/null || true)"

log "=== boot simulation begin ==="
log "root_dev=$ROOT_DEV uuid=$ROOT_UUID fstype=$ROOT_FSTYPE"

# --- 1. Permanent fielding ensure (simulated power-on) ---
if [[ -f "$STATE/permanent-field.marker" || -f "$SG/.nexus-state/permanent-field.marker" ]]; then
  if "$PY" "$NL/lib/field-permanent-fielding.py" ensure >/dev/null 2>&1; then
    pass "permanent fielding ensure"
  else
    fail "permanent fielding ensure"
  fi
else
  fail "permanent-field.marker missing"
fi

# --- 2. Nexus boot-impl refresh ---
if SG_ROOT="$SG" NEXUS_INSTALL_ROOT="$NL" NEXUS_STATE_DIR="$STATE" \
    bash "$NL/scripts/nexus-boot-impl.sh" >>"$STATE/boot-sim-impl.log" 2>&1; then
  pass "nexus-boot-impl refresh"
else
  fail "nexus-boot-impl refresh (see boot-sim-impl.log)"
fi

# --- 3. KILROY static handoff ---
if bash "$KILROY/scripts/test-boot-handoff.sh" >/dev/null 2>&1; then
  pass "KILROY boot handoff tests"
else
  fail "KILROY boot handoff tests"
fi

# --- 4. Fix grok root= for live host (LABEL mismatch) ---
HOST_ENTRIES="$KILROY/boot/grok/grok.entries.host.conf"
if [[ -n "$ROOT_UUID" ]]; then
  cat >"$HOST_ENTRIES" <<EOF
# Auto-generated host boot entries — root UUID matches live /
/+Host boot (simulated)
comment: Grok host simulation — root UUID from live mount (not LABEL=KILROY_FIELD)

/KILROY Field (host root)
comment: Primary — KILROY kernel on current Ubuntu root · UUID=$ROOT_UUID
protocol: linux
path: boot():/boot/kilroy/bzImage
cmdline: root=UUID=$ROOT_UUID rw quiet splash loglevel=3 kilroy.field=1 grok.security=strict

/KILROY Field (host + initrd)
comment: Host root with initramfs module
protocol: linux
path: boot():/boot/kilroy/bzImage
module_path: boot():/boot/kilroy/initramfs.cpio.gz
cmdline: root=UUID=$ROOT_UUID rw quiet splash loglevel=3 kilroy.field=1 grok.security=strict

/Ubuntu fallback (GRUB)
comment: Recovery — boot incumbent Ubuntu via shim if KILROY entry fails
protocol: efi
path: boot():/EFI/ubuntu/shimx64.efi
EOF
  fix "wrote grok.entries.host.conf with root=UUID=$ROOT_UUID"
  # Compose grok.conf including host entries
  GROK="$KILROY/boot/grok"
  THEME="$(tr -d '[:space:]' <"$GROK/themes/ACTIVE" 2>/dev/null || echo field)"
  TD="$GROK/themes/$THEME"
  theme_val() { grep -E "^${1}=" "$TD/theme.conf" 2>/dev/null | head -1 | cut -d= -f2-; }
  GROK_THEME_WALLPAPER="$(theme_val wallpaper)"
  GROK_THEME_BACKDROP="$(theme_val backdrop)"
  GROK_THEME_PALETTE="$(theme_val palette)"
  GROK_THEME_PALETTE_BRIGHT="$(theme_val palette_bright)"
  GROK_THEME_BG="$(theme_val bg)"
  GROK_THEME_FG="$(theme_val fg)"
  GROK_THEME_BG_BRIGHT="$(theme_val bg_bright)"
  GROK_THEME_FG_BRIGHT="$(theme_val fg_bright)"
  substitute() {
    local line="$1"
    line="${line//\$\{GROK_THEME_WALLPAPER\}/$GROK_THEME_WALLPAPER}"
    line="${line//\$\{GROK_THEME_BACKDROP\}/$GROK_THEME_BACKDROP}"
    line="${line//\$\{GROK_THEME_PALETTE\}/$GROK_THEME_PALETTE}"
    line="${line//\$\{GROK_THEME_PALETTE_BRIGHT\}/$GROK_THEME_PALETTE_BRIGHT}"
    line="${line//\$\{GROK_THEME_BG\}/$GROK_THEME_BG}"
    line="${line//\$\{GROK_THEME_FG\}/$GROK_THEME_FG}"
    line="${line//\$\{GROK_THEME_BG_BRIGHT\}/$GROK_THEME_BG_BRIGHT}"
    line="${line//\$\{GROK_THEME_FG_BRIGHT\}/$GROK_THEME_FG_BRIGHT}"
    printf '%s\n' "$line"
  }
  TMP="$(mktemp)"
  {
    echo "# Grok Bootloader — host simulation $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "default_entry: 1"
    echo ""
    while IFS= read -r line || [[ -n "$line" ]]; do substitute "$line"; done <"$GROK/grok.base.conf"
    echo ""
    cat "$HOST_ENTRIES"
    echo ""
    cat "$GROK/grok.entries.conf"
  } >"$TMP"
  mv "$TMP" "$GROK/grok.conf"
  fix "composed grok.conf with host UUID entry as default_entry=1"
else
  fail "could not detect root UUID"
fi

# --- 5. Sync ESP (needs sudo) ---
if [[ "$(id -u)" -eq 0 ]] || sudo -n true 2>/dev/null; then
  SUDO="sudo -n"
else
  SUDO="sudo"
fi
if $SUDO test -d "$ESP" 2>/dev/null; then
  $SUDO mkdir -p "$ESP/boot/kilroy" "$ESP/boot/grok" "$ESP/EFI/BOOT" 2>/dev/null || true
  if [[ -f "$KILROY/build/bzImage" ]]; then
    $SUDO cp -f "$KILROY/build/bzImage" "$ESP/boot/kilroy/bzImage" && fix "synced bzImage to ESP"
  else
    fail "missing $KILROY/build/bzImage"
  fi
  if [[ -f "$KILROY/build/initramfs.cpio.gz" ]]; then
    $SUDO cp -f "$KILROY/build/initramfs.cpio.gz" "$ESP/boot/kilroy/initramfs.cpio.gz" && fix "synced initramfs to ESP"
  else
    fail "missing initramfs.cpio.gz"
  fi
  if [[ -f "$GROK/grok.conf" ]]; then
    $SUDO cp -f "$GROK/grok.conf" "$ESP/boot/grok/grok.conf"
    $SUDO cp -f "$GROK/grok.conf" "$ESP/boot/limine.conf" 2>/dev/null || true
    $SUDO cp -f "$GROK/grok.conf" "$ESP/limine.conf" 2>/dev/null || true
    fix "synced grok.conf to ESP"
  fi
  if [[ -f "$KILROY/boot/grok/vendor/limine/BOOTX64.EFI" ]]; then
    $SUDO cp -f "$KILROY/boot/grok/vendor/limine/BOOTX64.EFI" "$ESP/EFI/BOOT/BOOTX64.EFI" && fix "synced BOOTX64.EFI"
  fi
  if $SUDO test -f "$ESP/boot/kilroy/bzImage" 2>/dev/null; then
    pass "ESP bzImage present"
  else
    fail "ESP bzImage missing after sync"
  fi
  if $SUDO grep -q "root=UUID=$ROOT_UUID" "$ESP/boot/grok/grok.conf" 2>/dev/null; then
    pass "ESP grok.conf has host root UUID"
  else
    fail "ESP grok.conf missing host root UUID"
  fi
else
  fail "ESP not accessible at $ESP"
fi

# --- 6. Panel + Queen stack ---
panel_code="$(curl -sf -o /dev/null -w '%{http_code}' --connect-timeout 2 http://127.0.0.1:9477/field 2>/dev/null || echo 000)"
queen_code="$(curl -sf -o /dev/null -w '%{http_code}' --connect-timeout 2 http://127.0.0.1:9481/api/status 2>/dev/null || echo 000)"
if [[ "$panel_code" == "200" ]]; then pass "panel :9477"; else
  fail "panel :9477 down ($panel_code)"
  # shellcheck source=/dev/null
  source "$NL/lib/nexus-aml-exec.sh"
  nexus_aml_exec script:scripts/impl/ammoos-direct-start.sh >/dev/null 2>&1 && fix "started panel+queen via ammoos-direct-start" || true
fi
if [[ "$queen_code" == "200" ]]; then pass "queen :9481"; else fail "queen :9481 down ($queen_code)"; fi

# --- 7. EFI boot order witness ---
if command -v efibootmgr >/dev/null 2>&1; then
  efibootmgr 2>/dev/null | head -6 >"$STATE/boot-sim-efi.txt" || true
  pass "EFI boot order captured"
else
  log "WARN: efibootmgr unavailable"
fi

# --- 8. Grok firmware audit (non-fatal) ---
if bash "$KILROY/scripts/grok-firmware-audit.sh" >/dev/null 2>&1; then
  pass "grok firmware audit"
else
  log "WARN: grok firmware audit — review before strict boot"
fi

# --- Write receipt ---
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
mkdir -p "$STATE"
FIX_JSON="$STATE/.boot-sim-fixes.json"
BLK_JSON="$STATE/.boot-sim-blockers.json"
printf '%s\n' "${FIXES[@]:-}" | "$PY" -c 'import json,sys; print(json.dumps([l for l in sys.stdin.read().splitlines() if l.strip()]))' >"$FIX_JSON"
printf '%s\n' "${BLOCKERS[@]:-}" | "$PY" -c 'import json,sys; print(json.dumps([l for l in sys.stdin.read().splitlines() if l.strip()]))' >"$BLK_JSON"
REBOOT_SAFE=0
[[ $FAIL -eq 0 ]] && REBOOT_SAFE=1
SG_ROOT="$SG" NEXUS_INSTALL_ROOT="$NL" NEXUS_STATE_DIR="$STATE" "$PY" - <<PYEOF
import json
from pathlib import Path
receipt = {
    "schema": "boot-simulation-receipt/v1",
    "ts": "$TS",
    "ok": bool($REBOOT_SAFE),
    "root_dev": "$ROOT_DEV",
    "root_uuid": "$ROOT_UUID",
    "root_fstype": "$ROOT_FSTYPE",
    "fixes": json.loads(Path("$FIX_JSON").read_text()),
    "blockers": json.loads(Path("$BLK_JSON").read_text()),
    "panel": "$panel_code",
    "queen": "$queen_code",
    "esp": "$ESP",
    "kilroy_bzimage": "$KILROY/build/bzImage",
    "grok_conf": "$KILROY/boot/grok/grok.conf",
    "reboot_safe": bool($REBOOT_SAFE),
    "motto": "Simulated boot from power input — preempt blockers before KILROY reboot.",
}
Path("$RECEIPT").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt, indent=2))
PYEOF
rm -f "$FIX_JSON" "$BLK_JSON"

log "=== boot simulation complete (exit=$FAIL) ==="
log "receipt: $RECEIPT"
exit "$FAIL"
