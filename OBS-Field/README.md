# OBS-Field

Sovereign local capture for AmmoOS — g16 `field_opt` build, no cloud login, portable config, readable UI, NVENC when RTX is present.

## Panel

http://127.0.0.1:9477/field-obs

## CLI

```bash
NEXUS_INSTALL_ROOT=NewLatest pythong NewLatest/lib/field-obs.py json
NEXUS_INSTALL_ROOT=NewLatest pythong NewLatest/lib/field-obs.py launch
NEXUS_INSTALL_ROOT=NewLatest pythong NewLatest/lib/field-obs.py record
NEXUS_INSTALL_ROOT=NewLatest pythong NewLatest/lib/field-obs.py us
NEXUS_INSTALL_ROOT=NewLatest pythong NewLatest/lib/field-obs.py build
```

## g16 build

```bash
./forge/clone-upstream.sh
./build-field-obs.sh
```

Prefers `prefix/bin/obs` (g16-built); falls back to system `obs` when configure is on hold.

## Hardening

- Portable config under `NEXUS_STATE_DIR/field-obs-portable/`
- Auto-updates off · bundled plugins only · WebSocket off by default
- Recordings land in `field-obs-portable/recordings/`
- Profile **Field** · scene collection **Field-Queen**

## Toolchain

- `cmake/g16-field-obs.cmake` — AmmoOS overlay
- `data/g16-field-obs-toolchain.json` — g16 probe manifest
- `Grok16/cmake/grok16-toolchain.cmake` — compiler toolchain