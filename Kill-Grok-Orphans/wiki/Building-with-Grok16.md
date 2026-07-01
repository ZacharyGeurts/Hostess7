# Building with Grok16

The native Linux `kgo` binary is compiled with **Grok16** (`g16`), the sovereign C compiler from the [Grok16](https://github.com/ZacharyGeurts/Grok16) distribution.

## Prerequisites

- Grok16 bootstrapped at `GROK16_ROOT` with `bin/g16` available
- Linux x86_64 host

## Build

```bash
export GROK16_ROOT=/path/to/Grok16
cd Kill-Grok-Orphans
make
./bin/kgo -c data/kgo-patterns.json --once --dry-run
```

## Install

```bash
sudo make install
# or
sudo packaging/linux/install.sh
```

## Compiler flags

```
g16 -std=gnu17 -O2 -Wall -Wextra -D_GNU_SOURCE
```

## Source layout

| File | Role |
|------|------|
| `src/kgo.c` | Daemon main loop |
| `src/kgo_scan.c` | `/proc` scan + kill |
| `src/kgo_config.c` | JSON pattern loader |
| `src/kgo.h` | Shared header |

Cross-platform watchdog: `python/kgo_watchdog.py` (no Grok16 required).