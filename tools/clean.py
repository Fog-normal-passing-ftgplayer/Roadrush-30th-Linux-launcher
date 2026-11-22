#!/usr/bin/env python3
"""对 read_mids() 解析出的事件流做 MIDI 清理：
 1) 同音重复触发：先补一个 note-off（delta 0），再 note-on，避免前一个音被硬切
 2) 孤立 note-off（没有对应 on）：丢弃，避免误切后面的音
 3) 曲末仍按住的音：补 note-off
用法: clean.py in.MID out.mid [--bpm B]
"""
import sys, struct
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from mids2smf import read_mids, build

def clean(events):
    out, active = [], {}
    fixed_retrig = dropped_off = 0
    pending = 0                      # 被丢弃事件携带的 delta，必须补偿给下一条
    def emit(item):
        nonlocal pending
        item[0] += pending; pending = 0
        out.append(item)
    for delta, st, d1, d2 in events:
        if st is None:
            emit([delta, st, d1, d2]); continue
        hi = st & 0xF0; ch = st & 0x0F; key = (ch, d1)
        if hi == 0x90 and d2 > 0:                 # note-on
            if key in active:                     # 同音未关就重触发
                emit([0, 0x80 | ch, d1, 0])
                fixed_retrig += 1
            active[key] = True
            emit([delta, st, d1, d2])
        elif hi == 0x80 or (hi == 0x90 and d2 == 0):   # note-off
            if key in active:
                active.pop(key)
                emit([delta, st, d1, d2])
            else:
                dropped_off += 1                  # 孤立 off：丢弃，但 delta 补偿给下一条
                pending += delta
        else:
            emit([delta, st, d1, d2])
    for (ch, key) in list(active):                # 收尾
        out.append([0, 0x80 | ch, key, 0]); active.pop((ch, key))
    return out, fixed_retrig, dropped_off

if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    bpm = float(sys.argv[sys.argv.index('--bpm')+1]) if '--bpm' in sys.argv else None
    ev, total = read_mids(src)
    ev2, r, o = clean(ev)
    open(dst, 'wb').write(build(ev2, bpm=bpm))
    print(f"{dst}: 原 {len(ev)} 事件 → 清理后 {len(ev2)}（修同音重触发 {r}, 丢孤立off {o}）")
