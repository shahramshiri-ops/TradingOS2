@echo off
setlocal
cd /d "%~dp0"
call scripts\run_daily_runtime.bat
python scripts\validate_daily_runtime_outputs.py .
endlocal
