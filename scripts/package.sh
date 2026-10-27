#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
VERSION=$(tr -d '[:space:]' < "$ROOT/VERSION")
OUT_DIR="$ROOT/dist"
NAME="dragon-codex-boot-linux-$VERSION"
ARCHIVE="$OUT_DIR/$NAME.tar.gz"
mkdir -p "$OUT_DIR"
tar -C "$(dirname -- "$ROOT")" \
    --exclude='dragon-codex-boot-linux/python-packages' \
    --exclude='dragon-codex-boot-linux/venv' \
    --exclude='dragon-codex-boot-linux/config/launcher.json' \
    --exclude='dragon-codex-boot-linux/dist' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    -czf "$ARCHIVE" "$(basename -- "$ROOT")"
sha256sum "$ARCHIVE" > "$ARCHIVE.sha256"
printf 'Created %s\n' "$ARCHIVE"
printf 'Created %s\n' "$ARCHIVE.sha256"
