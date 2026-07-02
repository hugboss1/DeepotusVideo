@echo off
rem Deepotus Video Gen - double-click this on the NEW PC to restore everything.
rem (app + generations + calendar + keys + Claude Code sessions)
title Deepotus Video Gen - Import
powershell -ExecutionPolicy Bypass -NoProfile -File "%~dp0import-all.ps1" -Src "%~dp0."
echo.
pause
