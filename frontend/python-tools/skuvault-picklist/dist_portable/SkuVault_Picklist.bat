@echo off
echo SkuVault Picklist Generator
echo ==========================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from python.org
    echo.
    pause
    exit /b 1
)

REM Check/Install dependencies
echo Checking dependencies...
pip install -r requirements.txt --quiet

REM Run the application
echo Starting application...
python main.py

if errorlevel 1 (
    echo.
    echo Application encountered an error.
    pause
)
