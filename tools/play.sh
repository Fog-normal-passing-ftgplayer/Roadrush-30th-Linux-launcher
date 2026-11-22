#!/usr/bin/env bash
# 不依赖 GUI 的启动脚本：Proton/GE-Proton（优先）或系统 wine
#   GAME_DIR=/path/to/game ./play.sh
#   PROTON=/path/to/proton ./play.sh        # 指定 runner
#   RR_VIRTUAL_DESKTOP=0 ./play.sh          # 关掉虚拟桌面
#   RR_MIDI=0 ./play.sh                     # 不启 MIDI 软音源
set -u
GAMEDIR="${GAME_DIR:-$(pwd)}"
[ -f "$GAMEDIR/RoadRash95.exe" ] || { echo "!! $GAMEDIR 里没有 RoadRash95.exe"; exit 1; }

find_proton() {
  local d p
  for d in "$HOME/.local/share/Steam/compatibilitytools.d" "$HOME/.steam/steam/compatibilitytools.d" \
           "$HOME/.local/share/Steam/steamapps/common" "$HOME/.steam/steam/steamapps/common"; do
    [ -d "$d" ] || continue
    p="$(ls -1d "$d"/GE-Proton* "$d"/Proton* 2>/dev/null | sort -V | tail -1)"
    [ -n "$p" ] && [ -x "$p/proton" ] && { echo "$p/proton"; return; }
  done
}
PROTON="${PROTON:-$(find_proton)}"

export WINEDLLOVERRIDES="dxva2=d${WINEDLLOVERRIDES:+;$WINEDLLOVERRIDES}"
unset XMODIFIERS XIM XIM_PROGRAM XIM_ARGS 2>/dev/null || true
export GTK_IM_MODULE=none QT_IM_MODULE=none SDL_IM_MODULE=none

WINPATH="Z:${GAMEDIR//\//\\}"; case "$WINPATH" in *\\) ;; *) WINPATH="$WINPATH\\";; esac
KEY='HKLM\Software\Wow6432Node\Electronic Arts\RoadRash 95'

if [ -n "$PROTON" ] && [ -x "$PROTON" ]; then
  export STEAM_COMPAT_DATA_PATH="${STEAM_COMPAT_DATA_PATH:-$HOME/.local/share/road-rash-30th}"
  export STEAM_COMPAT_CLIENT_INSTALL_PATH="${STEAM_COMPAT_CLIENT_INSTALL_PATH:-$HOME/.steam/steam}"
  mkdir -p "$STEAM_COMPAT_DATA_PATH"; PFX="$STEAM_COMPAT_DATA_PATH/pfx"
  PW="$(dirname "$PROTON")/files/bin/wine"
  reg_add() { if [ -d "$PFX" ] && [ -x "$PW" ]; then WINEPREFIX="$PFX" "$PW" reg add "$1" /v "$2" /t REG_SZ /d "$3" /f >/dev/null 2>&1
              else "$PROTON" run 'C:\windows\system32\reg.exe' add "$1" /v "$2" /t REG_SZ /d "$3" /f >/dev/null 2>&1; fi }
  reg_add "$KEY" path "$WINPATH"; reg_add "$KEY" language English
  [ "${RR_MIDI:-1}" != "0" ] && bash "$(dirname "$0")/start-midi-synth.sh" >/dev/null 2>&1 || true
  cd "$GAMEDIR" || exit 1
  VD="${RR_VIRTUAL_DESKTOP:-1920x1080}"; case "$VD" in 0|off|no|"") VD="";; esac
  if [ -n "$VD" ]; then exec "$PROTON" run explorer "/desktop=RoadRash,${VD}" "${WINPATH}RoadRash95.exe"
  else exec "$PROTON" run RoadRash95.exe; fi
else
  export WINEPREFIX="${WINEPREFIX:-$HOME/.wine}"
  wine reg add "$KEY" /v path /t REG_SZ /d "$WINPATH" /f >/dev/null 2>&1
  wine reg add "$KEY" /v language /t REG_SZ /d English /f >/dev/null 2>&1
  cd "$GAMEDIR" || exit 1
  VD="${RR_VIRTUAL_DESKTOP:-1920x1080}"; case "$VD" in 0|off|no|"") VD="";; esac
  if [ -n "$VD" ]; then exec wine explorer "/desktop=RoadRash,${VD}" RoadRash95.exe
  else exec wine RoadRash95.exe; fi
fi
