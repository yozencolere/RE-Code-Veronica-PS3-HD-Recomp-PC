"""Redessine les quads du releve (nearest, alpha) dans une zone de l'ecran 1280x720, agrandie S fois."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
dump, out, x0, y0, x1, y1, S = sys.argv[1], sys.argv[2], *map(int, sys.argv[3:8])
import png_simple, quads_dump as qd
atl = {}
def tex(h):
    import glob
    if h not in atl:
        f = glob.glob(rf'E:\Recomp\Test_CV\dump\{h}*.png')
        atl[h] = png_simple.read(f[0]) if f else None
    return atl[h]
W, H = (x1-x0)*S, (y1-y0)*S
img = bytearray(W*H*4)
for o,k,r,uv,q in qd.quads():
    t = tex(o['tex'][2]) if o['tex'] else None
    if not t or r[2] <= x0 or r[0] >= x1 or r[3] <= y0 or r[1] >= y1 or r[2]==r[0] or r[3]==r[1]: continue
    tw, th, px = t; bpp = len(px)//(tw*th)
    # orientation : u suit x si le sommet de x min a u min
    col = q[0].get(14,(1,1,1,1))
    for Y in range(max(0,int((r[1]-y0)*S)), min(H,int((r[3]-y0)*S))):
        fy = (Y+0.5)/S + y0; v = uv[1] + (fy-r[1])/(r[3]-r[1])*(uv[3]-uv[1])
        for X in range(max(0,int((r[0]-x0)*S)), min(W,int((r[2]-x0)*S))):
            fx = (X+0.5)/S + x0; u = uv[0] + (fx-r[0])/(r[2]-r[0])*(uv[2]-uv[0])
            ti = (int(v)%th*tw + int(u)%tw)*bpp
            a = px[ti+3] if bpp==4 else 255
            p = (Y*W+X)*4
            for c in range(3): img[p+c] = (px[ti+c]*a + img[p+c]*(255-a))//255
            img[p+3] = 255
png_simple.write(out, W, H, img)
