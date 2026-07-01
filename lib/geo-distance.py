#!/usr/bin/env pythong
"""Haversine distance — operator to threat peer (km/mi)."""
from __future__ import annotations

import math
from typing import Any


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return r * 2 * math.asin(min(1.0, math.sqrt(a)))


def format_distance(km: float | None, *, imperial: bool = False) -> str:
    if km is None or not math.isfinite(km):
        return "—"
    if imperial:
        mi = km * 0.621371
        if mi < 0.5:
            return f"{int(mi * 5280)} ft"
        if mi < 100:
            return f"{mi:.1f} mi"
        return f"{int(mi)} mi"
    if km < 1:
        return f"{int(km * 1000)} m"
    if km < 100:
        return f"{km:.1f} km"
    return f"{int(km)} km"


def distance_fields(
    op_lat: float | None,
    op_lon: float | None,
    peer_lat: float | None,
    peer_lon: float | None,
) -> dict[str, Any]:
    if None in (op_lat, op_lon, peer_lat, peer_lon):
        return {"distance_km": None, "distance_label": "—", "distance_mi": None}
    km = haversine_km(float(op_lat), float(op_lon), float(peer_lat), float(peer_lon))
    return {
        "distance_km": round(km, 2),
        "distance_mi": round(km * 0.621371, 2),
        "distance_label": format_distance(km),
        "distance_label_mi": format_distance(km, imperial=True),
    }


def main() -> int:
    import json
    import sys

    if len(sys.argv) < 5:
        print(json.dumps({"error": "usage: geo-distance.py <lat1> <lon1> <lat2> <lon2>"}))
        return 1
    out = distance_fields(
        float(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4])
    )
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())