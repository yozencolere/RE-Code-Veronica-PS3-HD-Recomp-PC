import struct, sys
def load(path):
    d = open(path, "rb").read()
    phoff, phnum = struct.unpack_from(">Q", d, 0x20)[0], struct.unpack_from(">H", d, 0x38)[0]
    segs = []
    for i in range(phnum):
        p = phoff + i * 0x38
        typ, = struct.unpack_from(">I", d, p)
        off, va, _, fsz = struct.unpack_from(">QQQQ", d, p + 8)
        if typ == 1: segs.append((va, off, fsz))
    def rd(va, n):
        for v, o, s in segs:
            if v <= va and va + n <= v + s: return d[o + va - v: o + va - v + n]
        raise KeyError(hex(va))
    return rd
us = load(sys.argv[1]); eu = load(sys.argv[2])
def show(name, b):
    print(name)
    for i in range(0, len(b), 32): print(f"  {i:3d}: " + " ".join(f"{x:2d}" for x in b[i:i+32]))
show("US 0x8780BC (proportionnelle) 0..300", us(0x8780BC, 300))
show("EU 0x87A308 (proportionnelle) 0..300", eu(0x87A308, 300))
