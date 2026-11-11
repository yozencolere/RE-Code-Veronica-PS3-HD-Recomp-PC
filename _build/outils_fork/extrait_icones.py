"""Extrait les textures de l'inventaire (item1\\subtx_tex.arc) : archive d'origine, ressources XET,
DDS (donnees DXT d'origine, sans perte), PNG des pages, et une PNG par icone (cases de 102x72).
Usage : python extrait_icones.py <subtx_tex.arc> <dossier_sortie> [dossier_dump_du_jeu]"""
import os, sys, struct, shutil
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
import png_simple, texhash
src = open(os.path.join(here, "compare_arc.py")).read().split("usa, eng, fra = sys.argv")[0]
ns = {}; exec(src, ns)

def c565(v): return ((v >> 11 & 31) * 255 + 15) // 31, ((v >> 5 & 63) * 255 + 31) // 63, ((v & 31) * 255 + 15) // 31

def decode(data, w, h, dxt5):
    """DXT1/DXT5 -> RGBA (octets PC : couleurs petit-boutistes, comme le dump du jeu)."""
    bs = 16 if dxt5 else 8; out = bytearray(w * h * 4)
    for by in range(h // 4):
        for bx in range(w // 4):
            b = (by * (w // 4) + bx) * bs; alpha = [255] * 16
            if dxt5:
                a0, a1 = data[b], data[b + 1]; bits = int.from_bytes(data[b + 2:b + 8], "little")
                pal = [a0, a1] + ([((6 - i) * a0 + i * a1) // 7 for i in range(1, 7)] if a0 > a1 else [((4 - i) * a0 + i * a1) // 5 for i in range(1, 5)] + [0, 255])
                alpha = [pal[(bits >> (3 * i)) & 7] for i in range(16)]; c = b + 8
            else: c = b
            v0, v1 = struct.unpack_from("<HH", data, c); idx = struct.unpack_from("<I", data, c + 4)[0]
            k0, k1 = c565(v0), c565(v1)
            if v0 > v1 or dxt5: pal = [k0 + (255,), k1 + (255,), tuple((2 * a + b2) // 3 for a, b2 in zip(k0, k1)) + (255,), tuple((a + 2 * b2) // 3 for a, b2 in zip(k0, k1)) + (255,)]
            else: pal = [k0 + (255,), k1 + (255,), tuple((a + b2) // 2 for a, b2 in zip(k0, k1)) + (255,), (0, 0, 0, 0)]
            for i in range(16):
                col = pal[(idx >> (2 * i)) & 3]; p = ((by * 4 + i // 4) * w + bx * 4 + i % 4) * 4
                out[p:p + 3] = bytes(col[:3]); out[p + 3] = alpha[i] if dxt5 else col[3]
    return out

def dds(data, w, h, dxt5):
    hdr = struct.pack("<4sIIIIIII44sIII4sIIIII5I", b"DDS ", 124, 0x81007, h, w, len(data), 0, 1, b"\0" * 44,
                      32, 4, 0, b"DXT5" if dxt5 else b"DXT1", 0, 0, 0, 0, 0, 0x1000, 0, 0, 0, 0)
    return hdr + data

def crop(img, w, x0, y0, cw, ch):
    out = bytearray()
    for y in range(y0, y0 + ch): out += img[(y * w + x0) * 4:(y * w + x0 + cw) * 4]
    return out

def content(img, w, x, y):
    r, g, b, a = img[(y * w + x) * 4:(y * w + x) * 4 + 4]
    return not (r < 48 and g < 48 and 40 <= b <= 160) and not (r < 12 and g < 12 and b < 12)

arc, out = sys.argv[1], sys.argv[2]; dump = sys.argv[3] if len(sys.argv) > 3 else None
for d in ("1_original", "1_original/textures_xet", "2_dds", "3_png_pages", "4_icones"): os.makedirs(os.path.join(out, d), exist_ok=True)
shutil.copy2(arc, os.path.join(out, "1_original", os.path.basename(arc)))
R = ns["load"](arc); bilan = []
for (name, typ), d in R.items():
    short = name.split("\\")[-1]
    open(os.path.join(out, "1_original", "textures_xet" if typ == 0x241f5deb else "", short + (".xet" if typ == 0x241f5deb else ".bin")), "wb").write(d)
    if typ != 0x241f5deb: continue
    h = struct.unpack_from(">H", d, 8)[0] >> 3; w = d[10] << 2; off = struct.unpack_from(">I", d, 0x10)[0]; dxt5 = d[14] == 0x18
    size = (w // 4) * (h // 4) * (16 if dxt5 else 8); data = d[off:off + size]
    hv = texhash.texpack_hash(data, w, h, 0x88 if dxt5 else 0x86)
    open(os.path.join(out, "2_dds", short + ".dds"), "wb").write(dds(data, w, h, dxt5))
    img = decode(data, w, h, dxt5)
    png_simple.write(os.path.join(out, "3_png_pages", short + ".png"), w, h, img)
    verif = "pas de capture du jeu"
    if dump:
        cand = [f for f in os.listdir(dump) if f.startswith("%016X" % hv)]
        if cand:
            dw, dh, dpx = png_simple.read(os.path.join(dump, cand[0]))
            ecart = max(abs(a - b) for a, b in zip(img, dpx)) if (dw, dh) == (w, h) and len(dpx) == len(img) else None
            # le dump est en RVB premultiplie par l'alpha : comparer en RVB seulement pour DXT1
            if not dxt5 and ecart is not None:
                ecart = max(abs(img[i] - dpx[i]) for i in range(len(img)) if i % 4 != 3)
            verif = "capture du jeu %s : ecart max %s" % (cand[0], ecart)
    bilan.append("%s %dx%d %s empreinte %016X | %s" % (short, w, h, "DXT5" if dxt5 else "DXT1", hv, verif))
    if dxt5: continue
    # pages d'icones : cases 102x72, 7 colonnes ; une icone qui deborde sur la case voisine est fusionnee
    page = short.replace("_BM", ""); dst = os.path.join(out, "4_icones", page); os.makedirs(dst, exist_ok=True)
    CW, CH, cols, rows = 102, 72, 7, h // 72; n = 0
    for r in range(rows):
        c = 0
        while c < cols:
            span = 1
            while c + span < cols:
                xb = (c + span) * CW
                both = sum(1 for y in range(r * CH, r * CH + CH) if content(img, w, xb - 1, y) and content(img, w, xb, y))
                if both >= 4: span += 1
                else: break
            cell = crop(img, w, c * CW, r * CH, CW * span, CH)
            filled = sum(1 for y in range(CH) for x in range(CW * span) if content(cell, CW * span, x, y))
            if filled > 60:
                png_simple.write(os.path.join(dst, "%s_ligne%02d_col%d%s.png" % (page, r, c, "-%d" % (c + span - 1) if span > 1 else "")), CW * span, CH, cell); n += 1
            c += span
    bilan.append("  %s : %d icones" % (page, n))
open(os.path.join(out, "LISEZMOI.txt"), "w", encoding="utf-8").write(
    "Textures de l'inventaire de Resident Evil Code: Veronica X HD (PS3, NPUB30467), archive item1\\subtx_tex.arc.\n\n"
    "1_original      : l'archive d'origine (copie) et ses ressources telles quelles (.xet = en-tete Capcom XET + donnees DXT).\n"
    "2_dds           : les memes donnees DXT dans un conteneur DDS (sans perte, lisible par les outils d'image).\n"
    "3_png_pages     : chaque texture entiere en PNG (tex0003 et tex0004 = pages d'icones d'objets).\n"
    "4_icones        : une PNG par icone, cases de 102x72 (les armes sur deux cases sont gardees entieres).\n\n"
    + "\n".join(bilan) + "\n")
print("\n".join(bilan))
