#!/usr/bin/env python3
"""
Improved Simple Zoom Chat Extractor

Fixes the duplicate channel extraction issue by:
1. Collecting all unique channels from all users
2. Extracting each channel only once
3. Avoiding duplicate processing
"""

import os
import sys
import json
import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
import click
from tqdm import tqdm

# Add the zoom_extractor module to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from zoom_extractor.auth import get_auth_from_env
from zoom_extractor.users import UserEnumerator
from zoom_extractor.rate_limiter import RateLimiter
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ImprovedChatExtractor:
    """Improved chat extractor that avoids duplicate channel processing"""
    
    def __init__(self, auth_headers: Dict[str, str], output_dir: str = "./chat_extraction", auth=None):
        self.auth_headers = auth_headers
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.rate_limiter = RateLimiter()
        # Store auth object for token refresh
        self.auth = auth
        
        # Create subdirectories
        (self.output_dir / "channels").mkdir(exist_ok=True)
        (self.output_dir / "messages").mkdir(exist_ok=True)
        (self.output_dir / "files").mkdir(exist_ok=True)
        (self.output_dir / "_metadata").mkdir(exist_ok=True)
        
        logger.info(f"Chat extraction output: {self.output_dir}")
    
    def refresh_auth_headers(self):
        """Refresh authentication headers if token has expired"""
        if self.auth:
            try:
                logger.info("Refreshing authentication headers...")
                self.auth_headers = self.auth.get_auth_headers()
                logger.info("Authentication headers refreshed successfully")
            except Exception as e:
                logger.error(f"Failed to refresh auth headers: {e}")
                raise
    
    def make_api_request(self, url: str, params: Dict = None, max_retries: int = 3) -> requests.Response:
        """Make API request with automatic token refresh on 401 errors"""
        if params is None:
            params = {}
            
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=self.auth_headers, params=params)
                
                # If we get a 401 (unauthorized), try to refresh the token
                if response.status_code == 401 and self.auth and attempt < max_retries - 1:
                    logger.warning(f"Got 401 error, attempting to refresh token (attempt {attempt + 1})")
                    self.refresh_auth_headers()
                    continue
                
                return response
                
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"API request failed, retrying (attempt {attempt + 1}): {e}")
                    continue
                else:
                    raise
        
        return response
    
    def get_user_channels(self, user_id: str = "me") -> List[Dict]:
        """Get user's channels using GET /v2/chat/users/{userId}/channels"""
        channels = []
        
        try:
            logger.info(f"Getting channels for user: {user_id}")
            
            url = f"https://api.zoom.us/v2/chat/users/{user_id}/channels"
            params = {"page_size": 50}
            
            next_page_token = None
            
            while True:
                if next_page_token:
                    params["next_page_token"] = next_page_token
                
                self.rate_limiter.sleep(0)
                response = self.make_api_request(url, params)
                
                if response.status_code == 200:
                    data = response.json()
                    page_channels = data.get("channels", [])
                    channels.extend(page_channels)
                    
                    next_page_token = data.get("next_page_token")
                    if not next_page_token:
                        break
                        
                elif response.status_code == 404:
                    logger.info(f"No channels found for user {user_id}")
                    break
                elif response.status_code == 400 and "No permission to access" in response.text:
                    logger.warning(f"No permission to access channels for user {user_id} - skipping")
                    break
                else:
                    logger.error(f"Failed to get channels: {response.status_code} - {response.text}")
                    break
                    
        except Exception as e:
            logger.error(f"Error getting channels: {e}")
        
        return channels
    
    def get_all_unique_channels(self, include_inactive: bool = True) -> List[Dict]:
        """Get all unique channels from all users (deduplicated)"""
        
        logger.info("Collecting all unique channels from all users")
        
        # Initialize user enumerator
        user_enumerator = UserEnumerator(self.auth_headers)
        
        # Get all users
        all_users = []
        
        logger.info("Getting active users...")
        try:
            active_users = list(user_enumerator.list_all_users(user_type="active"))
            all_users.extend(active_users)
            logger.info(f"Found {len(active_users)} active users")
        except Exception as e:
            logger.error(f"Could not get active users: {e}")
        
        if include_inactive:
            logger.info("Getting inactive users...")
            try:
                inactive_users = list(user_enumerator.list_all_users(user_type="inactive"))
                all_users.extend(inactive_users)
                logger.info(f"Found {len(inactive_users)} inactive users")
            except Exception as e:
                logger.error(f"Could not get inactive users: {e}")
        
        logger.info("Getting pending users...")
        try:
            pending_users = list(user_enumerator.list_all_users(user_type="pending"))
            all_users.extend(pending_users)
            logger.info(f"Found {len(pending_users)} pending users")
        except Exception as e:
            logger.error(f"Could not get pending users: {e}")
        
        logger.info(f"Total users to check: {len(all_users)}")
        
        # Collect all channels from all users
        all_channels = []
        seen_channel_ids: Set[str] = set()
        
        for i, user in enumerate(tqdm(all_users, desc="Collecting channels"), 1):
            user_email = user.get("email")
            user_id = user.get("id")
            
            if not user_email or not user_id:
                continue
            
            try:
                # Get channels for this user
                user_channels = self.get_user_channels(user_id)
                
                # Add unique channels
                for channel in user_channels:
                    channel_id = channel.get("id")
                    if channel_id and channel_id not in seen_channel_ids:
                        seen_channel_ids.add(channel_id)
                        # Add metadata about which users can see this channel
                        channel["accessible_by_users"] = [user_email]
                        all_channels.append(channel)
                    elif channel_id:
                        # Channel already seen, just add this user to the list
                        for existing_channel in all_channels:
                            if existing_channel.get("id") == channel_id:
                                if user_email not in existing_channel.get("accessible_by_users", []):
                                    existing_channel["accessible_by_users"].append(user_email)
                                break
                
            except Exception as e:
                logger.error(f"Error getting channels for user {user_email}: {e}")
                continue
        
        logger.info(f"Found {len(all_channels)} unique channels")
        return all_channels
    
    def get_messages(self, user_id: str = "me", to_contact: Optional[str] = None, 
                    to_channel: Optional[str] = None, from_date: Optional[str] = None,
                    to_date: Optional[str] = None, include_files: bool = True) -> List[Dict]:
        """Get messages using GET /v2/chat/users/{userId}/messages"""
        
        if not to_contact and not to_channel:
            logger.error("Must specify either to_contact or to_channel")
            return []
        
        messages = []
        
        try:
            logger.info(f"Getting messages for user: {user_id}")
            if to_contact:
                logger.info(f"Contact: {to_contact}")
            if to_channel:
                logger.info(f"Channel: {to_channel}")
            
            url = f"https://api.zoom.us/v2/chat/users/{user_id}/messages"
            params = {
                "page_size": 50,
                "download_file_formats": "mp4" if include_files else None
            }
            
            # Add contact or channel parameter
            if to_contact:
                params["to_contact"] = to_contact
            if to_channel:
                params["to_channel"] = to_channel
            
            # Add date filters if provided
            if from_date:
                params["from"] = from_date
            if to_date:
                params["to"] = to_date
            
            # Remove None values
            params = {k: v for k, v in params.items() if v is not None}
            
            next_page_token = None
            
            while True:
                if next_page_token:
                    params["next_page_token"] = next_page_token
                
                self.rate_limiter.sleep(0)
                response = self.make_api_request(url, params)
                
                # Debug: Log the full API request details
                logger.debug(f"API Request: {url}")
                logger.debug(f"API Params: {params}")
                logger.debug(f"API Response Status: {response.status_code}")
                logger.debug(f"API Response Headers: {dict(response.headers)}")
                
                if response.status_code == 200:
                    data = response.json()
                    page_messages = data.get("messages", [])
                    messages.extend(page_messages)
                    
                    # Debug: Log detailed response info
                    logger.info(f"API Response: Found {len(page_messages)} messages in this page")
                    logger.debug(f"Full API Response: {json.dumps(data, indent=2)}")
                    
                    next_page_token = data.get("next_page_token")
                    if not next_page_token:
                        logger.info(f"Reached end of messages (no more pages)")
                        break
                    else:
                        logger.info(f"More pages available, continuing...")
                        
                elif response.status_code == 404:
                    logger.info(f"No messages found (404 - endpoint not found)")
                    logger.debug(f"Response body: {response.text}")
                    break
                elif response.status_code == 400 and "No permission to access" in response.text:
                    logger.warning(f"No permission to access messages for user {user_id} - channel may be restricted")
                    logger.debug(f"Response body: {response.text}")
                    break
                else:
                    logger.error(f"Failed to get messages: {response.status_code} - {response.text}")
                    logger.debug(f"Full response: {response.text}")
                    break
                    
        except Exception as e:
            logger.error(f"Error getting messages: {e}")
        
        return messages
    
    def download_file(self, file_info: Dict) -> Optional[str]:
        """Download a file attachment"""
        try:
            download_url = file_info.get("download_url")
            file_name = file_info.get("file_name", "unknown_file")
            file_id = file_info.get("file_id", "unknown_id")
            
            if not download_url:
                logger.warning(f"No download URL for file {file_id}")
                return None
            
            logger.info(f"Downloading file: {file_name}")
            
            self.rate_limiter.sleep(0)
            response = self.make_api_request(download_url)
            
            if response.status_code == 200:
                # Create safe filename
                safe_filename = "".join(c for c in file_name if c.isalnum() or c in ('.', '-', '_')).strip()
                file_path = self.output_dir / "files" / f"{file_id}_{safe_filename}"
                
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                
                logger.info(f"Downloaded: {file_path}")
                return str(file_path)
            else:
                logger.error(f"Failed to download file {file_name}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            return None
    
    def extract_channel_messages(self, channel_id: str, channel_name: str, channel_info: Dict = None, 
                               days: int = 30, download_files: bool = True, extractor_user: str = "me", debug: bool = False) -> Dict[str, Any]:
        """Extract messages from a specific channel using a single user"""
        
        # Calculate date range
        to_date = datetime.now().isoformat() + "Z"
        from_date = (datetime.now() - timedelta(days=days)).isoformat() + "Z"
        
        logger.info(f"Extracting messages from channel '{channel_name}' ({channel_id})")
        logger.info(f"Date range: {from_date} to {to_date}")
        
        # All channels (including "1:1" type which are small group conversations) use to_channel
        # The "1:1" type in Zoom API refers to small group conversations, not actual 1:1 DMs
        channel_type = channel_info.get("type", "group") if channel_info else "group"
        
        logger.info(f"Extracting messages using to_channel parameter (type: {channel_type})")
        
        # Debug: Show more details about the channel and extraction parameters
        if debug:
            logger.debug(f"Channel ID: {channel_id}")
            logger.debug(f"Channel Name: {channel_name}")
            logger.debug(f"Channel Type: {channel_type}")
            logger.debug(f"Extractor User: {extractor_user}")
            logger.debug(f"Download Files: {download_files}")
            logger.debug(f"Days to look back: {days}")
            if channel_info:
                logger.debug(f"Full channel info: {json.dumps(channel_info, indent=2)}")
        
        # Try different approaches based on channel type
        messages = []
        
        # For all channels, use to_channel parameter
        logger.info(f"Attempting to extract messages using to_channel parameter...")
        messages = self.get_messages(
            user_id=extractor_user,
            to_channel=channel_id,
            from_date=from_date,
            to_date=to_date,
            include_files=download_files
        )
        
        # If no messages found and this is a group chat (type 4), try alternative approaches
        if not messages and channel_type == 4:
            logger.info(f"No messages found with to_channel. Channel type 4 detected - trying alternative approaches...")
            
            # Try using the JID (XMPP identifier) instead of channel ID
            if channel_info and channel_info.get("jid"):
                jid = channel_info.get("jid")
                logger.info(f"Trying with JID: {jid}")
                jid_messages = self.get_messages(
                    user_id=extractor_user,
                    to_channel=jid,
                    from_date=from_date,
                    to_date=to_date,
                    include_files=download_files
                )
                if jid_messages:
                    logger.info(f"Found {len(jid_messages)} messages using JID approach")
                    messages = jid_messages
                else:
                    logger.info(f"JID approach also returned no messages")
            
            # Try without date filters (some channels might not support date filtering)
            if not messages:
                logger.info(f"Trying without date filters...")
                no_date_messages = self.get_messages(
                    user_id=extractor_user,
                    to_channel=channel_id,
                    include_files=download_files
                )
                if no_date_messages:
                    logger.info(f"Found {len(no_date_messages)} messages without date filters")
                    messages = no_date_messages
                else:
                    logger.info(f"No date filter approach also returned no messages")
            
        # Try with each accessible user until we find one with access
        if not messages and channel_info and channel_info.get("accessible_by_users"):
            accessible_users = channel_info.get("accessible_by_users", [])
            logger.info(f"Trying each accessible user from the list: {accessible_users}")
            
            for test_user in accessible_users:
                if test_user == "me":
                    continue
                    
                logger.info(f"Trying with user context: {test_user}")
                
                try:
                    from zoom_extractor.users import UserEnumerator
                    user_enumerator = UserEnumerator(self.auth_headers)
                    user_info = user_enumerator.get_user_by_email(test_user)
                    
                    if user_info:
                        user_id = user_info.get("id")
                        logger.info(f"Found user ID {user_id} for {test_user}")
                        
                        # Test if this user has access to the channel
                        test_url = f"https://api.zoom.us/v2/chat/users/{user_id}/messages"
                        test_params = {"page_size": 1, "to_channel": channel_id}
                        
                        self.rate_limiter.sleep(0)
                        test_response = requests.get(test_url, headers=self.auth_headers, params=test_params, timeout=30)
                        
                        if test_response.status_code == 200:
                            logger.info(f"✅ User {test_user} has access to the channel!")
                            
                            # Now get all messages with this user
                            user_messages = self.get_messages(
                                user_id=user_id,
                                to_channel=channel_id,
                                from_date=from_date,
                                to_date=to_date,
                                include_files=download_files
                            )
                            
                            if user_messages:
                                logger.info(f"🎉 SUCCESS! Found {len(user_messages)} messages using user {test_user}")
                                messages = user_messages
                                break
                            else:
                                logger.info(f"User {test_user} has access but no messages found")
                        elif test_response.status_code == 404:
                            logger.info(f"❌ User {test_user} has no access to the channel (404)")
                        else:
                            logger.warning(f"⚠️  User {test_user} access test failed: {test_response.status_code}")
                    else:
                        logger.warning(f"Could not find user info for {test_user}")
                        
                except Exception as e:
                    logger.error(f"Error testing user {test_user}: {e}")
                    continue
            
            if not messages:
                logger.warning(f"None of the accessible users have access to the channel")
        
        if not messages:
            logger.warning(f"All extraction methods failed - no messages found for channel {channel_name}")
        else:
            logger.info(f"Successfully extracted {len(messages)} messages using primary method")
        
        # Download files if requested
        downloaded_files = []
        if download_files:
            for message in messages:
                files = message.get("files", [])
                for file_info in files:
                    file_path = self.download_file(file_info)
                    if file_path:
                        downloaded_files.append(file_path)
        
        # Save messages
        safe_channel_name = "".join(c for c in channel_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_channel_name = safe_channel_name.replace(' ', '_')[:30]  # Limit length
        messages_file = self.output_dir / "messages" / f"channel_{channel_id}_{safe_channel_name}_messages.json"
        with open(messages_file, 'w', encoding='utf-8') as f:
            json.dump(messages, f, indent=2, ensure_ascii=False)
        
        result = {
            "channel_id": channel_id,
            "channel_name": channel_name,
            "message_count": len(messages),
            "downloaded_files": downloaded_files,
            "date_range": f"{from_date} to {to_date}",
            "messages_file": str(messages_file),
            "extractor_user": extractor_user
        }
        
        logger.info(f"Channel '{channel_name}': {len(messages)} messages, {len(downloaded_files)} files")
        return result
    
    def extract_all_unique_channels(self, days: int = 30, download_files: bool = True,
                                  include_inactive: bool = True, extractor_user: str = "me") -> Dict[str, Any]:
        """Extract messages from all unique channels (no duplicates)"""
        
        logger.info("Starting comprehensive chat extraction for all unique channels")
        
        # Get all unique channels
        unique_channels = self.get_all_unique_channels(include_inactive)
        
        if not unique_channels:
            logger.error("No channels found")
            return {"channels": [], "total_messages": 0, "total_files": 0}
        
        # Save unique channels list
        channels_file = self.output_dir / "channels" / "all_unique_channels.json"
        with open(channels_file, 'w', encoding='utf-8') as f:
            json.dump(unique_channels, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Processing {len(unique_channels)} unique channels")
        
        # Extract messages from each unique channel
        results = []
        total_messages = 0
        total_files = 0
        
        for i, channel in enumerate(tqdm(unique_channels, desc="Processing channels"), 1):
            channel_id = channel.get("id")
            channel_name = channel.get("name", "Unknown")
            accessible_users = channel.get("accessible_by_users", [])
            
            channel_type = channel.get("type", "unknown")
            logger.info(f"[{i}/{len(unique_channels)}] Processing channel: {channel_name}")
            logger.info(f"  Type: {channel_type}, Accessible by {len(accessible_users)} users")
            
            try:
                result = self.extract_channel_messages(
                    channel_id=channel_id,
                    channel_name=channel_name,
                    channel_info=channel,
                    days=days,
                    download_files=download_files,
                    extractor_user=extractor_user
                )
                
                result["accessible_by_users"] = accessible_users
                results.append(result)
                total_messages += result.get("message_count", 0)
                total_files += len(result.get("downloaded_files", []))
                
            except Exception as e:
                logger.error(f"Error processing channel {channel_name}: {e}")
                continue
        
        # Create overall summary
        summary = {
            "extraction_date": datetime.now().isoformat(),
            "total_unique_channels": len(unique_channels),
            "processed_channels": len(results),
            "total_messages": total_messages,
            "total_files": total_files,
            "date_range_days": days,
            "include_inactive_users": include_inactive,
            "download_files": download_files,
            "extractor_user": extractor_user,
            "channels_file": str(channels_file),
            "results": results
        }
        
        # Save summary
        summary_file = self.output_dir / "_metadata" / "unique_channels_extraction_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Unique channels extraction complete!")
        logger.info(f"Processed {len(results)}/{len(unique_channels)} channels")
        logger.info(f"Total messages: {total_messages}")
        logger.info(f"Total files: {total_files}")
        
        return summary
    
    def extract_single_channel(self, channel_id: str, days: int = 30, download_files: bool = True,
                              extractor_user: str = "me", debug: bool = False) -> Dict[str, Any]:
        """Extract messages from a single channel by ID"""
        
        logger.info(f"Extracting messages from single channel: {channel_id}")
        
        # Try to get channel info from the channels list if it exists
        channel_info = None
        channel_name = "Unknown"
        
        try:
            # Check if we have the channels file from a previous run
            channels_file = self.output_dir / "channels" / "all_unique_channels.json"
            if channels_file.exists():
                with open(channels_file, 'r', encoding='utf-8') as f:
                    all_channels = json.load(f)
                
                # Find the channel in the list
                for channel in all_channels:
                    if channel.get("id") == channel_id:
                        channel_info = channel
                        channel_name = channel.get("name", "Unknown")
                        break
            
            logger.info(f"Found channel: {channel_name}")
            
            # Debug: Log detailed channel information
            if debug:
                logger.debug(f"Channel details: {json.dumps(channel_info, indent=2)}")
                logger.debug(f"Channel type: {channel_info.get('type', 'unknown')}")
                logger.debug(f"Channel settings: {channel_info.get('settings', {})}")
            
        except Exception as e:
            logger.warning(f"Could not load channel info: {e}")
        
        # Extract messages from the channel
        result = self.extract_channel_messages(
            channel_id=channel_id,
            channel_name=channel_name,
            channel_info=channel_info,
            days=days,
            download_files=download_files,
            extractor_user=extractor_user,
            debug=debug
        )
        
        # Save single channel result
        result["extraction_type"] = "single_channel"
        result["requested_channel_id"] = channel_id
        
        summary_file = self.output_dir / "_metadata" / f"single_channel_{channel_id}_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Single channel extraction complete!")
        logger.info(f"Channel: {channel_name}")
        logger.info(f"Messages: {result.get('message_count', 0)}")
        logger.info(f"Files: {len(result.get('downloaded_files', []))}")
        
        return result

def main():
    """Main CLI function"""
    
    @click.command()
    @click.option('--extractor-user', default='me', help='User ID to use for extracting messages (default: me). Try a specific user ID if "me" fails.')
    @click.option('--days', default=30, help='Number of days to look back (default: 30)')
    @click.option('--output-dir', default='./chat_extraction', help='Output directory')
    @click.option('--no-files', is_flag=True, help='Skip downloading file attachments')
    @click.option('--no-inactive', is_flag=True, help='Skip inactive users when collecting channels')
    @click.option('--list-channels', is_flag=True, help='Just list unique channels and exit')
    @click.option('--channel-id', help='Extract messages from a specific channel ID only')
    @click.option('--debug', is_flag=True, help='Enable debug logging for detailed API information')
    def cli(extractor_user, days, output_dir, no_files, no_inactive, list_channels, channel_id, debug):
        """Improved Simple Zoom Chat Extractor - No Duplicate Channels"""
        
        # Set debug logging level if requested
        if debug:
            logging.getLogger().setLevel(logging.DEBUG)
            logger.info("Debug logging enabled - detailed API information will be shown")
        
        # Initialize authentication
        try:
            auth = get_auth_from_env()
            auth_headers = auth.get_auth_headers()
            logger.info("Authentication successful")
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return 1
        
        # Initialize extractor
        extractor = ImprovedChatExtractor(auth_headers, output_dir, auth)
        
        try:
            download_files = not no_files
            include_inactive = not no_inactive
            
            # List channels mode
            if list_channels:
                channels = extractor.get_all_unique_channels(include_inactive)
                logger.info(f"Found {len(channels)} unique channels:")
                for channel in channels:
                    channel_id = channel.get("id")
                    channel_name = channel.get("name", "Unknown")
                    accessible_users = channel.get("accessible_by_users", [])
                    logger.info(f"  {channel_id}: {channel_name} (accessible by {len(accessible_users)} users)")
                return 0
            
            # Single channel extraction mode
            if channel_id:
                result = extractor.extract_single_channel(
                    channel_id=channel_id,
                    days=days,
                    download_files=download_files,
                    extractor_user=extractor_user,
                    debug=debug
                )
            else:
                # Extract from all unique channels
                result = extractor.extract_all_unique_channels(
                    days=days,
                    download_files=download_files,
                    include_inactive=include_inactive,
                    extractor_user=extractor_user
                )
            
            logger.info("Extraction completed successfully!")
            return 0
            
        except KeyboardInterrupt:
            logger.info("Extraction interrupted by user")
            return 1
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return 1
    
    return cli()

if __name__ == "__main__":
    sys.exit(main())
