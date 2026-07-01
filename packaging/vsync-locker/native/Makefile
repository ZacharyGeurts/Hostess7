GROK16_ROOT ?= ../../../Grok16
G16         ?= $(GROK16_ROOT)/bin/g16
VERSION     := $(shell python3 -c "import json;from pathlib import Path;p=Path('../../../data/field-vsync-locker-version.json');print(json.loads(p.read_text()).get('version','1.0.0'))" 2>/dev/null || echo 1.0.0)

CFLAGS  := -std=gnu17 -O2 -Wall -Wextra -fno-pie -D_GNU_SOURCE -DVSYNC_VERSION=\"$(VERSION)\"
LDFLAGS := -no-pie -static

CROSS_PREFIX_linux-gnu-i386     := i686-linux-gnu-
CROSS_PREFIX_linux-gnu-aarch64  := aarch64-linux-gnu-
CROSS_PREFIX_linux-gnu-arm      := arm-linux-gnueabihf-
CROSS_PREFIX_linux-gnu-riscv64  := riscv64-linux-gnu-

.PHONY: all clean cross

all: bin/vsync-launch

bin/vsync-launch: vsync-launch.c
	@mkdir -p bin
	@gcc $(CFLAGS) -o $@ $< $(LDFLAGS)

cross:
	@$(MAKE) _cross_one PLATFORM=linux-gnu-i386     OUT=../dist-bin/linux-gnu-i386/vsync-launch
	@$(MAKE) _cross_one PLATFORM=linux-gnu-aarch64  OUT=../dist-bin/linux-gnu-aarch64/vsync-launch
	@$(MAKE) _cross_one PLATFORM=linux-gnu-arm      OUT=../dist-bin/linux-gnu-arm/vsync-launch
	@$(MAKE) _cross_one PLATFORM=linux-gnu-riscv64  OUT=../dist-bin/linux-gnu-riscv64/vsync-launch

_cross_one:
	@mkdir -p $(dir $(OUT))
	@prefix="$(CROSS_PREFIX_$(PLATFORM))"; \
	if ! command -v "$${prefix}gcc" >/dev/null 2>&1; then \
	  echo "skip $(PLATFORM): $${prefix}gcc not installed"; exit 0; fi; \
	$${prefix}gcc $(CFLAGS) -o $(OUT) vsync-launch.c $(LDFLAGS) && \
	strip $(OUT) 2>/dev/null || true && \
	echo "built $(OUT)"

clean:
	rm -rf bin ../dist-bin