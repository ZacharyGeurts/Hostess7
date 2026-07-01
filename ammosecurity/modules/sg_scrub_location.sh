#!/usr/bin/env bash
# scrub_location — remove location metadata leaks from local SG tree + GitHub profile
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../lib/common.sh"

SG="$(cd "$AMMO_ROOT/.." && pwd)"

cmd_scrub_files() {
  ammo_log "scrub local SG files under $SG"
  perl -pi -e 's/,?\s*Gladstone Michigan//gi; s/Gladstone, Michigan, USA//gi; s/come to Michigan and //gi; s/come to Michigan//gi' \
    "$SG/README.md" \
    "$SG/submicro.md" \
    "$SG/AMOURANTHRTX-wiki/Home.md" \
    "$SG/AMOURANTHRTX-wiki/Memoriums.md" \
    "$SG/AMOURANTHRTX-wiki/scripts/gen_wiki_markdown.py" \
    "$SG/ammo/README.md" \
    "$SG/ammo/SG_DEEP_DIVE_BUSINESS_README.md" 2>/dev/null || true
  perl -pi -e 's/^- \*\*Location\*\*:.*\n//mg' "$SG/README.md" 2>/dev/null || true

  grep -rin 'gladstone\|michigan\|49837\|burntwood' "$SG" \
    --include='*.md' --include='*.py' --include='*.sh' --include='*.ps1' \
    2>/dev/null | grep -v 'toupper\|Upper \(UMB\)\|expand up\|expand down' \
    || ammo_log 'local tree clean'
}

cmd_scrub_github() {
  if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
    gh api -X PATCH user -f location='Singapore' \
      -f bio='God (1d) is both inside and outside of every dimension. All higher dimension contains both the lower dimensions (including 1) and the highest dimension (1). ¬0 ♠' \
      && ammo_log 'GitHub profile location -> Singapore'
    gh api user --jq '{login,location,bio}' 2>/dev/null || true
  else
    ammo_log 'gh not authenticated — skip profile scrub'
  fi
}

cmd_scrub_location() {
  cmd_scrub_files
  cmd_scrub_github
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  cmd_scrub_location "$@"
fi