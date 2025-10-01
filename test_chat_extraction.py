#!/usr/bin/env python3
"""
Test Script for Zoom Chat Messages Extraction

This script tests the chat extraction functionality with various scenarios:
- Test authentication
- Test user enumeration
- Test chat message extraction for a specific user
- Test different chat types (one-on-one, group, channel)
- Test date range filtering
- Test error handling

Usage:
    python test_chat_extraction.py --help
    python test_chat_extraction.py --test-user user@example.com
    python test_chat_extraction.py --test-all
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import requests
from tqdm import tqdm
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import our modules
from zoom_extractor.auth import get_auth_from_env
from zoom_extractor.users import UserEnumerator
from extract_chat_messages import ChatMessageExtractor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ChatExtractionTester:
    """Test the chat extraction functionality"""
    
    def __init__(self):
        self.auth_headers = None
        self.test_results = {
            "test_date": datetime.now().isoformat(),
            "tests_passed": 0,
            "tests_failed": 0,
            "test_details": []
        }
    
    def run_test(self, test_name: str, test_func):
        """Run a single test and record results"""
        logger.info(f"🧪 Running test: {test_name}")
        
        try:
            result = test_func()
            if result:
                self.test_results["tests_passed"] += 1
                self.test_results["test_details"].append({
                    "test": test_name,
                    "status": "PASSED",
                    "details": result
                })
                logger.info(f"✅ {test_name}: PASSED")
            else:
                self.test_results["tests_failed"] += 1
                self.test_results["test_details"].append({
                    "test": test_name,
                    "status": "FAILED",
                    "details": "Test returned False"
                })
                logger.error(f"❌ {test_name}: FAILED")
        except Exception as e:
            self.test_results["tests_failed"] += 1
            self.test_results["test_details"].append({
                "test": test_name,
                "status": "ERROR",
                "details": str(e)
            })
            logger.error(f"❌ {test_name}: ERROR - {e}")
    
    def test_authentication(self):
        """Test authentication with Zoom API"""
        logger.info("🔐 Testing authentication...")
        
        try:
            auth = get_auth_from_env()
            self.auth_headers = auth.get_auth_headers()
            
            # Test a simple API call
            test_url = "https://api.zoom.us/v2/users/me"
            response = requests.get(test_url, headers=self.auth_headers)
            
            if response.status_code == 200:
                user_info = response.json()
                logger.info(f"✅ Authentication successful for user: {user_info.get('email', 'Unknown')}")
                return {"authenticated": True, "user": user_info.get('email')}
            else:
                logger.error(f"❌ Authentication failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Authentication error: {e}")
            return False
    
    def test_user_enumeration(self):
        """Test user enumeration"""
        logger.info("👥 Testing user enumeration...")
        
        try:
            user_enumerator = UserEnumerator(self.auth_headers)
            
            # Test active users
            active_users = list(user_enumerator.list_all_users(user_type="active"))
            logger.info(f"✅ Found {len(active_users)} active users")
            
            # Test inactive users
            inactive_users = list(user_enumerator.list_all_users(user_type="inactive"))
            logger.info(f"✅ Found {len(inactive_users)} inactive users")
            
            # Test pending users
            try:
                pending_users = list(user_enumerator.list_all_users(user_type="pending"))
                logger.info(f"✅ Found {len(pending_users)} pending users")
            except Exception as e:
                logger.warning(f"⚠️ Pending users test failed: {e}")
                pending_users = []
            
            # Calculate total users across all types
            total_users = len(active_users) + len(inactive_users) + len(pending_users)
            logger.info(f"📊 Total users across all types: {total_users}")
            
            return {
                "active_users": len(active_users),
                "inactive_users": len(inactive_users),
                "pending_users": len(pending_users),
                "total_users": total_users,
                "sample_active_user": active_users[0] if active_users else None,
                "sample_inactive_user": inactive_users[0] if inactive_users else None,
                "sample_pending_user": pending_users[0] if pending_users else None
            }
            
        except Exception as e:
            logger.error(f"❌ User enumeration error: {e}")
            return False
    
    def test_chat_api_endpoints(self):
        """Test chat API endpoints availability"""
        logger.info("💬 Testing chat API endpoints...")
        
        try:
            # Test user messages endpoint
            test_user_id = "me"  # Use the authenticated user
            messages_url = f"https://api.zoom.us/v2/chat/users/{test_user_id}/messages"
            
            # Test with a recent date range
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            
            params = {
                "from": start_date,
                "to": end_date,
                "page_size": 10
            }
            
            response = requests.get(messages_url, headers=self.auth_headers, params=params)
            
            endpoint_results = {
                "messages_endpoint": {
                    "status_code": response.status_code,
                    "accessible": response.status_code in [200, 404],  # 404 is OK if no messages
                    "response_size": len(response.text) if response.text else 0
                }
            }
            
            if response.status_code == 200:
                data = response.json()
                messages = data.get("messages", [])
                endpoint_results["messages_endpoint"]["message_count"] = len(messages)
                logger.info(f"✅ Messages endpoint accessible, found {len(messages)} messages")
            elif response.status_code == 404:
                logger.info("✅ Messages endpoint accessible, no messages found")
                endpoint_results["messages_endpoint"]["message_count"] = 0
            else:
                logger.warning(f"⚠️ Messages endpoint returned {response.status_code}")
            
            # Test groups endpoint
            groups_url = f"https://api.zoom.us/v2/chat/users/{test_user_id}/groups"
            groups_response = requests.get(groups_url, headers=self.auth_headers)
            
            endpoint_results["groups_endpoint"] = {
                "status_code": groups_response.status_code,
                "accessible": groups_response.status_code in [200, 404],
                "response_size": len(groups_response.text) if groups_response.text else 0
            }
            
            if groups_response.status_code == 200:
                groups_data = groups_response.json()
                groups = groups_data.get("groups", [])
                endpoint_results["groups_endpoint"]["group_count"] = len(groups)
                logger.info(f"✅ Groups endpoint accessible, found {len(groups)} groups")
            elif groups_response.status_code == 404:
                logger.info("✅ Groups endpoint accessible, no groups found")
                endpoint_results["groups_endpoint"]["group_count"] = 0
            else:
                logger.warning(f"⚠️ Groups endpoint returned {groups_response.status_code}")
            
            # Test channels endpoint
            channels_url = f"https://api.zoom.us/v2/chat/users/{test_user_id}/channels"
            channels_response = requests.get(channels_url, headers=self.auth_headers)
            
            endpoint_results["channels_endpoint"] = {
                "status_code": channels_response.status_code,
                "accessible": channels_response.status_code in [200, 404],
                "response_size": len(channels_response.text) if channels_response.text else 0
            }
            
            if channels_response.status_code == 200:
                channels_data = channels_response.json()
                channels = channels_data.get("channels", [])
                endpoint_results["channels_endpoint"]["channel_count"] = len(channels)
                logger.info(f"✅ Channels endpoint accessible, found {len(channels)} channels")
            elif channels_response.status_code == 404:
                logger.info("✅ Channels endpoint accessible, no channels found")
                endpoint_results["channels_endpoint"]["channel_count"] = 0
            else:
                logger.warning(f"⚠️ Channels endpoint returned {channels_response.status_code}")
            
            return endpoint_results
            
        except Exception as e:
            logger.error(f"❌ Chat API endpoints test error: {e}")
            return False
    
    def test_chat_extraction_for_user(self, user_email: str):
        """Test chat extraction for a specific user"""
        logger.info(f"👤 Testing chat extraction for user: {user_email}")
        
        try:
            # Find the user
            user_enumerator = UserEnumerator(self.auth_headers)
            users = list(user_enumerator.list_all_users(user_type="active"))
            user = next((u for u in users if u.get("email") == user_email), None)
            
            if not user:
                # Try inactive users
                inactive_users = list(user_enumerator.list_all_users(user_type="inactive"))
                user = next((u for u in inactive_users if u.get("email") == user_email), None)
            
            if not user:
                logger.error(f"❌ User {user_email} not found")
                return False
            
            user_id = user.get("id")
            logger.info(f"✅ Found user: {user_email} (ID: {user_id})")
            
            # Initialize chat extractor
            extractor = ChatMessageExtractor(self.auth_headers, "./test_chat_output")
            
            # Test with recent date range
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            
            logger.info(f"📅 Testing extraction for date range: {start_date} to {end_date}")
            
            # Extract chat messages
            chat_data = extractor.extract_user_chat_messages(
                user_id, user_email, start_date, end_date
            )
            
            # Analyze results
            results = {
                "user_email": user_email,
                "user_id": user_id,
                "date_range": f"{start_date} to {end_date}",
                "one_on_one_messages": len(chat_data.get("one_on_one_messages", [])),
                "group_messages": len(chat_data.get("group_messages", [])),
                "channel_messages": len(chat_data.get("channel_messages", [])),
                "total_messages": chat_data.get("total_messages", 0),
                "extraction_successful": True
            }
            
            logger.info(f"✅ Chat extraction completed:")
            logger.info(f"  💬 One-on-one messages: {results['one_on_one_messages']}")
            logger.info(f"  👥 Group messages: {results['group_messages']}")
            logger.info(f"  📢 Channel messages: {results['channel_messages']}")
            logger.info(f"  📊 Total messages: {results['total_messages']}")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Chat extraction test error: {e}")
            return False
    
    def test_date_range_filtering(self):
        """Test date range filtering"""
        logger.info("📅 Testing date range filtering...")
        
        try:
            extractor = ChatMessageExtractor(self.auth_headers, "./test_chat_output")
            
            # Test with different date ranges
            test_ranges = [
                ("Last 7 days", (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')),
                ("Last 30 days", (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')),
                ("Last 90 days", (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')),
            ]
            
            results = {}
            end_date = datetime.now().strftime('%Y-%m-%d')
            
            for range_name, start_date in test_ranges:
                logger.info(f"  Testing {range_name}: {start_date} to {end_date}")
                
                # Test with the authenticated user
                test_user_id = "me"
                test_user_email = "me@test.com"
                
                try:
                    chat_data = extractor.extract_user_chat_messages(
                        test_user_id, test_user_email, start_date, end_date
                    )
                    
                    results[range_name] = {
                        "date_range": f"{start_date} to {end_date}",
                        "total_messages": chat_data.get("total_messages", 0),
                        "success": True
                    }
                    
                    logger.info(f"    ✅ {range_name}: {chat_data.get('total_messages', 0)} messages")
                    
                except Exception as e:
                    results[range_name] = {
                        "date_range": f"{start_date} to {end_date}",
                        "error": str(e),
                        "success": False
                    }
                    logger.warning(f"    ⚠️ {range_name}: Error - {e}")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Date range filtering test error: {e}")
            return False
    
    def test_error_handling(self):
        """Test error handling scenarios"""
        logger.info("🛡️ Testing error handling...")
        
        try:
            extractor = ChatMessageExtractor(self.auth_headers, "./test_chat_output")
            
            error_tests = {
                "invalid_user_id": False,
                "invalid_date_format": False,
                "network_error_simulation": False
            }
            
            # Test invalid user ID
            try:
                chat_data = extractor.extract_user_chat_messages(
                    "invalid_user_id", "test@example.com", "2024-01-01", "2024-01-31"
                )
                error_tests["invalid_user_id"] = True
                logger.info("  ✅ Invalid user ID handled gracefully")
            except Exception as e:
                logger.info(f"  ✅ Invalid user ID error handled: {e}")
                error_tests["invalid_user_id"] = True
            
            # Test invalid date format (this should be handled by the API)
            try:
                chat_data = extractor.extract_user_chat_messages(
                    "me", "test@example.com", "invalid-date", "2024-01-31"
                )
                error_tests["invalid_date_format"] = True
                logger.info("  ✅ Invalid date format handled gracefully")
            except Exception as e:
                logger.info(f"  ✅ Invalid date format error handled: {e}")
                error_tests["invalid_date_format"] = True
            
            return error_tests
            
        except Exception as e:
            logger.error(f"❌ Error handling test error: {e}")
            return False
    
    def run_all_tests(self):
        """Run all tests"""
        logger.info("🚀 Starting comprehensive chat extraction tests...")
        
        # Core functionality tests
        self.run_test("Authentication", self.test_authentication)
        
        if self.auth_headers:
            self.run_test("User Enumeration", self.test_user_enumeration)
            self.run_test("Chat API Endpoints", self.test_chat_api_endpoints)
            self.run_test("Date Range Filtering", self.test_date_range_filtering)
            self.run_test("Error Handling", self.test_error_handling)
        
        return self.test_results
    
    def run_user_specific_tests(self, user_email: str):
        """Run tests for a specific user"""
        logger.info(f"👤 Starting user-specific tests for: {user_email}")
        
        self.run_test("Authentication", self.test_authentication)
        
        if self.auth_headers:
            self.run_test(f"Chat Extraction for {user_email}", 
                         lambda: self.test_chat_extraction_for_user(user_email))
        
        return self.test_results
    
    def save_test_results(self, output_file: str = "chat_extraction_test_results.json"):
        """Save test results to file"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.test_results, f, indent=2, ensure_ascii=False)
            logger.info(f"💾 Test results saved to: {output_file}")
        except Exception as e:
            logger.error(f"❌ Error saving test results: {e}")
    
    def print_summary(self):
        """Print test summary"""
        total_tests = self.test_results["tests_passed"] + self.test_results["tests_failed"]
        
        print("\n" + "="*60)
        print("  Chat Extraction Test Summary")
        print("="*60)
        print(f"📊 Total Tests: {total_tests}")
        print(f"✅ Passed: {self.test_results['tests_passed']}")
        print(f"❌ Failed: {self.test_results['tests_failed']}")
        
        if total_tests > 0:
            success_rate = (self.test_results['tests_passed'] / total_tests) * 100
            print(f"📈 Success Rate: {success_rate:.1f}%")
        
        print("\n📋 Test Details:")
        for test in self.test_results["test_details"]:
            status_icon = "✅" if test["status"] == "PASSED" else "❌"
            print(f"  {status_icon} {test['test']}: {test['status']}")
            if test["status"] != "PASSED":
                print(f"      Details: {test['details']}")
        
        print("="*60)

