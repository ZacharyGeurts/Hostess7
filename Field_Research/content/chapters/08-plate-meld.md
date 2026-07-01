## Uninterruptable fused state

`field-plate-meld.py` motto: flock + fsync + chain-hash + triple mirror.

Plates always share **generation-linked truth**. Copilot and bus read meld first.

![Plate meld — chain hash fusion](../assets/images/plate-meld-art.jpg)

## Thirty plate sources

`PLATE_SOURCES` in meld includes among others:

- iron_plate, plate_runtime, field_plate, unified_bus
- gatekeeper, logic_gate, znetwork
- ironclad, ironclad_reality_field, ironclad_field_sanity
- g1id_baselines, field_io_packet
- g16_stack, g16_compiler_sense, truth_blocks
- field_combinatorics, combinatorics_bridge
- hostess7_brain, spatial_field, kernel, firmware

Each refresh publishes a panel JSON consumed on next fuse.

## meld() vs fuse()

- `fuse()` — fast fuse, on-disk plates only, no refresh storm
- `meld(refresh_plates=True)` — full refresh then collect → chain hash

`_GEN` monotonic. `_LAST_CHAIN` links generation to content digest.

## Diagnostic mode integration

When diagnostic mode is active, `_refresh_if_allowed()` gates each refresh:

**Allowed:** ironclad_field_sanity, g1id_baselines, field_io_packet, gatekeeper, logic_gate

**Skipped:** hostess7 modules, combinatorics, compatibility_layers, spatial, firmware, etc.

Fault isolation is not metaphor — meld literally stops refreshing fault-adjacent plates.

## Compiler sense reads meld

`g16-compiler-sense-plate.py` uses meld outputs to pick profile ladder step. Bench doctrine: meld post-ratio ~0.986 on hot path; compile-time win when expert profile chosen.

## Triple mirror

`plate-meld-redundant/` mirrors meld JSON with `.bak` siblings. Uninterruptable means: power loss mid-write still leaves recoverable chain.

## Research conclusion

Plate meld is the **single JSON truth** combinatorics bridge and compatibility layers read. Without meld, layers would stack on stale posture — launch seals would lie.

**Next:** Chapter 9 — compatibility layers and launch seals.