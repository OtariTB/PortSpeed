@echo off
REM Need for Speed ProStreet - WebAssembly Build Runner (Windows)
setlocal
cd /d "%~dp0"
python tools\build_wasm.py %*
exit /b %ERRORLEVEL%

