#!/usr/bin/env python3
"""
Quick Recording Count Script

Fast analysis to count recordings across your Zoom account.
"""

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

from zoom_extractor.auth import get_auth_from_env
from zoom_extractor.users import UserEnumerator
from zoom_extractor.recordings import RecordingsLister
from zoom_extractor.dates import DateWindowGenerator

def count_recordings():
    """Quick count of recordings."""
    print("🔍 Quick Recording Count")
    print("=" * 40)
    
    try:
        auth = get_auth_from_env()
        headers = auth.get_auth_headers()
        
        user_enumerator = UserEnumerator(headers)
        recordings_lister = RecordingsLister(headers)
        
        # Get all users
        print("📋 Getting users...")
        # Get all users (active + inactive for comprehensive coverage)
        active_users = list(user_enumerator.list_all_users(user_type="active"))
        inactive_users = list(user_enumerator.list_all_users(user_type="inactive"))
        users = active_users + inactive_users
        print(f"✅ Found {len(active_users)} active users and {len(inactive_users)} inactive users ({len(users)} total)")
        
        # Analyze different time periods
        time_periods = [
            ("Last 7 days", 7),
            ("Last 30 days", 30),
            ("Last 90 days", 90),
            ("Last year", 365),
            ("All 2024", None)
        ]
        
        for period_name, days in time_periods:
            print(f"\n📅 {period_name}:")
            
            if days:
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=days)
                date_gen = DateWindowGenerator(
                    start_date.strftime('%Y-%m-%d'),
                    end_date.strftime('%Y-%m-%d')
                )
            else:
                date_gen = DateWindowGenerator('2024-01-01', '2024-12-31')
            
            total_meetings = 0
            total_files = 0
            users_with_recordings = 0
            
            # Sample first 20 users for speed
            sample_size = min(20, len(users))
            sample_users = users[:sample_size]
            
            for i, user in enumerate(sample_users, 1):
                user_id = user["id"]
                user_email = user.get("email", "unknown")
                
                print(f"  [{i}/{sample_size}] {user_email[:30]}...", end=" ")
                
                user_meetings = 0
                user_files = 0
                
                try:
                    for start_date, end_date in date_gen.generate_monthly_windows():
                        meetings = list(recordings_lister.list_user_recordings(
                            user_id, start_date, end_date, include_trash=True
                        ))
                        
                        for meeting in meetings:
                            user_meetings += 1
                            user_files += len(meeting.get("processed_files", []))
                    
                    total_meetings += user_meetings
                    total_files += user_files
                    
                    if user_meetings > 0:
                        users_with_recordings += 1
                        print(f"✅ {user_meetings} meetings, {user_files} files")
                    else:
                        print("⭕ No recordings")
                
                except Exception as e:
                    print(f"❌ Error: {str(e)[:50]}")
                    continue
            
            # Scale up for full user base
            if sample_size > 0 and len(users) > 0:
                scale_factor = len(users) / sample_size
                estimated_meetings = int(total_meetings * scale_factor)
                estimated_files = int(total_files * scale_factor)
                estimated_users_with_recordings = int(users_with_recordings * scale_factor)
            else:
                estimated_meetings = total_meetings
                estimated_files = total_files
                estimated_users_with_recordings = users_with_recordings
            
            print(f"\n📊 Results ({period_name}):")
            print(f"  👥 Users with recordings: {estimated_users_with_recordings}/{len(users)}")
            print(f"  📅 Total meetings: {estimated_meetings:,}")
            print(f"  📁 Total files: {estimated_files:,}")
            print(f"  📈 Avg files/meeting: {estimated_files/max(estimated_meetings, 1):.1f}")
            
            if estimated_meetings > 0:
                print(f"  💾 Est. storage needed: ~{estimated_files * 50 / 1024:.1f} GB")
        
        print("\n✅ Analysis complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    count_recordings()
