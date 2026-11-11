"""Redessine les triangles du releve CV_NEAREST_DUMP (a0 = position 1280x720, a15/4096 = coordonnee normalisee, a14 = couleur)
dans la zone x0,y0-x1,y1 agrandie S fois. Echantillonnage : nearest, ou lineaire si 'lin' en 9e argument."""
import sys, os, re, glob; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import png_simple
dump, out, x0, y0, x1, y1, S = sys.argv[1], sys.argv[2], *map(int, sys.argv[3:8])
LIN = len(sys.argv) > 8 and sys.argv[8] in ('lin', 'ins')
INS = len(sys.argv) > 8 and sys.argv[8] == 'ins'
ops = []; cur = None
for line in open(dump):
    m = re.match(r'op(\d+) n=', line)
    if m: cur = dict(op=int(m[1]), tex=None, v=[], addr=0); ops.append(cur); continue
    if cur is None: continue
    m = re.match(r'\s+t0 .*addr=(\w+).*hash=(\w+)', line)
    if m: cur['tex'] = m[2]; cur['addr'] = int(m[1], 16); continue
    if re.match(r'\s+v\d+:', line):
        cur['v'].append({int(k): tuple(map(float, v.split())) for k, v in re.findall(r'a(\d+)=\(([^)]*)\)', line)})
atl = {}
def tex(h):
    if h not in atl:
        f = glob.glob(rf'E:\Recomp\Test_CV\dump\{h}*.png'); atl[h] = png_simple.read(f[0]) if f else None
    return atl[h]
W, H = (x1 - x0) * S, (y1 - y0) * S
img = bytearray(W * H * 3)
def fetch(t, u, v):
    tw, th, px = t; bpp = len(px) // (tw * th); i = ((int(v) % th) * tw + int(u) % tw) * bpp
    return px[i:i + 3], (px[i + 3] if bpp == 4 else 255)
def sample(t, u, v):
    if not LIN: return fetch(t, u, v)
    u -= 0.5; v -= 0.5; fu = u - int(u // 1); fv = v - int(v // 1); bu = u // 1; bv = v // 1
    acc = [0.0] * 4
    for du, dv, w in ((0, 0, (1 - fu) * (1 - fv)), (1, 0, fu * (1 - fv)), (0, 1, (1 - fu) * fv), (1, 1, fu * fv)):
        c, a = fetch(t, bu + du, bv + dv)
        for k in range(3): acc[k] += c[k] * a * w
        acc[3] += a * w
    a = acc[3]
    return (bytes(int(acc[k] / a) if a else 0 for k in range(3)), int(a))
for o in ops:
    t = tex(o['tex']) if o['tex'] else None
    if not t: continue
    v = o['v']
    for i in range(0, len(v) - 2, 3):
        P = [(p[0][0], p[0][1]) for p in v[i:i + 3]]; T = [(p.get(15, (0, 0))[0] / 4096 * t[0], p.get(15, (0, 0))[1] / 4096 * t[1]) for p in v[i:i + 3]]
        if INS and i - i % 6 + 6 <= len(v):
            g = v[i - i % 6:i - i % 6 + 6]; G = [(p.get(15, (0, 0))[0] / 4096 * t[0], p.get(15, (0, 0))[1] / 4096 * t[1]) for p in g]
            lo = [min(c[k] for c in G) for k in (0, 1)]; hi = [max(c[k] for c in G) for k in (0, 1)]
            T = [tuple(c[k] + (0.5 if c[k] <= lo[k] and hi[k] - lo[k] >= 1 else -0.5 if c[k] >= hi[k] and hi[k] - lo[k] >= 1 else 0) for k in (0, 1)) for c in T]
        (ax, ay), (bx, by), (cx, cy) = P
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if not den: continue
        lo_x = max(0, int((min(ax, bx, cx) - x0) * S)); hi_x = min(W, int((max(ax, bx, cx) - x0) * S) + 1)
        lo_y = max(0, int((min(ay, by, cy) - y0) * S)); hi_y = min(H, int((max(ay, by, cy) - y0) * S) + 1)
        for Y in range(lo_y, hi_y):
            fy = (Y + 0.5) / S + y0
            for X in range(lo_x, hi_x):
                fx = (X + 0.5) / S + x0
                l1 = ((by - cy) * (fx - cx) + (cx - bx) * (fy - cy)) / den
                l2 = ((cy - ay) * (fx - cx) + (ax - cx) * (fy - cy)) / den
                l3 = 1 - l1 - l2
                if l1 < 0 or l2 < 0 or l3 < 0: continue
                u = l1 * T[0][0] + l2 * T[1][0] + l3 * T[2][0]; vv = l1 * T[0][1] + l2 * T[1][1] + l3 * T[2][1]
                c, a = sample(t, u, vv); p = (Y * W + X) * 3
                for k in range(3): img[p + k] = (c[k] * a + img[p + k] * (255 - a)) // 255
png_simple.write(out, W, H, bytes(b for i in range(W * H) for b in (*img[i*3:i*3+3], 255)))
