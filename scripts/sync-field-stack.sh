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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/sync-field-stack.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Sync SG/NewLatest with latest Final_Eye, Final_Ear, Grok16 — probe manifests, restart stack.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SG="$(cd "${ROOT}/.." && pwd)"
QUEEN="${QUEEN_ROOT:-${ROOT}/Queen}"
STATE="${NEXUS_STATE_DIR:-${QUEEN}/.nexus-state}"
PY="${QUEEN}/scripts/queen-py"

export SG_ROOT="${SG}"
export NEXUS_INSTALL_ROOT="${ROOT}"
export NEXUS_STATE_DIR="${STATE}"
export NEXUS_FIELD_STANDALONE=1
export QUEEN_ROOT="${QUEEN}"
export FINAL_EYE_ROOT="${FINAL_EYE_ROOT:-${SG}/Final_Eye}"
export FINAL_EAR_ROOT="${FINAL_EAR_ROOT:-${SG}/Final_Ear}"
export FINAL_EYE_ROOT="${FINAL_EYE_ROOT:-${ROOT}/Final_Eye}"

export WORLD_REDATA_ROOT="${WORLD_REDATA_ROOT:-${SG}/World_Redata}"
export HOSTESS7_ROOT="${HOSTESS7_ROOT:-${NEXUS_INSTALL_ROOT:-${SG}/NewLatest}/Hostess7}"
# shellcheck source=/dev/null
source "${ROOT}/lib/sg-paths.sh"
sg_paths_export_defaults
export PATH="${SG}/GrokPy/bin:${SG}/PythonG/bin:${GROK16_ROOT}/bin:${QUEEN}/scripts:${QUEEN}/bin:${PATH}"

# shellcheck source=/dev/null
source "${ROOT}/lib/nexus-common.sh"

read_version() {
  local f="$1"
  [[ -f "$f" ]] && tr -d '[:space:]' <"$f" || echo ""
}

echo "=== compiler stack (Grok16 + AmmoCode + Vulkan doctrine) ==="
if [[ -x "${ROOT}/scripts/integrate-compiler-stack.sh" ]]; then
  bash "${ROOT}/scripts/integrate-compiler-stack.sh" || echo "WARN: compiler stack integrate partial" >&2
elif [[ -x "${GROK16_ROOT}/scripts/grok16-integrate.sh" ]]; then
  bash "${GROK16_ROOT}/scripts/grok16-integrate.sh" integrate || echo "WARN: grok16 integrate partial" >&2
fi
if [[ -f "${ROOT}/lib/nexus-g16-recompile.py" ]]; then
  "${PY}" "${ROOT}/lib/nexus-g16-recompile.py" balance || echo "WARN: combinatronics balance partial" >&2
fi

echo "=== sync-field-stack — eye · ear · g16 ==="
echo "  NewLatest: ${ROOT}"
echo "  Queen:     ${QUEEN}"
echo "  Grok16:    ${GROK16_ROOT}"
echo "  Final_Eye: ${FINAL_EYE_ROOT} ($(read_version "${FINAL_EYE_ROOT}/VERSION"))"
echo "  Final_Ear: ${FINAL_EAR_ROOT} ($(read_version "${FINAL_EAR_ROOT}/VERSION"))"
echo "  ZOCR:      ${FINAL_EYE_ROOT}"
echo "  Redata:    ${WORLD_REDATA_ROOT}"
echo ""

mkdir -p "${STATE}" "${QUEEN}/data"

# Comfort / teach doctrine mirrors (Queen reads these; sources live in SG trees).
for pair in \
  "${FINAL_EYE_ROOT}/data/eye-teach-doctrine.json:${QUEEN}/data/queen-eye-teach-doctrine.json" \
  "${FINAL_EAR_ROOT}/data/ear-equipment-protection.json:${QUEEN}/data/queen-ear-equipment.json"; do
  src="${pair%%:*}"
  dst="${pair##*:}"
  if [[ -f "$src" ]]; then
    install -m 644 "$src" "$dst"
    echo "  synced $(basename "$dst")"
  fi
done

