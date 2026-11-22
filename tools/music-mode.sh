#!/usr/bin/env bash
# 原版音乐 / 经典 MIDI 曲 两套配置切换（不依赖 GUI）
#   GAME_DIR=/path/to/game ./music-mode.sh status|original|classic
#   BITS=16 ./music-mode.sh classic
set -u
GAME_DIR="${GAME_DIR:-${1:-}}"
[ -n "${GAME_DIR}" ] || { echo "用法: GAME_DIR=/path/to/game $0 status|original|classic"; exit 1; }
MUSIC="$GAME_DIR/AUDIO/MUSIC"; BACKUP="$GAME_DIR/AUDIO/MUSIC._orig"
SRC="${SRC:-$HOME/Music/roadrush-classic}"
BITS="${BITS:-8}"
MENU_SLOTS="HB_TRIP"          # 前端锁定的原版曲（Jukebox 锁定 HB_Trip），永不被替换
declare -A MAP=(
  [HB_PASS]=GRUNGE1
  [MM_DINO]=GRUNGE3  [P_BRIDGE]=GRUNGE4 [P_JESSIE]=GRUNGE5
  [P_PANSY]=GRUNGE2  [SD_DUEL]=GRUNGE1  [SD_TRAIN]=GRUNGE3
  [SG_KICKS]=GRUNGE4 [SG_OUTSH]=GRUNGE5 [SG_RUSTY]=GRUNGE2
  [SG_SUPER]=GRUNGE1 [T_AUTO]=GRUNGE3   [T_TEETH]=GRUNGE4
)
conv() { local c=("-c:a" "pcm_u8"); [ "$1" = "16" ] && c=("-c:a" "pcm_s16le")
         ffmpeg -v error -y -i "$2" -ac 2 -ar 22050 -f wav "${c[@]}" "$3"; }
case "${2:-${1:-status}}" in
  original) cp -a "$BACKUP"/*.RRA "$MUSIC"/ && echo ">> 已还原全部原版音乐";;
  classic)
    missing=""
    for t in GRUNGE1 GRUNGE2 GRUNGE3 GRUNGE4 GRUNGE5; do
      [ -f "$SRC/$t.flac" ] || missing="$missing $t"
    done
    if [ -n "$missing" ]; then
      echo "!! 缺少经典曲源文件（$SRC）：$missing" >&2
      echo "   先运行: tools/make-classic-music.sh --game \"$GAME_DIR\" --install" >&2
      exit 2
    fi
    cp -a "$BACKUP"/*.RRA "$MUSIC"/          # 先回到原版做基线（不打印）
    for slot in "${!MAP[@]}"; do
      case " $MENU_SLOTS " in *" $slot "*) continue;; esac
      f="$SRC/${MAP[$slot]}.flac"; [ -f "$f" ] || continue
      conv "$BITS" "$f" "$MUSIC/$slot.RRA" && echo "   $slot.RRA ← ${MAP[$slot]} (${BITS}bit)"
    done
    echo ">> 经典曲模式完成（菜单槽位: $MENU_SLOTS）";;
  status)
    python3 - "$MUSIC" "$BACKUP" <<'PY'
import struct, glob, os, sys
music, backup = sys.argv[1], sys.argv[2]
for f in sorted(glob.glob(os.path.join(music, "*.RRA"))):
    n = os.path.basename(f)[:-4]
    d = open(f, 'rb').read(); br = struct.unpack('<I', d[28:32])[0]; bits = struct.unpack('<H', d[34:36])[0]
    o = os.path.getsize(os.path.join(backup, n + ".RRA"))
    print(f"  {n:10s} {len(d)/1048576:5.1f}MB {len(d)/br:4.0f}s {bits}bit  {'原版' if abs(len(d)-o) < 1024 else '经典曲'}")
PY
    ;;
  *) echo "未知命令"; exit 1;;
esac
