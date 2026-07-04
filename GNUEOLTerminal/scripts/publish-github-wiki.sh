#!/usr/bin/env bash
# Publish GNUEOLTerminal/wiki/*.md → github.com/ZacharyGeurts/GNUEOLTerminal/wiki
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NL="$(cd "${ROOT}/.." && pwd)"
WIKI_SRC="${ROOT}/wiki"
STAGE="${ROOT}/.wiki-github-stage"
WIKI_REPO="${WIKI_REPO:-${NL}/.wiki-gnueol-publish}"
WIKI_REMOTE="${WIKI_REMOTE:-git@github.com:ZacharyGeurts/GNUEOLTerminal.wiki.git}"
REPO="${GNUEOL_GITHUB_REPO:-ZacharyGeurts/GNUEOLTerminal}"
H7_SECURE="${NL}/Hostess7/scripts/hostess7_secure_git.py"
VER="$(cat "${ROOT}/VERSION" 2>/dev/null | tr -d '\n' || echo unknown)"
PY="${PYTHON:-python3}"

log() { printf '[gnueol-github-wiki] %s\n' "$*"; }

[[ -d "$WIKI_SRC" ]] || { log "missing ${WIKI_SRC}"; exit 1; }

# Ensure forge ran so wiki/*.md is current.
if [[ -f "${ROOT}/scripts/forge-gnu-wiki-manual.py" ]]; then
  "$PY" "${ROOT}/scripts/forge-gnu-wiki-manual.py" >/dev/null 2>&1 || true
fi

rm -rf "$STAGE"
mkdir -p "$STAGE"

# Stage pages — GitHub wiki uses Home.md (not index.md).
while IFS= read -r -d '' f; do
  base="$(basename "$f")"
  dest="$base"
  if [[ "$base" == "index.md" ]]; then
    dest="Home.md"
  fi
  # GitHub wiki internal links: drop .md suffix.
  sed -E 's/\]\(([^)]+)\.md\)/](\1)/g' "$f" > "${STAGE}/${dest}"
done < <(find "$WIKI_SRC" -maxdepth 1 -name '*.md' -print0)

# Sidebar for native wiki UI.
cat > "${STAGE}/_Sidebar.md" <<'SIDE'
**[Home](Home)**

### Start here
- [GNU EOL Terminal — Full Operator Manual](eol-terminal-full-manual)
- [GNU Technical Manual](gnu-technical-manual)
- [Field Tech commands](field-tech)

### Classic GNU
- [Emacs](emacs) · [Bash](bash) · [Coreutils](coreutils)
- [SSH](ssh) · [GPL FAQ](gpl)

### Production
- [RTX panels](rtx-panels) · [Entropy grade](entropy-grade)
- [Sovereign time](sovereign-time) · [DOS 4.0 modules](dos40-modules)

**[Pages wiki](https://zacharygeurts.github.io/GNUEOLTerminal/wiki/)** · **[Textbook](https://zacharygeurts.github.io/GNUEOLTerminal/)**
SIDE

gh repo edit "$REPO" --enable-wiki 2>/dev/null || true

if [[ ! -d "${WIKI_REPO}/.git" ]]; then
  rm -rf "$WIKI_REPO"
  if git ls-remote --heads "$WIKI_REMOTE" master 2>/dev/null | grep -q master; then
    git clone -b master "$WIKI_REMOTE" "$WIKI_REPO"
  elif git ls-remote --heads "$WIKI_REMOTE" main 2>/dev/null | grep -q main; then
    git clone -b main "$WIKI_REMOTE" "$WIKI_REPO"
  else
    mkdir -p "$WIKI_REPO"
    git -C "$WIKI_REPO" init -b master
    git -C "$WIKI_REPO" remote add origin "$WIKI_REMOTE"
  fi
fi

rsync -a --delete --exclude='.git' "${STAGE}/" "${WIKI_REPO}/"

count="$(find "$WIKI_REPO" -maxdepth 1 -name '*.md' | wc -l | tr -d ' ')"
if [[ "$count" -lt 10 ]]; then
  log "WARN: only ${count} wiki pages staged — expected 30+"
fi

git -C "$WIKI_REPO" add -A
if git -C "$WIKI_REPO" diff --cached --quiet; then
  log "GitHub wiki already up to date (${count} pages)"
  exit 0
fi

git -C "$WIKI_REPO" -c user.email="gzac5314@users.noreply.github.com" -c user.name="ZacharyGeurts" \
  commit -m "wiki: GNUEOLTerminal ${VER} — full operator manual + classic schooler (${count} pages)"

_pushed=0
if [[ -f "$H7_SECURE" ]] && "$PY" "$H7_SECURE" verify >/dev/null 2>&1; then
  if "$PY" "$H7_SECURE" push "$WIKI_REPO" --branch master --remote "$WIKI_REMOTE" --force 2>/dev/null \
    || "$PY" "$H7_SECURE" push "$WIKI_REPO" --branch main --remote "$WIKI_REMOTE" --force 2>/dev/null; then
    _pushed=1
  else
    log "secure push failed — falling back to direct git push"
  fi
fi
if [[ "$_pushed" -eq 0 ]]; then
  git -C "$WIKI_REPO" push origin master 2>/dev/null \
    || git -C "$WIKI_REPO" push origin main 2>/dev/null \
    || git -C "$WIKI_REPO" push -u origin HEAD
fi

log "published ${count} pages → https://github.com/${REPO}/wiki"
log "full manual → https://github.com/${REPO}/wiki/eol-terminal-full-manual"