# Shadow Reality

Inotify watcher on `lib/`, `panel/`, and critical config — detects tamper without polling entire disk.

- **Module:** `lib/shadow-reality.sh`
- **Toggle:** `NEXUS_SHADOW_WATCH=1`
- **State:** `$NEXUS_STATE_DIR/shadow/`

Pairs with [Self-Defense](Self-Defense) manifest verify on daemon start.