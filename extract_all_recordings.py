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
from zoom_extractor.structure import DirectoryStructure
from zoom_extractor.state import ExtractionState
from zoom_extractor.edge_cases import EdgeCaseHandler

def extract_all_recordings(
    output_dir: str = "./zoom_recordings_all",
    user_filter: Optional[List[str]] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    include_trash: bool = True,
    include_inactive_users: bool = True,
    max_concurrent: int = 2,
    dry_run: bool = True,
    resume: bool = True
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
    state_file = output_path / "_metadata" / "extraction_state.json"
    state = ExtractionState(state_file)
    
    # Check for resume capability
    start_from_user = 0
    if resume:
        try:
            existing_state = state.get_progress_summary()
            if existing_state and existing_state.get("users", {}).get("processed", 0) > 0:
                start_from_user = existing_state["users"]["processed"]
                print(f"🔄 RESUMING from user {start_from_user + 1}/{len(all_users)}")
        except:
            print("🆕 Starting fresh extraction")
    
    # Initialize components
    user_enumerator = UserEnumerator(headers)
    recordings_lister = RecordingsLister(headers)
    date_generator = DateWindowGenerator(from_date, to_date)
    structure = DirectoryStructure(output_dir)
    edge_handler = EdgeCaseHandler(headers)
    
    if not dry_run:
        downloader = FileDownloader(headers, max_concurrent)
    
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
    
    # Start from the resume point if applicable
    users_to_process = all_users[start_from_user:] if start_from_user > 0 else all_users
    
    for user_idx, user in enumerate(users_to_process, start_from_user + 1):
        user_id = user["id"]
        user_email = user.get("email", "unknown")
        user_status = user.get("status", "unknown")
        
        print(f"\n👤 [{user_idx}/{len(all_users)}] Processing {user_email} (status: {user_status})")
        
        try:
            # Validate user access
            user_warnings = edge_handler.check_account_restrictions(user)
            if user_warnings:
                print(f"   ⚠️  User warnings: {user_warnings}")
            
            user_meetings = 0
            user_files = 0
            
            # Process each date window
            for start_date, end_date in date_generator.generate_monthly_windows():
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
                        meeting_warnings = edge_handler.handle_meeting_type_restrictions(recording)
                        if meeting_warnings:
                            print(f"         ⚠️  Meeting warnings: {meeting_warnings}")
                        
                        user_meetings += 1
                        
                        # Process files
                        files = recording.get("processed_files", [])
                        for file_info in files:
                            user_files += 1
                            
                            file_path = structure.get_file_path(user, recording, file_info)
                            
                            if not dry_run:
                                # Download the file
                                try:
                                    # Get access token from auth headers
                                    access_token = headers.get("Authorization", "").replace("Bearer ", "")
                                    success, stats = downloader.download_file(file_info, file_path, access_token)
                                    
                                    if success:
                                        file_size = stats.get("file_size", 0)
                                        total_size += file_size
                                        print(f"         ✅ Downloaded: {file_path.name}")
                                        
                                        # Mark file as processed in state
                                        state.mark_file_processed(file_info.get("id", ""), "downloaded")
                                    else:
                                        print(f"         ❌ Failed: {file_path.name}")
                                        
                                        # Mark file as failed in state
                                        state.mark_file_processed(file_info.get("id", ""), "failed")
                                except Exception as e:
                                    print(f"         ❌ Download error: {e}")
                                    
                                    # Mark file as error in state
                                    state.mark_file_processed(file_info.get("id", ""), "error")
                            else:
                                # Dry run - just count
                                file_size = file_info.get("file_size", 0)
                                total_size += file_size
                                print(f"         🔍 Would download: {file_info.get('file_type', 'unknown')} ({file_size} bytes)")
                                
                                # Mark file as dry run in state
                                state.mark_file_processed(file_info.get("id", ""), "dry_run")
                
                except Exception as e:
                    print(f"      ❌ Error processing date window: {e}")
                    continue
            
            print(f"   📊 User summary: {user_meetings} meetings, {user_files} files")
            total_meetings += user_meetings
            total_files += user_files
            
        except Exception as e:
            print(f"   ❌ Error processing user {user_email}: {e}")
        
        # Always increment processed_users, regardless of success/failure
        processed_users += 1
        
        # Save progress every 10 users
        if processed_users % 10 == 0:
            state._save_state()
            print(f"   💾 Progress saved ({processed_users}/{len(all_users)} users processed)")
    
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
    state._save_state()
    
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
    parser.add_argument("--resume", action="store_true", default=True, help="Resume from previous state (default: True)")
    parser.add_argument("--no-resume", action="store_true", help="Don't resume, start fresh")
    
    args = parser.parse_args()
    
    try:
        # Set default date range if not provided
        from_date = args.from_date or (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')  # 2 years ago
        to_date = args.to_date or datetime.now().strftime('%Y-%m-%d')  # Today
        
        # Ensure to_date is not in the future
        today = datetime.now().strftime('%Y-%m-%d')
        if to_date > today:
            to_date = today
        
        # Determine resume setting
        resume_enabled = args.resume and not args.no_resume
        
        result = extract_all_recordings(
            output_dir=args.output_dir,
            user_filter=args.user_filter,
            from_date=from_date,
            to_date=to_date,
            include_trash=args.include_trash,
            include_inactive_users=args.include_inactive,
            max_concurrent=args.max_concurrent,
            dry_run=args.dry_run,
            resume=resume_enabled
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
