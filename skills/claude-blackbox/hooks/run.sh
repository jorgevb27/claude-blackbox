#!/usr/bin/env sh
# claude-blackbox hook runner: picks a working Python 3 on Windows (Git Bash), macOS and Linux.
# Never fails the Claude session: exits 0 if no Python is found.
DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
for PY in python3 python py; do
  if command -v "$PY" >/dev/null 2>&1 && "$PY" -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" </dev/null >/dev/null 2>&1; then
    exec "$PY" "$DIR/../scripts/blackbox.py" "$@"
  fi
done
echo "claude-blackbox: Python 3.8+ not found, event not recorded" >&2
exit 0
