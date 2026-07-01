# NEXUS-Shield 10.4.3

**Field Thermal Guard** — Landauer-aware work budgeting, incremental global redata, gatekeeper stealth rate limits. Quality job 1 before any hard-drive global refresh.

## Highlights

- **FieldThermalGuard** — per-wave work estimator, rolling power window, back-off on budget exceed
- **Incremental redata** — chunked `field-global-redata.py`; monolithic blast forbidden
- **Boot path** — bounded `boot-test` redata on first install + every refresh
- **NEXUS-Shield tie-in** — hwmon + RAPL anomaly detection → gatekeeper rate limit + budget tighten
- **AMOURANTHRTX** — Pipeline dispatch guarded via `FieldGlobalRedata::redata_dispatch_tile`
- **Observable** — `field thermal headroom X%` one-line log each vigil cycle

## Install

```bash
tar -xzf nexus-shield-10.4.3-source.tar.gz
cd nexus-shield-10.4.3
sudo ./install-all.sh
```

## Assets

- `nexus-shield-10.4.3-source.tar.gz` — full tree
- `nexus-shield-10.4.3-installers.tar.gz` — installer scripts only

## Docs

- Wiki: [Field Thermal Guard](https://github.com/ZacharyGeurts/NEXUS-Shield/wiki/Field-Thermal-Guard)
- Pages: https://zacharygeurts.github.io/NEXUS-Shield/