#!/usr/bin/env bash
# Sync latest upstream GIMP into SG/GIMP (shallow pull if repo exists).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
GIMP="${GIMP_ROOT:-${ROOT}/GIMP}"
REMOTE="${GIMP_REMOTE:-https://gitlab.gnome.org/GNOME/gimp.git}"
BRANCH="${GIMP_BRANCH:-master}"

if [[ ! -d "${GIMP}/.git" ]]; then
  echo "Cloning GIMP → ${GIMP}"
  git clone --depth 1 --branch "${BRANCH}" "${REMOTE}" "${GIMP}"
else
  echo "Pulling latest GIMP @ ${GIMP}"
  git -C "${GIMP}" fetch --depth 1 origin "${BRANCH}" 2>/dev/null || git -C "${GIMP}" fetch origin
  git -C "${GIMP}" checkout "${BRANCH}" 2>/dev/null || true
  git -C "${GIMP}" pull --ff-only origin "${BRANCH}" 2>/dev/null || git -C "${GIMP}" pull --rebase || true
fi

REV="$(git -C "${GIMP}" rev-parse --short HEAD 2>/dev/null || echo unknown)"
VER="$(grep -m1 "version:" "${GIMP}/meson.build" 2>/dev/null | sed "s/.*'\([^']*\)'.*/\1/" || echo unknown)"
echo "{\"ok\":true,\"path\":\"${GIMP}\",\"rev\":\"${REV}\",\"upstream_version\":\"${VER}\"}"