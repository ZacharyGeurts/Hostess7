# Queen Field Engine

Queen Browser engine backend for AmmoOS — **not** the operator's personal browser profile.

## What this is

- **Queen Browser** is the product name users see everywhere (tabs, Start menu, taskbar).
- **Field Engine** is the isolated gecko-hardened backend under `field-gecko/profile/`.
- Binaries ship as `queen-browser` or `queen-field-engine` — never third-party browser UI.

## Launch

```bash
./bin/launch-field-gecko.sh
```

Opens Queen with an isolated profile. Default home/search: DuckDuckGo.

## User guide

Operators migrating from a legacy gecko browser should open:

`http://127.0.0.1:9481/world/queen-browser-guide.html`

## Bootstrap (optional)

```bash
./scripts/bootstrap-field-gecko.sh --tag QUEEN_GECKO_ESR_128
```

Builds a stripped Field Engine from upstream gecko source (MPL 2.0). Queen branding applies in the AmmoOS shell.