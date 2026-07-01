#!/usr/bin/env bash
# One-liner GitHub install — curl -fsSL …/install-remote.sh | bash
set -euo pipefail

REPO="${NEXUS_GITHUB_REPO:-ZacharyGeurts/NEXUS-Shield}"
STAGING="${NEXUS_STATE_DIR:-${TMPDIR:-/tmp}/nexus-nxf}/remote-install"
mkdir -p "$STAGING"

echo "NEXUS-Shield remote NXF install (${REPO})…"

NXF="${STAGING}/latest.nxf"
for url in \
  "https://github.com/${REPO}/releases/latest/download/latest.nxf" \
  "https://raw.githubusercontent.com/${REPO}/main/nxf/latest.nxf"; do
  if curl -fsSL --retry 3 -o "$NXF" "$url" 2>/dev/null; then
    break
  fi
done

[[ -s "$NXF" ]] || { echo "Could not fetch latest.nxf from GitHub." >&2; exit 1; }

SOURCE_URL="$(python3 -c "import json; d=json.load(open('$NXF')); print(d['pack']['source']['url'])" 2>/dev/null || true)"
[[ -n "$SOURCE_URL" ]] || { echo "Invalid NXF manifest." >&2; exit 1; }

ARCHIVE="${STAGING}/source.tar.gz"
curl -fsSL --retry 3 -o "$ARCHIVE" "$SOURCE_URL"
EXTRACT="${STAGING}/tree"
rm -rf "$EXTRACT"
mkdir -p "$EXTRACT"
tar -xzf "$ARCHIVE" -C "$EXTRACT"
TREE="$(find "$EXTRACT" -maxdepth 2 -name install.sh -print -quit 2>/dev/null | xargs -r dirname)"
[[ -n "$TREE" && -f "${TREE}/install.sh" ]] || { echo "Source tree missing install.sh" >&2; exit 1; }

mkdir -p "${TREE}/nxf"
cp -f "$NXF" "${TREE}/nxf/latest.nxf"
cd "$TREE"
exec bash ./install.sh "$@"