#!/usr/bin/env python3
"""
Example usage of Zoom Recordings Extractor

This script demonstrates how to use the Zoom Extractor programmatically.
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add the package to the path
sys.path.insert(0, str(Path(__file__).parent))

from zoom_extractor.main import ZoomExtractor

def example_basic_extraction():
    """Example of basic extraction."""
    print("=== Basic Extraction Example ===")
    
    # Initialize extractor
    extractor = ZoomExtractor(
        output_dir="./example_recordings",
        from_date="2024-01-01",
        to_date="2024-12-31",
        max_concurrent=2,
        dry_run=True  # Don't actually download for this example
    )
    
    # Run extraction
    summary = extractor.extract_all_recordings()
    
    print("Extraction Summary:")
    print(f"Users processed: {summary.get('users', {}).get('processed', 0)}")
    print(f"Meetings processed: {summary.get('meetings', {}).get('processed', 0)}")
    print(f"Files downloaded: {summary.get('files', {}).get('downloaded', 0)}")
    print(f"Progress: {summary.get('files', {}).get('progress_percent', 0):.1f}%")

def example_user_filtered_extraction():
    """Example of extracting recordings for specific users."""
    print("\n=== User-Filtered Extraction Example ===")
    
    # List of users to extract recordings for
    user_emails = [
        "user1@company.com",
        "user2@company.com"
    ]
    
    extractor = ZoomExtractor(
        output_dir="./filtered_recordings",
        user_filter=user_emails,
        from_date="2024-06-01",  # Last 6 months
        max_concurrent=1,  # Conservative for testing
        dry_run=True
    )
    
    summary = extractor.extract_all_recordings()
    print(f"Filtered extraction completed: {summary}")

def example_recent_recordings():
    """Example of extracting only recent recordings."""
    print("\n=== Recent Recordings Example ===")
    
    # Get date 30 days ago
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    extractor = ZoomExtractor(
        output_dir="./recent_recordings",
        from_date=thirty_days_ago,
        max_concurrent=3,
        dry_run=True
    )
    
    summary = extractor.extract_all_recordings()
    print(f"Recent recordings extraction completed: {summary}")

def example_with_trash():
    """Example of including recordings in trash."""
    print("\n=== Extraction with Trash Example ===")
    
    extractor = ZoomExtractor(
        output_dir="./all_recordings",
        include_trash=True,  # Include recordings in trash
        dry_run=True
    )
    
    summary = extractor.extract_all_recordings()
    print(f"Extraction with trash completed: {summary}")

def main():
    """Run example usage scenarios."""
    print("Zoom Recordings Extractor - Usage Examples")
    print("=" * 50)
    
    # Check if environment is configured
    required_env_vars = ["ZOOM_ACCOUNT_ID", "ZOOM_CLIENT_ID", "ZOOM_CLIENT_SECRET"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        print("⚠ Warning: Missing environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nThese examples will run in dry-run mode to demonstrate functionality.")
        print("Configure your .env file to run actual extractions.")
    
    try:
        # Run examples
        example_basic_extraction()
        example_user_filtered_extraction()
        example_recent_recordings()
        example_with_trash()
        
        print("\n" + "=" * 50)
        print("✓ All examples completed successfully!")
        print("\nTo run actual extractions:")
        print("1. Configure your .env file with Zoom credentials")
        print("2. Set dry_run=False in the examples above")
        print("3. Or use the CLI: python zoom_extract.py")
        
    except Exception as e:
        print(f"\n✗ Example failed: {e}")
        print("Make sure you have installed all dependencies:")
        print("  pip install -r requirements.txt")

if __name__ == "__main__":
    main()
