"""Decode le premier niveau d'une texture XET 512x512 (DXT1 0x14 / DXT5 0x18) en PNG (alpha sur fond noir)."""
import struct, sys, zlib
def c565(v): return ((v >> 11 & 31) * 255 // 31, (v >> 5 & 63) * 255 // 63, (v & 31) * 255 // 31)
def decode(d):
    fmt = d[14]; off = struct.unpack_from(">I", d, 0x10)[0]
    w = struct.unpack_from(">H", d, 8)[0] >> 3; h = d[10] << 2
    bs = 8 if fmt == 0x14 else 16
    px = bytearray(w * h * 3)
    for by in range(h // 4):
        for bx in range(w // 4):
            b = off + (by * (w // 4) + bx) * bs
            alpha = [255] * 16
            if fmt == 0x18:
                a0, a1 = d[b], d[b + 1]; bits = int.from_bytes(d[b + 2:b + 8], "little")
                pal = [a0, a1] + ([((6 - i) * a0 + i * a1) // 7 for i in range(1, 7)] if a0 > a1 else [((4 - i) * a0 + i * a1) // 5 for i in range(1, 5)] + [0, 255])
                alpha = [pal[(bits >> (3 * i)) & 7] for i in range(16)]; c = b + 8
            else: c = b
            v0, v1 = struct.unpack_from("<HH", d, c); idx = struct.unpack_from("<I", d, c + 4)[0]
            k0, k1 = c565(v0), c565(v1)
            if v0 > v1 or fmt == 0x18: pal = [k0, k1, tuple((2 * a + b2) // 3 for a, b2 in zip(k0, k1)), tuple((a + 2 * b2) // 3 for a, b2 in zip(k0, k1))]
            else: pal = [k0, k1, tuple((a + b2) // 2 for a, b2 in zip(k0, k1)), (0, 0, 0)]
            for i in range(16):
                col = pal[(idx >> (2 * i)) & 3]; a = alpha[i]
                x, y = bx * 4 + i % 4, by * 4 + i // 4; p = (y * w + x) * 3
                px[p:p + 3] = bytes(v * a // 255 for v in col)
    return w, h, px
def png(path, w, h, px):
    raw = b"".join(b"\0" + bytes(px[y * w * 3:(y + 1) * w * 3]) for y in range(h))
    ch = lambda t, x: struct.pack(">I", len(x)) + t + x + struct.pack(">I", zlib.crc32(t + x))
    open(path, "wb").write(b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + ch(b"IDAT", zlib.compress(raw)) + ch(b"IEND", b""))
for src in sys.argv[1:]:
    png(src.rsplit(".", 1)[0] + ".png", *decode(open(src, "rb").read()))
    print("ok", src)
