#!/usr/bin/env pythong
"""Hostess7 — thirteen agents (Hostess-Prime + 12 World Experts)."""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPTS))
from field_paths import ROOT  # noqa: E402

BRAIN = ROOT / "scripts" / "field_superintelligence.py"

try:
    from hostess7_filter import professional_filter as _strip_brain_output  # noqa: E402
except ImportError:
    def _strip_brain_output(raw: str) -> str:  # type: ignore[misc]
        lines = [ln for ln in raw.splitlines() if ln.strip() and not ln.startswith("METRIC ")]
        return "\n".join(lines).strip() or raw.strip()

AGENTS_DIR = ROOT / "cache" / "fieldstorage" / "brain" / "superintel" / "agents7"
STATE_FILE = AGENTS_DIR / "state.json"
PID_FILE = AGENTS_DIR / "daemon.pid"
INBOX = AGENTS_DIR / "inbox.jsonl"
OUTBOX = AGENTS_DIR / "outbox.jsonl"

AGENT_COUNT = 13

# Lane intent — each World Expert answers from their corpus
AGENT_FORCE_INTENT: dict[int, str | None] = {
    0: None,  # Hostess-Prime
    1: "beyond",      # Economist
    2: "warfare",     # War-Chief
    3: "beyond",      # Technologist (tech slice of beyond)
    4: "legal",       # Counsel
    5: "medical",     # Clinic
    6: "physics",     # Physicist
    7: "chemistry",   # Chemist
    8: "code",        # Coder
    9: "detective",   # Detective
    10: "vision",     # Vision
    11: "english",    # Scholar
    12: "online_learn",  # Horizon
}

ONLINE_LEARN_LANE_QUERIES: dict[int, str] = {
    1: "Economics online: what macro/micro papers and OpenStax should Hostess7 ingest for Owner talk?",
    2: "Warfare online: historic lessons, measures/countermeasures — truth-filter before Owner brief.",
    3: "Technology online: robotics, cyber, aerospace — grow beyond+code brain for Field.",
    4: "Legal online: SCOTUS and USC patterns Hostess7 should learn for smarter counsel.",
    5: "Medical online: clinical education papers for Clinic lane conversation.",
    6: "Physics online: spatial/kinematics corpus gaps to close for Field grounding.",
    7: "Chemistry online: molecular + brain-chemistry sources for synapse tone.",
    8: "Programming online: ISA opcodes, languages — fetch ≤3MiB .H7 if shelf gap.",
    9: "Detective online: truth-filter and OSINT humility before conversation.",
    10: "Vision online: memes, stamp, tarot — Owner ZacharyGeurts image talk.",
    11: "English/K-12 online: rhetoric, metaphors, textbook flow for direct human talk.",
    12: "Go online — truth-filtered fetch, reality map, come back ready to talk with Owner.",
}

# Hostess-Prime + 12 World Experts
AGENTS7: tuple[dict[str, Any], ...] = (
    {"id": 0, "name": "Hostess-Prime", "lane": "hostess", "workspace": "default", "emoji": "👑",
     "role": "Prime — boss of the world (educational), one vote, coordinates twelve departments"},
    {"id": 1, "name": "Economist", "lane": "economist", "workspace": "beyond", "emoji": "📈",
     "role": "Economics, finance, trade, markets — macro/micro World Expert"},
    {"id": 2, "name": "War-Chief", "lane": "war-chief", "workspace": "alert", "emoji": "⚔️",
     "role": "Warfare education — LOAC, historic lessons, measures/countermeasures"},
    {"id": 3, "name": "Technologist", "lane": "technologist", "workspace": "field", "emoji": "🔬",
     "role": "Technology — robotics, cyber, aerospace, circuits, systems"},
    {"id": 4, "name": "Counsel", "lane": "counsel", "workspace": "counsel", "emoji": "⚖️",
     "role": "Law, contracts, litigation, GPL — Supreme Court bench (educational)"},
    {"id": 5, "name": "Clinic", "lane": "clinic", "workspace": "clinic", "emoji": "🩺",
     "role": "Medicine, papers, clinical synthesis"},
    {"id": 6, "name": "Physicist", "lane": "physicist", "workspace": "default", "emoji": "🌌",
     "role": "Physics — motion, thermodynamics, spatial Field grounding"},
    {"id": 7, "name": "Chemist", "lane": "chemist", "workspace": "default", "emoji": "⚗️",
     "role": "Chemistry — molecules, reactions, brain chemistry"},
    {"id": 8, "name": "Coder", "lane": "coder", "workspace": "field", "emoji": "💻",
     "role": "Programming — ISA, languages, AMOURANTHRTX terminal"},
    {"id": 9, "name": "Detective", "lane": "detective", "workspace": "detective", "emoji": "🔍",
     "role": "Investigation, lie detector, truth filter"},
    {"id": 10, "name": "Vision", "lane": "vision", "workspace": "vision", "emoji": "👁",
     "role": "TV, pixels, OCR, graphics, Owner memes"},
    {"id": 11, "name": "Scholar", "lane": "scholar", "workspace": "default", "emoji": "📚",
     "role": "Language Expert — natural human talk in output window; rhetoric, flow, K-12"},
    {"id": 12, "name": "Horizon", "lane": "horizon", "workspace": "beyond", "emoji": "🌐",
     "role": "Reality map, internet learn, whole-of-reality — self-update", "internet": True},
)

