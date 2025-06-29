#!/usr/bin/env python3
"""
Build script for creating Windows executable
"""

import os
import sys
import subprocess
import shutil

def build_exe():
    """Build the Windows executable using PyInstaller"""
    
    # Check if PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # Check if required packages are installed
    required_packages = ['requests', 'cryptography']
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            print(f"{package} not found. Installing...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    
    # Create icon if it doesn't exist (placeholder)
    if not os.path.exists('assets/icon.ico'):
        print("Note: No icon.ico found in assets/. The exe will use default icon.")
    
    # PyInstaller command
    cmd = [
        'pyinstaller',
        '--onefile',           # Single executable
        '--windowed',          # No console window
        '--name=SkuVault Picklist',  # Executable name
        '--distpath=dist',     # Output directory
        '--workpath=build',    # Build directory
        '--specpath=.',        # Spec file location
        '--clean',            # Clean build
        '--noconfirm',        # Overwrite without asking
    ]
    
    # Add icon if it exists
    if os.path.exists('assets/icon.ico'):
        cmd.extend(['--icon=assets/icon.ico'])
    
    # Add hidden imports that might be missed
    cmd.extend([
        '--hidden-import=cryptography',
        '--hidden-import=cryptography.fernet',
        '--hidden-import=requests',
        '--hidden-import=configparser',
    ])
    
    # Add the main script
    cmd.append('main.py')
    
    print("Building executable...")
    print("Command:", ' '.join(cmd))
    
    try:
        subprocess.check_call(cmd)
        print("\nBuild successful!")
        print(f"Executable created: dist/SkuVault Picklist.exe")
        
        # Create a batch file for easy launching
        with open('dist/Launch SkuVault Picklist.bat', 'w') as f:
            f.write('@echo off\n')
            f.write('start "" "SkuVault Picklist.exe"\n')
        
        print("Also created: dist/Launch SkuVault Picklist.bat")
        
    except subprocess.CalledProcessError as e:
        print(f"\nBuild failed: {e}")
        return False
    
    return True

def create_installer():
    """Create a simple installer package"""
    print("\nCreating installer package...")
    
    # Create installer directory
    installer_dir = "SkuVault_Picklist_Installer"
    if os.path.exists(installer_dir):
        shutil.rmtree(installer_dir)
    os.makedirs(installer_dir)
    
    # Copy executable
    if os.path.exists('dist/SkuVault Picklist.exe'):
        shutil.copy('dist/SkuVault Picklist.exe', installer_dir)
        shutil.copy('dist/Launch SkuVault Picklist.bat', installer_dir)
    
    # Create README
    readme_content = """SkuVault Picklist Generator
========================

Installation:
1. Copy "SkuVault Picklist.exe" to your desired location (e.g., Desktop)
2. Double-click to run

First Run:
1. The application will ask for your SkuVault API credentials
2. Enter your Tenant Token and User Token
3. Click "Test Connection" to verify
4. Click "Save" to store credentials securely

Usage:
1. Enter or scan SKUs into the input field
2. Press Enter or click "Add to Picklist"
3. Once all items are added, click "Generate Picklist"
4. Print or save the organized picklist

Features:
- Barcode scanner support (just scan into the SKU field)
- Real-time inventory lookup
- Location-based organization for efficient picking
- Save/load picklists
- Print-friendly format

Support:
For issues or questions, contact IT support.
"""
    
    with open(f'{installer_dir}/README.txt', 'w') as f:
        f.write(readme_content)
    
    print(f"Installer package created in: {installer_dir}/")
    print("Contents:")
    print("- SkuVault Picklist.exe")
    print("- Launch SkuVault Picklist.bat")
    print("- README.txt")

if __name__ == "__main__":
    if build_exe():
        create_installer()
        print("\nDone! The application is ready for distribution.")