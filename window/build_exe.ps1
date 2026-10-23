# build_exe.ps1 - Build Claudou thành file .exe
# Yêu cầu: pip install pyinstaller

param(
    [switch]$Install   # Truyền -Install để auto cài pyinstaller
)

Write-Host "=== Claudou Builder ===" -ForegroundColor Cyan

if ($Install) {
    Write-Host "Cài đặt pyinstaller..." -ForegroundColor Yellow
    pip install pyinstaller --quiet
}

# Kiểm tra pyinstaller
if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    Write-Host "Lỗi: pyinstaller chưa được cài. Chạy lại với -Install" -ForegroundColor Red
    exit 1
}

# Lấy path customtkinter để include assets
$ctk_path = python -c "import customtkinter; import os; print(os.path.dirname(customtkinter.__file__))"

Write-Host "customtkinter path: $ctk_path" -ForegroundColor Gray

# Build
pyinstaller `
    --onefile `
    --windowed `
    --name "Claudou" `
    --add-data "$ctk_path;customtkinter/" `
    --hidden-import "customtkinter" `
    --hidden-import "tkinter" `
    --uac-admin `
    claudou.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n=== Build thành công! ===" -ForegroundColor Green
    Write-Host "File exe: dist\Claudou.exe" -ForegroundColor Cyan
} else {
    Write-Host "`n=== Build thất bại ===" -ForegroundColor Red
}
