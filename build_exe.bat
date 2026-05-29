@echo off
title KSEI Dashboard - Build EXE
color 0A

echo ============================================
echo  KSEI Ownership Dashboard - Build Script
echo ============================================
echo.

cd /d "%~dp0"

echo [1/5] Cleaning previous build...
if exist "build"           rmdir /s /q "build"
if exist "dist\KSEI_Dashboard" rmdir /s /q "dist\KSEI_Dashboard"
if exist "KSEI_Dashboard.zip" del /q "KSEI_Dashboard.zip"
echo       Done.
echo.

echo [2/5] Installing pinned build dependencies...
echo       This makes the packaged dashboard match the tested UI runtime.
echo.
py -m pip install -r requirements.txt

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Dependency install failed! See output above for details.
    pause
    exit /b 1
)

echo.
echo [3/5] Building executable (this takes 3-10 minutes)...
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
echo [4/5] Creating distribution ZIP...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path 'dist\KSEI_Dashboard' -DestinationPath 'KSEI_Dashboard.zip' -Force"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] ZIP creation failed! See output above for details.
    pause
    exit /b 1
)

echo.
echo [5/5] Build complete!
echo.
echo ============================================
echo  OUTPUT LOCATION:
echo  %~dp0dist\KSEI_Dashboard\
echo.
echo  ZIP TO SEND TO OTHER PC:
echo  %~dp0KSEI_Dashboard.zip
echo.
echo  To distribute:
echo  - Send KSEI_Dashboard.zip
echo  - On target PC: unzip and run KSEI_Dashboard.exe
echo  - ksei.db (database) is saved next to the .exe
echo ============================================
echo.
pause
