#!/usr/bin/env python3
"""
Simple Total Count Script

Gives total counts across the entire organization for all time.
"""

import os
from dotenv import load_dotenv

load_dotenv()

from zoom_extractor.auth import get_auth_from_env
from zoom_extractor.users import UserEnumerator
from zoom_extractor.recordings import RecordingsLister
from zoom_extractor.dates import DateWindowGenerator

def total_count():
    """Get total counts across entire organization."""
    print("🔍 Zoom Organization Total Counts")
    print("=" * 50)
    
    try:
        auth = get_auth_from_env()
        headers = auth.get_auth_headers()
        
        user_enumerator = UserEnumerator(headers)
        recordings_lister = RecordingsLister(headers)
        
        # Get all users
        print("📋 Getting users...")
        users = list(user_enumerator.list_all_users())
        print(f"✅ Found {len(users)} total users")
        
        # Set up date range for all time (2020-2025 to cover everything)
        date_generator = DateWindowGenerator('2020-01-01', '2025-12-31')
        
        total_meetings = 0
        total_files = 0
        users_with_recordings = 0
        
        print(f"\n📊 Analyzing recordings for {len(users)} users...")
        print("This may take a few minutes...\n")
        
        for i, user in enumerate(users, 1):
            user_id = user["id"]
            user_email = user.get("email", "unknown")
            
            # Show progress every 10 users
            if i % 10 == 0 or i == len(users):
                print(f"Progress: {i}/{len(users)} users ({i/len(users)*100:.1f}%)")
            
            user_meetings = 0
            user_files = 0
            
            try:
                # Check all date windows
                for start_date, end_date in date_generator.generate_monthly_windows():
                    meetings = list(recordings_lister.list_user_recordings(
                        user_id, start_date, end_date
                    ))
                    
                    for meeting in meetings:
                        user_meetings += 1
                        user_files += len(meeting.get("processed_files", []))
                
                total_meetings += user_meetings
                total_files += user_files
                
                if user_meetings > 0:
                    users_with_recordings += 1
                
            except Exception as e:
                # Skip users with errors
                continue
        
        # Results
        print("\n" + "=" * 50)
        print("📊 TOTAL ORGANIZATION COUNTS")
        print("=" * 50)
        print(f"👥 Total Users: {len(users):,}")
        print(f"👥 Users with Recordings: {users_with_recordings:,}")
        print(f"📅 Total Meetings with Recordings: {total_meetings:,}")
        print(f"📁 Total Recording Files: {total_files:,}")
        
        if total_meetings > 0:
            print(f"📈 Average Files per Meeting: {total_files/total_meetings:.1f}")
        
        if users_with_recordings > 0:
            print(f"📈 Average Meetings per User: {total_meetings/users_with_recordings:.1f}")
        
        # Storage estimate (rough estimate: 50MB per file)
        estimated_storage_gb = (total_files * 50) / 1024
        print(f"💾 Estimated Storage Needed: ~{estimated_storage_gb:.1f} GB")
        
        print("\n✅ Analysis complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    total_count()
