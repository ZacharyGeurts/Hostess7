# AmmoOS 2.0.0-beta4 — WATCHGUARD

**Tag:** `v2.0.0-beta4` · **Repo:** [ZacharyGeurts/AmmoOS](https://github.com/ZacharyGeurts/AmmoOS) · **Manual:** [zacharygeurts.github.io/AmmoOS](https://zacharygeurts.github.io/AmmoOS/) · **Prior:** [v2.0.0-beta3.1](https://github.com/ZacharyGeurts/AmmoOS/releases/tag/v2.0.0-beta3.1)

## Beta 4 highlights

- **Final Eye → Hostess 7 seal** — OCR and vision dispatch require H7 handshake; direct lanes blocked
- **Component seal** — 61 stack components bound (body, sense, training, system, shell-owned desktop/browser/canvas/terminal)
- **Queen vision lanes closed** — `look` / `watch` / `observe` / `smoke` route through `hostess7-ocr-control`
- **Brain guard verified** — `MANIFEST.sha256` resealed; guard score 1.0 after truth review
- **Queen code seal** — 77 lib + forge files sealed; Ironclad field sanity cycle ok
- **Command deck live** — `hostess7-command-panel.json` rebuilt; panel cold-cache fast path
- **Canvas bridge** — no direct `final_eye_look` fallback without H7 stamp
- **Thermal Earth OCR** — stale session image path removed; H7 lane only

## Install

```bash
git clone https://github.com/ZacharyGeurts/AmmoOS.git
cd AmmoOS
git checkout v2.0.0-beta4
./scripts/wire-stack.sh
sudo ./install-all.sh
```

Or upgrade from beta3.1: `git pull && git checkout v2.0.0-beta4`

## Ship lane

```bash
./scripts/ammoos-release.sh --version 2.0.0-beta4 --push
```

## Pairings

| Component | Version |
|-----------|---------|
| Grok16 | 5.2.0 |
| KILROY | 1.0.0 Taco |
| Hostess 7 | supreme authority + component seal |