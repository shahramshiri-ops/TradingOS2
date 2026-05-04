@echo off
setlocal
cd /d "%~dp0"
python scripts\validate_daily_runtime_outputs.py .
endlocal
