#!/usr/bin/env python3
"""
Comprehensive analysis of Zoom recordings coverage.
This script helps identify why recording counts might differ from the Zoom portal.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Set
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from zoom_extractor.auth import get_auth_from_env
from zoom_extractor.users import UserEnumerator
from zoom_extractor.recordings import RecordingsLister

def analyze_user_coverage():
    """Analyze what types of users and recordings we're covering."""
    
    print("🔍 Zoom Recordings Coverage Analysis")
    print("=" * 50)
    
    # Get auth
    auth = get_auth_from_env()
    headers = auth.get_auth_headers()
    
    user_enumerator = UserEnumerator(headers)
    recordings_lister = RecordingsLister(headers)
    
    # Analyze different user types
    user_types = ["active", "inactive", "pending"]
    coverage_stats = {}
    
    for user_type in user_types:
        print(f"\n📊 Analyzing {user_type.upper()} users...")
        
        users = list(user_enumerator.list_all_users(user_type=user_type))
        coverage_stats[user_type] = {
            "total_users": len(users),
            "users_with_recordings": 0,
            "total_recordings": 0,
            "total_files": 0,
            "date_range": {}
        }
        
        print(f"   Found {len(users)} {user_type} users")
        
        # Sample a few users to check for recordings
        sample_size = min(10, len(users))
        for i, user in enumerate(users[:sample_size]):
            user_id = user["id"]
            user_email = user.get("email", "unknown")
            
            try:
                # Check last 90 days for recordings
                end_date = datetime.now()
                start_date = end_date - timedelta(days=90)
                
                recordings = list(recordings_lister.list_user_recordings(
                    user_id, start_date, end_date
                ))
                
                if recordings:
                    coverage_stats[user_type]["users_with_recordings"] += 1
                    coverage_stats[user_type]["total_recordings"] += len(recordings)
                    
                    # Count files
                    for recording in recordings:
                        files = recording.get("files", [])
                        coverage_stats[user_type]["total_files"] += len(files)
                
                print(f"   [{i+1}/{sample_size}] {user_email}: {len(recordings)} recordings")
                
            except Exception as e:
                print(f"   [{i+1}/{sample_size}] {user_email}: ERROR - {str(e)[:50]}...")
    
    # Check for deleted users' recordings
    print(f"\n🗑️  Analyzing DELETED users...")
    try:
        # Try to get inactive users (includes deleted)
        deleted_users = list(user_enumerator.list_all_users(user_type="inactive"))
        deleted_with_recordings = 0
        deleted_recordings = 0
        
        # Sample deleted users
        sample_size = min(5, len(deleted_users))
        for i, user in enumerate(deleted_users[:sample_size]):
            user_id = user["id"]
            user_email = user.get("email", "unknown")
            
            try:
                # Check last year for recordings
                end_date = datetime.now()
                start_date = end_date - timedelta(days=365)
                
                recordings = list(recordings_lister.list_user_recordings(
                    user_id, start_date, end_date
                ))
                
                if recordings:
                    deleted_with_recordings += 1
                    deleted_recordings += len(recordings)
                
                print(f"   [{i+1}/{sample_size}] {user_email}: {len(recordings)} recordings")
                
            except Exception as e:
                print(f"   [{i+1}/{sample_size}] {user_email}: ERROR - {str(e)[:50]}...")
        
        coverage_stats["deleted"] = {
            "total_users": len(deleted_users),
            "users_with_recordings": deleted_with_recordings,
            "total_recordings": deleted_recordings
        }
        
    except Exception as e:
        print(f"   ERROR accessing deleted users: {e}")
        coverage_stats["deleted"] = {"error": str(e)}
    
    return coverage_stats

