"""Compare une archive .arc US et sa version adaptee (cache LANGUAGE-US), entree par entree, sans normaliser.
Usage : python compare_salle.py <arc_us> <arc_adaptee>"""
import struct, sys, zlib, hashlib

def unwrap(b):
    if len(b) < 4 or struct.unpack_from(">I", b, 0)[0] != 0x00534648: return b, False
    expected = struct.unpack_from(">I", b, 8)[0]; out = bytearray(); at = 0
    while at < len(b) and len(out) < expected:
        n = min(0x1fff0, len(b) - at - 16, expected - len(out)); out += b[at + 16: at + 16 + n]; at += 0x20000
    return bytes(out), True

def load(path):
    arc, wrapped = unwrap(open(path, "rb").read())
    head = arc[:8]; count = struct.unpack_from(">H", arc, 6)[0]; res = []
    for i in range(count):
        a = 8 + i * 80
        name = arc[a:a + 64].split(b"\0")[0].decode("latin-1")
        typ, comp, cap, off = struct.unpack_from(">IIII", arc, a + 64)
        raw = arc[off: off + comp]
        try: data = zlib.decompress(raw) if len(raw) >= 6 and (raw[0] & 15) == 8 and ((raw[0] << 8 | raw[1]) % 31) == 0 else raw
        except zlib.error: data = raw
        res.append(dict(name=name, typ=typ, comp=comp, cap=cap, off=off, data=data, zipped=data is not raw))
    return dict(head=head, wrapped=wrapped, size=len(arc), res=res)

A, B = load(sys.argv[1]), load(sys.argv[2])
print("entete", A["head"].hex(), B["head"].hex(), "enveloppe", A["wrapped"], B["wrapped"], "taille", A["size"], B["size"])
print("ressources", len(A["res"]), len(B["res"]))
h = lambda b: hashlib.sha1(b).hexdigest()[:10]
for i, (x, y) in enumerate(zip(A["res"], B["res"])):
    diff = []
    for k in ("name", "typ", "cap"):
        if x[k] != y[k]: diff.append(f"{k}: {x[k]!r} -> {y[k]!r}")
    if x["zipped"] != y["zipped"]: diff.append(f"compression {x['zipped']} -> {y['zipped']}")
    if x["data"] != y["data"]: diff.append(f"donnees {len(x['data'])} {h(x['data'])} -> {len(y['data'])} {h(y['data'])}")
    print(f"{i:3} {x['typ']:08x} {x['name'][:48]:48} " + ("identique" if not diff else " | ".join(diff)))
