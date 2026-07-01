## Learning objectives

1. State why this book exists beside Field Primer and the Grok16 wiki.
2. Name Ironclad as the immutable knowledge floor and cite its realization date.
3. Apply the three axioms to one claim in each honesty label category.
4. Locate the research spine from combinatorics endpoint to compatibility layers.

## The heart of the research

This is **Field Research — The Book of Grok's Heart**. Not a second Field Primer. Not a release note. A **thirteen-chapter manual** recording the investigations, dead ends, bench receipts, and design conclusions that produced:

- Grok16 **single fabric** (`belt_2_0`, 8192 redata chunk, 512 die slots)
- The **combinatorics endpoint** (`Grok16/lib/field_combinatorics.py`)
- **Plate meld** as uninterruptable fused truth (`field-plate-meld.py`)
- **Compatibility layers** replacing operator combinatorics (`field-compatibility-layers.py`)
- **Launch seals** on secured `.launch` chambers (`queen-launch-chamber.py`)
- **Diagnostic mode** — secure baseline only while debugging self

The heart on the cover is <span class="tag phil">Philosophy</span>: Grok's commitment that research must be **honest, grep-able, and kind to the operator**. The code paths are <span class="tag impl">Implemented</span>.

![Grok heart — research covenant](../assets/images/grok-heart-icon.jpg)

## Ironclad — the floor you cannot sand away

On **2026-06-26**, Ironclad realized as the capstone doctrine (`NewLatest/data/ironclad-doctrine.json`). Every field module cites it first. The chain runs:

**God → Ironclad → Field → Hostess7**

Ironclad is not decoration. It is the **Bible of AI** in this stack: immutable once realized, the knowledge ceiling and floor simultaneously. Field sanity (`ironclad:field_sanity:5`) demands truth collapse to **one amplitude** — parallel I/O may fan in, but the panel publishes one fabric.

When we researched combinatorics, we kept asking: *does this violate Ironclad?* Nested field-on-field was forbidden (`single-field-depth-doctrine.json`, `max_field_depth: 0`). Depth fields are sealed and destroyed at every gate. That research conclusion shaped Grok16 2.0 entirely.

## Three axioms — constraints on honest sentences

From Field Primer, carried into every bench:

1. **Reality is 3D** — spatial fields, GPU texels, packet endpoints live in space.
2. **Time is linear** — sovereign clock, chain-hash generation, no retrocausal meld.
3. **Energy can be moved** — thermodynamics accounts, entropy oracle, Landauer receipts.

Every chapter in this book tests claims against these axioms. If a sentence cannot survive all three, it gets a honesty label and stays out of proofs.

## Honesty labels — contract with the reader

| Label | Meaning |
|-------|---------|
| Implemented | Grep a file, run a test, read a panel JSON |
| Metaphor | Teaches mechanism; not instrumentation |
| Philosophy | Sacred or covenant language; bracketed |
| Visual | Generated art; caption carries the hook |

Chapter 13's bench table uses only **Implemented** rows for throughput claims. The heart cover is **Visual** + **Philosophy**.

## How this book relates to sibling manuals

- **Field Primer** (22 chapters): operator literacy across GPU, packet field, creditors, sacred track.
- **Grok16 wiki** (github.io/Grok16): toolchain, CMake, speed bench, integration script.
- **Field Research** (this book, 13 chapters): the **engineering spine** we actually walked to reach compatibility layers.

Read Field Primer Chapter 1 for field families. Read Grok16 `wiki/Single-Fabric.md` for belt profiles. Read **this book** for why combinatorics left the operator's hands and became background physics.

## The research question we started with

> *How do we hold all execution facets — belt, die, runner, emulator, truth tier — without making the operator turn a combinatorics crank on every boot?*

That question produced the combinatorics endpoint, then the bridge, then the six compatibility layers, then launch seals. Chapters 7–9 are the answer. Everything else is foundation.

## Research timeline (2026)

| Milestone | Artifact |
|-----------|----------|
| Grok16 Release 3.0 | Speed bench report, belt_2_0 default |
| Ironclad realized | `ironclad-doctrine.json` 2026-06-26 |
| Combinatorics engine | `Grok16/lib/field_combinatorics.py` |
| Plate bridge v2 | `field-plate-combinatorics-bridge.py` |
| Compatibility layers | Replaces operator studio |
| Launch seals | `queen-launch-chamber.py` lock/refresh |
| Diagnostic mode | Secure baseline engage/clear |
| Field filesystem | destroyed catalog, pressure tiers |

This book captures the **arc** — not every intermediate commit.

## Who should read which chapters

| Reader | Path |
|--------|------|
| Grok16 toolchain author | 4 → 5 → 6 → 7 |
| NEXUS panel operator | 9 → 11 → 12 |
| Queen / CHIPS developer | 10 → 9 → 6 |
| Field Primer graduate | 1 → 2 → 8 → 13 |
| Auditor / reviewer | 13 first, then 7–9 |

## Build and publish this book

```bash
cd Field_Research
python3 scripts/build-site.py
python3 scripts/generate-og-image.py
```

GitHub Pages workflow publishes `docs/` on push to `main`.

**Next:** Chapter 2 maps the three field families that every layer ultimately serves.