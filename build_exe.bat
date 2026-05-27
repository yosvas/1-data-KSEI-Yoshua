@echo off
title KSEI Dashboard - Build EXE
color 0A

echo ============================================
echo  KSEI Ownership Dashboard - Build Script
echo ============================================
echo.

cd /d "%~dp0"

echo [1/3] Cleaning previous build...
if exist "build"           rmdir /s /q "build"
if exist "dist\KSEI_Dashboard" rmdir /s /q "dist\KSEI_Dashboard"
echo       Done.
echo.

echo [2/3] Building executable (this takes 3-10 minutes)...
echo       Please wait...
echo.
py -m PyInstaller ksei_dashboard.spec --noconfirm

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Build failed! See output above for details.
    pause
    exit /b 1
)

echo.
echo [3/3] Build complete!
echo.
echo ============================================
echo  OUTPUT LOCATION:
echo  %~dp0dist\KSEI_Dashboard\
echo.
echo  To distribute:
echo  - Zip the entire "KSEI_Dashboard" folder
echo  - On target PC: unzip and run KSEI_Dashboard.exe
echo  - ksei.db (database) is saved next to the .exe
echo ============================================
echo.
pause
