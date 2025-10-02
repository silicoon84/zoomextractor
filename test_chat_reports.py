#!/usr/bin/env python3
"""
Test script for Zoom Chat Reports extraction
"""

import os
import sys
import logging
from datetime import datetime, timedelta

# Add the zoom_extractor module to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from zoom_extractor.auth import get_auth_from_env
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_chat_reports():
    """Test chat reports extraction"""
    
    logger.info("[TEST] Starting Chat Reports API test")
    
    # Test authentication
    try:
        auth = get_auth_from_env()
        auth_headers = auth.get_auth_headers()
        logger.info("[OK] Authentication successful")
    except Exception as e:
        logger.error(f"[ERROR] Authentication failed: {e}")
        return False
    
    # Test chat sessions endpoint
    try:
        import requests
        from zoom_extractor.rate_limiter import RateLimiter
        
        rate_limiter = RateLimiter()
        
        # Test with last 30 days
        to_date = datetime.now().strftime("%Y-%m-%d")
        from_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        
        logger.info(f"[TEST] Testing chat sessions endpoint: {from_date} to {to_date}")
        
        url = "https://api.zoom.us/v2/report/chat/sessions"
        params = {
            "from": from_date,
            "to": to_date,
            "page_size": 10  # Small page for testing
        }
        
        rate_limiter.sleep(0)
        response = requests.get(url, headers=auth_headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            sessions = data.get("sessions", [])
            logger.info(f"[OK] Chat sessions endpoint working - found {len(sessions)} sessions")
            
            # Test one session if available
            if sessions:
                session = sessions[0]
                session_id = session.get("id")
                session_name = session.get("name", "Unknown")
                
                logger.info(f"[TEST] Testing session messages for: {session_name}")
                
                # Test session messages endpoint
                messages_url = f"https://api.zoom.us/v2/report/chat/sessions/{session_id}"
                messages_params = {
                    "from": from_date,
                    "to": to_date,
                    "page_size": 5
                }
                
                rate_limiter.sleep(0)
                messages_response = requests.get(messages_url, headers=auth_headers, params=messages_params)
                
                if messages_response.status_code == 200:
                    messages_data = messages_response.json()
                    messages = messages_data.get("messages", [])
                    edited = messages_data.get("edited_messages", [])
                    deleted = messages_data.get("deleted_messages", [])
                    
                    logger.info(f"[OK] Session messages endpoint working - {len(messages)} messages, {len(edited)} edited, {len(deleted)} deleted")
                else:
                    logger.warning(f"[WARN] Session messages endpoint returned {messages_response.status_code}")
            else:
                logger.info("[INFO] No sessions found in the test period")
                
        elif response.status_code == 404:
            logger.info("[INFO] No chat sessions found for the test period")
        else:
            logger.error(f"[ERROR] Chat sessions endpoint returned {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"[ERROR] Error testing chat reports API: {e}")
        return False
    
    logger.info("[SUCCESS] Chat Reports API test completed successfully")
    return True

if __name__ == "__main__":
    success = test_chat_reports()
    sys.exit(0 if success else 1)
