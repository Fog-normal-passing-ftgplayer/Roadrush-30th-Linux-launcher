#!/usr/bin/env python3
"""Road Rash 95 MIDS (RIFF, form=MIDS) → 标准 SMF.
格式（用「块尾时间 = 块内 delta 之和」校验过）：
  body = 8B 头 + N×(4100B) [+ 尾部部分块]
  每块 = 341 条 12B 记录 + 4B 块尾绝对时间 + 4B 填充
  记录 = [status,d1,d2,pad][delta u32][保留 u32]
  每块首条记录 status=0xFC（0x0FFC 标记），它的 delta 仍然是真实的时间推进。
用法: mids2smf.py in.MID out.mid [--bpm 170] [--scale-only]
"""
import sys, struct

VALID = set(range(0x8, 0xF))

def read_mids(path):
    d = open(path, 'rb').read()
    body = d[40:]
    ST = 4100
    events, total, nb = [], 0, (len(body) - 8) // ST
    def take(base, count):
        nonlocal total
        for i in range(count):
            off = base + i * 12
            if off + 12 > len(body): return False
            st, d1, d2, pad = body[off:off+4]
            delta = struct.unpack('<I', body[off+4:off+8])[0]
            total += delta
            if (st >> 4) in VALID and delta != 0xFFFFFFFF:
                events.append([delta, st, d1, d2])
            else:
                if events: events[-1][0] += delta          # 纯时间推进，挂到上一条
                elif delta: events.append([delta, None, 0, 0])
        return True
    for k in range(nb):
        if not take(8 + k * ST, 341): break
    # 尾部部分块（没有 0xFFC 标记）
    # 有些曲子尾部还带一条 12 字节头（[u32 本段字节数][u32 delta][u32 0]），
    # 直接按记录解析会在第一条就断掉 → 整段结尾丢失。这里先做对齐搜索。
    tail0 = 8 + nb * ST
    def _valid_at(off):
        if off + 12 > len(body): return False
        st, d1, d2, pad = body[off:off+4]
        if (st >> 4) not in VALID or pad != 0: return False
        return struct.unpack('<I', body[off+4:off+8])[0] != 0xFFFFFFFF
    def _run(off, need=8):
        cnt = 0
        while _valid_at(off):
            cnt += 1; off += 12
            if cnt >= need: return True
        return cnt >= need
    tail = tail0
    for skip in (0, 12, 8, 4, 16, 20):          # 常见：无头 / 12 字节头
        if _run(tail0 + skip):
            if skip:                            # 跳过的头部里可能带 delta，计入时间
                for k in range(skip // 12):
                    total += struct.unpack('<I', body[tail0 + k*12 + 4: tail0 + k*12 + 8])[0]
            tail = tail0 + skip
            break
    while tail + 12 <= len(body):
        st, d1, d2, pad = body[tail:tail+4]
        if (st >> 4) not in VALID: break
        delta = struct.unpack('<I', body[tail+4:tail+8])[0]
        if delta == 0xFFFFFFFF: break
        total += delta
        events.append([delta, st, d1, d2]); tail += 12
    return events, total

def vlq(n):
    b = [n & 0x7F]; n >>= 7
    while n: b.insert(0, (n & 0x7F) | 0x80); n >>= 7
    return bytes(b)

def build(events, division=480, bpm=None, scale=None):
    trk = b''
    if bpm:                                   # 标准播放器用：写 tempo 元事件
        us = int(round(60_000_000 / bpm))
        trk += bytes([0xFF,0x51,0x03,(us>>16)&0xFF,(us>>8)&0xFF,us&0xFF])
    for delta, st, d1, d2 in events:
        if st is None: continue
        if scale: delta = int(round(delta * scale))
        trk += vlq(delta)
        hi = st & 0xF0
        trk += bytes([st,d1]) if hi in (0xC0,0xD0) else bytes([st,d1,d2])
    trk += vlq(0) + bytes([0xFF,0x2F,0x00])
    return b'MThd' + struct.pack('>IHHH', 6, 0, 1, division) + b'MTrk' + struct.pack('>I', len(trk)) + trk

if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    bpm = float(sys.argv[sys.argv.index('--bpm')+1]) if '--bpm' in sys.argv else None
    scale = float(sys.argv[sys.argv.index('--scale')+1]) if '--scale' in sys.argv else None
    ev, total = read_mids(src)
    data = build(ev, bpm=bpm, scale=scale)
    open(dst, 'wb').write(data)
    print(f"{src} → {dst}: 事件={len(ev)} 总ticks={total} ~{total/480*(60/(bpm or 120)):.1f}s")
