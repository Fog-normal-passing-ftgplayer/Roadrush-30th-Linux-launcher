#!/usr/bin/env python3
"""clean.py 的加强版：除了同音重触发/孤立off/曲末补off，
还把过短的音符（默认 <10 tick）延长到 10 tick，避免被合成器当噪声丢弃（丢音）。"""
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from mids2smf import read_mids, build
from clean import clean

MIN_TICKS = 10

def extend_short(events, min_ticks=MIN_TICKS):
    out = [list(e) for e in events]
    # 先记住每个 (ch,key) 当前 on 的下标
    on_idx = {}
    pairs = []
    for i, (delta, st, d1, d2) in enumerate(out):
        if st is None: continue
        hi = st & 0xF0; key = (st & 0x0F, d1)
        if hi == 0x90 and d2 > 0:
            on_idx[key] = i
        elif hi == 0x80 or (hi == 0x90 and d2 == 0):
            if key in on_idx:
                pairs.append((on_idx.pop(key), i))
    # 计算每个音符时长，短的往后推 off
    def tick_pos(idx):
        return sum(out[k][0] for k in range(idx+1))
    for on_i, off_i in pairs:
        dur = sum(out[k][0] for k in range(on_i+1, off_i+1))
        if dur >= min_ticks: continue
        need = min_ticks - dur
        out[off_i][0] += need
        for k in range(off_i+1, len(out)):
            if out[k][0] >= need:
                out[k][0] -= need; break
            need -= out[k][0]; out[k][0] = 0
    return out

if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    ev, _ = read_mids(src)
    ev2, r, o = clean(ev)
    ev3 = extend_short(ev2)
    open(dst, 'wb').write(build(ev3))
    print(f"{dst}: {len(ev)} → {len(ev3)} 事件（重触发修复 {r}, 孤立off {o}, 短音延长 ≤{MIN_TICKS} tick）")
