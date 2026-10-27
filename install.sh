#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
DATA_HOME=${XDG_DATA_HOME:-"$HOME/.local/share"}
CONFIG_HOME=${XDG_CONFIG_HOME:-"$HOME/.config"}
BIN_DIR=${DRAGON_CODEX_BIN_DIR:-"$HOME/.local/bin"}
INSTALL_DIR=${DRAGON_CODEX_HOME:-"$DATA_HOME/dragon-codex-boot"}
CONFIG_DIR="$CONFIG_HOME/dragon-codex-boot"
CONFIG_FILE="$CONFIG_DIR/config.json"
APPLICATIONS_DIR="$DATA_HOME/applications"
LEGACY_ICON="$DATA_HOME/icons/hicolor/scalable/apps/dragon-codex-boot.svg"
DESKTOP_FILE="$APPLICATIONS_DIR/dragon-codex-boot.desktop"
WRAPPER="$BIN_DIR/dragon-codex-boot"

say() { printf '[Dragon Codex Boot] %s\n' "$*"; }
fail() { printf '[Dragon Codex Boot] ERROR: %s\n' "$*" >&2; exit 1; }

command -v python3 >/dev/null 2>&1 || fail "没有找到 Python 3。"
"$ROOT/run.sh" --version >/dev/null 2>&1 || true

if ! python3 - <<'PY' >/dev/null 2>&1
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
PY
then
    fail "缺少 GTK 3 Python 组件。请先安装：sudo apt install python3-gi gir1.2-gtk-3.0"
fi

if ! python3 -m pip --version >/dev/null 2>&1; then
    fail "缺少 pip。请先安装：sudo apt install python3-pip"
fi

if ! command -v paplay >/dev/null 2>&1 && ! command -v aplay >/dev/null 2>&1; then
    fail "缺少音频播放命令。请安装 pulseaudio-utils 或 alsa-utils。"
fi

[ -f "$ROOT/media/startup.mp4" ] || fail "缺少 media/startup.mp4，请下载带视频的完整源码包。"
[ -f "$ROOT/config/launcher.example.json" ] || fail "安装包不完整：缺少默认配置。"

mkdir -p "$INSTALL_DIR/dragon_codex_boot" "$INSTALL_DIR/config" "$INSTALL_DIR/media" \
    "$INSTALL_DIR/assets" "$INSTALL_DIR/python-packages" "$CONFIG_DIR" "$BIN_DIR" \
    "$APPLICATIONS_DIR"

install -m 644 "$ROOT/dragon_codex_boot/launcher.py" "$INSTALL_DIR/dragon_codex_boot/launcher.py"
install -m 644 "$ROOT/requirements.txt" "$INSTALL_DIR/requirements.txt"
install -m 644 "$ROOT/LICENSE" "$INSTALL_DIR/LICENSE"
install -m 644 "$ROOT/THIRD_PARTY_NOTICES.md" "$INSTALL_DIR/THIRD_PARTY_NOTICES.md"
install -m 644 "$ROOT/UPSTREAM.md" "$INSTALL_DIR/UPSTREAM.md"
install -m 644 "$ROOT/AUTHORS.md" "$INSTALL_DIR/AUTHORS.md"
install -m 644 "$ROOT/README.md" "$INSTALL_DIR/README.md"
install -m 644 "$ROOT/config/launcher.example.json" "$INSTALL_DIR/config/launcher.example.json"
install -m 644 "$ROOT/media/startup.mp4" "$INSTALL_DIR/media/startup.mp4"
install -m 644 "$ROOT/media/MEDIA_NOTICE.md" "$INSTALL_DIR/media/MEDIA_NOTICE.md"
install -m 755 "$ROOT/run.sh" "$INSTALL_DIR/run.sh"
install -m 755 "$ROOT/uninstall.sh" "$INSTALL_DIR/uninstall.sh"
install -m 644 "$ROOT/assets/dragon-codex-boot.svg" "$INSTALL_DIR/assets/dragon-codex-boot.svg"
install -m 644 "$ROOT/assets/preview.png" "$INSTALL_DIR/assets/preview.png"

if [ ! -f "$CONFIG_FILE" ]; then
    install -m 644 "$ROOT/config/launcher.example.json" "$CONFIG_FILE"
    say "已写入默认配置：$CONFIG_FILE"
else
    say "保留现有配置：$CONFIG_FILE"
fi

say "安装媒体依赖 PyAV 和 NumPy（仅写入程序目录）"
PIP_INDEX_ARGS=()
if [ -n "${DRAGON_CODEX_PIP_INDEX_URL:-}" ]; then
    PIP_INDEX_ARGS=(--index-url "$DRAGON_CODEX_PIP_INDEX_URL")
fi
python3 -m pip install --disable-pip-version-check --no-input --upgrade \
    --only-binary=:all: --target "$INSTALL_DIR/python-packages" \
    "${PIP_INDEX_ARGS[@]}" -r "$INSTALL_DIR/requirements.txt"

ln -sfn "$INSTALL_DIR/run.sh" "$WRAPPER"
if [ -e "$LEGACY_ICON" ]; then
    rm -f -- "$LEGACY_ICON"
fi

sed -e "s|@EXEC@|$WRAPPER|g" -e "s|@ICON@|chatgpt|g" \
    "$ROOT/assets/dragon-codex-boot.desktop.in" > "$DESKTOP_FILE"
chmod 644 "$DESKTOP_FILE"

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APPLICATIONS_DIR" >/dev/null 2>&1 || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q "$DATA_HOME/icons/hicolor" >/dev/null 2>&1 || true
fi

say "验证媒体和 ChatGPT 启动命令"
if ! DRAGON_CODEX_CONFIG="$CONFIG_FILE" "$WRAPPER" --verify; then
    fail "验证失败；请根据上方错误修正后重新运行安装脚本。"
fi

say "安装完成"
say "程序目录：$INSTALL_DIR"
say "配置文件：$CONFIG_FILE"
say "启动器命令：$WRAPPER"
say "也可以从应用菜单打开 Dragon Codex Boot。"
