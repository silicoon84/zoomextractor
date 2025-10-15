#!/usr/bin/env python3
"""
Test script to verify Zoom Extractor installation and basic functionality.
"""

import sys
import os
from pathlib import Path

def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")
    
    try:
        import requests
        print("✓ requests imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import requests: {e}")
        return False
    
    try:
        import click
        print("✓ click imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import click: {e}")
        return False
    
    try:
        import jwt
        print("✓ PyJWT imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import PyJWT: {e}")
        return False
    
    try:
        from dateutil.relativedelta import relativedelta
        print("✓ python-dateutil imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import python-dateutil: {e}")
        return False
    
    try:
        from dotenv import load_dotenv
        print("✓ python-dotenv imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import python-dotenv: {e}")
        return False
    
    return True

def test_zoom_extractor_modules():
    """Test that Zoom Extractor modules can be imported."""
    print("\nTesting Zoom Extractor modules...")
    
    try:
        from zoom_extractor.auth import ZoomAuth
        print("✓ zoom_extractor.auth imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import zoom_extractor.auth: {e}")
        return False
    
    try:
        from zoom_extractor.users import UserEnumerator
        print("✓ zoom_extractor.users imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import zoom_extractor.users: {e}")
        return False
    
    try:
        from zoom_extractor.dates import DateWindowGenerator
        print("✓ zoom_extractor.dates imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import zoom_extractor.dates: {e}")
        return False
    
    try:
        from zoom_extractor.recordings import RecordingsLister
        print("✓ zoom_extractor.recordings imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import zoom_extractor.recordings: {e}")
        return False
    
    try:
        from zoom_extractor.downloader import FileDownloader
        print("✓ zoom_extractor.downloader imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import zoom_extractor.downloader: {e}")
        return False
    
    try:
        from zoom_extractor.structure import DirectoryStructure
        print("✓ zoom_extractor.structure imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import zoom_extractor.structure: {e}")
        return False
    
    try:
        from zoom_extractor.state import ExtractionState, InventoryLogger
        print("✓ zoom_extractor.state imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import zoom_extractor.state: {e}")
        return False
    
    try:
        from zoom_extractor.edge_cases import EdgeCaseHandler
        print("✓ zoom_extractor.edge_cases imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import zoom_extractor.edge_cases: {e}")
        return False
    
    try:
        from zoom_extractor.rate_limiter import RateLimiter
        print("✓ zoom_extractor.rate_limiter imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import zoom_extractor.rate_limiter: {e}")
        return False
    
    return True

def test_cli_entry_point():
    """Test that the CLI entry point works."""
    print("\nTesting CLI entry point...")
    
    try:
        # Test that the main script can be imported
        sys.path.insert(0, str(Path(__file__).parent))
        from zoom_extractor.main import main
        print("✓ CLI entry point imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Failed to import CLI entry point: {e}")
        return False

def test_environment_file():
    """Test that environment file exists and has required variables."""
    print("\nTesting environment configuration...")
    
    env_file = Path(".env")
    env_example = Path("env.example")
    
    if not env_example.exists():
        print("✗ env.example file not found")
        return False
    
    print("✓ env.example file found")
    
    if not env_file.exists():
        print("⚠ .env file not found - you'll need to create it from env.example")
        return True
    
    print("✓ .env file found")
    
    # Check for required variables (without revealing values)
    required_vars = ["ZOOM_ACCOUNT_ID", "ZOOM_CLIENT_ID", "ZOOM_CLIENT_SECRET"]
    
    with open(env_file, 'r') as f:
        env_content = f.read()
    
    for var in required_vars:
        if f"{var}=" in env_content:
            print(f"✓ {var} is configured")
        else:
            print(f"⚠ {var} is not configured")
    
    return True

def main():
    """Run all tests."""
    print("Zoom Recordings Extractor - Installation Test")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_zoom_extractor_modules,
        test_cli_entry_point,
        test_environment_file,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ All tests passed! Zoom Extractor is ready to use.")
        print("\nNext steps:")
        print("1. Copy env.example to .env and configure your Zoom credentials")
        print("2. Run: python zoom_extract.py --help")
        print("3. Run: python zoom_extract.py --dry-run (to test)")
        return 0
    else:
        print("✗ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
