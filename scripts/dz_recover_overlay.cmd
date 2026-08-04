@echo off
rem Recuperation de l'overlay MSIX — a lancer HORS conteneur (explorer/schtasks).
echo === DEEPOTUS - recuperation overlay MSIX (ne pas fermer) ===
"%LOCALAPPDATA%\DeepotusVideoGen\runtime\python\python.exe" "%~dp0dz_recover_overlay.py"
echo === Termine - rapport: %USERPROFILE%\dz_recovery_report.txt ===
