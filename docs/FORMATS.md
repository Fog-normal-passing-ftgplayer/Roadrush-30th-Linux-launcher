# 逆向笔记：Road Rash 30th 用到的四种音频容器

全部基于对 `RoadRash95.exe` / `AUDIO/` 的静态分析与运行时验证（`WINEDEBUG=+file,+relay`），
没有对二进制打补丁。

## 1. `AUDIO/MUSIC/*.MID` —— 私有音序格式 `RIFF/MIDS`

扩展名是 `.MID`，但**不是标准 MIDI**，任何标准 MIDI 软件都读不了。

```
RIFF <size> MIDS
  fmt  (12) : 480(PPQ), 4096, 0
  data      : 8 字节头 + N × 4100 字节块 [+ 尾部不完整块]
```

每个 4100 字节块：

```
偏移   长度   内容
0      4      标记 0x00000FFC（= 4092 = 记录区长度）
4      4092   341 条 12 字节记录
4096   4      块尾绝对时间（tick）
```

12 字节记录：

```
0  1  status   （0x8n/0x9n/0xAn/0xBn/0xCn/0xDn/0xEn；块首记录为 0xFC 标记）
1  1  data1
2  1  data2
3  1  0
4  4  delta（tick，相对上一条）
8  4  保留
```

**校验方法**（这套结构不是猜的）：块内所有 delta 之和 == 块尾时间戳，
30~40 个块全部成立。踩过的两个坑：

1. 块首那条 `0xFC` 标记记录的 **delta 是真实时间推进**，丢弃会导致每块少几 tick；
2. 文件末尾有一段**没有 0x0FFC 标记的不完整块**（每首约 140 条事件 = 结尾乐句），
   只处理完整块会丢掉它。

转换器：`tools/mids2smf.py`

```bash
python3 tools/mids2smf.py AUDIO/MUSIC/GRUNGE1.MID out.mid --bpm 170
```

## 2. `AUDIO/MUSIC/*.SBK` —— SoundFont **1.0**

`ifil` 版本 = **1.0**，带 SF2 没有的 `snam` 块；采样头是 **16 字节**
（`[start,end,loopstart,loopend]`），**没有采样率、根音、名字**——那些当年存在 AWE 驱动/硬件里。
fluidsynth 只吃 SF2，所以直接加载会失败。

转换器 `tools/sf1_to_sf2.py`：

- `pbag/pgen/inst/ibag/igen` 与 SF2 布局相同 → 原样搬运
- `phdr` 重建（补 12 字节保留区）
- `shdr` 重建：16B → 46B，补名字/采样率/根音（**这两项文件里没有，只能估**）
- 注意 RIFF 奇数块：INFO 子块长度必须为偶数，否则被判定"structurally defective"

各个 `.SBK` 的内容（预置号是 GM 音色号）：

| 文件 | 预置 | 采样 |
|---|---|---|
| GRUNGE1.SBK | 29 RUSHTUTT / 30 Dist guitar / 87 Pulsy VCO Bass 2 | 3 |
| GRUNGE2.SBK | 36 Slap Bass / 30 FUNKCHRD | 3 |
| RRDRUMS.SBK | bank 128 preset 0「Heavy Drums」 | 12（按 GM 键位分区） |

> 用自动估根音转换后试听仍被判定"音高不对"，所以最终定稿没有用这套采样，
> 而是用通用 GM 音色（FluidR3）。这条路留给后来者。

## 3. `AUDIO/MUSIC/*.RRA` —— 游戏内实际播放的音乐

```
RIFF <size> WAVE
  fmt  (16) : PCM, 1 或 2 声道, 22050 Hz, 8-bit
  data      : 原始 PCM
```

就是**裸 8-bit PCM**，14 个文件对应 14 个"槽位"。替换时保持同样的 fmt 即可被引擎接受
（实测 8-bit 正常；16-bit 未验证）。

## 4. 影片

`VIDEO/*.AVI` = cinepak 320×192；`VIDEO/*.mp4` 与 `VIDEO_UP/*.mp4` = h264 Main@4.0 1458×1080 + AAC。
播放走 Media Foundation（`MF.dll`/`MFPlat.DLL` + EVR），Wine 下需要 `dxva2=d`（见 TROUBLESHOOTING）。
