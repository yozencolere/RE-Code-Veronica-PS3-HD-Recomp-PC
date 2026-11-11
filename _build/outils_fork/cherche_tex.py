"""Cherche dans les .arc d'un dossier les textures (type 0x241f5deb) dont l'empreinte texpack vaut l'une des cibles.
Usage : python cherche_tex.py <dossier> <hash1,hash2,...>"""
import os, sys, struct
import texhash
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "compare_arc.py")).read().split("usa, eng, fra = sys.argv")[0]
ns = {}; exec(src, ns)
targets = {int(x, 16) for x in sys.argv[2].split(",")}
for dp, dn, fn in os.walk(sys.argv[1]):
    for f in sorted(fn):
        if not f.endswith(".arc"): continue
        p = os.path.join(dp, f)
        try: R = ns["load"](p)
        except Exception as e: continue
        for (n, t), d in R.items():
            if t != 0x241f5deb or len(d) < 0x14: continue
            w = struct.unpack_from(">H", d, 8)[0] >> 3; h = d[10] << 2; off = struct.unpack_from(">I", d, 0x10)[0]; fmt = d[14]
            for bf, bs in ((0x86, 8), (0x88, 16), (0x87, 16)):
                size = (w // 4) * (h // 4) * bs
                if off + size > len(d): continue
                hv = texhash.texpack_hash(d[off:off + size], w, h, bf)
                if hv in targets: print("%016X" % hv, os.path.relpath(p, sys.argv[1]), n, w, h, "fmt %02X" % fmt)
