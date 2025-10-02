#!/usr/bin/env python3
"""
Test script for Simple Chat Extractor
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
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_simple_chat():
    """Test simple chat extractor"""
    
    logger.info("Testing Simple Chat Extractor")
    
    # Test authentication
    try:
        auth = get_auth_from_env()
        auth_headers = auth.get_auth_headers()
        logger.info("✓ Authentication successful")
    except Exception as e:
        logger.error(f"✗ Authentication failed: {e}")
        return False
    
    # Test channels endpoint
    try:
        import requests
        from zoom_extractor.rate_limiter import RateLimiter
        
        rate_limiter = RateLimiter()
        
        logger.info("Testing channels endpoint...")
        url = "https://api.zoom.us/v2/chat/users/me/channels"
        params = {"page_size": 10}
        
        rate_limiter.sleep(0)
        response = requests.get(url, headers=auth_headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            channels = data.get("channels", [])
            logger.info(f"✓ Channels endpoint working - found {len(channels)} channels")
            
            if channels:
                channel = channels[0]
                channel_id = channel.get("id")
                channel_name = channel.get("name", "Unknown")
                logger.info(f"  Sample channel: {channel_name} ({channel_id})")
            
        elif response.status_code == 404:
            logger.info("✓ Channels endpoint working - no channels found")
        else:
            logger.error(f"✗ Channels endpoint failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"✗ Error testing channels endpoint: {e}")
        return False
    
    # Test messages endpoint (if we have a channel)
    try:
        if channels:
            channel_id = channels[0].get("id")
            logger.info(f"Testing messages endpoint for channel: {channel_id}")
            
            # Test with last 7 days
            to_date = datetime.now().isoformat() + "Z"
            from_date = (datetime.now() - timedelta(days=7)).isoformat() + "Z"
            
            messages_url = "https://api.zoom.us/v2/chat/users/me/messages"
            messages_params = {
                "to_channel": channel_id,
                "from": from_date,
                "to": to_date,
                "page_size": 5
            }
            
            rate_limiter.sleep(0)
            messages_response = requests.get(messages_url, headers=auth_headers, params=messages_params)
            
            if messages_response.status_code == 200:
                messages_data = messages_response.json()
                messages = messages_data.get("messages", [])
                logger.info(f"✓ Messages endpoint working - found {len(messages)} messages")
                
                if messages:
                    message = messages[0]
                    message_text = message.get("message", "No text")[:50]
                    logger.info(f"  Sample message: {message_text}...")
                    
            elif messages_response.status_code == 404:
                logger.info("✓ Messages endpoint working - no messages found")
            else:
                logger.error(f"✗ Messages endpoint failed: {messages_response.status_code} - {messages_response.text}")
                return False
        else:
            logger.info("Skipping messages test - no channels available")
            
    except Exception as e:
        logger.error(f"✗ Error testing messages endpoint: {e}")
        return False
    
    logger.info("✓ All tests passed!")
    return True

if __name__ == "__main__":
    success = test_simple_chat()
    sys.exit(0 if success else 1)
