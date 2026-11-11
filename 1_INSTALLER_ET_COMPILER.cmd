@echo off
rem Double-clic : installe les outils dans E:\Recomp\Outils, genere le code du jeu
rem et compile la version US. Demande les droits administrateur (installeurs).
rem Relancable : ce qui est deja fait est saute.
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','%~dp0_build\installer_et_compiler.ps1'"
