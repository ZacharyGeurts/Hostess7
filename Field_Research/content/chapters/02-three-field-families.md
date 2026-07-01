## Three families, one literacy

Field Research assumes you have met the three families from Field Primer Chapter 2. We repeat them here because **every Grok16 facet and every compatibility layer ultimately serves one of these**:

## Family 1 — GPU fabric (AMOURANTHRTX)

**Binding map:** Phi (8), Thermo (9), Flow (10).

The GPU is not a pretty screen. It is **addressable field state** — texels as memory, shaders as operators, SSBO strips as thermodynamic ledgers. AMOURANTHRTX Navigator hosts CHIPS emulation behind the same fabric.

Research conclusion: combinatorics `runner` facet must know when execution stays on **GPU BSP** vs when it drops to native belt. The bridge reads meld plates including `g16_stack` and `g16_compiler_sense` to decide.

<span class="tag impl">Implemented:</span> `AMOURANTHRTX/Navigator/engine/CHIPS/`, Queen `queen-chips.py`.

## Family 2 — Field die (FieldX86Die)

**Binding 1:** 64 MiB linear address strip, wave bands, epoch frames.

The die is the **silicon metaphor made executable**: `fieldx86` facets in `g16-field-combinatorics-doctrine.json` define `belt_1_0` (256 slots) and `belt_2_0` (512 slots). Hard limits come from `field_combinatorics.hard_limits()` — 8³ dots per box, four scale nets, **max_field_depth: 0**.

Research conclusion: knowing is **fixed-size belt dispatch**, not nested fields. This is Grok16 2.0 single fabric.

## Family 3 — Packet field (NEXUS-Shield)

**Perimeter:** gatekeeper, packet-field.json, threat panel :9477.

Sockets become **readable perimeter**. IFF tables, connection intent, DPI classification. The packet field is where **diagnostic mode** publishes its quarantine state.

Research conclusion: compatibility layer 5 (Field surface) serves NEXUS shell programs; layer 0 (Substrate) pins KILROY/linux compat under the die.

## Cross-family data flow

```
GPU fabric ←→ Field die ←→ Packet field
     ↑              ↑              ↑
  CHIPS L4      combinatorics   gatekeeper
  emu BSP       belt/die        diagnostic
```

## Operator map — project names on first use

| Name | Role in this book |
|------|-------------------|
| Grok16 | Unified `g16` driver, belt profiles, combinatorics engine |
| NewLatest | NEXUS-Shield install root, plate meld, compatibility layers |
| Queen | Browser gates, launch chambers, CHIPS registry |
| KILROY | Kernel/linux compat substrate pin |
| Hostess7 | Brain guard, self-view, corruption hold |

## Validation — what you can grep today

```bash
grep -r "belt_2_0" Grok16/data/
grep "compatibility_layers" NewLatest/lib/field-panel-parallel.py
grep "launch_seal" NewLatest/Queen/lib/queen-launch-chamber.py
```

**Next:** Chapter 3 — why thermodynamics and entropy oracles sit in the engine, not in slide decks.