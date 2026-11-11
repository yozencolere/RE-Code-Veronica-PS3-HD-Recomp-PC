@echo off
rem Compile le test des archives de langue (code_veronica_native_language_tests).
call "%CV_TOOLS%\VS2022BuildTools\VC\Auxiliary\Build\vcvars64.bat" || exit /b 11
for %%I in ("%CV_PYTHON%") do set "CV_PYDIR=%%~dpI"
set "PATH=%CV_PYDIR%;%CV_TOOLS%\LLVM\bin;%CV_TOOLS%\CMake\bin;%CV_TOOLS%\Ninja;%PATH%"
cmake --build "%CV_SRC%\projects\code_veronica\build-release-us" --target code_veronica_native_language_tests || exit /b 13
