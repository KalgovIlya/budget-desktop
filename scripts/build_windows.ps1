$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

$py = Join-Path $PWD ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
  python -m venv .venv
  & $py -m pip install -r requirements.txt
}

& $py -m pip install -q pyinstaller
& $py -m PyInstaller --noconfirm --clean --windowed --onefile `
  --name Budget `
  --icon assets\budget.ico `
  --add-data "assets;assets" `
  --collect-all PySide6 `
  src/main.py

Write-Host "Built: dist\Budget.exe"
