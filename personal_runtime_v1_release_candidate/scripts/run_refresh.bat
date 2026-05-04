@echo off
setlocal
REM PRV1-01 Personal Runtime V1 — cache-first dry-run refresh.
REM This does not fetch live data, read API keys, connect to a broker, create orders, generate signals, or compute PnL.
cd /d "%~dp0\.."
python scripts\run_refresh.py --package-root . --print-summary
python scripts\check_runtime_status.py --package-root .
endlocal