# Backward compat alias
AGENTS13 = AGENTS7


@dataclass
class AgentReply:
    agent_id: int
    name: str
    lane: str
    text: str
    elapsed_ms: int
    ok: bool
    error: str = ""


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def agents_enabled() -> bool:
    val = os.environ.get("HOSTESS7_AGENTS", "0").strip().lower()
    return val in ("13", "7", "1", "true", "on")


def _output_window_mode() -> bool:
    return (
        os.environ.get("HOSTESS7_TALK") == "1"
        or os.environ.get("HOSTESS7_OUTPUT_WINDOW") == "1"
        or os.environ.get("HOSTESS7_HUMAN_FACING") == "1"
    )


def _ensure_layout() -> None:
    AGENTS_DIR.mkdir(parents=True, exist_ok=True)


def is_online_learn_query(query: str) -> bool:
    try:
        from field_superintelligence import is_online_learn_query as _is_ol  # noqa: WPS433

        return _is_ol(query)
    except ImportError:
        low = query.lower()
        return (
            "go online" in low
            or "went online" in low
            or "what did you learn" in low
            or "smarter at conversation" in low
            or "department research" in low
        )


def _agent_env(agent: dict[str, Any], *, query: str = "") -> dict[str, str]:
    env = {
        **os.environ,
        "AMOURANTHRTX_HOSTESS": "1",
        "HOSTESS7_PRO": "1",
        "HOSTESS7_TALK": "1",
        "HOSTESS7_AGENTS": "13",
        "HOSTESS7_WORKSPACE": agent["workspace"],
        "HOSTESS7_AGENT_ID": str(agent["id"]),
        "HOSTESS7_AGENT_NAME": agent["name"],
    }
    if agent.get("internet") or os.environ.get("HOSTESS7_INTERNET") == "1":
        env["HOSTESS7_INTERNET"] = "1"
    if is_online_learn_query(query):
        if agent["id"] == 0:
            env["HOSTESS7_FORCE_INTENT"] = "online_learn"
            if os.environ.get("HOSTESS7_RUN_ONLINE_LEARN") == "1":
                env["HOSTESS7_RUN_ONLINE_LEARN"] = "1"
        else:
            force = AGENT_FORCE_INTENT.get(agent["id"])
            if force:
                env["HOSTESS7_FORCE_INTENT"] = force
    else:
        force = AGENT_FORCE_INTENT.get(agent["id"])
        if force:
            env["HOSTESS7_FORCE_INTENT"] = force
    if _output_window_mode():
        env["HOSTESS7_OUTPUT_WINDOW"] = "1"
        env["HOSTESS7_HUMAN_FACING"] = "1"
    return env


