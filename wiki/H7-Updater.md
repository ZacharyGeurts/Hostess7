# H7 Updater

**[→ GitHub: ZacharyGeurts/H7updater](https://github.com/ZacharyGeurts/H7updater)** · **[Pages](https://zacharygeurts.github.io/H7updater/)**

Layer 0 **Archival Warehouse** — official software update catalog for the field stack.

---

## Sovereign vs personal

| Lane | Who | Write access |
|------|-----|--------------|
| **Sovereign** | Everyone reads `ZacharyGeurts/*` manifest | Only **ZacharyGeurts** pushes to sovereign repos |
| **Personal** | You authorize GitHub (read-only device flow) | Your repos only — never ZacharyGeurts |

---

## Alphabetized stack folders

```
stack/{LETTER}/{RepoName}/
```

- **LETTER** = first character of repo name (A–Z, else `#`)
- **layer_z** = stack depth (−4 Hostess7 brain → 0 warehouse → 3 satellites)

Manifest: `data/h7updater-stack-index.json` in the H7updater repo.

---

## Surfaces

| Surface | URL |
|---------|-----|
| H7updater Pages | https://zacharygeurts.github.io/H7updater/ |
| Archival Warehouse (Layer 0) | `/ammoos-warehouse` or Hostess7 Pages `/h7updater/` |
| Local apply | `/ammoos-update-os` — Software Update Manager |

---

## Connect your GitHub (read-only)

1. Create a [GitHub OAuth App](https://github.com/settings/applications/new) with **Device flow** enabled.
2. Scopes: `read:user`, `repo:read` only.
3. Open H7updater Pages → **Your GitHub** → paste Client ID → **Authorize**.

Updates you apply locally use **your** repos. The sovereign catalog stays ZacharyGeurts-only.

---

## Rebuild manifest (operator)

```bash
python3 H7updater/scripts/build-stack-index.py
bash scripts/publish-h7updater-github.sh
```

See also **[Getting Started](Getting-Started)** and **[Old Projects (Stack Siblings)](Stack-Siblings)**.