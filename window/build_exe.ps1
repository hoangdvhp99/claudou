# Build Claudou.exe with PyInstaller.
# Usage: .\build_exe.ps1 [-Install]
param([switch]$Install)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if ($Install) {
    pip install -r requirements.txt pyinstaller
}
if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    Write-Host "pyinstaller not found. Re-run with -Install." -ForegroundColor Red
    exit 1
}

# App icon (.ico): same sharpened multi-size frames the app uses at runtime
$ico = python -c "from claudou.ui import _icon_file; print(_icon_file())"

$ctk = python -c "import customtkinter, os; print(os.path.dirname(customtkinter.__file__))"

pyinstaller --noconfirm --onefile --windowed --name Claudou `
    --icon $ico `
    --add-data "$ctk;customtkinter/" `
    --add-data "..\assets;assets" `
    --add-data "..\VERSION;." `
    --hidden-import pystray._win32 `
    main.py

if ($LASTEXITCODE -eq 0) { Write-Host "Built: dist\Claudou.exe" -ForegroundColor Green }
else { Write-Host "Build failed" -ForegroundColor Red; exit 1 }
