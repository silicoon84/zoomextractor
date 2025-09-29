#!/usr/bin/env python3
"""
Fix Progress Script

Fixes the progress file to resume from the correct position after token expiration errors.
"""

import json
import os
import re
from datetime import datetime

def analyze_log_file():
    """Analyze the log file to find where we actually stopped successfully."""
    log_file = 'total_count.log'
    
    if not os.path.exists(log_file):
        print("❌ No log file found")
        return None
    
    print("🔍 Analyzing log file...")
    
    # Read the log file
    with open(log_file, 'r') as f:
        lines = f.readlines()
    
    # Find the last successful user processing
    last_successful_user = 0
    last_401_error = 0
    
    for i, line in enumerate(lines):
        # Look for successful user processing
        if "Processing user" in line and "INFO" in line:
            match = re.search(r'Processing user (\d+)/200', line)
            if match:
                user_num = int(match.group(1))
                last_successful_user = max(last_successful_user, user_num)
        
        # Look for 401 errors
        if "401" in line and "ERROR" in line:
            # Find the user number for this error
            for j in range(max(0, i-5), min(len(lines), i+5)):
                if "Processing user" in lines[j] and "INFO" in lines[j]:
                    match = re.search(r'Processing user (\d+)/200', lines[j])
                    if match:
                        user_num = int(match.group(1))
                        last_401_error = max(last_401_error, user_num)
                        break
    
    print(f"📊 Last successful user: {last_successful_user}")
    print(f"⚠️  Last 401 error at user: {last_401_error}")
    
    # The resume point should be the last successful user
    resume_point = last_successful_user
    print(f"🎯 Recommended resume point: {resume_point}")
    
    return resume_point

def fix_progress_file(resume_point):
    """Fix the progress file to resume from the correct point."""
    progress_file = 'count_progress.json'
    
    if not os.path.exists(progress_file):
        print("❌ No progress file found")
        return
    
    print(f"🔧 Fixing progress file to resume from user {resume_point}...")
    
    # Load existing progress
    with open(progress_file, 'r') as f:
        progress = json.load(f)
    
    # Update the progress
    progress['processed_users'] = resume_point
    progress['last_update'] = datetime.now().isoformat()
    
    # Reset counters to 0 since we're starting over from this point
    progress['total_meetings'] = 0
    progress['total_files'] = 0
    progress['users_with_recordings'] = 0
    
    # Save the fixed progress
    with open(progress_file, 'w') as f:
        json.dump(progress, f, indent=2)
    
    print(f"✅ Progress file updated to resume from user {resume_point}")

def main():
    print("🔧 Zoom Extractor Progress Fixer")
    print("=" * 40)
    
    # Analyze log file
    resume_point = analyze_log_file()
    
    if resume_point is None:
        print("❌ Could not determine resume point")
        return
    
    # Ask user if they want to fix the progress
    response = input(f"\nFix progress file to resume from user {resume_point}? (y/n): ").lower().strip()
    
    if response in ['y', 'yes']:
        fix_progress_file(resume_point)
        print(f"\n✅ Fixed! Now run 'python total_count.py' to resume from user {resume_point}")
    else:
        print("❌ Progress file not modified")

if __name__ == "__main__":
    main()
