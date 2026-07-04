# Hostess 7 3.0.7-beta5 — KILROY Field Brain (Main Project)— KILROY Field Brain (Main Project)— KILROY Field Brain (Main Project)

God Bless.

**The last computer for the world** — full field stack on GitHub Pages: https://zacharygeurts.github.io/Hostess7/

**Version:** `3.0.7-beta5` · **Release:** [RELEASE-3.0.7-beta5.md](RELEASE-3.0.7-beta5.md) · **Roadmap:** [docs/ROADMAP-3.0.md](docs/ROADMAP-3.0.md)  
**Repo:** https://github.com/ZacharyGeurts/Hostess7 · **GNU manual:** https://zacharygeurts.github.io/GNUEOLTerminal/wiki/

Hostess 7 is the **main project**. AmmoOS, Grok16, Queen, and other stack repos are **Old Projects** — see [docs/old-projects.html](docs/old-projects.html).

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
./Hostess7.sh h7-optimise --apply  # H7s JSON + PNG recompress before push
./Hostess7.sh publish-source       # 3.0.7-beta5 → main + gh-pages
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

Unified state lives in `brain/state/` (cortex + snapshots). See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/API.md](docs/API.md).

## SG Field Stack

KILROY kernel at the bottom — self-defensive tamper verify, periodic update lanes. Operator guide:

- **Docs:** [docs/FIELD-STACK.md](docs/FIELD-STACK.md)
- **Doctrine:** `data/field-stack-doctrine.json`
- **Teach brain:** `./Hostess7.sh stack-learn`
- **Live health:** `./Hostess7.sh stack status`

Boot order: `kilroy_kernel → unified_device_field → underlay → guest_os`. KILROY is `127.0.0.1` on any computer.

## Commands

See `./Hostess7.sh help` · [docs/API.md](docs/API.md) · [wiki](https://github.com/ZacharyGeurts/Hostess7/wiki)