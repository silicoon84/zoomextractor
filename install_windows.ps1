# Windows PowerShell Installation Script for Zoom Recordings Extractor
# Run this script to install the package and test it

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   Zoom Recordings Extractor - Windows Installation" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Check if Python is installed
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ ERROR: Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Python 3.8+ from https://python.org" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check Python version
$pythonMajor = python -c "import sys; print(sys.version_info.major)" 2>$null
$pythonMinor = python -c "import sys; print(sys.version_info.minor)" 2>$null

if ([int]$pythonMajor -lt 3 -or ([int]$pythonMajor -eq 3 -and [int]$pythonMinor -lt 8)) {
    Write-Host "❌ ERROR: Python 3.8+ is required. Found Python $pythonMajor.$pythonMinor" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "✅ Python version is compatible." -ForegroundColor Green
Write-Host ""

# Upgrade pip
Write-Host "🔄 Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

# Install the package in development mode
Write-Host "📦 Installing Zoom Recordings Extractor..." -ForegroundColor Yellow
pip install -e .

# Install test dependencies
Write-Host "🧪 Installing test dependencies..." -ForegroundColor Yellow
pip install pytest pytest-mock responses

# Run the Windows setup test
Write-Host ""
Write-Host "🔍 Running Windows setup test..." -ForegroundColor Yellow
python test_windows_setup.py

# Check if test passed
if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host "   Installation completed successfully!" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "You can now run:" -ForegroundColor White
    Write-Host "  zoom-extract --help" -ForegroundColor Cyan
    Write-Host "  zoom-extract-all --help" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Or run the test script anytime:" -ForegroundColor White
    Write-Host "  python test_windows_setup.py" -ForegroundColor Cyan
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Yellow
    Write-Host "   Installation completed with warnings" -ForegroundColor Yellow
    Write-Host "============================================================" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Some tests failed, but the package should still work." -ForegroundColor White
    Write-Host "Check the output above for details." -ForegroundColor White
    Write-Host ""
}

Read-Host "Press Enter to exit"
