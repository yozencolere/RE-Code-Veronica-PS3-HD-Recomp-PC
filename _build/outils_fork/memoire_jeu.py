"""Lecture de la memoire invitee du jeu de test (lecture seule, ReadProcessMemory).
  python memoire_jeu.py instantane <fichier>      : copie les zones invitees engagees (< 0x40000000)
  python memoire_jeu.py cherche <f1> <f2> ...     : octets / mots dont la valeur suit la suite attendue (--suite 3,2,1,0)
  python memoire_jeu.py lit <adresse_hex> [n]     : lit n octets a une adresse invitee"""
import ctypes, ctypes.wintypes as W, pickle, struct, subprocess, sys

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
class MBI(ctypes.Structure):
    _fields_ = [("BaseAddress", ctypes.c_void_p), ("AllocationBase", ctypes.c_void_p), ("AllocationProtect", W.DWORD),
                ("PartitionId", W.WORD), ("RegionSize", ctypes.c_size_t), ("State", W.DWORD), ("Protect", W.DWORD), ("Type", W.DWORD)]
k32.OpenProcess.restype = W.HANDLE
k32.VirtualQueryEx.argtypes = [W.HANDLE, ctypes.c_void_p, ctypes.POINTER(MBI), ctypes.c_size_t]
k32.ReadProcessMemory.argtypes = [W.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]

def pid():
    out = subprocess.run(["powershell", "-NoProfile", "-Command",
        "(Get-Process CodeVeronicaPort_US | Where-Object { $_.Path -like 'E:\\Recomp\\Test_CV\\*' } | Select-Object -First 1).Id"],
        capture_output=True, text=True).stdout.strip()
    return int(out)

def regions(h):
    a = 0; m = MBI()
    while k32.VirtualQueryEx(h, ctypes.c_void_p(a), ctypes.byref(m), ctypes.sizeof(m)):
        yield m.BaseAddress or 0, m.AllocationBase or 0, m.RegionSize, m.State
        a = (m.BaseAddress or 0) + m.RegionSize
        if a >= 1 << 47: break

def read(h, addr, n):
    buf = ctypes.create_string_buffer(n); got = ctypes.c_size_t()
    if not k32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, n, ctypes.byref(got)): return None
    return buf.raw[:got.value]

def guest_base(h):
    spans = {}
    for b, ab, sz, st in regions(h):
        lo, hi = spans.get(ab, (b, b + sz)); spans[ab] = (min(lo, b), max(hi, b + sz))
    for ab, (lo, hi) in sorted(spans.items()):
        if hi - lo >= 0xF0000000:
            hdr = read(h, ab + 0x10000, 4)
            if hdr == b"\x7fELF": return ab
    raise SystemExit("base invitee introuvable")

def open_game():
    h = k32.OpenProcess(0x0410, False, pid())   # QUERY_INFORMATION | VM_READ
    if not h: raise SystemExit("OpenProcess a echoue")
    return h, guest_base(h)

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "instantane":
        h, base = open_game(); snap = {}
        for b, ab, sz, st in regions(h):
            if st != 0x1000 or b < base or b + sz > base + 0x60000000: continue
            d = read(h, b, sz)
            if d: snap[b - base] = d
        pickle.dump(snap, open(sys.argv[2], "wb"))
        print("base 0x%X, %d zones, %.1f Mo" % (base, len(snap), sum(map(len, snap.values())) / 2**20))
    elif cmd == "lit":
        h, base = open_game(); a = int(sys.argv[2], 16); n = int(sys.argv[3]) if len(sys.argv) > 3 else 16
        print(read(h, base + a, n).hex(" "))
    elif cmd == "cherche":
        args = sys.argv[2:]; suite = [3, 2, 1, 0]
        if "--suite" in args: i = args.index("--suite"); suite = [int(x) for x in args[i + 1].split(",")]; del args[i:i + 2]
        snaps = [pickle.load(open(f, "rb")) for f in args]
        assert len(snaps) == len(suite)
        for off, d0 in sorted(snaps[0].items()):
            ds = [s.get(off) for s in snaps]
            if any(d is None or len(d) != len(d0) for d in ds): continue
            for p in range(0, len(d0), 4096):
                pages = [d[p:p + 4096] for d in ds]
                if all(x == pages[0] for x in pages[1:]): continue
                for j in range(len(pages[0])):
                    if [pg[j] for pg in pages] == suite: print("octet 0x%08X" % (off + p + j))
                for j in range(0, len(pages[0]) - 3, 4):
                    if [struct.unpack_from(">I", pg, j)[0] for pg in pages] == suite: print("mot32 0x%08X" % (off + p + j))
                for j in range(0, len(pages[0]) - 1, 2):
                    if [struct.unpack_from(">H", pg, j)[0] for pg in pages] == suite: print("mot16 0x%08X" % (off + p + j))
