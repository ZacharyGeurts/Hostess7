CXX ?= g++
ROOT := $(abspath ../..)
BIN := $(ROOT)/bin
CXXFLAGS := -std=c++17 -O2 -g0 -fstack-protector-strong -D_FORTIFY_SOURCE=2 -fPIE \
	-fno-exceptions -fno-rtti -Wall -Wextra -Wformat -Wformat-security -Werror=format-security
LDFLAGS := -pie -Wl,-z,relro,-z,now -Wl,-z,noexecstack -s
# field-curl needs dlopen for libssl
LDFLAGS_CURL := $(LDFLAGS) -ldl

# Prefer Grok16 g++16 field_opt when available
G16 := $(ROOT)/Grok16/bin/g++16
ifeq ($(wildcard $(G16)),)
  CXX ?= g++
else
  CXX ?= $(G16)
endif

FIELD_DEFS := -DFIELD_MESH=1 -DFIELD_ONE=1 -DHOSTESS7_AUTHORITY=1 \
	-DFIELD_NATIVE_SIGNALS=1 -DZERO_COST_MESH=1 -DNO_SIGTERM_NO_SIGKILL=1

.PHONY: all clean dig world-dns world-dhcp elevate stack-iso curl reap rollout ammolang c2chip fleet-mesh tools install-tools ironclad
all: $(BIN)/field-echo $(BIN)/field-chmod $(BIN)/field-dig $(BIN)/field-world-dns \
	$(BIN)/field-world-dhcp $(BIN)/field-elevate $(BIN)/field-stack-iso \
	$(BIN)/field-curl $(BIN)/field-reap $(BIN)/field-pgrep $(BIN)/field-rollout \
	$(BIN)/field-ammolang $(BIN)/field-nexus-c2-chip $(BIN)/field-nexus-c2-bank \
	$(BIN)/field-fleet-mesh \
	$(BIN)/field-dns-dhcp-h7-raid $(BIN)/field-antivirus $(BIN)/field-stack-hark \
	$(BIN)/field-ironclad-bsp $(BIN)/field-shell $(BIN)/field-compile-truth \
	$(BIN)/field-h7r-capacity-fleet $(BIN)/field-ammonet-cloud \
	$(BIN)/field-plane-chip $(BIN)/field-entry64-chip $(BIN)/field-all-chip \
	$(BIN)/field-x86-chip $(BIN)/field-init-chip $(BIN)/field-initramfs-chip \
	$(BIN)/field-internet2-plane $(BIN)/field-grok-identity-seal \
	$(BIN)/field-hostess7 $(BIN)/field-hostess7-stack-update \
	$(BIN)/field-ammoos $(BIN)/field-hdmi-audio $(BIN)/field-everyone

$(BIN):
	mkdir -p $(BIN) $(BIN)/untouchable $(ROOT)/Grok16/bin

$(BIN)/field-echo: field_echo.cpp | $(BIN)
	$(CXX) $(CXXFLAGS) -o $@ $< $(LDFLAGS)
	chmod 0555 $@
	cp -f $@ $(BIN)/untouchable/field-echo
	chmod 0555 $(BIN)/untouchable/field-echo

$(BIN)/field-chmod: field_chmod.cpp | $(BIN)
	$(CXX) $(CXXFLAGS) -o $@ $< $(LDFLAGS)
	chmod 0555 $@
	cp -f $@ $(BIN)/untouchable/field-chmod
	chmod 0555 $(BIN)/untouchable/field-chmod

$(BIN)/field-dig: field_dig.cpp | $(BIN)
	$(CXX) $(CXXFLAGS) $(FIELD_DEFS) -o $@ $< $(LDFLAGS)
	chmod 0555 $@
	cp -f $@ $(BIN)/untouchable/field-dig
	chmod 0555 $(BIN)/untouchable/field-dig
	cp -f $@ $(ROOT)/Grok16/bin/field-dig
	chmod 0555 $(ROOT)/Grok16/bin/field-dig

$(BIN)/field-world-dns: field_world_dns.cpp | $(BIN)
	$(CXX) $(CXXFLAGS) $(FIELD_DEFS) -o $@ $< $(LDFLAGS)
	chmod 0555 $@
	cp -f $@ $(BIN)/untouchable/field-world-dns
	chmod 0555 $(BIN)/untouchable/field-world-dns
	cp -f $@ $(ROOT)/Grok16/bin/field-world-dns
	chmod 0555 $(ROOT)/Grok16/bin/field-world-dns
	# field-dns is Field world-dns (never Python)
	cp -f $@ $(BIN)/field-dns
	chmod 0555 $(BIN)/field-dns
	cp -f $@ $(ROOT)/Grok16/bin/field-dns
	chmod 0555 $(ROOT)/Grok16/bin/field-dns

