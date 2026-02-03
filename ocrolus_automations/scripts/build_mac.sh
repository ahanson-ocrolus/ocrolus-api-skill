#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

ENTRYPOINT=${1:-"src/ocrolus_automations/gui.py"}
APP_NAME=${2:-"Transfer Book Automation"}
CLEAN=${3:-""}

if [[ "$CLEAN" == "--clean" ]]; then
  rm -rf build dist
fi

python3 -m PyInstaller --onefile --windowed -n "$APP_NAME" "$ENTRYPOINT"

echo "Build complete. Output: dist/$APP_NAME"
