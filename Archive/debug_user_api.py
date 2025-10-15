#!/usr/bin/env python3
"""
Debug the user API to see exactly what's being returned.
"""

import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from zoom_extractor.auth import get_auth_from_env

def debug_user_api():
    """Debug the user API responses."""
    
    print("🔍 Debugging User API Responses")
    print("=" * 50)
    
    # Get auth
    auth = get_auth_from_env()
    headers = auth.get_auth_headers()
    
    # Test active users with detailed logging
    print("📋 Testing Active Users API...")
    url = "https://api.zoom.us/v2/users"
    params = {
        "page_size": 30,
        "status": "active"
    }
    
    response = requests.get(url, headers=headers, params=params)
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Response keys: {list(data.keys())}")
        print(f"Total records: {data.get('total_records', 'NOT_FOUND')}")
        print(f"Page count: {data.get('page_count', 'NOT_FOUND')}")
        print(f"Page number: {data.get('page_number', 'NOT_FOUND')}")
        print(f"Page size: {data.get('page_size', 'NOT_FOUND')}")
        print(f"Next page token: {data.get('next_page_token', 'NOT_FOUND')}")
        
        users = data.get("users", [])
        print(f"Users in this page: {len(users)}")
        
        if users:
            print(f"First user keys: {list(users[0].keys())}")
            print(f"First user: {json.dumps(users[0], indent=2)}")
    else:
        print(f"Error response: {response.text}")
    
    print("\n" + "="*50)
    
    # Test inactive users
    print("📋 Testing Inactive Users API...")
    params["status"] = "inactive"
    
    response = requests.get(url, headers=headers, params=params)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Total records: {data.get('total_records', 'NOT_FOUND')}")
        print(f"Page count: {data.get('page_count', 'NOT_FOUND')}")
        users = data.get("users", [])
        print(f"Users in this page: {len(users)}")
        
        if users:
            print(f"First user keys: {list(users[0].keys())}")
    else:
        print(f"Error response: {response.text}")
    
    print("\n" + "="*50)
    
    # Test without status filter
    print("📋 Testing Users API without status filter...")
    params = {"page_size": 300}
    
    response = requests.get(url, headers=headers, params=params)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Total records: {data.get('total_records', 'NOT_FOUND')}")
        print(f"Page count: {data.get('page_count', 'NOT_FOUND')}")
        users = data.get("users", [])
        print(f"Users in this page: {len(users)}")
        
        # Count by status
        status_counts = {}
        for user in users:
            status = user.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print(f"Status breakdown:")
        for status, count in status_counts.items():
            print(f"  {status}: {count}")
            
    else:
        print(f"Error response: {response.text}")

def main():
    """Main entry point."""
    try:
        debug_user_api()
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
