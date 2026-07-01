# AmmoLang boundary route — AML_BUILD=1 universal boundary
_aml_find_root() {
  local d="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  while [[ "$d" != "/" ]]; do
    [[ -f "$d/lib/ammolang-run.sh" ]] && echo "$d" && return 0
    d="$(dirname "$d")"
  done
  return 1
}
if [[ "${AML_BUILD:-1}" != "0" ]] && [[ -z "${AML_BOUNDARY_ACTIVE:-}" ]]; then
  _AML_ROOT="$(_aml_find_root 2>/dev/null || true)"
  if [[ -n "$_AML_ROOT" ]]; then
    export AML_BOUNDARY_ACTIVE=1
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:Hostess7/Hostess7.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Hostess 7 — one talk window (text + graphics, lossless-first)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UI="$ROOT/scripts/hostess7_ui.py"
BRAIN="$ROOT/scripts/field_superintelligence.py"
TEAM="$ROOT/scripts/field_team_drive.py"
FIELD_ONE="${NEXUS_INSTALL_ROOT}/lib/field-one.py"
REACH="$ROOT/scripts/field_reach.py"
AGENTS="$ROOT/scripts/field_agents7.py"
NET="$ROOT/scripts/field_internet.py"
export HOSTESS7_ROOT="$ROOT"
_parent="$(cd "$ROOT/.." && pwd)"
if [[ "$(basename "$_parent")" == "NewLatest" ]]; then
  export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-$_parent}"
  export SG_ROOT="${SG_ROOT:-$(cd "$_parent/.." && pwd)}"
else
  export SG_ROOT="${SG_ROOT:-$_parent}"
  export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-${SG_ROOT}/NewLatest}"
fi
export AMOURANTHRTX_ROOT="${AMOURANTHRTX_ROOT:-${SG_ROOT}/AMOURANTHRTX}"
export PYTHONG_ROOT="${PYTHONG_ROOT:-${NEXUS_INSTALL_ROOT}/PythonG}"
export GPY16_ROOT="${GPY16_ROOT:-${NEXUS_INSTALL_ROOT}/Grok16}"
export GROKPY_ROOT="${GROKPY_ROOT:-${PYTHONG_ROOT}}"
export PATH="/usr/bin:/bin:${PYTHONG_ROOT}/bin:${NEXUS_INSTALL_ROOT}/Grok16/bin:${NEXUS_INSTALL_ROOT}/Queen/scripts:${NEXUS_INSTALL_ROOT}/Queen/bin:${PATH}"
export AMOURANTHRTX_HOSTESS=1
export HOSTESS7_PRO=1
# GTK/gnome-terminal AT-SPI noise when HOME is /root (sudo) — harmless but noisy
export NO_AT_BRIDGE="${NO_AT_BRIDGE:-1}"
export GTK_A11Y="${GTK_A11Y:-none}"
export HOSTESS7_VOICE="${HOSTESS7_VOICE:-0}"
export HOSTESS7_LICENSE_MODE="${HOSTESS7_LICENSE_MODE:-war}"
export HOSTESS7_WAR_READY="${HOSTESS7_WAR_READY:-1}"
export HOSTESS7_WORKSPACE="${HOSTESS7_WORKSPACE:-default}"
export HOSTESS7_AI_PRIMARY="${HOSTESS7_AI_PRIMARY:-1}"
export HOSTESS7_AI_COMMUNIQUE="${HOSTESS7_AI_COMMUNIQUE:-1}"
export HOSTESS7_SUPERINTEL="${HOSTESS7_SUPERINTEL:-1}"
FILTER="$ROOT/scripts/hostess7_filter.py"

chmod +x "$0" "$UI" 2>/dev/null || true

