@echo off
rem Wrapper execute HORS conteneur MSIX quand lance via explorer.exe / schtasks.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0dz_probe_real_dataroot.ps1"
