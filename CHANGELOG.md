# Changelog

All notable **NewLatest / NEXUS-Shield** orchestration changes. Historical `RELEASE-*.md` files remain in the repo archive.

**Version lines:** Hostess7 product = `1.0.0-beta` · AmmoOS = `2.0.0-beta4` · This changelog = `10.3.0-beta` internal. See [VERSION.md](VERSION.md).

## [10.3.2-beta] — 2026-06-30

### Hostess7 war-ready + Pages boot

- **`./Hostess7.sh boot`** — self-contained boot in Hostess7 (zac · stack-learn · on · alert-posture · web-start)
- **Never demo** — `HOSTESS7_LICENSE_MODE=war`; `is_demo()` always false; war-ready API posture
- **GitHub Pages** — boot manifest, Codespaces auto-boot, no canned demo replies
- **Master review** — VERSION.md, INSTALL.md, CI, biology seal, AML-only boot paths (10.3.1)

## [10.3.1-beta] — 2026-06-30

### Hostess7 master review fixes

- **VERSION.md** — single version matrix (Hostess7 `1.0.0-beta` vs AmmoOS `2.0.0-beta4` vs changelog `10.3.x`)
- **INSTALL.md** — release extract + git clone paths, prerequisite matrix
- **scripts/check-deps.sh** — dependency gate before wire/install
- **scripts/impl/field-vm-boot.sh** — KILROY + VM full stack bootstrap
- **scripts/README.md** — documents `scripts/` vs `scripts/impl/` two-tier layout
- **.github/workflows/ci.yml** — shellcheck, py_compile, biology-seal exempt, manifest dry-run
- **Biology seal exempt** — training/brain/cache paths never locked by executable seal
- **AML-only execution** — `lib/nexus-aml-exec.sh`, `field_vm_boot.aml`; no `AML_BUILD=0` / `AML_IMPL` bypass in stack boot paths

## [10.3.0-beta] — 2026-06-26

### NewLatest consolidation beta

- **Codecraft chamber** — `hostess7-codecraft.py`, doctrine/battery/testing-center JSON, panel `/api/hostess7/codecraft`, brain-guard seal
- **Adaptive IQ** — floor 100, scales with battery/truth/training/self-interaction (`hostess7-iq-doctrine.json`, truth-rating)
- **Voice** — American English female Piper HQ + spd-say fallback (`hostess7-voice.py`)
- **Self-interaction training** — GUI tracks via Training Viewer (`/api/train/self-interaction`, `/api/train/track`, `/api/train/iq`, `/api/voice/speak`)
- **NewLatest stack** — `SG_ROOT` = install root; `scripts/wire-stack.sh` symlinks Grok16, KILROY, Final_Eye/Ear, ZNEWOCR, etc.; `data/sg-canonical.json` updated
- **Hostess7 in-tree** — brain scripts under `Hostess7/`; training viewer at `hostess7-training-viewer/`
- **Queen operator surface** — source wired; build/vendor/cache gitignored
- **CI** — `.github/workflows/ci.yml` shellcheck + py_compile on push

## [10.0.1] — 2026-06-26

### Beta polish (Zachary reviewed)

- README trimmed: Well Wishes section, portable paths, panel quick-start
- GUI: personalized startup toast, Well Wishes banner, field.html warm landing
- Config: dedupe `NEXUS_I18N_DIR`, portable path comments (no operator-specific defaults)
- State hygiene: `.nexus-state/` gitignored; migration helper for repo-local state
- Integrity: manifest paths relative to install root; `nexus verify` on daemon boot
- CI: shellcheck + py_compile + editorial tests on push

## [10.0.0]

- Field plates rearchitecture, sense package meld, ZNEWOCR eye root, secure signal line