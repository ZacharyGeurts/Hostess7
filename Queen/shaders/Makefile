# Queen Browser — SPIR-V compshader build (same toolchain as AMOURANTHRTX)
PROJECT_ROOT := $(abspath ..)
GLSLC     ?= glslc
SPIRV_VAL ?= spirv-val
SPIRV_ENV := --target-spv=spv1.6 --target-env=vulkan1.4
OUT       := $(PROJECT_ROOT)/assets/shaders/compute
SRCS      := $(wildcard compute/*.comp)
OUTS      := $(patsubst compute/%.comp,$(OUT)/%.spv,$(SRCS))

.PHONY: all clean
all: $(OUTS)
	@echo "queen-shaders: $(words $(OUTS)) modules"

$(OUT)/%.spv: compute/%.comp
	@mkdir -p $(OUT)
	@echo "glslc: $<"
	$(GLSLC) -g -O0 $(SPIRV_ENV) -fshader-stage=comp "$<" -o "$@"
	$(SPIRV_VAL) --target-env vulkan1.4 "$@" 2>/dev/null || true

clean:
	rm -f $(OUT)/*.spv