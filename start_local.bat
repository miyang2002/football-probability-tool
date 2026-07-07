@echo off
setlocal
cd /d "%~dp0"

py -3 tools\local_launcher.py
if %errorlevel% neq 0 (
  python tools\local_launcher.py
)

pause
