@echo off
setlocal
cd /d "%~dp0\.."
echo PRV1B cautious one-surface credentialed read-only refresh starting...
python scripts\credentialed_refresh_preflight.py --package-root . --print-summary
if errorlevel 1 (
  echo Preflight failed or caveated. Review reports\credentialed_refresh_preflight_report.json
  exit /b 2
)
python scripts\credentialed_refresh_runner.py --package-root . --max-surfaces 1 --print-summary
if errorlevel 1 (
  echo Credentialed refresh failed or requires review. Check reports and proofs.
  exit /b 3
)
python scripts\validate_credentialed_refresh_outputs.py .
echo PRV1B cautious one-surface credentialed read-only refresh completed.
echo Open panel\index_credentialed_refresh.html
endlocal
