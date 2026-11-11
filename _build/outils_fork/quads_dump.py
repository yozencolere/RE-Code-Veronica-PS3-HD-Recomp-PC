"""Lit le releve CV_NEAREST_DUMP et liste les quads (6 sommets) : rect ecran + rect UV (texels = a15/8)."""
import re, sys
ops=[]; cur=None
for line in open(sys.argv[1]):
    m=re.match(r'op(\d+) n=(\d+)',line)
    if m: cur=dict(op=int(m[1]),tex=[],v=[]); ops.append(cur); continue
    if cur is None: continue
    m=re.match(r'\s+t0 (\d+)x(\d+) fmt=(\w+).*hash=(\w+)',line)
    if m: cur['tex']=(m[1]+'x'+m[2],m[3],m[4]); continue
    m=re.match(r'\s+v\d+:',line)
    if m:
        a={int(k):tuple(map(float,v.split())) for k,v in re.findall(r'a(\d+)=\(([^)]*)\)',line)}
        cur['v'].append(a)
def quads():
    for o in ops:
        v=o['v']
        for i in range(0,len(v)-5,6):
            q=v[i:i+6]
            xs=[p.get(0,(0,0))[0] for p in q]; ys=[p.get(0,(0,0))[1] for p in q]
            us=[p.get(15,(0,0))[0]/8 for p in q]; vs=[p.get(15,(0,0))[1]/8 for p in q]
            yield o,i//6,(min(xs),min(ys),max(xs),max(ys)),(min(us),min(vs),max(us),max(vs)),q
if __name__=='__main__':
    for o,k,r,uv,q in quads():
        print(f"op{o['op']:03} q{k:03} {o['tex'][0]:>9} {o['tex'][2][:8]} pos=({r[0]:.0f},{r[1]:.0f})-({r[2]:.0f},{r[3]:.0f}) uv=({uv[0]:.2f},{uv[1]:.2f})-({uv[2]:.2f},{uv[3]:.2f})")