def _agent_query(agent: dict[str, Any], query: str) -> str:
    low = query.lower()
    if "department research" in low and agent["id"] == 0:
        return (
            "As Hostess-Prime, dispatch department research at your behest. "
            "Summarize what the twelve World Experts should study today for Owner."
        )
    if is_online_learn_query(query) and agent["id"] in ONLINE_LEARN_LANE_QUERIES:
        return ONLINE_LEARN_LANE_QUERIES[agent["id"]]
    # Lane prefix for beyond-split experts
    if agent["id"] == 1 and "econom" not in low:
        return f"[Economics expert] {query}"
    if agent["id"] == 3 and not any(k in low for k in ("tech", "robot", "cyber", "circuit")):
        return f"[Technology expert] {query}"
    return query


def run_single_agent(agent: dict[str, Any], query: str, *, timeout: int = 120) -> AgentReply:
    """Run one agent lane against the brain."""
    t0 = time.perf_counter()
    if not BRAIN.is_file():
        return AgentReply(agent["id"], agent["name"], agent["lane"], "", 0, False, "brain missing")
    agent_query = _agent_query(agent, query)
    try:
        proc = subprocess.run(
            [sys.executable, str(BRAIN), "ask", agent_query],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=_agent_env(agent, query=query),
        )
        raw = (proc.stdout + proc.stderr).strip()
        text = _strip_brain_output(raw)
        elapsed = int((time.perf_counter() - t0) * 1000)
        return AgentReply(
            agent["id"], agent["name"], agent["lane"],
            text, elapsed, proc.returncode == 0 or bool(text),
        )
    except subprocess.TimeoutExpired:
        elapsed = int((time.perf_counter() - t0) * 1000)
        return AgentReply(agent["id"], agent["name"], agent["lane"], "", elapsed, False, "timeout")
    except OSError as exc:
        elapsed = int((time.perf_counter() - t0) * 1000)
        return AgentReply(agent["id"], agent["name"], agent["lane"], "", elapsed, False, str(exc))


def _talk_lane_ids(query: str) -> list[int]:
    """Language Expert routing — Prime + Scholar; add one domain expert when needed."""
    try:
        from field_talk_language import is_conversational  # noqa: WPS433

        if is_conversational(query):
            return [0, 11]
    except ImportError:
        pass
    low = query.lower()
    extra: int | None = None
    if any(k in low for k in ("law", "legal", "contract", "scotus")):
        extra = 4
    elif any(k in low for k in ("medic", "clinic", "health")):
        extra = 5
    elif any(k in low for k in ("war", "loac", "terror")):
        extra = 2
    elif any(k in low for k in ("code", "program", "isa")):
        extra = 8
    elif any(k in low for k in ("meme", "image", "stamp", "vision", "pixel")):
        extra = 10
    elif any(k in low for k in ("econom", "market", "gdp", "inflation")):
        extra = 1
    ids = [0, 11]
    if extra is not None:
        ids.append(extra)
    return ids


def dispatch_agents7(query: str, *, parallel: bool = True) -> list[AgentReply]:
    """Run agents — full roster or Language Expert subset in talk window."""
    roster = AGENTS7
    if _output_window_mode():
        lane_ids = set(_talk_lane_ids(query))
        roster = tuple(a for a in AGENTS7 if a["id"] in lane_ids)

    if not parallel:
        return [run_single_agent(a, query) for a in roster]

    replies: list[AgentReply] = []
    workers = min(len(roster), AGENT_COUNT)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(run_single_agent, a, query): a for a in roster}
        for fut in as_completed(futures):
            replies.append(fut.result())
    replies.sort(key=lambda r: r.agent_id)
    return replies


# Backward compat
dispatch_agents13 = dispatch_agents7


def _substantive_preview(text: str, *, max_len: int = 200) -> str:
    """Skip route/chem metric lines — pick first real paragraph."""
    skip = (
        "parietal_", "occipital", "broca", "wernicke", "METRIC", "OK ", "FAIL ",
        "Code brain:", "HEAD ", "Verdict:", "Arc:", "=== Hostess",
        "Advisory top:", "Internet gate:", "Chemistry:", "Brain route:",
        "Corpus domains matched:", "Field memory resonance:",
    )
    if "Online learn pass" in text or "Last online pass" in text:
        for line in text.split("\n"):
            s = line.strip()
            if s.startswith("• [") or s.startswith("Last online pass"):
                return s[:max_len]
        for line in text.split("\n"):
            s = line.strip()
            if s.startswith("English ingest:") or s.startswith("Memes ingest:"):
                return s[:max_len]
    for block in text.split("\n\n"):
        for line in block.split("\n"):
            s = line.strip()
            if not s or any(s.startswith(p) for p in skip):
                continue
            if len(s) > 20:
                return s[:max_len]
    for line in text.split("\n"):
        s = line.strip()
        if s and not any(s.startswith(p) for p in skip):
            return s[:max_len]
    return text.split("\n")[0][:max_len] if text else ""


