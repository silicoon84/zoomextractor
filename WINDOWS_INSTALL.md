# Windows Installation Guide

This guide will help you install and test the Zoom Recordings Extractor on Windows.

## 🚀 Quick Installation

### Option 1: Automated Installation (Recommended)

**Using Command Prompt:**
```cmd
install_windows.bat
```

**Using PowerShell:**
```powershell
.\install_windows.ps1
```

### Option 2: Manual Installation

1. **Install Python 3.8+** (if not already installed):
   - Download from [python.org](https://python.org)
   - Make sure to check "Add Python to PATH" during installation

2. **Open Command Prompt or PowerShell** as Administrator

3. **Navigate to the project directory:**
   ```cmd
   cd "C:\path\to\zoom-recordings-extractor"
   ```

4. **Upgrade pip:**
   ```cmd
   python -m pip install --upgrade pip
   ```

5. **Install the package:**
   ```cmd
   pip install -e .
   ```

6. **Install test dependencies:**
   ```cmd
   pip install pytest pytest-mock responses
   ```

7. **Run the test script:**
   ```cmd
   python test_windows_setup.py
   ```

## 🧪 Testing the Installation

After installation, run the comprehensive test:

```cmd
python test_windows_setup.py
```

This will test:
- ✅ Python version compatibility
- ✅ Package imports
- ✅ Zoom extractor modules
- ✅ Entry points
- ✅ File system permissions
- ✅ Environment variables
- ✅ Network connectivity

## 🎯 Usage

Once installed, you can use the following commands:

```cmd
# Get help
zoom-extract --help
zoom-extract-all --help

# Run extraction
zoom-extract-all --user-filter user@example.com --from-date 2020-01-01
```

## 🔧 Troubleshooting

### Common Issues:

1. **"Python is not recognized"**
   - Install Python from [python.org](https://python.org)
   - Make sure to check "Add Python to PATH"

2. **Permission denied errors**
   - Run Command Prompt/PowerShell as Administrator
   - Or use a virtual environment:
     ```cmd
     python -m venv venv
     venv\Scripts\activate
     pip install -e .
     ```

3. **Import errors**
   - Make sure you're in the correct directory
   - Check that all dependencies are installed:
     ```cmd
     pip install -r requirements.txt
     ```

4. **Network connectivity issues**
   - Check your internet connection
   - Verify firewall settings
   - Test with: `python -c "import requests; print(requests.get('https://api.zoom.us').status_code)"`

## 📁 Directory Structure

After installation, you should see:
```
zoom-recordings-extractor/
├── zoom_extractor/          # Main package
├── extract_all_recordings.py # Main extraction script
├── test_windows_setup.py     # Windows test script
├── install_windows.bat       # Batch installer
├── install_windows.ps1       # PowerShell installer
├── requirements.txt          # Dependencies
└── setup.py                  # Package setup
```

## 🔐 Environment Setup

1. **Copy the environment template:**
   ```cmd
   copy env.example .env
   ```

2. **Edit `.env` with your Zoom credentials:**
   ```
   ZOOM_ACCOUNT_ID=your_account_id
   ZOOM_CLIENT_ID=your_client_id
   ZOOM_CLIENT_SECRET=your_client_secret
   ZOOM_FROM=2020-01-01
   ZOOM_TO=2025-12-31
   ZOOM_OUTDIR=./zoom_recordings
   ```

## 🎉 Success!

If everything works correctly, you should see:
```
✅ All tests passed! Setup is working correctly.
```

You're now ready to extract Zoom recordings! 🚀
