#!/usr/bin/env python3
"""
Build script for creating cross-platform package on Linux
"""

import os
import sys
import subprocess
import shutil
import zipfile

def create_portable_package():
    """Create a portable Python package that can run on Windows"""
    
    print("Creating portable package for Windows...")
    
    # Create dist directory
    dist_dir = "dist_portable"
    if os.path.exists(dist_dir):
        shutil.rmtree(dist_dir)
    os.makedirs(dist_dir)
    
    # Copy Python files
    files_to_copy = [
        'main.py',
        'skuvault_api.py',
        'requirements.txt',
        'README.md'
    ]
    
    for file in files_to_copy:
        if os.path.exists(file):
            shutil.copy(file, dist_dir)
    
    # Create a Windows batch launcher
    launcher_content = """@echo off
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
"""
    
    with open(f'{dist_dir}/SkuVault_Picklist.bat', 'w') as f:
        f.write(launcher_content)
    
    # Create a PowerShell launcher (alternative)
    ps_launcher = """# SkuVault Picklist Generator Launcher

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
"""
    
    with open(f'{dist_dir}/SkuVault_Picklist.ps1', 'w') as f:
        f.write(ps_launcher)
    
    # Create setup instructions
    setup_content = """SETUP INSTRUCTIONS FOR WINDOWS
==============================

Option 1: If Python is already installed
----------------------------------------
1. Double-click 'SkuVault_Picklist.bat'
2. The app will start automatically

Option 2: If Python is NOT installed
------------------------------------
1. Download Python from https://python.org/downloads/
2. During installation, CHECK "Add Python to PATH"
3. After installation, double-click 'SkuVault_Picklist.bat'

Option 3: Using PowerShell
-------------------------
1. Right-click 'SkuVault_Picklist.ps1'
2. Select "Run with PowerShell"

First Run:
----------
1. The app will ask for SkuVault API credentials
2. Enter your Tenant Token and User Token
3. Click "Test Connection" to verify
4. Credentials are saved securely for future use

Troubleshooting:
---------------
- If you see "Python is not installed", install Python 3.8+
- Make sure to check "Add Python to PATH" during installation
- If dependencies fail to install, run as Administrator
"""
    
    with open(f'{dist_dir}/SETUP.txt', 'w') as f:
        f.write(setup_content)
    
    # Create a zip file
    zip_name = 'SkuVault_Picklist_Portable.zip'
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(dist_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, dist_dir)
                zipf.write(file_path, arcname)
    
    print(f"\n✓ Portable package created: {zip_name}")
    print(f"  Contents: {dist_dir}/")
    print("  - SkuVault_Picklist.bat (Windows batch launcher)")
    print("  - SkuVault_Picklist.ps1 (PowerShell launcher)")
    print("  - main.py (Application)")
    print("  - skuvault_api.py (API wrapper)")
    print("  - requirements.txt (Dependencies)")
    print("  - SETUP.txt (Instructions)")
    
    return True

def create_wine_exe():
    """Attempt to create Windows exe using Wine and PyInstaller"""
    
    print("\nAttempting to build Windows .exe using Wine...")
    
    # Check if Wine is installed
    try:
        subprocess.run(['wine', '--version'], check=True, capture_output=True)
    except:
        print("✗ Wine is not installed. Install it with:")
        print("  sudo pacman -S wine wine-mono wine-gecko")
        return False
    
    print("✓ Wine is installed")
    
    # Instructions for Wine build
    print("\nTo build a Windows .exe on Linux:")
    print("1. Install Wine: sudo pacman -S wine wine-mono wine-gecko")
    print("2. Install Windows Python in Wine:")
    print("   wget https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe")
    print("   wine python-3.10.11-amd64.exe")
    print("3. Install PyInstaller in Wine:")
    print("   wine python.exe -m pip install pyinstaller requests cryptography")
    print("4. Build the exe:")
    print("   wine python.exe build.py")
    
    return False

def create_nuitka_build():
    """Create a compiled executable using Nuitka (cross-platform)"""
    
    print("\nChecking Nuitka option for creating standalone executable...")
    
    try:
        import nuitka
        print("✓ Nuitka is installed")
    except ImportError:
        print("✗ Nuitka not installed. Install with:")
        print("  pip install nuitka")
        print("\nNuitka can create standalone executables that work on Windows")
        print("but must be built on the target platform.")
        return False
    
    return True

if __name__ == "__main__":
    print("Building SkuVault Picklist for Windows from Linux")
    print("=" * 50)
    
    # Create portable package (always works)
    create_portable_package()
    
    # Show other options
    print("\n" + "=" * 50)
    print("Additional Options:")
    print("=" * 50)
    
    create_wine_exe()
    print()
    create_nuitka_build()
    
    print("\n" + "=" * 50)
    print("Recommendation:")
    print("=" * 50)
    print("The portable package (SkuVault_Picklist_Portable.zip) is ready!")
    print("This will work on any Windows machine with Python installed.")
    print("\nFor a true .exe file without Python dependency:")
    print("- Copy the project to a Windows machine")
    print("- Run: python build.py")
    print("- This will create a standalone .exe file")