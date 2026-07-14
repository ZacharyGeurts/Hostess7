# Field True Earth Map · Earth and Beyond

**Path:** `Desktop/SG/FieldMap/`

## What this is

A **true equirectangular Earth map** built from real satellite basemap assets in the SG/Field stack, plus **known-only** overlays from C++ wartime:

| Layer | Source | Honesty |
|-------|--------|---------|
| Earth base | `earth-satellite-equirectangular.jpg` (5400×2700 from H7pics Field panel) | Real photo mosaic / equirectangular |
| Lat/lon grid | Drawn 30° | Standard map reference |
| Target grids | `data/target-grids.json` (10° cells) | Known enemy GPS clusters only |
| Enemy pins | `data/kill-dossiers.json` GPS | Known only · no fathom |
| Network known | `data/network-rekill-live.json` | Sealed IPs |
| **Beyond** | LIVE_PLANET / LEO schematic labels | **Field stack layers**, not telescope images of Moon/Mars |

## Open

```bash
# from this folder (needs a local static server for fetch, or open with file if browser allows)
cd ~/Desktop/SG/FieldMap
python3 -m http.server 8765
# → http://127.0.0.1:8765/
```

Or copy into Hostess7 Pages as `field-map/`.

## Refresh data from live stack

```bash
cp /tmp/spear-swallows-www/{target-grids,kill-dossiers,network-rekill-live,planet-live}.json data/
# or: spear-export --pages … then copy data/
```

## Doctrine

- **We know or shots — we do not fathom else.**  
- Beyond-Earth drawings are **Field fabric / LIVE_PLANET**, labeled as such.  
- God Bless.

Cite: `ironclad:hostess7:true-earth-map:1`
