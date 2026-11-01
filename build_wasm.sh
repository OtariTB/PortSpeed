#!/usr/bin/env bash
# Need for Speed ProStreet - WebAssembly Build Runner (POSIX)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
python3 tools/build_wasm.py "$@"

