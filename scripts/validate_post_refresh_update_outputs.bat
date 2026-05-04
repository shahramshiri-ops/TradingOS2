@echo off
setlocal
cd /d "%~dp0\.."
python scripts\validate_post_refresh_update_outputs.py .
endlocal
