#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
echo "==================================================="
echo "[1/3] Building WebAssembly Recompilation Binary..."
echo "==================================================="
python3 tools/build_wasm.py "$@"

echo "==================================================="
echo "[2/3] Building Web Client Bundle..."
echo "==================================================="
cd web
npm run build

echo "==================================================="
echo "[3/3] Synchronizing WASM artifacts to dist..."
echo "==================================================="
cp -f public/prostreet.wasm dist/prostreet.wasm
cp -f public/prostreet.json dist/prostreet.json
echo "Build completed successfully! Run ./start.sh to launch."
