#!/usr/bin/env python3
"""Road Rash 95 SF1(.SBK) → fluidsynth 可加载的 SF2。
SF1 与 SF2 的 pbag/pgen/inst/ibag/igen 记录布局相同（4/4/22/4/4 字节），
区别在：shdr 是 16 字节（无名字/采样率/根音）、phdr 少 12 字节保留、pmod/imod 6 字节。
用法: sf1_to_sf2.py in.SBK out.sf2 [rate] [root]
"""
import struct, sys

def parse(d):
    acc = {}
    def scan(s, e):
        i = s
        while i + 8 <= e:
            cid = d[i:i+4]; size = struct.unpack('<I', d[i+4:i+8])[0]; body = i+8
            acc.setdefault(cid, (body, size))
            if cid == b'LIST' and d[body:body+4] in (b'INFO', b'sdta', b'pdta'):
                scan(body+4, body+size)
            i += 8+size+(size & 1)
    scan(12, len(d))
    return acc

def chunk(cid, body):
    if len(body) & 1: body += b'\0'
    return cid + struct.pack('<I', len(body)) + body

def lst(t, body):
    return chunk(b'LIST', t + body)


def _f0(seg, rate):
    n = len(seg)
    if n < 2048: return None
    best = (-1e30, 0); step = max(1, n // 4096)
    for lag in range(int(rate/1200), min(int(rate/25), n//2)):
        c = 0.0
        for i in range(0, n - lag, step):
            c += seg[i]*seg[i+lag]
        if c > best[0]: best = (c, lag)
    return rate/best[1] if best[1] else None

def auto_roots(samples_by_index, rate):
    import array, math
    out = []
    for A in samples_by_index:
        seg = A[len(A)//4: len(A)//4 + min(8192, max(1024, len(A)//2))]
        f = _f0(seg, rate)
        if not f or f <= 20: out.append(60); continue
        n = 69 + 12*math.log2(f/440.0)
        while n < 0: n += 12
        out.append(max(0, min(127, int(round(n)))))
    return out

def convert(src, dst, rate=22050, root=60):
    d = open(src, 'rb').read(); a = parse(d)
    # 采样
    snam_o, snam_s = a[b'snam']
    names = [d[snam_o+k*20:snam_o+(k+1)*20].split(b'\0')[0].decode('latin1') for k in range(snam_s//20)]
    shdr_o, shdr_s = a[b'shdr']
    recs = [struct.unpack('<IIII', d[shdr_o+k*16:shdr_o+(k+1)*16]) for k in range(shdr_s//16)]
    # 末尾 EOS：全零或 end<=start
    while recs and (not any(recs[-1]) or recs[-1][1] <= recs[-1][0]):
        recs = recs[:-1]
    smpl_o, smpl_s = a[b'smpl']; smpl = d[smpl_o:smpl_o+smpl_s]
    # 重排采样数据（46 字节对齐），并记录每条新起点/长度
    sd = bytearray(); placed = []
    for i, (s, e, ls, le) in enumerate(recs):
        while len(sd) % 46: sd.append(0)
        start = len(sd) // 2
        sd += smpl[s*2:e*2]
        placed.append((start, e - s, ls - s, le - s))
    while len(sd) % 46: sd.append(0)
    # 自动为每条采样估根音（SF1 不存这个值）
    import array as _arr
    samples_i = []
    for (st_, en_, ls_, le_) in recs:
        A = _arr.array('h'); A.frombytes(smpl[st_*2:en_*2]); samples_i.append(A)
    roots = auto_roots(samples_i, rate)
    if len(sys.argv) > 5 and sys.argv[5] == 'fixed':
        roots = [root] * len(samples_i)   # 所有采样统一用固定根音（复刻用户选中的版本）
    print("自动根音:", roots)
    # pdta：pbag/pgen/inst/ibag/igen 原样搬运，phdr / shdr 重建
    phdr_o, phdr_s = a[b'phdr']
    phdr = b''
    for k in range(phdr_s // 38):
        e = d[phdr_o+k*38:phdr_o+(k+1)*38]
        name = e[:20].split(b'\0')[0]
        pre, ban, bag = struct.unpack('<HHH', e[20:26])
        phdr += name[:19].ljust(20, b'\0') + struct.pack('<HHH', pre, ban, bag) + struct.pack('<III', 0, 0, 0)
    shdr = b''
    for i, (start, dur, ls, le) in enumerate(placed):
        nm = names[i] if i < len(names) else f'S{i}'
        loop_s = start + ls if 0 <= ls <= dur else start
        loop_e = start + le if 0 <= le <= dur else start + dur - 1
        shdr += nm.encode('latin1')[:19].ljust(20, b'\0') + struct.pack(
            '<IIIII', start, start + dur - 1, loop_s, loop_e, rate) + bytes([roots[i] if i < len(roots) else root, 0]) + struct.pack('<HH', 0, 1)
    shdr += b'EOS'.ljust(20, b'\0') + struct.pack('<IIIII', 0, 0, 0, 0, 0) + bytes([0, 0]) + struct.pack('<HH', 0, 0)
    def raw(cid):
        o, s = a[cid]; return d[o:o+s]
    info = lst(b'INFO', chunk(b'ifil', struct.pack('<HH', 2, 1)) +
               chunk(b'isng', b'EMU8000\0') + chunk(b'INAM', b'RoadRash95 Bank\0'))
    sdta = lst(b'sdta', chunk(b'smpl', bytes(sd)))
    pdta = lst(b'pdta', chunk(b'phdr', phdr) + chunk(b'pbag', raw(b'pbag')) +
               chunk(b'pmod', struct.pack('<HhHhH', 0, 0, 0, 0, 0)) + chunk(b'pgen', raw(b'pgen')) +
               chunk(b'inst', raw(b'inst')) + chunk(b'ibag', raw(b'ibag')) +
               chunk(b'imod', struct.pack('<HhHhH', 0, 0, 0, 0, 0)) + chunk(b'igen', raw(b'igen')) +
               chunk(b'shdr', shdr))
    open(dst, 'wb').write(chunk(b'RIFF', b'sfbk' + info + sdta + pdta))
    print(f"{dst}: {len(placed)} 采样, {len(open(dst,'rb').read())} 字节, rate={rate} root={root}")

if __name__ == '__main__':
    convert(sys.argv[1], sys.argv[2],
            int(sys.argv[3]) if len(sys.argv) > 3 else 22050,
            int(sys.argv[4]) if len(sys.argv) > 4 else 60)