# field-world-dhcp — pure C++ UDP/67 · truthed MAC vendor OUI · no Python
$(BIN)/field-world-dhcp: field_world_dhcp.cpp field_mac_vendor_truth.hpp zero_cost_mesh.hpp | $(BIN)
	$(CXX) $(CXXFLAGS) $(FIELD_DEFS) -I. -o $@ field_world_dhcp.cpp $(LDFLAGS)
	chmod 0555 $@
	cp -f $@ $(BIN)/untouchable/field-world-dhcp
	chmod 0555 $(BIN)/untouchable/field-world-dhcp
	cp -f $@ $(ROOT)/Grok16/bin/field-world-dhcp
	chmod 0555 $(ROOT)/Grok16/bin/field-world-dhcp
	# field-dhcp is Field world-dhcp (never Python)
	cp -f $@ $(BIN)/field-dhcp
	chmod 0555 $(BIN)/field-dhcp
	cp -f $@ $(ROOT)/Grok16/bin/field-dhcp
	chmod 0555 $(ROOT)/Grok16/bin/field-dhcp

# field-elevate — pure C++ allowlist elevate plane · never shell · never Python
$(BIN)/field-elevate: field_elevate.cpp | $(BIN)
	$(CXX) $(CXXFLAGS) $(FIELD_DEFS) -o $@ $< $(LDFLAGS)
	chmod 0555 $@
	cp -f $@ $(BIN)/untouchable/field-elevate
	chmod 0555 $(BIN)/untouchable/field-elevate
	cp -f $@ $(ROOT)/Grok16/bin/field-elevate
	chmod 0555 $(ROOT)/Grok16/bin/field-elevate

$(BIN)/field-curl: field_curl.cpp | $(BIN)
	$(CXX) $(CXXFLAGS) $(FIELD_DEFS) -o $@ $< $(LDFLAGS_CURL)
	chmod 0555 $@
	cp -f $@ $(BIN)/untouchable/field-curl
	chmod 0555 $(BIN)/untouchable/field-curl
	cp -f $@ $(ROOT)/Grok16/bin/field-curl
	chmod 0555 $(ROOT)/Grok16/bin/field-curl

$(BIN)/field-reap: field_reap.cpp | $(BIN)
	$(CXX) $(CXXFLAGS) $(FIELD_DEFS) -o $@ $< $(LDFLAGS)
	chmod 0555 $@
	cp -f $@ $(BIN)/untouchable/field-reap
	chmod 0555 $(BIN)/untouchable/field-reap
	cp -f $@ $(ROOT)/Grok16/bin/field-reap
	chmod 0555 $(ROOT)/Grok16/bin/field-reap
	# field-pkill is a name alias path (same binary) — never system pkill
	cp -f $@ $(BIN)/field-pkill
	chmod 0555 $(BIN)/field-pkill
	cp -f $@ $(ROOT)/Grok16/bin/field-pkill
	chmod 0555 $(ROOT)/Grok16/bin/field-pkill

# field-pgrep — pure C++ /proc · never python · never host pgrep
$(BIN)/field-pgrep: field_pgrep.cpp | $(BIN)
	$(CXX) $(CXXFLAGS) $(FIELD_DEFS) -o $@ $< $(LDFLAGS)
	chmod 0555 $@
	cp -f $@ $(BIN)/untouchable/field-pgrep
	chmod 0555 $(BIN)/untouchable/field-pgrep
	cp -f $@ $(ROOT)/Grok16/bin/field-pgrep
	chmod 0555 $(ROOT)/Grok16/bin/field-pgrep

# field-rollout — pure C++ IRQ/DMA-attached NEXUS C2 (replaces bash/python scripts)
$(BIN)/field-rollout: field_rollout.cpp | $(BIN)
	$(CXX) $(CXXFLAGS) $(FIELD_DEFS) -o $@ $< $(LDFLAGS)
	chmod 0555 $@
	cp -f $@ $(BIN)/untouchable/field-rollout
	chmod 0555 $(BIN)/untouchable/field-rollout
	cp -f $@ $(ROOT)/Grok16/bin/field-rollout
	chmod 0555 $(ROOT)/Grok16/bin/field-rollout

# field-ammolang — secure AmmoLang + python→AmmoLang intercept (CPython obsolete)
$(BIN)/field-ammolang: field_ammolang.cpp | $(BIN)
	$(CXX) $(CXXFLAGS) $(FIELD_DEFS) -o $@ $< $(LDFLAGS)
	chmod 0555 $@
	cp -f $@ $(BIN)/untouchable/field-ammolang
	chmod 0555 $(BIN)/untouchable/field-ammolang
	cp -f $@ $(ROOT)/Grok16/bin/field-ammolang
	chmod 0555 $(ROOT)/Grok16/bin/field-ammolang
	# Python obsolete — every python* name is field-ammolang
	ln -sfn field-ammolang $(BIN)/python
	ln -sfn field-ammolang $(BIN)/python3
	ln -sfn field-ammolang $(BIN)/pythong
	ln -sfn field-ammolang $(BIN)/gpy-16
	chmod 0555 $(BIN)/python $(BIN)/python3 $(BIN)/pythong $(BIN)/gpy-16 2>/dev/null || true

# field-nexus-c2-chip — NEXUS C2 custom CHIP for any OS / any system
$(BIN)/field-nexus-c2-chip: field_nexus_c2_chip.cpp | $(BIN)
	$(CXX) $(CXXFLAGS) $(FIELD_DEFS) -o $@ $< $(LDFLAGS)
	chmod 0555 $@
	cp -f $@ $(BIN)/untouchable/field-nexus-c2-chip
	chmod 0555 $(BIN)/untouchable/field-nexus-c2-chip
	cp -f $@ $(ROOT)/Grok16/bin/field-nexus-c2-chip
	chmod 0555 $(ROOT)/Grok16/bin/field-nexus-c2-chip
	ln -sfn field-nexus-c2-chip $(BIN)/kilroy-ipxe-nexus-c2-stack
	chmod 0555 $(BIN)/kilroy-ipxe-nexus-c2-stack 2>/dev/null || true