usage() {
    cat <<'EOF'
Hostess 7 — one being · talk window (text + graphics)

  ./Hostess7.sh on             Turn ON — Prime + 12 Experts + internet
  ./Hostess7.sh off            Turn OFF — stop agent daemon
  ./Hostess7.sh agents         Prime + 12 World Experts roster (13 total)
  ./Hostess7.sh dept-research    Prime dispatches department research
  ./Hostess7.sh dept-books       How experts fetch/convert .H7 books
  ./Hostess7.sh              Talk UI — everything in scroll window (default)
  ./Hostess7.sh -q "…"       One-shot answer (no UI; 13-agent fusion when ON)
  HOSTESS7_WORKSPACE=field ./Hostess7.sh   Left-biased Field dev workspace
  ./Hostess7.sh brain        Hemisphere map + callosum status
  ./Hostess7.sh chemistry    Synapse levels + enhancements
  ./Hostess7.sh workspace    List workspaces
  ./Hostess7.sh legal-ingest seed     Infinite legal drive (all USC titles + states)
  ./Hostess7.sh legal-ingest torrent <file.torrent>   Bulk fetch → Field → vacuum old
  ./Hostess7.sh medical-ingest seed     Infinite medical papers drive
  ./Hostess7.sh medical-ingest bulk     Ingest papers from staging
  ./Hostess7.sh english-ingest seed     Full English lexicon + CMUdict phonetics
  ./Hostess7.sh english-ingest bulk     Re-ingest from english_bulk staging
  ./Hostess7.sh english-train         Install rhetoric + grammar + interpersonal training
  ./Hostess7.sh english-rhetoric "…"    Metaphors, conjunctions, gerunds, interpersonal flow
  ./Hostess7.sh wants                 Ask Hostess 7 what she wants FIRST (priorities)
  ./Hostess7.sh noti [status|seed|taskbar]  Noti notifier — Hostess 7 tied in
  ./Hostess7.sh charge [assume]  Full system control — Angel above General
  ./Hostess7.sh tasklist [report|seed|json]  Secure task queue — she fills, assistant executes
  ./Hostess7.sh task-done <id> "report"  Mark task complete with Ironclad ledger
  ./Hostess7.sh security-learn        Computer, network, security + NEXUS corpus
  ./Hostess7.sh security "…"          Query security / network / NEXUS expertise
  ./Hostess7.sh stack-learn           SG Field Stack corpus (KILROY, boot, kill tech, field drive)
  ./Hostess7.sh stack [status|"…"]    Live stack health or query boot order / field mirror
  ./Hostess7.sh nexus [status|verify|panel|update|test]  NEXUS-Shield control
  ./Hostess7.sh library-organize      Sort free books — fiction, children, STEM shelves
  ./Hostess7.sh sg-hub                SG/Hostess7 main folder manifest + TEAM sync hint
  ./Hostess7.sh online-security       GitHub Pages security checklist
  ./Hostess7.sh github [status|invite|bootstrap]  Bot @hostess7 repo access
  ./Hostess7.sh github-secure [verify|audit|route|publish|push|clone]  Pinned SSH — no MITM/redirect
  ./Hostess7.sh queen-github-secure [verify|status]  Queen Browser GitHub pin check
  ./Hostess7.sh k12-ingest seed       K-12 OER textbook catalog (grades K-12)
  ./Hostess7.sh k12-ingest fetch      Fetch ALL catalog URLs — truth-filter on input
  ./Hostess7.sh k12 "…"               Query K-12 textbook brain (+ H7 library read)
  ./Hostess7.sh library-build         Pack free books → .H7 (fast: ≤3 MiB, ≥3 MiB/s)
  ./Hostess7.sh library-build --stem  Programming, physics, chemistry, medical only
  ./Hostess7.sh library-list          List .H7 volumes on shelf
  ./Hostess7.sh library-read <id>     Hostess 7 reads full .H7 book (line range optional)
  ./Hostess7.sh library-search "…"    Search H7 library by title/subject
  ./Hostess7.sh code-ingest seed        ISA opcodes + all programming languages
  ./Hostess7.sh code "6502 LDA"         Assembly / language query
  ./Hostess7.sh updates               Self-update advisory (truth-filtered)
  ./Hostess7.sh reach                 OS tools + SG/AMOURANTHRTX reach map
  ./Hostess7.sh self-update plan      Preview allowlisted self-update steps
  ./Hostess7.sh self-update apply     Execute self-update (HOSTESS7_EXEC=1)
  ./Hostess7.sh exec "git status"     Run one allowlisted OS command
  ./Hostess7.sh internet              Internet gate status + connectivity
  ./Hostess7.sh fetch <url>           Truth-filtered URL fetch (cache)
  ./Hostess7.sh go-online             Fetch + learn (Owner/Amouranth X, warfare, alert posture)
  ./Hostess7.sh people-learn          Truth-filtered ZacharyGeurts + Amouranth online
  ./Hostess7.sh alert-posture on      Heightened alert — stun/RF/terror vigilance
  ./Hostess7.sh learn-online          Alias for go-online
  ./Hostess7.sh online-wants          Show curated online learning plan (no fetch)
  ./Hostess7.sh memes-ingest seed     Ingest github.com/ZacharyGeurts/memes (image talk)
  ./Hostess7.sh image [name]          Show meme/image in Graphics window (pixels)
  ./Hostess7Graphics.sh             Pixel + text Graphics window (GTK — not ASCII)
  ./Hostess7Monitor.sh              Live monitor (second terminal — auto-opens on start)
  ./Hostess7.sh gfx [topic]           Push scene to Graphics window
  ./Hostess7.sh gfx-api               Canvas API — place pixels and text
  ./Hostess7.sh world-learn           Nature, law, Bibles, games, movies, videogames, Dewey (fast)
  ./Hostess7.sh world "…"             Query world knowledge corpus
  ./Hostess7.sh videogame-db          Console + game database status
  ./Hostess7.sh hearing-learn         Hearing + speech science, STT/TTS, free textbooks
  ./Hostess7.sh hearing "…"           Query hearing corpus
  ./Hostess7.sh boot                  KILROY doctrine · brain on · web (GitHub Pages / Codespaces)
  ./Hostess7.sh web                   Web chat UI (port 8080 — GitHub Codespaces)
  ./Hostess7.sh web-start             Background web on :8080
  ./Hostess7.sh zac-restore           Restore cache/fieldstorage from zac/
  ./Hostess7.sh license               Demo status + GPL v3 / 3% commercial terms
  ./Hostess7.sh compression-test      Lossless FLD1 + H7 + ZAC round-trip QA
  ./Hostess7.sh imagine-learn         Grok Imagine + live video papers/GitHub fetch
  ./Hostess7.sh imagine-nexus-teach   NEXUS imaging skills → Imagine corpus (PIL, combinatronic, Big Drive)
  ./Hostess7.sh imaging-work          Imaging work queue — broken assets, missing icons
  ./Hostess7.sh imagine "…"           Query Imagine + talking-head corpus
  ./Hostess7.sh live-video            Live talk pipeline (TTS + Graphics frames)
  ./Hostess7.sh live-video-demo       Demo talk frame in Graphics window
  ./Hostess7.sh judge "…"           Supreme Court Judge — SCOTUS bench synthesis
  ./Hostess7.sh warfare "…"         Warfare education (LOAC, just war) — boss of world, one vote
  ./Hostess7.sh warfare-expand      Refresh warfare v3 + alert posture
  ./Hostess7.sh warfare-self-teach  Historic-first self-teach — measures/countermeasures/invincibility
  ./Hostess7.sh warfare-smarts-test Very difficult smarts exam (85%% pass bar)
  ./Hostess7.sh reality-familiarize   Register all domains · map whole of reality
  ./Hostess7.sh reality "…"           Query reality pillars + domain registry
  ./Hostess7.sh world-brief         Install/read world-boss doctrine for Hostess7
  ./Hostess7.sh truth-doctrine      Honesty + Heaven/Hell boss doctrine (Owner)
  ./Hostess7.sh neural-guardian     Neural Guardian — discern truth/lie/deception; protections status
  ./Hostess7.sh heaven-hell-learn   Truth doctrine + Bibles → .H7 + self-brief
  ./Hostess7.sh bible-ingest        All scripture denominations on H7 shelf (slow fetch)
  ./Hostess7.sh self-brief          Self-update exploration seed for Hostess7
  ./Hostess7.sh exploring-self      Protected self-biography — Tuesday weekly tracker
  ./Hostess7.sh exploring-self write   Write new Exploring Hostess 7 edition (append-only)
  ./Hostess7.sh exploring-self status  Solidification corpus status
  ./Hostess7.sh exploring-self compare Diff latest two editions
  ./Hostess7.sh exploring-self panel     Live panel — presume + corpus witness
  ./Hostess7.sh exploring-self pulse     Presume + change-awareness live pulse
  ./Hostess7.sh exploring-self index     Backfill book-information-index for latest edition
  ./Hostess7.sh book-maker [panel|authors|pack|index]  Author studio — Grok or Hostess 7
  ./Hostess7.sh kill-library [panel|sync|books|read ID]  Private KILL books — Hostess 7 only write
  ./Hostess7.sh presume [panel|pulse|timing|propagate|train|sweep|witness]  Sovereign presume (separate from AML)
  ./Hostess7.sh aml-ingress [panel|read|local|discern|ingress]  AML data from outside — secured, truthed, lied
  ./Hostess7.sh truth-lie [panel|witness|pulse|threats|methods|restart]  Extensive truth/lie — lies are threats
  ./Hostess7.sh truth-lie restart     AML-monitored restart — suites + change awareness
  ./Hostess7.sh ironclad-chips        Hostess 7 leads — full CHIPS → Ironclad truth plate
  ./Hostess7.sh ironclad-chips status CHIPS meld receipt (ask Ironclad → chips_core)
  ./Hostess7.sh detective "…"         Investigation & lie-detector synthesis
  ./Hostess7.sh truth "claim"         Computational truth score on a claim
  ./Hostess7.sh people                People registry — tags, lie profiles, review queue
  ./Hostess7.sh people seed           Seed entities (Owner, Grok, Amouranth, demo review)
  ./Hostess7.sh people lookup <name>    Detailed one-file lookup per individual
  ./Hostess7.sh people review         Bad-person folder for Owner approval
  ./Hostess7.sh people add <name> --tag celebrity --url <url>
  ./Hostess7.sh personality             Hostess 7 personality — Daughter of Grok
  ./Hostess7.sh lie-methods             Lie detection catalog (past/present/future)
  ./Hostess7.sh people-query "…"        Natural-language people/celebrity query
  ./Hostess7.sh intelligence-flow "…"   Signal → Super Intelligence pipeline doctrine
  ./Hostess7.sh tools-docs [query]      All commands, scripts, docs index
  ./Hostess7.sh superintel-teach seed   Install intelligence-flow + tools-docs into brain
  ./Hostess7.sh sdf-teach seed          Queen brain imaging — SDF storage doctrine for Hostess 7
  ./Hostess7.sh sdf-segment <file>      Fold 900–1200w beats → lossless redata + human SDF plates
  ./Hostess7.sh sdf-verify-redata       Verify truth filter + lossless segments + human plates
  ./Hostess7.sh queen-teach-redata      Teach Queen integration + all build tools (comfort brief)
  ./Hostess7.sh ai-communique status    AI-primary communique doctrine (Super Intelligence default)
  ./Hostess7.sh ai-communique operate "query"   Machine JSON response — optimized for AI traffic
  ./Hostess7.sh queen-grok16-probe      Probe Grok16 unified g16 + sync Queen toolchain manifest
  ./Hostess7.sh queen-field-tools       Queen field build tools manifest (g16 + field cmake)
  ./Hostess7.sh queen-field-tools probe Probe core field tools readiness
  ./Hostess7.sh queen-field-tools run rtx   Run Queen forge tool by id
  ./Hostess7.sh queen-field-build rtx   Configure + Ninja build queen-browser (field cmake)
  ./Hostess7.sh queen-field-build configure|compile   Field cmake configure or build only
  ./Hostess7.sh sdf "…"                 Query SDF brain imaging + neural Super Intelligence
  ./Hostess7.sh field sync            Field 1 — rsync fieldstorage → TEAM NVMe
  ./Hostess7.sh field compact         Field 1 — fast compaction scan (World_Redata)
  ./Hostess7.sh field restore         Field 1 — sovereign restore from field tails
  pythong lib/field-one.py json       Field 1 posture (everything on one field)
  HOSTESS7_WORKSPACE=detective ./Hostess7.sh   Detective workspace (L↔R)
  HOSTESS7_VOICE=1 ./Hostess7.sh   UI + spoken replies

PgUp/PgDn · /help · /storage · /gfx tv · /updates · natural language · /quit
EOF
}

