"""Version « distribution » (sous-systeme graphique, sans console) de l'exe US,
d'apres projects/code_veronica/distribution/build.py, limitee a la version US et
aux outils de E:\\Recomp\\Outils. Reutilise les objets du code genere deja
compiles par build_us.cmd (build-release-us) quand leur source est identique.
A lancer depuis build_us_dist.cmd (environnement vcvars)."""
from pathlib import Path
import hashlib, json, os, shutil, subprocess, sys

ROOT = Path(os.environ["CV_SRC"])
TOOLS = Path(os.environ["CV_TOOLS"]).as_posix()
PORT = ROOT / "projects" / "code_veronica"
OUT = PORT / "build-distribution"
OLD = PORT / "build-release-us"

def sha(p):
    with open(p, "rb") as f: return hashlib.file_digest(f, "sha256").hexdigest()

def run(command, log):
    print(" ".join(map(str, command)), flush=True)
    with open(log, "w", encoding="utf-8") as f:
        subprocess.run(list(map(str, command)), stdout=f, stderr=subprocess.STDOUT, check=True)

def main():
    build = OUT / "us"; build.mkdir(parents=True, exist_ok=True)
    objects = []; provenance = []
    for source in sorted((ROOT / "src/recomp_us").glob("ppu_recomp_*.cpp")):
        fresh = build / "verified-lift" / source.name; fresh.parent.mkdir(exist_ok=True)
        run([sys.executable, ROOT / "tools/cv_appearance_hooks.py", "--input", source, "--output", fresh, "--region", "us"],
            build / f"verify-{source.stem}.log")
        saved = OLD / "native_menu_lift" / source.name
        obj = OLD / "CMakeFiles/MyGameRecomp.dir/native_menu_lift" / (source.name + ".obj")
        if not saved.is_file() or sha(saved) != sha(fresh) or not obj.is_file() or obj.stat().st_mtime < saved.stat().st_mtime:
            objects.append(fresh); provenance.append(dict(source=str(source), compiled_fresh=True)); continue
        objects.append(obj); provenance.append(dict(source=str(source), object=str(obj), object_sha256=sha(obj)))
    for source in sorted((PORT / "spu").glob("*/spu_recomp.c")):
        obj = OLD / "CMakeFiles/MyGameRecomp.dir/spu" / source.parent.name / "spu_recomp.c.obj"
        if not obj.is_file() or obj.stat().st_mtime < source.stat().st_mtime: raise RuntimeError(f"Objet SPU perime : {obj}")
        objects.append(obj); provenance.append(dict(source=str(source), object=str(obj)))
    copied = []
    for i, obj in enumerate(objects):
        if obj.suffix == ".cpp": copied.append(obj.as_posix()); continue
        dst = build / "lifted-objects" / f"{i:03}.obj"; dst.parent.mkdir(exist_ok=True)
        shutil.copy2(obj, dst); copied.append(dst.as_posix())
    (build / "reuse.cmake").write_text("set(CV_LIFTED_OBJECTS\n" + "".join(f' "{p}"\n' for p in copied) + ")\n", encoding="utf-8")
    (build / "lift-provenance.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    fresh_count = sum(1 for p in provenance if p.get("compiled_fresh"))
    print(f"unites du code genere : {len(provenance)} ({fresh_count} a recompiler)", flush=True)
    run(["cmake", "-S", PORT / "distribution", "-B", build, "-G", "Ninja", "-DCMAKE_BUILD_TYPE=Release",
         "-DPython3_EXECUTABLE=" + sys.executable, f"-DCMAKE_MAKE_PROGRAM={TOOLS}/Ninja/ninja.exe",
         f"-DCMAKE_C_COMPILER={TOOLS}/LLVM/bin/clang-cl.exe", f"-DCMAKE_CXX_COMPILER={TOOLS}/LLVM/bin/clang-cl.exe",
         f"-DCMAKE_LINKER={TOOLS}/LLVM/bin/lld-link.exe", "-DCMAKE_C_FLAGS_RELEASE=/O2 /Ob2", "-DCMAKE_CXX_FLAGS_RELEASE=/O2 /Ob2",
         "-DCV_REGION=US", f"-DRECOMP_DIR={(ROOT / 'src/recomp_us').as_posix()}", f"-DSPU_DIR={(PORT / 'spu').as_posix()}",
         "-DCV_CPU_COMPAT=OFF"], build / "configure.log")
    run(["cmake", "--build", build, "--target", "MyGameRecomp", "CodeVeronicaLauncher", "-j", os.environ.get("CV_JOBS", "6")],
        build / "build.log")
    exe = OUT / "bin" / "CodeVeronicaPort_US.exe"
    print("OK", exe, sha(exe), flush=True)
    print("OK", OUT / "Code Veronica.exe", sha(OUT / "Code Veronica.exe"), flush=True)

if __name__ == "__main__": main()
