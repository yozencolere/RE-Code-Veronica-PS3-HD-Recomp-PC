"""Toutes les adresses construites par lis+addi/ori/lbz/lwz dans [cible-0x400, cible+0x400]."""
import struct, sys
from collections import Counter
path, target = sys.argv[1], int(sys.argv[2], 16)
d = open(path, "rb").read()
phoff = struct.unpack_from(">Q", d, 0x20)[0]
off, va, _, fs = struct.unpack_from(">QQQQ", d, phoff + 8)
names = {14: "addi", 24: "ori", 34: "lbz", 32: "lwz", 40: "lhz", 36: "stw", 48: "lfs"}
found = Counter(); first = {}
lis = {}   # registre -> (valeur haute, position)
for i in range(0, fs - 3, 4):
    w = struct.unpack_from(">I", d, off + i)[0]
    op = w >> 26
    if op == 15 and ((w >> 16) & 31) == 0:
        lis[(w >> 21) & 31] = ((w & 0xFFFF) << 16, i); continue
    if op in names:
        ra = (w >> 16) & 31
        if ra in lis and i - lis[ra][1] <= 48:
            imm = w & 0xFFFF
            a = (lis[ra][0] | imm) if op == 24 else (lis[ra][0] + (imm - 0x10000 if imm & 0x8000 else imm)) & 0xFFFFFFFF
            if abs(a - target) <= 0x400:
                found[(names[op], a)] += 1; first.setdefault((names[op], a), va + i)
for (n, a), c in sorted(found.items(), key=lambda x: x[0][1]):
    print(f"{n:5s} 0x{a:08X} (cible{a - target:+d}) x{c}, premiere a 0x{first[(n, a)]:08X}")