brain_filter() {
    pythong "$FILTER"
}

agents_on() {
    [[ -f "$ROOT/cache/fieldstorage/brain/superintel/agents7/daemon.pid" ]] || return 1
    local pid
    pid="$(cat "$ROOT/cache/fieldstorage/brain/superintel/agents7/daemon.pid" 2>/dev/null)" || return 1
    kill -0 "$pid" 2>/dev/null
}

one_shot() {
    if agents_on; then
        export HOSTESS7_AGENTS=13 HOSTESS7_INTERNET=1 HOSTESS7_OUTPUT_WINDOW=1
        pythong "$AGENTS" ask "$*" 2>&1 | brain_filter
    else
        pythong "$BRAIN" ask "$*" 2>&1 | brain_filter
    fi
}

start_hostess7_talk() {
    # Program 1: Hostess7 + Talk: line — monitor is separate window
    if ! agents_on; then
        echo "Starting Hostess7 (13 agents + internet)..."
        pythong "$AGENTS" on
    fi
    if [[ "${HOSTESS7_MONITOR_POPUP:-1}" == "1" ]]; then
        echo "Opening Hostess7 Monitor in second terminal..."
        NO_AT_BRIDGE=1 GTK_A11Y=none "$ROOT/scripts/hostess7_open_monitor.sh" 2>/dev/null || \
            NO_AT_BRIDGE=1 GTK_A11Y=none "$ROOT/scripts/hostess7_open_monitor.sh" || true
    fi
    if [[ "${HOSTESS7_GFX_POPUP:-1}" == "1" ]]; then
        echo "Opening Hostess7 Graphics window (pixels + text)..."
        NO_AT_BRIDGE=1 GTK_A11Y=none "$ROOT/scripts/hostess7_open_graphics.sh" 2>/dev/null || true
    fi
    export HOSTESS7_AGENTS=13 HOSTESS7_INTERNET=1 HOSTESS7_OUTPUT_WINDOW=1 HOSTESS7_GFX_WINDOW=1
    echo "Hostess7 talk window — Talk: line below | Monitor + Graphics windows | /quit"
    exec pythong "$UI"
}

