#!/usr/bin/env bash
# Need for Speed ProStreet - Web & Asset Streaming Server
set -euo pipefail
cd "$(dirname "$0")"
python3 tools/serve.py --port 8080 "$@"

