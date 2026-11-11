"""Aligne le code texte US et EU (instructions normalisees) et, pour chaque lecture de
constante flottante US (lis/addi + lfs), dit si l'EU la rend dependante de la langue."""
import struct, sys, difflib
sys.path.insert(0, r"E:\Recomp\Code_Veronica_PC\tools")
import ppu_disasm

def load(path):
    d = open(path, "rb").read()
    phoff = struct.unpack_from(">Q", d, 0x20)[0]
    segs = [struct.unpack_from(">QQQQ", d, phoff + i * 0x38 + 8) for i in range(2)]
    def word(a):
        for off, va, _, fs in segs:
            if va <= a < va + fs: return struct.unpack_from(">I", d, off + a - va)[0]
    def flt(a):
        w = word(a); return None if w is None else struct.unpack(">f", struct.pack(">I", w))[0]
    return word, flt

def norm(w):
    op = w >> 26
    if op in (16, 18): return f"br{op}:{(w >> 21) & 31}"       # branches : sans cible
    if op == 15: return f"lis:{(w >> 21) & 31}"                    # lis : sans valeur
    if op in (14, 12) : return f"add{op}:{(w >> 21) & 31}:{(w >> 16) & 31}"
    if op in (48, 34, 32, 50): return f"ld{op}:{(w >> 21) & 31}:{(w >> 16) & 31}"
    return f"{w:08X}"

us_w, us_f = load(sys.argv[1]); eu_w, eu_f = load(sys.argv[2])
US = (0x15E000, 0x163200); EU = (0x15F000, 0x165000)
ua = list(range(US[0], US[1], 4)); ea = list(range(EU[0], EU[1], 4))
un = [norm(us_w(a)) for a in ua]; en = [norm(eu_w(a)) for a in ea]
sm = difflib.SequenceMatcher(None, un, en, autojunk=False)
s16 = lambda x: x - 0x10000 if x & 0x8000 else x

def const_reads(word, addrs):
    """{adresse instruction: adresse constante} pour lis+addi/addic+lfs et lis+lfs"""
    regs = {}; out = {}
    for a in addrs:
        w = word(a); op = w >> 26; rt, ra, imm = (w >> 21) & 31, (w >> 16) & 31, w & 0xFFFF
        if op == 15 and ra == 0: regs[rt] = ((imm << 16) & 0xFFFFFFFF, a)
        elif op in (14, 12) and ra in regs and a - regs[ra][1] < 200: regs[rt] = ((regs[ra][0] + s16(imm)) & 0xFFFFFFFF, a)
        elif op == 48 and ra in regs and a - regs[ra][1] < 200: out[a] = (regs[ra][0] + s16(imm)) & 0xFFFFFFFF
        elif op == 34 and ra in regs and a - regs[ra][1] < 200: out[a] = (regs[ra][0] + s16(imm)) & 0xFFFFFFFF
    return out
ur = const_reads(us_w, ua); er = const_reads(eu_w, ea)
# correspondance instruction US -> instruction EU
m = {}
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == "equal":
        for k in range(i2 - i1): m[ua[i1 + k]] = ea[j1 + k]
    elif tag == "replace" and i2 - i1 == j2 - j1:
        for k in range(i2 - i1): m[ua[i1 + k]] = ea[j1 + k]
print(f"ratio {sm.ratio():.3f}, instructions US appariees {len(m)}/{len(ua)}")
# pour chaque lecture US : l'EU equivalente est-elle dans une branche de langue ?
flag_reads = set()
for a in ea:
    w = eu_w(a)
    if (w >> 26) == 34 and (w & 0xFFFF) == 0x33FC: flag_reads.add(a)
for a, c in sorted(ur.items()):
    e = m.get(a)
    v = us_f(c)
    near = e is not None and any(e - 64 <= f <= e for f in flag_reads)
    ec = er.get(e) if e else None
    tag = "LANGUE?" if near else ""
    if near or e is None:
        print(f"US 0x{a:08X} lit 0x{c:08X}={v}  -> EU {('0x%08X' % e) if e else '??'} lit {('0x%08X=%s' % (ec, eu_f(ec))) if ec else '-'} {tag}")
