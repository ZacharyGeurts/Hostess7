# Hostess 7 — KILROY Field Brain

**GitHub Pages (full package):** https://zacharygeurts.github.io/Hostess7/  
**Repo:** https://github.com/ZacharyGeurts/Hostess7

Full Hostess 7 on **github.io** via the **GitHub brain** — an isolated read-only mirror (same doctrine/corpus, public chat never touches `cache/fieldstorage/brain` or `brain/state`). Sovereign brain runs on loopback after `./Hostess7.sh boot`.

## Boot (real brain)

```bash
git clone https://github.com/ZacharyGeurts/Hostess7.git
cd Hostess7
pip install -r requirements.txt
./Hostess7.sh boot          # zac-restore · stack-learn · on · web-start
```

Open http://127.0.0.1:8080/ for live agents + KILROY + Queen. GitHub Pages runs the full exported package; loopback upgrades automatically when you boot locally.

```bash
./Hostess7.sh github-brain build   # mirror sovereign → docs/github-brain (read-only)
./Hostess7.sh pages-build          # github-brain + API export → docs/
./Hostess7.sh pages-publish        # push to gh-pages
```

**Codespaces (one-click boot):** https://github.com/codespaces/new?repo=ZacharyGeurts/Hostess7  
The devcontainer runs `./Hostess7.sh boot` on start and forwards port 8080.

## Embed (drop-in sovereign brain)

```bash
pip install -e .
./Hostess7.sh embed              # user systemd + boot + daemon
./Hostess7.sh core status        # unified supervisor JSON
./Hostess7.sh cohesion           # IQ + truth score
curl -s http://127.0.0.1:8080/api/brain | python -m json.tool
```

**Docker:**

```bash
docker compose up -d --build
docker compose logs -f
```

**Tarball:**

```bash
./Hostess7.sh embed pack
# → dist/hostess7-1.0.7h-embed.tar.gz
tar -xzf dist/hostess7-1.0.7h-embed.tar.gz && cd hostess7-1.0.7h-embed
bash scripts/install-hostess7-embed.sh
```

Unified state lives in `brain/state/` (cortex + snapshots). See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/API.md](docs/API.md).

## SG Field Stack

KILROY kernel at the bottom — self-defensive tamper verify, periodic update lanes. Operator guide:

- **Docs:** [docs/FIELD-STACK.md](docs/FIELD-STACK.md)
- **Doctrine:** `data/field-stack-doctrine.json`
- **Teach brain:** `./Hostess7.sh stack-learn`
- **Live health:** `./Hostess7.sh stack status`

Boot order: `kilroy_kernel → unified_device_field → underlay → guest_os`. KILROY is `127.0.0.1` on any computer.

## Commands

```bash
./Hostess7.sh boot              # full boot — brain + web
./Hostess7.sh web               # foreground web UI
./Hostess7.sh stack status      # KILROY / panel / Queen health
./Hostess7.sh stack-learn       # install field stack corpus
./Hostess7.sh                   # talk window (terminal + gfx)
```

**License:** GPL v3 or 3% commercial (gzac5314@gmail.com)