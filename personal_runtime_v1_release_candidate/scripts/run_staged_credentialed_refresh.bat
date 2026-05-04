@echo off
setlocal
cd /d "%~dp0\.."
echo PRV1C staged credentialed read-only refresh starting...
python scripts\run_staged_credentialed_refresh.py --package-root .
echo.
echo PRV1C staged refresh finished. Review proofs\staged_refresh_local_validation_result.json
endlocal