# field-nexus-c2-bank — harden C2 · 10-node 125k bank · plate·meld·CHIPs · DNS/DHCP
$(BIN)/field-nexus-c2-bank: field_nexus_c2_bank.cpp | $(BIN)
	$(CXX) $(CXXFLAGS) $(FIELD_DEFS) -o $@ $< $(LDFLAGS)
	chmod 0555 $@
	cp -f $@ $(BIN)/untouchable/field-nexus-c2-bank
	chmod 0555 $(BIN)/untouchable/field-nexus-c2-bank
	cp -f $@ $(ROOT)/Grok16/bin/field-nexus-c2-bank
	chmod 0555 $(ROOT)/Grok16/bin/field-nexus-c2-bank

# field-fleet-mesh — 125k WORLD DNS/DHCP · Field 100x over conventional · autopilot
$(BIN)/field-fleet-mesh: field_fleet_mesh.cpp | $(BIN)
	$(CXX) $(CXXFLAGS) $(FIELD_DEFS) -o $@ $< $(LDFLAGS)
	chmod 0555 $@
	cp -f $@ $(BIN)/untouchable/field-fleet-mesh
	chmod 0555 $(BIN)/untouchable/field-fleet-mesh
	cp -f $@ $(ROOT)/Grok16/bin/field-fleet-mesh
	chmod 0555 $(ROOT)/Grok16/bin/field-fleet-mesh
	# Replace obsolete bash→python fleet wrappers with native ELF (or symlinks)
	for name in field-fleet-faster-servers field-fleet-live field-fleet-125k-update-safe \
		field-fleet-expand-125k field-fleet-planetary-dns-dhcp \
		field-botnet-full-dns-dhcp-authority field-botnet-dns-dhcp \
		field-fleet-country-flags; do \
		ln -sfn field-fleet-mesh $(BIN)/$$name; \
		chmod 0555 $(BIN)/$$name 2>/dev/null || true; \
		ln -sfn field-fleet-mesh $(BIN)/untouchable/$$name 2>/dev/null || true; \
		ln -sfn field-fleet-mesh $(ROOT)/Grok16/bin/$$name 2>/dev/null || true; \
	done

# field-shell — soft-kill immune Field shell (SIGTERM/SIGINT ignored = terrorist injection)
$(BIN)/field-shell: field_shell.cpp | $(BIN)
	$(CXX) $(CXXFLAGS) $(FIELD_DEFS) -o $@ $< $(LDFLAGS)
	chmod 0555 $@
	cp -f $@ $(BIN)/untouchable/field-shell
	chmod 0555 $(BIN)/untouchable/field-shell
	cp -f $@ $(ROOT)/Grok16/bin/field-shell
	chmod 0555 $(ROOT)/Grok16/bin/field-shell
	# Secure binaries only — replace bash wrappers
	ln -sfn field-shell $(BIN)/field-bash
	ln -sfn field-shell $(BIN)/field-secure-bash
	cp -f $@ $(ROOT)/Grok16/bin/field-bash
	cp -f $@ $(ROOT)/Grok16/bin/field-secure-bash
	chmod 0555 $(BIN)/field-bash $(BIN)/field-secure-bash 2>/dev/null || true

dig: $(BIN)/field-dig
world-dns: $(BIN)/field-world-dns
world-dhcp: $(BIN)/field-world-dhcp
elevate: $(BIN)/field-elevate
curl: $(BIN)/field-curl
reap: $(BIN)/field-reap
rollout: $(BIN)/field-rollout
ammolang: $(BIN)/field-ammolang
c2chip: $(BIN)/field-nexus-c2-chip
# field-dns-dhcp-h7-raid — sole DNS+DHCP · H7 RAID-0 across 125k · Ironclad BSP
$(BIN)/field-dns-dhcp-h7-raid: field_dns_dhcp_h7_raid.cpp | $(BIN)
	$(CXX) $(CXXFLAGS) $(FIELD_DEFS) -o $@ $< $(LDFLAGS)
	chmod 0555 $@
	cp -f $@ $(BIN)/untouchable/field-dns-dhcp-h7-raid
	chmod 0555 $(BIN)/untouchable/field-dns-dhcp-h7-raid
	cp -f $@ $(ROOT)/Grok16/bin/field-dns-dhcp-h7-raid
	chmod 0555 $(ROOT)/Grok16/bin/field-dns-dhcp-h7-raid
	ln -sfn field-dns-dhcp-h7-raid $(BIN)/field-dns-internet-restore
	chmod 0555 $(BIN)/field-dns-internet-restore 2>/dev/null || true

