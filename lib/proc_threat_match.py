"""Token-accurate process matching — avoids substring false positives (e.g. xte in extension)."""
from __future__ import annotations


def proc_hits_marker(marker: str, comm: str, cmd: str) -> bool:
    m = marker.lower()
    if not m:
        return False
    c = (comm or "").lower()
    if c == m:
        return True
    # /proc/comm truncates at TASK_COMM_LEN (15) — match truncated comm to full marker only
    if len(c) == 15 and m.startswith(c):
        return True
    for token in (cmd or "").lower().split():
        base = token.rsplit("/", 1)[-1].strip(",;:\"'")
        if base == m:
            return True
    return False


def proc_hits_any(markers: frozenset[str], comm: str, cmd: str) -> str | None:
    for marker in markers:
        if proc_hits_marker(marker, comm, cmd):
            return marker
    return None