@echo off
REM Windows Installation Script for Zoom Recordings Extractor
REM Run this script to install the package and test it

echo ============================================================
echo   Zoom Recordings Extractor - Windows Installation
echo ============================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

echo Python found:
python --version

REM Check Python version
for /f "tokens=2" %%i in ('python -c "import sys; print(sys.version_info.major)"') do set PYTHON_MAJOR=%%i
for /f "tokens=2" %%i in ('python -c "import sys; print(sys.version_info.minor)"') do set PYTHON_MINOR=%%i

if %PYTHON_MAJOR% lss 3 (
    echo ERROR: Python 3.8+ is required. Found Python %PYTHON_MAJOR%.%PYTHON_MINOR%
    pause
    exit /b 1
)

if %PYTHON_MAJOR% equ 3 if %PYTHON_MINOR% lss 8 (
    echo ERROR: Python 3.8+ is required. Found Python %PYTHON_MAJOR%.%PYTHON_MINOR%
    pause
    exit /b 1
)

echo Python version is compatible.
echo.

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install the package in development mode
echo Installing Zoom Recordings Extractor...
pip install -e .

REM Install test dependencies
echo Installing test dependencies...
pip install pytest pytest-mock responses

REM Run the Windows setup test
echo.
echo Running Windows setup test...
python test_windows_setup.py

REM Check if test passed
if %errorlevel% equ 0 (
    echo.
    echo ============================================================
    echo   Installation completed successfully!
    echo ============================================================
    echo.
    echo You can now run:
    echo   zoom-extract --help
    echo   zoom-extract-all --help
    echo.
    echo Or run the test script anytime:
    echo   python test_windows_setup.py
    echo.
) else (
    echo.
    echo ============================================================
    echo   Installation completed with warnings
    echo ============================================================
    echo.
    echo Some tests failed, but the package should still work.
    echo Check the output above for details.
    echo.
)

pause