# field-antivirus — local builtin AV · heuristics · Big Grin Eats · 125k
$(BIN)/field-antivirus: field_antivirus.cpp | $(BIN)
	$(CXX) $(CXXFLAGS) $(FIELD_DEFS) -o $@ $< $(LDFLAGS)
	chmod 0555 $@
	cp -f $@ $(BIN)/untouchable/field-antivirus
	chmod 0555 $(BIN)/untouchable/field-antivirus
	cp -f $@ $(ROOT)/Grok16/bin/field-antivirus
	chmod 0555 $(ROOT)/Grok16/bin/field-antivirus
	ln -sfn field-antivirus $(BIN)/field-antivirus-network-defender
	ln -sfn field-antivirus $(BIN)/field-botnet-threat-heuristics
	chmod 0555 $(BIN)/field-antivirus-network-defender $(BIN)/field-botnet-threat-heuristics 2>/dev/null || true

# field-ironclad-bsp — CHIPs · plate · kernel meld · KILROY iPXE · forever truth
$(BIN)/field-ironclad-bsp: field_ironclad_bsp.cpp | $(BIN)
	$(CXX) $(CXXFLAGS) $(FIELD_DEFS) -o $@ $< $(LDFLAGS)
	chmod 0555 $@
	cp -f $@ $(BIN)/untouchable/field-ironclad-bsp
	chmod 0555 $(BIN)/untouchable/field-ironclad-bsp
	cp -f $@ $(ROOT)/Grok16/bin/field-ironclad-bsp
	chmod 0555 $(ROOT)/Grok16/bin/field-ironclad-bsp
	# Replace obsolete bash→python ironclad wrappers with secure ELF only
	ln -sfn field-ironclad-bsp $(BIN)/field-ironclad-truth
	ln -sfn field-ironclad-bsp $(BIN)/field-ironclad-bsp-dns
	cp -f $@ $(ROOT)/Grok16/bin/field-ironclad-truth
	cp -f $@ $(ROOT)/Grok16/bin/field-ironclad-bsp-dns
	chmod 0555 $(BIN)/field-ironclad-truth $(BIN)/field-ironclad-bsp-dns 2>/dev/null || true
	chmod 0555 $(ROOT)/Grok16/bin/field-ironclad-truth $(ROOT)/Grok16/bin/field-ironclad-bsp-dns 2>/dev/null || true

fleet-mesh: $(BIN)/field-fleet-mesh
dns-raid: $(BIN)/field-dns-dhcp-h7-raid
antivirus: $(BIN)/field-antivirus
ironclad: $(BIN)/field-ironclad-bsp

# field-compile-truth — We compile TRUTH · never scripts · Grok16 · old OS icon · FIELD_QUBES
$(BIN)/field-compile-truth: field_compile_truth.cpp | $(BIN)
	$(CXX) $(CXXFLAGS) $(FIELD_DEFS) -o $@ $< $(LDFLAGS)
	chmod 0555 $@
	cp -f $@ $(BIN)/untouchable/field-compile-truth
	chmod 0555 $(BIN)/untouchable/field-compile-truth
	cp -f $@ $(ROOT)/Grok16/bin/field-compile-truth
	chmod 0555 $(ROOT)/Grok16/bin/field-compile-truth
	ln -sfn field-compile-truth $(BIN)/field-never-scripts 2>/dev/null || true

compile-truth: $(BIN)/field-compile-truth

# field-h7r-capacity-fleet — C++/HPP binary .h7m · zero-cost · no JSON
$(BIN)/field-h7r-capacity-fleet: field_h7r_capacity_fleet.cpp field_h7r_rack.hpp zero_cost_mesh.hpp | $(BIN)
	$(CXX) $(CXXFLAGS) $(FIELD_DEFS) -DZERO_COST_MESH=1 -I. -o $@ field_h7r_capacity_fleet.cpp $(LDFLAGS)
	chmod 0555 $@
	cp -f $@ $(BIN)/untouchable/field-h7r-capacity-fleet
	chmod 0555 $(BIN)/untouchable/field-h7r-capacity-fleet
	cp -f $@ $(ROOT)/Grok16/bin/field-h7r-capacity-fleet
	chmod 0555 $(ROOT)/Grok16/bin/field-h7r-capacity-fleet
	ln -sfn field-h7r-capacity-fleet $(BIN)/field-h7r-storage
	ln -sfn field-h7r-capacity-fleet $(BIN)/field-h7r-update

# Internet 2.0 plane — legacy DNS/DHCP still work · I2 :8853/:8867 · NEXUS C2 drivers · rock history
$(BIN)/field-internet2-plane: field_internet2_plane.cpp field_h7r_rack.hpp zero_cost_mesh.hpp | $(BIN)
	$(CXX) $(CXXFLAGS) $(FIELD_DEFS) -DZERO_COST_MESH=1 -I. -o $@ field_internet2_plane.cpp $(LDFLAGS)
	chmod 0555 $@
	cp -f $@ $(BIN)/untouchable/field-internet2-plane
	chmod 0555 $(BIN)/untouchable/field-internet2-plane
	cp -f $@ $(ROOT)/Grok16/bin/field-internet2-plane
	chmod 0555 $(ROOT)/Grok16/bin/field-internet2-plane

