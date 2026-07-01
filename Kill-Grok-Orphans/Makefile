# Kill Grok Orphans — built with Grok16 (g16) + cross GCC per platform manifest
GROK16_ROOT ?= /home/default/Desktop/SG/Grok16
G16         ?= $(GROK16_ROOT)/bin/g16
PREFIX      ?= /usr/local
VERSION     := $(shell cat VERSION 2>/dev/null || echo 1.1.0)

CFLAGS  := -std=gnu17 -O3 -Wall -Wextra -fno-pie -D_GNU_SOURCE -DKGO_VERSION=\"$(VERSION)\"
LDFLAGS := -no-pie -static
SRCS    := src/kgo.c src/kgo_scan.c src/kgo_config.c

CROSS_PREFIX_linux-gnu-i386       := i686-linux-gnu-
CROSS_PREFIX_linux-gnu-aarch64    := aarch64-linux-gnu-
CROSS_PREFIX_linux-gnu-arm        := arm-linux-gnueabihf-
CROSS_PREFIX_linux-gnu-riscv64    := riscv64-linux-gnu-

.PHONY: all clean install package cross

all: bin/kgo

bin/kgo: $(SRCS) src/kgo.h
	@mkdir -p bin
	$(G16) $(CFLAGS) -o $@ $(SRCS) $(LDFLAGS)

cross:
	@$(MAKE) _cross_one PLATFORM=linux-gnu-i386       OUT=dist/linux-gnu-i386/kgo
	@$(MAKE) _cross_one PLATFORM=linux-gnu-aarch64    OUT=dist/linux-gnu-aarch64/kgo
	@$(MAKE) _cross_one PLATFORM=linux-gnu-arm        OUT=dist/linux-gnu-arm/kgo
	@$(MAKE) _cross_one PLATFORM=linux-gnu-riscv64    OUT=dist/linux-gnu-riscv64/kgo

_cross_one:
	@mkdir -p $(dir $(OUT))
	@prefix="$(CROSS_PREFIX_$(PLATFORM))"; \
	if ! command -v "$${prefix}gcc" >/dev/null 2>&1; then \
	  echo "skip $(PLATFORM): $${prefix}gcc not installed"; exit 0; fi; \
	$${prefix}gcc $(CFLAGS) -o $(OUT) $(SRCS) $(LDFLAGS) && \
	strip $(OUT) 2>/dev/null || true && \
	echo "built $(OUT)"

install: bin/kgo
	install -d $(DESTDIR)$(PREFIX)/sbin
	install -d $(DESTDIR)/etc/kgo
	install -m 755 bin/kgo $(DESTDIR)$(PREFIX)/sbin/kgo
	install -m 644 data/kgo-patterns.json $(DESTDIR)/etc/kgo/kgo-patterns.json

package: all
	@mkdir -p dist
	tar -czf dist/kgo-$(VERSION)-linux-gnu-x86_64.tar.gz \
		bin/kgo data/kgo-patterns.json python/kgo_watchdog.py \
		packaging/linux/install.sh packaging/linux/kgo.service \
		README.md LICENSE VERSION data/kgo-platform-manifest.json

clean:
	rm -f src/*.o bin/kgo
	rm -rf dist