def analyze_recording_types():
    """Analyze what types of recordings we're finding."""
    
    print(f"\n📁 Analyzing Recording Types...")
    
    auth = get_auth_from_env()
    headers = auth.get_auth_headers()
    
    user_enumerator = UserEnumerator(headers)
    recordings_lister = RecordingsLister(headers)
    
    # Get a sample of active users
    users = list(user_enumerator.list_all_users(user_type="active"))
    sample_users = users[:5]  # Sample 5 users
    
    file_type_counts = {}
    recording_types = set()
    
    for user in sample_users:
        user_id = user["id"]
        user_email = user.get("email", "unknown")
        
        try:
            # Check last 30 days
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            recordings = list(recordings_lister.list_user_recordings(
                user_id, start_date, end_date
            ))
            
            for recording in recordings:
                recording_type = recording.get("type", "unknown")
                recording_types.add(recording_type)
                
                files = recording.get("files", [])
                for file_info in files:
                    file_type = file_info.get("file_type", "unknown")
                    file_type_counts[file_type] = file_type_counts.get(file_type, 0) + 1
        
        except Exception as e:
            print(f"   ERROR processing {user_email}: {e}")
    
    print(f"   Recording types found: {list(recording_types)}")
    print(f"   File types found: {dict(file_type_counts)}")
    
    return {
        "recording_types": list(recording_types),
        "file_type_counts": file_type_counts
    }

def check_trash_recordings():
    """Check if there are recordings in trash that we're missing."""
    
    print(f"\n🗑️  Checking Trash Recordings...")
    
    auth = get_auth_from_env()
    headers = auth.get_auth_headers()
    
    user_enumerator = UserEnumerator(headers)
    recordings_lister = RecordingsLister(headers)
    
    # Get a few active users
    users = list(user_enumerator.list_all_users(user_type="active"))
    sample_users = users[:3]  # Sample 3 users
    
    trash_count = 0
    
    for user in sample_users:
        user_id = user["id"]
        user_email = user.get("email", "unknown")
        
        try:
            # Check last 90 days with trash included
            end_date = datetime.now()
            start_date = end_date - timedelta(days=90)
            
            # Get recordings with trash
            recordings_with_trash = list(recordings_lister.list_user_recordings(
                user_id, start_date, end_date, include_trash=True
            ))
            
            # Get recordings without trash
            recordings_without_trash = list(recordings_lister.list_user_recordings(
                user_id, start_date, end_date, include_trash=False
            ))
            
            trash_diff = len(recordings_with_trash) - len(recordings_without_trash)
            if trash_diff > 0:
                trash_count += trash_diff
                print(f"   {user_email}: {trash_diff} recordings in trash")
        
        except Exception as e:
            print(f"   ERROR checking trash for {user_email}: {e}")
    
    print(f"   Total trash recordings in sample: {trash_count}")
    return trash_count

def main():
    """Run comprehensive coverage analysis."""
    
    try:
        # Analyze user coverage
        coverage_stats = analyze_user_coverage()
        
        # Analyze recording types
        recording_analysis = analyze_recording_types()
        
        # Check trash
        trash_count = check_trash_recordings()
        
        # Summary
        print(f"\n📋 COVERAGE SUMMARY")
        print("=" * 50)
        
        for user_type, stats in coverage_stats.items():
            if isinstance(stats, dict) and "error" not in stats:
                print(f"{user_type.upper()}:")
                print(f"  - Total users: {stats['total_users']}")
                print(f"  - Users with recordings: {stats['users_with_recordings']}")
                print(f"  - Total recordings (sample): {stats['total_recordings']}")
                print(f"  - Total files (sample): {stats['total_files']}")
        
        print(f"\n🔍 POTENTIAL GAPS:")
        print("1. INACTIVE/DELETED USERS: May have recordings not counted")
        print("2. TRASH RECORDINGS: {trash_count} found in sample")
        print("3. OLDER RECORDINGS: May be beyond default date ranges")
        print("4. WEBINAR RECORDINGS: May have different access patterns")
        print("5. SHARED RECORDINGS: May be accessible to other users")
        
        print(f"\n💡 RECOMMENDATIONS:")
        print("1. Run extraction with user_type='inactive' to get deleted users")
        print("2. Include trash recordings with --include-trash")
        print("3. Extend date range beyond default 1 year")
        print("4. Check if webinar recordings need special handling")
        
        # Save results
        results = {
            "timestamp": datetime.now().isoformat(),
            "coverage_stats": coverage_stats,
            "recording_analysis": recording_analysis,
            "trash_count": trash_count
        }
        
        with open("coverage_analysis.json", "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 Results saved to coverage_analysis.json")
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
