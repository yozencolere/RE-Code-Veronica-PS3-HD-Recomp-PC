@echo off
rem Compilation de la version americaine (NPUB30467) avec les outils de E:\Recomp\Outils.
rem Memes options que projects\code_veronica\build-release.cmd (bloc CV_BUILD_US),
rem sans dependre de C:\Program Files\LLVM ni de vswhere.
rem Variables attendues : CV_SRC, CV_TOOLS, CV_PYTHON, CV_JOBS.
setlocal
if not defined CV_SRC exit /b 10
if not defined CV_TOOLS exit /b 10
if not defined CV_PYTHON exit /b 10
if not defined CV_JOBS set "CV_JOBS=6"

call "%CV_TOOLS%\VS2022BuildTools\VC\Auxiliary\Build\vcvars64.bat" || exit /b 11

for %%I in ("%CV_PYTHON%") do set "CV_PYDIR=%%~dpI"
set "PATH=%CV_PYDIR%;%CV_TOOLS%\LLVM\bin;%CV_TOOLS%\CMake\bin;%CV_TOOLS%\Ninja;%PATH%"

cd /d "%CV_SRC%\projects\code_veronica" || exit /b 12

set "R=%CV_SRC:\=/%"
set "T=%CV_TOOLS:\=/%"
set "P=%CV_PYTHON:\=/%"

echo ==== versions ====
clang-cl --version
cmake --version
ninja --version
python --version
echo ==================

if exist build-release-us\CMakeCache.txt goto build
cmake -S . -B build-release-us -G Ninja ^
 -DCMAKE_BUILD_TYPE=Release ^
 "-DCMAKE_MAKE_PROGRAM=%T%/Ninja/ninja.exe" ^
 "-DCMAKE_C_COMPILER=%T%/LLVM/bin/clang-cl.exe" ^
 "-DCMAKE_CXX_COMPILER=%T%/LLVM/bin/clang-cl.exe" ^
 "-DCMAKE_LINKER=%T%/LLVM/bin/lld-link.exe" ^
 "-DCMAKE_C_FLAGS_RELEASE=/O2 /Ob2" ^
 "-DCMAKE_CXX_FLAGS_RELEASE=/O2 /Ob2" ^
 "-DPython3_EXECUTABLE=%P%" ^
 "-DPS3RECOMP_DIR=%R%" ^
 "-DRECOMP_DIR=%R%/src/recomp_us" ^
 -DCV_REGION=US ^
 "-DSPU_DIR=%R%/projects/code_veronica/spu" ^
 -DPORT_ENABLE_SPU=ON ^
 -DPS3RECOMP_BUILD_TESTS=OFF ^
 "-DCMAKE_RUNTIME_OUTPUT_DIRECTORY=%R%/projects/code_veronica/build-release/bin"
if errorlevel 1 exit /b 13

:build
cmake --build build-release-us -j %CV_JOBS%
if errorlevel 1 exit /b 14
exit /b 0
