# Contributing

Business. No bullshit.

## Rules

1. **AML-only paths** — stack boot, wire, and install go through `./lib/ammolang-run.sh`. No `AML_BUILD=0` bypass in production paths.
2. **War profile** — `HOSTESS7_LICENSE_MODE=war` and NEXUS-Shield defaults stay on unless an explicit operator doc says otherwise.
3. **Version source of truth** — [VERSION.md](VERSION.md). README/INSTALL point there; do not hard-code stale version strings.
4. **State isolation** — use `.nexus-state` or `NEXUS_STATE_DIR`; never commit runtime JSON churn.
5. **Test before wire** — run CI-equivalent checks locally:

```bash
./lib/ammolang-run.sh exec script:scripts/check-deps.sh
bash tests/ammolang/snippets/hostess7_perf_smoke.sh
./status.sh
./bin/nexus verify
```

6. **Publish lanes** — pages and senses use separate publish trees; see [docs/UPDATE-WORKFLOW.md](docs/UPDATE-WORKFLOW.md).

## Pull requests

- Keep diffs focused.
- Shellcheck + `python3 -m py_compile` on touched paths.
- No secrets in tree — GitHub secret scanning is enabled; grep CI also flags obvious token patterns.

## Releases

- Product bumps: update VERSION.md, `data/hostess7-platform-release.json`, CHANGELOG section, `Hostess7/RELEASE-*.md`.
- Tag only after local `./Hostess7/Hostess7.sh profile` + `./status.sh` pass.