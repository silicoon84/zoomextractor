#!/usr/bin/env python3
"""
Check for Zoom Rooms and investigate required scopes.
"""

import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from zoom_extractor.auth import get_auth_from_env

def check_zoom_rooms():
    """Check for Zoom Rooms using different API endpoints."""
    
    print("🔍 Checking for Zoom Rooms")
    print("=" * 50)
    
    # Get auth
    auth = get_auth_from_env()
    headers = auth.get_auth_headers()
    
    # Check 1: List Zoom Rooms endpoint
    print("📋 Checking Zoom Rooms endpoint...")
    try:
        url = "https://api.zoom.us/v2/rooms"
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            rooms = data.get("rooms", [])
            print(f"✅ Found {len(rooms)} Zoom Rooms")
            
            for i, room in enumerate(rooms[:5], 1):  # Show first 5
                room_name = room.get("name", "Unknown")
                room_id = room.get("id", "Unknown")
                room_email = room.get("email", "Unknown")
                print(f"   {i}. {room_name} (ID: {room_id}, Email: {room_email})")
            
            if len(rooms) > 5:
                print(f"   ... and {len(rooms) - 5} more")
                
        elif response.status_code == 403:
            print("❌ Forbidden - Missing 'room:read:admin' scope")
        elif response.status_code == 401:
            print("❌ Unauthorized - Token issue")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Check 2: List Zoom Rooms with different parameters
    print(f"\n📋 Checking Zoom Rooms with different parameters...")
    
    endpoints_to_try = [
        "/v2/rooms",
        "/v2/rooms?page_size=100",
        "/v2/rooms?include_fields=id,name,email,status",
    ]
    
    for endpoint in endpoints_to_try:
        try:
            url = f"https://api.zoom.us{endpoint}"
            response = requests.get(url, headers=headers)
            print(f"   {endpoint}: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                rooms = data.get("rooms", [])
                print(f"      Found {len(rooms)} rooms")
                
        except Exception as e:
            print(f"   {endpoint}: ❌ {e}")
    
    # Check 3: Check current token scopes
    print(f"\n📋 Checking current token scopes...")
    try:
        url = "https://api.zoom.us/v2/users/me"
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Token is valid")
            print(f"   User: {data.get('email', 'Unknown')}")
            print(f"   Type: {data.get('type', 'Unknown')}")
        else:
            print(f"❌ Token check failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Token check error: {e}")
    
    # Check 4: Try to get room recordings
    print(f"\n📋 Checking if we can access room recordings...")
    try:
        # First get rooms if possible
        url = "https://api.zoom.us/v2/rooms"
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            rooms = data.get("rooms", [])
            
            if rooms:
                # Try to get recordings for first room
                room_id = rooms[0].get("id")
                room_name = rooms[0].get("name", "Unknown")
                
                print(f"   Testing room: {room_name} (ID: {room_id})")
                
                # Try to get recordings for this room
                recordings_url = f"https://api.zoom.us/v2/rooms/{room_id}/recordings"
                recordings_response = requests.get(recordings_url, headers=headers)
                
                print(f"   Room recordings endpoint: {recordings_response.status_code}")
                
                if recordings_response.status_code == 200:
                    recordings_data = recordings_response.json()
                    meetings = recordings_data.get("meetings", [])
                    print(f"      Found {len(meetings)} meetings with recordings")
                else:
                    print(f"      Error: {recordings_response.text}")
            else:
                print("   No rooms found to test")
        else:
            print(f"   Cannot access rooms: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Room recordings check error: {e}")

def check_required_scopes():
    """Check what scopes are required for Zoom Rooms."""
    
    print(f"\n📚 REQUIRED SCOPES FOR ZOOM ROOMS:")
    print("=" * 50)
    print("To access Zoom Rooms, you need these scopes:")
    print("")
    print("🔑 Required Scopes:")
    print("   - room:read:admin     (List Zoom Rooms)")
    print("   - recording:read:admin (Access room recordings)")
    print("   - meeting:read:admin   (Access room meetings)")
    print("")
    print("🔧 How to Add Scopes:")
    print("   1. Go to Zoom Marketplace")
    print("   2. Find your Server-to-Server OAuth app")
    print("   3. Click 'Scopes' tab")
    print("   4. Add the missing scopes")
    print("   5. Re-authorize the app")
    print("")
    print("📋 Current Scopes (check your app):")
    print("   - user:read:list_users:admin")
    print("   - user:read:admin")
    print("   - account:read:sub_account:admin")
    print("   - recording:read:admin")
    print("   - meeting:read:admin")
    print("   - room:read:admin (MISSING - ADD THIS)")

def main():
    """Main entry point."""
    try:
        check_zoom_rooms()
        check_required_scopes()
        
        print(f"\n💡 NEXT STEPS:")
        print("=" * 50)
        print("1. Add 'room:read:admin' scope to your Zoom app")
        print("2. Re-authorize the app")
        print("3. Run this script again to verify")
        print("4. Update your extraction scripts to include Zoom Rooms")
        print("")
        print("🎯 This should give you the missing 4 users (Zoom Rooms)!")
        
    except Exception as e:
        print(f"❌ Check failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