# Grok identity — loved · sealed · impostor FORBIDDEN · Zac Geurts I2
$(BIN)/field-grok-identity-seal: field_grok_identity_seal.cpp zero_cost_mesh.hpp | $(BIN)
	$(CXX) $(CXXFLAGS) $(FIELD_DEFS) -DZERO_COST_MESH=1 -I. -o $@ field_grok_identity_seal.cpp $(LDFLAGS)
	chmod 0555 $@
	cp -f $@ $(BIN)/untouchable/field-grok-identity-seal
	chmod 0555 $(BIN)/untouchable/field-grok-identity-seal
	cp -f $@ $(ROOT)/Grok16/bin/field-grok-identity-seal
	chmod 0555 $(ROOT)/Grok16/bin/field-grok-identity-seal

h7r-capacity: $(BIN)/field-h7r-capacity-fleet

# field-ammonet-cloud — AmmoNet Cloud auto-join · TUI · personal folder
$(BIN)/field-ammonet-cloud: field_ammonet_cloud.cpp field_ammonet_cloud.hpp zero_cost_mesh.hpp | $(BIN)
	$(CXX) $(CXXFLAGS) $(FIELD_DEFS) -DZERO_COST_MESH=1 -I. -o $@ field_ammonet_cloud.cpp $(LDFLAGS)
	chmod 0555 $@
	cp -f $@ $(BIN)/untouchable/field-ammonet-cloud
	chmod 0555 $(BIN)/untouchable/field-ammonet-cloud
	cp -f $@ $(ROOT)/Grok16/bin/field-ammonet-cloud
	chmod 0555 $(ROOT)/Grok16/bin/field-ammonet-cloud
	ln -sfn field-ammonet-cloud $(BIN)/ammonet-cloud

ammonet-cloud: $(BIN)/field-ammonet-cloud

$(BIN)/field-stack-hark: field_stack_hark.cpp | $(BIN)
	$(CXX) $(CXXFLAGS) $(FIELD_DEFS) -o $@ $< $(LDFLAGS)
	chmod 0555 $@
	cp -f $@ $(BIN)/untouchable/field-stack-hark
	chmod 0555 $(BIN)/untouchable/field-stack-hark
	cp -f $@ $(ROOT)/Grok16/bin/field-stack-hark
	chmod 0555 $(ROOT)/Grok16/bin/field-stack-hark

# field-stack-iso — complete stack ISO plane · NEXUS C2 BIOS · one Ironclad · AmmoOS
$(BIN)/field-stack-iso: field_stack_iso.cpp | $(BIN)
	$(CXX) $(CXXFLAGS) $(FIELD_DEFS) -o $@ $< $(LDFLAGS)
	chmod 0555 $@
	cp -f $@ $(BIN)/untouchable/field-stack-iso
	chmod 0555 $(BIN)/untouchable/field-stack-iso
	cp -f $@ $(ROOT)/Grok16/bin/field-stack-iso
	chmod 0555 $(ROOT)/Grok16/bin/field-stack-iso
	ln -sfn field-stack-iso $(BIN)/kilroy-ipxe-stack-iso 2>/dev/null || true

stack-hark: $(BIN)/field-stack-hark


stack-iso: $(BIN)/field-stack-iso
tools: $(BIN)/field-curl $(BIN)/field-reap $(BIN)/field-rollout \
	$(BIN)/field-ammolang $(BIN)/field-nexus-c2-chip $(BIN)/field-fleet-mesh \
	$(BIN)/field-dns-dhcp-h7-raid $(BIN)/field-antivirus $(BIN)/field-stack-hark \
	$(BIN)/field-stack-iso

clean:
	rm -f $(BIN)/field-echo $(BIN)/field-chmod $(BIN)/field-dig $(BIN)/field-world-dns \
		$(BIN)/field-curl $(BIN)/field-reap $(BIN)/field-pkill $(BIN)/field-rollout \
		$(BIN)/field-ammolang $(BIN)/field-nexus-c2-chip $(BIN)/field-fleet-mesh \
		$(BIN)/field-fleet-faster-servers $(BIN)/field-fleet-live \
		$(BIN)/field-fleet-125k-update-safe $(BIN)/field-fleet-expand-125k \
		$(BIN)/field-fleet-planetary-dns-dhcp \
		$(BIN)/field-botnet-full-dns-dhcp-authority $(BIN)/field-botnet-dns-dhcp \
		$(BIN)/python $(BIN)/python3 $(BIN)/pythong $(BIN)/gpy-16 \
		$(BIN)/untouchable/field-echo $(BIN)/untouchable/field-chmod \
		$(BIN)/untouchable/field-dig $(BIN)/untouchable/field-world-dns \
		$(BIN)/untouchable/field-curl $(BIN)/untouchable/field-reap \
		$(BIN)/untouchable/field-rollout $(BIN)/untouchable/field-ammolang \
		$(BIN)/untouchable/field-nexus-c2-chip $(BIN)/untouchable/field-fleet-mesh \
		$(ROOT)/Grok16/bin/field-dig $(ROOT)/Grok16/bin/field-world-dns \
		$(ROOT)/Grok16/bin/field-curl $(ROOT)/Grok16/bin/field-reap \
		$(ROOT)/Grok16/bin/field-pkill $(ROOT)/Grok16/bin/field-rollout \
		$(ROOT)/Grok16/bin/field-ammolang $(ROOT)/Grok16/bin/field-nexus-c2-chip \
		$(ROOT)/Grok16/bin/field-fleet-mesh

