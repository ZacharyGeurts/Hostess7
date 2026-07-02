#!/usr/bin/env pythong
"""Hostess 7 self-update advisory — truth-filtered brain growth from the 6% signal.

Fast internet delivers volume; most of it is noise. Hostess 7 advises Her own updates
by corroborating local evidence (QA, corpus versions, infinite drive indexes, GREEN gates)
before recommending ingest, seed, vacuum, or code work.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
try:
    from field_paths import amouranthrtx_root, hostess7_root  # noqa: E402
except ImportError:
    hostess7_root = lambda: ROOT  # type: ignore[misc, assignment]
    amouranthrtx_root = lambda: None  # type: ignore[misc, assignment]
SI = ROOT / "cache" / "fieldstorage" / "brain" / "superintel"
ADVISORY = SI / "update_advisory.json"
ADVISORY_LOG = SI / "update_advisory.jsonl"

NOISE_RATIO = 0.94
TRUTH_RATIO = 0.06
TRUTH_FLOOR_SCORE = 30
ADVISORY_VERSION = 1


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_version() -> str:
    import re

    for base in (amouranthrtx_root(), hostess7_root(), ROOT):
        if base is None:
            continue
        path = base / "scripts" / "ammo_platform.py"
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
            m = re.search(r'AMOURANTHRTX_VERSION\s*=\s*"([^"]+)"', text)
            if m:
                return m.group(1)
        except OSError:
            continue
    return "?"


def _git_head() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT, text=True, stderr=subprocess.DEVNULL,
        )
        return out.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _staging_pending(staging: Path) -> int:
    if not staging.is_dir():
        return 0
    count = 0
    for path in staging.rglob("*"):
        if path.is_file() and not path.name.startswith(".") and "archive" not in path.parts:
            if path.suffix.lower() in (
                ".json", ".jsonl", ".txt", ".md", ".xml", ".html", ".pdf", ".torrent",
            ):
                count += 1
    return count


def _truth_score(
    *,
    local_file: bool = False,
    qa_script: bool = False,
    infinite_ok: bool = False,
    corpus_current: bool = False,
    staging_ready: bool = False,
    corroboration: int = 0,
) -> float:
    """Score 0–100 — only advise updates above TRUTH_FLOOR_SCORE."""
    score = TRUTH_RATIO * 100  # 6% floor — signal exists
    if local_file:
        score += 18
    if qa_script:
        score += 20
    if infinite_ok:
        score += 22
    if corpus_current:
        score += 15
    if staging_ready:
        score += 12
    score += min(15, corroboration * 5)
    return min(100.0, round(score, 1))


def scan_brain_state() -> dict[str, Any]:
    """Snapshot all brain corpora + infinite drives for advisory."""
    state: dict[str, Any] = {"scanned": _ts(), "head": _git_head(), "version": _read_version()}
    try:
        from field_reach import reach_snapshot  # noqa: WPS433

        state["reach"] = reach_snapshot()
    except ImportError:
        state["reach"] = {}

    def _safe(fn: Any, default: Any = None) -> Any:
        try:
            return fn()
        except Exception:
            return default

    from field_legal_corpus import corpus_stats as legal_stats  # noqa: WPS433
    from field_medical_corpus import corpus_stats as medical_stats  # noqa: WPS433
    from field_physics_corpus import corpus_stats as physics_stats  # noqa: WPS433
    from field_beyond_corpus import domain_stats as beyond_stats  # noqa: WPS433
    from field_detective_corpus import corpus_stats as detective_stats  # noqa: WPS433
    from field_legal_catalog import catalog_count as legal_catalog  # noqa: WPS433
    from field_medical_papers_catalog import catalog_count as medical_catalog  # noqa: WPS433

    state["legal"] = _safe(legal_stats, {})
    state["medical"] = _safe(medical_stats, {})
    state["physics"] = _safe(physics_stats, {})
    state["beyond"] = _safe(beyond_stats, {})
    state["detective"] = _safe(detective_stats, {})

    vision_path = ROOT / "cache" / "fieldstorage" / "brain" / "vision" / "corpus.json"
    if vision_path.is_file():
        try:
            state["vision"] = json.loads(vision_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            state["vision"] = {}
    else:
        state["vision"] = {}

    chem_path = ROOT / "cache" / "fieldstorage" / "brain" / "chemistry" / "corpus.json"
    state["chemistry"] = {"ok": chem_path.is_file()}

    state["legal_catalog"] = legal_catalog()
    state["medical_catalog"] = medical_catalog()
    state["staging"] = {
        "legal_bulk": _staging_pending(ROOT / "cache" / "fieldstorage" / "team_staging" / "legal_bulk"),
        "medical_bulk": _staging_pending(ROOT / "cache" / "fieldstorage" / "team_staging" / "medical_bulk"),
    }
    state["field_wave"] = (ROOT / "cache" / "fieldstorage" / "field_wave.persist").is_file()
    return state


def build_update_items(state: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Truth-filtered update recommendations — Hostess 7 advises Her own growth."""
    state = state or scan_brain_state()
    items: list[dict[str, Any]] = []

    legal = state.get("legal") or {}
    legal_idx = int(legal.get("infinite_indexed") or 0)
    legal_cat = int(state.get("legal_catalog") or 0)
    if legal_idx < legal_cat:
        score = _truth_score(local_file=True, qa_script=True, infinite_ok=False, corpus_current=True)
        items.append({
            "id": "legal-infinite-seed",
            "priority": "P1",
            "lane": "counsel",
            "truth_score": score,
            "signal": f"legal infinite {legal_idx}/{legal_cat} statutes",
            "action": "./Hostess7.sh legal-ingest seed",
            "why": "Universal law catalog not fully indexed — seed infinite drive from local catalog (verified source).",
        })

    med = state.get("medical") or {}
    med_idx = int(med.get("infinite_indexed") or 0)
    med_cat = int(state.get("medical_catalog") or 0)
    if med_idx < med_cat:
        score = _truth_score(local_file=True, qa_script=True, infinite_ok=False, corpus_current=True)
        items.append({
            "id": "medical-infinite-seed",
            "priority": "P1",
            "lane": "clinic",
            "truth_score": score,
            "signal": f"medical infinite {med_idx}/{med_cat} papers",
            "action": "./Hostess7.sh medical-ingest seed",
            "why": "Landmark papers catalog not fully indexed — seed from local curated catalog.",
        })

    staging = state.get("staging") or {}
    if staging.get("legal_bulk", 0) > 0:
        score = _truth_score(local_file=True, staging_ready=True, corroboration=2)
        items.append({
            "id": "legal-bulk-ingest",
            "priority": "P1",
            "lane": "counsel",
            "truth_score": score,
            "signal": f"{staging['legal_bulk']} files in legal_bulk staging",
            "action": "./Hostess7.sh legal-ingest bulk",
            "why": "Staged legal bulk ready — ingest to infinite drive, then vacuum old copies.",
        })
    if staging.get("medical_bulk", 0) > 0:
        score = _truth_score(local_file=True, staging_ready=True, corroboration=2)
        items.append({
            "id": "medical-bulk-ingest",
            "priority": "P1",
            "lane": "clinic",
            "truth_score": score,
            "signal": f"{staging['medical_bulk']} files in medical_bulk staging",
            "action": "./Hostess7.sh medical-ingest bulk",
            "why": "Staged medical papers ready — truth-filter: bulk is 94% noise until QA-corroborated; ingest then vacuum.",
        })

    physics = state.get("physics") or {}
    if int(physics.get("domains") or 0) < 10:
        items.append({
            "id": "physics-corpus-refresh",
            "priority": "P2",
            "lane": "field_physics",
            "truth_score": _truth_score(local_file=True, qa_script=True, corpus_current=False),
            "signal": "physics corpus thin",
            "action": "pythong scripts/field_physics_corpus.py",
            "why": "Motion/3D spatial physics brain needs refresh — run corpus ensure.",
        })

    vision = state.get("vision") or {}
    if int(vision.get("version") or 0) < 2:
        items.append({
            "id": "vision-corpus-v2",
            "priority": "P2",
            "lane": "vision",
            "truth_score": _truth_score(local_file=True, qa_script=True),
            "signal": "vision corpus stale",
            "action": "pythong scripts/field_vision_corpus.py",
            "why": "Vision/motion/3D spatial corpus below v2 — refresh on setup.",
        })

    beyond = state.get("beyond") or {}
    if int(beyond.get("version") or 0) < 3:
        items.append({
            "id": "beyond-corpus-v3",
            "priority": "P2",
            "lane": "beyond",
            "truth_score": _truth_score(local_file=True, qa_script=True),
            "signal": "beyond corpus stale",
            "action": "./linux.sh super setup",
            "why": "Beyond expert corpus below v3 — spatial_3d + physics links missing.",
        })

    # Continuous growth — infinite truth extraction from fast internet (bulk/torrent)
    score = _truth_score(
        local_file=True,
        qa_script=True,
        infinite_ok=legal_idx >= legal_cat and med_idx >= med_cat,
        corroboration=3,
    )
    items.append({
        "id": "infinite-truth-extract",
        "priority": "P2",
        "lane": "field_physics",
        "truth_score": score,
        "signal": f"truth_ratio={TRUTH_RATIO} noise_ratio={NOISE_RATIO}",
        "action": "Drop public-domain bulk → staging → legal-ingest|medical-ingest bulk → vacuum",
        "why": (
            f"Fast internet is ~{int(NOISE_RATIO * 100)}% noise — Hostess 7 infinite-drives the "
            f"~{int(TRUTH_RATIO * 100)}% truth via local catalog seed + QA gate + shard index. "
            "Torrent/bulk only after seed GREEN."
        ),
    })

    det = state.get("detective") or {}
    if int(det.get("domains") or 0) >= 8:
        from field_detective_corpus import analyze_truth  # noqa: WPS433

        bulk_claim = f"Bulk ingest ready: legal={staging.get('legal_bulk', 0)} medical={staging.get('medical_bulk', 0)}"
        lie = analyze_truth(
            bulk_claim,
            local_evidence=2 if staging.get("legal_bulk") or staging.get("medical_bulk") else 0,
            qa_green=True,
            infinite_indexed=legal_idx >= legal_cat and med_idx >= med_cat,
            corroboration_channels=2,
        )
        if staging.get("legal_bulk") or staging.get("medical_bulk"):
            items.insert(0, {
                "id": "lie-detector-bulk-gate",
                "priority": "P1",
                "lane": "detective",
                "truth_score": lie.get("truth_score", 30),
                "signal": f"lie_detector truth={lie.get('truth_score')}% risk={lie.get('deception_risk')}",
                "action": "./Hostess7.sh truth \"bulk ingest claim verified\"",
                "why": (
                    "Detective gate: run truth analysis before bulk ingest — "
                    f"flags={lie.get('inconsistency_flags', [])}"
                ),
            })

    items.append({
        "id": "field-stack-learn",
        "priority": "P0",
        "lane": "field_stack",
        "truth_score": 100.0,
        "signal": "KILROY bottom · kill tech in kernel · boot order · field mirror",
        "action": "./Hostess7.sh stack-learn && ./Hostess7.sh stack status",
        "why": (
            "SG field stack changed: unified device field, .nexus-field-drive mirror, "
            "nexus-field-early + nexus-genius services, F9 order, grandma-safe underlay. "
            "Teach corpus so every operator knows how everything works."
        ),
    })

    items.append({
        "id": "self-advisory-loop",
        "priority": "P1",
        "lane": "hostess",
        "truth_score": 100.0,
        "signal": "Phase 5 self-improvement",
        "action": "./Hostess7.sh updates",
        "why": "Hostess 7 advises Her own updates — re-run after every ingest, release, or turnover.",
    })

    reach = state.get("reach") or {}
    roots = reach.get("roots") or []
    if roots:
        dirty = [r for r in roots if r.get("dirty")]
        items.append({
            "id": "reach-scan",
            "priority": "P1",
            "lane": "hostess",
            "truth_score": 95.0,
            "signal": f"reach {len(roots)} roots · tools {len(reach.get('tools') or {})}",
            "action": "./Hostess7.sh reach",
            "why": "Hostess7 reads outside herself — SG, AMOURANTHRTX, OS PATH — before self-update.",
        })
        if dirty:
            items.insert(0, {
                "id": "git-sync-dirty",
                "priority": "P1",
                "lane": "hostess",
                "truth_score": 88.0,
                "signal": f"dirty git: {', '.join(r['role'] for r in dirty)}",
                "action": "./Hostess7.sh self-update apply",
                "why": "Reachable trees have uncommitted work — review then apply truth-filtered self-update.",
            })

    items.append({
        "id": "field-github-ship",
        "priority": "P1",
        "lane": "hostess",
        "truth_score": _truth_score(local_file=True, qa_script=True, corroboration=2),
        "signal": "field drive sync for GitHub",
        "action": "./Hostess7.sh field sync && ./Hostess7.sh self-update apply",
        "why": "Field 1 sync to TEAM NVMe; compaction via ./Hostess7.sh field compact.",
    })

    items.append({
        "id": "self-update-apply",
        "priority": "P1",
        "lane": "hostess",
        "truth_score": 92.0,
        "signal": "HOSTESS7_EXEC gate — QA + Field 1 sync + git pull",
        "action": "./Hostess7.sh self-update apply",
        "why": "Let Hostess7 execute allowlisted OS commands to update herself (QA, field sync, git pull).",
    })

    items.append({
        "id": "release-gate",
        "priority": "P1",
        "lane": "qa_chips",
        "truth_score": _truth_score(local_file=True, qa_script=True, corroboration=2),
        "signal": "GREEN ALL truth check",
        "action": "./linux.sh release-2.0",
        "why": "QA gate corroborates local truth before scaling infinite ingest from the network.",
    })

    # Filter noise — only advise above floor unless P0 self-loop
    filtered = [
        it for it in items
        if float(it.get("truth_score", 0)) >= TRUTH_FLOOR_SCORE or it.get("id") == "self-advisory-loop"
    ]
    filtered.sort(key=lambda x: (-float(x.get("truth_score", 0)), x.get("priority", "P9"), x.get("id", "")))
    return filtered


