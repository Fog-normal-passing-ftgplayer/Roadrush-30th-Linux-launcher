# 免责声明 / Disclaimer

## 中文

1. **本项目不包含任何游戏资源。** 仓库里没有 `RoadRash95.exe`、没有 `.RRA/.MID/.SBK` 音频、
   没有 `.sf2` 音色库、也没有任何"经典 MIDI 曲"的渲染产物（`.flac/.wav`）。这些文件都在
   `.gitignore` 里被显式排除。
2. **Road Rash 及其所有素材（代码、图像、音乐、音效、影片）的版权归 Electronic Arts 所有。**
   本项目与 EA 无任何关联，未获其授权或背书。请使用你**合法持有**的游戏副本。
3. **"经典 MIDI 音乐"是本地生成的。** `tools/make-classic-music.sh` 只是把你自己游戏目录里的
   `AUDIO/MUSIC/*.MID`（私有 `RIFF/MIDS` 容器）解码成标准 MIDI 再渲染成音频，供你本人在自己
   的机器上使用。**已生成的音频属于派生作品，请不要分发、上传或用于任何商业用途。**
4. 本项目的代码（`gui.py`/`core.py`/`tools/*` 等）以 MIT 许可发布（见 `LICENSE`）。
5. 作者不对使用本项目造成的任何后果负责，包括但不限于：存档损坏、系统配置被修改、
   违反第三方许可/法律、以及被版权方追究。

如果你只是想要"能在 Linux 上把这个游戏跑起来 + 听经典音乐"，本项目帮你省掉踩坑的时间；
但**音乐文件的来源与去向由你自己负责**。

## English

1. **No game assets are included.** This repository contains no `RoadRash95.exe`, no `.RRA/.MID/.SBK`
   audio, no `.sf2` SoundFonts, and no rendered "classic MIDI" audio (`.flac/.wav`). These are
   explicitly excluded via `.gitignore`.
2. **Road Rash and all of its assets (code, art, music, SFX, video) are copyright Electronic Arts.**
   This project is not affiliated with or endorsed by EA. Use it only with a game copy you legally own.
3. **The "classic MIDI music" is generated locally.** `tools/make-classic-music.sh` only decodes the
   private `RIFF/MIDS` files from *your* game directory into standard MIDI and renders them for your
   own private use. **The rendered audio is a derivative work — do not redistribute it.**
4. The project's own code is released under the MIT license (see `LICENSE`).
5. The authors accept no liability for any consequences of using this project, including but not
   limited to save corruption, system configuration changes, license or legal violations, or claims
   from rights holders.