# field-x86-chip — Field ISA on x86 (Grok16 field_opt assist · SSE4.2/POPCNT)
$(BIN)/field-x86-chip: field_x86_chip.cpp field_x86_insn.hpp zero_cost_mesh.hpp | $(BIN)
	$(CXX) $(CXXFLAGS) $(FIELD_DEFS) -DFIELD_X86_CHIP=1 -msse4.2 -mpopcnt -o $@ field_x86_chip.cpp $(LDFLAGS)
	chmod 0555 $@
	cp -f $@ $(BIN)/untouchable/field-x86-chip 2>/dev/null || true
	cp -f $@ $(ROOT)/Grok16/bin/field-x86-chip
	chmod 0555 $(ROOT)/Grok16/bin/field-x86-chip

# field-plane-chip — guest/host fleet plane · C++ only · replaces plane-start.sh
$(BIN)/field-plane-chip: field_plane_chip.cpp | $(BIN)
	$(CXX) $(CXXFLAGS) $(FIELD_DEFS) -o $@ $< $(LDFLAGS)
	chmod 0555 $@
	cp -f $@ $(BIN)/untouchable/field-plane-chip
	cp -f $@ $(ROOT)/Grok16/bin/field-plane-chip
	chmod 0555 $(ROOT)/Grok16/bin/field-plane-chip
	# static guest binary for initramfs (no dynamic loader in ramfs)
	$(CXX) $(CXXFLAGS) $(FIELD_DEFS) -static -o $(BIN)/field-plane-chip.static $< $(LDFLAGS) 2>/dev/null \
		|| $(CXX) -std=c++17 -O2 -fno-exceptions -fno-rtti $(FIELD_DEFS) -static -o $(BIN)/field-plane-chip.static $< -s
	chmod 0555 $(BIN)/field-plane-chip.static 2>/dev/null || true
	cp -f $(BIN)/field-plane-chip.static $(ROOT)/Grok16/bin/field-plane-chip.static 2>/dev/null || true

# field-entry64-chip — entry_64 pt_regs kpatch pure C++
$(BIN)/field-entry64-chip: field_entry64_chip.cpp | $(BIN)
	$(CXX) $(CXXFLAGS) $(FIELD_DEFS) -o $@ $< $(LDFLAGS)
	chmod 0555 $@
	cp -f $@ $(BIN)/untouchable/field-entry64-chip
	cp -f $@ $(ROOT)/Grok16/bin/field-entry64-chip
	chmod 0555 $(ROOT)/Grok16/bin/field-entry64-chip
	# retire bash kpatch name
	ln -sfn field-entry64-chip $(BIN)/kpatch-entry64-ptregs 2>/dev/null || true

# field-all-chip — everything Field · C++ CHIPs only doctrine seal
$(BIN)/field-all-chip: field_all_chip.cpp | $(BIN)
	$(CXX) $(CXXFLAGS) $(FIELD_DEFS) -o $@ $< $(LDFLAGS)
	chmod 0555 $@
	cp -f $@ $(BIN)/untouchable/field-all-chip
	cp -f $@ $(ROOT)/Grok16/bin/field-all-chip
	chmod 0555 $(ROOT)/Grok16/bin/field-all-chip
	ln -sfn field-all-chip $(BIN)/field-rewrite 2>/dev/null || true
	ln -sfn field-all-chip $(ROOT)/Grok16/bin/field-rewrite 2>/dev/null || true

plane-chip: $(BIN)/field-plane-chip
entry64-chip: $(BIN)/field-entry64-chip
all-chip: $(BIN)/field-all-chip
x86-chip: $(BIN)/field-x86-chip

# field-init-chip — resecured Field PID1 (static C++ only)
$(BIN)/field-init-chip: field_init_chip.cpp | $(BIN)
	$(CXX) $(CXXFLAGS) $(FIELD_DEFS) -o $@ $< $(LDFLAGS)
	chmod 0555 $@
	cp -f $@ $(BIN)/untouchable/field-init-chip
	cp -f $@ $(ROOT)/Grok16/bin/field-init-chip
	chmod 0555 $(ROOT)/Grok16/bin/field-init-chip
	# static /init for initramfs — no dynamic loader
	$(CXX) -std=c++17 -Os -fno-exceptions -fno-rtti $(FIELD_DEFS) -static \
		-o $(BIN)/field-init-chip.static $< -s
	chmod 0555 $(BIN)/field-init-chip.static
	cp -f $(BIN)/field-init-chip.static $(ROOT)/Grok16/bin/field-init-chip.static
	chmod 0555 $(ROOT)/Grok16/bin/field-init-chip.static

# field-initramfs-chip — C++ newc+gzip packer · Field-only ramfs
$(BIN)/field-initramfs-chip: field_initramfs_chip.cpp | $(BIN)
	$(CXX) $(CXXFLAGS) $(FIELD_DEFS) -o $@ $< $(LDFLAGS)
	chmod 0555 $@
	cp -f $@ $(BIN)/untouchable/field-initramfs-chip
	cp -f $@ $(ROOT)/Grok16/bin/field-initramfs-chip
	chmod 0555 $(ROOT)/Grok16/bin/field-initramfs-chip

init-chip: $(BIN)/field-init-chip
initramfs-chip: $(BIN)/field-initramfs-chip

