# Field I/O

NEXUS I/O is **loopback-first**: panel HTTP on `:9477`, state under `NEXUS_STATE_DIR`, CLI mirrors trust/block.

**Full manual:** https://zacharygeurts.github.io/NEXUS-Shield/io.html

---

## Architecture

![Architecture I/O](https://raw.githubusercontent.com/ZacharyGeurts/NEXUS-Shield/main/docs/images/io-architecture.svg)

Operator browser ↔ panel HTTP ↔ `nexus-genius.service` ↔ `/var/lib/nexus-shield` ↔ nftables perimeter.

---

## Boot I/O

![Boot flow](https://raw.githubusercontent.com/ZacharyGeurts/NEXUS-Shield/main/docs/images/io-boot-flow.svg)

| Marker | Meaning |
|--------|---------|
| `first-boot.complete` | First full impl done |
| `boot-impl.last` | `mode=first` or `mode=refresh` |
| `panel-launched.boot` | Browser opened this boot |

→ **[Boot Implementation](Boot-Implementation)**

---

## Field switch safety

![Field switch safety](https://raw.githubusercontent.com/ZacharyGeurts/NEXUS-Shield/main/docs/images/field-switch-safety.svg)

| File | Role |
|------|------|
| `field-switch-safety.json` | Last preflight panel |
| `thermal-advisory.json` | hwmon peak, quota advisory |
| `wave-shed-advisory.json` | Excess draw shed receipt |

→ **[Field Switch Safety](Field-Switch-Safety)**

---

## Field thermal guard

![Field thermal guard](https://raw.githubusercontent.com/ZacharyGeurts/NEXUS-Shield/main/docs/images/field-thermal-guard.svg)

| File | Role |
|------|------|
| `field-thermal-guard.json` | Headroom, budget, anomaly panel |
| `field-global-redata.json` | Last incremental redata receipt |
| `field-thermal-rate-limit.json` | Gatekeeper stealth limit when active |

→ **[Field Thermal Guard](Field-Thermal-Guard)**

---

## State files

![State file map](https://raw.githubusercontent.com/ZacharyGeurts/NEXUS-Shield/main/docs/images/io-state-files.svg)

Production: `/var/lib/nexus-shield` · Dev: `.nexus-state/` — **never commit state**.

| File | Role |
|------|------|
| `threat-panel.json` | Panel publish blob |
| `firewall-trusted.tsv` | Trust memory |
| `firewall-blocks.tsv` | Active blocks |
| `hostess7-training-panel.json` | Training tracks |

---

## Panel API (sample)

![API surface](https://raw.githubusercontent.com/ZacharyGeurts/NEXUS-Shield/main/docs/images/io-api-surface.svg)

```bash
curl -s http://127.0.0.1:9477/api/status | jq .
curl -s http://127.0.0.1:9477/api/gatekeeper | jq .
curl -s http://127.0.0.1:9477/api/hostess7/training/bundle | jq .
```

| Route | Purpose |
|-------|---------|
| `/api/threat-panel.json` | Full panel state |
| `/api/field-host-desktop` | Host desktop app list + theme |
| `/api/field-host-freeze` | Host OS freeze (soft/mem/disk) |
| `/api/field-underlay-surface` | Drop / rise underlay |
| `/api/field-underlay` | Underlay F9 JSON |
| `/api/tristate-installer` | Tristate wizard API |
| `/api/hostess7/training/bundle` | Training tab |

### HTML pages (g16)

| Path | File |
|------|------|
| `/field` | `panel/field-desktop.html` |
| `/command` | `panel/threat-panel.html` |
| `/underlay-f9` | `panel/underlay-f9.html` |

---

## CLI

```bash
nexus trust 203.0.113.10
nexus block 203.0.113.10
nexus verify
./nexus.sh --no-browser
```