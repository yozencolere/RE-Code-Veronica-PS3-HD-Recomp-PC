#!/usr/bin/env python3
"""Generate the Code Veronica SPU folder from the AMERICAN EBOOT.elf (NPUB30467).

    python tools/cv_make_spu_us.py <EBOOT.elf> [--out projects/code_veronica/spu]

tools/cv_make_spu.py holds the European addresses. In the American executable
the same SPU images and the same three SPURS job binaries (identical FNV-1a-64
hashes, checked by cv_make_spu before anything is lifted) sit 0x2A00 lower.
This wrapper only shifts those addresses; every step is cv_make_spu's own.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cv_make_spu as m

US_DELTA = -0x2A00


def _shift_name(name):
    # "spu_0019_at_00A25400..." -> same image, American offset
    head, _, tail = name.partition("_at_")
    addr, rest = tail[:8], tail[8:]
    return f"{head}_at_{int(addr, 16) + US_DELTA:08X}{rest}"


m.JOBS = [(v + US_DELTA, *rest) for v, *rest in m.JOBS]
m.EXTRA_FUNCS = [_shift_name(e) for e in m.EXTRA_FUNCS]
m.PLUGIN_SRC = _shift_name(m.PLUGIN_SRC)

if __name__ == "__main__":
    try:
        sys.exit(m.main())
    except m.Fail as e:
        print("ERROR: " + str(e))
        sys.exit(1)