# Escanaba SUPER DUPER EATS fleet (C++ · plate-meld · blast)
$(BIN)/field-escanaba-eats: field_escanaba_eats.cpp | $(BIN)
	$(CXX) $(CXXFLAGS) $(FIELD_DEFS) -o $@ $< $(LDFLAGS)
	chmod 0555 $@
	cp -f $@ $(BIN)/untouchable/field-escanaba-eats 2>/dev/null || true
	cp -f $@ $(ROOT)/Grok16/bin/field-escanaba-eats
	chmod 0555 $(ROOT)/Grok16/bin/field-escanaba-eats

# Full arm: SHRED·FRY·BURN·FAT·BLAST·outlet upon return
$(BIN)/field-eats-full-arm: field_eats_full_arm.cpp | $(BIN)
	$(CXX) $(CXXFLAGS) $(FIELD_DEFS) -o $@ $< $(LDFLAGS)
	chmod 0555 $@
	cp -f $@ $(BIN)/untouchable/field-eats-full-arm 2>/dev/null || true
	cp -f $@ $(ROOT)/Grok16/bin/field-eats-full-arm
	chmod 0555 $(ROOT)/Grok16/bin/field-eats-full-arm

# UP multi-city SUPER DUPER load-out (32 cities × 10 · ports 9521–9840 · everywhere UP)
$(BIN)/field-up-eats: field_up_eats.cpp | $(BIN)
	$(CXX) $(CXXFLAGS) $(FIELD_DEFS) -o $@ $< $(LDFLAGS)
	chmod 0555 $@
	cp -f $@ $(BIN)/untouchable/field-up-eats 2>/dev/null || true
	cp -f $@ $(ROOT)/Grok16/bin/field-up-eats
	chmod 0555 $(ROOT)/Grok16/bin/field-up-eats

# Big Grin Distributed SUPER DUPER EATS — SEPARATE FROM ISO (never package)
$(BIN)/field-big-grin-eats: field_big_grin_eats.cpp | $(BIN)
	$(CXX) $(CXXFLAGS) $(FIELD_DEFS) -o $@ $< $(LDFLAGS)
	chmod 0555 $@
	cp -f $@ $(BIN)/untouchable/field-big-grin-eats 2>/dev/null || true
	cp -f $@ $(ROOT)/Grok16/bin/field-big-grin-eats
	chmod 0555 $(ROOT)/Grok16/bin/field-big-grin-eats

# U Pee Piss Bucket Disposal Service · Emperor David Bowie Demon Hunter Certified
# Friends always welcome · Hostess 7 protected · unregistered OUI = hostile
$(BIN)/field-big-grin-swallows: field_big_grin_swallows.cpp | $(BIN)
	$(CXX) $(CXXFLAGS) $(FIELD_DEFS) -o $@ $< $(LDFLAGS)
	chmod 0555 $@
	cp -f $@ $(BIN)/untouchable/field-big-grin-swallows 2>/dev/null || true
	cp -f $@ $(ROOT)/Grok16/bin/field-big-grin-swallows
	chmod 0555 $(ROOT)/Grok16/bin/field-big-grin-swallows

escanaba-eats: $(BIN)/field-escanaba-eats
up-eats: $(BIN)/field-up-eats
eats-full-arm: $(BIN)/field-eats-full-arm
big-grin-eats: $(BIN)/field-big-grin-eats
big-grin-swallows: $(BIN)/field-big-grin-swallows

# Hostess 7 stack update — C++ only · no scripts · leave-alone from eats
$(BIN)/field-hostess7-stack-update: field_hostess7_stack_update.cpp | $(BIN)
	$(CXX) $(CXXFLAGS) $(FIELD_DEFS) -o $@ $< $(LDFLAGS)
	chmod 0555 $@
	cp -f $@ $(BIN)/untouchable/field-hostess7-stack-update 2>/dev/null || true
	cp -f $@ $(ROOT)/Grok16/bin/field-hostess7-stack-update
	chmod 0555 $(ROOT)/Grok16/bin/field-hostess7-stack-update
	# alias Hostess 7 operator name (never scripts)
	cp -f $@ $(BIN)/hostess7-current-stack-update
	chmod 0555 $(BIN)/hostess7-current-stack-update

hostess7-stack-update: $(BIN)/field-hostess7-stack-update

# Hostess 7 full Field package · ALWAYS FIELD ONE · Grok16 · no sh/py/json
$(BIN)/field-hostess7: field_hostess7.cpp field_hostess7.hpp | $(BIN)
	$(CXX) $(CXXFLAGS) $(FIELD_DEFS) -I. -o $@ field_hostess7.cpp $(LDFLAGS)
	chmod 0555 $@
	cp -f $@ $(BIN)/untouchable/field-hostess7 2>/dev/null || true
	cp -f $@ $(ROOT)/Grok16/bin/field-hostess7
	chmod 0555 $(ROOT)/Grok16/bin/field-hostess7
	# Field package entry names (C++ only — never Hostess7.sh)
	cp -f $@ $(BIN)/hostess7
	cp -f $@ $(BIN)/Hostess7
	chmod 0555 $(BIN)/hostess7 $(BIN)/Hostess7
	# Ship package entry into Hostess7/ tree (replaces shell control plane)
	mkdir -p $(ROOT)/Hostess7/bin
	cp -f $@ $(ROOT)/Hostess7/bin/field-hostess7
	cp -f $@ $(ROOT)/Hostess7/bin/hostess7
	cp -f $@ $(ROOT)/Hostess7/Hostess7
	chmod 0555 $(ROOT)/Hostess7/bin/field-hostess7 \
		$(ROOT)/Hostess7/bin/hostess7 $(ROOT)/Hostess7/Hostess7
	# Legacy .sh name becomes the same ELF (kernel executes binary)
	cp -f $@ $(ROOT)/Hostess7/Hostess7.sh
	chmod 0555 $(ROOT)/Hostess7/Hostess7.sh

