#!/usr/bin/env python3
"""
Enhanced Zoom Recordings Extractor - Finds ALL recordings including:
- Active users
- Inactive/deleted users  
- Trash recordings
- Extended date ranges
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

from zoom_extractor.auth import get_auth_from_env
from zoom_extractor.users import UserEnumerator
from zoom_extractor.recordings import RecordingsLister
from zoom_extractor.dates import DateWindowGenerator
from zoom_extractor.downloader import FileDownloader
from zoom_extractor.structure import get_output_path, sanitize_filename
from zoom_extractor.state import ExtractionState
from zoom_extractor.edge_cases import validate_user_access, validate_meeting_access

def extract_all_recordings(
    output_dir: str = "./zoom_recordings_all",
    user_filter: Optional[List[str]] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    include_trash: bool = True,
    include_inactive_users: bool = True,
    max_concurrent: int = 2,
    dry_run: bool = True
):
    """
    Extract recordings from ALL users including inactive/deleted ones.
    
    Args:
        output_dir: Directory to save recordings
        user_filter: Optional list of specific user emails/IDs
        from_date: Start date (YYYY-MM-DD), defaults to 2 years ago
        to_date: End date (YYYY-MM-DD), defaults to today
        include_trash: Whether to include recordings in trash
        include_inactive_users: Whether to include inactive/deleted users
        max_concurrent: Maximum concurrent downloads
        dry_run: If True, don't actually download files
    """
    
    # Set default date range to 2 years if not specified
    if not from_date:
        from_date = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')
    if not to_date:
        to_date = datetime.now().strftime('%Y-%m-%d')
    
    print("🚀 Enhanced Zoom Recordings Extractor")
    print("=" * 50)
    print(f"📁 Output Directory: {output_dir}")
    print(f"👥 User Filter: {user_filter or 'All users'}")
    print(f"📅 Date Range: {from_date} to {to_date}")
    print(f"🗑️  Include Trash: {include_trash}")
    print(f"👻 Include Inactive Users: {include_inactive_users}")
    print(f"⚡ Max Concurrent: {max_concurrent}")
    print(f"🧪 Dry Run: {dry_run}")
    print("=" * 50)
    
    # Initialize components
    auth = get_auth_from_env()
    headers = auth.get_auth_headers()
    
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Initialize state tracking
    state = ExtractionState(output_path)
    
    # Initialize components
    user_enumerator = UserEnumerator(headers)
    recordings_lister = RecordingsLister(headers)
    date_generator = DateWindowGenerator(from_date, to_date)
    
    if not dry_run:
        downloader = FileDownloader(max_concurrent)
    
    # Get all users (active + inactive if requested)
    all_users = []
    
    # Always get active users
    print("📋 Getting active users...")
    active_users = list(user_enumerator.list_all_users(user_filter, user_type="active"))
    all_users.extend(active_users)
    print(f"   Found {len(active_users)} active users")
    
    # Get inactive users if requested
    if include_inactive_users:
        print("📋 Getting inactive users...")
        try:
            inactive_users = list(user_enumerator.list_all_users(user_filter, user_type="inactive"))
            all_users.extend(inactive_users)
            print(f"   Found {len(inactive_users)} inactive users")
        except Exception as e:
            print(f"   ⚠️  Could not get inactive users: {e}")
    
    print(f"🎯 Total users to process: {len(all_users)}")
    
    if not all_users:
        print("❌ No users found to process")
        return {"error": "No users found"}
    
    # Process all users
    total_meetings = 0
    total_files = 0
    total_size = 0
    processed_users = 0
    
    for user_idx, user in enumerate(all_users, 1):
        user_id = user["id"]
        user_email = user.get("email", "unknown")
        user_status = user.get("status", "unknown")
        
        print(f"\n👤 [{user_idx}/{len(all_users)}] Processing {user_email} (status: {user_status})")
        
        try:
            # Validate user access
            user_warnings = validate_user_access(user)
            if user_warnings:
                print(f"   ⚠️  User warnings: {user_warnings}")
            
            user_meetings = 0
            user_files = 0
            
            # Process each date window
            for start_date, end_date in date_generator.generate_windows():
                print(f"   📅 Processing {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
                
                try:
                    recordings = list(recordings_lister.list_user_recordings(
                        user_id, start_date, end_date, include_trash=include_trash
                    ))
                    
                    for recording in recordings:
                        meeting_id = recording.get("id", "unknown")
                        meeting_topic = recording.get("topic", "Unknown Topic")
                        
                        print(f"      📹 Meeting: {meeting_topic}")
                        
                        # Validate meeting access
                        meeting_warnings = validate_meeting_access(recording)
                        if meeting_warnings:
                            print(f"         ⚠️  Meeting warnings: {meeting_warnings}")
                        
                        user_meetings += 1
                        
                        # Process files
                        files = recording.get("files", [])
                        for file_info in files:
                            processed_file = recordings_lister.process_file(file_info)
                            if processed_file:
                                user_files += 1
                                
                                if not dry_run:
                                    # Download the file
                                    download_url = processed_file["download_url"]
                                    file_path = get_output_path(
                                        output_path, user, recording, processed_file
                                    )
                                    
                                    try:
                                        success = downloader.download_file(download_url, file_path)
                                        if success:
                                            file_size = file_info.get("file_size", 0)
                                            total_size += file_size
                                            print(f"         ✅ Downloaded: {file_path.name}")
                                        else:
                                            print(f"         ❌ Failed: {file_path.name}")
                                    except Exception as e:
                                        print(f"         ❌ Download error: {e}")
                                else:
                                    # Dry run - just count
                                    file_size = file_info.get("file_size", 0)
                                    total_size += file_size
                                    print(f"         🔍 Would download: {processed_file.get('file_type', 'unknown')} ({file_size} bytes)")
                        
                        # Log to state
                        state.log_meeting(user, recording, files)
                
                except Exception as e:
                    print(f"      ❌ Error processing date window: {e}")
                    continue
            
            print(f"   📊 User summary: {user_meetings} meetings, {user_files} files")
            total_meetings += user_meetings
            total_files += user_files
            processed_users += 1
            
            # Save progress every 10 users
            if processed_users % 10 == 0:
                state.save_state()
                print(f"   💾 Progress saved ({processed_users}/{len(all_users)} users processed)")
        
        except Exception as e:
            print(f"   ❌ Error processing user {user_email}: {e}")
            continue
    
    # Final summary
    print(f"\n🎉 EXTRACTION COMPLETE")
    print("=" * 50)
    print(f"👥 Users processed: {processed_users}/{len(all_users)}")
    print(f"📹 Total meetings: {total_meetings}")
    print(f"📁 Total files: {total_files}")
    print(f"💾 Total size: {total_size / (1024**3):.2f} GB")
    
    if dry_run:
        print(f"🧪 DRY RUN - No files were actually downloaded")
        print(f"💡 Run without --dry-run to perform actual downloads")
    
    # Save final state
    state.save_state()
    
    return {
        "users_processed": processed_users,
        "total_users": len(all_users),
        "total_meetings": total_meetings,
        "total_files": total_files,
        "total_size_gb": total_size / (1024**3),
        "dry_run": dry_run
    }

def main():
    """Main entry point with command line interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced Zoom Recordings Extractor")
    parser.add_argument("--output-dir", default="./zoom_recordings_all", help="Output directory")
    parser.add_argument("--user-filter", nargs="*", help="Filter by user emails/IDs")
    parser.add_argument("--from-date", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--to-date", help="End date (YYYY-MM-DD)")
    parser.add_argument("--include-trash", action="store_true", default=True, help="Include trash recordings")
    parser.add_argument("--include-inactive", action="store_true", default=True, help="Include inactive users")
    parser.add_argument("--max-concurrent", type=int, default=2, help="Max concurrent downloads")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    
    args = parser.parse_args()
    
    try:
        result = extract_all_recordings(
            output_dir=args.output_dir,
            user_filter=args.user_filter,
            from_date=args.from_date,
            to_date=args.to_date,
            include_trash=args.include_trash,
            include_inactive_users=args.include_inactive,
            max_concurrent=args.max_concurrent,
            dry_run=args.dry_run
        )
        
        if "error" in result:
            print(f"❌ Extraction failed: {result['error']}")
            return 1
        
        print(f"✅ Extraction completed successfully!")
        return 0
        
    except KeyboardInterrupt:
        print(f"\n⏹️  Extraction interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
