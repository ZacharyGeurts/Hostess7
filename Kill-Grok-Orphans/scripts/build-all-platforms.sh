#!/usr/bin/env bash
# Build Kill Grok Orphans for every Grok16 host OS target (native Linux + cross + Python bundles)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GROK16_ROOT="${GROK16_ROOT:-$(cd "${ROOT}/../Grok16" && pwd)}"
VERSION="$(tr -d '\n' < "${ROOT}/VERSION")"
DIST="${ROOT}/dist"
STAGE="${DIST}/stage"

log() { printf '[%s] kgo-build %s\n' "$(date +%H:%M:%S)" "$*"; }

rm -rf "${DIST}"
mkdir -p "${STAGE}"

log "native linux-gnu-x86_64 (Grok16 g16)"
export GROK16_ROOT
make -C "${ROOT}" clean bin/kgo
strip "${ROOT}/bin/kgo" 2>/dev/null || true

log "cross Linux ELF targets"
make -C "${ROOT}" cross || true

pack_linux() {
  local id="$1"
  local bin="${ROOT}/bin/kgo"
  if [[ "$id" != "linux-gnu-x86_64" ]]; then
    bin="${ROOT}/dist/${id}/kgo"
    [[ -x "$bin" ]] || { log "skip package ${id} (binary missing)"; return 0; }
  fi
  local out="${DIST}/kgo-${VERSION}-${id}.tar.gz"
  local tmp="${STAGE}/${id}"
  rm -rf "$tmp"
  mkdir -p "$tmp/packaging/linux"
  install -m 755 "$bin" "$tmp/kgo"
  cp "${ROOT}/data/kgo-patterns.json" "$tmp/"
  cp "${ROOT}/python/kgo_watchdog.py" "$tmp/"
  cp "${ROOT}/packaging/linux/install.sh" "$tmp/packaging/linux/"
  cp "${ROOT}/packaging/linux/kgo.service" "$tmp/packaging/linux/"
  cp "${ROOT}/README.md" "${ROOT}/LICENSE" "${ROOT}/VERSION" "$tmp/"
  cp "${ROOT}/data/kgo-platform-manifest.json" "$tmp/"
  tar -czf "$out" -C "$tmp" .
  log "packed ${out}"
}

for id in linux-gnu-x86_64 linux-gnu-i386 linux-gnu-aarch64 linux-gnu-arm linux-gnu-riscv64; do
  pack_linux "$id"
done

log "darwin-universal (Python watchdog + launchd)"
darwin="${STAGE}/darwin-universal"
rm -rf "$darwin"
mkdir -p "$darwin/packaging/macos"
cp "${ROOT}/python/kgo_watchdog.py" "$darwin/"
cp "${ROOT}/data/kgo-patterns.json" "$darwin/"
cp "${ROOT}/packaging/macos/install.sh" "$darwin/packaging/macos/"
cp "${ROOT}/packaging/macos/com.grok.killorphans.plist" "$darwin/packaging/macos/"
cp "${ROOT}/requirements.txt" "${ROOT}/README.md" "${ROOT}/LICENSE" "${ROOT}/VERSION" "$darwin/"
tar -czf "${DIST}/kgo-${VERSION}-darwin-universal.tar.gz" -C "$darwin" .
log "packed kgo-${VERSION}-darwin-universal.tar.gz"

log "windows-x86_64 (Python watchdog + Scheduled Task)"
win="${STAGE}/windows-x86_64"
rm -rf "$win"
mkdir -p "$win/packaging/windows"
cp "${ROOT}/python/kgo_watchdog.py" "$win/"
cp "${ROOT}/data/kgo-patterns.json" "$win/"
cp "${ROOT}/packaging/windows/Install-KGO.ps1" "$win/packaging/windows/"
cp "${ROOT}/packaging/windows/Start-KGO.ps1" "$win/packaging/windows/" 2>/dev/null || true
cp "${ROOT}/requirements.txt" "${ROOT}/README.md" "${ROOT}/LICENSE" "${ROOT}/VERSION" "$win/"
(
  cd "$win"
  zip -qr "${DIST}/kgo-${VERSION}-windows-x86_64.zip" .
)
log "packed kgo-${VERSION}-windows-x86_64.zip"

log "manifest"
ls -lh "${DIST}"/kgo-"${VERSION}"* > "${DIST}/kgo-${VERSION}-MANIFEST.txt"
cat "${DIST}/kgo-${VERSION}-MANIFEST.txt"
log "done — ${DIST}"