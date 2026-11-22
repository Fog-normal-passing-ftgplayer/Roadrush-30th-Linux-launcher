#!/usr/bin/env python3
"""给每个 note-off 加一段「释放尾巴」（延长衰减），避免 GM 音色把和弦尾巴硬切。"""
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from mids2smf import read_mids, build
from clean import clean

def add_tail(events, tail_ticks):
    out=[list(e) for e in events]
    off_idx=[]
    for i,(delta,st,d1,d2) in enumerate(out):
        if st is None: continue
        hi=st&0xF0
        if hi==0x80 or (hi==0x90 and d2==0): off_idx.append(i)
    for i in off_idx:
        need=tail_ticks
        out[i][0]+=need
        for k in range(i+1,len(out)):
            if out[k][0]>=need: out[k][0]-=need; break
            need-=out[k][0]; out[k][0]=0
    return out

if __name__=='__main__':
    src,dst,tail=sys.argv[1],sys.argv[2],int(sys.argv[3])
    ev,_=read_mids(src); ev2,_,_=clean(ev)
    open(dst,'wb').write(build(add_tail(ev2,tail)))
    print(f"{dst}: off 延长 {tail} tick")
