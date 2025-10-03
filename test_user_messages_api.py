#!/usr/bin/env python3
"""
Test script for the /chat/users/{userId}/messages API endpoint
Tests different variations to understand what works for message extraction
"""

import os
import sys
import json
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

# Add the zoom_extractor module to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from zoom_extractor.auth import get_auth_from_env
from zoom_extractor.users import UserEnumerator
from zoom_extractor.rate_limiter import RateLimiter

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class UserMessagesAPITester:
    """Test the /chat/users/{userId}/messages API endpoint"""
    
    def __init__(self):
        try:
            self.auth = get_auth_from_env()
            self.auth_headers = self.auth.get_auth_headers()
            self.rate_limiter = RateLimiter()
            logger.info("Authentication successful")
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise
    
    def test_user_messages_endpoint(self, user_id: str = "me", channel_id: str = None, contact_email: str = None):
        """Test the GET /chat/users/{userId}/messages endpoint with different parameters"""
        
        logger.info(f"Testing /chat/users/{user_id}/messages endpoint")
        
        base_url = f"https://api.zoom.us/v2/chat/users/{user_id}/messages"
        
        # Test different parameter combinations based on Zoom API specification
        test_cases = [
            {
                "name": "Basic request (no parameters)",
                "params": {"page_size": "50"}
            },
            {
                "name": "With channel ID",
                "params": {"page_size": "50", "to_channel": channel_id} if channel_id else None
            },
            {
                "name": "With contact email",
                "params": {"page_size": "50", "to_contact": contact_email} if contact_email else None
            },
            {
                "name": "With date range (last 30 days)",
                "params": {
                    "page_size": "50",
                    "from": (datetime.now() - timedelta(days=30)).isoformat() + "Z",
                    "to": datetime.now().isoformat() + "Z"
                }
            },
            {
                "name": "With date range (from 2020)",
                "params": {
                    "page_size": "50",
                    "from": "2020-01-01T00:00:00Z",
                    "to": datetime.now().isoformat() + "Z"
                }
            },
            {
                "name": "With date range and channel (from 2020)",
                "params": {
                    "page_size": "50",
                    "to_channel": channel_id,
                    "from": "2020-01-01T00:00:00Z",
                    "to": datetime.now().isoformat() + "Z"
                } if channel_id else None
            },
            {
                "name": "With file downloads enabled",
                "params": {
                    "page_size": "50",
                    "download_file_formats": "audio/mp4"
                }
            },
            {
                "name": "With comprehensive parameters (from 2020)",
                "params": {
                    "page_size": "50",
                    "to_channel": channel_id,
                    "from": "2020-01-01T00:00:00Z",
                    "to": datetime.now().isoformat() + "Z",
                    "include_deleted_and_edited_message": "true",
                    "download_file_formats": "audio/mp4"
                } if channel_id else None
            },
            {
                "name": "With search parameters",
                "params": {
                    "page_size": "50",
                    "to_channel": channel_id,
                    "search_type": "message",
                    "search_key": "hello"
                } if channel_id else None
            },
            {
                "name": "With exclude child messages",
                "params": {
                    "page_size": "50",
                    "to_channel": channel_id,
                    "exclude_child_message": "true"
                } if channel_id else None
            }
        ]
        
        results = {}
        
        for test_case in test_cases:
            if test_case["params"] is None:
                logger.info(f"Skipping {test_case['name']} - no parameters")
                continue
                
            logger.info(f"\n🧪 Testing: {test_case['name']}")
            logger.info(f"Parameters: {test_case['params']}")
            
            try:
                self.rate_limiter.sleep(0)
                response = requests.get(base_url, headers=self.auth_headers, params=test_case["params"], timeout=30)
                
                result = {
                    "status_code": response.status_code,
                    "success": response.status_code == 200,
                    "params": test_case["params"]
                }
                
                if response.status_code == 200:
                    data = response.json()
                    messages = data.get("messages", [])
                    next_page_token = data.get("next_page_token")
                    
                    result.update({
                        "message_count": len(messages),
                        "next_page_token": next_page_token,
                        "has_more_pages": bool(next_page_token),
                        "sample_message": messages[0] if messages else None
                    })
                    
                    logger.info(f"✅ SUCCESS: Found {len(messages)} messages")
                    if messages:
                        sample = messages[0]
                        logger.info(f"   Sample message: {sample.get('message', 'No message text')[:100]}...")
                        logger.info(f"   From: {sample.get('sender', 'Unknown')}")
                        logger.info(f"   Date: {sample.get('date_time', 'Unknown')}")
                    
                elif response.status_code == 404:
                    result["error"] = "Endpoint not found"
                    logger.warning(f"⚠️  404: Endpoint not found")
                elif response.status_code == 400:
                    result["error"] = response.text
                    logger.warning(f"⚠️  400: {response.text}")
                else:
                    result["error"] = response.text
                    logger.error(f"❌ {response.status_code}: {response.text}")
                
                results[test_case["name"]] = result
                
            except Exception as e:
                logger.error(f"❌ Exception: {e}")
                results[test_case["name"]] = {
                    "status_code": None,
                    "success": False,
                    "error": str(e),
                    "params": test_case["params"]
                }
        
        return results
    
    def test_different_users(self, channel_id: str = None):
        """Test the endpoint with different users"""
        
        logger.info(f"\n👥 Testing with different users")
        
        # Get list of users
        try:
            user_enumerator = UserEnumerator(self.auth_headers)
            active_users = list(user_enumerator.list_all_users(user_type="active"))
            
            logger.info(f"Found {len(active_users)} active users")
            
            # Test with first few users
            test_users = active_users[:3]  # Test with first 3 users
            
            user_results = {}
            
            for user in test_users:
                user_id = user.get("id")
                user_email = user.get("email")
                
                if not user_id or not user_email:
                    continue
                
                logger.info(f"\n🔍 Testing with user: {user_email} (ID: {user_id})")
                
                # Test basic endpoint for this user
                results = self.test_user_messages_endpoint(user_id=user_id, channel_id=channel_id)
                user_results[user_email] = results
            
            return user_results
            
        except Exception as e:
            logger.error(f"Error testing different users: {e}")
            return {}
    
    def test_channel_specific_extraction(self, channel_id: str, channel_name: str = "Unknown"):
        """Test channel-specific message extraction with different approaches"""
        
        logger.info(f"\n📢 Testing channel-specific extraction: {channel_name}")
        logger.info(f"Channel ID: {channel_id}")
        
        approaches = [
            {
                "name": "User 'me' with channel ID",
                "user_id": "me",
                "params": {"to_channel": channel_id, "page_size": "50"}
            },
            {
                "name": "User 'me' with channel ID and date range (from 2020)",
                "user_id": "me", 
                "params": {
                    "to_channel": channel_id,
                    "page_size": "50",
                    "from": "2020-01-01T00:00:00Z",
                    "to": datetime.now().isoformat() + "Z"
                }
            },
            {
                "name": "User 'me' without date range",
                "user_id": "me",
                "params": {"to_channel": channel_id, "page_size": "10"}
            },
            {
                "name": "User 'me' with comprehensive parameters (from 2020)",
                "user_id": "me",
                "params": {
                    "to_channel": channel_id,
                    "page_size": "50",
                    "from": "2020-01-01T00:00:00Z",
                    "to": datetime.now().isoformat() + "Z",
                    "include_deleted_and_edited_message": "true",
                    "download_file_formats": "audio/mp4"
                }
            }
        ]
        
        results = {}
        
        for approach in approaches:
            logger.info(f"\n🔧 Testing: {approach['name']}")
            
            url = f"https://api.zoom.us/v2/chat/users/{approach['user_id']}/messages"
            
            try:
                self.rate_limiter.sleep(0)
                response = requests.get(url, headers=self.auth_headers, params=approach["params"], timeout=30)
                
                result = {
                    "status_code": response.status_code,
                    "success": response.status_code == 200,
                    "approach": approach["name"],
                    "params": approach["params"]
                }
                
                if response.status_code == 200:
                    data = response.json()
                    messages = data.get("messages", [])
                    
                    result.update({
                        "message_count": len(messages),
                        "next_page_token": data.get("next_page_token"),
                        "sample_messages": messages[:3] if messages else []
                    })
                    
                    logger.info(f"✅ Found {len(messages)} messages")
                    
                else:
                    result["error"] = response.text
                    logger.warning(f"⚠️  {response.status_code}: {response.text}")
                
                results[approach["name"]] = result
                
            except Exception as e:
                logger.error(f"❌ Exception: {e}")
                results[approach["name"]] = {
                    "status_code": None,
                    "success": False,
                    "error": str(e),
                    "approach": approach["name"]
                }
        
        return results
    
    def test_exact_api_format(self, user_id: str = "me", channel_id: str = None):
        """Test the exact API format from the documentation"""
        
        logger.info(f"\n🔬 Testing exact API format from documentation")
        
        # Test the exact format you provided
        exact_params = {
            "page_size": "10",
            "include_deleted_and_edited_message": "true",
            "download_file_formats": "audio/mp4"
        }
        
        if channel_id:
            exact_params["to_channel"] = channel_id
        
        # Add date range (from 2020 to capture older messages)
        exact_params.update({
            "from": "2020-01-01T00:00:00Z",
            "to": datetime.now().isoformat() + "Z"
        })
        
        url = f"https://api.zoom.us/v2/chat/users/{user_id}/messages"
        
        logger.info(f"Testing exact format:")
        logger.info(f"URL: {url}")
        logger.info(f"Params: {exact_params}")
        
        try:
            self.rate_limiter.sleep(0)
            response = requests.get(url, headers=self.auth_headers, params=exact_params, timeout=30)
            
            result = {
                "status_code": response.status_code,
                "success": response.status_code == 200,
                "params": exact_params,
                "url": url
            }
            
            if response.status_code == 200:
                data = response.json()
                messages = data.get("messages", [])
                
                result.update({
                    "message_count": len(messages),
                    "next_page_token": data.get("next_page_token"),
                    "sample_messages": messages[:3] if messages else []
                })
                
                logger.info(f"✅ SUCCESS: Found {len(messages)} messages with exact format")
                
            else:
                result["error"] = response.text
                logger.warning(f"⚠️  {response.status_code}: {response.text}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Exception: {e}")
            return {
                "status_code": None,
                "success": False,
                "error": str(e),
                "params": exact_params
            }