echo ""
echo "=== compiler_probe (g16 + ninja → g16-toolchain.json) ==="
"${PY}" "${QUEEN}/lib/queen-forge.py" run compiler_probe || {
  echo "WARN: compiler_probe failed — continuing" >&2
}

echo ""
echo "=== field-tools probe ==="
"${PY}" "${QUEEN}/lib/queen-field-tools.py" probe || true
"${PY}" "${QUEEN}/lib/queen-field-tools.py" teach || true

echo ""
echo "=== eye + ear forge verify ==="
"${PY}" "${QUEEN}/lib/queen-forge.py" run queen_eyeball || echo "WARN: queen_eyeball verify incomplete" >&2
"${PY}" "${QUEEN}/lib/queen-forge.py" run queen_earball || echo "WARN: queen_earball verify incomplete" >&2

echo ""
echo "=== update field-stack-manifest.json ==="
"${PY}" - <<'PY'
import json
import os
from datetime import datetime, timezone
from pathlib import Path

sg = Path(os.environ["SG_ROOT"])
root = Path(os.environ["NEXUS_INSTALL_ROOT"])
queen = Path(os.environ["QUEEN_ROOT"])
eye = Path(os.environ.get("FINAL_EYE_ROOT", str(sg / "Final_Eye")))
znew = Path(os.environ.get("Final_Eye_ROOT", os.environ.get("FINAL_EYE_ROOT", str(sg / "Final_Eye"))))
ear = Path(os.environ["FINAL_EAR_ROOT"])
zocr = Path(os.environ.get("FINAL_EYE_ROOT", str(znew)))
wrdt = Path(os.environ.get("WORLD_REDATA_ROOT", str(sg / "World_Redata")))
g16 = Path(os.environ["GROK16_ROOT"])

def ver(p: Path) -> str:
    f = p / "VERSION"
    return f.read_text(encoding="utf-8").strip() if f.is_file() else ""

