# SG Workspace — Code Bug Report

**Generated:** 2026-06-27T07:30:40Z
**Ironclad:** GREEN · sealed=True · truth%=100.0

## Executive summary

- **Areas scanned:** 9
- **Files scanned:** 227
- **Actionable findings:** 5
- **Truth-confirmed bugs:** 0
- **Truth suspects (noise):** 322
- **C++ exec() false positives:** 10
- **Patterns:** {'eval_exec': 3, 'shell_true': 2}

## Scan matrix

| Area | Files | Heuristics | Actionable | Rate |
|------|-------|------------|------------|------|
| `GIMP-Field/lib` | 1 | 2 | 0 | 1622.2 |
| `Grok16/forge` | 17 | 1 | 0 | 1703.0 |
| `Grok16/lib` | 48 | 1 | 0 | 1422.9 |
| `Grok16/python` | 14 | 3 | 3 | 1685.7 |
| `KeePass-Field` | 2 | 0 | 0 | 1177.9 |
| `NewLatest/Queen/lib` | 48 | 45 | 0 | 2079.1 |
| `NewLatest/lib` | 48 | 15 | 0 | 1314.2 |
| `NewLatest/lib/field-wave-engine.py` | 1 | 2 | 2 | 1643.0 |
| `OBS-Field` | 48 | 28 | 10 | 2044.2 |

## Findings

### FIND-001 — eval_exec (high) · disposition: **by design**

- **File:** `Grok16/python/driver/gpy16_driver.py` · line **95**
- **Code:** `exec(compile(sys.stdin.read(), "<gpy-16>", "exec"), {"__name__": "__main__"})`
- **Note:** GPY-16 driver / GrokVM interpreter entry — expected `exec` of compiled field Python, not arbitrary user eval.

### FIND-002 — eval_exec (high) · disposition: **by design**

- **File:** `Grok16/python/driver/gpy16_driver.py` · line **101**
- **Code:** `exec(compile(code, "<gpy-16>", "exec"), {"__name__": "__main__"})`
- **Note:** Same — `-c` / tooling lane for built-in interpreter.

### FIND-003 — eval_exec (high) · disposition: **by design**

- **File:** `Grok16/python/driver/gpy16_driver.py` · line **208**
- **Code:** `exec(compile(source, "<gpy-16>", "exec"), {"__name__": "__main__"})`
- **Note:** GrokVM hot-path execution — keep; whitelist in bugfinder next pass.

### FIND-004 — shell_true (high) · disposition: **review**

- **File:** `NewLatest/lib/field-wave-engine.py` · line **327**
- **Code:** `proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=seconds + 12)`
- **Fix:** Audit `cmd` construction; prefer argv list without `shell=True` if any segment is operator-controlled.

### FIND-005 — shell_true (high) · disposition: **review**

- **File:** `NewLatest/lib/field-wave-engine.py` · line **378**
- **Code:** `proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)`
- **Fix:** Same as FIND-004 — highest-priority real security review item in this scan.

## False positives (do not fix)

- **10** C++ `QDialog::exec()` hits in OBS upstream
- **322** truth-suspect rows from security docstrings vs unrelated KB

## Artifacts

- JSON: `NewLatest/data/field-code-bugfinder-report.json`
- Scan cache: `NewLatest/data/bugfinder-scan-cache/`
- Re-run: `pythong NewLatest/lib/field-code-bugfinder.py scan <path>`