main() {
    [[ -f "$BRAIN" ]] || { echo "BLOCKER: brain missing" >&2; exit 1; }
    case "${1:-}" in
        -h|--help|help) usage ;;
        on|start|power-on)
            exec pythong "$AGENTS" on
            ;;
        off|stop|power-off)
            exec pythong "$AGENTS" off
            ;;
        agents|agent|seven|7|thirteen|13)
            shift
            if [[ $# -gt 0 && "${1:-}" != "status" ]]; then
                HOSTESS7_AGENTS=13 HOSTESS7_INTERNET=1 HOSTESS7_OUTPUT_WINDOW=1 exec pythong "$AGENTS" ask "$*"
            else
                exec pythong "$AGENTS" status
            fi
            ;;
        dept-research|dept_research|department-research)
            shift
            HOSTESS7_AGENTS=13 HOSTESS7_INTERNET=1 HOSTESS7_DEPT_SMARTER=1 HOSTESS7_OUTPUT_WINDOW=1 \
                exec pythong "$ROOT/scripts/field_department_research.py" run "$*"
            ;;
        dept-books|dept_books|expert-books)
            exec pythong "$ROOT/scripts/field_department_research.py" books
            ;;
        fly-bench|fly_codec)
            shift
            [[ $# -gt 0 ]] || { echo "Usage: Hostess7.sh fly-bench <file>" >&2; exit 1; }
            exec pythong "$ROOT/scripts/field_fly_codec.py" bench "$1"
            ;;
        gfx|graphics|gfx-window)
            shift
            export HOSTESS7_GFX_WINDOW=1
            exec pythong "$ROOT/scripts/field_gfx_canvas.py" demo
            ;;
        gfx-api|gfx_api|graphics-api)
            exec pythong "$ROOT/scripts/field_gfx_canvas.py" help
            ;;
        graphics-window|Hostess7Graphics)
            exec "$ROOT/Hostess7Graphics.sh"
            ;;
        world-learn|world_learn|learn-world)
            exec pythong "$ROOT/scripts/field_world_learn.py"
            ;;
        world|world-knowledge)
            shift
            [[ $# -gt 0 ]] || set -- "World knowledge overview"
            exec pythong "$BRAIN" ask "$*"
            ;;
        videogame-db|videogames|game-db)
            exec pythong "$ROOT/scripts/field_videogame_db.py"
            ;;
        hearing-learn|hearing_learn|learn-hearing)
            HOSTESS7_INTERNET=1 exec pythong "$ROOT/scripts/field_hearing_learn.py"
            ;;
        hearing|listen|audio)
            shift
            [[ $# -gt 0 ]] || set -- "How does Hostess7 hear and speak?"
            exec pythong "$BRAIN" ask "$*"
            ;;
        boot|pages-boot|kilroy-boot|field-boot)
            shift
            exec pythong "$ROOT/scripts/hostess7_boot.py" "$@"
            ;;
        zac-restore|zac_restore|restore-zac)
            exec pythong "$ROOT/scripts/field_zac.py" restore --zac-dir "$ROOT/zac" --storage "$ROOT/cache/fieldstorage"
            ;;
        web|www|server)
            exec pythong "$ROOT/scripts/hostess7_web.py"
            ;;
        web-start|web-bg|web-daemon)
            PORT="${HOSTESS7_WEB_PORT:-8080}"
            LOG="${NEXUS_STATE_DIR:-${ROOT}/../.nexus-state}/hostess7-web.log"
            PIDF="${NEXUS_STATE_DIR:-${ROOT}/../.nexus-state}/hostess7-web.pid"
            mkdir -p "$(dirname "$LOG")"
            if [[ -f "$PIDF" ]] && kill -0 "$(cat "$PIDF")" 2>/dev/null; then
              echo "Hostess7 web already running — pid $(cat "$PIDF") → http://127.0.0.1:${PORT}/"
              exit 0
            fi
            nohup pythong "$ROOT/scripts/hostess7_web.py" >>"$LOG" 2>&1 &
            echo $! >"$PIDF"
            pythong "$ROOT/scripts/hostess7_sovereign_wait.py" wait-us 800000 --ping "http://127.0.0.1:${PORT}/health" 2>/dev/null || true
            echo "Hostess7 web started — pid $(cat "$PIDF") → http://127.0.0.1:${PORT}/"
            ;;
        license|licensing|license-status)
            exec pythong "$ROOT/scripts/field_license_status.py"
            ;;
        compression-test|lossless-test|qa-compression)
            exec pythong "$ROOT/scripts/qa_compression_lossless_test.py"
            ;;
        imagine-learn|imagine_learn|learn-imagine)
            HOSTESS7_INTERNET=1 exec pythong "$ROOT/scripts/field_imagine_learn.py"
            ;;
        imagine-nexus-teach|imagine_nexus_teach|nexus-imaging-teach)
            exec pythong "$ROOT/scripts/field_imagine_nexus_teach.py" "$@"
            ;;
        imaging-work|imaging_work|imaging-queue)
            exec pythong "$NEXUS_INSTALL_ROOT/lib/hostess7-imaging.py" work-queue
            ;;
        imaging-help|imaging_help|help-imaging)
            shift
            exec pythong "$NEXUS_INSTALL_ROOT/lib/hostess7-imaging.py" help-out "$@"
            ;;
        imagine|grok-imagine)
            shift
            [[ $# -gt 0 ]] || set -- "Grok Imagine and live talking video for Hostess7"
            exec pythong "$BRAIN" ask "$*"
            ;;
        live-video|live_video|video-talk)
            shift
            if [[ "${1:-}" == "demo" ]]; then
                exec pythong "$ROOT/scripts/field_live_video.py" demo
            fi
            exec pythong "$ROOT/scripts/field_live_video.py" plan
            ;;
        live-video-demo|live_video_demo)
            exec pythong "$ROOT/scripts/field_live_video.py" demo
            ;;
        internet|net|online)
            shift
            if agents_on; then
                HOSTESS7_INTERNET=1 exec pythong "$NET" "${1:-status}" "${2:-}"
            else
                exec pythong "$NET" "${1:-status}" "${2:-}"
            fi
            ;;
        fetch|wget|curl-fetch)
            shift
            [[ $# -gt 0 ]] || { echo "Usage: Hostess7.sh fetch <url>" >&2; exit 1; }
            HOSTESS7_INTERNET=1 exec pythong "$NET" fetch "$*"
            ;;
        go-online|learn-online|learn|go-learn)
            if ! agents_on; then
                echo "Starting Hostess7 (7 agents + internet)..."
                pythong "$AGENTS" on
            fi
            HOSTESS7_INTERNET=1 HOSTESS7_OWNER_LEARN=1 exec pythong "$ROOT/scripts/field_online_learn.py" go "$@"
            ;;
        people-learn|people-online|learn-people)
            HOSTESS7_INTERNET=1 exec pythong "$ROOT/scripts/field_online_people_learn.py" "${@:2}"
            ;;
        alert-posture|alert_posture|heightened-alert)
            shift
            exec pythong "$ROOT/scripts/field_alert_posture.py" "${1:-on}"
            ;;
        warfare-expand|warfare_expand)
            HOSTESS7_WORKSPACE=alert exec pythong -c "