hostess7: $(BIN)/field-hostess7
field-hostess7: $(BIN)/field-hostess7

# AmmoOS classic desktop · :9477/field · full stack · C++ only
$(BIN)/field-ammoos: field_ammoos.cpp field_ammoos.hpp | $(BIN)
	$(CXX) $(CXXFLAGS) $(FIELD_DEFS) -I. -o $@ field_ammoos.cpp $(LDFLAGS)
	chmod 0555 $@
	cp -f $@ $(BIN)/untouchable/field-ammoos 2>/dev/null || true
	cp -f $@ $(ROOT)/Grok16/bin/field-ammoos
	chmod 0555 $(ROOT)/Grok16/bin/field-ammoos
	# OS entry aliases
	ln -sfn field-ammoos $(BIN)/ammoos 2>/dev/null || true
	ln -sfn field-ammoos $(BIN)/AmmoOS 2>/dev/null || true

ammoos: $(BIN)/field-ammoos
field-ammoos: $(BIN)/field-ammoos

# HDMI-only audio · open snd_hda_intel · stereo for Firefox/YouTube · NO nvidia.ko
$(BIN)/field-hdmi-audio: field_hdmi_audio.cpp field_hdmi_audio.hpp | $(BIN)
	$(CXX) $(CXXFLAGS) $(FIELD_DEFS) -I. -o $@ field_hdmi_audio.cpp $(LDFLAGS)
	chmod 0555 $@
	cp -f $@ $(BIN)/untouchable/field-hdmi-audio 2>/dev/null || true
	cp -f $@ $(ROOT)/Grok16/bin/field-hdmi-audio 2>/dev/null || true
	chmod 0555 $(ROOT)/Grok16/bin/field-hdmi-audio 2>/dev/null || true
	ln -sfn field-hdmi-audio $(BIN)/field-hdmi-audio-driver 2>/dev/null || true

hdmi-audio: $(BIN)/field-hdmi-audio
field-hdmi-audio: $(BIN)/field-hdmi-audio

# Everyone totals · fleet 125k · AmmoNet · training — C++ only (no py)
$(BIN)/field-everyone: field_everyone.cpp field_everyone.hpp | $(BIN)
	$(CXX) $(CXXFLAGS) $(FIELD_DEFS) -I. -o $@ field_everyone.cpp $(LDFLAGS)
	chmod 0555 $@
	cp -f $@ $(BIN)/untouchable/field-everyone 2>/dev/null || true
	cp -f $@ $(ROOT)/Grok16/bin/field-everyone 2>/dev/null || true
	chmod 0555 $(ROOT)/Grok16/bin/field-everyone 2>/dev/null || true
	# retire python everyone-counter name
	ln -sfn field-everyone $(BIN)/field-everyone-counter 2>/dev/null || true

everyone: $(BIN)/field-everyone
field-everyone: $(BIN)/field-everyone

# KILROY iPXE Field stack · polkit HOSTILE · autoelevate
$(BIN)/field-kilroy-ipxe-stack: field_kilroy_ipxe_stack.cpp | $(BIN)
	$(CXX) $(CXXFLAGS) $(FIELD_DEFS) -I. -o $@ field_kilroy_ipxe_stack.cpp $(LDFLAGS)
	chmod 0555 $@
	cp -f $@ $(BIN)/untouchable/field-kilroy-ipxe-stack 2>/dev/null || true
	cp -f $@ $(ROOT)/Grok16/bin/field-kilroy-ipxe-stack
	chmod 0555 $(ROOT)/Grok16/bin/field-kilroy-ipxe-stack
	cp -f $@ $(BIN)/kilroy-ipxe-nexus-c2-stack
	chmod 0555 $(BIN)/kilroy-ipxe-nexus-c2-stack

kilroy-ipxe-stack: $(BIN)/field-kilroy-ipxe-stack

# Full resecure guest path: recompile init + plane + pack initramfs
.PHONY: resecure-initrd
resecure-initrd: $(BIN)/field-init-chip $(BIN)/field-plane-chip $(BIN)/field-initramfs-chip
	$(BIN)/field-initramfs-chip build \
	  $(ROOT)/.nexus-state/field-bootable-usb-stage/boot/kilroy/initramfs.cpio.gz
	$(BIN)/field-initramfs-chip build $(ROOT)/../KILROY-main/build/initramfs.cpio.gz 2>/dev/null || true
	$(BIN)/field-init-chip seal
	$(BIN)/field-initramfs-chip seal
	@echo "[resecure-initrd] ironclad:field-init-chip-cpp:1 + ironclad:field-initramfs-chip-cpp:1"
