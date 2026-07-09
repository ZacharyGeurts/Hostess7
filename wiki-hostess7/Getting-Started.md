# Getting Started

## Quick install (Linux x86_64)

From release assets — H7e archive:

```bash
./scripts/field-h7e-extract.sh hostess7-1.0.0-beta-source.h7e
cd hostess7-1.0.0-beta
./scripts/wire-stack.sh
sudo ./install-all.sh
./Hostess7/Hostess7.sh on
```

`wire-stack.sh` materializes stack siblings (AmmoOS, Grok16, Queen Browser, KILROY, ZNetwork) into one tree.

---

## Turn ON

```bash
./Hostess7/Hostess7.sh on
```

This starts Prime + twelve World Experts, opens the internet gate when mandated, and prepares counsel fusion.

---

## Surfaces after install

| Surface | How to reach |
|---------|--------------|
| Talk UI (default) | `./Hostess7/Hostess7.sh` or `./Hostess7/Hostess7.sh talk` |
| One-shot query | `./Hostess7/Hostess7.sh -q "your question"` |
| Brain map | `./Hostess7/Hostess7.sh brain` |
| Field desktop | http://127.0.0.1:9477/field |
| Queen Browser | http://127.0.0.1:9481/world/browser.html |
| Training | http://127.0.0.1:9477/command#training |

---

## Workspace bias

Field development workspace (left-biased):

```bash
HOSTESS7_WORKSPACE=field ./Hostess7/Hostess7.sh
```

---

## Train before update

Full training runs before release pack/push:

```bash
./lib/ammolang-run.sh hostess7_train_before_update
```

See **[Training Campus](Training-Campus)**.

---

## Software updates

Official catalog: **[H7 Updater](H7-Updater)** — https://zacharygeurts.github.io/H7updater/

- **Sovereign lane:** reads ZacharyGeurts stack manifest (no login).
- **Personal lane:** authorize your GitHub read-only to browse your repos the same way.
- **Local apply:** `/ammoos-update-os` after install.

---

## GitHub Pages (demo only)

Public hub: https://zacharygeurts.github.io/Hostess7/

Demo mode — no full brain, no secrets. Extract and run locally or in Codespaces for counsel and NEXUS panel.