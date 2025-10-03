#!/usr/bin/env python3
"""
Diagnostic script for Zoom Chat API permissions issues.
Helps identify and fix "No permission to access this channel" errors.
"""

import os
import sys
import json
import requests
import logging
from datetime import datetime, timedelta
from pathlib import Path
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

class ChatPermissionDiagnostic:
    """Diagnostic tool for chat permission issues"""
    
    def __init__(self):
        try:
            self.auth = get_auth_from_env()
            self.auth_headers = self.auth.get_auth_headers()
            self.rate_limiter = RateLimiter()
            logger.info("Authentication successful")
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise
    
    def test_basic_api_access(self) -> Dict[str, Any]:
        """Test basic API access and token validity"""
        logger.info("Testing basic API access...")
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "basic_access": {},
            "account_info": {},
            "user_access": {},
            "chat_permissions": {},
            "recommendations": []
        }
        
        # Test 1: Basic account info
        try:
            url = "https://api.zoom.us/v2/accounts/me"
            response = requests.get(url, headers=self.auth_headers, timeout=30)
            
            results["basic_access"]["account_endpoint"] = {
                "status_code": response.status_code,
                "success": response.status_code == 200
            }
            
            if response.status_code == 200:
                account_data = response.json()
                results["account_info"] = {
                    "account_name": account_data.get("account_name", "Unknown"),
                    "account_id": account_data.get("account_id", "Unknown"),
                    "account_type": account_data.get("account_type", "Unknown"),
                    "plan_type": account_data.get("plan_type", "Unknown")
                }
                logger.info(f"Account: {account_data.get('account_name', 'Unknown')}")
                logger.info(f"Plan: {account_data.get('plan_type', 'Unknown')}")
            else:
                logger.error(f"Account endpoint failed: {response.text}")
                results["recommendations"].append("Fix basic authentication - account endpoint failed")
                
        except Exception as e:
            logger.error(f"Account endpoint error: {e}")
            results["basic_access"]["account_endpoint"] = {"error": str(e)}
            results["recommendations"].append("Fix authentication - unable to access account endpoint")
        
        return results
    
    def test_user_access(self) -> Dict[str, Any]:
        """Test user enumeration and access"""
        logger.info("Testing user access...")
        
        results = {
            "user_enumeration": {},
            "current_user_info": {},
            "user_permissions": {}
        }
        
        try:
            # Test user enumeration
            user_enumerator = UserEnumerator(self.auth_headers)
            
            # Try to get current user info using "me"
            try:
                current_user_url = "https://api.zoom.us/v2/users/me"
                response = requests.get(current_user_url, headers=self.auth_headers, timeout=30)
                
                results["current_user_info"] = {
                    "status_code": response.status_code,
                    "success": response.status_code == 200
                }
                
                if response.status_code == 200:
                    user_data = response.json()
                    results["current_user_info"]["user_data"] = {
                        "id": user_data.get("id", "Unknown"),
                        "email": user_data.get("email", "Unknown"),
                        "first_name": user_data.get("first_name", "Unknown"),
                        "last_name": user_data.get("last_name", "Unknown"),
                        "type": user_data.get("type", "Unknown"),
                        "role_name": user_data.get("role_name", "Unknown")
                    }
                    logger.info(f"Current user: {user_data.get('email', 'Unknown')} ({user_data.get('role_name', 'Unknown')})")
                else:
                    logger.warning(f"Current user endpoint failed: {response.text}")
                    
            except Exception as e:
                logger.error(f"Current user endpoint error: {e}")
                results["current_user_info"] = {"error": str(e)}
            
            # Test user enumeration
            try:
                active_users = list(user_enumerator.list_all_users(user_type="active"))
                results["user_enumeration"] = {
                    "active_users_count": len(active_users),
                    "success": True,
                    "sample_users": active_users[:3] if active_users else []
                }
                logger.info(f"Found {len(active_users)} active users")
            except Exception as e:
                logger.error(f"User enumeration error: {e}")
                results["user_enumeration"] = {"error": str(e)}
                
        except Exception as e:
            logger.error(f"User access test error: {e}")
            results["error"] = str(e)
        
        return results
    
    def test_chat_permissions(self) -> Dict[str, Any]:
        """Test chat API permissions specifically"""
        logger.info("Testing chat permissions...")
        
        results = {
            "chat_channels": {},
            "chat_messages": {},
            "permission_issues": [],
            "working_endpoints": [],
            "failed_endpoints": []
        }
        
        # Test 1: Try to get channels for "me"
        try:
            logger.info("Testing channels endpoint for 'me'...")
            channels_url = "https://api.zoom.us/v2/chat/users/me/channels"
            response = requests.get(channels_url, headers=self.auth_headers, timeout=30)
            
            results["chat_channels"]["me_endpoint"] = {
                "status_code": response.status_code,
                "success": response.status_code == 200
            }
            
            if response.status_code == 200:
                data = response.json()
                channels = data.get("channels", [])
                results["chat_channels"]["me_endpoint"]["channel_count"] = len(channels)
                results["chat_channels"]["me_endpoint"]["channels"] = channels[:5]  # First 5 channels
                results["working_endpoints"].append("GET /v2/chat/users/me/channels")
                logger.info(f"✅ Successfully accessed {len(channels)} channels for 'me'")
            else:
                results["failed_endpoints"].append(f"GET /v2/chat/users/me/channels - {response.status_code}")
                results["permission_issues"].append(f"Channels endpoint failed: {response.status_code} - {response.text}")
                logger.error(f"❌ Channels endpoint failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"Channels endpoint error: {e}")
            results["chat_channels"]["me_endpoint"] = {"error": str(e)}
            results["failed_endpoints"].append(f"GET /v2/chat/users/me/channels - ERROR")
            results["permission_issues"].append(f"Channels endpoint error: {e}")
        
        # Test 2: Try to get channels for a specific user (if we have users)
        try:
            user_enumerator = UserEnumerator(self.auth_headers)
            active_users = list(user_enumerator.list_all_users(user_type="active"))
            
            if active_users:
                test_user = active_users[0]
                user_id = test_user.get("id")
                user_email = test_user.get("email")
                
                logger.info(f"Testing channels endpoint for user: {user_email}")
                channels_url = f"https://api.zoom.us/v2/chat/users/{user_id}/channels"
                response = requests.get(channels_url, headers=self.auth_headers, timeout=30)
                
                results["chat_channels"]["specific_user_endpoint"] = {
                    "user_email": user_email,
                    "user_id": user_id,
                    "status_code": response.status_code,
                    "success": response.status_code == 200
                }
                
                if response.status_code == 200:
                    data = response.json()
                    channels = data.get("channels", [])
                    results["chat_channels"]["specific_user_endpoint"]["channel_count"] = len(channels)
                    results["working_endpoints"].append(f"GET /v2/chat/users/{user_id}/channels")
                    logger.info(f"✅ Successfully accessed {len(channels)} channels for {user_email}")
                else:
                    results["failed_endpoints"].append(f"GET /v2/chat/users/{user_id}/channels - {response.status_code}")
                    results["permission_issues"].append(f"User channels endpoint failed for {user_email}: {response.status_code} - {response.text}")
                    logger.error(f"❌ User channels endpoint failed: {response.status_code} - {response.text}")
            else:
                results["chat_channels"]["specific_user_endpoint"] = {"error": "No active users found"}
                
        except Exception as e:
            logger.error(f"Specific user channels test error: {e}")
            results["chat_channels"]["specific_user_endpoint"] = {"error": str(e)}
        
        # Test 3: Try messages endpoint (if we have channels)
        if results["chat_channels"].get("me_endpoint", {}).get("success"):
            try:
                channels = results["chat_channels"]["me_endpoint"].get("channels", [])
                if channels:
                    test_channel = channels[0]
                    channel_id = test_channel.get("id")
                    channel_name = test_channel.get("name", "Unknown")
                    
                    logger.info(f"Testing messages endpoint for channel: {channel_name}")
                    messages_url = "https://api.zoom.us/v2/chat/users/me/messages"
                    params = {"to_channel": channel_id, "page_size": 1}
                    
                    response = requests.get(messages_url, headers=self.auth_headers, params=params, timeout=30)
                    
                    results["chat_messages"]["test_channel"] = {
                        "channel_id": channel_id,
                        "channel_name": channel_name,
                        "status_code": response.status_code,
                        "success": response.status_code == 200
                    }
                    
                    if response.status_code == 200:
                        results["working_endpoints"].append("GET /v2/chat/users/me/messages")
                        logger.info(f"✅ Successfully accessed messages for channel: {channel_name}")
                    else:
                        results["failed_endpoints"].append(f"GET /v2/chat/users/me/messages - {response.status_code}")
                        results["permission_issues"].append(f"Messages endpoint failed for {channel_name}: {response.status_code} - {response.text}")
                        logger.error(f"❌ Messages endpoint failed: {response.status_code} - {response.text}")
                else:
                    results["chat_messages"]["test_channel"] = {"error": "No channels available for testing"}
                    
            except Exception as e:
                logger.error(f"Messages endpoint test error: {e}")
                results["chat_messages"]["test_channel"] = {"error": str(e)}
        
        return results
    
    def generate_recommendations(self, test_results: Dict[str, Any]) -> List[str]:
        """Generate specific recommendations based on test results"""
        recommendations = []
        
        # Check basic access
        if not test_results.get("basic_access", {}).get("account_endpoint", {}).get("success"):
            recommendations.append("🔧 Fix basic authentication - unable to access account endpoint")
        
        # Check account type
        account_info = test_results.get("account_info", {})
        plan_type = account_info.get("plan_type", "").lower()
        if "basic" in plan_type:
            recommendations.append("⚠️  Basic plan detected - some chat features may be limited")
        
        # Check user permissions
        current_user = test_results.get("current_user_info", {}).get("user_data", {})
        role_name = current_user.get("role_name", "").lower()
        if "admin" not in role_name and "owner" not in role_name:
            recommendations.append("⚠️  Current user is not an admin - may need admin permissions for chat access")
        
        # Check chat permissions
        chat_results = test_results.get("chat_permissions", {})
        failed_endpoints = chat_results.get("failed_endpoints", [])
        
        if any("channels" in endpoint for endpoint in failed_endpoints):
            recommendations.extend([
                "🔑 Add required chat scopes to your OAuth app:",
                "   - chat:read:admin",
                "   - imchat:read:admin", 
                "   - team_chat:read:admin",
                "   - user:read:admin",
                "",
                "📋 How to add scopes:",
                "   1. Go to Zoom Marketplace (https://marketplace.zoom.us/)",
                "   2. Find your Server-to-Server OAuth app",
                "   3. Click 'Scopes' tab",
                "   4. Add the missing scopes listed above",
                "   5. Save and re-authorize the app",
                "   6. Regenerate your access token"
            ])
        
        if any("messages" in endpoint for endpoint in failed_endpoints):
            recommendations.extend([
                "💬 Messages endpoint failing - check if you have:",
                "   - Proper chat permissions",
                "   - Access to the specific channel",
                "   - Correct user context ('me' vs specific user ID)"
            ])
        
        # Alternative approaches
        if chat_results.get("failed_endpoints"):
            recommendations.extend([
                "",
                "🔄 Alternative approaches to try:",
                "   1. Use a specific user ID instead of 'me':",
                "      python simple_chat_extractor_improved.py --extractor-user <user_id>",
                "",
                "   2. Try the Reports API approach:",
                "      python extract_chat_reports.py --from-date 2024-01-01",
                "",
                "   3. Use individual user extraction:",
                "      python extract_chat_messages.py --user-filter user@example.com"
            ])
        
        return recommendations
    
    def run_full_diagnostic(self) -> Dict[str, Any]:
        """Run complete diagnostic and return results"""
        logger.info("Starting comprehensive chat permission diagnostic...")
        
        results = {
            "diagnostic_timestamp": datetime.now().isoformat(),
            "basic_access": {},
            "user_access": {},
            "chat_permissions": {},
            "recommendations": []
        }
        
        # Run all tests
        results["basic_access"] = self.test_basic_api_access()
        results["user_access"] = self.test_user_access()
        results["chat_permissions"] = self.test_chat_permissions()
        
        # Generate recommendations
        results["recommendations"] = self.generate_recommendations(results)
        
        # Save results
        output_file = Path("chat_permission_diagnostic_results.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Diagnostic complete! Results saved to: {output_file}")
        
        return results
    
    def print_summary(self, results: Dict[str, Any]):
        """Print a summary of diagnostic results"""
        print("\n" + "="*80)
        print("🔍 ZOOM CHAT PERMISSION DIAGNOSTIC SUMMARY")
        print("="*80)
        
        # Basic access
        basic_access = results.get("basic_access", {})
        account_endpoint = basic_access.get("account_endpoint", {})
        if account_endpoint.get("success"):
            account_info = basic_access.get("account_info", {})
            print(f"✅ Account Access: {account_info.get('account_name', 'Unknown')} ({account_info.get('plan_type', 'Unknown')})")
        else:
            print("❌ Account Access: FAILED")
        
        # User access
        user_access = results.get("user_access", {})
        current_user = user_access.get("current_user_info", {})
        if current_user.get("success"):
            user_data = current_user.get("user_data", {})
            print(f"✅ Current User: {user_data.get('email', 'Unknown')} ({user_data.get('role_name', 'Unknown')})")
        else:
            print("❌ Current User: FAILED")
        
        # Chat permissions
        chat_perms = results.get("chat_permissions", {})
        working_endpoints = chat_perms.get("working_endpoints", [])
        failed_endpoints = chat_perms.get("failed_endpoints", [])
        
        print(f"\n📊 Chat API Results:")
        print(f"   ✅ Working endpoints: {len(working_endpoints)}")
        print(f"   ❌ Failed endpoints: {len(failed_endpoints)}")
        
        if working_endpoints:
            print("   Working:")
            for endpoint in working_endpoints:
                print(f"     - {endpoint}")
        
        if failed_endpoints:
            print("   Failed:")
            for endpoint in failed_endpoints:
                print(f"     - {endpoint}")
        
        # Recommendations
        recommendations = results.get("recommendations", [])
        if recommendations:
            print(f"\n💡 Recommendations:")
            for rec in recommendations:
                print(f"   {rec}")
        
        print("\n" + "="*80)

def main():
    """Main entry point"""
    try:
        diagnostic = ChatPermissionDiagnostic()
        results = diagnostic.run_full_diagnostic()
        diagnostic.print_summary(results)
        
        # Exit with error code if there are issues
        chat_perms = results.get("chat_permissions", {})
        if chat_perms.get("failed_endpoints"):
            print("\n⚠️  Some chat endpoints failed. Check recommendations above.")
            return 1
        else:
            print("\n✅ All tests passed! Chat permissions look good.")
            return 0
            
    except Exception as e:
        logger.error(f"Diagnostic failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
