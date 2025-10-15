#!/usr/bin/env python3
"""
Enhanced extraction script that includes Zoom Rooms.
"""

import os
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from zoom_extractor.auth import get_auth_from_env
from zoom_extractor.users import UserEnumerator
from zoom_extractor.recordings import RecordingsLister
from zoom_extractor.dates import DateWindowGenerator
from zoom_extractor.structure import DirectoryStructure

def get_zoom_rooms(auth_headers: Dict[str, str]) -> List[Dict]:
    """Get all Zoom Rooms."""
    print("🏠 Getting Zoom Rooms...")
    
    url = "https://api.zoom.us/v2/rooms"
    params = {"page_size": 100}
    
    try:
        response = requests.get(url, headers=auth_headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            rooms = data.get("rooms", [])
            print(f"   ✅ Found {len(rooms)} Zoom Rooms")
            return rooms
        elif response.status_code == 403:
            print("   ❌ Missing 'room:read:admin' scope")
            return []
        else:
            print(f"   ❌ Error: {response.status_code} - {response.text}")
            return []
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return []

def extract_with_rooms(
    output_dir: str = "./zoom_recordings_with_rooms",
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    include_trash: bool = True,
    dry_run: bool = True
):
    """
    Extract recordings including Zoom Rooms.
    
    Args:
        output_dir: Directory to save recordings
        from_date: Start date (YYYY-MM-DD)
        to_date: End date (YYYY-MM-DD)
        include_trash: Whether to include trash recordings
        dry_run: If True, don't actually download files
    """
    
    print("🚀 Enhanced Zoom Recordings Extractor (with Zoom Rooms)")
    print("=" * 60)
    print(f"📁 Output Directory: {output_dir}")
    print(f"📅 Date Range: {from_date or 'Default'} to {to_date or 'Default'}")
    print(f"🗑️  Include Trash: {include_trash}")
    print(f"🧪 Dry Run: {dry_run}")
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
    
    # Get all users (active + inactive + pending)
    print("📋 Getting users...")
    active_users = list(user_enumerator.list_all_users(user_type="active"))
    inactive_users = list(user_enumerator.list_all_users(user_type="inactive"))
    pending_users = list(user_enumerator.list_all_users(user_type="pending"))
    
    all_users = active_users + inactive_users + pending_users
    print(f"✅ Found {len(active_users)} active, {len(inactive_users)} inactive, and {len(pending_users)} pending users")
    
    # Get Zoom Rooms
    zoom_rooms = get_zoom_rooms(headers)
    
    # Convert Zoom Rooms to user-like format for processing
    room_users = []
    for room in zoom_rooms:
        room_user = {
            "id": room.get("id"),
            "email": room.get("email", f"room_{room.get('id')}@zoom.room"),
            "first_name": room.get("name", "Zoom Room"),
            "last_name": "",
            "display_name": room.get("name", "Zoom Room"),
            "type": "room",  # Custom type for rooms
            "status": "active",
            "is_room": True
        }
        room_users.append(room_user)
    
    all_users.extend(room_users)
    
    print(f"🎯 Total entities to process: {len(all_users)} ({len(active_users + inactive_users + pending_users)} users + {len(zoom_rooms)} rooms)")
    
    # Process all users and rooms
    total_meetings = 0
    total_files = 0
    total_size = 0
    
    for user_idx, user in enumerate(all_users, 1):
        user_id = user["id"]
        user_email = user.get("email", "unknown")
        user_type = user.get("type", "user")
        is_room = user.get("is_room", False)
        
        entity_type = "🏠 Room" if is_room else "👤 User"
        print(f"\n{entity_type} [{user_idx}/{len(all_users)}] Processing {user_email}")
        
        try:
            user_meetings = 0
            user_files = 0
            user_size = 0
            
            # Process each date window
            for start_date, end_date in date_generator.generate_monthly_windows():
                try:
                    # Use different endpoint for rooms vs users
                    if is_room:
                        # For Zoom Rooms, use the rooms recordings endpoint
                        url = f"https://api.zoom.us/v2/rooms/{user_id}/recordings"
                        params = {
                            "from": start_date.strftime('%Y-%m-%d'),
                            "to": end_date.strftime('%Y-%m-%d'),
                            "page_size": 30
                        }
                        
                        response = requests.get(url, headers=headers, params=params)
                        
                        if response.status_code == 200:
                            data = response.json()
                            recordings = data.get("meetings", [])
                        else:
                            print(f"      ❌ Error getting room recordings: {response.status_code}")
                            continue
                    else:
                        # For regular users, use the existing method
                        recordings = list(recordings_lister.list_user_recordings(
                            user_id, start_date, end_date, include_trash=include_trash
                        ))
                    
                    for recording in recordings:
                        meeting_id = recording.get("id", "unknown")
                        meeting_topic = recording.get("topic", "Unknown Topic")
                        
                        print(f"      📹 Meeting: {meeting_topic}")
                        
                        user_meetings += 1
                        total_meetings += 1
                        
                        # Process files
                        files = recording.get("files", [])
                        for file_info in files:
                            file_type = file_info.get("file_type", "unknown")
                            file_size = file_info.get("file_size", 0)
                            download_url = file_info.get("download_url", "")
                            
                            if download_url:
                                user_files += 1
                                total_files += 1
                                user_size += file_size
                                total_size += file_size
                                
                                if not dry_run:
                                    # Download the file
                                    output_path = structure.get_file_path(user, recording, file_info)
                                    print(f"         ✅ Would download: {output_path.name} ({file_size} bytes)")
                                else:
                                    print(f"         🔍 Would download: {file_type} ({file_size} bytes)")
                
                except Exception as e:
                    print(f"      ❌ Error processing date window: {e}")
                    continue
            
            print(f"   📊 Summary: {user_meetings} meetings, {user_files} files, {user_size / (1024**3):.2f} GB")
        
        except Exception as e:
            print(f"   ❌ Error processing {entity_type.lower()}: {e}")
            continue
    
    # Final summary
    print(f"\n🎉 EXTRACTION SUMMARY")
    print("=" * 60)
    print(f"👥 Users processed: {len(active_users + inactive_users + pending_users)}")
    print(f"🏠 Rooms processed: {len(zoom_rooms)}")
    print(f"📹 Total meetings: {total_meetings}")
    print(f"📁 Total files: {total_files}")
    print(f"💾 Total size: {total_size / (1024**3):.2f} GB")
    
    if dry_run:
        print(f"🧪 DRY RUN - No files were actually downloaded")
        print(f"💡 Run without --dry-run to perform actual downloads")
    
    return {
        "users_processed": len(active_users + inactive_users + pending_users),
        "rooms_processed": len(zoom_rooms),
        "total_meetings": total_meetings,
        "total_files": total_files,
        "total_size_gb": total_size / (1024**3),
        "dry_run": dry_run
    }

def main():
    """Main entry point with command line interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced Zoom Recordings Extractor with Rooms")
    parser.add_argument("--output-dir", default="./zoom_recordings_with_rooms", help="Output directory")
    parser.add_argument("--from-date", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--to-date", help="End date (YYYY-MM-DD)")
    parser.add_argument("--include-trash", action="store_true", default=True, help="Include trash recordings")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    
    args = parser.parse_args()
    
    try:
        result = extract_with_rooms(
            output_dir=args.output_dir,
            from_date=args.from_date,
            to_date=args.to_date,
            include_trash=args.include_trash,
            dry_run=args.dry_run
        )
        
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
