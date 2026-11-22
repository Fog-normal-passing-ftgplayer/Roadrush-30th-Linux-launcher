#!/usr/bin/env python3
"""只对指定通道（默认 ch1 贝斯）做：最短音长 + note-off 释放尾巴。
用法: bassfix.py in.MID out.mid <chan> <min_ticks> <tail_ticks>"""
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from mids2smf import read_mids, build
from clean import clean

def fix(events, chan, min_ticks, tail_ticks):
    out=[list(e) for e in events]
    on={}
    pairs=[]
    for i,(delta,st,d1,d2) in enumerate(out):
        if st is None: continue
        ch=st&0x0F; hi=st&0xF0
        if ch!=chan: continue
        if hi==0x90 and d2>0: on[d1]=i
        elif hi==0x80 or (hi==0x90 and d2==0):
            if d1 in on: pairs.append((on.pop(d1), i))
    for a,b in pairs:
        dur=sum(out[k][0] for k in range(a+1,b+1))
        need=max(0, min_ticks-dur)+tail_ticks
        if need<=0: continue
        out[b][0]+=need
        for k in range(b+1,len(out)):
            if out[k][0]>=need: out[k][0]-=need; break
            need-=out[k][0]; out[k][0]=0
    return out

if __name__=='__main__':
    src,dst,chan,min_t,tail_t=sys.argv[1],sys.argv[2],int(sys.argv[3]),int(sys.argv[4]),int(sys.argv[5])
    ev,_=read_mids(src); ev2,_,_=clean(ev)
    open(dst,'wb').write(build(fix(ev2,chan,min_t,tail_t)))
    print(f"{dst}: ch{chan} 最短 {min_t} tick, off 尾巴 +{tail_t} tick")
