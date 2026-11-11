"""Ressources localisables que prepare_archive() ne remplace pas : US != EU-eng mais EU-eng == EU-fra.
Usage : python compare_arc.py <usa> <eu_eng> <eu_fra> [motif]"""
import os, struct, sys, zlib, hashlib
LOCALIZABLE = {0x46c78353: "msg", 0x6a76e771: "msg2", 0x241f5deb: "tex"}

def unwrap(b):
    if len(b) < 4 or struct.unpack_from(">I", b, 0)[0] != 0x00534648: return b
    expected = struct.unpack_from(">I", b, 8)[0]; out = bytearray(); at = 0
    while at < len(b) and len(out) < expected:
        n = min(0x1fff0, len(b) - at - 16, expected - len(out)); out += b[at + 16: at + 16 + n]; at += 0x20000
    return bytes(out)

def load(path):
    arc = unwrap(open(path, "rb").read())
    if struct.unpack_from(">I", arc, 0)[0] != 0x00435241: return {}
    count = struct.unpack_from(">H", arc, 6)[0]; res = {}
    for i in range(count):
        a = 8 + i * 80
        name = arc[a:a + 64].split(b"\0")[0].decode("latin-1")
        typ, comp, cap, off = struct.unpack_from(">IIII", arc, a + 64)
        raw = arc[off: off + comp]
        try: data = zlib.decompress(raw) if len(raw) >= 6 and (raw[0] & 15) == 8 and ((raw[0] << 8 | raw[1]) % 31) == 0 else raw
        except zlib.error: data = raw
        for loc in ("eng", "fra", "ger", "ita", "spa", "usa"):
            name = name.replace("biocv_tmp\\" + loc + "\\", "biocv_tmp\\usa\\")
        res[(name, typ)] = data.replace(b"biocv_tmp\\eng\\", b"biocv_tmp\\usa\\").replace(b"biocv_tmp\\fra\\", b"biocv_tmp\\usa\\")
    return res

usa, eng, fra = sys.argv[1:4]; motif = sys.argv[4] if len(sys.argv) > 4 else ""
h = lambda b: hashlib.sha1(b).hexdigest()[:10]
for dp, dn, fn in os.walk(fra):
    for f in fn:
        if not f.endswith(".arc"): continue
        rel = os.path.relpath(os.path.join(dp, f), fra)
        if motif and motif not in rel: continue
        pu, pe = os.path.join(usa, rel), os.path.join(eng, rel)
        if not (os.path.isfile(pu) and os.path.isfile(pe)): continue
        try: U, E, F = load(pu), load(pe), load(os.path.join(fra, rel))
        except Exception as ex: print("ERREUR", rel, ex); continue
        for k, u in U.items():
            if k[1] not in LOCALIZABLE or k not in E or k not in F: continue
            if h(u) != h(E[k]) and h(E[k]) == h(F[k]):
                print(f"{rel}: {LOCALIZABLE[k[1]]} {k[0]} (US {len(u)} o, EU {len(E[k])} o) -> NON remplace")
