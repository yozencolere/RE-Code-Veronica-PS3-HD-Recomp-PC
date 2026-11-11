"""Decoupe une zone d'un BMP 24/32 bits (bas en haut) vers PNG."""
import sys, struct, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import png_simple
src, dst, x0, y0, x1, y1 = sys.argv[1], sys.argv[2], *map(int, sys.argv[3:7])
d = open(src, 'rb').read(); off = struct.unpack_from('<I', d, 10)[0]
w, h = struct.unpack_from('<ii', d, 18); bpp = struct.unpack_from('<H', d, 28)[0] // 8
stride = (w * bpp + 3) & ~3; out = bytearray()
for y in range(y0, y1):
    row = (h - 1 - y) if h > 0 else y; base = off + row * stride
    for x in range(x0, x1):
        p = base + x * bpp; out += bytes((d[p + 2], d[p + 1], d[p], 255))
png_simple.write(dst, x1 - x0, y1 - y0, out)
