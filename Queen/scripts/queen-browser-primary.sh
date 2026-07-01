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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:Queen/scripts/queen-browser-primary.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Register Queen Browser as system default (xdg) — primary browser drop-in.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NEXUS_ROOT="$(cd "${ROOT}/.." && pwd)"
PORT="${QUEEN_WORLD_PORT:-9481}"
URL="http://127.0.0.1:${PORT}/world/browser.html"
DESKTOP="${NEXUS_ROOT}/.local-queen-browser.desktop"

mkdir -p "$(dirname "$DESKTOP")"
cat >"$DESKTOP" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Queen Browser
Comment=Queen sovereign web browser — secured imports · field gates
Exec=env NEXUS_INSTALL_ROOT=${NEXUS_ROOT} ${NEXUS_ROOT}/Queen/scripts/queen-py ${NEXUS_ROOT}/lib/queen-integrated-browser.py open
Icon=queen-browser
Terminal=false
Categories=Network;WebBrowser;
MimeType=text/html;text/xml;application/xhtml+xml;x-scheme-handler/http;x-scheme-handler/https;
StartupNotify=true
StartupWMClass=Queen
EOF
chmod 644 "$DESKTOP"

register_xdg() {
  command -v xdg-settings >/dev/null 2>&1 || return 1
  xdg-settings set default-web-browser "$(basename "$DESKTOP")" 2>/dev/null \
    || xdg-settings set default-web-browser "local-queen-browser.desktop" 2>/dev/null \
    || return 1
  xdg-mime default "$(basename "$DESKTOP")" text/html 2>/dev/null || true
  xdg-mime default "$(basename "$DESKTOP")" x-scheme-handler/http 2>/dev/null || true
  xdg-mime default "$(basename "$DESKTOP")" x-scheme-handler/https 2>/dev/null || true
  return 0
}

install_desktop() {
  local apps="${HOME}/.local/share/applications"
  mkdir -p "$apps"
  if [[ -f "${NEXUS_ROOT}/Queen/scripts/queen-icon-kit.py" ]]; then
    python3 "${NEXUS_ROOT}/Queen/scripts/queen-icon-kit.py" >/dev/null 2>&1 \
      || pythong "${NEXUS_ROOT}/Queen/scripts/queen-icon-kit.py" >/dev/null 2>&1 || true
  fi
  cp -f "$DESKTOP" "${apps}/queen-browser.desktop"
  chmod 644 "${apps}/queen-browser.desktop"
  command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$apps" 2>/dev/null || true
}

install_desktop
if register_xdg; then
  printf '{"ok":true,"primary":true,"url":"%s","desktop":"%s/.local/share/applications/queen-browser.desktop"}\n' "$URL" "$HOME"
else
  printf '{"ok":true,"primary":false,"url":"%s","hint":"Open Queen Browser from applications menu — xdg-settings unavailable"}\n' "$URL"
fi