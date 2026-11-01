@echo off
setlocal
cd /d "%~dp0"
echo ===================================================
echo [1/3] Building WebAssembly Recompilation Binary...
echo ===================================================
python tools\build_wasm.py %*
if %ERRORLEVEL% neq 0 (
    echo [ERROR] WebAssembly build failed.
    exit /b %ERRORLEVEL%
)

echo ===================================================
echo [2/3] Building Web Client Bundle...
echo ===================================================
cd web
call npm run build
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Web client build failed.
    exit /b %ERRORLEVEL%
)

echo ===================================================
echo [3/3] Synchronizing WASM artifacts to dist...
echo ===================================================
copy /y public\prostreet.wasm dist\prostreet.wasm
copy /y public\prostreet.json dist\prostreet.json
echo Build completed successfully! Run start.bat to launch.
