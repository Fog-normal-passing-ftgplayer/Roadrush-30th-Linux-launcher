# 在 Linux / Wine 上跑 Road Rash 30th 的四个坑（以及各自的原因）

结论先放：**能用 GE-Proton 就别用系统 wine**，其余按顺序加开关。

## 1. 启动只弹一个 "Warning" 小窗然后退出

**原因**：游戏启动时做安装检测，读
`HKLM\SOFTWARE\Electronic Arts\RoadRash 95`（32 位进程 → 实际读 `Wow6432Node` 视图）。
免安装/复制版没有这个键 → 弹 `MessageBoxA(NULL, "Warning", "", MB_ICONWARNING)` 后退出。
（正文只有一个单词 "Warning"，所以看起来像个没内容的空窗；按钮上的中文"确定"在缺字形的
Wine 对话框里还会显示成两个方块。）

**修复**：写注册表（**必须在 Wow6432Node 下**，只写 64 位视图无效）

```bash
wine reg add 'HKLM\Software\Wow6432Node\Electronic Arts\RoadRash 95' /v path /t REG_SZ /d 'Z:\path\to\game\' /f
wine reg add 'HKLM\Software\Wow6432Node\Electronic Arts\RoadRash 95' /v language /t REG_SZ /d English /f
```
launcher 与 `tools/play.sh` 每次启动都会自动补。

## 2. 片头影片崩溃 / 黑屏且没声音

**原因 A（崩溃）**：影片走 Media Foundation + EVR，EVR 会调 `dxva2` 的视频处理器
（Wine 里是半 stub），日志末尾是 `dxva2:...GetVideoProcessorDeviceGuids semi-stub`
然后 `Unhandled page fault on read access to 00000000`。

修复：`WINEDLLOVERRIDES="dxva2=d"`（强制软件解码）。

**原因 B（黑屏+静音，只在系统 wine 上）**：`winegstreamer/winedmo` 解析这批 1080p h264 的
caps 失败：
`GStreamer-Video-CRITICAL ... gst_video_info_from_caps: assertion 'gst_caps_is_fixed (caps)' failed`
→ 媒体会话整个死掉（画面和声音一起）。
**GE-Proton 自带改造过的 mfplat/mfreadwrite，同一批文件不报错**。这是切换 Proton 的最大理由。

## 3. 游戏跑着跑着"卡住"，Alt+Tab 切一下才恢复

**原因**：DirectDraw 全屏窗口 + XWayland + KWin。影片窗口是独立的 1920×1080 顶层窗口
（`DigitalVideo` 窗口类由 `winmm` 的 MCI 创建、`EVR Fullscreen Window` 是 MF 那条路），
它一盖上来 KWin 就判定游戏窗口"被遮挡"，停止送帧 → `glXSwapBuffers` 阻塞 → 像卡死；
影片结束后遮挡状态不一定清除，直到 Alt+Tab 让窗口重新 active。
另外 fcitx5 的 XIM 窗口（`class=fcitx`）也会抢 active。

**修复**：
- 用 **wine 虚拟桌面**跑（`explorer /desktop=RoadRash,1920x1080`），所有窗口包在同一个 X 窗口里
- 启动前清掉输入法环境：`unset XMODIFIERS XIM; export GTK_IM_MODULE=none QT_IM_MODULE=none SDL_IM_MODULE=none`

## 4. `Game music`（原版 MIDI）没声音

**原因**：这个选项走的是 **AWE32/64 硬件音源**路线（`AWEMAN32.DLL` + `GRUNGE*.SBK`），
Wine 不模拟 AWE 卡，所以是死路。`Rock music in race` 放的才是 `AUDIO/MUSIC/*.RRA`，
那个可以被替换。

**绕法（本项目采用）**：把 MIDS 解成 SMF、渲染成 WAV/FLAC，再替换 RRA 槽位（见 MUSIC.md）。
**另一条没走完的路**：游戏 exe 里同时导入了 `midiStreamOpen/midiStreamOut`，
说明存在标准 GM MIDI 分支；若让 Wine 的 MIDI 设备可用（或 patch 掉 AWE 检测），
理论上游戏可以直接播原版 MIDI。trace 显示启动阶段它根本没调 MIDI API，需要进比赛复现。

## 附：影片/音乐是"随机池"
- 比赛内音乐从 12 个槽位（`SG_* T_* P_* SD_* MM_*`）里**随机**挑
- 前端/菜单会锁定 Jukebox 里选中的那首（本项目锁定 `HB_TRIP`，所以菜单永远原版）
