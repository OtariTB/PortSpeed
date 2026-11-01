@echo off
setlocal
cd /d "%~dp0\.."
python tools\serve.py --port 8080 %*
exit /b %ERRORLEVEL%

