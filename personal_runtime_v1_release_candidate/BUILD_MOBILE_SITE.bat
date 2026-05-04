@echo off
setlocal
cd /d "%~dp0"
python scripts\generate_mobile_pages_site.py --package-root . --site-dir site_local_preview
endlocal
