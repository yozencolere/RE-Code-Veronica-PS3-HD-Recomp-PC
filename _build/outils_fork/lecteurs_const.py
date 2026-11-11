"""Compte les lectures (lis+addi/addic puis lfs off(r)) ou (lis puis lfs off(r)) d'adresses absolues."""
import struct, sys
path = sys.argv[1]; targets = [int(x, 16) for x in sys.argv[2].split(",")]
d = open(path, "rb").read()
phoff = struct.unpack_from(">Q", d, 0x20)[0]
off, va, _, fs = struct.unpack_from(">QQQQ", d, phoff + 8)
s16 = lambda x: x - 0x10000 if x & 0x8000 else x
regs = {}; hits = {t: [] for t in targets}
for k in range(0, fs - 3, 4):
    w = struct.unpack_from(">I", d, off + k)[0]; op = w >> 26
    rt, ra, imm = (w >> 21) & 31, (w >> 16) & 31, w & 0xFFFF
    a = va + k
    if op == 18 and not (w & 1) and False: pass
    if op == 15 and ra == 0: regs[rt] = ((imm << 16) & 0xFFFFFFFF, a); continue
    if op in (14, 12) and ra in regs and a - regs[ra][1] < 256:
        regs[rt] = ((regs[ra][0] + s16(imm)) & 0xFFFFFFFF, a); continue
    if op in (48, 50) and ra in regs and a - regs[ra][1] < 256:   # lfs / lfd
        ea = (regs[ra][0] + s16(imm)) & 0xFFFFFFFF
        if ea in hits: hits[ea].append(hex(a))
    if op == 31 and ((w >> 1) & 0x3FF) == 535 and ra in regs:   # lfsx
        pass
for t in targets: print(hex(t), len(hits[t]), hits[t][:12])
