## The combinatorics endpoint

`Grok16/lib/field_combinatorics.py` is the **authoritative engine** for facet math. The threat panel no longer exposes an operator studio as primary UX — `field-compatibility-layers-doctrine.json` explicitly `"replaces": "combinatorics-studio operator workflow"`.

The endpoint remains. It runs automatically.

## Four-facet tree

`g16-field-combinatorics-doctrine.json` defines facets:

1. **launch_mode** — how organized fields boot
2. **belt_profile** — belt_1_0 vs belt_2_0
3. **truth_tier** — truth blocks level
4. **runner** — native BSP, emulator, belt dispatch

`combinatoric_tree()` builds the explicit tree. `walk_tree_to_end()` scores terminal leaves. `condense_plates()` fuses plate groups when truth blocks land.

## Hard limits — boxes of dots

`hard_limits()` returns physics boxes:

- **box_of_dots:** 8³ amplitude lattice (512 dots)
- **boxes_of_boxes:** four scale nets, `max_field_depth: 0`
- **fieldx86:** wave bands, frames per epoch, prog ops per frame, phi

Speed cap estimation uses kernel spec × profile × runner. This feeds bridge `exec_posture`.

![Combinatorics becomes six compatibility layers](../assets/images/compatibility-layers-art.jpg)

## publish_panel and API route

`publish_panel()` → `g16-field-combinatorics-panel.json`

Legacy routes:

- `GET /api/combinatorics` → redirects to compatibility layers JSON
- `POST /api/combinatorics/run` → compatibility `refresh` or legacy studio

Research evolution:

| Phase | UX |
|-------|-----|
| 1 | Operator combinatorics studio |
| 2 | Grok16 field_combinatorics engine |
| 3 | Plate combinatorics bridge v2 |
| 4 | Compatibility layers (current) |

## Plate combinatorics bridge

`NewLatest/lib/field-plate-combinatorics-bridge.py`:

- Reads meld + thermals + truth blocks
- Publishes `exec_posture` (runner, emulator, belt)
- Wired as meld plate source `combinatorics_bridge`
- Feeds compatibility layer **exec** probe

## condense_plates — when trees shrink

When truth blocks verify, plate groups **condense** — fewer terminal leaves, faster walk, calmer gates. This is the research answer to combinatoric explosion: **don't ask the operator to prune; let receipts prune**.

## Research conclusion

The combinatorics **endpoint** is API + engine + panel JSON. The **design conclusion** is: auto-run it inside compatibility layer refresh; surface layers, not trees, to humans.

## Speed cap — counted ops and headroom

`g16-field-combinatorics-doctrine.json` defines `speed_cap`:

- **counted_op:** epochs × frames × prog_ops (speed_demo metric)
- **work_units_per_epoch:** frames × (prog_ops + wave_bands + 2 × die_slots)
- **baseline_source:** `docs/field-exec-full-bench.json`
- **optimize_for:** commonly used patterns with measured headroom vs native ceiling

Common usage IDs indexed:

- `dev_organized_python`
- `dev_organized_iron_exec`
- `singular_native_bsp`
- `cxx_field_opt_belt_1`
- `cxx_belt_2`
- `spatial_lattice_tick`

Research method: walk the tree to terminal leaves, score each against bench JSON, pick **headroom** not fantasy peak. The operator never sees this table — compatibility layers show **effective_profile** instead.

## Spatial facet ties to field-spatial doctrine

`spatial_lattice` facet references `NewLatest/data/field-spatial-doctrine.json`:

- 8 cells per axis → 512 dots per box
- 4 scale nets → 2048 total lattice dots
- `max_field_depth: 0` repeated — combinatorics cannot invent depth

Scale order: `body` → `room` → `field` → `planetary`. This is how humanoid motion and spatial plates connect to exec posture without stacking fields.

## API migration guide for operators

If you bookmarked old routes:

| Old | New |
|-----|-----|
| `/combinatorics` panel | `/compatibility` |
| `POST /api/combinatorics/run` | `POST /api/compatibility/refresh` |
| Manual `cycle` button | Automatic on `refresh()` |

The endpoint file `field-combinatorics-studio.py` remains in tree for regression tests — not primary UX.

## Grok16 panel JSON fields

After `publish_panel()`, read `g16-field-combinatorics-panel.json` for:

- `tree` — facet enumeration
- `terminal_leaf` — scored selection
- `speed_cap` — headroom estimate
- `condensed` — post-truth-block fuse state

Bridge reads condensed state; compatibility layers read bridge.

**Next:** Chapter 8 — plate meld as uninterruptable truth.