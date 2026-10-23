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

# App icon (.ico) generated from the shared logo
$ico = Join-Path $env:TEMP "claudou.ico"
python -c "from PIL import Image; Image.open(r'..\assets\logo.png').convert('RGBA').save(r'$ico', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])"

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
