# Scripts layout

Hostess7 uses a **two-tier** script layout. This is intentional — not duplication to delete.

**All execution goes through AML** — `./lib/ammolang-run.sh` with `AML_BUILD=1` (default). Never bypass with `AML_BUILD=0` or `AML_IMPL=1 bash scripts/impl/...`.

## `scripts/` — public entrypoints

Thin wrappers that route through the AML boundary (`ammolang-run.sh`):

```bash
./scripts/wire-stack.sh                    # AML → wire_stack
./scripts/kilroy-load-os.sh                # AML → load_os
./scripts/field-vm-boot.sh               # AML → field_vm_boot
./lib/ammolang-run.sh exec script:scripts/check-deps.sh
```

## `scripts/impl/` — authoritative implementations

Full logic lives here. Invoked only via AML boundary (`exec script:...` or named tasks):

```bash
./lib/ammolang-run.sh exec script:scripts/impl/wire-stack.sh
./lib/ammolang-run.sh field_vm_boot
```

Internal sub-calls use `lib/nexus-aml-exec.sh` — never direct `bash scripts/impl/...`.

## Common commands (AML only)

| Goal | Command |
|------|---------|
| Check deps | `./lib/ammolang-run.sh exec script:scripts/check-deps.sh` |
| Wire siblings | `./lib/ammolang-run.sh exec script:scripts/wire-stack.sh` |
| KILROY + desktop | `./lib/ammolang-run.sh exec script:scripts/kilroy-load-os.sh` |
| Full VM boot | `./lib/ammolang-run.sh field_vm_boot` |
| Restart stack | `./lib/ammolang-run.sh exec script:scripts/impl/restart-field-stack.sh` |
| Hostess7 on | `./lib/ammolang-run.sh exec script:Hostess7/Hostess7.sh on` |

## Do not merge tiers

Removing `scripts/` stubs breaks AML boundary routing and published installer paths. New scripts: implementation in `impl/`, thin delegator in `scripts/`, sub-invocations via `nexus_aml_exec`.