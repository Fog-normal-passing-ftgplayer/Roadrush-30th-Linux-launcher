#!/usr/bin/env bash
# 一键：从你自己游戏里的原始 MIDS 生成经典 MIDI 曲，并可直接装进游戏
#
#   ./make-classic-music.sh --game /path/to/Road.Rash.30th.Anniversary.Edition [--out DIR] [--install]
#
# 依赖：python3 / fluidsynth / ffmpeg / 一个 GM 音色库（默认 FluidR3_GM.sf2）
# 产物：<out>/GRUNGE1..5.flac（44.1kHz, -16 LUFS）+ GRUNGE1..5.mid（标准 MIDI，带 tempo）
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GAME=""; OUT="${HOME}/Music/roadrush-classic"; INSTALL=0
SF="${RR_SOUNDFONT:-/usr/share/soundfonts/FluidR3_GM.sf2}"
declare -A BPM=([1]=170 [2]=120 [3]=180 [4]=145 [5]=200)

while [ $# -gt 0 ]; do
  case "$1" in
    --game) GAME="${2:-}"; shift 2;;
    --out)  OUT="${2:-}";  shift 2;;
    --install) INSTALL=1; shift;;
    -h|--help) sed -n '2,9p' "$0"; exit 0;;
    *) echo "未知参数: $1"; exit 1;;
  esac
done
[ -n "$GAME" ] || { echo "用法: $0 --game /path/to/game [--out DIR] [--install]"; exit 1; }
[ -f "$GAME/RoadRash95.exe" ] || { echo "!! $GAME 里没有 RoadRash95.exe"; exit 1; }
MUSIC="$GAME/AUDIO/MUSIC"
for t in python3 fluidsynth ffmpeg; do command -v "$t" >/dev/null || { echo "!! 缺 $t"; exit 1; }; done
[ -f "$SF" ] || { echo "!! 缺音色库 $SF（装 soundfont-fluid，或用 RR_SOUNDFONT= 指定）"; exit 1; }

mkdir -p "$OUT"; TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
for n in 1 2 3 4 5; do
  b="${BPM[$n]}"; src="$MUSIC/GRUNGE$n.MID"
  [ -f "$src" ] || { echo "!! 缺 $src"; exit 1; }
  echo "==> GRUNGE$n  (${b} BPM)"
  # 1) 标准 MIDI（给播放器/DAW，带 tempo 元事件）
  python3 "$HERE/mids2smf.py" "$src" "$OUT/GRUNGE$n.mid" --bpm "$b" >/dev/null
  # 2) 清理 + 跨通道起音对齐 → 无 tempo 元事件的 SMF
  python3 "$HERE/align.py" "$src" "$TMP/a$n.mid" >/dev/null
  # 3) 时间轴缩放到目标 BPM（fluidsynth 对 tempo 元事件有 bug，只能缩放 delta）
  python3 "$HERE/retempo.py" "$TMP/a$n.mid" "$TMP/s$n.mid" "$(python3 -c "print(120/$b)")"
  # 4) 渲染 + 响度归一
  fluidsynth -ni -a pulseaudio -F "$TMP/r$n.wav" -r 44100 -g 0.8 \
    -o synth.polyphony=1024 -o synth.min-note-length=0 "$SF" "$TMP/s$n.mid" >/dev/null 2>&1
  ffmpeg -v error -y -i "$TMP/r$n.wav" -af loudnorm=I=-16:TP=-1.5:LRA=11 -ar 44100 \
    -c:a flac -compression_level 8 "$OUT/GRUNGE$n.flac"
  printf "    %s.flac  %.1fs\n" "GRUNGE$n" "$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT/GRUNGE$n.flac")"
done
printf '%s\n' GRUNGE1.flac GRUNGE2.flac GRUNGE3.flac GRUNGE4.flac GRUNGE5.flac > "$OUT/playlist.m3u"
echo "==> 完成：$OUT"

if [ "$INSTALL" = "1" ]; then
  echo "==> 装进游戏（备份原版，菜单曲 HB_TRIP 保持原版）"
  GAME_DIR="$GAME" SRC="$OUT" "$HERE/music-mode.sh" classic
fi
