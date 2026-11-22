#!/usr/bin/env bash
# 起 fluidsynth（ALSA seq）+ seq-connect 桥，把 Wine 的 MIDI 输出接到软音源
# 需要：fluidsynth、音色库、seq-connect（tools/seq-connect.c 编译所得）
set -u
SF="${RR_SOUNDFONT:-/usr/share/soundfonts/FluidR3_GM.sf2}"
BRIDGE="${RR_BRIDGE:-$HOME/.local/share/road-rash-30th/bin/seq-connect}"
command -v fluidsynth >/dev/null 2>&1 || { echo "缺 fluidsynth"; exit 0; }
[ -f "$SF" ] || { echo "缺音色库 $SF"; exit 0; }
pgrep -x fluidsynth >/dev/null || setsid bash -c "tail -f /dev/null | exec fluidsynth -a pulseaudio -m alsa_seq -g 1.0 '$SF'" >/dev/null 2>&1 &
[ -x "$BRIDGE" ] && { pgrep -x seq-connect >/dev/null || setsid "$BRIDGE" >/dev/null 2>&1 & }
echo "MIDI 软音源已就绪"
