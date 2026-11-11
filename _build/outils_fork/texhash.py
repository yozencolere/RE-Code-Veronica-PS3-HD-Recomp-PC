"""texpack_hash (libs/video/rsx_texture_pack.c) en Python, pour nommer une texture
comme le fait le dump. Usage : python texhash.py fichier.arc nom_ressource fmt"""
import os, sys, struct
M = (1 << 64) - 1
def rotl(v, r): return ((v << r) | (v >> (64 - r))) & M
def texpack_hash(b, w, h, fmt):
    n = len(b)
    x = 0x9E3779B97F4A7C15 ^ ((n * 0xC2B2AE3D27D4EB4F) & M) ^ ((w << 40) | (h << 16) | fmt)
    i = 0
    while i + 8 <= n:
        v = struct.unpack_from("<Q", b, i)[0]
        x ^= (rotl((v * 0x87C37B91114253D5) & M, 31) * 0x4CF5AD432745937F) & M
        x = (rotl(x, 27) * 5 + 0x52DCE729) & M
        i += 8
    while i < n:
        x ^= (b[i] * 0x9E3779B97F4A7C15) & M; x = (rotl(x, 11) * 0x87C37B91114253D5) & M; i += 1
    x ^= x >> 33; x = (x * 0xFF51AFD7ED558CCD) & M; x ^= x >> 33; x = (x * 0xC4CEB9FE1A85EC53) & M; x ^= x >> 33
    return x or 1
if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    src = open(os.path.join(here, "compare_arc.py")).read().split("usa, eng, fra = sys.argv")[0]
    ns = {}; exec(src, ns)
    R = ns["load"](sys.argv[1])
    for (n, t), d in R.items():
        if n.endswith(sys.argv[2]) and t == 0x241f5deb:
            w = struct.unpack_from(">H", d, 8)[0] >> 3; h = d[10] << 2; off = struct.unpack_from(">I", d, 0x10)[0]
            payload = d[off:]
            print(n, w, h, len(payload), "%016X" % texpack_hash(payload, w, h, int(sys.argv[3], 0)), payload[:16].hex())
