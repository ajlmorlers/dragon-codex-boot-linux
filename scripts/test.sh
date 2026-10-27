#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
python3 -m py_compile dragon_codex_boot/launcher.py tests/test_config.py
PYTHONPATH="$ROOT" python3 -m unittest discover -s tests -v
if [ -f media/startup.mp4 ]; then
    ./run.sh --verify
else
    printf 'WARNING: media/startup.mp4 is missing; skipping media verification.\n' >&2
fi
