@echo off
setlocal
cd /d "%~dp0\.."
echo PRV1C plan-only check starting...
python scripts\run_staged_credentialed_refresh.py --package-root . --plan-only
echo.
echo Review reports\staged_refresh_plan.json
endlocal
