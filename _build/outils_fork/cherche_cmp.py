"""Liste les cmpwi/cmplwi rX,<valeurs> dans une plage d'adresses du code."""
import struct, sys
path, lo, hi = sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3], 16)
vals = [int(v) for v in sys.argv[4].split(",")]
d = open(path, "rb").read()
phoff = struct.unpack_from(">Q", d, 0x20)[0]
off, va, _, fs = struct.unpack_from(">QQQQ", d, phoff + 8)
for a in range(lo, hi, 4):
    w = struct.unpack_from(">I", d, off + a - va)[0]
    op = w >> 26
    if op in (10, 11):   # cmpli / cmpi
        imm = w & 0xFFFF
        if op == 11 and imm & 0x8000: imm -= 0x10000
        if imm in vals:
            print(f"0x{a:08X} {'cmpwi' if op == 11 else 'cmplwi'} cr{(w >> 23) & 7}, r{(w >> 16) & 31}, {imm}")