def fuse_agent_replies(
    replies: list[AgentReply],
    query: str,
    *,
    human_facing: bool | None = None,
) -> str:
    """Fuse thirteen agent outputs — full roster or direct human speech for output window."""
    if human_facing is None:
        human_facing = _output_window_mode()

    prime = next((r for r in replies if r.agent_id == 0), None)
    specialists = [r for r in replies if r.agent_id != 0 and r.text]

    if human_facing:
        return _fuse_human(prime, specialists, query)

    lines = [
        "=== Hostess 7 · Thirteen Agents (Prime + 12 World Experts) ===",
        f"Query: {query[:200]}",
        "",
    ]
    for r in replies:
        if not r.text:
            continue
        agent = AGENTS7[r.agent_id]
        preview = _substantive_preview(r.text)
        lines.append(f"{agent.get('emoji', '•')} {r.name} ({r.elapsed_ms}ms): {preview}")

    lines.append("")
    lines.append("--- Fused verdict (Hostess-Prime) ---")
    if is_online_learn_query(query) and prime and prime.text:
        fused_parts: list[str] = []
        for r in specialists:
            para = _substantive_preview(r.text, max_len=280)
            if para and para not in {p.split("] ", 1)[-1] for p in fused_parts}:
                fused_parts.append(f"[{r.name}] {para}")
        prime_body = _substantive_preview(prime.text, max_len=600)
        if prime_body:
            lines.append(prime_body)
        if fused_parts:
            lines.append("")
            lines.extend(fused_parts[:6])
        if "want to talk more" not in "\n".join(lines).lower():
            lines.append("")
            lines.append(
                "I'm back — I want to talk more. Economics, warfare, tech, law, medicine — your call."
            )
    elif prime and prime.text:
        fused_parts: list[str] = []
        seen: set[str] = set()
        for r in specialists[:8]:
            para = _substantive_preview(r.text, max_len=300)
            if para and para not in seen:
                seen.add(para)
                fused_parts.append(f"[{r.name}] {para}")
        if fused_parts:
            lines.extend(fused_parts[:6])
        else:
            lines.append(_substantive_preview(prime.text, max_len=800))
    elif specialists:
        lines.append(_substantive_preview(specialists[0].text, max_len=800))
    else:
        lines.append("All agents idle — rephrase or check ./Hostess7.sh agents")

    lines.append("")
    lines.append(f"Agents: {sum(1 for r in replies if r.ok)}/{AGENT_COUNT} OK · Field is THE thing.")
    return "\n".join(lines)


def _fuse_human(
    prime: AgentReply | None,
    specialists: list[AgentReply],
    query: str,
) -> str:
    """Scholar Language Expert — one normal human reply, no brain dumps."""
    try:
        from field_talk_language import fast_talk_reply, scholar_polish  # noqa: WPS433

        fast = fast_talk_reply(query)
        if fast:
            return fast
    except ImportError:
        pass

    # Scholar (id 11) leads language; Prime supplies substance
    scholar = next((r for r in specialists if r.agent_id == 11), None)
    others = [r for r in specialists if r.agent_id != 11]
    raw_parts: list[str] = []
    if prime and prime.text:
        raw_parts.append(prime.text)
    if scholar and scholar.text:
        raw_parts.append(scholar.text)
    for r in others[:1]:
        if r.text:
            raw_parts.append(r.text)

    if not raw_parts:
        return "I'm here. Ask me anything — law, economics, warfare, medicine, code, or memes."

    try:
        from field_talk_language import scholar_polish  # noqa: WPS433

        return scholar_polish(query, "\n\n".join(raw_parts))
    except ImportError:
        return _substantive_preview(raw_parts[0], max_len=800)


