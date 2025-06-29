# SkuVault Picklist Generator Launcher

Write-Host "SkuVault Picklist Generator" -ForegroundColor Cyan
Write-Host "==========================" -ForegroundColor Cyan
Write-Host ""

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Found $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Python is not installed" -ForegroundColor Red
    Write-Host "Please install Python 3.8+ from python.org"
    Read-Host "Press Enter to exit"
    exit 1
}

# Install dependencies
Write-Host "Checking dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt --quiet

# Run application
Write-Host "Starting application..." -ForegroundColor Green
python main.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "Application encountered an error." -ForegroundColor Red
    Read-Host "Press Enter to exit"
}