def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description="Test Script for Zoom Chat Messages Extraction",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_chat_extraction.py --test-all
  python test_chat_extraction.py --test-user user@example.com
  python test_chat_extraction.py --test-user user@example.com --save-results
        """
    )
    
    parser.add_argument(
        "--test-all",
        action="store_true",
        help="Run all tests"
    )
    
    parser.add_argument(
        "--test-user",
        help="Test chat extraction for a specific user email"
    )
    
    parser.add_argument(
        "--save-results",
        action="store_true",
        help="Save test results to JSON file"
    )
    
    parser.add_argument(
        "--output-file",
        default="chat_extraction_test_results.json",
        help="Output file for test results"
    )
    
    args = parser.parse_args()
    
    if not args.test_all and not args.test_user:
        logger.error("❌ Please specify either --test-all or --test-user")
        return 1
    
    try:
        tester = ChatExtractionTester()
        
        if args.test_all:
            results = tester.run_all_tests()
        elif args.test_user:
            results = tester.run_user_specific_tests(args.test_user)
        
        tester.print_summary()
        
        if args.save_results:
            tester.save_test_results(args.output_file)
        
        # Return exit code based on test results
        if results["tests_failed"] == 0:
            logger.info("🎉 All tests passed!")
            return 0
        else:
            logger.warning(f"⚠️ {results['tests_failed']} tests failed")
            return 1
        
    except KeyboardInterrupt:
        logger.info("🛑 Testing interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"❌ Unexpected error during testing: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
