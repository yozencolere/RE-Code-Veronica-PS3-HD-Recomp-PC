"""Indexe toutes les textures XET (archives .arc et fichiers .tex) d'un ou plusieurs dossiers et calcule
l'empreinte texpack (nom de fichier du dump du jeu) avec plusieurs hypotheses, puis la confronte a un dossier de dump.
Usage : python index_textures.py <dossier_dump> <sortie.tsv> <dossier1> [dossier2 ...]"""
import os, sys, struct, pickle
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
import texhash
src = open(os.path.join(here, "compare_arc.py")).read().split("usa, eng, fra = sys.argv")[0]
ns = {}; exec(src, ns)

# XET format byte -> (RSX format, octets par bloc 4x4 ou par pixel, compresse)
FMT = {0x14: (0x86, 8, True), 0x18: (0x88, 16, True), 0x16: (0x87, 16, True), 0x28: (0x85, 4, False),
       0x19: (0x81, 1, False), 0x2b: (0x8B, 2, False)}

def xet_info(d):
    """(w, h, nmips, fmt XET, offset donnees) ou None."""
    if len(d) < 0x14 or d[1:4] != b"XET": return None
    v = int.from_bytes(d[8:11], "big"); h = (v >> 13) * 4; f = d[14]; mips = d[11]
    off = struct.unpack_from(">I", d, 0x10)[0]
    if f not in FMT: return (0, h, mips, f, off)
    rsx, bpp, comp = FMT[f]
    # largeur deduite de la taille du niveau 0 (le champ largeur n'a pas la meme unite partout)
    return (v & 0x1FFF) * 4, h, mips, f, off

def level_bytes(w, h, f):
    rsx, bpp, comp = FMT[f]
    return ((w + 3) // 4) * ((h + 3) // 4) * bpp if comp else w * h * bpp

def textures_of(path):
    if path.lower().endswith(".tex"):
        d = ns["unwrap"](open(path, "rb").read())
        yield os.path.basename(path), d
        return
    try: R = ns["load"](path)
    except Exception: return
    for (name, typ), d in R.items():
        if typ == 0x241f5deb: yield name.split("\\")[-1], d

dump = sys.argv[1]; out = sys.argv[2]
dumped = {}
for f in os.listdir(dump):
    if len(f) > 17 and f[16] == "_": dumped[f[:16]] = f
rows = []
for root in sys.argv[3:]:
    for dp, dn, fn in os.walk(root):
        for f in fn:
            if not f.lower().endswith((".arc", ".tex")): continue
            p = os.path.join(dp, f)
            for name, d in textures_of(p):
                info = xet_info(d)
                if not info: continue
                w, h, mips, fx, off = info
                if fx not in FMT: rows.append((p, name, w, h, mips, "%02X" % fx, "", "")); continue
                # largeur : essai de la valeur lue, puis de la moitie / du double si la taille ne colle pas
                rest = len(d) - off
                for ww in (w, w // 2, w * 2, w // 4):
                    if ww and level_bytes(ww, h, fx) <= rest: w = ww; break
                n0 = level_bytes(w, h, fx)
                rsx = FMT[fx][0]
                cands = {"n0": d[off:off + n0], "tout": d[off:]}
                hit = ""; hv0 = "%016X" % texhash.texpack_hash(cands["n0"], w, h, rsx)
                for k, b in cands.items():
                    hv = "%016X" % texhash.texpack_hash(b, w, h, rsx)
                    if hv in dumped: hit = k + ":" + dumped[hv]; hv0 = hv
                rows.append((p, name, w, h, mips, "%02X" % fx, hv0, hit))
with open(out, "w", encoding="utf-8") as o:
    for r in rows: o.write("\t".join(map(str, r)) + "\n")
found = [r for r in rows if r[7]]
print(len(rows), "textures,", len(found), "retrouvees dans le dump (", len(dumped), "fichiers de dump )")
for r in found: print(" ", os.path.relpath(r[0], sys.argv[3]), r[1], r[2], r[3], r[5], r[7])
