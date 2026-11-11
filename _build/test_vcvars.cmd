@echo off
rem Code 0 si le vcvars64.bat donne en argument fournit un environnement complet.
if not exist "%~1" exit /b 1
call "%~1" >nul 2>nul
if errorlevel 1 exit /b 1
if not defined VCToolsInstallDir exit /b 1
if not defined WindowsSdkDir exit /b 1
where rc.exe >nul 2>nul
if errorlevel 1 exit /b 1
where mt.exe >nul 2>nul
if errorlevel 1 exit /b 1
exit /b 0
