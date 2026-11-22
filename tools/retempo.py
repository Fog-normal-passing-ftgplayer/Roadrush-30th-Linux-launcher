#!/usr/bin/env python3
"""把标准 SMF 的时间轴按因子缩放（不改音高）：new = old * factor。
   factor < 1 → 更快；等价于把 120BPM 当作 target_bpm 播放。"""
import sys, struct

def read_vlq(b, i):
    v = 0
    while True:
        c = b[i]; i += 1
        v = (v << 7) | (c & 0x7F)
        if not c & 0x80: return v, i

def write_vlq(n):
    out = [n & 0x7F]; n >>= 7
    while n: out.insert(0, (n & 0x7F) | 0x80); n >>= 7
    return bytes(out)

def main(src, dst, factor):
    d = open(src, 'rb').read()
    hl = struct.unpack('>I', d[4:8])[0]; hdr = d[:8+hl]
    p = 8+hl; tl = struct.unpack('>I', d[p+4:p+8])[0]; trk = d[p+8:p+8+tl]
    i = 0; out = bytearray()
    while i < len(trk):
        delta, i = read_vlq(trk, i)
        out += write_vlq(int(round(delta * factor)))
        st = trk[i]
        if st == 0xFF:                      # meta
            out.append(st); out.append(trk[i+1])
            ln, j = read_vlq(trk, i+2)
            out += write_vlq(ln); out += trk[j:j+ln]; i = j+ln
        elif st in (0xF0, 0xF7):
            out.append(st); ln, j = read_vlq(trk, i+1)
            out += write_vlq(ln); out += trk[j:j+ln]; i = j+ln
        else:
            if st & 0x80:
                out.append(st); i += 1
                hi = st & 0xF0
            else:
                hi = st & 0xF0 if False else None
            n = 1 if hi in (0xC0, 0xD0) else 2
            out += trk[i:i+n]; i += n
    open(dst, 'wb').write(hdr + b'MTrk' + struct.pack('>I', len(out)) + bytes(out))

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], float(sys.argv[3]))
