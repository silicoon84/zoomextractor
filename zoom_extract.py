#!/usr/bin/env python3
"""
Zoom Recordings Extractor - Main Entry Point

A comprehensive tool for downloading all cloud recordings from a Zoom account.
"""

import sys
from pathlib import Path

# Add the zoom_extractor package to the path
package_dir = Path(__file__).parent / 'zoom_extractor'
sys.path.insert(0, str(package_dir.parent))

from zoom_extractor.main import main

if __name__ == '__main__':
    main()
