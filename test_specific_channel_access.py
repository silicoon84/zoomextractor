#!/usr/bin/env python3
"""
Quick test to verify channel access with specific users
"""

import os
import sys
import json
import requests
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add the zoom_extractor module to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from zoom_extractor.auth import get_auth_from_env
from zoom_extractor.users import UserEnumerator
from zoom_extractor.rate_limiter import RateLimiter

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_channel_access():
    """Test channel access with specific users"""
    
    try:
        auth = get_auth_from_env()
        auth_headers = auth.get_auth_headers()
        rate_limiter = RateLimiter()
        logger.info("Authentication successful")
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        return
    
    # Channel from your file
    channel_id = "d6c65e4872704eaf8b859c8bd5adc5ed"
    accessible_users = [
        "jgeorgiou@atwea.edu.au",
        "nbailey@atwea.edu.au", 
        "kdavidson@atwea.edu.au",
        "gdennis@atwea.edu.au"
    ]
    
    logger.info(f"Testing channel access for: {channel_id}")
    logger.info(f"Channel name: NAIDOC Week")
    logger.info(f"Testing with accessible users: {accessible_users}")
    
    # Test with 'me' first
    logger.info(f"\n🔍 Testing with 'me':")
    test_url = f"https://api.zoom.us/v2/chat/users/me/messages"
    test_params = {"page_size": "10", "to_channel": channel_id}
    
    try:
        rate_limiter.sleep(0)
        response = requests.get(test_url, headers=auth_headers, params=test_params, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            messages = data.get("messages", [])
            logger.info(f"✅ SUCCESS with 'me': Found {len(messages)} messages")
            if messages:
                logger.info(f"   Sample: {messages[0].get('message', 'No text')[:100]}...")
        else:
            logger.warning(f"❌ FAILED with 'me': {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"❌ ERROR with 'me': {e}")
    
    # Test with specific users
    user_enumerator = UserEnumerator(auth_headers)
    
    for user_email in accessible_users[:3]:  # Test first 3 users
        logger.info(f"\n🔍 Testing with user: {user_email}")
        
        try:
            # Get user ID
            user_info = user_enumerator.get_user_by_email(user_email)
            if not user_info:
                logger.warning(f"❌ Could not find user info for {user_email}")
                continue
                
            user_id = user_info.get("id")
            logger.info(f"   User ID: {user_id}")
            
            # Test channel access
            test_url = f"https://api.zoom.us/v2/chat/users/{user_id}/messages"
            test_params = {"page_size": "10", "to_channel": channel_id}
            
            rate_limiter.sleep(0)
            response = requests.get(test_url, headers=auth_headers, params=test_params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                messages = data.get("messages", [])
                logger.info(f"✅ SUCCESS with {user_email}: Found {len(messages)} messages")
                if messages:
                    logger.info(f"   Sample: {messages[0].get('message', 'No text')[:100]}...")
                    # If we found messages, break out of the loop
                    break
            else:
                logger.warning(f"❌ FAILED with {user_email}: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"❌ ERROR with {user_email}: {e}")
            continue

if __name__ == "__main__":
    test_channel_access()
