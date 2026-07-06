# Field Grok — secure operator CLI binary (Grok16 g16)
GROK16_ROOT ?= /home/default/Desktop/SG/NewLatest/Grok16
G16         ?= $(GROK16_ROOT)/bin/g16
OUT         ?= ../../lib/bin/field-grok
VERSION     := 1.0.0

CFLAGS  := -std=gnu17 -O3 -Wall -Wextra -fno-pie -D_GNU_SOURCE -DFIELD_GROK_VERSION=\"$(VERSION)\"
LDFLAGS := -no-pie -static

.PHONY: all clean install

all: $(OUT)

$(OUT): field-grok.c
	@mkdir -p $(dir $(OUT))
	$(G16) $(CFLAGS) -o $(OUT) field-grok.c $(LDFLAGS)
	@chmod 755 $(OUT)
	@echo "built $(OUT)"

install: all
	@true

clean:
	rm -f $(OUT)