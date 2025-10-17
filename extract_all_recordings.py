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
    resume: bool = True,
    max_retries: int = 3
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
        resume: Resume from previous state if True
        max_retries: Maximum number of retry attempts for failed downloads (default: 3)
    """
    
    # Set default date range to 2 years if not specified
    if not from_date:
        from_date = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')
    if not to_date:
        to_date = datetime.now().strftime('%Y-%m-%d')
    
    print("[START] Enhanced Zoom Recordings Extractor")
    print("=" * 50)
    print(f"[DIR] Output Directory: {output_dir}")
    print(f"[USERS] User Filter: {user_filter or 'All users'}")
    print(f"[DATE] Date Range: {from_date} to {to_date}")
    print(f"[TRASH] Include Trash: {include_trash}")
    print(f"[INACTIVE] Include Inactive Users: {include_inactive_users}")
    print(f"[CONCURRENT] Max Concurrent: {max_concurrent}")
    print(f"[RETRIES] Max Retries per File: {max_retries}")
    print(f"[DRY-RUN] Dry Run: {dry_run}")
    print("=" * 50)
    
    # Initialize components
    auth = get_auth_from_env()
    headers = auth.get_auth_headers()
    
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Initialize state tracking
    state_file = output_path / "_metadata" / "extraction_state.json"
    state = ExtractionState(state_file)
    
    # Initialize components
    user_enumerator = UserEnumerator(headers, auth)
    recordings_lister = RecordingsLister(headers, auth)
    date_generator = DateWindowGenerator(from_date, to_date)
    structure = DirectoryStructure(output_dir)
    edge_handler = EdgeCaseHandler(headers, auth)
    
    if not dry_run:
        downloader = FileDownloader(headers, max_concurrent, auth=auth)
    
    # Get all users (active + inactive if requested)
    all_users = []
    
    # Always get active users
    print("[INFO] Getting active users...")
    active_users = list(user_enumerator.list_all_users(user_filter, user_type="active"))
    all_users.extend(active_users)
    print(f"   Found {len(active_users)} active users")
    
    # Get inactive users if requested
    if include_inactive_users:
        print("[INFO] Getting inactive users...")
        try:
            inactive_users = list(user_enumerator.list_all_users(user_filter, user_type="inactive"))
            all_users.extend(inactive_users)
            print(f"   Found {len(inactive_users)} inactive users")
        except Exception as e:
            print(f"   [WARN] Could not get inactive users: {e}")
    
    print(f"[TARGET] Total users to process: {len(all_users)}")
    
    if not all_users:
        print("[ERROR] No users found to process")
        return {"error": "No users found"}
    
    # Check for resume capability (after users are loaded)
    start_from_user = 0
    if resume:
        try:
            existing_state = state.get_progress_summary()
            if existing_state and existing_state.get("users", {}).get("processed", 0) > 0:
                start_from_user = existing_state["users"]["processed"]
                print(f"[RESUME] RESUMING from user {start_from_user + 1}/{len(all_users)}")
            else:
                print("[NEW] Starting fresh extraction")
        except Exception as e:
            print(f"[NEW] Starting fresh extraction (error checking state: {e})")
    
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
        
        print(f"\n[USER] [{user_idx}/{len(all_users)}] Processing {user_email} (status: {user_status})")
        
        try:
            # Validate user access
            user_warnings = edge_handler.check_account_restrictions(user)
            if user_warnings:
                print(f"   [WARN] User warnings: {user_warnings}")
            
            user_meetings = 0
            user_files = 0
            
            # Process each date window
            for start_date, end_date in date_generator.generate_monthly_windows():
                print(f"   [DATE] Processing {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
                
                try:
                    recordings = list(recordings_lister.list_user_recordings(
                        user_id, start_date, end_date, include_trash=include_trash
                    ))
                    
                    for recording in recordings:
                        meeting_id = recording.get("id", "unknown")
                        meeting_topic = recording.get("topic", "Unknown Topic")
                        
                        print(f"      [MEETING] Meeting: {meeting_topic}")
                        
                        # Validate meeting access
                        meeting_warnings = edge_handler.handle_meeting_type_restrictions(recording)
                        if meeting_warnings:
                            print(f"         [WARN] Meeting warnings: {meeting_warnings}")
                        
                        user_meetings += 1
                        
                        # Process files
                        files = recording.get("processed_files", [])
                        for file_info in files:
                            user_files += 1
                            
                            file_path = structure.get_file_path(user, recording, file_info)
                            
                            # Check if file already exists (resume capability)
                            if file_path.exists() and not dry_run:
                                file_size = file_path.stat().st_size
                                total_size += file_size
                                print(f"         [SKIP] Skipped (already exists): {file_path.name}")
                                # Mark file as processed in state
                                state.mark_file_processed(file_info.get("id", ""), "skipped")
                                continue
                            
                            if not dry_run:
                                # Download the file
                                try:
                                    # Get access token from auth headers
                                    access_token = headers.get("Authorization", "").replace("Bearer ", "")
                                    success, stats = downloader.download_file(file_info, file_path, access_token, max_retries=max_retries)
                                    
                                    if success:
                                        file_size = stats.get("file_size", 0)
                                        total_size += file_size
                                        print(f"         [OK] Downloaded: {file_path.name}")
                                        
                                        # Mark file as processed in state
                                        state.mark_file_processed(file_info.get("id", ""), "downloaded")
                                    else:
                                        print(f"         [ERROR] Failed after {max_retries} attempts: {file_path.name}")
                                        
                                        # Mark file as failed in state
                                        state.mark_file_processed(file_info.get("id", ""), "failed")
                                except Exception as e:
                                    print(f"         [ERROR] Download error: {e}")
                                    
                                    # Mark file as error in state
                                    state.mark_file_processed(file_info.get("id", ""), "error")
                            else:
                                # Dry run - just count
                                file_size = file_info.get("file_size", 0)
                                total_size += file_size
                                print(f"         [DRY] Would download: {file_info.get('file_type', 'unknown')} ({file_size} bytes)")
                                
                                # Mark file as dry run in state
                                state.mark_file_processed(file_info.get("id", ""), "dry_run")
                
                except Exception as e:
                    print(f"      [ERROR] Error processing date window: {e}")
                    continue
            
            print(f"   [SUMMARY] User summary: {user_meetings} meetings, {user_files} files")
            total_meetings += user_meetings
            total_files += user_files
            
        except Exception as e:
            print(f"   [ERROR] Error processing user {user_email}: {e}")
        
        # Always increment processed_users, regardless of success/failure
        processed_users += 1
        
        # Mark user as processed in state
        state.mark_user_processed(user_id)
        
        # Save progress every 10 users
        if processed_users % 10 == 0:
            state._save_state()
            print(f"   [SAVED] Progress saved ({processed_users}/{len(all_users)} users processed)")
    
    # Final summary
    print(f"\n[COMPLETE] EXTRACTION COMPLETE")
    print("=" * 50)
    print(f"[USERS] Users processed: {processed_users}/{len(all_users)}")
    print(f"[MEETINGS] Total meetings: {total_meetings}")
    print(f"[FILES] Total files: {total_files}")
    print(f"[SIZE] Total size: {total_size / (1024**3):.2f} GB")
    
    if dry_run:
        print(f"[DRY-RUN] DRY RUN - No files were actually downloaded")
        print(f"[TIP] Run without --dry-run to perform actual downloads")
    
    # Save final state
    state._save_state()
    
    # Save summary to log file
    log_file = output_path / "_metadata" / "extraction_summary.log"
    with open(log_file, "w") as f:
        f.write(f"Zoom Recordings Extraction Summary\n")
        f.write(f"===================================\n")
        f.write(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Users processed: {processed_users}/{len(all_users)}\n")
        f.write(f"Total meetings: {total_meetings}\n")
        f.write(f"Total files: {total_files}\n")
        f.write(f"Total size: {total_size / (1024**3):.2f} GB\n")
        f.write(f"Dry run: {dry_run}\n")
        f.write(f"Output directory: {output_path.absolute()}\n")
    
    print(f"[LOG] Summary saved to: {log_file}")
    
    return {
        "users_processed": processed_users,
        "total_users": len(all_users),
        "total_meetings": total_meetings,
        "total_files": total_files,
        "total_size_gb": total_size / (1024**3),
        "dry_run": dry_run,
        "log_file": str(log_file)
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
    parser.add_argument("--max-retries", type=int, default=3, help="Max retry attempts for failed downloads (default: 3)")
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
            resume=resume_enabled,
            max_retries=args.max_retries
        )
        
        if "error" in result:
            print(f"[ERROR] Extraction failed: {result['error']}")
            return 1
        
        print(f"[OK] Extraction completed successfully!")
        return 0
        
    except KeyboardInterrupt:
        print(f"\n[STOP] Extraction interrupted by user")
        return 1
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
