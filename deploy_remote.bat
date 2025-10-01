@echo off
REM Remote Windows Deployment Script for Zoom Recordings Extractor
REM This script can be run on any Windows host to deploy the extractor

setlocal enabledelayedexpansion

echo ============================================================
echo   Zoom Recordings Extractor - Remote Deployment
echo ============================================================
echo.

REM Set default values
set GITHUB_REPO=https://github.com/silicoon84/zoomextractor.git
set INSTALL_DIR=C:\zoom-extractor
set USE_VENV=1

REM Check Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

echo Python found:
python --version

REM Check Git installation
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Git is not installed or not in PATH
    echo Please install Git from https://git-scm.com
    pause
    exit /b 1
)

echo Git found:
git --version

REM Create installation directory
echo.
echo Creating installation directory: %INSTALL_DIR%
if exist "%INSTALL_DIR%" (
    echo Directory already exists. Removing...
    rmdir /s /q "%INSTALL_DIR%"
)
mkdir "%INSTALL_DIR%"

REM Clone repository
echo.
echo Cloning repository from GitHub...
cd /d "%INSTALL_DIR%"
git clone %GITHUB_REPO% .

if %errorlevel% neq 0 (
    echo ERROR: Failed to clone repository
    pause
    exit /b 1
)

echo Repository cloned successfully

REM Set up virtual environment if requested
if "%USE_VENV%"=="1" (
    echo.
    echo Creating virtual environment...
    python -m venv venv
    
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
    
    echo Virtual environment activated
)

REM Upgrade pip
echo.
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo.
echo Installing dependencies...
pip install -r requirements.txt

REM Install package
echo.
echo Installing Zoom Recordings Extractor...
pip install -e .

REM Install test dependencies
echo.
echo Installing test dependencies...
pip install pytest pytest-mock responses

REM Create .env file if it doesn't exist
if not exist ".env" (
    echo.
    echo Creating .env file template...
    copy env.example .env
    echo WARNING: Please edit .env file with your Zoom credentials
)

REM Run tests
echo.
echo Running installation tests...
python test_windows_setup.py

if %errorlevel% equ 0 (
    echo All tests passed!
) else (
    echo Some tests failed, but installation may still work
)

REM Final instructions
echo.
echo ============================================================
echo   Deployment Complete!
echo ============================================================
echo.
echo Installation directory: %INSTALL_DIR%
echo.
echo Next steps:
echo 1. Edit .env file with your Zoom credentials
echo 2. Test the installation: python test_windows_setup.py
echo 3. Run extraction: python extract_all_recordings.py --help
echo.

if "%USE_VENV%"=="1" (
    echo To activate virtual environment in the future:
    echo    cd %INSTALL_DIR%
    echo    venv\Scripts\activate.bat
    echo.
)

echo For more information, see DEPLOY_WINDOWS.md
echo.

pause
