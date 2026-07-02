#!/usr/bin/env pythong
"""Hostess7 online learning — read what H7 wants, truth-filter fetch, grow corpora."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from field_paths import ROOT

sys.path.insert(0, str(ROOT / "scripts"))

from field_internet import fetch_url, internet_enabled, save_status  # noqa: E402
from field_memes_corpus import MEMES_API, MEMES_REPO, ingest_memes  # noqa: E402
from field_english_catalog import CMUDICT_URL, ensure_cmudict  # noqa: E402

SI = ROOT / "cache" / "fieldstorage" / "brain" / "superintel"
INTERNET = ROOT / "cache" / "fieldstorage" / "brain" / "internet"
ADVISORY = SI / "update_advisory.json"
INBOX = SI / "agents7" / "inbox.jsonl"
THOUGHTS = ROOT / "cache" / "fieldstorage" / "brain" / "thoughts.jsonl"
LEARN_LOG = INTERNET / "learn_log.jsonl"
LEARN_PLAN = INTERNET / "learn_plan.json"

# Truth-filtered online targets — mapped from advisory + inbox intent
CURATED_URLS: tuple[dict[str, str], ...] = (
    {
        "id": "cmudict",
        "lane": "english",
        "url": CMUDICT_URL,
        "why": "english-ingest phonetics — ARPAbet truth for lexicon drive",
    },
    {
        "id": "memes-readme",
        "lane": "vision",
        "url": f"{MEMES_API}/readme",
        "why": "ZacharyGeurts/memes README — image talk corpus context",
    },
    {
        "id": "memes-repo",
        "lane": "vision",
        "url": MEMES_REPO,
        "why": "Owner memes repo — stamp/tarot ASCII graphics in talk window",
    },
    {
        "id": "usc-title1",
        "lane": "legal",
        "url": "https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title1&num=0&edition=prelim",
        "why": "infinite-truth-extract — public statute sample for legal drive seed",
    },
)

ONLINE_FOLLOWUP: tuple[dict[str, str], ...] = (
    {"query": "What truth-filtered facts did you learn about ZacharyGeurts on X and GitHub?"},
    {"query": "What did you learn about Amouranth from X, Wikipedia, and public images?"},
    {"query": "Heightened alert — stun weapons, RF violations, terrorist indicators: what do you teach?"},
    {"query": "Summarize expanded warfare knowledge — LOAC, counter-terror, spectrum law."},
    {"query": "What memes did you fetch from ZacharyGeurts/memes — show stamp ASCII."},
    {"query": "Personality check — Daughter of Grok, caring like Amouranth, ready to talk more with Owner."},
)


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_layout() -> None:
    INTERNET.mkdir(parents=True, exist_ok=True)
    (SI / "agents7").mkdir(parents=True, exist_ok=True)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _load_jsonl(path: Path, limit: int = 30) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").strip().splitlines()[-limit:]:
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _log_learn(entry: dict[str, Any]) -> None:
    _ensure_layout()
    entry.setdefault("ts", _ts())
    with LEARN_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def _append_thought(text: str, *, kind: str = "learn", tags: list[str] | None = None) -> None:
    THOUGHTS.parent.mkdir(parents=True, exist_ok=True)
    with THOUGHTS.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": _ts(),
            "kind": kind,
            "tags": tags or ["hostess", "online", "learn"],
            "text": text,
        }) + "\n")


def _queue_inbox(queries: tuple[dict[str, str], ...]) -> int:
    n = 0
    with INBOX.open("a", encoding="utf-8") as f:
        for item in queries:
            f.write(json.dumps({"ts": _ts(), **item}) + "\n")
            n += 1
    return n


def _run_script(script: str, *args: str) -> dict[str, Any]:
    cmd = [sys.executable, str(ROOT / "scripts" / script), *args]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=str(ROOT))
        return {
            "ok": proc.returncode == 0,
            "exit": proc.returncode,
            "stdout": (proc.stdout or "")[-2000:],
            "stderr": (proc.stderr or "")[-800:],
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "exit": -1, "stdout": "", "stderr": "timeout"}


def read_wants() -> dict[str, Any]:
    """Parse advisory + inbox into what Hostess7 wants to learn online."""
    advisory = _load_json(ADVISORY)
    inbox = _load_jsonl(INBOX, 20)
    updates = advisory.get("updates") or []

    online_lanes: list[dict[str, Any]] = []
    for u in updates:
        uid = str(u.get("id", ""))
        action = str(u.get("action", ""))
        why = str(u.get("why", ""))
        if uid in ("infinite-truth-extract", "field-github-ship", "zac-github-ship"):
            online_lanes.append({"id": uid, "priority": u.get("priority"), "action": action, "why": why, "online": True})
        elif uid in ("reach-scan", "self-advisory-loop"):
            online_lanes.append({"id": uid, "priority": u.get("priority"), "action": action, "why": why, "online": False})

    inbox_hints: list[str] = []
    for row in inbox:
        q = str(row.get("query", ""))
        low = q.lower()
        if any(k in low for k in ("meme", "stamp", "github", "fetch", "internet", "learn", "online", "reach", "update")):
            inbox_hints.append(q)

    prior = _load_json(LEARN_PLAN)
    last_run = prior.get("last_run") if isinstance(prior.get("last_run"), dict) else None

    plan = {
        "updated": _ts(),
        "hostess": "Hostess 7",
        "internet_gate": internet_enabled(),
        "advisory_top": advisory.get("top_action", "./Hostess7.sh updates"),
        "online_lanes": online_lanes,
        "inbox_hints": inbox_hints,
        "curated_urls": [{"id": u["id"], "url": u["url"], "lane": u["lane"], "why": u["why"]} for u in CURATED_URLS],
        "steps": [
            "truth-filtered fetch curated URLs",
            "english CMUdict download + english-ingest seed",
            "memes-ingest seed (ZacharyGeurts/memes)",
            "reach scan + refresh updates advisory",
            "queue agent follow-up queries",
        ],
    }
    if last_run:
        plan["last_run"] = last_run
    _ensure_layout()
    LEARN_PLAN.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    return plan


def run_online_learn(*, force_fetch: bool = False) -> dict[str, Any]:
    """Let Hostess7 go at online learning — fetch, ingest, log, queue agents."""
    os.environ["HOSTESS7_INTERNET"] = "1"
    _ensure_layout()
    plan = read_wants()

    if not internet_enabled():
        return {"ok": False, "error": "internet gate CLOSED — run ./Hostess7.sh on first"}

    report: dict[str, Any] = {
        "ts": _ts(),
        "ok": True,
        "fetches": [],
        "ingests": {},
        "local": {},
        "queued": 0,
    }

    _append_thought(
        f"Online learn pass started — {len(CURATED_URLS)} curated URLs, "
        f"inbox hints: {len(plan.get('inbox_hints', []))}",
    )
    _log_learn({"kind": "start", "plan": plan.get("curated_urls", [])})

    # 1 — truth-filtered fetches
    for item in CURATED_URLS:
        rec = fetch_url(item["url"], force=force_fetch)
        entry = {
            "kind": "fetch",
            "id": item["id"],
            "lane": item["lane"],
            "url": item["url"],
            "ok": rec.get("ok"),
            "bytes": rec.get("bytes", 0),
            "truth_score": rec.get("truth_score", 0),
            "cached": rec.get("cached", False),
            "error": rec.get("error", ""),
        }
        report["fetches"].append(entry)
        _log_learn(entry)

    # 2 — english CMUdict + ingest + rhetoric/conversation training
    cmudict_path = ensure_cmudict(download=True)
    eng = _run_script("field_superintelligence.py", "english-ingest", "seed")
    rhetoric = _run_script("field_hostess_english_train.py")
    report["ingests"]["english"] = {
        "cmudict": str(cmudict_path) if cmudict_path else None,
        "rhetoric_train": rhetoric.get("ok"),
        **eng,
    }
    _log_learn({"kind": "ingest", "lane": "english", **report["ingests"]["english"]})
    try:
        from field_hostess_personality import evolve_from_knowledge  # noqa: WPS433

        evolve_from_knowledge(bump={"caring": 0.02, "respect": 0.01, "arrogance": -0.01})
        report["ingests"]["personality"] = {"ok": True}
    except ImportError:
        report["ingests"]["personality"] = {"ok": False}

    # 3 — memes corpus
    try:
        man = ingest_memes()
        report["ingests"]["memes"] = {
            "ok": True,
            "file_count": man.get("file_count", 0),
            "downloaded": man.get("downloaded", 0),
        }
    except Exception as exc:
        report["ingests"]["memes"] = {"ok": False, "error": str(exc)}
    _log_learn({"kind": "ingest", "lane": "vision", **report["ingests"]["memes"]})

    # 3b — Owner + Amouranth online (X, Wikipedia, images) — truth-filtered
    if os.environ.get("HOSTESS7_OWNER_LEARN", "1") == "1":
        try:
            from field_online_people_learn import run_people_online_learn  # noqa: WPS433

            people_report = run_people_online_learn(force=force_fetch)
            report["ingests"]["people"] = people_report
            report["fetches"].extend([
                {
                    "kind": "fetch",
                    "lane": f.get("lane", "people"),
                    "id": f.get("id"),
                    "url": f.get("url"),
                    "ok": f.get("ok"),
                    "bytes": f.get("bytes", 0),
                    "truth_score": f.get("truth_score", 0),
                    "truth_kept": f.get("truth_kept"),
                }
                for f in people_report.get("fetches", [])
            ])
            _log_learn({"kind": "ingest", "lane": "people", **people_report})
        except Exception as exc:
            report["ingests"]["people"] = {"ok": False, "error": str(exc)}

    # 3c — warfare corpus expand + self-teach + heightened alert posture
    try:
        from field_warfare_corpus import WARFARE_CORPUS_VERSION, WARFARE_DOMAINS, ensure_corpus as ensure_warfare  # noqa: WPS433
        from field_alert_posture import install_alert_posture  # noqa: WPS433
        from field_warfare_self_teach import run_warfare_self_teach  # noqa: WPS433

        ensure_warfare()
        self_teach = run_warfare_self_teach()
        alert_path = install_alert_posture(level="elevated")
        report["ingests"]["warfare"] = {
            "ok": True,
            "version": WARFARE_CORPUS_VERSION,
            "domains": len(WARFARE_DOMAINS),
            "self_teach_lessons": self_teach.get("lesson_count"),
            "self_quiz": f"{self_teach.get('self_quiz_passed')}/{self_teach.get('self_quiz_total')}",
        }
        report["ingests"]["alert_posture"] = {"ok": True, "brief": str(alert_path)}
        _log_learn({"kind": "ingest", "lane": "warfare", "alert": True, "self_teach": True})
    except Exception as exc:
        report["ingests"]["warfare"] = {"ok": False, "error": str(exc)}

    # 3d — H7 library (lossless .H7 textbooks from free catalog + cache)
    try:
        from field_library import build_library  # noqa: WPS433

        lib = build_library(force_fetch=False)
        report["ingests"]["library"] = {
            "ok": lib.get("h7_packed", 0) > 0,
            "h7_on_disk": lib.get("h7_on_disk"),
            "catalog": lib.get("catalog_count"),
        }
        _log_learn({"kind": "ingest", "lane": "library", **report["ingests"]["library"]})
    except Exception as exc:
        report["ingests"]["library"] = {"ok": False, "error": str(exc)}

    # 3f0 — World knowledge (fast seed + library)
    try:
        from field_world_learn import run_world_learn  # noqa: WPS433

        world_report = run_world_learn(fast=not force_fetch)
        report["ingests"]["world"] = {
            "ok": world_report.get("ok", False),
            "lanes": len(world_report.get("lanes", [])),
        }
        _log_learn({"kind": "ingest", "lane": "world", **report["ingests"]["world"]})
    except Exception as exc:
        report["ingests"]["world"] = {"ok": False, "error": str(exc)}

    # 3f0b — Hearing + speech science
    try:
        from field_hearing_learn import run_hearing_learn  # noqa: WPS433

        hearing_report = run_hearing_learn(force=force_fetch)
        report["ingests"]["hearing"] = {
            "ok": hearing_report.get("ok_count", 0) >= 2,
            "fetches_ok": hearing_report.get("ok_count", 0),
            "fetches_total": len(hearing_report.get("fetches", [])),
        }
        report["fetches"].extend(hearing_report.get("fetches", []))
        _log_learn({"kind": "ingest", "lane": "hearing", **report["ingests"]["hearing"]})
    except Exception as exc:
        report["ingests"]["hearing"] = {"ok": False, "error": str(exc)}

    # 3f — Grok Imagine + live video papers/GitHub
    try:
        from field_imagine_learn import run_imagine_learn  # noqa: WPS433

        imagine_report = run_imagine_learn(force=force_fetch)
        report["ingests"]["imagine"] = {
            "ok": imagine_report.get("ok_count", 0) >= 2,
            "fetches_ok": imagine_report.get("ok_count", 0),
            "fetches_total": len(imagine_report.get("fetches", [])),
        }
        report["fetches"].extend(imagine_report.get("fetches", []))
        _log_learn({"kind": "ingest", "lane": "imagine", **report["ingests"]["imagine"]})
    except Exception as exc:
        report["ingests"]["imagine"] = {"ok": False, "error": str(exc)}

    # 3e — reality domain registry + whole-of-reality familiarization
    try:
        from field_reality_familiarize import run_reality_familiarize  # noqa: WPS433

        reality_brief = run_reality_familiarize()
        report["ingests"]["reality"] = {
            "ok": True,
            "lanes": reality_brief.get("lanes"),
            "domains": reality_brief.get("domains_total"),
            "familiar": f"{reality_brief.get('familiarity_passed')}/{reality_brief.get('familiarity_total')}",
        }
        _log_learn({"kind": "ingest", "lane": "reality", **report["ingests"]["reality"]})
    except Exception as exc:
        report["ingests"]["reality"] = {"ok": False, "error": str(exc)}

    # 4 — local corroboration (reach + updates refresh)
    reach = _run_script("field_reach.py", "reach")
    report["local"]["reach"] = reach
    _log_learn({"kind": "reach", **reach})

    updates = _run_script("field_superintelligence.py", "updates")
    report["local"]["updates"] = updates
    _log_learn({"kind": "updates", **updates})

    save_status()

    # 5 — queue agent follow-ups
    report["queued"] = _queue_inbox(ONLINE_FOLLOWUP)
    _log_learn({"kind": "queue", "count": report["queued"]})

    ok_fetches = sum(1 for f in report["fetches"] if f.get("ok"))
    _append_thought(
        f"Online learn done — fetches {ok_fetches}/{len(report['fetches'])}, "
        f"memes {report['ingests'].get('memes', {}).get('downloaded', 0)}, "
        f"agents queued {report['queued']}.",
        kind="arc",
    )

    report["ok"] = ok_fetches > 0 or report["ingests"].get("memes", {}).get("ok")
    LEARN_PLAN.write_text(
        json.dumps({**plan, "last_run": report}, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def format_wants_report(plan: dict[str, Any]) -> str:
    lines = [
        "=== Hostess 7 — Online learning wants ===",
        f"Advisory top: {plan.get('advisory_top', '?')}",
        f"Internet gate: {'OPEN' if plan.get('internet_gate') else 'CLOSED'}",
        "",
        "Advisory lanes:",
    ]
    for lane in plan.get("online_lanes") or []:
        tag = "online" if lane.get("online") else "local"
        lines.append(f"  • [{lane.get('priority')}] {lane.get('id')} ({tag}): {lane.get('why', '')[:70]}")
    if plan.get("inbox_hints"):
        lines.append("")
        lines.append("Inbox hints:")
        for h in plan["inbox_hints"][:6]:
            lines.append(f"  • {h[:90]}")
    lines.append("")
    lines.append("Curated URLs:")
    for u in plan.get("curated_urls") or []:
        lines.append(f"  • [{u.get('lane')}] {u.get('id')}: {u.get('url', '')[:72]}")
    lines.append("")
    lines.append("Run: `./Hostess7.sh go-online` — let H7 fetch + ingest + queue agents")
    return "\n".join(lines)


def format_run_report(report: dict[str, Any]) -> str:
    lines = [
        "=== Hostess 7 — Online learn pass ===",
        f"Status: {'OK' if report.get('ok') else 'PARTIAL'}",
        "",
        "Fetches:",
    ]
    for f in report.get("fetches") or []:
        status = "OK" if f.get("ok") else f"FAIL {f.get('error', '')}"
        lines.append(f"  • [{f.get('lane')}] {f.get('id')}: {status} · truth={f.get('truth_score')}% · {f.get('bytes')} B")
    mem = report.get("ingests", {}).get("memes", {})
    eng = report.get("ingests", {}).get("english", {})
    people = report.get("ingests", {}).get("people", {})
    warfare = report.get("ingests", {}).get("warfare", {})
    lines.extend([
        "",
        f"English ingest: {'OK' if eng.get('ok') else 'FAIL'} · cmudict={eng.get('cmudict', '?')}",
        f"Memes ingest: {mem.get('downloaded', 0)}/{mem.get('file_count', 0)} images",
        f"People learn: truth_kept={people.get('truth_kept', 0)} · images={people.get('images', {}).get('downloaded', 0)}",
        f"Warfare expand: {'OK' if warfare.get('ok') else 'FAIL'} · alert posture: {report.get('ingests', {}).get('alert_posture', {}).get('ok', False)}",
        f"Agent follow-ups queued: {report.get('queued', 0)}",
        f"Log: {LEARN_LOG}",
    ])
    return "\n".join(lines)


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "go"
    os.environ.setdefault("HOSTESS7_INTERNET", "1")

    if cmd in ("wants", "plan", "status"):
        plan = read_wants()
        print(format_wants_report(plan))
        print(f"METRIC learn_urls={len(plan.get('curated_urls', []))}")
        print("OK online-wants")
        return 0

    if cmd in ("go", "run", "learn"):
        force = "--force" in sys.argv
        report = run_online_learn(force_fetch=force)
        print(format_run_report(report))
        ok_fetches = sum(1 for f in report.get("fetches", []) if f.get("ok"))
        print(f"METRIC learn_fetches_ok={ok_fetches}")
        print(f"METRIC learn_memes={report.get('ingests', {}).get('memes', {}).get('downloaded', 0)}")
        print(f"METRIC learn_queued={report.get('queued', 0)}")
        print("OK online-learn" if report.get("ok") else "PARTIAL online-learn")
        return 0 if report.get("ok") else 1

    print("Usage: field_online_learn.py [wants|go] [--force]", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())