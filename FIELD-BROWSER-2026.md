# Field Browser 2026 — Queen Browser Doctrine

**Nothing optional. Hold all gates. MP4. We want it ALL.**

Queen Browser is not a minimal privacy fork. It is the **complete web surface** with **every capability present** and **every egress held** by NEXUS.

## Gate mode: hold, never omit

| Wrong (rejected) | Right (Queen Browser) |
|------------------|---------------|
| DRM off by default | DRM **held** — gatekeeper scores every license server flow |
| WebRTC disabled | WebRTC **on** — camera/mic/data channels gated per tab |
| WebGPU optional pack | WebGPU **in-tree** — thermo-billed per context |
| MP4 codec optional | MP4 + H.264 + AAC **mandatory in-tree** |
| "Use Chrome for video" | Queen Browser ships full MSE + FFmpeg media path via Field Gecko engine |

Capabilities are not toggles that remove surface area. They are **gates** the operator holds via:

- Connection Gatekeeper (10-axis intent)
- Packet Field (per-navigation receipts)
- Honorability DB (site trust before egress)
- Fair Ad Guardian (first-party vs junk)
- Thermal Governor (per-tab energy honesty)
- Truth DNS (no foreign resolver shortcut)
- Sovereign Time (signed pulses, micron witness)

## Engines

| Track | Engine | When |
|-------|--------|------|
| **Ship now** | **Queen Browser** — hardened Field Gecko engine | 2026 operator desktop |
| **Millennium** | Ladybird / Servo | Independent engine, same gate doctrine |

No Chromium telemetry chew. Full compat: old web, WASM surrogates for dead plugins, inline PDF, SVG, MathML.

## Codec stack (MP4 mandatory)

```
Container: video/mp4, video/webm, audio/mp4, audio/mpeg, …
Video:     avc1/h264, hev1/h265, vp8, vp9, av01
Audio:     mp4a/aac, mp3, opus, vorbis, flac
Path:      MSE → Gecko media → FFmpeg (in-tree)
```

## NEXUS bindings

```bash
# Queen Browser defaults — all ON, hold all gates
NEXUS_FIELD_BROWSER_QUEEN=1
NEXUS_FIELD_BROWSER_HOLD_ALL_GATES=1
NEXUS_FIELD_BROWSER_MP4=1
NEXUS_FIELD_GECKO_ENGINE=queen-browser

# Launch
./Queen/field-gecko/bin/launch-field-gecko.sh https://zacharygeurts.github.io/Field_Primer/

# Panel slice
pythong lib/field-queen-browser.py json
```

## Files

| File | Role |
|------|------|
| `data/field-queen-gates-seed.json` | All gates, all held |
| `lib/field-queen-browser.py` | Panel + gate manifest |
| `Queen/field-gecko/bin/launch-field-gecko.sh` | Field Gecko launch |
| `lib/queen-browser-launch.sh` | Queen Browser launch entrypoint |
| `lib/fieldfox-native-bridge.py` | Queen Browser native messaging → gatekeeper |
| `lib/browser-awareness.py` | Active tab honorability |
| `lib/connection-gatekeeper.py` | Per-flow intent scoring |

## Year 3000

One sovereign stack: **Queen Browser + NEXUS + Truth DNS + sovereign DHCP/TIME + ELLIE Last Host.**

The web does not shrink. The gates do not open without receipts.