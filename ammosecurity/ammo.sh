#!/usr/bin/env bash
# legacy wrapper → sg_build.sh
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/sg_build.sh" "$@"