manifest_path = root / "data" / "field-stack-manifest.json"
doc = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
doc.setdefault("layers", {})
doc["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
doc["layers"]["final_eye"] = {
    "root": str(znew.relative_to(sg.parent) if znew.is_relative_to(sg.parent) else znew),
    "lineage": str(eye.relative_to(sg.parent) if eye.is_relative_to(sg.parent) else eye),
    "version": ver(znew) or ver(eye) or "1.3.0",
    "codename": "heaven-hell-ops",
    "role": "Assist tenant — vision offense, entity weapons, IRTN mesh",
    "port": int(os.environ.get("ZOCR_PORT", os.environ.get("FINAL_EYE_PORT", "9479"))),
}
doc["layers"].pop("znewocr", None)
doc["layers"].pop("zocr", None)
doc["layers"]["final_ear"] = {
    "root": str(ear.relative_to(sg.parent) if ear.is_relative_to(sg.parent) else ear),
    "version": ver(ear) or "1.0.0",
    "codename": "auditus-gac1",
    "role": "Audio offense — truth filter, GAC1, eye-ear fusion",
    "bridge": "Queen/lib/queen-earball.py",
}
doc["layers"]["final_eye"]["version"] = ver(eye) or doc["layers"].get("final_eye", {}).get("version", "1.3.0")
doc["layers"]["final_eye"]["root"] = str(eye.relative_to(sg.parent) if eye.is_relative_to(sg.parent) else eye)
doc["layers"]["world_redata"] = {
    "root": str(wrdt.relative_to(sg.parent) if wrdt.is_relative_to(sg.parent) else wrdt),
    "port": int(os.environ.get("WORLD_REDATA_WEB_PORT", "9478")),
    "formats": ["WRDT1", "WRZC1", "ZAC7"],
    "role": "Lossless redata envelopes — drive converter, in-place snap",
}
doc["layers"]["sense_package"] = {
    "doctrine": "data/field-sense-package-doctrine.json",
    "meld": "lib/field-sense-package-meld.py",
    "api": "/api/sense-package",
    "role": "Unified meld + protect — eye, ear, zocr, redata, Hostess7 brain (witness read-only)",
}
obs_filter = sg / "OBS-FieldVoiceFilter"
if obs_filter.is_dir():
    doc["layers"]["obs_field_stack"] = {
        "root": str(obs_filter.relative_to(sg.parent) if obs_filter.is_relative_to(sg.parent) else obs_filter),
        "install": "OBS-FieldVoiceFilter/install.sh",
        "runtime_status": "data/field-obs-stack.json",
        "threat_ledger": "data/threat-ledger.jsonl",
        "posterity_doctrine": "data/field-security-posterity-doctrine.json",
        "api": "/api/obs-threat-posterity",
        "role": "OBS Scene Guard — one filter on scene; prune legacy filters; spiderweb down tree",
    }
h7 = sg / "Hostess7"
if h7.is_dir():
    doc["layers"]["hostess7"] = {
        "root": str(h7.relative_to(sg.parent) if h7.is_relative_to(sg.parent) else h7),
        "brain_witness": "lib/field-sense-package-meld.py",
        "brain_sync": "lib/field-brain-sync.sh",
        "role": "Forever Watchguard Angel — brain melded onto sense stack; read-only witness, never relocated",
    }
g16_ver_path = g16 / "data" / "grok16-version.json"
g16_ver = {}
if g16_ver_path.is_file():
    try:
        g16_ver = json.loads(g16_ver_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        pass
doc["layers"]["grok16"] = {
    "root": str(g16.relative_to(sg.parent) if g16.is_relative_to(sg.parent) else g16),
    "distro_version": g16_ver.get("distro_version", "1.0.0"),
    "tag": g16_ver.get("tag", "v1.0.0"),
    "g16_version": g16_ver.get("g16_version", "16.1.1"),
    "build": "g16 + Ninja (Queen/scripts/g16-build.sh)",
    "release_packages": "dist/grok16-1.0.0",
    "build_manifest": "data/grok16-build.json",
    "role": "Field compiler @ gnu++26 — queen-browser RTX",
}
doc["bridges"] = {
    **(doc.get("bridges") or {}),
    "queen_earball": "Queen/lib/queen-earball.py",
    "queen_final_ear": "Queen/lib/queen_final_ear.py",
    "g16_build": "Queen/scripts/g16-build.sh",
}
manifest_path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
print(f"  wrote {manifest_path}")
PY

canonical="${ROOT}/data/sg-canonical.json"
if [[ -f "$canonical" ]]; then
  "${PY}" - <<'PY'
import json, os
from datetime import datetime, timezone
from pathlib import Path
p = Path(os.environ["NEXUS_INSTALL_ROOT"]) / "data" / "sg-canonical.json"
doc = json.loads(p.read_text(encoding="utf-8"))
doc["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
doc.setdefault("stack", {})
doc["stack"]["final_eye"] = "Final_Eye"
doc["stack"]["final_ear"] = "Final_Ear"
doc["stack"]["final_eye"] = "Final_Eye"
doc["stack"]["world_redata"] = "World_Redata"
doc.setdefault("launch", {})
doc["launch"]["g16_build"] = "NewLatest/Queen/scripts/g16-build.sh"
doc["launch"]["field_stack"] = "NewLatest/scripts/start-field-stack.sh"
p.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
print(f"  wrote {p}")
PY
fi

echo ""
echo "=== OBS Field Voice Filter (sense lane) ==="
OBS_FILTER="${SG}/OBS-FieldVoiceFilter"
if [[ -d "${OBS_FILTER}" && -x "${OBS_FILTER}/install.sh" ]]; then
  bash "${OBS_FILTER}/install.sh"
  echo "  installed obs-field-voice-filter"
else
  echo "WARN: OBS-FieldVoiceFilter missing — skip" >&2
fi

echo ""
echo "=== OBS threat posterity bridge ==="
"${PY}" "${ROOT}/lib/obs-threat-posterity-bridge.py" sync || echo "WARN: obs threat posterity bridge incomplete" >&2

echo ""
echo "=== sense package meld ==="
"${PY}" "${ROOT}/lib/field-sense-package-meld.py" meld || echo "WARN: sense package meld incomplete" >&2

echo ""
echo "=== restart field stack ==="
# Stop stale RTX browser so restart picks fresh binary when build lands.
pkill -f "${QUEEN}/build/rtx/bin/Linux/queen-browser" 2>/dev/null || true
sleep 0.5

exec "${ROOT}/scripts/start-field-stack.sh"