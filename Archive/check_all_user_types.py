#!/usr/bin/env python3
"""
Check all possible user types to find the missing 4 users.
"""

import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from zoom_extractor.auth import get_auth_from_env
from zoom_extractor.users import UserEnumerator

def check_all_user_types():
    """Check all possible user types to find missing users."""
    
    print("🔍 Checking All User Types for Missing Users")
    print("=" * 50)
    
    # Get auth
    auth = get_auth_from_env()
    headers = auth.get_auth_headers()
    
    user_enumerator = UserEnumerator(headers)
    
    # All possible user statuses according to Zoom API
    user_statuses = [
        "active",
        "inactive", 
        "pending",
        "deactivated"  # This might be another status
    ]
    
    all_users = []
    status_counts = {}
    
    print("📋 Checking all user statuses...")
    
    for status in user_statuses:
        try:
            print(f"\n🔍 Checking '{status}' users...")
            users = list(user_enumerator.list_all_users(user_type=status))
            status_counts[status] = len(users)
            all_users.extend(users)
            print(f"   ✅ Found {len(users)} {status} users")
            
            # Show first few user emails for verification
            for i, user in enumerate(users[:3]):
                email = user.get("email", "unknown")
                user_id = user.get("id", "unknown")
                print(f"      {i+1}. {email} (ID: {user_id})")
            
            if len(users) > 3:
                print(f"      ... and {len(users) - 3} more")
                
        except Exception as e:
            print(f"   ❌ Error getting {status} users: {e}")
            status_counts[status] = 0
    
    # Check for duplicates
    unique_users = {}
    duplicates = []
    
    for user in all_users:
        user_id = user.get("id")
        user_email = user.get("email", "unknown")
        
        if user_id in unique_users:
            duplicates.append({
                "id": user_id,
                "email": user_email,
                "first_status": unique_users[user_id]["status"],
                "duplicate_status": user.get("status", "unknown")
            })
        else:
            unique_users[user_id] = {
                "email": user_email,
                "status": user.get("status", "unknown")
            }
    
    # Summary
    print(f"\n📊 USER TYPE SUMMARY")
    print("=" * 50)
    
    total_with_duplicates = sum(status_counts.values())
    total_unique = len(unique_users)
    
    for status, count in status_counts.items():
        print(f"{status.upper()}: {count} users")
    
    print(f"\nTOTAL (with duplicates): {total_with_duplicates}")
    print(f"TOTAL (unique users): {total_unique}")
    print(f"Zoom Portal shows: 368 users")
    print(f"Our script shows: 364 users")
    print(f"Difference: {368 - total_unique} missing")
    
    if duplicates:
        print(f"\n🔄 DUPLICATE USERS FOUND:")
        print("=" * 50)
        for dup in duplicates:
            print(f"ID: {dup['id']}")
            print(f"Email: {dup['email']}")
            print(f"Statuses: {dup['first_status']} + {dup['duplicate_status']}")
            print()
    
    # Check if we're missing any user statuses
    print(f"\n💡 ANALYSIS:")
    print("=" * 50)
    
    if total_unique < 368:
        missing_count = 368 - total_unique
        print(f"❌ We're missing {missing_count} users")
        print(f"🔍 Possible reasons:")
        print(f"   1. Unknown user status not checked")
        print(f"   2. API pagination issue")
        print(f"   3. Permission restrictions")
        print(f"   4. Time zone differences")
        print(f"   5. Data sync delays")
    else:
        print(f"✅ We found all users!")
    
    # Try to get users without status filter
    print(f"\n🔍 Trying to get users without status filter...")
    try:
        # This might not work, but let's try
        users_no_filter = list(user_enumerator.list_all_users())
        print(f"   Found {len(users_no_filter)} users without status filter")
        
        if len(users_no_filter) > total_unique:
            print(f"   ✅ Found {len(users_no_filter) - total_unique} additional users!")
            
    except Exception as e:
        print(f"   ❌ Error getting users without filter: {e}")
    
    return {
        "status_counts": status_counts,
        "total_unique": total_unique,
        "total_with_duplicates": total_with_duplicates,
        "duplicates": duplicates,
        "missing_count": 368 - total_unique
    }

def main():
    """Main entry point."""
    try:
        results = check_all_user_types()
        
        print(f"\n🎯 RECOMMENDATIONS:")
        print("=" * 50)
        
        if results["missing_count"] > 0:
            print(f"1. Update scripts to include ALL user statuses")
            print(f"2. Check for 'deactivated' or other status types")
            print(f"3. Verify API permissions")
            print(f"4. Consider time zone differences")
        else:
            print(f"✅ All users accounted for!")
            
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
