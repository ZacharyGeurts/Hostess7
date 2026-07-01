## Packet field as readable perimeter

NEXUS-Shield turns sockets into **operator-readable state**:

- `packet-field.py` → ring, ports, recent flows
- `connection-gatekeeper.py` → IFF, trust, suggestions
- Threat panel HTTP `:9477` → parallel slice publish

Field Research added **diagnostic mode** as perimeter reflex: when truth breaks, **shrink the attack surface**.

![Diagnostic mode — lock away from fault](../assets/images/diagnostic-mode-art.jpg)

## Diagnostic mode doctrine

`field-diagnostic-mode-doctrine.json`:

> Problems detected → drop to diagnostic. All systems lock away from the fault; it is reorganized out.

Fault signals:

- ironclad_field_sanity (quarantine, gate_not_ok)
- g1id_baselines (critical)
- field_io_packet truth gate
- filesystem_critical
- thermal_crit
- brain_corruption
- compatibility_fault

## engage() sequence

1. `detect_problems()`
2. `reorganize_fault()` — quarantine fault domains, sanity operator pass
3. Write panel `engaged: true`
4. Filter parallel slices to secure baseline set
5. Gate meld refreshes via `_refresh_if_allowed`

## debug_self() — clear only after pass

Secure baseline chain:

```
g1id-baseline verify → ironclad sanity → io-packet gate → probe guard
```

`clear()` refuses until `debug_self` passes unless `force`.

## API and UI

- `GET/POST /api/diagnostic-mode`
- Threat panel banner + System card
- `NEXUS_DIAGNOSTIC_MODE=1` force on; `=0` force off
- Slice `field_diagnostic` in parallel publish

## Filesystem update (related perimeter)

`field-filesystem-update.py` — disk pressure warn/reclaim; `destroyed` catalog field. Feeds diagnostic on `critical` pressure.

## Research conclusion

Perimeter is not only firewall rules. It is **which modules may run when truth is wounded**. Diagnostic mode is the researched answer — not panic shutdown, **baseline-only self-debug**.

**Next:** Chapter 12 — Queen browser and host desktop shell.