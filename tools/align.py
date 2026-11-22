#!/usr/bin/env python3
"""把「同音高、跨通道、彼此间隔 <= W tick」的 note-on 对齐到最早那个时刻，
消除 ch0/ch5/ch6 三层同音叠加造成的 flam（听感上的“卡/咔”）。"""
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from mids2smf import read_mids, build
from clean import clean

W = 20

def align(events):
    abs_ev=[]; t=0
    for delta,st,d1,d2 in events:
        t+=delta; abs_ev.append([t, st, d1, d2])
    ons=[i for i,e in enumerate(abs_ev) if e[1] is not None and (e[1]&0xF0)==0x90 and e[3]>0]
    ons.sort(key=lambda i: abs_ev[i][0])
    moved=0; i=0
    while i < len(ons):
        j=i; key=abs_ev[ons[i]][2]; t0=abs_ev[ons[i]][0]
        cluster=[ons[i]]
        while j+1 < len(ons) and abs_ev[ons[j+1]][2]==key and abs_ev[ons[j+1]][0]-t0 <= W:
            j+=1; cluster.append(ons[j])
        if len(cluster)>1:
            for k in cluster:
                if abs_ev[k][0]!=t0: moved+=1
                abs_ev[k][0]=t0
        i=j+1
    abs_ev.sort(key=lambda e:e[0])          # 稳定排序保持同刻内的相对顺序
    prev=0; out=[]
    for t,st,d1,d2 in abs_ev:
        out.append([t-prev, st, d1, d2]); prev=t
    return out, moved

if __name__=='__main__':
    src,dst=sys.argv[1],sys.argv[2]
    ev,_=read_mids(src); ev2,_,_=clean(ev)
    out,moved=align(ev2)
    open(dst,'wb').write(build(out))
    print(f"{dst}: 对齐 {moved} 个跨通道同音 note-on（窗口 {W} tick）")
