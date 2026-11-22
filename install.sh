#!/usr/bin/env bash
# 把启动器装进应用菜单（不需要 root）
set -e
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APPS="$HOME/.local/share/applications"
mkdir -p "$APPS" "$HOME/.local/share/icons/hicolor/scalable/apps"
cp "$HERE/assets/roadrush.svg" "$HOME/.local/share/icons/hicolor/scalable/apps/roadrush-launcher.svg"
cat > "$APPS/roadrush-launcher.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=ROADRUSH-LINUX-LAUNCHER
Comment=Road Rash 30th Anniversary Edition — Linux 启动器（音乐版本可切换）
Exec=python3 $HERE/gui.py
Path=$HERE
Icon=roadrush-launcher
Terminal=false
Categories=Game;
EOF
update-desktop-database "$APPS" 2>/dev/null || true
echo "已安装: $APPS/roadrush-launcher.desktop"
