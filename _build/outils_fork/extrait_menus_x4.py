"""Extrait les textures des menus (archives adv, window, on_manual, compevt, polices systeme), versions US et FR,
et les agrandit x4 au plus proche voisin. Les PNG agrandies portent le nom que le jeu attend
(<empreinte>_<L>x<H>_<FMT>.png) : il suffit de les poser dans le dossier des textures du jeu.
Usage : python extrait_menus_x4.py <nativePS3 US> <biocv_disc EU> <dossier_sortie> [dossier_dump]"""
import os, sys, struct
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
import png_simple, texhash
src = open(os.path.join(here, "compare_arc.py")).read().split("usa, eng, fra = sys.argv")[0]
ns = {}; exec(src, ns)

def c565(v):
    r, g, b = (v >> 11) & 31, (v >> 5) & 63, v & 31
    return (r << 3 | r >> 2, g << 2 | g >> 4, b << 3 | b >> 2)
def decode_dxt(data, w, h, dxt5):
    """Copie de texpack_decode_bc (libs/video/rsx_texture_pack.c), arrondis compris."""
    bs = 16 if dxt5 else 8; out = bytearray(w * h * 4); bw = (w + 3) // 4
    for by in range((h + 3) // 4):
        for bx in range(bw):
            b = (by * bw + bx) * bs; cb = b + 8 if dxt5 else b
            c0, c1 = struct.unpack_from("<HH", data, cb); idx = struct.unpack_from("<I", data, cb + 4)[0]
            p0, p1 = c565(c0), c565(c1)
            if dxt5 or c0 > c1:
                pal = [p0 + (255,), p1 + (255,), tuple((2 * x + y + 1) // 3 for x, y in zip(p0, p1)) + (255,), tuple((x + 2 * y + 1) // 3 for x, y in zip(p0, p1)) + (255,)]
            else:
                pal = [p0 + (255,), p1 + (255,), tuple((x + y) // 2 for x, y in zip(p0, p1)) + (255,), (0, 0, 0, 0)]
            alpha = None
            if dxt5:
                a = [data[b], data[b + 1]] + [0] * 6
                if a[0] > a[1]:
                    for i in range(1, 7): a[i + 1] = ((7 - i) * a[0] + i * a[1] + 3) // 7
                else:
                    for i in range(1, 5): a[i + 1] = ((5 - i) * a[0] + i * a[1] + 2) // 5
                    a[6], a[7] = 0, 255
                bits = int.from_bytes(data[b + 2:b + 8], "little")
                alpha = [a[(bits >> (3 * i)) & 7] for i in range(16)]
            for i in range(16):
                x, y = bx * 4 + (i & 3), by * 4 + (i >> 2)
                if x >= w or y >= h: continue
                col = pal[(idx >> (2 * i)) & 3]; p = (y * w + x) * 4
                out[p:p + 4] = bytes(col)
                if dxt5: out[p + 3] = alpha[i]
    return out

# octet de format XET -> (format RSX pour l'empreinte, nom du dump, octets par bloc/pixel, compresse)
FMT = {0x14: (0x86, "DXT1", 8, True), 0x18: (0x88, "DXT5", 16, True), 0x28: (0x85, "ARGB", 4, False),
       0x19: (0x86, "DXT1", 8, True), 0x2b: (0x88, "DXT5", 16, True)}  # 0x19/0x2b : polices (taille = DXT1/DXT5)
def level_bytes(w, h, f):
    _, _, bpp, comp = FMT[f]
    return ((w + 3) // 4) * ((h + 3) // 4) * bpp if comp else w * h * bpp

def unswizzle(lvl, w, h, bpp):
    """Textures non compressees avec niveaux de detail : pixels entrelaces (ordre de Morton, x d'abord)."""
    lw, lh = w.bit_length() - 1, h.bit_length() - 1
    out = bytearray(len(lvl))
    for y in range(h):
        for x in range(w):
            o = 0; s = 0
            for i in range(max(lw, lh)):
                if i < lw: o |= ((x >> i) & 1) << s; s += 1
                if i < lh: o |= ((y >> i) & 1) << s; s += 1
            out[(y * w + x) * bpp:(y * w + x + 1) * bpp] = lvl[o * bpp:(o + 1) * bpp]
    return bytes(out)

def decode(lvl, w, h, f, swizzled=False):
    """Comme tex_dump_image du jeu : les canaux tels que le shader les recoit."""
    if FMT[f][3]: return decode_dxt(lvl, w, h, FMT[f][2] == 16)
    if swizzled: lvl = unswizzle(lvl, w, h, FMT[f][2])
    out = bytearray(w * h * 4)
    if f == 0x28:
        for i in range(w * h): out[i * 4:i * 4 + 4] = bytes((lvl[i * 4 + 1], lvl[i * 4 + 2], lvl[i * 4 + 3], lvl[i * 4]))
    elif f == 0x19:
        for i in range(w * h): out[i * 4:i * 4 + 4] = bytes((lvl[i], lvl[i], lvl[i], 255))
    else:
        for i in range(w * h): out[i * 4:i * 4 + 4] = bytes((lvl[i * 2], lvl[i * 2 + 1], 0, 255))
    return out

def x4(px, w, h):
    out = bytearray()
    for y in range(h):
        row = bytearray()
        for x in range(w): row += px[(y * w + x) * 4:(y * w + x) * 4 + 4] * 4
        out += bytes(row) * 4
    return out

us, eu, dst = sys.argv[1], sys.argv[2], sys.argv[3]; dump = sys.argv[4] if len(sys.argv) > 4 else None
dumped = {f[:16]: f for f in os.listdir(dump)} if dump else {}
SOURCES = [("menus", r"adv\title.arc"), ("menus", r"adv\opt.arc"), ("menus", r"adv\screen_setting.arc"),
           ("menus", r"adv\vs_mpsel_tex.arc"), ("menus", r"system\compevt_tex.arc"), ("manuel", r"on_manual\on_manual.arc"),
           ("fenetres", r"window\window0_0.arc"), ("fenetres", r"window\window2_0.arc"),
           ("boutons", r"window\button_guide.arc")]
FONTS = [r"system\font\Gothic_AM_NOMIP.tex", r"system\texture\nrodinpro_BM_HQ_NOMIP.tex",
         r"system\texture\sysfont2_AM_NOMIP.tex", r"system\texture\sysfont_AM_NOMIP.tex"]
jobs = []
for cat, rel in SOURCES:
    for ver, path in (("us", os.path.join(us, "biocv_disc", "usa", rel)), ("fr", os.path.join(eu, "fra", rel))):
        R = ns["load"](path)
        for (name, typ), d in R.items():
            if typ == 0x241f5deb: jobs.append((cat, ver, os.path.basename(rel)[:-4], name.split("\\")[-1], d))
for rel in FONTS:
    jobs.append(("police_texte", "us", "system", os.path.basename(rel)[:-4], ns["unwrap"](open(os.path.join(us, rel), "rb").read())))

seen = {}; log = []
for cat, ver, arc, name, d in jobs:
    v = int.from_bytes(d[8:11], "big"); h = v >> 11; f = d[14]; mips = d[11]
    off = struct.unpack_from(">I", d, 0x10)[0]
    if f not in FMT: log.append(f"IGNOREE (format {f:02X}) {ver} {arc} {name}"); continue
    rest = len(d) - off; w = (v & 0x7FF) * 4
    for ww in (w, w // 2, w * 2, w // 4):
        if ww and level_bytes(ww, h, f) <= rest: w = ww; break
    if mips > 1:
        # niveau 0 : la table des decalages suit l'en-tete (offset 0x10 = premier niveau)
        lvl = d[off:off + level_bytes(w, h, f)]; hashed = lvl
    else:
        lvl = d[off:off + level_bytes(w, h, f)]; hashed = d[off:]
    rsx, fname = FMT[f][0], FMT[f][1]
    hv = "%016X" % texhash.texpack_hash(hashed, w, h, rsx)
    key = f"{hv}_{w}x{h}_{fname}"
    if key in seen: seen[key][1].append(f"{ver} {arc}\\{name}"); continue
    pow2 = (w & (w - 1)) == 0 and (h & (h - 1)) == 0
    px = decode(lvl, w, h, f, swizzled=mips > 1 and pow2)
    verif = ""
    if hv in dumped:
        dw, dh, dpx = png_simple.read(os.path.join(dump, dumped[hv]))
        if (dw, dh) == (w, h):
            rgb = False
            ecart = max(abs(px[i] - dpx[i]) for i in range(len(px)) if not (rgb and i % 4 == 3))
            verif = f" | verifie contre l'extraction du jeu : ecart max {ecart}"
    o1 = os.path.join(dst, "1_originaux", cat); o2 = os.path.join(dst, "2_upscale_x4_plus_proche_voisin", cat)
    os.makedirs(o1, exist_ok=True); os.makedirs(o2, exist_ok=True)
    png_simple.write(os.path.join(o1, f"{ver}_{arc}_{name}_{key}.png"), w, h, px)
    png_simple.write(os.path.join(o2, key + ".png"), w * 4, h * 4, x4(px, w, h))
    seen[key] = (cat, [f"{ver} {arc}\\{name}"], w, h, mips, verif)
    print(cat, key, ver, arc, name, verif, flush=True)
with open(os.path.join(dst, "LISEZMOI.txt"), "w", encoding="utf-8") as o:
    o.write("Textures des menus de Resident Evil Code: Veronica X HD (US NPUB30467 et FR NPEB00553), agrandies x4 au plus proche voisin.\n\n"
            "1_originaux : chaque texture a sa taille d'origine (prefixe us_/fr_, archive, nom interne, puis le nom attendu par le jeu).\n"
            "2_upscale_x4_plus_proche_voisin : les memes x4, nommees <empreinte>_<LxH d'origine>_<format>.png = nom attendu par le jeu.\n"
            "  Pour les utiliser : copier ces PNG dans le dossier texturas du jeu (sous-dossier libre) et activer le remplacement.\n"
            "  Le jeu en francais affiche les versions fr ; les deux versions sont fournies quand elles different.\n\n")
    for key, (cat, srcs, w, h, mips, verif) in sorted(seen.items(), key=lambda kv: (kv[1][0], kv[0])):
        o.write(f"[{cat}] {key}.png ({w}x{h}, {mips} niveau(x)) <- {', '.join(srcs)}{verif}\n")
    for l in log: o.write(l + "\n")
print(len(seen), "textures distinctes ;", "\n".join(log))
