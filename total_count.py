#!/usr/bin/env python3
"""
Simple Total Count Script

Gives total counts across the entire organization for all time.
Includes logging and progress saving to survive session interruptions.
"""

import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from zoom_extractor.auth import get_auth_from_env
from zoom_extractor.users import UserEnumerator
from zoom_extractor.recordings import RecordingsLister
from zoom_extractor.dates import DateWindowGenerator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('total_count.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def save_progress(progress_data):
    """Save progress to file."""
    with open('count_progress.json', 'w') as f:
        json.dump(progress_data, f, indent=2, default=str)

def load_progress():
    """Load progress from file."""
    try:
        if os.path.exists('count_progress.json'):
            with open('count_progress.json', 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Could not load progress: {e}")
    return None

def total_count():
    """Get total counts across entire organization."""
    logger.info("🔍 Zoom Organization Total Counts")
    print("🔍 Zoom Organization Total Counts")
    print("=" * 50)
    
    try:
        # Check for existing progress
        progress = load_progress()
        if progress:
            print(f"📋 Found existing progress from {progress.get('last_update', 'unknown')}")
            print(f"   Processed: {progress.get('processed_users', 0)} users")
            response = input("Resume from where you left off? (y/n): ").lower().strip()
            if response in ['y', 'yes']:
                start_from = progress.get('processed_users', 0)
                total_meetings = progress.get('total_meetings', 0)
                total_files = progress.get('total_files', 0)
                users_with_recordings = progress.get('users_with_recordings', 0)
                processed_users = progress.get('processed_users', 0)
            else:
                start_from = 0
                total_meetings = 0
                total_files = 0
                users_with_recordings = 0
                processed_users = 0
        else:
            start_from = 0
            total_meetings = 0
            total_files = 0
            users_with_recordings = 0
            processed_users = 0
        
        auth = get_auth_from_env()
        headers = auth.get_auth_headers()
        
        user_enumerator = UserEnumerator(headers)
        recordings_lister = RecordingsLister(headers)
        
        # Get all users (active + inactive for comprehensive coverage)
        logger.info("📋 Getting users...")
        print("📋 Getting users...")
        active_users = list(user_enumerator.list_all_users(user_type="active"))
        inactive_users = list(user_enumerator.list_all_users(user_type="inactive"))
        users = active_users + inactive_users
        logger.info(f"✅ Found {len(active_users)} active users and {len(inactive_users)} inactive users ({len(users)} total)")
        print(f"✅ Found {len(active_users)} active users and {len(inactive_users)} inactive users ({len(users)} total)")
        
        # Set up date range for all time (2020-2025 to cover everything)
        date_generator = DateWindowGenerator('2020-01-01', '2025-12-31')
        
        logger.info(f"📊 Analyzing recordings for {len(users)} users (starting from {start_from})...")
        print(f"\n📊 Analyzing recordings for {len(users)} users...")
        print("This may take a few minutes...\n")
        print("💾 Progress is saved every 10 users to count_progress.json")
        print("📝 Full log is saved to total_count.log\n")
        
        for i, user in enumerate(users[start_from:], start_from + 1):
            user_id = user["id"]
            user_email = user.get("email", "unknown")
            
            logger.info(f"Processing user {i}/{len(users)}: {user_email}")
            
            # Show progress every 10 users
            if i % 10 == 0 or i == len(users):
                progress_percent = i/len(users)*100
                logger.info(f"Progress: {i}/{len(users)} users ({progress_percent:.1f}%)")
                print(f"Progress: {i}/{len(users)} users ({progress_percent:.1f}%)")
                
                # Save progress
                save_progress({
                    'last_update': datetime.now().isoformat(),
                    'processed_users': i,
                    'total_meetings': total_meetings,
                    'total_files': total_files,
                    'users_with_recordings': users_with_recordings,
                    'total_users': len(users)
                })
            
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
                processed_users = i
                
                if user_meetings > 0:
                    users_with_recordings += 1
                    logger.info(f"  ✅ {user_meetings} meetings, {user_files} files")
                else:
                    logger.info(f"  ⭕ No recordings")
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Error processing {user_email}: {e}")
                
                # Check if it's a token expiration error
                if "401" in error_msg or "Unauthorized" in error_msg:
                    logger.warning("Token expired, refreshing...")
                    try:
                        # Refresh the auth headers
                        auth = get_auth_from_env()
                        headers = auth.get_auth_headers()
                        
                        # Update the components with new headers
                        user_enumerator = UserEnumerator(headers)
                        recordings_lister = RecordingsLister(headers)
                        
                        logger.info("Token refreshed, retrying user...")
                        
                        # Retry the current user
                        try:
                            user_meetings = 0
                            user_files = 0
                            
                            for start_date, end_date in date_generator.generate_monthly_windows():
                                meetings = list(recordings_lister.list_user_recordings(
                                    user_id, start_date, end_date, include_trash=True
                                ))
                                
                                for meeting in meetings:
                                    user_meetings += 1
                                    user_files += len(meeting.get("processed_files", []))
                            
                            total_meetings += user_meetings
                            total_files += user_files
                            processed_users = i
                            
                            if user_meetings > 0:
                                users_with_recordings += 1
                                logger.info(f"  ✅ {user_meetings} meetings, {user_files} files (after retry)")
                            else:
                                logger.info(f"  ⭕ No recordings (after retry)")
                        
                        except Exception as retry_error:
                            logger.error(f"Retry failed for {user_email}: {retry_error}")
                            continue
                    
                    except Exception as refresh_error:
                        logger.error(f"Token refresh failed: {refresh_error}")
                        continue
                else:
                    # Non-token error, just skip
                    continue
        
        # Save final results
        final_results = {
            'total_users': len(users),
            'users_with_recordings': users_with_recordings,
            'total_meetings': total_meetings,
            'total_files': total_files,
            'average_files_per_meeting': total_files/max(total_meetings, 1),
            'average_meetings_per_user': total_meetings/max(users_with_recordings, 1),
            'estimated_storage_gb': (total_files * 50) / 1024,
            'completed_at': datetime.now().isoformat()
        }
        
        save_progress(final_results)
        
        # Results
        logger.info("=" * 50)
        logger.info("📊 TOTAL ORGANIZATION COUNTS")
        logger.info("=" * 50)
        logger.info(f"👥 Total Users: {len(users):,}")
        logger.info(f"👥 Users with Recordings: {users_with_recordings:,}")
        logger.info(f"📅 Total Meetings with Recordings: {total_meetings:,}")
        logger.info(f"📁 Total Recording Files: {total_files:,}")
        logger.info(f"📈 Average Files per Meeting: {total_files/max(total_meetings, 1):.1f}")
        logger.info(f"📈 Average Meetings per User: {total_meetings/max(users_with_recordings, 1):.1f}")
        logger.info(f"💾 Estimated Storage Needed: ~{(total_files * 50) / 1024:.1f} GB")
        
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
        print("📝 Full results saved to count_progress.json")
        print("📋 Full log saved to total_count.log")
        
        # Clean up progress file since we're done
        if os.path.exists('count_progress.json'):
            os.rename('count_progress.json', 'count_results.json')
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        print(f"❌ Error: {e}")
        print("📝 Check total_count.log for details")

if __name__ == "__main__":
    total_count()
