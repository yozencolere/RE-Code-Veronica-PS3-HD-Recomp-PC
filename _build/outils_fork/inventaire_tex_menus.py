"""Liste les textures XET des archives de menus (usa et fra) et l'en-tete des .tex systeme.
Usage : python inventaire_tex_menus.py <racine nativePS3 US> <racine biocv_disc EU>"""
import os, sys, struct
here = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(here, "compare_arc.py")).read().split("usa, eng, fra = sys.argv")[0]
ns = {}; exec(src, ns)
us, eu = sys.argv[1], sys.argv[2]
ARCS = [r"adv\boot.arc", r"adv\opt.arc", r"adv\screen_setting.arc", r"adv\title.arc", r"adv\capcom_logo_tex.arc",
        r"adv\vs_mpsel_tex.arc", r"window\button_guide.arc", r"window\window0_0.arc", r"window\window2_0.arc",
        r"on_manual\on_manual.arc", r"system\compevt_tex.arc"]
for rel in ARCS:
    for tag, path in (("usa", os.path.join(us, "biocv_disc", "usa", rel)), ("fra", os.path.join(eu, "fra", rel))):
        if not os.path.isfile(path): print(tag, rel, "absent"); continue
        R = ns["load"](path)
        for (name, typ), d in R.items():
            if typ != 0x241f5deb: continue
            print(tag, rel, name.split("\\")[-1], len(d), d[:0x20].hex())
for f in (r"system\font\Gothic_AM_NOMIP.tex", r"system\texture\nrodinpro_BM_HQ_NOMIP.tex",
          r"system\texture\sysfont2_AM_NOMIP.tex", r"system\texture\sysfont_AM_NOMIP.tex"):
    d = open(os.path.join(us, f), "rb").read()
    print("tex", f, len(d), d[:0x40].hex())
