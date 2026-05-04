@echo off
setlocal
cd /d "%~dp0\.."
python scripts\run_post_refresh_candidate_lifecycle_update.py .
endlocal
