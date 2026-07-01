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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/impl/boot-qemu-zpics-test.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Boot order audit · surface checks · zpics capture · Final Eye OCR · QEMU smoke
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SG="$(cd "${ROOT}/.." && pwd)"
ZPICS="${SG}/zpics"
KR="${KILROY_ROOT:-${ROOT}/KILROY}"
PY="$(command -v pythong || command -v python3)"
export SG_ROOT="$SG" NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-${ROOT}/.nexus-state}"

mkdir -p "$ZPICS" "$NEXUS_STATE_DIR"
[[ -f "${SG}/.nexus-state/permanent-field.marker" ]] && \
  cp -f "${SG}/.nexus-state/permanent-field.marker" "$NEXUS_STATE_DIR/" 2>/dev/null || true

log() { printf '[boot-qemu-zpics] %s\n' "$*" | tee -a "$ZPICS/boot-qemu-test.log"; }

log "=== boot order reference ==="
"$PY" - <<'PY' > "$ZPICS/boot-order-reference.txt"
import json
from pathlib import Path
NL = Path("/home/default/Desktop/SG/NewLatest")
boot = json.loads((NL / "Queen/data/ammoos-boot-map.json").read_text())
stack = json.loads((NL / "data/field-stack-layer-doctrine.json").read_text())
print("# Queen boot phases (ammoos-boot-map)")
for p in boot["phases"]:
    print(f"{p['order']:>5} {p['id']}: {p['role']}")
print("\n# Field stack layers")
for l in stack["layers_bottom_up"]:
    print(f"{l['order']:>3} {l['id']}: {l.get('role','')}")
PY

log "=== stack fast (AmmoLang impl) ==="
AML_IMPL=1 AML_IMPL=1 bash "${ROOT}/scripts/impl/ammoos-direct-start.sh" >>"$ZPICS/boot-qemu-test.log" 2>&1 || true

log "=== surface HTTP ==="
: > "$ZPICS/surface-checks.txt"
for row in \
  "http://127.0.0.1:9477/field|AmmoOS desktop" \
  "http://127.0.0.1:9481/world/?dock=terminal|Queen terminal" \
  "http://127.0.0.1:9481/world/browser.html|Queen browser"; do
  u="${row%%|*}"; name="${row##*|}"
  code=$(curl -sf -o /dev/null -w '%{http_code}' --connect-timeout 8 "$u" 2>/dev/null || echo 000)
  echo "$code $name $u" | tee -a "$ZPICS/surface-checks.txt"
done
curl -sf --max-time 10 "http://127.0.0.1:9481/api/queen-terminal" > "$ZPICS/terminal-api.json" 2>/dev/null || \
  echo '{"ok":false}' > "$ZPICS/terminal-api.json"

log "=== screenshots (playwright venv) ==="
VENV="/tmp/nexus-cap-venv"
if [[ ! -x "$VENV/bin/python" ]]; then
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install playwright -q
  "$VENV/bin/playwright" install chromium
fi
"$VENV/bin/python" - <<'PY' 2>&1 | tee -a "$ZPICS/boot-qemu-test.log"
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ZPICS = Path("/home/default/Desktop/SG/zpics")
shots = [
    ("01-ammoos-field.png", "http://127.0.0.1:9477/field"),
    ("02-queen-terminal.png", "http://127.0.0.1:9481/world/?dock=terminal"),
    ("03-queen-browser.png", "http://127.0.0.1:9481/world/browser.html"),
]
rows = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1280, "height": 800}, ignore_https_errors=True)
    for fname, url in shots:
        page = ctx.new_page()
        row = {"file": fname, "url": url, "ok": False}
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)
            out = ZPICS / fname
            page.screenshot(path=str(out))
            row["ok"] = out.is_file()
            row["bytes"] = out.stat().st_size if row["ok"] else 0
        except Exception as exc:
            row["error"] = str(exc)[:200]
        rows.append(row)
        page.close()
    browser.close()
(ZPICS / "screenshot-results.json").write_text(json.dumps(rows, indent=2) + "\n")
print(json.dumps(rows, indent=2))
PY

log "=== Hostess 7 component seal (full stack) ==="
HOSTESS7_COMPONENT_CONTROL=1 NEXUS_INSTALL_ROOT="$ROOT" "$PY" "${ROOT}/lib/hostess7-component-seal.py" seal \
  > "$ZPICS/hostess7-component-seal.json" 2>/dev/null || echo '{"sealed":false}' > "$ZPICS/hostess7-component-seal.json"
HOSTESS7_OCR_CONTROL=1 NEXUS_INSTALL_ROOT="$ROOT" "$PY" "${ROOT}/lib/final-eye-hostess7-seal.py" seal \
  > "$ZPICS/final-eye-seal.json" 2>/dev/null || echo '{"sealed":false}' > "$ZPICS/final-eye-seal.json"
HOSTESS7_COMPONENT_CONTROL=1 NEXUS_INSTALL_ROOT="$ROOT" "$PY" "${ROOT}/lib/hostess7-system-control.py" assume \
  >>"$ZPICS/hostess7-component-seal.json" 2>/dev/null || true

