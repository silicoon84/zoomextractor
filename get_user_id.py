#!/usr/bin/env python3
"""
Quick script to get a user ID from an email address using Zoom API
"""

import os
import sys
import requests
from dotenv import load_dotenv

# Add the zoom_extractor module to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from zoom_extractor.auth import get_auth_from_env

# Load environment variables
load_dotenv()

def get_user_id_by_email(email: str):
    """Get user ID from email address"""
    
    try:
        # Get authentication
        auth = get_auth_from_env()
        auth_headers = auth.get_auth_headers()
        
        print(f"Looking up user ID for email: {email}")
        
        # Make API request to get user by email
        url = f"https://api.zoom.us/v2/users/{email}"
        
        response = requests.get(url, headers=auth_headers)
        
        if response.status_code == 200:
            user_data = response.json()
            user_id = user_data.get("id")
            user_name = user_data.get("first_name", "") + " " + user_data.get("last_name", "")
            
            print(f"✅ Found user:")
            print(f"   Email: {email}")
            print(f"   User ID: {user_id}")
            print(f"   Name: {user_name.strip()}")
            print(f"   Status: {user_data.get('status', 'unknown')}")
            print(f"   Type: {user_data.get('type', 'unknown')}")
            
            return user_id
            
        elif response.status_code == 404:
            print(f"❌ User not found: {email}")
            print(f"   This email may not exist in your Zoom account")
            return None
            
        else:
            print(f"❌ Error getting user: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def main():
    """Main function"""
    
    if len(sys.argv) != 2:
        print("Usage: python get_user_id.py <email>")
        print("Example: python get_user_id.py user@example.com")
        sys.exit(1)
    
    email = sys.argv[1]
    
    # Validate email format (basic check)
    if "@" not in email or "." not in email:
        print("❌ Please provide a valid email address")
        sys.exit(1)
    
    user_id = get_user_id_by_email(email)
    
    if user_id:
        print(f"\n🎯 User ID: {user_id}")
        print(f"You can use this ID in other scripts like:")
        print(f"python simple_chat_extractor_improved.py --channel-id some_channel --extractor-user {user_id}")
    else:
        print(f"\n❌ Could not find user ID for: {email}")
        sys.exit(1)

if __name__ == "__main__":
    main()
