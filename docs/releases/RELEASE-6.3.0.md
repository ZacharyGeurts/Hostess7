# NEXUS-Shield 6.3.0 — Midnight Contrast UI

## Theme
- **Midnight v6.3** — ~50% higher contrast dark palette across the threat panel
- New `panel/assets/nexus-theme.css` — unified map chrome, US dashboard, Leaflet controls
- Deeper blacks, brighter accent hues (`--internet`, `--gold`, `--ok`, `--threat`)

## Maps
- **`nexus-map.js`** — shared Leaflet bootstrap for all panel maps
  - Mousewheel zoom (centered, debounced)
  - Drag pan with grab cursor
  - Wheel capture — no accidental page scroll over maps
  - Bottom-right zoom controls, `invalidateSize` scheduling
  - `resolveAnchor` — operator GPS → entity centroid → field default (Gladstone MI)
  - `varianceExtents` — dominant ENU axis (height/U often has most spread)
  - `fitLatLngs` / `flyToAnchor` / `primeMapPanel` / `watchResize`
- **`.map-viewport`** — fixed `min(58vh, 580px)` height so Leaflet always has real pixels
- Host Attack globe, Precision map, Terror spiderweb, Thermal Earth — all use `NexusMap`
- Operator blue pin on Host Attack map when GPS is set
- Precision local ENU patch scales to entity variance (not fixed ±20 mm only)
- **Precision spiderweb canvas** — scroll zoom + drag pan

## US field layout
- Redesigned dashboard: hero header + stats bar, rundown panel, main network column + sidebar cards
- Responsive — network meters stack on narrow viewports

## RE-KILL (from 6.2 carry)
- Constant RE-KILL cycle when hostile registry has entries (packet loop + kill-detect)

## Hostess7 GitHub
- `./Hostess7.sh github status|invite|bootstrap` for `@hostess7` bot collaborator flow