log "=== Final Eye OCR ==="
for img in "$ZPICS"/01-ammoos-field.png "$ZPICS"/02-queen-terminal.png "$ZPICS"/03-queen-browser.png; do
  [[ -f "$img" ]] || continue
  base=$(basename "$img" .png)
  NEXUS_INSTALL_ROOT="$ROOT" "$PY" "${ROOT}/lib/final-eye-h7-ocr.py" ocr "$img" \
    > "$ZPICS/${base}-ocr.json" 2>/dev/null || echo '{"ok":false}' > "$ZPICS/${base}-ocr.json"
  "$PY" -c "
import json, pathlib
d=json.loads(pathlib.Path('$ZPICS/${base}-ocr.json').read_text())
t=str(d.get('text') or d.get('ocr') or '')
pathlib.Path('$ZPICS/${base}-ocr.txt').write_text(t[:2000])
print('${base}:', len(t), 'chars')
" 2>/dev/null || true
done

log "=== QEMU KILROY smoke ==="
mkdir -p "$KR/build"
[[ -f "$KR/build/bzImage" ]] || cp -f "${ROOT}/Queen/field/sovereign/kernel/bzImage" "$KR/build/bzImage" 2>/dev/null || true
if [[ -f "$KR/build/bzImage" && -x "$KR/scripts/grok-boot-qemu.sh" ]]; then
  if [[ ! -f "$KR/build/grok-kilroy.img" && -x "$KR/scripts/grok-mkimage.sh" ]]; then
    # Vendor already present — patch-fetch skip via env
    GROK_SKIP_FETCH=1 bash -c '
      cd "$KR"
      export BZIMAGE=build/bzImage OUT=build
      bash scripts/grok-compose.sh 2>/dev/null || true
      VENDOR=boot/grok/vendor/limine
      LIMINE=$(find "$VENDOR" -maxdepth 4 -name limine -type f | head -1)
      BOOTX64=$(find "$VENDOR" -maxdepth 4 -name BOOTX64.EFI | head -1)
      BIOS_SYS=$(find "$VENDOR" -maxdepth 4 -name limine-bios.sys | head -1)
      STAGING=build/grok-staging IMG=build/grok-kilroy.img PART_OFFSET=1048576
      rm -rf "$STAGING" && mkdir -p "$STAGING/EFI/BOOT" "$STAGING/boot/grok" "$STAGING/boot/kilroy"
      cp -f "$BOOTX64" "$STAGING/EFI/BOOT/BOOTX64.EFI"
      cp -f "$BIOS_SYS" "$STAGING/boot/limine-bios.sys" 2>/dev/null || true
      cp -f boot/grok/grok.conf "$STAGING/boot/grok/grok.conf"
      cp -f boot/grok/grok.conf "$STAGING/limine.conf"
      cp -f build/bzImage "$STAGING/boot/kilroy/bzImage"
      cp -f build/initramfs.cpio.gz "$STAGING/boot/kilroy/" 2>/dev/null || true
      rm -f "$IMG"
      dd if=/dev/zero of="$IMG" bs=1M count=512 status=none
      parted -s "$IMG" mklabel msdos mkpart primary fat32 2048s 100%
      parted -s "$IMG" set 1 boot on
      mformat -i "${IMG}@@${PART_OFFSET}" -F -v KILROY ::
      mcopy -i "${IMG}@@${PART_OFFSET}" -s "$STAGING/EFI" ::/EFI
      mcopy -i "${IMG}@@${PART_OFFSET}" -s "$STAGING/boot" ::/boot
      mcopy -i "${IMG}@@${PART_OFFSET}" "$STAGING/limine.conf" ::/limine.conf
      "$LIMINE" bios-install "$IMG"
    ' KR="$KR" >>"$ZPICS/qemu-mkimage.log" 2>&1 || log "WARN: mkimage partial"
  fi
  GRAPHICAL=0 TIMEOUT=60 MEMORY=1G bash "$KR/scripts/grok-boot-qemu.sh" \
    >"$ZPICS/qemu-boot.log" 2>&1 || true
  grep -iE 'KILROY|GROK|PASS|FAIL|field' "$ZPICS/qemu-boot.log" 2>/dev/null | tail -15 >"$ZPICS/qemu-boot-summary.txt" || true
else
  log "WARN: QEMU path missing bzImage or grok-boot-qemu.sh"
fi

log "=== receipt ==="
"$PY" - <<PY > "$ZPICS/boot-qemu-receipt.json"
import json, pathlib, time
Z = pathlib.Path("$ZPICS")
surfaces = [l.strip() for l in (Z/"surface-checks.txt").read_text().splitlines() if l.strip()] if (Z/"surface-checks.txt").is_file() else []
shots = json.loads((Z/"screenshot-results.json").read_text()) if (Z/"screenshot-results.json").is_file() else []
ocr_ok = sum(1 for p in Z.glob("*-ocr.txt") if p.stat().st_size > 10)
receipt = {
    "schema": "boot-qemu-zpics-receipt/v1",
    "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "surfaces": surfaces,
    "screenshots": shots,
    "ocr_files": ocr_ok,
    "qemu_summary": (Z/"qemu-boot-summary.txt").read_text()[:500] if (Z/"qemu-boot-summary.txt").is_file() else "",
    "ok": all(s.startswith("200") for s in surfaces if s) and any(s.get("ok") for s in shots),
    "zpics": str(Z),
}
print(json.dumps(receipt, indent=2))
PY

log "DONE → $ZPICS"
exit 0
