# Explaining Core — Grok15 shared reference

Generated: 2026-07-01T05:05:18Z

Non-redundant backbone for all `explaining_*` language manuals.

## Canonical combinatronic atoms

All field languages boil to these 36 ops — documented once in `explaining_core`.

- **exec** — Execute / eval / run (runner: native_bsp, belt: belt_2_0)
- **assign** — Assign / bind / set (runner: python, belt: belt_1_0)
- **call** — Call / invoke / apply (runner: native_bsp, belt: belt_2_0)
- **return** — Return / exit function (runner: native_bsp, belt: belt_2_0)
- **branch** — Branch / if / switch (runner: native_bsp, belt: belt_1_0)
- **loop** — Loop / iterate / repeat (runner: native_bsp, belt: belt_1_0)
- **break** — Break / leave loop (runner: native_bsp, belt: belt_1_0)
- **continue** — Continue / next iteration (runner: native_bsp, belt: belt_1_0)
- **declare** — Declare / define / let (runner: python, belt: belt_1_0)
- **type** — Type / typedef / interface (runner: native_bsp, belt: belt_2_0)
- **cast** — Cast / convert / coerce (runner: native_bsp, belt: belt_2_0)
- **load** — Load / read memory (runner: native_bsp, belt: belt_2_0)
- **store** — Store / write memory (runner: native_bsp, belt: belt_2_0)
- **alloc** — Allocate / new / malloc (runner: native_bsp, belt: belt_2_0)
- **free** — Free / delete / drop (runner: native_bsp, belt: belt_2_0)
- **io** — I/O / print / read / write file (runner: python, belt: belt_1_0)
- **import** — Import / use / require (runner: python, belt: belt_1_0)
- **export** — Export / pub / module out (runner: native_bsp, belt: belt_2_0)
- **module** — Module / package / namespace (runner: python, belt: belt_1_0)
- **compare** — Compare / eq / ord (runner: native_bsp, belt: belt_1_0)
- **logic** — Logic / and / or / not (runner: native_bsp, belt: belt_1_0)
- **math** — Math / arithmetic (runner: native_bsp, belt: belt_1_0)
- **string** — String / format / concat (runner: python, belt: belt_1_0)
- **struct** — Struct / record / object (runner: native_bsp, belt: belt_2_0)
- **index** — Index / subscript / slice (runner: python, belt: belt_1_0)
- **throw** — Throw / raise / panic (runner: native_bsp, belt: belt_2_0)
- **catch** — Catch / rescue / except (runner: native_bsp, belt: belt_2_0)
- **yield** — Yield / generator / coroutine (runner: python, belt: belt_1_0)
- **lambda** — Lambda / closure / fn (runner: python, belt: belt_1_0)
- **match** — Pattern match / case (runner: native_bsp, belt: belt_2_0)
- **async** — Async / await / concurrent (runner: python, belt: belt_1_0)
- **sync** — Sync / lock / mutex / atomic (runner: native_bsp, belt: belt_2_0)
- **asm** — Inline asm / intrinsics (runner: native_bsp, belt: belt_2_0)
- **unsafe** — Unsafe / raw pointer (runner: native_bsp, belt: belt_2_0)
- **meta** — Macro / reflection / eval (runner: python, belt: belt_1_0)
- **query** — Query / select / SQL (runner: python, belt: belt_1_0)

## Secure compile & run chamber

Every language compiles and runs inside `g16-secure-chamber.py` — security gate first,
scrubbed env, protected paths (AmmoOS, Hostess7, Grok16/bin). See `explaining_core`.

- **Module:** `lib/g16-secure-chamber.py`
- **Posture:** `/api/g16/secure-chamber`
- **Policy:** `data/g16-secure-compile-doctrine.json`

## Reading guide

1. **At a glance** — paradigm, typing, memory (this manual).
2. **Language delta** — keywords unique to this id (not inherited).
3. **explaining_core** — shared atoms, chamber, G16 path, pitfalls.

## G16 compile path

- **Universal facet:** `field-g16-universal-combinatronic.json`
- **Secure chamber:** mandatory for all Grok16 languages
- **Combinatronics:** `g16-compile-combinatronics.py` program facet

## Performance notes

belt_2_0 native_bsp for hot paths; belt_1_0 python when combinatorics degrades.
Always-optimal panel pins belt from bench receipts.

## Research references

Training manuals complement Explaining deltas. See Dewey shelf `training_*` when published.

## Pitfalls (shared)

- Never run user code on the bare host — use secure chamber.
- Extended packs inherit parent commands; this manual lists **delta only** when `extends` is set.
- Missing host toolchains return clear errors inside the chamber.

## Where in NEXUS-Shield

- Core: `library/dewey/000-computer-science/explaining_core/`
- Seed: `data/field-program-combinatronic-seed.json`
- Grok15 core: `Grok16/lib/grok15-language-core.py`
- Reader: `/api/lang-manuals` · `/field-lang-manuals`

