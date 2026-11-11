"""Agrandit x4 au plus proche voisin (chaque pixel devient un bloc 4x4, aucun flou) toutes les PNG d'origine
de l'extraction (3_png_pages et 4_icones), en gardant l'arborescence.
Les images deja agrandies (upscayl, *_2.png) sont ignorees.
Usage : python agrandit_x4_ppv.py <dossier_extraction> <dossier_sortie>"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import png_simple

S = 4
src, dst = sys.argv[1], sys.argv[2]
n = 0
for sub in ("3_png_pages", "4_icones"):
    for root, _, files in os.walk(os.path.join(src, sub)):
        for f in sorted(files):
            if not f.lower().endswith(".png") or "upscayl" in f or f.endswith("_2.png"): continue
            w, h, px = png_simple.read(os.path.join(root, f))
            out = bytearray()
            for y in range(h):
                row = bytearray()
                for x in range(w): row += px[(y * w + x) * 4:(y * w + x) * 4 + 4] * S
                out += bytes(row) * S
            d = os.path.join(dst, os.path.relpath(root, src)); os.makedirs(d, exist_ok=True)
            png_simple.write(os.path.join(d, f[:-4] + "_x4.png"), w * S, h * S, out)
            n += 1
            print(f"{os.path.relpath(os.path.join(root, f), src)} {w}x{h} -> {w*S}x{h*S}")
print(n, "images")
