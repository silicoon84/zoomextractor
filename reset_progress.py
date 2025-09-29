#!/usr/bin/env python3
"""
Simple Progress Reset Script

Resets the progress file to resume from a specific user number.
"""

import json
import os
from datetime import datetime

def reset_progress(user_number):
    """Reset progress to start from a specific user number."""
    progress_file = 'count_progress.json'
    
    if not os.path.exists(progress_file):
        print("❌ No progress file found")
        return False
    
    print(f"🔧 Resetting progress to start from user {user_number}...")
    
    # Load existing progress
    with open(progress_file, 'r') as f:
        progress = json.load(f)
    
    # Update the progress
    progress['processed_users'] = user_number
    progress['last_update'] = datetime.now().isoformat()
    
    # Reset counters to 0 since we're starting over from this point
    progress['total_meetings'] = 0
    progress['total_files'] = 0
    progress['users_with_recordings'] = 0
    
    # Save the reset progress
    with open(progress_file, 'w') as f:
        json.dump(progress, f, indent=2)
    
    print(f"✅ Progress reset to start from user {user_number}")
    return True

def main():
    print("🔧 Simple Progress Reset")
    print("=" * 30)
    
    # Check if progress file exists
    if not os.path.exists('count_progress.json'):
        print("❌ No progress file found")
        return
    
    # Show current progress
    with open('count_progress.json', 'r') as f:
        progress = json.load(f)
    
    print(f"📊 Current progress: {progress.get('processed_users', 0)} users")
    print(f"📅 Last update: {progress.get('last_update', 'unknown')}")
    
    # Ask for user number to resume from
    try:
        user_number = int(input("\nEnter user number to resume from (0-200): "))
        
        if user_number < 0 or user_number > 200:
            print("❌ Invalid user number")
            return
        
        # Confirm the reset
        response = input(f"Reset progress to start from user {user_number}? (y/n): ").lower().strip()
        
        if response in ['y', 'yes']:
            if reset_progress(user_number):
                print(f"\n✅ Done! Run 'python total_count.py' to resume from user {user_number}")
        else:
            print("❌ Reset cancelled")
    
    except ValueError:
        print("❌ Invalid input")

if __name__ == "__main__":
    main()
