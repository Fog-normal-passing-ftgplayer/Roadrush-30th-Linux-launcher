#!/usr/bin/env bash
# 本地构建 + 打一个可当 pacman 源用的仓库目录
# 用法: packaging/make-release.sh [输出目录，默认 ./dist]
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="${1:-$HERE/../dist}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
cp "$HERE/pkgbuild/PKGBUILD" "$HERE/pkgbuild/roadrush-launcher-git.install" "$WORK/"
( cd "$WORK" && makepkg -f --nocheck --noconfirm >/dev/null )
mkdir -p "$OUT"
cp "$WORK"/*.pkg.tar.zst "$OUT/"
( cd "$OUT" && repo-add -q roadrush.db.tar.gz ./*.pkg.tar.zst )
echo "==> 产物在 $OUT"
ls -la "$OUT"
cat <<'TIP'

上传到 GitHub Releases（手动或 gh release create <tag> dist/*）：
  1. roadrush-launcher-git-*.pkg.tar.zst
  2. roadrush.db.tar.gz
  3. roadrush.files.tar.gz

用户侧添加源：
  /etc/pacman.conf 追加
    [roadrush]
    SigLevel = Optional TrustAll
    Server = https://github.com/Fog-normal-passing-ftgplayer/Roadrush-30th-Linux-launcher/releases/latest/download
  然后 sudo pacman -Sy && sudo pacman -S roadrush-launcher-git
TIP
