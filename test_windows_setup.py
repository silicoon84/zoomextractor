#!/usr/bin/env python3
"""
Windows Setup Test Script for Zoom Recordings Extractor

This script tests the setup.py installation on Windows systems.
Run this after installing the package to verify everything works.
"""

import sys
import platform
import subprocess
import importlib
from pathlib import Path

def print_header(title):
    """Print a formatted header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_status(message, status="INFO"):
    """Print a status message with emoji"""
    emojis = {
        "INFO": "[INFO]",
        "SUCCESS": "[OK]",
        "WARNING": "[WARN]",
        "ERROR": "[ERROR]"
    }
    print(f"{emojis.get(status, '[INFO]')} {message}")

def test_python_version():
    """Test Python version compatibility"""
    print_header("Python Version Check")
    
    version = sys.version_info
    print_status(f"Python Version: {version.major}.{version.minor}.{version.micro}")
    print_status(f"Platform: {platform.platform()}")
    print_status(f"Architecture: {platform.architecture()}")
    
    if version.major == 3 and version.minor >= 8:
        print_status("Python version is compatible (>=3.8)", "SUCCESS")
        return True
    else:
        print_status("Python version is too old (requires >=3.8)", "ERROR")
        return False

def test_package_imports():
    """Test that all required packages can be imported"""
    print_header("Package Import Test")
    
    packages = [
        ('requests', 'requests'),
        ('python_dotenv', 'dotenv'),
        ('click', 'click'),
        ('tqdm', 'tqdm'),
        ('PyJWT', 'jwt'),
        ('python_dateutil', 'dateutil')
    ]
    
    all_imported = True
    for package_name, import_name in packages:
        try:
            importlib.import_module(import_name)
            print_status(f"Successfully imported {package_name}", "SUCCESS")
        except ImportError as e:
            print_status(f"Failed to import {package_name}: {e}", "ERROR")
            all_imported = False
    
    return all_imported

def test_zoom_extractor_imports():
    """Test that zoom_extractor modules can be imported"""
    print_header("Zoom Extractor Module Test")
    
    modules = [
        'zoom_extractor',
        'zoom_extractor.auth',
        'zoom_extractor.users',
        'zoom_extractor.recordings',
        'zoom_extractor.downloader',
        'zoom_extractor.dates',
        'zoom_extractor.structure',
        'zoom_extractor.rate_limiter',
        'zoom_extractor.state',
        'zoom_extractor.edge_cases',
        'zoom_extractor.main'
    ]
    
    all_imported = True
    for module in modules:
        try:
            importlib.import_module(module)
            print_status(f"Successfully imported {module}", "SUCCESS")
        except ImportError as e:
            print_status(f"Failed to import {module}: {e}", "ERROR")
            all_imported = False
    
    return all_imported

def test_entry_points():
    """Test that console scripts are properly installed"""
    print_header("Entry Points Test")
    
    try:
        # Test if the main script can be imported
        from extract_all_recordings import main
        print_status("extract_all_recordings.main can be imported", "SUCCESS")
        
        # Test if zoom_extractor.main can be imported
        from zoom_extractor.main import main as zoom_main
        print_status("zoom_extractor.main can be imported", "SUCCESS")
        
        return True
    except ImportError as e:
        print_status(f"Entry points test failed: {e}", "ERROR")
        return False

def test_file_permissions():
    """Test file system permissions on Windows"""
    print_header("File System Permissions Test")
    
    try:
        # Test creating a directory
        test_dir = Path("test_permissions")
        test_dir.mkdir(exist_ok=True)
        print_status("Can create directories", "SUCCESS")
        
        # Test creating a file
        test_file = test_dir / "test.txt"
        test_file.write_text("test content")
        print_status("Can create files", "SUCCESS")
        
        # Test reading a file
        content = test_file.read_text()
        print_status("Can read files", "SUCCESS")
        
        # Test deleting files and directories
        test_file.unlink()
        test_dir.rmdir()
        print_status("Can delete files and directories", "SUCCESS")
        
        return True
    except Exception as e:
        print_status(f"File system test failed: {e}", "ERROR")
        return False

def test_environment_variables():
    """Test environment variable handling"""
    print_header("Environment Variables Test")
    
    try:
        import os
        try:
            from dotenv import load_dotenv
            dotenv_available = True
        except ImportError:
            dotenv_available = False
            print_status("python-dotenv not installed (this is OK)", "WARNING")
        
        # Test loading .env file if it exists and dotenv is available
        if dotenv_available:
            env_file = Path(".env")
            if env_file.exists():
                load_dotenv()
                print_status("Successfully loaded .env file", "SUCCESS")
            else:
                print_status("No .env file found (this is OK)", "WARNING")
        else:
            print_status("Skipping .env test (python-dotenv not available)", "WARNING")
        
        return True
    except Exception as e:
        print_status(f"Environment variables test failed: {e}", "ERROR")
        return False

def test_network_connectivity():
    """Test basic network connectivity"""
    print_header("Network Connectivity Test")
    
    try:
        import requests
        
        # Test HTTPS connection to Zoom API
        response = requests.get("https://api.zoom.us", timeout=10)
        print_status(f"Successfully connected to Zoom API (status: {response.status_code})", "SUCCESS")
        
        return True
    except Exception as e:
        print_status(f"Network connectivity test failed: {e}", "WARNING")
        return False

def main():
    """Run all tests"""
    print_header("Windows Setup Test for Zoom Recordings Extractor")
    print_status(f"Running on {platform.system()} {platform.release()}")
    
    tests = [
        test_python_version,
        test_package_imports,
        test_zoom_extractor_imports,
        test_entry_points,
        test_file_permissions,
        test_environment_variables,
        test_network_connectivity
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print_status(f"Test {test.__name__} crashed: {e}", "ERROR")
            results.append(False)
    
    print_header("Test Summary")
    passed = sum(results)
    total = len(results)
    
    print_status(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print_status("All tests passed! Setup is working correctly.", "SUCCESS")
        return 0
    else:
        print_status("Some tests failed. Check the output above for details.", "WARNING")
        return 1

if __name__ == "__main__":
    sys.exit(main())
