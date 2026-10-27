#!/bin/sh
set -eu
SELF=$(readlink -f -- "$0")
ROOT=$(dirname -- "$SELF")
if [ -d "$ROOT/python-packages" ]; then
    PYTHONPATH="$ROOT/python-packages${PYTHONPATH:+:$PYTHONPATH}"
    export PYTHONPATH
fi
exec python3 "$ROOT/dragon_codex_boot/launcher.py" "$@"
