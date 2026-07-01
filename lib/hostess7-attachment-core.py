#!/usr/bin/env pythong
"""Hostess7 attachments — mount, vision inspect, learn proficiency like native hands."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(_LIB.parent)))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", str(INSTALL / ".nexus-state")))
DOCTRINE = INSTALL / "data" / "hostess7-attachment-doctrine.json"
REGISTRY = STATE / "hostess7-attachment-registry.json"
PANEL = STATE / "hostess7-attachment-panel.json"
LEDGER = STATE / "hostess7-attachment-ledger.jsonl"


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _h7s_read_json(path: Path, default: Any = None) -> Any:
    fs_py = INSTALL / "lib" / "field-h7s-fs.py"
    if path.suffix.lower() == ".json" and fs_py.is_file():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("_h7s_fs_io", fs_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "read_json"):
                    return mod.read_json(path, default=default)
        except Exception:
            pass
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}

def _load(path: Path, default: Any = None) -> Any:
    return _h7s_read_json(path, default=default)


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append_ledger(row: dict[str, Any]) -> None:
    try:
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({**row, "ts": _ts()}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _hand_core() -> Any | None:
    py = _LIB / "hostess7-hand-core.py"
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location("hand_core_attach", py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _ocr_core() -> Any | None:
    py = _LIB / "final-eye-ocr-core.py"
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location("ocr_core_attach", py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _sense_core() -> Any | None:
    py = _LIB / "hostess7-sense-core.py"
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location("sense_core_attach", py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _catalog() -> dict[str, dict[str, Any]]:
    doc = _load(DOCTRINE, {})
    return {a["id"]: a for a in doc.get("catalog") or [] if a.get("id")}


def load_registry() -> dict[str, Any]:
    doc = _load(REGISTRY, {})
    mounted = doc.get("mounted") or {}
    learned = doc.get("learned") or {}
    return {
        "schema": "hostess7-attachment-registry/v1",
        "updated": doc.get("updated") or _ts(),
        "mounted": mounted,
        "learned": learned,
        "custom": doc.get("custom") or [],
    }


def save_registry(reg: dict[str, Any]) -> None:
    reg["updated"] = _ts()
    _save(REGISTRY, reg)


def _attachment_row(att_id: str) -> dict[str, Any] | None:
    cat = _catalog()
    reg = load_registry()
    if att_id in cat:
        row = dict(cat[att_id])
        learned = (reg.get("learned") or {}).get(att_id) or {}
        row.update(learned)
        return row
    for c in reg.get("custom") or []:
        if c.get("id") == att_id:
            learned = (reg.get("learned") or {}).get(att_id) or {}
            return {**c, **learned}
    return None


def list_attachments() -> list[dict[str, Any]]:
    reg = load_registry()
    cat = _catalog()
    out: list[dict[str, Any]] = []
    for aid, spec in cat.items():
        mount = (reg.get("mounted") or {}).get(aid)
        learned = (reg.get("learned") or {}).get(aid) or {}
        out.append({
            **spec,
            "mounted": mount,
            "mount_point": mount or spec.get("default_mount"),
            "proficiency": float(learned.get("proficiency") or 0),
            "fluent": float(learned.get("proficiency") or 0) >= 0.72,
            "mastered": float(learned.get("proficiency") or 0) >= 0.95,
            "last_inspect": learned.get("last_inspect"),
            "vision_match": learned.get("vision_match"),
        })
    for c in reg.get("custom") or []:
        aid = c.get("id")
        if not aid or aid in cat:
            continue
        learned = (reg.get("learned") or {}).get(aid) or {}
        out.append({
            **c,
            "mounted": (reg.get("mounted") or {}).get(aid),
            "proficiency": float(learned.get("proficiency") or 0),
            "last_inspect": learned.get("last_inspect"),
        })
    return out


def mount_attachment(att_id: str, *, mount_point: str | None = None) -> dict[str, Any]:
    row = _attachment_row(att_id)
    if not row:
        return {"ok": False, "error": "unknown_attachment", "id": att_id}
    mp = mount_point or row.get("default_mount") or row.get("mount")
    if not mp:
        return {"ok": False, "error": "mount_point_required"}
    doctrine = _load(DOCTRINE, {})
    if mp not in (doctrine.get("mount_points") or []):
        return {"ok": False, "error": "invalid_mount_point", "mount_point": mp}
    reg = load_registry()
    reg.setdefault("mounted", {})[att_id] = mp
    save_registry(reg)
    hand = _hand_core()
    if hand and hasattr(hand, "set_grip"):
        side = "left" if mp.endswith("_l") or mp == "hand_l" else "right"
        if "hand" in mp:
            hand.set_grip(side, str(row.get("grip") or "precision"))
    _append_ledger({"event": "mount", "id": att_id, "mount": mp})
    return {"ok": True, "id": att_id, "mount_point": mp, "attachment": row}


def unmount_attachment(att_id: str) -> dict[str, Any]:
    reg = load_registry()
    mounted = reg.get("mounted") or {}
    if att_id not in mounted:
        return {"ok": False, "error": "not_mounted", "id": att_id}
    mp = mounted.pop(att_id)
    save_registry(reg)
    _append_ledger({"event": "unmount", "id": att_id, "mount": mp})
    return {"ok": True, "id": att_id, "former_mount": mp}


def _vision_text_from_path(path: str) -> tuple[str, dict[str, Any]]:
    ocr = _ocr_core()
    if not ocr:
        return "", {"error": "ocr_core_missing"}
    fp = Path(path).expanduser()
    if fp.is_file() and hasattr(ocr, "ocr_via_hostess7"):
        row = ocr.ocr_via_hostess7({"action": "ocr_image", "path": str(fp), "label": f"attachment_{fp.stem}"})
        return str(row.get("text") or row.get("ocr") or ""), row
    return "", {"error": "file_missing", "path": str(fp)}


def _vision_text_look() -> tuple[str, dict[str, Any]]:
    ocr = _ocr_core()
    if ocr and hasattr(ocr, "ocr_via_hostess7"):
        look = ocr.ocr_via_hostess7({"action": "final_eye", "subaction": "look", "prefer": "auto"})
        img = look.get("image") or look.get("h7_file") or look.get("ocr_file")
        if img and Path(str(img)).is_file():
            return _vision_text_from_path(str(img))
        text = str(look.get("ocr") or look.get("text") or "")
        return text, look
    sense = _sense_core()
    if sense and hasattr(sense, "sense_dispatch"):
        row = sense.sense_dispatch({"action": "look", "channel": "eye"})
        text = str(row.get("ocr") or row.get("text") or "")
        return text, row
    return "", {"error": "vision_unavailable"}


def _match_attachment(text: str, att_id: str | None = None) -> dict[str, Any]:
    blob = (text or "").lower()
    if not blob.strip():
        return {"match": False, "score": 0.0, "tags": []}
    if att_id:
        row = _attachment_row(att_id)
        tags = [t.lower() for t in (row or {}).get("vision_tags") or []]
        hits = [t for t in tags if t in blob]
        score = len(hits) / max(len(tags), 1)
        return {"match": score >= 0.25, "score": round(score, 3), "tags": hits, "id": att_id}
    best_id, best_score, best_hits = "", 0.0, []
    for aid, spec in _catalog().items():
        tags = [t.lower() for t in spec.get("vision_tags") or []]
        hits = [t for t in tags if t in blob]
        score = len(hits) / max(len(tags), 1)
        if score > best_score:
            best_id, best_score, best_hits = aid, score, hits
    return {"match": best_score >= 0.25, "score": round(best_score, 3), "tags": best_hits, "id": best_id or None}


def inspect_attachment(*, att_id: str | None = None, path: str | None = None, look: bool = True) -> dict[str, Any]:
    """Look at mounted attachment — OCR + tag match."""
    meta: dict[str, Any] = {}
    if path:
        text, meta = _vision_text_from_path(path)
    elif look:
        text, meta = _vision_text_look()
    else:
        text, meta = "", {"skipped": True}
    match = _match_attachment(text, att_id)
    reg = load_registry()
    reg.setdefault("learned", {})
    target = att_id or match.get("id")
    if target:
        entry = reg["learned"].setdefault(target, {"proficiency": 0.0, "trained_ticks": 0})
        entry["last_inspect"] = _ts()
        entry["vision_match"] = match
        entry["ocr_snippet"] = (text or "")[:400]
        if match.get("match"):
            bonus = float((_load(DOCTRINE, {}).get("vision_learn") or {}).get("proficiency_match_bonus") or 0.04)
            entry["proficiency"] = round(min(1.0, float(entry.get("proficiency") or 0) + bonus), 4)
        save_registry(reg)
    _append_ledger({"event": "inspect", "id": target, "match": match.get("match"), "score": match.get("score")})
    return {
        "ok": True,
        "action": "inspect",
        "attachment_id": target,
        "ocr_text": (text or "")[:800],
        "vision": meta,
        "match": match,
        "learned": (reg.get("learned") or {}).get(target or "", {}),
    }


def register_attachment(spec: dict[str, Any]) -> dict[str, Any]:
    label = str(spec.get("label") or spec.get("name") or "").strip()
    if not label:
        return {"ok": False, "error": "label_required"}
    aid = str(spec.get("id") or "").strip() or hashlib.sha256(label.lower().encode()).hexdigest()[:12]
    row = {
        "id": aid,
        "label": label,
        "kind": str(spec.get("kind") or "custom"),
        "default_mount": spec.get("default_mount") or spec.get("mount") or "hand_r",
        "grip": str(spec.get("grip") or "precision"),
        "vision_tags": spec.get("vision_tags") or [w for w in re.findall(r"[a-z]{3,}", label.lower())[:6]],
        "learn_primitives": spec.get("learn_primitives") or ["precision_aim", "point", "release"],
        "hand_equivalence": float(spec.get("hand_equivalence") or 0.75),
    }
    reg = load_registry()
    custom = reg.setdefault("custom", [])
    custom = [c for c in custom if c.get("id") != aid]
    custom.append(row)
    reg["custom"] = custom
    save_registry(reg)
    return {"ok": True, "attachment": row}


def learn_attachment(att_id: str, *, ticks: int | None = None) -> dict[str, Any]:
    """Train attachment proficiency — same cadence as hand fluency."""
    row = _attachment_row(att_id)
    if not row:
        return {"ok": False, "error": "unknown_attachment", "id": att_id}
    doctrine = _load(DOCTRINE, {})
    vl = doctrine.get("vision_learn") or {}
    n = int(ticks or vl.get("train_ticks_default") or 48)
    hand = _hand_core()
    primitives = row.get("learn_primitives") or ["point", "precision_aim", "release"]
    mp = (load_registry().get("mounted") or {}).get(att_id) or row.get("default_mount") or "hand_r"
    side = "left" if str(mp).endswith("_l") else "right"
    steps: list[dict[str, Any]] = []
    if hand and hasattr(hand, "hand_dispatch"):
        for i in range(n):
            prim = primitives[i % len(primitives)]
            step = hand.hand_dispatch({"action": "primitive", "primitive": prim, "side": side})
            steps.append({"primitive": prim, "ok": step.get("ok", True)})
    reg = load_registry()
    entry = reg.setdefault("learned", {}).setdefault(att_id, {"proficiency": 0.0, "trained_ticks": 0})
    equiv = float(row.get("hand_equivalence") or 0.85)
    hand_st = hand.hand_status() if hand and hasattr(hand, "hand_status") else {}
    hand_prof = float(hand_st.get("proficiency") or 0.35)
    gain = 0.014 * equiv
    new_prof = min(1.0, float(entry.get("proficiency") or 0) + gain * n)
    entry["proficiency"] = round(new_prof, 4)
    entry["trained_ticks"] = int(entry.get("trained_ticks") or 0) + n
    entry["hand_proficiency_ref"] = hand_prof
    entry["fluent"] = new_prof >= 0.72
    entry["mastered"] = new_prof >= 0.95
    entry["hand_equivalent"] = new_prof >= hand_prof * 0.9
    save_registry(reg)
    _append_ledger({"event": "learn", "id": att_id, "ticks": n, "proficiency": entry["proficiency"]})
    return {
        "ok": True,
        "id": att_id,
        "label": row.get("label"),
        "ticks": n,
        "proficiency": entry["proficiency"],
        "fluent": entry["fluent"],
        "mastered": entry["mastered"],
        "hand_equivalent": entry["hand_equivalent"],
        "mount_point": mp,
        "steps_sample": steps[-6:],
        "attachment": row,
    }


def wield_attachment(att_id: str, *, primitive: str | None = None) -> dict[str, Any]:
    """Use mounted attachment with learned grip mapping."""
    row = _attachment_row(att_id)
    if not row:
        return {"ok": False, "error": "unknown_attachment"}
    reg = load_registry()
    mp = (reg.get("mounted") or {}).get(att_id)
    if not mp:
        mount_attachment(att_id)
        mp = (load_registry().get("mounted") or {}).get(att_id)
    learned = (reg.get("learned") or {}).get(att_id) or {}
    prof = float(learned.get("proficiency") or 0)
    if prof < 0.15:
        return {"ok": False, "error": "insufficient_proficiency", "proficiency": prof, "hint": "inspect and learn first"}
    hand = _hand_core()
    prim = primitive or (row.get("learn_primitives") or ["point"])[0]
    side = "left" if str(mp).endswith("_l") else "right"
    motor = hand.hand_dispatch({"action": "primitive", "primitive": prim, "side": side}) if hand else {}
    return {
        "ok": True,
        "id": att_id,
        "mount_point": mp,
        "primitive": prim,
        "proficiency": prof,
        "motor": motor,
        "wireframe": hand.hand_wireframe() if hand and hasattr(hand, "hand_wireframe") else {},
    }


def attachment_status() -> dict[str, Any]:
    hand = _hand_core()
    return {
        "schema": "hostess7-attachment-status/v1",
        "updated": _ts(),
        "commander": "Hostess7",
        "sovereign": True,
        "mount_points": _load(DOCTRINE, {}).get("mount_points") or [],
        "attachments": list_attachments(),
        "mounted_count": len((load_registry().get("mounted") or {})),
        "hands": hand.hand_status() if hand and hasattr(hand, "hand_status") else {},
        "hand_wireframe": hand.hand_wireframe() if hand and hasattr(hand, "hand_wireframe") else {},
    }


def attachment_dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or body.get("subaction") or "status").strip().lower().replace("-", "_")

    if action in ("status", "json", "panel", "list"):
        return {"ok": True, **attachment_status()}

    if action in ("mount", "attach"):
        return mount_attachment(str(body.get("id") or body.get("attachment_id") or ""), mount_point=body.get("mount") or body.get("mount_point"))

    if action in ("unmount", "detach"):
        return unmount_attachment(str(body.get("id") or body.get("attachment_id") or ""))

    if action in ("inspect", "look", "see"):
        return inspect_attachment(
            att_id=body.get("id") or body.get("attachment_id"),
            path=body.get("path") or body.get("image"),
            look=body.get("look", True) is not False,
        )

    if action in ("learn", "train", "train_attachment"):
        return learn_attachment(str(body.get("id") or body.get("attachment_id") or ""), ticks=body.get("ticks"))

    if action in ("wield", "use"):
        return wield_attachment(str(body.get("id") or body.get("attachment_id") or ""), primitive=body.get("primitive"))

    if action in ("register", "add"):
        return register_attachment(body)

    return {"ok": False, "error": "unknown_attachment_action", "action": action}


def main() -> int:
    import sys
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}, ensure_ascii=False))
            return 1
        print(json.dumps(attachment_dispatch(body), ensure_ascii=False))
        return 0
    if cmd in ("json", "status", "panel", "list"):
        print(json.dumps({"ok": True, **attachment_status()}, ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: hostess7-attachment-core.py [json|dispatch]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())