"""Repere (et corrige) les separateurs verticaux fins d'un atlas d'interface :
colonnes de 1-2 texels transparentes ou sombres, entre deux texels opaques clairs,
sur au moins MIN_RUN lignes consecutives.
Usage : python separateurs.py entree.png marque.png [corrige.png]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import png_simple

MIN_RUN = 6
src, marked = sys.argv[1], sys.argv[2]
fixed = sys.argv[3] if len(sys.argv) > 3 else None
w, h, px = png_simple.read(src)
def P(x, y): o = (y * w + x) * 4; return px[o], px[o + 1], px[o + 2], px[o + 3]
def lum(p): return (p[0] * 3 + p[1] * 6 + p[2]) / 10
def clear(p): return p[3] > 200 and lum(p) > 70

hits = set()   # (x, y, largeur)
for y in range(h):
    for x in range(1, w - 2):
        L, C = P(x - 1, y), P(x, y)
        for width in (1, 2):
            R = P(x + width, y)
            if not (clear(L) and clear(R)): continue
            mid = [P(x + k, y) for k in range(width)]
            ref = min(lum(L), lum(R))
            if all(m[3] < 128 or lum(m) < 0.6 * ref for m in mid):
                hits.add((x, y, width)); break
# ne garder que les runs verticaux
keep = set()
for (x, y, wd) in hits:
    run = 1; yy = y - 1
    while (x, yy, wd) in hits: run += 1; yy -= 1
    yy = y + 1
    while (x, yy, wd) in hits: run += 1; yy += 1
    if run >= MIN_RUN: keep.add((x, y, wd))
cols = {}
for (x, y, wd) in keep: cols.setdefault((x, wd), []).append(y)
for (x, wd), ys in sorted(cols.items()):
    ys.sort(); print(f"x={x} largeur={wd} lignes {ys[0]}..{ys[-1]} ({len(ys)})")
out = bytearray(px)
for (x, y, wd) in keep:
    for k in range(wd):
        o = (y * w + x + k) * 4; out[o:o + 4] = bytes((255, 0, 0, 255))
png_simple.write(marked, w, h, out)
if fixed:
    fx = bytearray(px)
    for (x, y, wd) in keep:
        L, R = P(x - 1, y), P(x + wd, y)
        for k in range(wd):
            t = (k + 1) / (wd + 1)
            o = (y * w + x + k) * 4
            fx[o:o + 4] = bytes(round(L[c] * (1 - t) + R[c] * t) for c in range(4))
    png_simple.write(fixed, w, h, fx)
    print("corrige :", fixed, len(keep), "texels")
