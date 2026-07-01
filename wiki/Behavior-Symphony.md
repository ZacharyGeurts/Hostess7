# Behavior Symphony

Process behavior scoring loop — syscall patterns, churn paths, alert thresholds.

- **Module:** `lib/behavior-symphony.sh`
- **Toggle:** `NEXUS_BEHAVIOR_WATCH=1`
- **State:** `$NEXUS_STATE_DIR/behavior/`
- **Threshold:** `NEXUS_BEHAVIOR_THRESHOLD_CALM` (default 50)

Adaptive poll: calm 3s · alert 2s · storm 1s.