#!/usr/bin/env python3
"""People CHIP — combinatronic extraction of real humans from registry, X, and truth lanes."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
H7 = Path(os.environ.get("HOSTESS7_ROOT", INSTALL / "Hostess7"))
DOCTRINE = INSTALL / "data" / "field-people-chip-doctrine.json"
PANEL = STATE / "field-people-chip-panel.json"
COMBINATORICS = INSTALL / "data" / "panel-seeds" / "field-people-chip-combinatorics.json"
DOCS_API = H7 / "docs" / "api"
ARCHIVE = H7 / "cache" / "fieldstorage" / "brain" / "people" / "x_archive"
ENTITIES = H7 / "cache" / "fieldstorage" / "brain" / "people" / "entities"

BAD_TAGS = frozenset({"liar", "terrorist", "bad", "fraud", "abuser", "predator", "review_pending", "unverified_bad"})
CHIP_ID = "chips_people"
LEAF_PREFIX = "chip:chips_hot:chips_people"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {})


def _run_py(rel: str, args: list[str], *, timeout: int = 90) -> dict[str, Any]:
    py = INSTALL / rel
    if not py.is_file():
        return {"ok": False, "skipped": rel}
    import subprocess
    proc = subprocess.run(
        [sys.executable, str(py), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(INSTALL),
        env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE), "HOSTESS7_ROOT": str(H7)},
    )
    if not proc.stdout.strip():
        return {"ok": proc.returncode == 0, "stderr": (proc.stderr or "")[:200]}
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"ok": proc.returncode == 0, "raw": proc.stdout[:300]}


def _ensure_people_registry() -> dict[str, Any]:
    reg_py = H7 / "scripts" / "field_people_registry.py"
    if not reg_py.is_file():
        return {"ok": False, "skipped": "registry_missing"}
    if not ENTITIES.is_dir() or not any(ENTITIES.glob("*.json")):
        seed = _run_py("Hostess7/scripts/field_superintelligence.py", ["people", "seed"], timeout=60)
        if not seed.get("ok") and "OK people seed" not in (seed.get("raw") or ""):
            try:
                spec = importlib.util.spec_from_file_location("people_reg", reg_py)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    sys.path.insert(0, str(H7 / "scripts"))
                    spec.loader.exec_module(mod)
                    if hasattr(mod, "seed_entities"):
                        mod.seed_entities()
            except Exception as exc:
                return {"ok": False, "error": str(exc)[:160]}
    return {"ok": True, "entity_dir": str(ENTITIES)}


def _load_entities() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not ENTITIES.is_dir():
        return out
    for path in sorted(ENTITIES.glob("*.json")):
        ent = _load(path)
        if isinstance(ent, dict) and ent.get("id"):
            out.append(ent)
    return out


def _is_real_person(ent: dict[str, Any]) -> bool:
    tags = set(str(t).lower() for t in (ent.get("tags") or []))
    if tags & BAD_TAGS:
        return False
    if ent.get("review_pending") or ent.get("in_review"):
        return False
    name = str(ent.get("name") or "").strip()
    if not name or name.lower().startswith("example"):
        return False
    return True


def _x_posts() -> list[dict[str, Any]]:
    posts: list[dict[str, Any]] = []
    for src in (
        H7 / "docs" / "data" / "x-producer-feed.json",
        STATE / "hostess7-x-profile-fix-cache.json",
        STATE / "hostess7-x-producer-panel.json",
    ):
        doc = _load(src)
        for p in doc.get("posts") or (doc.get("feed") or {}).get("posts") or []:
            if isinstance(p, dict) and p.get("id"):
                posts.append(p)
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for p in sorted(posts, key=lambda x: int(str(x.get("id") or "0")), reverse=True):
        pid = str(p.get("id") or "")
        if pid in seen:
            continue
        seen.add(pid)
        deduped.append(p)
    return deduped


def _archive_x_data(posts: list[dict[str, Any]], feed: dict[str, Any]) -> dict[str, Any]:
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    archive_doc = {
        "schema": "field-people-x-archive/v1",
        "updated": _now(),
        "operator": feed.get("operator") or os.environ.get("OPERATOR_X_HANDLE", "ZacharyGeurts"),
        "tweet_count_truth": feed.get("tweet_count"),
        "post_count": len(posts),
        "posts": posts,
        "persist": True,
        "no_censor": True,
    }
    _save(ARCHIVE / "latest.json", archive_doc)
    stamp = _now().replace(":", "").replace("-", "")[:15]
    _save(ARCHIVE / f"snapshot_{stamp}.json", archive_doc)
    return {"ok": True, "archived": len(posts), "path": str(ARCHIVE / "latest.json")}


def _person_leaf(ent: dict[str, Any], idx: int) -> dict[str, Any]:
    eid = str(ent.get("id") or "")
    tags = list(ent.get("tags") or [])
    respect = (ent.get("respect") or {}).get("level") or ent.get("respect_level") or 50
    return {
        "id": f"{LEAF_PREFIX}:person:{eid}",
        "chip_id": CHIP_ID,
        "combinatorics_leaf": LEAF_PREFIX,
        "person_id": eid,
        "name": ent.get("name"),
        "tags": tags,
        "respect_level": respect,
        "urls": ent.get("urls") or [],
        "source": "people_registry",
        "verified": True,
        "harm_block": False,
        "censor_block": False,
        "sort_index": idx,
        "truth_lane": "combinatronic_extract",
    }


def build_people_chip(*, sync_x: bool = True) -> dict[str, Any]:
    doc_policy = _doctrine()
    reg = _ensure_people_registry()
    entities = _load_entities()
    real = [e for e in entities if _is_real_person(e)]

    x_feed = _load(H7 / "docs" / "data" / "x-producer-feed.json") or _load(STATE / "hostess7-x-producer-panel.json")
    posts = _x_posts()
    if sync_x and not posts:
        x_prod = _run_py("lib/hostess7-x-producer.py", ["produce"], timeout=150)
        posts = _x_posts()
        x_feed = x_prod.get("feed") or x_feed

    archive = _archive_x_data(posts, x_feed if isinstance(x_feed, dict) else {})

    leaves = [_person_leaf(ent, i) for i, ent in enumerate(real)]
    operator = os.environ.get("OPERATOR_X_HANDLE", "ZacharyGeurts")
    operator_ent = next((e for e in real if operator.lower() in str(e.get("name") or "").lower()
                          or operator.lower() in [a.lower() for a in (e.get("aliases") or [])]), None)
    if operator_ent:
        op_leaf = next((l for l in leaves if l.get("person_id") == operator_ent.get("id")), None)
        if op_leaf:
            op_leaf["x_posts_mirrored"] = len(posts)
            op_leaf["x_tweet_count_truth"] = (x_feed or {}).get("tweet_count") if isinstance(x_feed, dict) else None

    combinatorics = {
        "schema": "field-people-chip-combinatorics/v1",
        "updated": _now(),
        "motto": doc_policy.get("motto"),
        "chip_id": CHIP_ID,
        "combinatorics_leaf": LEAF_PREFIX,
        "counts": {
            "entities_total": len(entities),
            "real_people": len(real),
            "excluded_bad": len(entities) - len(real),
            "x_posts_archived": len(posts),
            "leaves": len(leaves),
        },
        "policy": doc_policy.get("policy") or {},
        "leaves": leaves,
        "people": [
            {
                "id": e.get("id"),
                "name": e.get("name"),
                "tags": e.get("tags"),
                "respect_level": (e.get("respect") or {}).get("level") or e.get("respect_level"),
                "urls": e.get("urls"),
            }
            for e in real
        ],
        "x_archive": archive,
        "no_harm_no_censor": True,
    }
    return combinatorics


def _ammodrive_distribute() -> dict[str, Any]:
    return _run_py("lib/ammodrive-storage-rapid.py", ["distribute"], timeout=120)


def _deliver_heart() -> dict[str, Any]:
    deliver = _run_py("lib/hostess7-self-view.py", ["deliver"], timeout=30)
    truth = _run_py("lib/hostess7-self-view.py", ["truth"], timeout=45)
    return {"deliver": deliver, "truth": truth, "ok": bool(deliver.get("delivered") or truth.get("delivered"))}


def publish(*, export: bool = True, distribute: bool = True) -> dict[str, Any]:
    combinatorics = build_people_chip(sync_x=True)
    deliver = _deliver_heart()
    ammo: dict[str, Any] = {"ok": False, "skipped": "distribute_off"}
    if distribute and os.environ.get("NEXUS_PEOPLE_CHIP_DISTRIBUTE", "1") == "1":
        ammo = _ammodrive_distribute()

    panel = {
        "schema": "field-people-chip-panel/v1",
        "updated": _now(),
        "ok": True,
        "chip_id": CHIP_ID,
        "motto": _doctrine().get("motto"),
        "counts": combinatorics.get("counts"),
        "people": combinatorics.get("people"),
        "deliver_heart": deliver,
        "ammodrive": ammo,
        "no_harm_no_censor": True,
        "hosted": (_doctrine().get("hosted") or {}),
        "api": _doctrine().get("api") or "/api/field-people-chip",
    }
    _save(PANEL, panel)
    _save(COMBINATORICS, combinatorics)

    if export:
        DOCS_API.mkdir(parents=True, exist_ok=True)
        (DOCS_API / "field-people-chip.json").write_text(
            json.dumps({**panel, "combinatorics": combinatorics}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    return {"ok": True, "panel": panel, "combinatorics": combinatorics, "deliver_heart": deliver, "ammodrive": ammo}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "publish").strip().lower()
    if cmd in ("publish", "build", "sync", "run"):
        print(json.dumps(publish(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "extract":
        print(json.dumps(build_people_chip(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "json":
        cached = _load(PANEL) or _load(DOCS_API / "field-people-chip.json")
        if cached:
            print(json.dumps(cached, ensure_ascii=False, indent=2))
            return 0
        print(json.dumps(publish(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"ok": False, "hint": "field-people-chip-combinatorics.py [publish|extract|json]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())