def main():
    """Main test function"""
    
    try:
        tester = UserMessagesAPITester()
        
        # Test with the specific channel from your example
        channel_id = "d6c65e4872704eaf8b859c8bd5adc5ed"  # NAIDOC Week channel
        
        print("\n" + "="*80)
        print("🧪 TESTING ZOOM CHAT MESSAGES API")
        print("="*80)
        
        # Test 1: Basic endpoint with 'me'
        print("\n1️⃣  Testing basic /chat/users/me/messages endpoint:")
        basic_results = tester.test_user_messages_endpoint(user_id="me")
        
        # Test 2: Channel-specific extraction
        print(f"\n2️⃣  Testing channel-specific extraction for: {channel_id}")
        channel_results = tester.test_channel_specific_extraction(channel_id, "NAIDOC Week")
        
        # Test 3: Different users (if we have access)
        print(f"\n3️⃣  Testing with different users:")
        user_results = tester.test_different_users(channel_id)
        
        # Test 4: Exact API format from documentation
        print(f"\n4️⃣  Testing exact API format from documentation:")
        exact_format_results = tester.test_exact_api_format(user_id="me", channel_id=channel_id)
        
        # Save all results
        all_results = {
            "timestamp": datetime.now().isoformat(),
            "channel_id": channel_id,
            "basic_endpoint_tests": basic_results,
            "channel_specific_tests": channel_results,
            "user_specific_tests": user_results,
            "exact_format_test": exact_format_results
        }
        
        output_file = "user_messages_api_test_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n📊 RESULTS SUMMARY:")
        print(f"✅ Tests completed - results saved to: {output_file}")
        
        # Print summary
        successful_tests = 0
        total_tests = 0
        
        for test_type, results in all_results.items():
            if isinstance(results, dict) and "status_code" not in str(results):
                for test_name, result in results.items():
                    if isinstance(result, dict):
                        total_tests += 1
                        if result.get("success"):
                            successful_tests += 1
        
        print(f"📈 Success Rate: {successful_tests}/{total_tests} tests passed")
        
        return 0
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
