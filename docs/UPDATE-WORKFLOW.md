# Update workflow — monorepo + publish lanes

How the NewLatest tree relates to sibling repos and `.pages-*` / `.senses-publish-*` gitlinks.

## Tree layout

| Lane | Path pattern | Purpose |
|------|----------------|---------|
| **Main stack** | `Hostess7/`, `Queen/`, `lib/`, `panel/` | Sovereign brain + AmmoOS + NEXUS |
| **Pages publish** | `.pages-hostess7-publish`, `.pages-ammoos-publish`, `.pages-hub-*` | gh-pages / GitHub.io mirrors |
| **Senses publish** | `.senses-publish-Final_Eye`, `Final_Ear`, `Final_Mouth` | Military EOL sense repos |
| **State (gitignored)** | `.nexus-state*`, `Hostess7/.pages-build-state/` | Runtime panels — never commit |

## Typical operator flow

```bash
# 1. Sync main tree
git pull origin main

# 2. Wire siblings (idempotent)
./lib/ammolang-run.sh exec script:scripts/wire-stack.sh

# 3. Health before changes
./status.sh

# 4. Boot / panel (portable)
./lib/ammolang-run.sh field_vm_boot
# or
./Hostess7/Hostess7.sh boot
```

## GitHub push lanes

When Charter/Spectrum flakes on `github.com:443` API, use lane probe + multi-push:

```bash
./scripts/github-lanes.sh probe          # SSH :22, tunnel :443, HTTPS, Pages CDN
./scripts/github-lanes.sh setup-remotes  # origin + origin-tunnel + origin-https
HOSTESS7_GIT_SKIP_API_TLS=1 ./scripts/github-lanes.sh verify
HOSTESS7_GIT_TUNNEL=tunnel ./scripts/github-lanes.sh push main
```

| Lane | Remote | When |
|------|--------|------|
| SSH direct | `git@github.com:…` | `:22` reachable |
| SSH tunnel | `ssh://git@ssh.github.com:443/…` | ISP blocks :22 |
| HTTPS token | `origin-https` | `GITHUB_TOKEN` set, API reachable |
| Secure git | `hostess7_secure_git.py push` | Tries all lanes in order |

## Pages publish (Hostess7 github.io)

Workflow: `.github/workflows/hostess7-pages.yml` (repo root — GitHub only runs root workflows).

```bash
./Hostess7/Hostess7.sh pages-build      # surfaces + API export → Hostess7/docs/
./Hostess7/Hostess7.sh pages-publish    # push gh-pages lane
```

CI skips sovereign brain build; exports sanitized API JSON only. War profile enforced in workflow.

## Senses publish (Eye · Ear · Mouth)

```bash
bash scripts/publish-senses-github.sh
```

Each sense repo is built from `.senses-publish-*` trees. Final_Eye uses Military EOL — not system tesseract.

## Gitlinks / submodules

If a publish tree is a submodule:

```bash
git submodule update --init --recursive
```

After updating a gitlink target, rebuild the publish artifact before tagging:

```bash
./Hostess7/Hostess7.sh pages-build
./lib/ammolang-run.sh exec script:tests/ammolang/snippets/hostess7_perf_smoke.sh
```

## Version bumps

1. Edit [VERSION.md](../VERSION.md) and `data/hostess7-platform-release.json`
2. Add CHANGELOG section (UI / Perf / Bug)
3. Add `Hostess7/RELEASE-<ver>.md` for product notes
4. Sync README one-liner to VERSION.md — no orphan `2.0.7h` strings

## Lite / profile (3.1.0+)

```bash
./Hostess7/Hostess7.sh profile        # baseline witness
./Hostess7/Hostess7.sh lite on        # opt-in throttle — NEXUS unchanged
./Hostess7/Hostess7.sh lite off       # restore full polling
```