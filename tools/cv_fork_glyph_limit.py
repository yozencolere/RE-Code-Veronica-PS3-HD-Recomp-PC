"""fork: make the US text code's glyph limit (cmpwi rX,108) a runtime variable.

The European executable compares glyph codes with 108 in English and 162 in
the other languages (its accented letters live in slots 108..161 of the
European font atlas). The US executable only has the English comparisons.
This rewrites exactly these ten lifted comparisons of the US build to read
`cv_glyph_limit` (108 by default, so nothing changes unless
cv_eu_text_metrics_install() raises it to 162).

Idempotent: already patched sites are recognised and counted.
Usage: python cv_fork_glyph_limit.py <src/recomp_us>
"""
import os, re, sys

# (address, compared register) from the US EBOOT, text routines 0x15FE58..0x163000.
SITES = [(0x15FE68, 3), (0x15FF90, 22), (0x160184, 29), (0x16099C, 30), (0x1612F0, 7),
         (0x1613AC, 20), (0x1616F0, 31), (0x161AB4, 31), (0x16204C, 26), (0x162E6C, 27)]
DECL = 'extern "C" int cv_glyph_limit;   /* fork: cv_eu_text_metrics.h */\n'

root = sys.argv[1]
files = sorted(f for f in os.listdir(root) if re.fullmatch(r"ppu_recomp_\d+\.cpp", f))
func_re = re.compile(r"^void func_([0-9A-F]{8})\(ppu_context\* ctx\) \{\r?$", re.M)

# every function start, per file
starts = []
texts = {}
for f in files:
    t = open(os.path.join(root, f), encoding="latin-1", newline="").read()
    texts[f] = t
    for m in func_re.finditer(t):
        starts.append((int(m.group(1), 16), f, m.start()))
starts.sort()

# The lifter can emit the same code twice (e.g. func_0015FE58 in one file and
# func_0015FE60 in another). Each site is patched in every function that
# covers it: per file, the last function starting at or before the address,
# if the next function of that file starts after it.
groups = {}   # (file, function start, text offset, reg) -> sites
for addr, reg in SITES:
    owners = 0
    for f in files:
        fs = [s for s in starts if s[1] == f]
        before = [s for s in fs if s[0] <= addr]
        if not before: continue
        own = max(before, key=lambda s: s[0])
        after = [s for s in fs if s[0] > own[0]]
        if after and min(after, key=lambda s: s[0])[0] <= addr: continue
        groups.setdefault((f, own[0], own[2], reg), []).append(addr); owners += 1
    if not owners: sys.exit(f"0x{addr:08X}: no lifted function covers it")

changed = set()
covered = set()
# patch from the end of each file so earlier offsets stay valid
for (f, fa, pos, reg), addrs in sorted(groups.items(), key=lambda g: (g[0][0], -g[0][2])):
    t = texts[f]
    end = t.find("\nvoid func_", pos + 1)
    body = t[pos:end if end > 0 else len(t)]
    orig = f"int64_t a = (int32_t)ctx->gpr[{reg}]; int64_t b = (int64_t)0x6C;"
    new = f"int64_t a = (int32_t)ctx->gpr[{reg}]; int64_t b = (int64_t)cv_glyph_limit;"
    n_orig, n_new = body.count(orig), body.count(new)
    sites = ", ".join(f"0x{a:08X}" for a in addrs)
    if n_orig + n_new == 0:
        print(f"{f} func_{fa:08X} r{reg} ({sites}): no comparison in this copy, skipped")
        continue
    if n_orig + n_new != len(addrs):
        sys.exit(f"{f} func_{fa:08X} r{reg} ({sites}): {n_orig} original + {n_new} patched, expected {len(addrs)}")
    if n_orig:
        old_len = len(body)
        body = body.replace(orig, new)
        texts[f] = t[:pos] + body + t[pos + old_len:]
        changed.add(f)
    covered.update(addrs)
    print(f"{f} func_{fa:08X} r{reg} ({sites}): {'patched' if n_orig else 'already patched'}")
missing = [a for a, _ in SITES if a not in covered]
if missing: sys.exit("not patched anywhere: " + ", ".join(f"0x{a:08X}" for a in missing))
done = len(SITES)

for f in changed:
    t = texts[f]
    if DECL not in t:
        first = t.find("\n", t.find('#include "ppu_recomp.h"')) + 1
        if first <= 0: sys.exit(f"{f}: no ppu_recomp.h include")
        t = t[:first] + (DECL.replace("\n", "\r\n") if "\r\n" in t[:first] else DECL) + t[first:]
    open(os.path.join(root, f), "w", encoding="latin-1", newline="").write(t)
print(f"{done}/{len(SITES)} sites, {len(changed)} files written")
