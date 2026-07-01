# Find the Grok AI Lab

Bootable **AmmoOS desktop** — Final Eye OCR brain, kill-list revalidation, RE-KILL at boot.

## Quick open (browser)

| Surface | URL |
|---------|-----|
| **Grok AI Lab desktop** | http://127.0.0.1:9477/grok-lab |
| **AmmoOS field desktop** | http://127.0.0.1:9477/field → **Grok AI Lab** icon |
| **Final Eye** | http://127.0.0.1:9479/ops |
| **Queen World** | http://127.0.0.1:9481/world/ |

Home is always **127.0.0.1** — sanctuary inside.

## Install / boot (one command)

From the NewLatest tree:

```bash
cd NewLatest
bash GrokLab/scripts/grok-lab-boot-desktop.sh
```

Mint / production boot-ready (systemd + F9, GRUB untouched):

```bash
sudo bash scripts/field-mint-boot-ready.sh
bash GrokLab/scripts/grok-lab-boot-desktop.sh
```

Full field stack (panel + Queen + lab):

```bash
bash scripts/start-field-stack.sh
```

## CLI

```bash
bash GrokLab/scripts/grok-lab-run.sh boot      # RE-KILL + seal
bash GrokLab/scripts/grok-lab-run.sh battery   # protection tests
bash GrokLab/scripts/grok-lab-run.sh status
bash GrokLab/scripts/grok-lab-run.sh live 3
```

## Paths

| Item | Location |
|------|----------|
| Lab root | `NewLatest/GrokLab/` |
| Engine | `NewLatest/lib/grok-ai-lab.py` |
| Desktop API | `NewLatest/lib/grok-lab-desktop.py` |
| Panel UI | `NewLatest/panel/grok-lab.html` |
| State | `.nexus-state/` or `GrokLab/.lab-state/` |
| Boot marker | `.nexus-state/grok-lab-boot-desktop.json` |

## Repo

Ships with **AmmoOS** / **NEXUS-Shield** stack: KILROY + Final Eye + Hostess7 + field attack kit.

War posture: **the world is our defensive perimeter** — coexist, eliminate threats, kill evil. A new internet from every home; sanctuary at 127.0.0.1; stack corroboration only.

## Share

X compose draft (mentions @X @xAI @grok): open `GrokLab/post-x-intent.url` or copy from `GrokLab/post-x-grok-lab.txt`.