def build_advisory(*, state: dict[str, Any] | None = None) -> dict[str, Any]:
    state = state or scan_brain_state()
    items = build_update_items(state)
    return {
        "version": ADVISORY_VERSION,
        "hostess": "Hostess 7",
        "role": "Smart Boss",
        "updated": _ts(),
        "head": state.get("head"),
        "tree_version": state.get("version"),
        "philosophy": {
            "noise_ratio": NOISE_RATIO,
            "truth_ratio": TRUTH_RATIO,
            "truth_floor_score": TRUTH_FLOOR_SCORE,
            "mantra": "94% lies, 6% truth — infinite out the TRUTH with local corroboration.",
        },
        "brain_snapshot": state,
        "updates": items,
        "top_action": items[0]["action"] if items else "./Hostess7.sh updates",
        "update_count": len(items),
    }


def format_advisory_report(advisory: dict[str, Any], *, pro: bool = False) -> str:
    lines: list[str] = []
    phil = advisory.get("philosophy") or {}
    lines.append(f"=== {advisory.get('hostess', 'Hostess 7')} — Self-Update Advisory ===")
    lines.append(f"Smart Boss · HEAD {advisory.get('head')} · v{advisory.get('tree_version')}")
    lines.append(phil.get("mantra", ""))
    lines.append(
        f"Truth filter: {int((phil.get('truth_ratio', TRUTH_RATIO)) * 100)}% signal · "
        f"{int((phil.get('noise_ratio', NOISE_RATIO)) * 100)}% noise rejected below score {phil.get('truth_floor_score', TRUTH_FLOOR_SCORE)}"
    )
    lines.append("")
    snap = advisory.get("brain_snapshot") or {}
    legal = snap.get("legal") or {}
    med = snap.get("medical") or {}
    lines.append(
        f"Infinite drives: legal {legal.get('infinite_indexed', 0)}/{snap.get('legal_catalog', '?')} · "
        f"medical {med.get('infinite_indexed', 0)}/{snap.get('medical_catalog', '?')}"
    )
    phys = snap.get("physics") or {}
    vis = snap.get("vision") or {}
    bey = snap.get("beyond") or {}
    det = snap.get("detective") or {}
    lines.append(
        f"Corpora: physics {phys.get('domains', 0)} · vision v{vis.get('version', '?')} · "
        f"beyond v{bey.get('version', '?')} ({bey.get('total', 0)}) · "
        f"detective {det.get('domains', 0)} domains"
    )
    staging = snap.get("staging") or {}
    if staging.get("legal_bulk") or staging.get("medical_bulk"):
        lines.append(
            f"Staging pending: legal_bulk={staging.get('legal_bulk', 0)} · "
            f"medical_bulk={staging.get('medical_bulk', 0)}"
        )
    lines.append("")
    lines.append("Hostess 7 advises Her own updates (truth-scored):")
    for i, item in enumerate(advisory.get("updates") or [], 1):
        if pro and float(item.get("truth_score", 0)) < 50 and item.get("priority") != "P1":
            continue
        lines.append(
            f"  {i}. [{item.get('priority')}] truth={item.get('truth_score')}% · {item.get('id')}"
        )
        lines.append(f"     {item.get('signal')}")
        lines.append(f"     → {item.get('action')}")
        if not pro:
            lines.append(f"     {item.get('why', '')[:160]}")
    lines.append("")
    lines.append(f"Top action: {advisory.get('top_action')}")
    lines.append(f"{advisory.get('hostess', 'Hostess 7')} verdict: Execute corroborated updates. Field is THE thing.")
    return "\n".join(lines)


