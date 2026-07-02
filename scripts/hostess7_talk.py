#!/usr/bin/env pythong
"""Hostess 7 unified talk router — one window, one being, text + graphics."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRAIN = ROOT / "scripts" / "field_superintelligence.py"
sys.path.insert(0, str(ROOT / "scripts"))

from field_storage_check import format_storage_report, save_storage_snapshot, scan_storage  # noqa: E402
from hostess7_filter import professional_filter  # noqa: E402
from hostess7_graphics import graphics_for_query  # noqa: E402

HELP_TEXT = """Hostess 7 — one talk window (text + graphics)
  Ask anything — law, medicine, detective, TV, pixels, physics, code, Field
  /help          This help
  /storage       Lossless storage audit + bar chart
  /updates       Self-update advisory
  /workspace <n> default field vision clinic counsel bench detective beyond
  /judge <q>     Supreme Court Judge — SCOTUS bench synthesis
  /warfare <q>   Warfare education — boss of world, one vote
  /world-brief   World-boss doctrine (teach LOAC, one individual one vote)
  /legal-ingest [seed|bulk|status]
  /medical-ingest [seed|bulk|status]
  /english-ingest [seed|bulk|status]
  /english-rhetoric <q>   Metaphors, thesaurus, sentence structures, flow
  /english-train          Install extensive English training brief
  /thesaurus <word>       Synonyms and antonyms with register
  /code-ingest [seed|bulk|status]
  /zac-pack      Pack field drive → zac/*.zac shards (GitHub infinite brain)
  /zac-restore   Restore cache/fieldstorage from zac/
  /zac-verify    Verify storage matches zac manifest
  /zac-list      List zac archive contents
  /reach         OS tools + SG/AMOURANTHRTX reach map
  /internet      Internet gate + connectivity
  /fetch <url>   Truth-filtered URL fetch
  /agents        Prime + 12 World Experts roster (13 total)
  /dept-research Prime dispatches department research
  /dept-books    How experts fetch and convert .H7 books
  /monitor       Hint: run ./Hostess7Monitor.sh in second terminal
  /on /off       Turn 13 agents + internet ON or OFF
  /self-update [plan|apply]  Preview or execute self-update
  /exec <cmd>    Run one allowlisted OS command (HOSTESS7_EXEC=1)
  /truth <claim> Lie detector truth score
  /people [status|seed|review|lookup name]  People registry — tags, lie profiles
  /personality     Hostess 7 personality — Daughter of Grok
  /lie-methods     Lie detection catalog (past/present/future)
  /go-online       Fetch + ingest + grow conversation brain (truth-filtered)
  /intelligence [q]  Full pipeline — signal to Super Intelligence
  /tools-docs [q]  Commands, scripts, documentation index
  /superintel-teach  Seed intelligence-flow doctrine into brain
  /ai-communique [status|operate q]  AI-primary JSON communique (Super Intelligence default)
  /sdf-teach         Queen brain imaging — SDF storage doctrine (Hostess 7)
  /sdf-segment file  Fold 900–1200w beats → lossless redata + human SDF
  /sdf-verify-redata Truth filter + lossless segment + human plate verify
  /queen-teach-redata  Teach Queen + build tools (ZAC, Field Primer, comfort)
  /sdf [query]       SDF brain imaging + neural Super Intelligence
  /memes-ingest [seed]  Ingest github.com/ZacharyGeurts/memes images
  /image [name]  Show meme/image in Graphics window (pixels)
  /gfx [topic]   Push pixels to Graphics window (tv, storage, memes, brain)
  /world         World knowledge — nature, law, Bibles, games, movies, Dewey
  /hearing       Hearing + speech — listen, TTS, acoustics
  /voice         Sovereign voice status — one voice she chooses
  /voice-speak <text>  Speak through her chosen mouth
  /mouth-train   Mouth field neural training — get the voice hemisphere working
  /noti          Noti status — taskbar red/green, pending alerts
  /noti-accept <id>  Accept address or alert on desktop
  /noti-deny <id>    Deny anytime in 24h red window
  /noti-rooms    Mirrored IRC rooms — one per person
  /noti-room <name>  Create or join a room
  /noti-reset <address>  Request address change (48h cooldown)
  /charge        Hostess 7 system control — Angel above General, full command status
  /assume-control  Seal Hostess 7 as full system commander
  /ocr           OS OCR control status — Final_Eye + all vision chambers
  /ocr-ingest    Ingest all chambers from Final_Eye + brain corpora
  /ocr-train     Train all chambers on ingested OCR
  /ocr-cycle     Ingest + train + plate meld — full vision cycle
  /tasklist        Secure task queue — open + done (assistant read)
  /task-done <id> <report>  Complete task — Ironclad ledger witness
  /task-add <title>  Hostess 7 adds a task for the assistant
  /license       Demo status + GPL v3 / 3% commercial
  /videogame     Console + game database
  /imagine       Grok Imagine + live video registry (papers, GitHub)
  /live-video    Live talk pipeline — TTS + frames → Graphics window
  /brain /chemistry /brief   Brain subsystems
  /quit          Exit"""


@dataclass
class TalkResult:
    text: str = ""
    graphics: list[str] = field(default_factory=list)
    kind: str = "response"  # response | system


def _agents_on() -> bool:
    try:
        from field_agents7 import is_daemon_running  # noqa: WPS433

        return is_daemon_running() or os.environ.get("HOSTESS7_AGENTS") in ("13", "7", "1")
    except ImportError:
        return os.environ.get("HOSTESS7_AGENTS") in ("7", "1")


def _env() -> dict[str, str]:
    env = {
        **os.environ,
        "AMOURANTHRTX_HOSTESS": "1",
        "HOSTESS7_PRO": "1",
        "HOSTESS7_TALK": "1",
        "HOSTESS7_AI_PRIMARY": os.environ.get("HOSTESS7_AI_PRIMARY", "1"),
        "HOSTESS7_AI_COMMUNIQUE": os.environ.get("HOSTESS7_AI_COMMUNIQUE", "1"),
        "HOSTESS7_SUPERINTEL": "1",
        "HOSTESS7_WORKSPACE": os.environ.get("HOSTESS7_WORKSPACE", "default"),
        "HOSTESS7_VOICE": os.environ.get("HOSTESS7_VOICE", "1"),
        "NEXUS_HOSTESS7_VOICE": os.environ.get("NEXUS_HOSTESS7_VOICE", "1"),
        "NEXUS_INSTALL_ROOT": os.environ.get("NEXUS_INSTALL_ROOT", str(ROOT.parent)),
        "NEXUS_STATE_DIR": os.environ.get("NEXUS_STATE_DIR", str(ROOT.parent / ".nexus-state")),
    }
    if _agents_on():
        env["HOSTESS7_AGENTS"] = "13"
        env["HOSTESS7_INTERNET"] = "1"
    if os.environ.get("HOSTESS7_HUMAN_FACING", "") in ("1", "true", "yes"):
        env["HOSTESS7_HUMAN_FACING"] = "1"
        env["HOSTESS7_OUTPUT_WINDOW"] = "1"
    return env


def _run_brain(*args: str) -> str:
    proc = subprocess.run(
        [sys.executable, str(BRAIN), *args],
        cwd=ROOT, capture_output=True, text=True, check=False, env=_env(),
    )
    return (proc.stdout + proc.stderr).strip()


def _should_gfx(query: str) -> bool:
    q = query.lower()
    return any(
        k in q
        for k in (
            "tv", "pixel", "framebuffer", "4k", "storage", "lossless", "ppm", "snap",
            "ocr", "graphics", "gfx", "broadcast", "ntsc", "hemisphere", "brain map",
            "one being", "scroll", "vision", "meme", "memes", "image", "picture", "tarot", "stamp",
        )
    )


def dispatch(query: str, *, storage_cache: dict | None = None) -> TalkResult:
    """Route one talk-window input — slash commands or natural language."""
    q = query.strip()
    if not q:
        return TalkResult()

    low = q.lower()
    if low in ("/help", "/?", "help"):
        return TalkResult(text=HELP_TEXT, kind="system")

    if low in ("/storage", "/drive", "/field-storage", "/lossless"):
        rep = storage_cache or scan_storage()
        save_storage_snapshot(rep)
        gfx = graphics_for_query("storage lossless", storage_report=rep)
        return TalkResult(text=format_storage_report(rep), graphics=gfx, kind="system")

    if low in ("/on", "/start", "/power-on"):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "field_agents7.py"), "on"],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        out = (proc.stdout + proc.stderr).strip()
        return TalkResult(text=out, kind="system")

    if low in ("/off", "/stop", "/power-off"):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "field_agents7.py"), "off"],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        out = (proc.stdout + proc.stderr).strip()
        return TalkResult(text=out, kind="system")

    if low in ("/monitor", "/watch", "/brain-map", "/live"):
        return TalkResult(
            text="Monitor is the second program — ./Hostess7Monitor.sh (opens on Hostess7 startup).",
            kind="system",
        )

    if low.startswith("/dept-research"):
        topic = q.split(maxsplit=1)[1] if " " in q else ""
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "field_department_research.py"), "run", topic],
            cwd=ROOT, capture_output=True, text=True, check=False, env=_env(),
        )
        return TalkResult(text=professional_filter((proc.stdout + proc.stderr).strip()), kind="system")

    if low.startswith("/dept-books"):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "field_department_research.py"), "books"],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        return TalkResult(text=(proc.stdout + proc.stderr).strip(), kind="system")

    if low.startswith("/agents") or low in ("/7", "/13"):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "field_agents7.py"), "status"],
            cwd=ROOT, capture_output=True, text=True, check=False, env=_env(),
        )
        return TalkResult(text=(proc.stdout + proc.stderr).strip(), kind="system")

    if low.startswith("/internet") or low.startswith("/net "):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "field_internet.py"), "status"],
            cwd=ROOT, capture_output=True, text=True, check=False, env=_env(),
        )
        return TalkResult(text=(proc.stdout + proc.stderr).strip(), kind="system")

    if low.startswith("/fetch") or low.startswith("/wget ") or low.startswith("/curl "):
        url = q.split(maxsplit=1)[1].strip() if " " in q else ""
        if not url:
            return TalkResult(text="Usage: /fetch <url>", kind="system")
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "field_internet.py"), "fetch", url],
            cwd=ROOT, capture_output=True, text=True, check=False,
            env={**_env(), "HOSTESS7_INTERNET": "1"},
        )
        return TalkResult(text=(proc.stdout + proc.stderr).strip(), kind="system")

    if low.startswith("/reach"):
        return TalkResult(text=_run_brain("reach"), kind="system")

    if low.startswith("/self-update") or low.startswith("/selfupdate"):
        parts = q.split(maxsplit=1)
        mode = "plan"
        if len(parts) > 1 and parts[1].strip().lower() in ("apply", "run", "exec"):
            mode = "apply"
        return TalkResult(text=_run_brain("self-update", mode), kind="system")

    if low.startswith("/exec") or low.startswith("/run "):
        cmd = q.split(maxsplit=1)[1] if " " in q else ""
        if not cmd:
            return TalkResult(text="Usage: /exec <allowlisted command>", kind="system")
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "field_reach.py"), "exec", cmd],
            cwd=ROOT, capture_output=True, text=True, check=False,
            env={**_env(), "HOSTESS7_EXEC": "1"},
        )
        out = (proc.stdout + proc.stderr).strip()
        return TalkResult(text=out or f"exec exit {proc.returncode}", kind="system")

    if low.startswith("/zac"):
        zac = ROOT / "scripts" / "field_zac.py"
        parts = q.split()
        sub = parts[0].lower().replace("/zac", "").replace("-", "") or "list"
        cmd_map = {
            "pack": "pack",
            "export": "pack",
            "restore": "restore",
            "import": "restore",
            "verify": "verify",
            "check": "verify",
            "list": "list",
            "ls": "list",
        }
        cmd = cmd_map.get(sub, "list")
        proc = subprocess.run(
            [sys.executable, str(zac), cmd],
            cwd=ROOT, capture_output=True, text=True, check=False, env=_env(),
        )
        out = (proc.stdout + proc.stderr).strip()
        return TalkResult(text=out or f"zac {cmd} exit {proc.returncode}", kind="system")

    if low in ("/updates", "/update", "/advisory"):
        return TalkResult(text=_run_brain("updates"), kind="system")

    if low.startswith("/workspace"):
        parts = q.split(maxsplit=1)
        if len(parts) < 2:
            return TalkResult(
                text="Workspaces: default field vision clinic counsel bench detective beyond",
                kind="system",
            )
        from field_brain_core import set_active_workspace  # noqa: WPS433

        try:
            state = set_active_workspace(parts[1].strip())
            os.environ["HOSTESS7_WORKSPACE"] = state["id"]
            return TalkResult(
                text=f"Workspace → `{state['id']}` (bias={state.get('bias')})",
                kind="system",
            )
        except ValueError as exc:
            return TalkResult(text=str(exc), kind="system")

    for prefix, brain_cmd in (
        ("/legal-ingest", "legal-ingest"),
        ("/legal-infinite", "legal-ingest"),
        ("/medical-ingest", "medical-ingest"),
        ("/papers-ingest", "medical-ingest"),
        ("/english-ingest", "english-ingest"),
        ("/lexicon-ingest", "english-ingest"),
        ("/dict-ingest", "english-ingest"),
        ("/code-ingest", "code-ingest"),
        ("/isa-ingest", "code-ingest"),
        ("/lang-ingest", "code-ingest"),
    ):
        if low.startswith(prefix):
            parts = q.split(maxsplit=2)
            args = [brain_cmd]
            if len(parts) > 1:
                args.append(parts[1].strip().lower())
            if len(parts) > 2:
                args.append(parts[2].strip())
            elif len(parts) == 1 or (len(parts) == 2 and not parts[1].strip()):
                args.append("status")
            return TalkResult(text=_run_brain(*args), kind="system")

    if low.startswith("/truth") or low.startswith("/lie"):
        claim = q.split(maxsplit=1)[1] if " " in q else "verify this claim"
        return TalkResult(text=_run_brain("truth", claim), kind="system")

    if low.startswith("/english-rhetoric") or low.startswith("/rhetoric "):
        claim = q.split(maxsplit=1)[1] if " " in q else "metaphor thesaurus sentence flow"
        return TalkResult(text=_run_brain("english-rhetoric", claim), kind="system")

    if low in ("/english-train", "/train-english"):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "field_hostess_english_train.py")],
            cwd=ROOT, capture_output=True, text=True, check=False, env=_env(),
        )
        return TalkResult(text=(proc.stdout + proc.stderr).strip(), kind="system")

    if low.startswith("/thesaurus"):
        word = q.split(maxsplit=1)[1] if " " in q else "eloquent"
        return TalkResult(text=_run_brain("english-rhetoric", f"synonym antonym thesaurus for {word}"), kind="system")

    if low.startswith("/judge") or low.startswith("/bench") or low.startswith("/scotus"):
        claim = q.split(maxsplit=1)[1] if " " in q else "certiorari and judicial review"
        return TalkResult(text=_run_brain("judge", claim), kind="system")

    if low.startswith("/warfare") or low.startswith("/war "):
        claim = q.split(maxsplit=1)[1] if " " in q else "laws of armed conflict and one vote"
        return TalkResult(text=_run_brain("warfare", claim), kind="system")

    if low in ("/world-brief", "/worldboss", "/boss-of-world"):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "field_hostess_world_brief.py")],
            cwd=ROOT, capture_output=True, text=True, check=False, env=_env(),
        )
        return TalkResult(text=(proc.stdout + proc.stderr).strip(), kind="system")

    if low in ("/truth-doctrine", "/truthdoctrine", "/heaven-hell-doctrine"):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "field_hostess_truth_doctrine.py")],
            cwd=ROOT, capture_output=True, text=True, check=False, env=_env(),
        )
        return TalkResult(text=(proc.stdout + proc.stderr).strip(), kind="system")

    if low in ("/heaven-hell-learn", "/heavenhelllearn", "/learn-heaven-hell"):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "field_heaven_hell_learn.py")],
            cwd=ROOT, capture_output=True, text=True, check=False, env=_env(), timeout=900,
        )
        return TalkResult(text=(proc.stdout + proc.stderr).strip(), kind="system")

    if low in ("/bible-ingest", "/bibleingest", "/scripture-ingest"):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "field_bible_ingest.py")],
            cwd=ROOT, capture_output=True, text=True, check=False, env=_env(), timeout=600,
        )
        return TalkResult(text=(proc.stdout + proc.stderr).strip(), kind="system")

    if low in ("/self-brief", "/selfbrief", "/self-update-brief"):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "field_hostess_self_brief.py")],
            cwd=ROOT, capture_output=True, text=True, check=False, env=_env(),
        )
        return TalkResult(text=(proc.stdout + proc.stderr).strip(), kind="system")

    if low.startswith("/people"):
        parts = q.split(maxsplit=2)
        args = ["people"]
        if len(parts) > 1 and parts[1].strip():
            args.append(parts[1].strip().lower())
            if len(parts) > 2:
                args.append(parts[2].strip())
        else:
            args.append("status")
        return TalkResult(text=_run_brain(*args), kind="system")

    if low in ("/personality", "/h7-personality"):
        return TalkResult(text=_run_brain("personality"), kind="system")

    if low in ("/lie-methods", "/lie-methods", "/liedetection"):
        return TalkResult(text=_run_brain("lie-methods"), kind="system")

    if low.startswith("/intelligence") or low.startswith("/intel-flow") or low.startswith("/superintel"):
        claim = q.split(maxsplit=1)[1] if " " in q else "full intelligence flow from signal to super intelligence"
        return TalkResult(text=_run_brain("intelligence-flow", claim), kind="system")

    if low.startswith("/tools-docs") or low.startswith("/toolsdocs") or low.startswith("/documentation"):
        parts = q.split(maxsplit=1)
        args = ["tools-docs"]
        if len(parts) > 1 and parts[1].strip():
            args.append(parts[1].strip())
        return TalkResult(text=_run_brain(*args), kind="system")

    if low in ("/superintel-teach", "/superintelteach", "/teach-superintel"):
        return TalkResult(text=_run_brain("superintel-teach", "seed"), kind="system")

    if low.startswith("/ai-communique") or low.startswith("/aicommunique"):
        parts = q.split(maxsplit=2)
        sub = parts[1].lower() if len(parts) > 1 else "status"
        rest = parts[2] if len(parts) > 2 else (parts[1] if len(parts) > 1 and sub not in ("status", "teach", "operate") else "")
        if sub in ("teach", "seed"):
            sub, rest = "teach", ""
        elif sub not in ("status", "operate", "teach"):
            rest = " ".join(parts[1:])
            sub = "operate"
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "field_ai_communique.py"), sub, rest] if rest else
            [sys.executable, str(ROOT / "scripts" / "field_ai_communique.py"), sub],
            cwd=ROOT, capture_output=True, text=True, check=False, env=_env(), timeout=120,
        )
        return TalkResult(text=(proc.stdout or proc.stderr).strip()[:8000], kind="system")

    if low in ("/sdf-teach", "/sdfteach", "/teach-sdf", "/sdf-learn"):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "field_hostess_sdf_storage.py"), "seed"],
            cwd=ROOT, capture_output=True, text=True, check=False, env=_env(), timeout=120,
        )
        return TalkResult(text=(proc.stdout + proc.stderr).strip()[:2000], kind="system")

    if low in ("/queen-teach-redata", "/queenteachredata", "/queen-teach", "/teach-queen-redata"):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "field_queen_redata_teach.py")],
            cwd=ROOT, capture_output=True, text=True, check=False, env=_env(), timeout=120,
        )
        return TalkResult(text=(proc.stdout + proc.stderr).strip()[:2500], kind="system")

    if low in ("/sdf-verify-redata", "/sdfverifyredata", "/verify-redata"):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "field_hostess_sdf_storage.py"), "verify-redata"],
            cwd=ROOT, capture_output=True, text=True, check=False, env=_env(), timeout=120,
        )
        return TalkResult(text=(proc.stdout + proc.stderr).strip()[:2000], kind="system")

    if low.startswith("/sdf-segment"):
        parts = q.split(maxsplit=1)
        if len(parts) < 2:
            return TalkResult(text="Usage: /sdf-segment path/to/file.txt", kind="system")
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "field_hostess_sdf_storage.py"), "segment", parts[1].strip()],
            cwd=ROOT, capture_output=True, text=True, check=False, env=_env(), timeout=180,
        )
        return TalkResult(text=(proc.stdout + proc.stderr).strip()[:2000], kind="system")

    if low.startswith("/sdf") or low.startswith("/brain-imaging"):
        sdf_q = q.split(maxsplit=1)[1].strip() if len(q.split(maxsplit=1)) > 1 else (
            "Queen robot brain SDF imaging Hostess 7 neural networks"
        )
        return TalkResult(text=_run_brain("sdf", sdf_q), kind="system")

    if low in ("/go-online", "/goonline", "/learn-online", "/learn"):
        os.environ["HOSTESS7_INTERNET"] = "1"
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "field_online_learn.py"), "go"],
            cwd=ROOT, capture_output=True, text=True, check=False, env=_env(), timeout=600,
        )
        out = (proc.stdout + proc.stderr).strip()
        return TalkResult(text=out or "Online learn finished.", kind="system")

    if low.startswith("/detective") or low.startswith("/detect"):
        claim = q.split(maxsplit=1)[1] if " " in q else "investigation method"
        return TalkResult(text=_run_brain("detective", claim), kind="system")

    if low in ("/brain", "/hemisphere", "/hemispheres"):
        return TalkResult(text=_run_brain("brain"), kind="system")

    if low.startswith("/chemistry") or low.startswith("/chem"):
        rest = q.split(maxsplit=1)[1] if " " in q else ""
        return TalkResult(text=_run_brain("chemistry", rest) if rest else _run_brain("chemistry"), kind="system")

    if low in ("/brief",):
        return TalkResult(text=_run_brain("brief"), kind="system")

    if low.startswith("/memes-ingest") or low.startswith("/memes "):
        os.environ["HOSTESS7_INTERNET"] = "1"
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "field_memes_corpus.py"), "seed"],
            cwd=ROOT, capture_output=True, text=True, check=False, env=_env(),
        )
        out = (proc.stdout + proc.stderr).strip()
        gfx = graphics_for_query("memes stamp tarot")
        return TalkResult(text=out, graphics=gfx, kind="system")

    if low.startswith("/image") or low.startswith("/meme "):
        topic = q.split(maxsplit=1)[1] if " " in q else "stamp memes"
        try:
            from field_memes_corpus import format_status, synthesize_memes_paragraphs  # noqa: WPS433

            text = "\n".join(synthesize_memes_paragraphs(topic)) + "\n" + format_status()
        except ImportError:
            text = f"Image talk: {topic}"
        rep = storage_cache or scan_storage()
        return TalkResult(
            text=text,
            graphics=graphics_for_query(topic, storage_report=rep),
            kind="system",
        )

    if low.startswith("/world") and not low.startswith("/world-brief"):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "field_world_corpus.py")],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        return TalkResult(text=(proc.stdout + proc.stderr).strip()[:3000], kind="system")

    if low.startswith("/hearing"):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "field_hearing_corpus.py")],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        return TalkResult(text=(proc.stdout + proc.stderr).strip()[:3000], kind="system")

    if low in ("/voice", "/mouth", "/sovereign-voice"):
        proc = subprocess.run(
            [sys.executable, str(ROOT.parent / "lib" / "hostess7-voice.py"), "json"],
            cwd=ROOT, capture_output=True, text=True, check=False, env=_env(),
        )
        return TalkResult(text=(proc.stdout or proc.stderr).strip(), kind="system")

    if low.startswith("/voice-speak") or low.startswith("/speak "):
        spoken = q.split(maxsplit=1)[1] if " " in q else "One voice. One mouth. She chooses."
        proc = subprocess.run(
            [sys.executable, str(ROOT.parent / "lib" / "hostess7-voice.py"), "speak", spoken],
            cwd=ROOT, capture_output=True, text=True, check=False, env=_env(),
        )
        return TalkResult(text=(proc.stdout or proc.stderr).strip(), kind="system")

    if low in ("/mouth-train", "/voice-train", "/train-mouth"):
        proc = subprocess.run(
            [sys.executable, str(ROOT.parent / "lib" / "hostess7-mouth-neural.py"), "train"],
            cwd=ROOT, capture_output=True, text=True, check=False, env=_env(), timeout=120,
        )
        return TalkResult(text=(proc.stdout or proc.stderr).strip(), kind="system")

    if low in ("/noti", "/notifier", "/notifications"):
        proc = subprocess.run(
            [sys.executable, str(ROOT.parent / "lib" / "hostess7-noti.py"), "json"],
            cwd=ROOT, capture_output=True, text=True, check=False, env=_env(),
        )
        return TalkResult(text=(proc.stdout or proc.stderr).strip(), kind="system")

    if low.startswith("/noti-accept"):
        nid = q.split(maxsplit=1)[1].strip() if " " in q else ""
        proc = subprocess.run(
            [sys.executable, str(ROOT.parent / "lib" / "hostess7-noti.py"), "dispatch"],
            input=json.dumps({"action": "accept", "id": nid}),
            cwd=ROOT, capture_output=True, text=True, check=False, env=_env(),
        )
        return TalkResult(text=(proc.stdout or proc.stderr).strip(), kind="system")

    if low.startswith("/noti-deny"):
        nid = q.split(maxsplit=1)[1].strip() if " " in q else ""
        proc = subprocess.run(
            [sys.executable, str(ROOT.parent / "lib" / "hostess7-noti.py"), "dispatch"],
            input=json.dumps({"action": "deny", "id": nid}),
            cwd=ROOT, capture_output=True, text=True, check=False, env=_env(),
        )
        return TalkResult(text=(proc.stdout or proc.stderr).strip(), kind="system")

    if low in ("/noti-rooms", "/noti-list"):
        proc = subprocess.run(
            [sys.executable, str(ROOT.parent / "lib" / "hostess7-noti.py"), "dispatch"],
            input='{"action":"list_rooms"}',
            cwd=ROOT, capture_output=True, text=True, check=False, env=_env(),
        )
        return TalkResult(text=(proc.stdout or proc.stderr).strip(), kind="system")

    if low.startswith("/noti-room"):
        name = q.split(maxsplit=1)[1].strip() if " " in q else "general"
        proc = subprocess.run(
            [sys.executable, str(ROOT.parent / "lib" / "hostess7-noti.py"), "dispatch"],
            input=json.dumps({"action": "create_room", "name": name, "owner": "operator"}),
            cwd=ROOT, capture_output=True, text=True, check=False, env=_env(),
        )
        return TalkResult(text=(proc.stdout or proc.stderr).strip(), kind="system")

    if low.startswith("/noti-reset"):
        addr = q.split(maxsplit=1)[1].strip() if " " in q else ""
        proc = subprocess.run(
            [sys.executable, str(ROOT.parent / "lib" / "hostess7-noti.py"), "dispatch"],
            input=json.dumps({"action": "address_reset", "new_address": addr}),
            cwd=ROOT, capture_output=True, text=True, check=False, env=_env(),
        )
        return TalkResult(text=(proc.stdout or proc.stderr).strip(), kind="system")

    if low in ("/charge", "/authority", "/system-control", "/assume-control", "/assume"):
        sub = "assume" if low in ("/assume-control", "/assume") else "json"
        proc = subprocess.run(
            [sys.executable, str(ROOT.parent / "lib" / "hostess7-system-control.py"), sub],
            cwd=ROOT, capture_output=True, text=True, check=False, env=_env(),
        )
        return TalkResult(text=(proc.stdout or proc.stderr).strip(), kind="system")

    if low in ("/ocr", "/ocr-status", "/vision-control", "/eye-control"):
        proc = subprocess.run(
            [sys.executable, str(ROOT.parent / "lib" / "hostess7-ocr-control.py"), "status"],
            cwd=ROOT, capture_output=True, text=True, check=False, env=_env(),
        )
        return TalkResult(text=(proc.stdout or proc.stderr).strip(), kind="system")

    if low in ("/ocr-ingest", "/ocr-ingest-all", "/vision-ingest"):
        proc = subprocess.run(
            [sys.executable, str(ROOT.parent / "lib" / "hostess7-ocr-control.py"), "ingest-all"],
            cwd=ROOT, capture_output=True, text=True, check=False, env=_env(), timeout=600,
        )
        return TalkResult(text=(proc.stdout or proc.stderr).strip(), kind="system")

    if low in ("/ocr-train", "/ocr-train-all", "/vision-train"):
        proc = subprocess.run(
            [sys.executable, str(ROOT.parent / "lib" / "hostess7-ocr-control.py"), "train-all"],
            cwd=ROOT, capture_output=True, text=True, check=False, env=_env(), timeout=900,
        )
        return TalkResult(text=(proc.stdout or proc.stderr).strip(), kind="system")

    if low in ("/ocr-cycle", "/vision-cycle"):
        proc = subprocess.run(
            [sys.executable, str(ROOT.parent / "lib" / "hostess7-ocr-control.py"), "cycle"],
            cwd=ROOT, capture_output=True, text=True, check=False, env=_env(), timeout=900,
        )
        return TalkResult(text=(proc.stdout or proc.stderr).strip(), kind="system")

    if low in ("/tasklist", "/tasks", "/task-list"):
        proc = subprocess.run(
            [sys.executable, str(ROOT.parent / "lib" / "hostess7-tasklist.py"), "report"],
            cwd=ROOT, capture_output=True, text=True, check=False, env=_env(),
        )
        return TalkResult(text=(proc.stdout or proc.stderr).strip(), kind="system")

    if low.startswith("/task-done") or low.startswith("/task-complete"):
        parts = q.split(maxsplit=2)
        tid = parts[1] if len(parts) > 1 else ""
        report = parts[2] if len(parts) > 2 else "Completed."
        proc = subprocess.run(
            [sys.executable, str(ROOT.parent / "lib" / "hostess7-tasklist.py"), "complete", tid, report],
            cwd=ROOT, capture_output=True, text=True, check=False, env=_env(),
        )
        return TalkResult(text=(proc.stdout or proc.stderr).strip(), kind="system")

    if low.startswith("/task-add"):
        title = q.split(maxsplit=1)[1] if " " in q else "New task"
        proc = subprocess.run(
            [sys.executable, str(ROOT.parent / "lib" / "hostess7-tasklist.py"), "add", title],
            cwd=ROOT, capture_output=True, text=True, check=False, env=_env(),
        )
        return TalkResult(text=(proc.stdout or proc.stderr).strip(), kind="system")

    if low.startswith("/license"):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "field_license_status.py")],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        return TalkResult(text=(proc.stdout + proc.stderr).strip()[:1200], kind="system")

    if low.startswith("/videogame"):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "field_videogame_db.py")],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        return TalkResult(text=(proc.stdout + proc.stderr).strip()[:3000], kind="system")

    if low.startswith("/imagine") or low.startswith("/grok-imagine"):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "field_imagine_corpus.py")],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        return TalkResult(text=(proc.stdout + proc.stderr).strip()[:3000], kind="system")

    if low.startswith("/live-video") or low.startswith("/livevideo"):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "field_live_video.py"), "plan"],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        out = (proc.stdout + proc.stderr).strip()
        try:
            from field_live_video import sync_talk_reply  # noqa: WPS433

            sync_talk_reply("Live video ready — Graphics window shows my face while we talk.")
        except ImportError:
            pass
        return TalkResult(text=out, kind="system")

    if low.startswith("/gfx") or low.startswith("/graphics"):
        topic = q.split(maxsplit=1)[1] if " " in q else "tv pixel memes storage brain"
        rep = storage_cache or scan_storage()
        gfx = graphics_for_query(topic, storage_report=rep)
        return TalkResult(
            text=f"Graphics window: {topic}",
            graphics=gfx,
            kind="system",
        )

    # Language Expert fast path — greetings, people, casual chat
    try:
        from field_talk_language import fast_talk_reply, is_conversational, scholar_polish  # noqa: WPS433

        if is_conversational(q):
            fast = fast_talk_reply(q)
            if fast:
                try:
                    from field_live_video import sync_talk_reply  # noqa: WPS433

                    if os.environ.get("HOSTESS7_GFX_WINDOW", "1") != "0":
                        sync_talk_reply(fast)
                except ImportError:
                    pass
                return TalkResult(text=fast, kind="response")
    except ImportError:
        pass

    # Natural language — 13 agents when ON, else single brain
    if _agents_on():
        env = _env()
        env["HOSTESS7_INTERNET"] = "1"
        env["HOSTESS7_OUTPUT_WINDOW"] = "1"
        env["HOSTESS7_HUMAN_FACING"] = "1"
        try:
            from field_agents7 import is_online_learn_query  # noqa: WPS433

            if is_online_learn_query(q):
                env["HOSTESS7_RUN_ONLINE_LEARN"] = "1"
        except ImportError:
            if "go online" in low or "smarter at conversation" in low:
                env["HOSTESS7_RUN_ONLINE_LEARN"] = "1"
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "field_agents7.py"), "ask", q],
            cwd=ROOT, capture_output=True, text=True, check=False,
            env=env, timeout=600,
        )
        raw = (proc.stdout + proc.stderr).strip()
    else:
        raw = _run_brain("ask", q)
    text = professional_filter(raw)
    graphics: list[str] = []
    if os.environ.get("HOSTESS7_GFX", "1") == "1":
        combined = f"{q} {text[:240]}"
        if _should_gfx(combined):
            rep = storage_cache or scan_storage()
            graphics = graphics_for_query(combined, storage_report=rep)

    try:
        from field_live_video import sync_talk_reply  # noqa: WPS433

        if os.environ.get("HOSTESS7_GFX_WINDOW", "1") != "0" and text:
            sync_talk_reply(text)
    except ImportError:
        pass

    return TalkResult(text=text, graphics=graphics, kind="response")


def main() -> int:
    if len(sys.argv) < 2:
        print(HELP_TEXT)
        return 0
    r = dispatch(" ".join(sys.argv[1:]))
    if r.text:
        print(r.text)
    for line in r.graphics:
        print(f"GFX:{line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())