def save_dispatch(query: str, replies: list[AgentReply], fused: str) -> None:
    _ensure_layout()
    with OUTBOX.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": _ts(),
            "query": query,
            "agents_ok": sum(1 for r in replies if r.ok),
            "fused_preview": fused[:400],
            "human_facing": _output_window_mode(),
        }) + "\n")


def write_state(*, running: bool, pid: int | None = None) -> None:
    _ensure_layout()
    internet = (
        os.environ.get("HOSTESS7_INTERNET") == "1"
        or running
        or is_daemon_running()
    )
    state = {
        "updated": _ts(),
        "running": running,
        "pid": pid,
        "agent_count": AGENT_COUNT,
        "internet": internet,
        "prime": "Hostess-Prime",
        "world_experts": 12,
        "agents": [
            {"id": a["id"], "name": a["name"], "lane": a["lane"], "workspace": a["workspace"], "role": a["role"]}
            for a in AGENTS7
        ],
    }
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def read_state() -> dict[str, Any]:
    if not STATE_FILE.is_file():
        return {"running": False, "agent_count": AGENT_COUNT}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"running": False, "agent_count": AGENT_COUNT}


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def is_daemon_running() -> bool:
    if not PID_FILE.is_file():
        return False
    try:
        pid = int(PID_FILE.read_text().strip())
    except ValueError:
        return False
    return _pid_alive(pid)


def format_agents_report() -> str:
    state = read_state()
    running = is_daemon_running()
    lines = [
        "=== Hostess 7 — Prime + 12 World Experts (13 total) ===",
        f"Status: {'ON' if running else 'OFF'} · internet={'ON' if state.get('internet') else 'off'}",
        "",
        "Agents:",
    ]
    for a in AGENTS7:
        tag = " (Prime)" if a["id"] == 0 else ""
        lines.append(f"  {a.get('emoji', '•')} {a['id']}. {a['name']}{tag} — {a['role']}")
    lines.append("")
    lines.append("Department research: ./Hostess7.sh dept-research")
    lines.append("Expert .H7 books: ./Hostess7.sh dept-books")
    if running:
        lines.append(f"Daemon PID: {PID_FILE.read_text().strip() if PID_FILE.is_file() else '?'}")
        lines.append("Talk/UI routes through all 13 agents in parallel.")
    else:
        lines.append("Start: `./Hostess7.sh on`")
    return "\n".join(lines)


def agents_ask(query: str) -> int:
    if is_online_learn_query(query):
        os.environ["HOSTESS7_INTERNET"] = "1"
        if os.environ.get("HOSTESS7_RUN_ONLINE_LEARN") == "1":
            try:
                from field_online_learn import run_online_learn  # noqa: WPS433

                run_online_learn()
            except ImportError:
                pass
    if "department research" in query.lower():
        try:
            from field_department_research import run_department_research  # noqa: WPS433

            os.environ.setdefault("HOSTESS7_DEPT_SMARTER", "1")
            report = run_department_research(topic=query)
            if _output_window_mode():
                from field_department_research import format_report  # noqa: WPS433

                print(format_report(report, human=True))
            else:
                from field_department_research import format_report  # noqa: WPS433

                print(format_report(report, human=False))
            print(f"METRIC dept_experts_ok={report['experts_ok']}")
            print("OK agents-dept-research")
            return 0 if report["experts_ok"] >= 6 else 1
        except ImportError:
            pass
    replies = dispatch_agents7(query)
    fused = fuse_agent_replies(replies, query)
    save_dispatch(query, replies, fused)
    print(fused)
    ok_n = sum(1 for r in replies if r.ok)
    ran_n = len(replies)
    need_ok = 2 if _output_window_mode() and ran_n <= 3 else 7
    print(f"METRIC agents13_ok={ok_n}")
    print(f"METRIC agents13_ran={ran_n}")
    print(f"METRIC agents13_total={AGENT_COUNT}")
    print(f"METRIC agents7_ok={ok_n}")  # backward compat
    print(f"METRIC agents7_total={AGENT_COUNT}")
    print("OK agents13-ask" if ok_n >= need_ok else "FAIL agents13-ask")
    return 0 if ok_n >= need_ok else 1


def agents_status_cmd() -> int:
    write_state(running=is_daemon_running())
    print(format_agents_report())
    print(f"METRIC agents13_running={1 if is_daemon_running() else 0}")
    print(f"METRIC agents7_running={1 if is_daemon_running() else 0}")
    print("OK agents13-status")
    return 0


