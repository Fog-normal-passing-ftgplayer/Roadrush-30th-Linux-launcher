# 经典 MIDI 音乐的还原与实装

## 成品（本地生成，不入库）
| 曲目 | 关卡 | BPM | 时长 |
|---|---|---|---|
| GRUNGE1 | City（都市） | 170 | 2:34 |
| GRUNGE2 | Sierra Nevada（内华达山脉） | 120 | 2:22 |
| GRUNGE3 | City streets（城市街道） | 180 | 2:53 |
| GRUNGE4 | Hills（山丘公路） | 145 | 2:49 |
| GRUNGE5 | Coastal highway（沿海公路） | 200 | 2:12 |

BPM 是逐首试听后定的（原始 MIDS **不存 tempo**，SMF 缺省 120 BPM 会偏慢）。

## 一键生成（推荐）
```bash
tools/make-classic-music.sh --game /path/to/game [--out DIR] [--install]
```
约 30 秒跑完 5 首，产物写到 `~/Music/roadrush-classic/`；`--install` 会顺带替换游戏槽位。

下面是它内部做的事（想手动调参时看）：

## 渲染流水线
```bash
GAME=/path/to/Road.Rash.30th.Anniversary.Edition
# 1) MIDS → SMF（带 tempo 元事件，给播放器/DAW 用）
python3 tools/mids2smf.py "$GAME/AUDIO/MUSIC/GRUNGE1.MID" GRUNGE1.mid --bpm 170
# 2) 清理：同音重触发补 off / 丢孤立 note-off / 曲末补 off / 跨通道同音起音对齐
python3 tools/clean.py  GRUNGE1.mid /tmp/c.mid
python3 tools/align.py  GRUNGE1.mid /tmp/a.mid        # 消除 ch0/5/6 三层错位造成的 flam
# 3) fluidsynth 渲染（注意：这个构建遇到 tempo 元事件会输出空文件 → 用 --scale 缩放时间轴）
python3 tools/retempo.py /tmp/a.mid /tmp/s.mid $(python3 -c 'print(120/170)')
fluidsynth -ni -F /tmp/r.wav -r 44100 -g 0.8 \
  -o synth.polyphony=1024 -o synth.min-note-length=0 \
  /usr/share/soundfonts/FluidR3_GM.sf2 /tmp/s.mid
# 4) 响度归一 + 44.1kHz（loudnorm 默认会升到 192k）
ffmpeg -y -i /tmp/r.wav -af loudnorm=I=-16:TP=-1.5:LRA=11 -ar 44100 -c:a flac GRUNGE1.flac
```

### 会让"结尾缺失"的两个坑（已修）
1. **尾部残块不是从第 0 字节开始记录**：有些曲子尾部还带一条 12 字节头
   `[u32 本段字节数][u32 delta][u32 0]`，直接按记录解析会在第一条就断掉 → 整段结尾丢失
   （GRUNGE2 丢 170 条、GRUNGE5 丢 109 条）。现在会先做对齐搜索（0/12/8/4/16/20 偏移）。
2. **清理时丢弃孤立 note-off 会连它的 delta 一起丢**：时间轴会整体缩短、结尾被"压缩"。
   现在被丢弃事件的 delta 会补偿给下一条事件。

### 三个必须的合成器参数
- `synth.min-note-length=0`：默认 10ms，会直接吞掉极短音（每首 1~4% 的音符 <10ms）
- `synth.polyphony=1024`：默认 256 在密集段落会 voice stealing，听起来像"卡一下"
- `dxva2=d` 与本流程无关，但启动游戏时要加（见 TROUBLESHOOTING）

## 实装进游戏（替换 RRA）
```bash
# 备份 + 只把赛道槽位换成经典曲（HB_TRIP 永远保留原版：前端锁定的就是它）
GAME_DIR="$GAME" SRC=~/Music/roadrash-95-official tools/music-mode.sh classic
GAME_DIR="$GAME" tools/music-mode.sh status
GAME_DIR="$GAME" tools/music-mode.sh original      # 一键回原版
```
槽位映射（比赛内随机播放，所以是循环填充）：

```
HB_TRIP  ← 原版（菜单锁定曲，永不替换）
HB_PASS  ← GRUNGE1     MM_DINO  ← GRUNGE3     P_BRIDGE ← GRUNGE4
P_JESSIE ← GRUNGE5     P_PANSY  ← GRUNGE2     SD_DUEL  ← GRUNGE1
SD_TRAIN ← GRUNGE3     SG_KICKS ← GRUNGE4     SG_OUTSH ← GRUNGE5
SG_RUSTY ← GRUNGE2     SG_SUPER ← GRUNGE1     T_AUTO   ← GRUNGE3
T_TEETH  ← GRUNGE4
```

## 还能做的
- 池子扩容：`SBKGRNG1-5` + `KLOWN` 也是同一套 MIDS，渲进来可以把随机池从 5 首扩到 11 首
- 16-bit：`BITS=16 tools/music-mode.sh classic`（未验证引擎是否接受 16-bit PCM）
- 原版音色：`tools/sf1_to_sf2.py` 可以把 `.SBK`（SF1）转成 fluidsynth 能加载的 SF2，
  但采样率/根音在文件里缺失，需要按各采样实测基频校准（当前自动估值试听效果不好，未采用）