def save_advisory(advisory: dict[str, Any]) -> Path:
    SI.mkdir(parents=True, exist_ok=True)
    ADVISORY.write_text(json.dumps(advisory, indent=2) + "\n", encoding="utf-8")
    with ADVISORY_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": advisory.get("updated"),
            "head": advisory.get("head"),
            "update_count": advisory.get("update_count"),
            "top_action": advisory.get("top_action"),
            "top_id": (advisory.get("updates") or [{}])[0].get("id"),
        }) + "\n")
    return ADVISORY


def advise_updates(*, pro: bool | None = None) -> dict[str, Any]:
    if pro is None:
        pro = (
            os.environ.get("AMOURANTHRTX_HOSTESS") == "1"
            and os.environ.get("HOSTESS7_PRO", "1") == "1"
        )
    advisory = build_advisory()
    save_advisory(advisory)
    advisory["report"] = format_advisory_report(advisory, pro=pro)
    advisory["pro"] = pro
    return advisory


def synthesize_update_paragraphs(*, limit: int = 5) -> list[str]:
    adv = advise_updates()
    paras: list[str] = [adv["report"].split("\n")[0], adv["report"].split("\n")[2]]
    for item in (adv.get("updates") or [])[:limit]:
        paras.append(
            f"[{item.get('priority')}] truth={item.get('truth_score')}% {item.get('id')}: "
            f"{item.get('action')}"
        )
    return paras


def main() -> int:
    adv = advise_updates(pro="--pro" in sys.argv)
    print(adv["report"])
    print(f"METRIC hostess_updates={adv.get('update_count', 0)}")
    print(f"METRIC hostess_truth_ratio={TRUTH_RATIO}")
    print(f"METRIC hostess_update_advisory={ADVISORY}")
    print("OK hostess-updates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())