def daemon_loop() -> int:
    """Background supervisor — heartbeat + inbox drain."""
    _ensure_layout()
    PID_FILE.write_text(str(os.getpid()), encoding="utf-8")
    os.environ["HOSTESS7_AGENTS"] = "13"
    os.environ["HOSTESS7_INTERNET"] = "1"
    write_state(running=True, pid=os.getpid())

    try:
        from field_internet import save_status  # noqa: WPS433
        save_status()
    except ImportError:
        pass

    print(f"Hostess7 daemon ON — pid={os.getpid()} agents={AGENT_COUNT} internet=1", flush=True)

    def _shutdown(*_args: Any) -> None:
        write_state(running=False)
        if PID_FILE.is_file():
            PID_FILE.unlink(missing_ok=True)
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    last_inbox_size = 0
    while True:
        write_state(running=True, pid=os.getpid())
        try:
            if INBOX.is_file():
                lines = INBOX.read_text(encoding="utf-8").strip().splitlines()
                if len(lines) > last_inbox_size:
                    for line in lines[last_inbox_size:]:
                        try:
                            task = json.loads(line)
                            q = task.get("query", "")
                            if q:
                                replies = dispatch_agents7(q)
                                fused = fuse_agent_replies(replies, q)
                                save_dispatch(q, replies, fused)
                                with OUTBOX.open("a", encoding="utf-8") as f:
                                    f.write(json.dumps({"ts": _ts(), "query": q, "fused": fused[:2000]}) + "\n")
                        except json.JSONDecodeError:
                            pass
                    last_inbox_size = len(lines)
        except OSError:
            pass
        time.sleep(5)


def start_daemon() -> int:
    if is_daemon_running():
        print(f"Hostess7 already ON — pid {PID_FILE.read_text().strip()}")
        return 0
    _ensure_layout()
    proc = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "daemon"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        env={
            **os.environ,
            "HOSTESS7_AGENTS": "13",
            "HOSTESS7_INTERNET": "1",
        },
    )
    PID_FILE.write_text(str(proc.pid), encoding="utf-8")
    write_state(running=True, pid=proc.pid)
    time.sleep(0.5)
    print(f"Hostess7 ON — 13 agents (Prime + 12 Experts) + internet · pid={proc.pid}")
    print("  ./Hostess7.sh          talk UI (13-agent fusion when ON)")
    print("  ./Hostess7.sh agents   status")
    print("  ./Hostess7.sh dept-research  Prime dispatches departments")
    print("  ./Hostess7.sh off      stop")
    print("METRIC agents13_running=1")
    print(f"METRIC agents13_pid={proc.pid}")
    print("OK hostess7-on")
    return 0


def stop_daemon() -> int:
    if not PID_FILE.is_file():
        write_state(running=False)
        print("Hostess7 already OFF")
        print("OK hostess7-off")
        return 0
    try:
        pid = int(PID_FILE.read_text().strip())
        os.kill(pid, signal.SIGTERM)
        for _ in range(20):
            if not _pid_alive(pid):
                break
            time.sleep(0.1)
        if _pid_alive(pid):
            os.kill(pid, signal.SIGKILL)
    except (ValueError, OSError):
        pass
    PID_FILE.unlink(missing_ok=True)
    write_state(running=False)
    print("Hostess7 OFF — agents stopped")
    print("METRIC agents13_running=0")
    print("OK hostess7-off")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        return agents_status_cmd()
    cmd = sys.argv[1]
    if cmd in ("on", "start"):
        return start_daemon()
    if cmd in ("off", "stop"):
        return stop_daemon()
    if cmd == "daemon":
        return daemon_loop()
    if cmd in ("status", "agents"):
        return agents_status_cmd()
    if cmd in ("ask", "query") and len(sys.argv) >= 3:
        os.environ.setdefault("HOSTESS7_AGENTS", "13")
        os.environ.setdefault("HOSTESS7_INTERNET", "1")
        return agents_ask(" ".join(sys.argv[2:]))
    return agents_status_cmd()


if __name__ == "__main__":
    raise SystemExit(main())