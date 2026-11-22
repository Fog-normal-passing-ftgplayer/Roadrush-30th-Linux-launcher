#!/usr/bin/env python3
"""只修「过短的音符」：某通道里短于 <thr> tick 的音，把它的 off 往后推到 <target> tick。
  其它音符完全不动（保留原版 articulation）。
用法: bassfix2.py in.MID out.mid <chan> <thr_ticks> <target_ticks>"""
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from mids2smf import read_mids, build
from clean import clean

def fix(events, chan, thr, target):
    out=[list(e) for e in events]
    on={}; pairs=[]
    for i,(delta,st,d1,d2) in enumerate(out):
        if st is None: continue
        if (st&0x0F)!=chan: continue
        hi=st&0xF0
        if hi==0x90 and d2>0: on[d1]=i
        elif hi==0x80 or (hi==0x90 and d2==0):
            if d1 in on: pairs.append((on.pop(d1), i))
    changed=0
    for a,b in pairs:
        dur=sum(out[k][0] for k in range(a+1,b+1))
        if dur>=thr: continue
        need=target-dur
        out[b][0]+=need
        for k in range(b+1,len(out)):
            if out[k][0]>=need: out[k][0]-=need; break
            need-=out[k][0]; out[k][0]=0
        changed+=1
    return out, changed

if __name__=='__main__':
    src,dst,chan,thr,target=sys.argv[1],sys.argv[2],int(sys.argv[3]),int(sys.argv[4]),int(sys.argv[5])
    ev,_=read_mids(src); ev2,_,_=clean(ev)
    out,ch=fix(ev2,chan,thr,target)
    open(dst,'wb').write(build(out))
    print(f"{dst}: ch{chan} 里短于 {thr} tick 的音 {ch} 个 → 拉长到 {target} tick，其它不动")
