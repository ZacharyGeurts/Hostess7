#!/usr/bin/env bash
# Pack VSYNC-Locker for every platform still in use (Grok16 native stub + Python guard).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VER="$(python3 -c "import json;from pathlib import Path;d=json.loads(Path('${ROOT}/data/field-vsync-locker-version.json').read_text());print(d['version'])")"
DIST="${ROOT}/dist"
STAGE_ROOT="${DIST}/vsync-locker-stage"
MANIFEST="${DIST}/vsync-locker-${VER}-platforms.json"

log() { printf '[%s] vsync-pack %s\n' "$(date +%H:%M:%S)" "$*"; }

mkdir -p "$DIST"
rm -rf "$STAGE_ROOT"
mkdir -p "$STAGE_ROOT"

log "Grok16 native launcher (linux-gnu-x86_64)"
if [[ -d "${ROOT}/Grok16" ]]; then
  export GROK16_ROOT="${ROOT}/Grok16"
elif [[ -d "${ROOT}/../Grok16" ]]; then
  export GROK16_ROOT="$(cd "${ROOT}/../Grok16" && pwd)"
fi
make -C "${ROOT}/packaging/vsync-locker/native" all 2>/dev/null || log "WARN native stub build partial"
make -C "${ROOT}/packaging/vsync-locker/native" cross 2>/dev/null || log "WARN cross stubs partial"

stage_core() {
  local dest="$1"
  mkdir -p "${dest}/lib" "${dest}/data" "${dest}/panel" "${dest}/packaging"
  install -m 644 "${ROOT}/lib/field-vsync-locker.py" "${dest}/lib/"
  install -m 755 "${ROOT}/lib/field-vsync-locker-launch.sh" "${dest}/lib/"
  install -m 755 "${ROOT}/lib/field-vsync-locker-guard.sh" "${dest}/lib/"
  [[ -f "${ROOT}/lib/hardware_wire_registry.py" ]] && \
    install -m 644 "${ROOT}/lib/hardware_wire_registry.py" "${dest}/lib/"
  install -m 644 "${ROOT}/data/field-vsync-locker-doctrine.json" "${dest}/data/"
  install -m 644 "${ROOT}/data/field-vsync-locker-version.json" "${dest}/data/"
  install -m 644 "${ROOT}/data/field-vsync-locker-platform-release.json" "${dest}/data/"
  cp -a "${ROOT}/packaging/vsync-locker" "${dest}/packaging/"
  cp -a "${ROOT}/library/dewey/000-computer-science/ammolang/vsync_locker.aml" "${dest}/vsync_locker.aml" 2>/dev/null || true
  sed "s|__INSTALL_ROOT__|${dest}|g" "${ROOT}/panel/field-vsync-locker.desktop" > "${dest}/panel/field-vsync-locker.desktop"
  printf '%s\n' "$VER" > "${dest}/VERSION"
  cat > "${dest}/README.md" <<EOF
# VSYNC-Locker ${VER}

Sovereign display timing — lock, drift, patrol, KILL trespassers.

\`\`\`bash
# Linux
sudo packaging/vsync-locker/linux/install.sh

# macOS
packaging/vsync-locker/macos/install.sh

# Windows (PowerShell)
./packaging/vsync-locker/windows/Install-VSYNSLocker.ps1
\`\`\`

Double-click **VSYNC Locker** desktop icon after install — background guard stays on patrol.
EOF
}

pack_linux() {
  local id="$1"
  local tmp="${STAGE_ROOT}/${id}"
  stage_core "$tmp"
  mkdir -p "${tmp}/bin"
  local stub=""
  if [[ "$id" == "linux-gnu-x86_64" && -x "${ROOT}/packaging/vsync-locker/native/bin/vsync-launch" ]]; then
    stub="${ROOT}/packaging/vsync-locker/native/bin/vsync-launch"
  elif [[ -x "${ROOT}/packaging/vsync-locker/native/dist-bin/${id}/vsync-launch" ]]; then
    stub="${ROOT}/packaging/vsync-locker/native/dist-bin/${id}/vsync-launch"
  fi
  [[ -n "$stub" ]] && install -m 755 "$stub" "${tmp}/bin/vsync-launch"
  local out="${DIST}/vsync-locker-${VER}-${id}.tar.gz"
  tar -czf "$out" -C "$tmp" .
  log "packed ${out}"
}

pack_tar() {
  local id="$1"
  local tmp="${STAGE_ROOT}/${id}"
  stage_core "$tmp"
  local out="${DIST}/vsync-locker-${VER}-${id}.tar.gz"
  tar -czf "$out" -C "$tmp" .
  log "packed ${out}"
}

pack_zip() {
  local id="$1"
  local tmp="${STAGE_ROOT}/${id}"
  stage_core "$tmp"
  local out="${DIST}/vsync-locker-${VER}-${id}.zip"
  ( cd "$tmp" && zip -qr "$out" . )
  log "packed ${out}"
}

for id in linux-gnu-x86_64 linux-gnu-aarch64 linux-gnu-arm linux-gnu-riscv64 linux-gnu-i386; do
  pack_linux "$id"
done
for id in darwin-aarch64 darwin-x86_64 freebsd-amd64 android-aarch64; do
  pack_tar "$id"
done
pack_zip windows-x86_64

cp "${ROOT}/data/field-vsync-locker-platform-release.json" "$MANIFEST"
ls -lh "${DIST}"/vsync-locker-"${VER}"-* > "${DIST}/vsync-locker-${VER}-MANIFEST.txt" 2>/dev/null || true
log "done — ${DIST}/vsync-locker-${VER}-*"