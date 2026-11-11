@echo off
rem Version distribution (sans console) de l'exe US + "Code Veronica.exe".
rem Variables attendues : CV_SRC, CV_TOOLS, CV_PYTHON, CV_JOBS.
setlocal
if not defined CV_SRC exit /b 10
if not defined CV_TOOLS exit /b 10
if not defined CV_PYTHON exit /b 10
if not defined CV_JOBS set "CV_JOBS=6"
call "%CV_TOOLS%\VS2022BuildTools\VC\Auxiliary\Build\vcvars64.bat" || exit /b 11
for %%I in ("%CV_PYTHON%") do set "CV_PYDIR=%%~dpI"
set "PATH=%CV_PYDIR%;%CV_TOOLS%\LLVM\bin;%CV_TOOLS%\CMake\bin;%CV_TOOLS%\Ninja;%PATH%"
"%CV_PYTHON%" "%CV_SRC%\_build\build_us_dist.py" || exit /b 14
exit /b 0
