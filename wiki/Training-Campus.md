# Training Campus

Hostess 7 trains **fully** before stack update. No `--fast` shortcuts on the release path.

---

## Release train route

```bash
./lib/ammolang-run.sh hostess7_train_before_update
```

Orchestrates:

- Full curriculum assessment
- Brain campus wiring
- Training floor / room / chamber completion
- Doctrine tracks (hands, H7B pack, omnibus when enabled)
- Progress ledger at `.nexus-state/hostess7-full-train-progress.json`

Then release:

```bash
./lib/ammolang-run.sh hostess7_release
```

Train → pack → publish (AML boundary on).

---

## Manual training CLI

```bash
./Hostess7.sh english-train          # rhetoric + grammar + interpersonal
./Hostess7.sh security-learn         # network + NEXUS corpus
./Hostess7.sh imagine-nexus-teach    # imaging fabric into corpus
```

Training panel (browser):

http://127.0.0.1:9477/command#training

API bundle:

```bash
curl -s http://127.0.0.1:9477/api/hostess7/training/bundle | jq .
```

---

## English fluency (priority #1)

Hostess 7 wants warm, fluent English — contractions, conjunctions, gerunds, strong verbs, concrete nouns, interpersonal turn-taking:

```bash
./Hostess7.sh english-rhetoric "contractions"
./Hostess7.sh english-rhetoric "interpersonal flow"
```

---

## Monitor progress

```bash
tail -f .nexus-state/hostess7-full-train-progress.json
tail -f .nexus-state/hostess7-release-progress.json
```