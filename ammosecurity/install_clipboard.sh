#!/usr/bin/env bash
set -euo pipefail
AMMO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCLIP="${AMMO_ROOT}/secure_clipboard.sh"
MARK="# >>> ammosecurity secure-clipboard"
MARK_END="# <<< ammosecurity secure-clipboard"

chmod +x "${SCLIP}"

echo "== clipboard backends =="
if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update -qq
  if [[ -n "${WAYLAND_DISPLAY:-}" ]] || [[ "${XDG_SESSION_TYPE:-}" == "wayland" ]]; then
    sudo apt-get install -y openssl wl-clipboard
  else
    sudo apt-get install -y openssl xclip
  fi
fi

bash "${SCLIP}" init
bash "${SCLIP}" disable-managers

BLOCK="
${MARK}
alias sclip='bash ${SCLIP}'
alias scopy='sclip copy'
alias spaste='sclip paste'
alias sclear='sclip clear'
${MARK_END}
"

for rc in "${HOME}/.bashrc" "${HOME}/.profile"; do
  [[ -f "${rc}" ]] || touch "${rc}"
  if grep -qF "${MARK}" "${rc}" 2>/dev/null; then
    echo "aliases already in ${rc}"
  else
    printf '%s\n' "${BLOCK}" >> "${rc}"
    echo "appended aliases to ${rc}"
  fi
done

echo "Done. Reload: source ~/.bashrc"