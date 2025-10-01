# Remote Windows Deployment Script for Zoom Recordings Extractor
# This script can be run on any Windows host to deploy the extractor

param(
    [string]$GitHubRepo = "https://github.com/silicoon84/zoomextractor.git",
    [string]$InstallDir = "C:\zoom-extractor",
    [switch]$UseVirtualEnv = $true,
    [switch]$SkipTests = $false
)

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   Zoom Recordings Extractor - Remote Deployment" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
if (-not $isAdmin) {
    Write-Host "⚠️  WARNING: Not running as Administrator. Some operations may fail." -ForegroundColor Yellow
}

# Check Python installation
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ ERROR: Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Python 3.8+ from https://python.org" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check Git installation
try {
    $gitVersion = git --version 2>&1
    Write-Host "✅ Git found: $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ ERROR: Git is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Git from https://git-scm.com" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Create installation directory
Write-Host "📁 Creating installation directory: $InstallDir" -ForegroundColor Yellow
if (Test-Path $InstallDir) {
    Write-Host "⚠️  Directory already exists. Removing..." -ForegroundColor Yellow
    Remove-Item $InstallDir -Recurse -Force
}
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null

# Clone repository
Write-Host "📥 Cloning repository from GitHub..." -ForegroundColor Yellow
Set-Location $InstallDir
git clone $GitHubRepo .

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ ERROR: Failed to clone repository" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Repository cloned successfully" -ForegroundColor Green

# Set up virtual environment if requested
if ($UseVirtualEnv) {
    Write-Host "🐍 Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    
    Write-Host "🔄 Activating virtual environment..." -ForegroundColor Yellow
    & ".\venv\Scripts\Activate.ps1"
    
    Write-Host "✅ Virtual environment activated" -ForegroundColor Green
}

# Upgrade pip
Write-Host "⬆️  Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

# Install dependencies
Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

# Install package
Write-Host "🔧 Installing Zoom Recordings Extractor..." -ForegroundColor Yellow
pip install -e .

# Install test dependencies
Write-Host "🧪 Installing test dependencies..." -ForegroundColor Yellow
pip install pytest pytest-mock responses

# Create .env file if it doesn't exist
if (-not (Test-Path ".env")) {
    Write-Host "📝 Creating .env file template..." -ForegroundColor Yellow
    Copy-Item "env.example" ".env"
    Write-Host "⚠️  Please edit .env file with your Zoom credentials" -ForegroundColor Yellow
}

# Run tests if not skipped
if (-not $SkipTests) {
    Write-Host "🧪 Running installation tests..." -ForegroundColor Yellow
    python test_windows_setup.py
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ All tests passed!" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Some tests failed, but installation may still work" -ForegroundColor Yellow
    }
}

# Final instructions
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "   Deployment Complete!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "📁 Installation directory: $InstallDir" -ForegroundColor White
Write-Host ""
Write-Host "🔧 Next steps:" -ForegroundColor White
Write-Host "1. Edit .env file with your Zoom credentials" -ForegroundColor Cyan
Write-Host "2. Test the installation: python test_windows_setup.py" -ForegroundColor Cyan
Write-Host "3. Run extraction: python extract_all_recordings.py --help" -ForegroundColor Cyan
Write-Host ""

if ($UseVirtualEnv) {
    Write-Host "🐍 To activate virtual environment in the future:" -ForegroundColor White
    Write-Host "   cd $InstallDir" -ForegroundColor Cyan
    Write-Host "   .\venv\Scripts\Activate.ps1" -ForegroundColor Cyan
    Write-Host ""
}

Write-Host "📚 For more information, see DEPLOY_WINDOWS.md" -ForegroundColor White
Write-Host ""

Read-Host "Press Enter to exit"
