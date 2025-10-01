# Windows Deployment Guide

This guide will help you deploy the Zoom Recordings Extractor on any Windows host.

## 🚀 **Method 1: From GitHub (Recommended)**

### **Step 1: Clone the Repository**
```cmd
# Using Command Prompt
git clone https://github.com/silicoon84/zoomextractor.git
cd zoomextractor

# Or using PowerShell
git clone https://github.com/silicoon84/zoomextractor.git
cd zoomextractor
```

### **Step 2: Automated Installation**
```cmd
# Run the automated installer
install_windows.bat

# Or using PowerShell (run as Administrator)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\install_windows.ps1
```

### **Step 3: Verify Installation**
```cmd
python test_windows_setup.py
```

---

## 🛠️ **Method 2: Manual Installation**

### **Prerequisites**
- Python 3.8 or higher
- Git (for cloning)
- Internet connection

### **Step 1: Install Python**
1. Download Python from [python.org](https://python.org)
2. **IMPORTANT**: Check "Add Python to PATH" during installation
3. Verify installation:
   ```cmd
   python --version
   pip --version
   ```

### **Step 2: Clone Repository**
```cmd
git clone https://github.com/silicoon84/zoomextractor.git
cd zoomextractor
```

### **Step 3: Install Dependencies**
```cmd
# Upgrade pip
python -m pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

# Install package in development mode
pip install -e .

# Install test dependencies (optional)
pip install pytest pytest-mock responses
```

### **Step 4: Test Installation**
```cmd
python test_windows_setup.py
```

---

## 🔧 **Method 3: Using Virtual Environment (Recommended for Production)**

### **Step 1: Create Virtual Environment**
```cmd
# Create virtual environment
python -m venv zoom_extractor_env

# Activate it
zoom_extractor_env\Scripts\activate

# Verify activation (should show the env name)
where python
```

### **Step 2: Install in Virtual Environment**
```cmd
# Clone repository (if not already done)
git clone https://github.com/silicoon84/zoomextractor.git
cd zoomextractor

# Install dependencies
pip install -r requirements.txt
pip install -e .
```

### **Step 3: Test**
```cmd
python test_windows_setup.py
```

---

## ⚙️ **Configuration**

### **Step 1: Set Up Environment Variables**
```cmd
# Copy the example file
copy env.example .env

# Edit .env with your Zoom credentials
notepad .env
```

### **Step 2: Configure Zoom App**
Your `.env` file should contain:
```env
ZOOM_ACCOUNT_ID=your_account_id
ZOOM_CLIENT_ID=your_client_id
ZOOM_CLIENT_SECRET=your_client_secret
ZOOM_FROM=2020-01-01
ZOOM_TO=2025-12-31
ZOOM_OUTDIR=./zoom_recordings
```

### **Step 3: Test Configuration**
```cmd
# Test authentication
python -c "from zoom_extractor.auth import get_auth_from_env; print('Auth OK' if get_auth_from_env() else 'Auth Failed')"
```

---

## 🎯 **Usage**

### **Basic Commands**
```cmd
# Get help
zoom-extract --help
python extract_all_recordings.py --help

# Dry run (test without downloading)
python extract_all_recordings.py --dry-run --user-filter user@example.com

# Full extraction
python extract_all_recordings.py --user-filter user@example.com --from-date 2020-01-01
```

### **Background Execution**
```cmd
# Using nohup (if available)
nohup python extract_all_recordings.py --user-filter user@example.com > extraction.log 2>&1 &

# Using Windows Task Scheduler (recommended)
# Create a scheduled task that runs the script
```

---

## 🚨 **Troubleshooting**

### **Common Issues**

1. **"Python is not recognized"**
   ```cmd
   # Fix: Add Python to PATH or reinstall with PATH option
   # Or use full path: C:\Python39\python.exe
   ```

2. **"Permission denied"**
   ```cmd
   # Run Command Prompt as Administrator
   # Or use virtual environment
   ```

3. **"Module not found"**
   ```cmd
   # Reinstall dependencies
   pip install -r requirements.txt --force-reinstall
   ```

4. **"Authentication failed"**
   ```cmd
   # Check .env file exists and has correct credentials
   # Verify Zoom app is activated in Zoom Marketplace
   ```

### **Network Issues**
```cmd
# Test connectivity
python -c "import requests; print(requests.get('https://api.zoom.us').status_code)"

# Check firewall settings
# Ensure ports 80/443 are open
```

### **Get Help**
```cmd
# Run diagnostic test
python test_windows_setup.py

# Check logs
type extraction.log
```

---

## 📁 **File Structure After Installation**

```
zoomextractor/
├── zoom_extractor/          # Main package
├── extract_all_recordings.py # Main extraction script
├── test_windows_setup.py     # Windows test script
├── install_windows.bat       # Batch installer
├── install_windows.ps1       # PowerShell installer
├── requirements.txt          # Dependencies
├── setup.py                  # Package setup
├── .env                      # Your configuration (create this)
└── zoom_recordings/          # Downloaded recordings (created during extraction)
```

---

## 🔐 **Security Notes**

1. **Never commit `.env` file** to version control
2. **Use virtual environments** for isolation
3. **Run as limited user** when possible
4. **Keep credentials secure** and rotate regularly

---

## ✅ **Success Indicators**

You'll know it's working when:
- ✅ `python test_windows_setup.py` shows "All tests passed!"
- ✅ `zoom-extract --help` shows the help menu
- ✅ Authentication test passes
- ✅ Network connectivity test passes

---

## 🆘 **Getting Support**

If you encounter issues:
1. Run `python test_windows_setup.py` and share the output
2. Check the troubleshooting section above
3. Verify your Zoom app configuration
4. Ensure all prerequisites are met
