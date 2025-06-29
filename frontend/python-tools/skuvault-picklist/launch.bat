@echo off
REM Launch SkuVault Picklist Generator

REM Check if exe exists
if exist "SkuVault Picklist.exe" (
    start "" "SkuVault Picklist.exe"
) else if exist "dist\SkuVault Picklist.exe" (
    start "" "dist\SkuVault Picklist.exe"
) else (
    echo SkuVault Picklist.exe not found!
    echo Please run build.py first to create the executable.
    pause
)