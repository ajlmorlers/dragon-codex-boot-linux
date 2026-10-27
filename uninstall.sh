#!/usr/bin/env bash
set -euo pipefail

DATA_HOME=${XDG_DATA_HOME:-"$HOME/.local/share"}
CONFIG_HOME=${XDG_CONFIG_HOME:-"$HOME/.config"}
CACHE_HOME=${XDG_CACHE_HOME:-"$HOME/.cache"}
BIN_DIR=${DRAGON_CODEX_BIN_DIR:-"$HOME/.local/bin"}
INSTALL_DIR=${DRAGON_CODEX_HOME:-"$DATA_HOME/dragon-codex-boot"}
CONFIG_DIR="$CONFIG_HOME/dragon-codex-boot"
CACHE_DIR="$CACHE_HOME/dragon-codex-boot"
APPLICATIONS_DIR="$DATA_HOME/applications"
ICON_FILE="$DATA_HOME/icons/hicolor/scalable/apps/dragon-codex-boot.svg"
WRAPPER="$BIN_DIR/dragon-codex-boot"
PURGE=false

if [ "${1:-}" = "--purge" ]; then
    PURGE=true
fi

printf '[Dragon Codex Boot] 移除启动器文件\n'
if [ -L "$WRAPPER" ] || [ -f "$WRAPPER" ]; then
    rm -f -- "$WRAPPER"
fi
rm -f -- "$APPLICATIONS_DIR/dragon-codex-boot.desktop" "$ICON_FILE"
if [ -d "$INSTALL_DIR" ]; then
    rm -rf -- "$INSTALL_DIR"
fi

if [ "$PURGE" = true ]; then
    rm -rf -- "$CONFIG_DIR" "$CACHE_DIR"
    printf '[Dragon Codex Boot] 已同时删除配置和缓存。\n'
else
    printf '[Dragon Codex Boot] 配置已保留：%s\n' "$CONFIG_DIR/config.json"
    printf '[Dragon Codex Boot] 如需连同配置和缓存一起删除，请重新运行安装包中的 ./uninstall.sh --purge。\n'
fi

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APPLICATIONS_DIR" >/dev/null 2>&1 || true
fi
printf '[Dragon Codex Boot] 卸载完成。\n'
