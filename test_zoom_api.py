#!/usr/bin/env python3
"""
Test script based on official Zoom API documentation
https://developers.zoom.us/docs/api/
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Get auth headers
from zoom_extractor.auth import get_auth_from_env
auth = get_auth_from_env()
headers = auth.get_auth_headers()

print("=== Testing Zoom API according to official documentation ===")

# Test 1: Basic users endpoint - most basic request
print("\n1. Testing basic users endpoint:")
url = "https://api.zoom.us/v2/users"
params = {
    "page_size": 30,
    "status": "active"
}

try:
    response = requests.get(url, headers=headers, params=params, timeout=30)
    print(f"Status: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        data = response.json()
        users = data.get("users", [])
        print(f"SUCCESS: Found {len(users)} users")
        if users:
            user = users[0]
            print(f"Sample user: {user.get('email', 'No email')} (ID: {user.get('id', 'No ID')})")
        print(f"Next page token: {data.get('next_page_token', 'None')}")
    else:
        print(f"ERROR: {response.status_code}")
        print(f"Response: {response.text}")
        
except Exception as e:
    print(f"EXCEPTION: {e}")

# Test 2: Try without any parameters
print("\n2. Testing with minimal parameters:")
params_minimal = {
    "page_size": 10
}

try:
    response = requests.get(url, headers=headers, params=params_minimal, timeout=30)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        users = data.get("users", [])
        print(f"SUCCESS: Found {len(users)} users with minimal params")
    else:
        print(f"ERROR: {response.status_code}")
        print(f"Response: {response.text}")
        
except Exception as e:
    print(f"EXCEPTION: {e}")

# Test 3: Try different status values
print("\n3. Testing different status values:")
for status in ["active", "inactive", "pending"]:
    params_status = {
        "page_size": 10,
        "status": status
    }
    
    try:
        response = requests.get(url, headers=headers, params=params_status, timeout=30)
        print(f"Status '{status}': {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            users = data.get("users", [])
            print(f"  Found {len(users)} {status} users")
        else:
            print(f"  Error: {response.text[:100]}")
            
    except Exception as e:
        print(f"  Exception: {e}")

# Test 4: Check account info
print("\n4. Testing account info:")
try:
    account_url = "https://api.zoom.us/v2/accounts/me"
    response = requests.get(account_url, headers=headers, timeout=30)
    print(f"Account info status: {response.status_code}")
    
    if response.status_code == 200:
        account_data = response.json()
        print(f"Account: {account_data.get('account_name', 'Unknown')}")
        print(f"Account ID: {account_data.get('account_id', 'Unknown')}")
        print(f"Account Type: {account_data.get('account_type', 'Unknown')}")
    else:
        print(f"Account info error: {response.text}")
        
except Exception as e:
    print(f"Account info exception: {e}")

print("\n=== Test completed ===")
