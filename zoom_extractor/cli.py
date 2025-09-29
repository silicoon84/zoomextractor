"""
CLI Entry Point for Zoom Extractor

Provides command-line interface for the Zoom recordings extractor.
"""

import sys
from pathlib import Path

# Add the package to the path
package_dir = Path(__file__).parent
sys.path.insert(0, str(package_dir.parent))

from zoom_extractor.main import main

if __name__ == '__main__':
    main()
