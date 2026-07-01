#!/usr/bin/env bash
# sg_no_bullshit — desktop + services clean, no extra security stack
set -euo pipefail
M="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

bash "$M/sg_service_cleaner.sh"
bash "$M/sg_grok_world.sh" all