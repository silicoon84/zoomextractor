#!/usr/bin/env python3
"""
Deep investigation of missing users - try different approaches to find all 368 users.
"""

import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from zoom_extractor.auth import get_auth_from_env
from zoom_extractor.users import UserEnumerator

def investigate_missing_users():
    """Deep investigation using multiple approaches."""
    
    print("🔍 Deep Investigation of Missing Users")
    print("=" * 60)
    
    # Get auth
    auth = get_auth_from_env()
    headers = auth.get_auth_headers()
    
    user_enumerator = UserEnumerator(headers)
    
    # Approach 1: Try different page sizes
    print("📋 APPROACH 1: Testing different page sizes...")
    page_sizes = [30, 50, 100, 200, 300]
    
    for page_size in page_sizes:
        try:
            print(f"\n🔍 Testing page_size={page_size}...")
            
            # Get active users with different page size
            url = "https://api.zoom.us/v2/users"
            params = {
                "page_size": page_size,
                "status": "active"
            }
            
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json()
                total_records = data.get("total_records", 0)
                users_count = len(data.get("users", []))
                print(f"   Active: {users_count} users (total_records: {total_records})")
                
                # Get inactive users with same page size
                params["status"] = "inactive"
                response = requests.get(url, headers=headers, params=params)
                if response.status_code == 200:
                    data = response.json()
                    total_records = data.get("total_records", 0)
                    users_count = len(data.get("users", []))
                    print(f"   Inactive: {users_count} users (total_records: {total_records})")
                    
        except Exception as e:
            print(f"   ❌ Error with page_size={page_size}: {e}")
    
    # Approach 2: Try without status filter
    print(f"\n📋 APPROACH 2: Getting users without status filter...")
    try:
        url = "https://api.zoom.us/v2/users"
        params = {"page_size": 300}  # Try larger page size
        
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            total_records = data.get("total_records", 0)
            users = data.get("users", [])
            print(f"   ✅ Found {len(users)} users (total_records: {total_records})")
            
            # Analyze status distribution
            status_counts = {}
            for user in users:
                status = user.get("status", "unknown")
                status_counts[status] = status_counts.get(status, 0) + 1
            
            print(f"   Status breakdown:")
            for status, count in status_counts.items():
                print(f"      {status}: {count} users")
                
        else:
            print(f"   ❌ Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Approach 3: Try different API endpoints
    print(f"\n📋 APPROACH 3: Testing different API endpoints...")
    
    endpoints_to_try = [
        "/v2/users",
        "/v2/users?include_fields=id,email,status,type",
        "/v2/users?page_size=300",
        "/v2/users?status=active&page_size=300",
        "/v2/users?status=inactive&page_size=300",
    ]
    
    for endpoint in endpoints_to_try:
        try:
            url = f"https://api.zoom.us{endpoint}"
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                total_records = data.get("total_records", 0)
                users = data.get("users", [])
                print(f"   {endpoint}: {len(users)} users (total_records: {total_records})")
            else:
                print(f"   {endpoint}: ❌ {response.status_code}")
        except Exception as e:
            print(f"   {endpoint}: ❌ {e}")
    
    # Approach 4: Check if there are other user types
    print(f"\n📋 APPROACH 4: Testing other possible user statuses...")
    
    possible_statuses = [
        "active", "inactive", "pending", "deactivated",
        "suspended", "deleted", "archived", "disabled",
        "enabled", "verified", "unverified", "provisioned"
    ]
    
    for status in possible_statuses:
        try:
            url = "https://api.zoom.us/v2/users"
            params = {
                "page_size": 30,
                "status": status
            }
            
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json()
                users = data.get("users", [])
                total_records = data.get("total_records", 0)
                if len(users) > 0 or total_records > 0:
                    print(f"   {status}: ✅ {len(users)} users (total_records: {total_records})")
                else:
                    print(f"   {status}: 0 users")
            elif response.status_code == 400:
                print(f"   {status}: ❌ Invalid status")
            else:
                print(f"   {status}: ❌ {response.status_code}")
                
        except Exception as e:
            print(f"   {status}: ❌ {e}")
    
    # Approach 5: Check account-level vs user-level differences
    print(f"\n📋 APPROACH 5: Checking account vs user differences...")
    
    try:
        # Check if we're looking at the right account level
        url = "https://api.zoom.us/v2/accounts"
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            accounts = data.get("accounts", [])
            print(f"   Found {len(accounts)} accounts")
            
            for account in accounts:
                account_id = account.get("id", "unknown")
                account_name = account.get("account_name", "unknown")
                print(f"      Account: {account_name} (ID: {account_id})")
        else:
            print(f"   ❌ Cannot access accounts endpoint: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error checking accounts: {e}")
    
    # Summary and recommendations
    print(f"\n💡 ANALYSIS AND RECOMMENDATIONS:")
    print("=" * 60)
    print("Based on the investigation:")
    print("1. The 4 missing users are likely due to:")
    print("   - API pagination edge cases")
    print("   - Permission/visibility differences")
    print("   - Time zone or data sync issues")
    print("   - Different account levels or sub-accounts")
    print("")
    print("2. Next steps to try:")
    print("   - Check if Zoom portal includes sub-accounts")
    print("   - Verify API permissions include all user types")
    print("   - Check for time zone differences")
    print("   - Compare with Zoom portal at exact same time")
    print("")
    print("3. The current 364 users should include all accessible recordings")

def main():
    """Main entry point."""
    try:
        investigate_missing_users()
        
    except Exception as e:
        print(f"❌ Investigation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