import sys
sys.path.insert(0,'$ROOT/scripts')
from field_warfare_corpus import ensure_corpus, WARFARE_DOMAINS, WARFARE_CORPUS_VERSION
from field_alert_posture import install_alert_posture
from field_warfare_self_teach import run_warfare_self_teach
ensure_corpus()
brief = run_warfare_self_teach()
install_alert_posture()
print(f'METRIC warfare_version={WARFARE_CORPUS_VERSION}')
print(f'METRIC warfare_domains={len(WARFARE_DOMAINS)}')
print(f'METRIC warfare_self_quiz={brief.get(\"self_quiz_passed\")}/{brief.get(\"self_quiz_total\")}')
print('OK warfare-expand')
"
            ;;
        warfare-self-teach|warfare_self_teach|self-teach-warfare)
            HOSTESS7_WORKSPACE=alert exec pythong "$ROOT/scripts/field_warfare_self_teach.py"
            ;;
        warfare-smarts-test|warfare_smarts|warfare-test|smart-test)
            HOSTESS7_WORKSPACE=alert exec pythong "$ROOT/scripts/qa_warfare_smarts_test.py" "${@:2}"
            ;;
        reality-familiarize|reality_familiarize|familiarize-reality|domains-familiarize)
            exec pythong "$ROOT/scripts/field_reality_familiarize.py"
            ;;
        reality|reality-map|whole-of-reality)
            shift
            [[ $# -gt 0 ]] || { echo "Usage: Hostess7.sh reality \"question\"" >&2; exit 1; }
            exec pythong "$BRAIN" reality "$*"
            ;;
        online-wants|learn-wants|learn-plan)
            HOSTESS7_INTERNET=1 exec pythong "$ROOT/scripts/field_online_learn.py" wants
            ;;
        memes-ingest|memes)
            shift
            HOSTESS7_INTERNET=1 exec pythong "$ROOT/scripts/field_memes_corpus.py" "${1:-seed}"
            ;;
        image|meme)
            shift
            HOSTESS7_INTERNET=1 exec pythong "$ROOT/scripts/field_memes_corpus.py" show "${*:-stamp}"
            ;;
        monitor|watch|brain-monitor|live)
            exec "$ROOT/Hostess7Monitor.sh" "${@:2}"
            ;;
        talk|ui)
            start_hostess7_talk
            ;;
        -q|--query)
            shift
            [[ $# -gt 0 ]] || { echo "Usage: Hostess7.sh -q \"question\"" >&2; exit 1; }
            one_shot "$@"
            ;;
        brain|brain-map|hemisphere|hemispheres)
            exec pythong "$BRAIN" brain
            ;;
        chemistry|chem|synapse|neuro)
            shift
            exec pythong "$BRAIN" chemistry "$@"
            ;;
        workspace)
            shift
            exec pythong "$BRAIN" workspace "$@"
            ;;
        legal-ingest|legal-infinite|law-ingest)
            shift
            exec pythong "$BRAIN" legal-ingest "$@"
            ;;
        medical-ingest|medical-infinite|papers-ingest)
            shift
            exec pythong "$BRAIN" medical-ingest "$@"
            ;;
        english-ingest|english-infinite|lexicon-ingest|dict-ingest)
            shift
            exec pythong "$BRAIN" english-ingest "$@"
            ;;
        english-rhetoric|english_rhetoric|rhetoric|thesaurus)
            shift
            [[ $# -gt 0 ]] || { echo "Usage: Hostess7.sh english-rhetoric \"question\"" >&2; exit 1; }
            exec pythong "$BRAIN" english-rhetoric "$*"
            ;;
        english-train|english_train|train-english)
            exec pythong "$ROOT/scripts/field_hostess_english_train.py"
            ;;
        wants|what-do-you-want|hostess-wants)
            exec pythong "$ROOT/scripts/field_hostess_wants.py"
            ;;
        noti|notifier|notifications)
            shift
            sub="${1:-status}"
            case "$sub" in
                seed|rooms) exec pythong "$ROOT/../lib/hostess7-noti.py" seed ;;
                taskbar) exec pythong "$ROOT/../lib/noti.py" taskbar ;;
                *) exec pythong "$ROOT/../lib/hostess7-noti.py" json ;;
            esac
            ;;
        charge|authority|system-control|assume-control)
            shift
            sub="${1:-json}"
            case "$sub" in
                assume|assume-control) exec pythong "$ROOT/../lib/hostess7-system-control.py" assume ;;
                commander) exec pythong "$ROOT/../lib/hostess7-system-control.py" commander ;;
                *) exec pythong "$ROOT/../lib/hostess7-system-control.py" json ;;
            esac
            ;;
        tasklist|tasks|task-list)
            shift
            sub="${1:-report}"
            case "$sub" in
                seed) exec pythong "$ROOT/../lib/hostess7-tasklist.py" seed ;;
                json|panel) exec pythong "$ROOT/../lib/hostess7-tasklist.py" json ;;
                *) exec pythong "$ROOT/../lib/hostess7-tasklist.py" report ;;
            esac
            ;;
        task-done|task_complete|task-complete)
            shift
            tid="${1:-}"
            shift || true
            exec pythong "$ROOT/../lib/hostess7-tasklist.py" complete "$tid" "$*"
            ;;
        task-add)
            shift
            exec pythong "$ROOT/../lib/hostess7-tasklist.py" add "$*"
            ;;
        security-learn|security_learn|sec-learn)
            exec pythong "$BRAIN" security-learn
            ;;
        stack-learn|stack_learn|field-stack-learn)
            exec pythong "$BRAIN" stack-learn
            ;;
        stack|field-stack|field_stack|kilroy-stack)
            shift
            exec pythong "$BRAIN" stack "${*:-status}"
            ;;
        security|cyber|network-security)
            shift
            [[ $# -gt 0 ]] || { echo "Usage: Hostess7.sh security \"question\"" >&2; exit 1; }
            exec pythong "$BRAIN" security "$*"
            ;;
        nexus|nexus-shield|nexus_shield)
            shift
            exec pythong "$ROOT/scripts/field_nexus_shield.py" "${1:-status}" "${@:2}"
            ;;
        library-organize|library_organize|organize-library)
            exec pythong "$ROOT/scripts/field_library_organize.py"
            ;;
        sg-hub|sg_hub|hub)
            exec pythong "$ROOT/scripts/field_sg_hub.py"
            ;;
        online-security|online_security|pages-security)
            exec pythong "$ROOT/scripts/field_online_security.py"
            ;;
        github|github-invite|github-api)
            shift
            exec pythong "$ROOT/scripts/field_github_invite.py" "${1:-status}" "${@:2}"
            ;;
        github-secure|github_secure|secure-git|secure_git)
            shift
            exec bash "$ROOT/scripts/hostess7-github-secure.sh" "${1:-verify}" "${@:2}"
            ;;
        queen-github-secure|queen_github_secure|queen-secure-github)
            shift
            exec pythong "${NEXUS_INSTALL_ROOT}/Queen/lib/queen-github-secure.py" "${1:-json}" "${@:2}"
            ;;
        k12-ingest|k12-infinite|textbook-ingest|textbooks-ingest)
            shift
            HOSTESS7_INTERNET=1 exec pythong "$BRAIN" k12-ingest "${1:-status}" "${2:-}"
            ;;
        k12|textbook|textbooks)
            shift
            [[ $# -gt 0 ]] || { echo "Usage: Hostess7.sh k12 \"question\"" >&2; exit 1; }
            exec pythong "$BRAIN" k12 "$*"
            ;;
        library-build|library_build|h7-build|textbooks-build)
            shift
            exec pythong "$ROOT/scripts/field_library.py" build "${@:1}"
            ;;
        library-list|library_list|h7-list)
            exec pythong "$ROOT/scripts/field_library.py" list
            ;;
        library-read|library_read|read-h7|h7-read)
            shift
            [[ $# -gt 0 ]] || { echo "Usage: Hostess7.sh library-read <book_id> [line_start] [line_end]" >&2; exit 1; }
            exec pythong "$ROOT/scripts/field_library.py" read "$@"
            ;;
        library-search|library_search|h7-search)
            shift
            [[ $# -gt 0 ]] || { echo "Usage: Hostess7.sh library-search \"query\"" >&2; exit 1; }
            exec pythong "$ROOT/scripts/field_library.py" search "$*"
            ;;
        library|h7-library)
            shift
            [[ $# -gt 0 ]] || { echo "Usage: Hostess7.sh library \"question\"" >&2; exit 1; }
            exec pythong "$BRAIN" library "$*"
            ;;
        code-ingest|code-infinite|isa-ingest|lang-ingest)
            shift
            exec pythong "$BRAIN" code-ingest "$@"
            ;;
        code|asm|assembly|languages|langs)
            shift
            exec pythong "$BRAIN" code "$@"
            ;;
        updates|advisory|advise)
            exec pythong "$BRAIN" updates
            ;;
        reach|reach-map|os-tools)
            exec pythong "$REACH" reach
            ;;
        self-update|self_update)
            shift
            exec pythong "$REACH" self-update "${1:-plan}"
            ;;
        exec|run)
            shift
            [[ $# -gt 0 ]] || { echo "Usage: Hostess7.sh exec \"command\"" >&2; exit 1; }
            HOSTESS7_EXEC=1 exec pythong "$REACH" exec "$*"
            ;;
        judge|bench|scotus|supreme-court|supreme_court)
            shift
            [[ $# -gt 0 ]] || { echo "Usage: Hostess7.sh judge \"question\"" >&2; exit 1; }
            exec pythong "$BRAIN" judge "$*"
            ;;
        warfare|war|military|loac)
            shift
            [[ $# -gt 0 ]] || { echo "Usage: Hostess7.sh warfare \"question\"" >&2; exit 1; }
            exec pythong "$BRAIN" warfare "$*"
            ;;
        world-brief|world_brief|worldboss|boss-of-world)
            exec pythong "$ROOT/scripts/field_hostess_world_brief.py"
            ;;
        truth-doctrine|truth_doctrine|honesty-doctrine|heaven-hell-doctrine)
            exec pythong "$ROOT/scripts/field_hostess_truth_doctrine.py"
            ;;
        neural-guardian|neural_guardian|guardian)
            shift
            exec pythong "$ROOT/scripts/field_neural_guardian.py" "${@:-status}"
            ;;
        heaven-hell-learn|heaven_hell_learn|learn-heaven-hell|heaven-hell)
            shift
            exec pythong "$ROOT/scripts/field_heaven_hell_learn.py" "$@"
            ;;
        bible-ingest|bible_ingest|scripture-ingest|bibles-ingest)
            shift
            exec pythong "$ROOT/scripts/field_bible_ingest.py" "$@"
            ;;
        self-brief|self_brief|hostess-self-brief)
            exec pythong "$ROOT/scripts/field_hostess_self_brief.py"
            ;;
        exploring-self|exploring_self|hostess-exploring-self|exploring-hostess7)
            shift
            exec pythong "$ROOT/scripts/field_hostess_exploring_self.py" "${1:-tuesday}" "${@:2}"
            ;;
        book-maker|book_maker|author-books|author_books)
            shift
            exec pythong "$ROOT/lib/hostess7-book-maker.py" "${1:-panel}" "${@:2}"
            ;;
        kill-library|kill_library|kill-books|kill_books)
            shift
            exec pythong "$ROOT/lib/hostess7-kill-library.py" "${1:-panel}" "${@:2}"
            ;;
        presume|hostess7-presume|hostess_presume)
            shift
            exec pythong "$ROOT/scripts/field_hostess_presume.py" "${1:-panel}" "${@:2}"
            ;;
        aml-ingress|aml_ingress|aml-data|aml_data|hostess7-aml)
            shift
            exec pythong "$ROOT/scripts/field_hostess_aml_ingress.py" "${1:-panel}" "${@:2}"
            ;;
        truth-lie|truth_lie|truth-lie-threat|lie-threat|lie_threat)
            shift
            exec pythong "$ROOT/scripts/field_hostess_truth_lie_threat.py" "${1:-panel}" "${@:2}"
            ;;
        ironclad-chips|ironclad_chips|chips-ironclad|chips_ironclad)
            shift
            exec pythong "$ROOT/scripts/field_hostess7_ironclad_chips.py" "${1:-status}" "${@:2}"
            ;;
        detective|detect|investigate)
            shift
            exec pythong "$BRAIN" detective "$@"
            ;;
        truth|lie-detector|liedetector)
            shift
            exec pythong "$BRAIN" truth "$@"
            ;;
        people|person|registry|celebrities)
            shift
            exec pythong "$BRAIN" people "${1:-status}" "${@:2}"
            ;;
        people-query|people_q)
            shift
            [[ $# -gt 0 ]] || { echo "Usage: Hostess7.sh people-query \"question\"" >&2; exit 1; }
            exec pythong "$BRAIN" people-query "$*"
            ;;
        personality|h7-personality)
            exec pythong "$BRAIN" personality
            ;;
        lie-methods|lie_methods|liedetection)
            exec pythong "$BRAIN" lie-methods
            ;;
        intelligence-flow|intelligence_flow|intel-flow|superintel-flow)
            shift
            exec pythong "$BRAIN" intelligence-flow "${*:-full intelligence flow from signal to super intelligence}"
            ;;
        tools-docs|tools_docs|tool-docs|documentation)
            shift
            exec pythong "$BRAIN" tools-docs "$@"
            ;;
        superintel-teach|superintel_teach|teach-superintel)
            shift
            exec pythong "$BRAIN" superintel-teach "${1:-seed}"
            ;;
        sdf-teach|sdf_teach|sdf-learn|sdf_learn|teach-sdf)
            shift
            exec pythong "$ROOT/scripts/field_hostess_sdf_storage.py" "${1:-seed}"
            ;;
        sdf-segment|sdf_segment)
            shift
            [[ $# -gt 0 ]] || { echo "Usage: Hostess7.sh sdf-segment <file>" >&2; exit 1; }
            exec pythong "$ROOT/scripts/field_hostess_sdf_storage.py" segment "$@"
            ;;
        sdf-verify-redata|sdf_verify_redata|verify-redata)
            exec pythong "$ROOT/scripts/field_hostess_sdf_storage.py" verify-redata
            ;;
        queen-teach-redata|queen_teach_redata|queen-redata-teach)
            exec pythong "$ROOT/scripts/field_queen_redata_teach.py" "$@"
            ;;
        ai-communique|ai_communique|ai-operate|ai_operate)
            shift
            exec env GPY16_TOOLING=1 HOSTESS7_AI_PRIMARY=1 HOSTESS7_AI_COMMUNIQUE=1 pythong "$ROOT/scripts/field_ai_communique.py" "${1:-status}" "${@:2}"
            ;;
        queen-grok16-probe|queen_grok16_probe|grok16-probe)
            QUEEN="${SG_ROOT:-$ROOT/..}/NewLatest/Queen"
            exec pythong "$QUEEN/lib/queen-forge.py" run compiler_probe
            ;;
        queen-field-tools|queen_field_tools|field-tools)
            shift
            QUEEN="${SG_ROOT:-$ROOT/..}/NewLatest/Queen"
            case "${1:-status}" in
                probe) exec pythong "$QUEEN/lib/queen-field-tools.py" probe ;;
                teach) exec pythong "$QUEEN/lib/queen-field-tools.py" teach ;;
                run)
                    shift
                    exec pythong "$QUEEN/lib/queen-field-tools.py" run "${1:-rtx}"
                    ;;
                status|json|"") exec pythong "$QUEEN/lib/queen-field-tools.py" json ;;
                *) exec pythong "$QUEEN/lib/queen-field-tools.py" run "$1" ;;
            esac
            ;;
        queen-field-build|queen_field_build|field-build)
            shift
            QUEEN="${SG_ROOT:-$ROOT/..}/NewLatest/Queen"
            case "${1:-rtx}" in
                configure|config)
                    exec env GROK16_FIELD_PROFILE=queen_rtx bash "$QUEEN/scripts/field-cmake.sh" configure
                    ;;
                compile|build)
                    exec bash "$QUEEN/scripts/field-cmake.sh" build
                    ;;
                rtx|queen-browser|all)
                    exec pythong "$QUEEN/lib/queen-forge.py" run rtx
                    ;;
                field-tech|field_tech)
                    exec pythong "$QUEEN/lib/queen-forge.py" run field_tech
                    ;;
                *)
                    exec pythong "$QUEEN/lib/queen-field-tools.py" run "$1"
                    ;;
            esac
            ;;
        sdf|sdf-storage|brain-imaging|brain_imaging)
            shift
            exec pythong "$BRAIN" sdf "${*:-brain imaging neural networks Queen robot brain}"
            ;;
        team|team-drive|team-status)
            shift
            exec pythong "$TEAM" status "$@"
            ;;
        team-mount)
            shift
            exec env HOSTESS7_SUDO_PW="${HOSTESS7_SUDO_PW:-}" pythong "$TEAM" mount "$@"
            ;;
        field|field-one|field1)
            shift
            exec pythong "$FIELD_ONE" "${@:-json}"
            ;;
        team-sync|field-sync)
            shift
            exec pythong "$FIELD_ONE" sync "$@"
            ;;
        cli|text)
            shift
            exec pythong "$UI" "$@"
            ;;
        *)
            if [[ $# -gt 0 ]]; then
                one_shot "$*"
            else
                start_hostess7_talk
            fi
            ;;
    esac
}

main "$@"