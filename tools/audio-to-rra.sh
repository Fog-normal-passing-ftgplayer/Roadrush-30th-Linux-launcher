#!/usr/bin/env bash
# 把任意音频（mp3/flac/ogg/wav…）转成游戏能播的 .RRA 槽位文件
#   ./audio-to-rra.sh <音频文件> <槽位名> [更多 "音频 槽位" 对 ...]
# 例：
#   ./audio-to-rra.sh ~/Music/"Oringnal music/1. 沿海公路.mp3" P_PANSY
#   ./audio-to-rra.sh a.mp3 SG_KICKS b.flac T_AUTO
# 需要 GAME_DIR（或自动从当前目录/常见位置推断）；首次会备份原版到 AUDIO/MUSIC._orig
set -euo pipefail
GAME_DIR="${GAME_DIR:-}"
if [ -z "$GAME_DIR" ]; then
  for cand in "$PWD" "$HOME/PCGAME-Road.Rash.30th.Anniversary.Edition.Build.26105967-P2P/Road.Rash.30th.Anniversary.Edition"; do
    [ -f "$cand/RoadRash95.exe" ] && GAME_DIR="$cand" && break
  done
fi
[ -n "$GAME_DIR" ] && [ -f "$GAME_DIR/RoadRash95.exe" ] || { echo "!! 需要 GAME_DIR（含 RoadRash95.exe 的目录）" >&2; exit 1; }
MUSIC="$GAME_DIR/AUDIO/MUSIC"; BACKUP="$GAME_DIR/AUDIO/MUSIC._orig"
BITS="${BITS:-8}"
[ $# -ge 2 ] || { sed -n '2,9p' "$0"; exit 1; }
mkdir -p "$BACKUP"
install_one() {
  local src="$1" slot="$2"
  [ -f "$src" ] || { echo "!! 找不到 $src" >&2; return 1; }
  # 杂项保护：不是音频就报错（有些“mp3”其实是网页）
  ffprobe -v error -show_entries format=format_name -of csv=p=0 "$src" | grep -qiE "mp3|flac|ogg|wav|aac|m4a" \
    || { echo "!! $src 不是有效音频（可能是下载失败的网页）" >&2; return 1; }
  [ -f "$BACKUP/$slot.RRA" ] || cp -a "$MUSIC/$slot.RRA" "$BACKUP/" 2>/dev/null || true
  local codec=("-c:a" "pcm_u8"); [ "$BITS" = "16" ] && codec=("-c:a" "pcm_s16le")
  ffmpeg -v error -y -i "$src" -ac 2 -ar 22050 -f wav "${codec[@]}" "$MUSIC/$slot.RRA"
  local dur; dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$MUSIC/$slot.RRA")
  printf "   %-14s ← %-40s %6.1fs %s\n" "$slot.RRA" "$(basename "$src")" "$dur" "${BITS}bit"
}
while [ $# -ge 2 ]; do
  install_one "$1" "${2%.RRA}"
  shift 2
done
echo ">> 完成（原版已备份到 AUDIO/MUSIC._orig，可用 music-mode.sh original 一键还原）"
