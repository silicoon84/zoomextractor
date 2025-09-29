#!/usr/bin/env python3
"""
Quick Fix Script

Simple script to reset progress to user 85 (before the 401 errors started).
"""

import json
import os
from datetime import datetime

def quick_fix():
    """Quick fix to reset progress to user 85."""
    progress_file = 'count_progress.json'
    
    print("🔧 Quick Progress Fix")
    print("=" * 25)
    print("Based on your log, 401 errors started around user 87")
    print("Resetting progress to user 85 to be safe")
    
    # Create fresh progress starting from user 85
    progress = {
        'processed_users': 85,
        'total_meetings': 0,
        'total_files': 0,
        'users_with_recordings': 0,
        'total_users': 200,
        'last_update': datetime.now().isoformat(),
        'resume_point': 85,
        'note': 'Reset to user 85 before 401 errors started'
    }
    
    # Save the progress
    with open(progress_file, 'w') as f:
        json.dump(progress, f, indent=2)
    
    print(f"✅ Progress file created/reset to user 85")
    print(f"📝 File saved as: {progress_file}")
    print(f"\n🚀 Now run: python total_count.py")
    print("   It will ask if you want to resume - say 'y'")
    print("   It will start from user 85 and process users 85-200")

if __name__ == "__main__":
    quick_fix()
