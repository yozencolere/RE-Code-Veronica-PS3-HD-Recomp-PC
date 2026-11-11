"""Page d'icones agrandie x4 (bilineaire, comme le filtrage du jeu) avec des icones remplacees.
Usage : python page_icones_x4.py <page.png 768x768> <sortie.png> <ligne> <colonne> <icone.png 408x288> [...]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import png_simple

src, dst = sys.argv[1], sys.argv[2]
w, h, px = png_simple.read(src)
S = 4; W, H = w * S, h * S
out = bytearray(W * H * 4)
# coordonnee source de chaque colonne / ligne de sortie (centres de texels), bornee
def axis(n, N):
    t = []
    for o in range(N):
        s = (o + 0.5) / S - 0.5
        s = min(max(s, 0.0), n - 1.0)
        i = min(int(s), n - 2); f = s - i
        t.append((i, f))
    return t
ax, ay = axis(w, W), axis(h, H)
for Y, (y0, fy) in enumerate(ay):
    r0 = y0 * w * 4; r1 = (y0 + 1) * w * 4; base = Y * W * 4
    for X, (x0, fx) in enumerate(ax):
        a = r0 + x0 * 4; b = a + 4; c = r1 + x0 * 4; d = c + 4
        w00 = (1 - fx) * (1 - fy); w10 = fx * (1 - fy); w01 = (1 - fx) * fy; w11 = fx * fy
        p = base + X * 4
        for k in range(4):
            out[p + k] = int(px[a + k] * w00 + px[b + k] * w10 + px[c + k] * w01 + px[d + k] * w11 + 0.5)
args = sys.argv[3:]
for i in range(0, len(args), 3):
    row, col, icon = int(args[i]), int(args[i + 1]), args[i + 2]
    iw, ih, ipx = png_simple.read(icon)
    assert (iw, ih) == (102 * S, 72 * S), f"{icon} : {iw}x{ih}, attendu {102*S}x{72*S}"
    x0, y0 = col * 102 * S, row * 72 * S
    # Upscalers shift the flat blue background by a few levels, which would
    # show as a lighter rectangle in the game's blue slot: where the new icon
    # is only background (close to the enlarged original there, give or take
    # that shift), keep the original; elsewhere the new icon, blended softly.
    for y in range(ih):
        for x in range(iw):
            p = ((y0 + y) * W + x0 + x) * 4; q = (y * iw + x) * 4
            o = out[p:p + 3]; n = ipx[q:q + 3]
            bg = o[0] < 48 and o[1] < 48 and 40 <= o[2] <= 160
            dist = max(abs(int(n[k]) - int(o[k])) for k in range(3))
            t = 1.0 if not bg else min(max((dist - 12) / 24.0, 0.0), 1.0)
            for k in range(3): out[p + k] = int(o[k] * (1 - t) + n[k] * t + 0.5)
            out[p + 3] = 255
    print(f"icone ligne {row} colonne {col} : {icon} en ({x0},{y0})")
png_simple.write(dst, W, H, out)
print(dst, W, H)
