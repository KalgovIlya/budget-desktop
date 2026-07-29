#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PY="${PWD}/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  python3 -m venv .venv
  PY="${PWD}/.venv/bin/python"
  "$PY" -m pip install -r requirements.txt
fi

"$PY" -m pip install -q pyinstaller
"$PY" -m PyInstaller --noconfirm --clean --windowed --onefile \
  --name Budget \
  --icon assets/budget.ico \
  --add-data "assets:assets" \
  --collect-all PySide6 \
  src/main.py

echo "Built: dist/Budget"
echo "Run:   ./dist/Budget"
