# Hostess 7 — KILROY Field Brain

**GitHub Pages:** https://zacharygeurts.github.io/Hostess7/  
**Repo:** https://github.com/ZacharyGeurts/Hostess7

Full Hostess 7 — war-ready, never demo. Sovereign brain, KILROY field stack, alert posture. Everything to boot lives in this repo.

## Boot (real brain)

```bash
git clone https://github.com/ZacharyGeurts/Hostess7.git
cd Hostess7
pip install -r requirements.txt
./Hostess7.sh boot          # zac-restore · stack-learn · on · web-start
```

Open http://127.0.0.1:8080/ — same UI as GitHub Pages, with live `/api/ask` and `/api/status`.

**Codespaces (one-click boot):** https://github.com/codespaces/new?repo=ZacharyGeurts/Hostess7  
The devcontainer runs `./Hostess7.sh boot` on start and forwards port 8080.

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