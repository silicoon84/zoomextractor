#!/usr/bin/env python3
"""
Enhanced Dry Run with Detailed Report
Provides comprehensive breakdown of all recordings that would be downloaded,
including exact file counts, sizes, and storage requirements.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
from collections import defaultdict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from zoom_extractor.auth import get_auth_from_env
from zoom_extractor.users import UserEnumerator
from zoom_extractor.recordings import RecordingsLister
from zoom_extractor.dates import DateWindowGenerator
from zoom_extractor.structure import DirectoryStructure

def detailed_dry_run(
    output_dir: str = "./zoom_recordings",
    user_filter: Optional[List[str]] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    include_trash: bool = True,
    include_inactive_users: bool = True,
    max_sample_users: int = None
):
    """
    Run detailed dry run with comprehensive reporting.
    
    Args:
        output_dir: Directory where files would be saved
        user_filter: Optional list of specific user emails/IDs
        from_date: Start date (YYYY-MM-DD)
        to_date: End date (YYYY-MM-DD)
        include_trash: Whether to include trash recordings
        include_inactive_users: Whether to include inactive users
        max_sample_users: Max users to sample (None = all)
    """
    
    print("🔍 Detailed Zoom Recordings Dry Run Report")
    print("=" * 60)
    print(f"📁 Output Directory: {output_dir}")
    print(f"👥 User Filter: {user_filter or 'All users'}")
    print(f"📅 Date Range: {from_date or 'Default'} to {to_date or 'Default'}")
    print(f"🗑️  Include Trash: {include_trash}")
    print(f"👻 Include Inactive Users: {include_inactive_users}")
    print("=" * 60)
    
    # Initialize components
    auth = get_auth_from_env()
    headers = auth.get_auth_headers()
    
    user_enumerator = UserEnumerator(headers)
    recordings_lister = RecordingsLister(headers)
    structure = DirectoryStructure(output_dir)
    
    # Set default date range if not provided
    if not from_date:
        from_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    if not to_date:
        to_date = datetime.now().strftime('%Y-%m-%d')
    
    date_generator = DateWindowGenerator(from_date, to_date)
    
    # Get all users
    print("📋 Getting users...")
    active_users = list(user_enumerator.list_all_users(user_filter, user_type="active"))
    inactive_users = []
    
    if include_inactive_users:
        inactive_users = list(user_enumerator.list_all_users(user_filter, user_type="inactive"))
    
    all_users = active_users + inactive_users
    
    if max_sample_users and len(all_users) > max_sample_users:
        print(f"📊 Sampling {max_sample_users} users out of {len(all_users)} total")
        all_users = all_users[:max_sample_users]
    
    print(f"✅ Found {len(active_users)} active users and {len(inactive_users)} inactive users")
    print(f"🎯 Processing {len(all_users)} users for detailed analysis")
    
    # Detailed tracking
    report = {
        "timestamp": datetime.now().isoformat(),
        "config": {
            "output_dir": output_dir,
            "user_filter": user_filter,
            "from_date": from_date,
            "to_date": to_date,
            "include_trash": include_trash,
            "include_inactive_users": include_inactive_users,
            "total_users_analyzed": len(all_users)
        },
        "summary": {
            "users_with_recordings": 0,
            "users_without_recordings": 0,
            "total_meetings": 0,
            "total_files": 0,
            "total_size_bytes": 0,
            "total_size_gb": 0,
            "file_types": defaultdict(int),
            "recording_types": defaultdict(int)
        },
        "users": [],
        "meetings": [],
        "files": []
    }
    
    # Process each user
    for user_idx, user in enumerate(all_users, 1):
        user_id = user["id"]
        user_email = user.get("email", "unknown")
        user_status = user.get("status", "unknown")
        
        print(f"\n👤 [{user_idx}/{len(all_users)}] Analyzing {user_email} ({user_status})")
        
        user_data = {
            "email": user_email,
            "status": user_status,
            "meetings": [],
            "total_meetings": 0,
            "total_files": 0,
            "total_size_bytes": 0
        }
        
        user_has_recordings = False
        
        # Process each date window
        for start_date, end_date in date_generator.generate_monthly_windows():
            try:
                recordings = list(recordings_lister.list_user_recordings(
                    user_id, start_date, end_date, include_trash=include_trash
                ))
                
                for recording in recordings:
                    meeting_id = recording.get("id", "unknown")
                    meeting_topic = recording.get("topic", "Unknown Topic")
                    meeting_type = recording.get("type", "unknown")
                    meeting_start = recording.get("start_time", "unknown")
                    
                    user_has_recordings = True
                    report["summary"]["total_meetings"] += 1
                    user_data["total_meetings"] += 1
                    
                    meeting_data = {
                        "id": meeting_id,
                        "topic": meeting_topic,
                        "type": meeting_type,
                        "start_time": meeting_start,
                        "files": [],
                        "total_files": 0,
                        "total_size_bytes": 0
                    }
                    
                    # Process files
                    processed_files = recording.get("processed_files", [])
                    for file_info in processed_files:
                        file_type = file_info.get("file_type", "unknown")
                        file_size = file_info.get("file_size", 0)
                        file_extension = file_info.get("file_extension", "")
                        download_url = file_info.get("download_url", "")
                        
                        if download_url:  # Only count files with download URLs
                            report["summary"]["total_files"] += 1
                            report["summary"]["total_size_bytes"] += file_size
                            report["summary"]["file_types"][file_type] += 1
                            report["summary"]["recording_types"][meeting_type] += 1
                            
                            user_data["total_files"] += 1
                            user_data["total_size_bytes"] += file_size
                            
                            meeting_data["total_files"] += 1
                            meeting_data["total_size_bytes"] += file_size
                            
                            # Generate output path
                            output_path = structure.get_file_path(user, recording, file_info)
                            
                            file_data = {
                                "user_email": user_email,
                                "meeting_topic": meeting_topic,
                                "file_type": file_type,
                                "file_extension": file_extension,
                                "file_size": file_size,
                                "file_size_mb": file_size / (1024 * 1024),
                                "output_path": str(output_path),
                                "download_url": download_url[:50] + "..." if len(download_url) > 50 else download_url
                            }
                            
                            meeting_data["files"].append(file_data)
                            report["files"].append(file_data)
                    
                    user_data["meetings"].append(meeting_data)
                    report["meetings"].append(meeting_data)
            
            except Exception as e:
                print(f"   ❌ Error processing date window: {e}")
                continue
        
        if user_has_recordings:
            report["summary"]["users_with_recordings"] += 1
            print(f"   ✅ {user_data['total_meetings']} meetings, {user_data['total_files']} files, {user_data['total_size_bytes'] / (1024**3):.2f} GB")
        else:
            report["summary"]["users_without_recordings"] += 1
            print(f"   ⚪ No recordings found")
        
        report["users"].append(user_data)
    
    # Calculate final totals
    report["summary"]["total_size_gb"] = report["summary"]["total_size_bytes"] / (1024**3)
    
    # Generate detailed report
    print(f"\n📊 DETAILED DRY RUN REPORT")
    print("=" * 60)
    print(f"👥 Users Analyzed: {report['config']['total_users_analyzed']}")
    print(f"   ✅ With Recordings: {report['summary']['users_with_recordings']}")
    print(f"   ⚪ Without Recordings: {report['summary']['users_without_recordings']}")
    print(f"")
    print(f"📹 Total Meetings: {report['summary']['total_meetings']}")
    print(f"📁 Total Files: {report['summary']['total_files']}")
    print(f"💾 Total Size: {report['summary']['total_size_gb']:.2f} GB")
    print(f"")
    print(f"📋 File Types Breakdown:")
    for file_type, count in sorted(report['summary']['file_types'].items()):
        print(f"   {file_type}: {count} files")
    print(f"")
    print(f"🎬 Recording Types:")
    for rec_type, count in sorted(report['summary']['recording_types'].items()):
        print(f"   {rec_type}: {count} meetings")
    
    # Top users by size
    print(f"\n🏆 Top 10 Users by Storage Usage:")
    users_by_size = sorted(
        [u for u in report['users'] if u['total_size_bytes'] > 0],
        key=lambda x: x['total_size_bytes'],
        reverse=True
    )
    
    for i, user in enumerate(users_by_size[:10], 1):
        size_gb = user['total_size_bytes'] / (1024**3)
        print(f"   {i}. {user['email']}: {user['total_meetings']} meetings, {user['total_files']} files, {size_gb:.2f} GB")
    
    # Save detailed report
    report_file = f"detailed_dry_run_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n💾 Detailed report saved to: {report_file}")
    print(f"📁 This file contains complete breakdown of all meetings, files, and paths")
    
    return report

def main():
    """Main entry point with command line interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Detailed Zoom Recordings Dry Run")
    parser.add_argument("--output-dir", default="./zoom_recordings", help="Output directory")
    parser.add_argument("--user-filter", nargs="*", help="Filter by user emails/IDs")
    parser.add_argument("--from-date", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--to-date", help="End date (YYYY-MM-DD)")
    parser.add_argument("--include-trash", action="store_true", default=True, help="Include trash recordings")
    parser.add_argument("--include-inactive", action="store_true", default=True, help="Include inactive users")
    parser.add_argument("--max-sample", type=int, help="Max users to sample for analysis")
    
    args = parser.parse_args()
    
    try:
        report = detailed_dry_run(
            output_dir=args.output_dir,
            user_filter=args.user_filter,
            from_date=args.from_date,
            to_date=args.to_date,
            include_trash=args.include_trash,
            include_inactive_users=args.include_inactive,
            max_sample_users=args.max_sample
        )
        
        print(f"\n✅ Detailed dry run completed successfully!")
        return 0
        
    except KeyboardInterrupt:
        print(f"\n⏹️  Dry run interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
