#!/usr/bin/env python3
"""
Comprehensive Zoom Recordings Analysis - Checks larger samples and different date ranges.
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

def comprehensive_user_analysis():
    """Comprehensive analysis with larger samples and multiple date ranges."""
    
    print("🔍 Comprehensive Zoom Recordings Analysis")
    print("=" * 60)
    
    # Get auth
    auth = get_auth_from_env()
    headers = auth.get_auth_headers()
    
    user_enumerator = UserEnumerator(headers)
    recordings_lister = RecordingsLister(headers)
    
    # Get all users
    print("📋 Getting all users...")
    active_users = list(user_enumerator.list_all_users(user_type="active"))
    inactive_users = list(user_enumerator.list_all_users(user_type="inactive"))
    
    print(f"   Active users: {len(active_users)}")
    print(f"   Inactive users: {len(inactive_users)}")
    
    # Test different date ranges
    date_ranges = [
        ("Last 30 days", 30),
        ("Last 90 days", 90),
        ("Last 6 months", 180),
        ("Last year", 365),
        ("Last 2 years", 730),
        ("Last 3 years", 1095)
    ]
    
    results = {
        "active_users": {"total": len(active_users), "samples": {}},
        "inactive_users": {"total": len(inactive_users), "samples": {}}
    }
    
    # Analyze active users with larger sample
    print(f"\n📊 Analyzing ACTIVE users (larger sample)...")
    sample_size = min(50, len(active_users))  # Sample 50 users instead of 10
    
    for date_name, days in date_ranges:
        print(f"\n   📅 {date_name}:")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        users_with_recordings = 0
        total_recordings = 0
        total_files = 0
        
        for i, user in enumerate(active_users[:sample_size]):
            user_id = user["id"]
            user_email = user.get("email", "unknown")
            
            try:
                recordings = list(recordings_lister.list_user_recordings(
                    user_id, start_date, end_date
                ))
                
                if recordings:
                    users_with_recordings += 1
                    total_recordings += len(recordings)
                    
                    # Count files
                    for recording in recordings:
                        files = recording.get("files", [])
                        total_files += len(files)
                
                # Show progress every 10 users
                if (i + 1) % 10 == 0:
                    print(f"      Processed {i+1}/{sample_size} users...")
                
            except Exception as e:
                if "401" in str(e):
                    print(f"      ⚠️  Token expired at user {i+1}")
                    break
                continue
        
        results["active_users"]["samples"][date_name] = {
            "users_with_recordings": users_with_recordings,
            "total_recordings": total_recordings,
            "total_files": total_files,
            "sample_size": sample_size
        }
        
        print(f"      ✅ {users_with_recordings}/{sample_size} users had recordings")
        print(f"      📹 Total recordings: {total_recordings}")
        print(f"      📁 Total files: {total_files}")
    
    # Analyze inactive users with smaller sample (they're more likely to have recordings)
    print(f"\n📊 Analyzing INACTIVE users (sample)...")
    sample_size = min(20, len(inactive_users))
    
    for date_name, days in date_ranges:
        print(f"\n   📅 {date_name}:")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        users_with_recordings = 0
        total_recordings = 0
        total_files = 0
        
        for i, user in enumerate(inactive_users[:sample_size]):
            user_id = user["id"]
            user_email = user.get("email", "unknown")
            
            try:
                recordings = list(recordings_lister.list_user_recordings(
                    user_id, start_date, end_date
                ))
                
                if recordings:
                    users_with_recordings += 1
                    total_recordings += len(recordings)
                    
                    # Count files
                    for recording in recordings:
                        files = recording.get("files", [])
                        total_files += len(files)
                
                # Show progress every 5 users
                if (i + 1) % 5 == 0:
                    print(f"      Processed {i+1}/{sample_size} users...")
                
            except Exception as e:
                if "401" in str(e):
                    print(f"      ⚠️  Token expired at user {i+1}")
                    break
                continue
        
        results["inactive_users"]["samples"][date_name] = {
            "users_with_recordings": users_with_recordings,
            "total_recordings": total_recordings,
            "total_files": total_files,
            "sample_size": sample_size
        }
        
        print(f"      ✅ {users_with_recordings}/{sample_size} users had recordings")
        print(f"      📹 Total recordings: {total_recordings}")
        print(f"      📁 Total files: {total_files}")
    
    return results

def find_users_with_recordings():
    """Find specific users who have recordings in any time period."""
    
    print(f"\n🎯 Finding Users with Recordings...")
    
    auth = get_auth_from_env()
    headers = auth.get_auth_headers()
    
    user_enumerator = UserEnumerator(headers)
    recordings_lister = RecordingsLister(headers)
    
    # Get all users
    all_users = []
    all_users.extend(list(user_enumerator.list_all_users(user_type="active")))
    all_users.extend(list(user_enumerator.list_all_users(user_type="inactive")))
    
    users_with_recordings = []
    
    # Check last 2 years
    end_date = datetime.now()
    start_date = end_date - timedelta(days=730)
    
    print(f"   Checking {len(all_users)} users for recordings in last 2 years...")
    
    for i, user in enumerate(all_users):
        user_id = user["id"]
        user_email = user.get("email", "unknown")
        user_status = user.get("status", "unknown")
        
        try:
            recordings = list(recordings_lister.list_user_recordings(
                user_id, start_date, end_date
            ))
            
            if recordings:
                total_files = sum(len(rec.get("files", [])) for rec in recordings)
                users_with_recordings.append({
                    "email": user_email,
                    "status": user_status,
                    "recordings": len(recordings),
                    "files": total_files
                })
                print(f"   ✅ {user_email} ({user_status}): {len(recordings)} recordings, {total_files} files")
            
            # Show progress every 50 users
            if (i + 1) % 50 == 0:
                print(f"   Processed {i+1}/{len(all_users)} users...")
        
        except Exception as e:
            if "401" in str(e):
                print(f"   ⚠️  Token expired at user {i+1}")
                break
            continue
    
    print(f"\n📊 SUMMARY: Found {len(users_with_recordings)} users with recordings")
    
    # Show top users by recording count
    users_with_recordings.sort(key=lambda x: x["recordings"], reverse=True)
    
    print(f"\n🏆 Top 10 Users by Recording Count:")
    for i, user in enumerate(users_with_recordings[:10]):
        print(f"   {i+1}. {user['email']} ({user['status']}): {user['recordings']} recordings, {user['files']} files")
    
    return users_with_recordings

def main():
    """Run comprehensive analysis."""
    
    try:
        # Run comprehensive analysis
        results = comprehensive_user_analysis()
        
        # Find specific users with recordings
        users_with_recordings = find_users_with_recordings()
        
        # Save results
        final_results = {
            "timestamp": datetime.now().isoformat(),
            "comprehensive_analysis": results,
            "users_with_recordings": users_with_recordings
        }
        
        with open("comprehensive_analysis.json", "w") as f:
            json.dump(final_results, f, indent=2)
        
        print(f"\n💾 Results saved to comprehensive_analysis.json")
        
        # Summary
        print(f"\n📋 FINAL SUMMARY")
        print("=" * 60)
        print(f"👥 Total users checked: {results['active_users']['total'] + results['inactive_users']['total']}")
        print(f"🎯 Users with recordings found: {len(users_with_recordings)}")
        
        if users_with_recordings:
            total_recordings = sum(user["recordings"] for user in users_with_recordings)
            total_files = sum(user["files"] for user in users_with_recordings)
            print(f"📹 Total recordings found: {total_recordings}")
            print(f"📁 Total files found: {total_files}")
        
        print(f"\n💡 RECOMMENDATIONS:")
        print("1. Use the enhanced extract_all_recordings.py script")
        print("2. Include inactive users with --include-inactive")
        print("3. Use a 2-3 year date range to catch older recordings")
        print("4. Check the users_with_recordings list for specific test cases")
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
