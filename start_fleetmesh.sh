#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
if command -v python3 >/dev/null 2>&1; then
    exec python3 start.py --open "$@"
fi
printf '%s\n' 'Python 3.10 or newer is required. Install Python and run this launcher again.'
exit 1
