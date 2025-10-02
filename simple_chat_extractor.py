#!/usr/bin/env python3
"""
Simple Zoom Chat Extractor

Extracts chat messages using the official Chat API endpoints:
1. GET /v2/chat/users/{userId}/channels - List user's channels
2. GET /v2/chat/users/{userId}/messages - Get messages (DMs or channel messages)

Usage:
    python simple_chat_extractor.py --user me --days 30
    python simple_chat_extractor.py --user me --contact user@example.com --days 7
    python simple_chat_extractor.py --user me --channel channelId123 --days 30
"""

import os
import sys
import json
import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
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

class SimpleChatExtractor:
    """Simple chat extractor using official Chat API endpoints"""
    
    def __init__(self, auth_headers: Dict[str, str], output_dir: str = "./chat_extraction"):
        self.auth_headers = auth_headers
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.rate_limiter = RateLimiter()
        
        # Create subdirectories
        (self.output_dir / "channels").mkdir(exist_ok=True)
        (self.output_dir / "messages").mkdir(exist_ok=True)
        (self.output_dir / "files").mkdir(exist_ok=True)
        (self.output_dir / "_metadata").mkdir(exist_ok=True)
        
        logger.info(f"Chat extraction output: {self.output_dir}")
    
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
                response = requests.get(url, headers=self.auth_headers, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    page_channels = data.get("channels", [])
                    channels.extend(page_channels)
                    
                    logger.info(f"Retrieved {len(page_channels)} channels")
                    
                    next_page_token = data.get("next_page_token")
                    if not next_page_token:
                        break
                        
                elif response.status_code == 404:
                    logger.info(f"No channels found for user {user_id}")
                    break
                else:
                    logger.error(f"Failed to get channels: {response.status_code} - {response.text}")
                    break
                    
        except Exception as e:
            logger.error(f"Error getting channels: {e}")
        
        logger.info(f"Total channels found: {len(channels)}")
        return channels
    
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
                response = requests.get(url, headers=self.auth_headers, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    page_messages = data.get("messages", [])
                    messages.extend(page_messages)
                    
                    logger.info(f"Retrieved {len(page_messages)} messages")
                    
                    next_page_token = data.get("next_page_token")
                    if not next_page_token:
                        break
                        
                elif response.status_code == 404:
                    logger.info(f"No messages found")
                    break
                else:
                    logger.error(f"Failed to get messages: {response.status_code} - {response.text}")
                    break
                    
        except Exception as e:
            logger.error(f"Error getting messages: {e}")
        
        logger.info(f"Total messages retrieved: {len(messages)}")
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
            response = requests.get(download_url, headers=self.auth_headers)
            
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
    
    def extract_channel_messages(self, user_id: str = "me", channel_id: str = None,
                               days: int = 30, download_files: bool = True) -> Dict[str, Any]:
        """Extract messages from a specific channel"""
        
        if not channel_id:
            logger.error("Channel ID is required")
            return {}
        
        # Calculate date range
        to_date = datetime.now().isoformat() + "Z"
        from_date = (datetime.now() - timedelta(days=days)).isoformat() + "Z"
        
        logger.info(f"Extracting channel messages from {from_date} to {to_date}")
        
        # Get messages
        messages = self.get_messages(
            user_id=user_id,
            to_channel=channel_id,
            from_date=from_date,
            to_date=to_date,
            include_files=download_files
        )
        
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
        messages_file = self.output_dir / "messages" / f"channel_{channel_id}_messages.json"
        with open(messages_file, 'w', encoding='utf-8') as f:
            json.dump(messages, f, indent=2, ensure_ascii=False)
        
        result = {
            "channel_id": channel_id,
            "message_count": len(messages),
            "downloaded_files": downloaded_files,
            "date_range": f"{from_date} to {to_date}",
            "messages_file": str(messages_file)
        }
        
        logger.info(f"Channel extraction complete: {len(messages)} messages, {len(downloaded_files)} files")
        return result
    
    def extract_contact_messages(self, user_id: str = "me", contact: str = None,
                               days: int = 30, download_files: bool = True) -> Dict[str, Any]:
        """Extract messages with a specific contact"""
        
        if not contact:
            logger.error("Contact is required")
            return {}
        
        # Calculate date range
        to_date = datetime.now().isoformat() + "Z"
        from_date = (datetime.now() - timedelta(days=days)).isoformat() + "Z"
        
        logger.info(f"Extracting contact messages from {from_date} to {to_date}")
        
        # Get messages
        messages = self.get_messages(
            user_id=user_id,
            to_contact=contact,
            from_date=from_date,
            to_date=to_date,
            include_files=download_files
        )
        
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
        safe_contact = contact.replace("@", "_").replace(".", "_")
        messages_file = self.output_dir / "messages" / f"contact_{safe_contact}_messages.json"
        with open(messages_file, 'w', encoding='utf-8') as f:
            json.dump(messages, f, indent=2, ensure_ascii=False)
        
        result = {
            "contact": contact,
            "message_count": len(messages),
            "downloaded_files": downloaded_files,
            "date_range": f"{from_date} to {to_date}",
            "messages_file": str(messages_file)
        }
        
        logger.info(f"Contact extraction complete: {len(messages)} messages, {len(downloaded_files)} files")
        return result
    
    def extract_all_channels(self, user_id: str = "me", days: int = 30, 
                           download_files: bool = True) -> Dict[str, Any]:
        """Extract messages from all user's channels"""
        
        logger.info(f"Extracting messages from all channels for user: {user_id}")
        
        # Get all channels
        channels = self.get_user_channels(user_id)
        
        if not channels:
            logger.info("No channels found")
            return {"channels": [], "total_messages": 0, "total_files": 0}
        
        # Save channels list
        channels_file = self.output_dir / "channels" / f"user_{user_id}_channels.json"
        with open(channels_file, 'w', encoding='utf-8') as f:
            json.dump(channels, f, indent=2, ensure_ascii=False)
        
        # Extract messages from each channel
        results = []
        total_messages = 0
        total_files = 0
        
        for i, channel in enumerate(channels, 1):
            channel_id = channel.get("id")
            channel_name = channel.get("name", "Unknown")
            
            logger.info(f"[{i}/{len(channels)}] Processing channel: {channel_name}")
            
            try:
                result = self.extract_channel_messages(
                    user_id=user_id,
                    channel_id=channel_id,
                    days=days,
                    download_files=download_files
                )
                
                result["channel_name"] = channel_name
                results.append(result)
                total_messages += result.get("message_count", 0)
                total_files += len(result.get("downloaded_files", []))
                
            except Exception as e:
                logger.error(f"Error processing channel {channel_name}: {e}")
                continue
        
        summary = {
            "user_id": user_id,
            "total_channels": len(channels),
            "processed_channels": len(results),
            "total_messages": total_messages,
            "total_files": total_files,
            "channels_file": str(channels_file),
            "results": results
        }
        
        # Save summary
        summary_file = self.output_dir / "_metadata" / f"user_{user_id}_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        logger.info(f"All channels extraction complete: {total_messages} messages, {total_files} files")
        return summary
    
    def extract_all_users_all_channels(self, days: int = 30, download_files: bool = True,
                                     include_inactive: bool = True) -> Dict[str, Any]:
        """Extract messages from all users and their channels"""
        
        logger.info("Starting comprehensive chat extraction for all users")
        
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
        
        logger.info(f"Total users to process: {len(all_users)}")
        
        if not all_users:
            logger.error("No users found")
            return {"users": [], "total_messages": 0, "total_files": 0, "total_channels": 0}
        
        # Process each user
        user_results = []
        total_messages = 0
        total_files = 0
        total_channels = 0
        processed_users = 0
        
        # Use tqdm for progress indication
        for i, user in enumerate(tqdm(all_users, desc="Processing users"), 1):
            user_email = user.get("email")
            user_id = user.get("id")
            
            if not user_email or not user_id:
                logger.warning(f"Skipping user {i} - missing email or ID")
                continue
            
            logger.info(f"[{i}/{len(all_users)}] Processing user: {user_email} ({user_id})")
            
            try:
                # Extract all channels for this user
                user_result = self.extract_all_channels(
                    user_id=user_id,
                    days=days,
                    download_files=download_files
                )
                
                user_result["user_email"] = user_email
                user_result["user_id"] = user_id
                user_results.append(user_result)
                
                # Update totals
                total_messages += user_result.get("total_messages", 0)
                total_files += user_result.get("total_files", 0)
                total_channels += user_result.get("total_channels", 0)
                processed_users += 1
                
                logger.info(f"User {user_email}: {user_result.get('total_messages', 0)} messages, {user_result.get('total_files', 0)} files")
                
            except Exception as e:
                logger.error(f"Error processing user {user_email}: {e}")
                continue
        
        # Create overall summary
        overall_summary = {
            "extraction_date": datetime.now().isoformat(),
            "total_users_found": len(all_users),
            "processed_users": processed_users,
            "total_channels": total_channels,
            "total_messages": total_messages,
            "total_files": total_files,
            "date_range_days": days,
            "include_inactive": include_inactive,
            "download_files": download_files,
            "user_results": user_results
        }
        
        # Save overall summary
        overall_summary_file = self.output_dir / "_metadata" / "overall_extraction_summary.json"
        with open(overall_summary_file, 'w', encoding='utf-8') as f:
            json.dump(overall_summary, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Comprehensive extraction complete!")
        logger.info(f"Processed {processed_users}/{len(all_users)} users")
        logger.info(f"Total channels: {total_channels}")
        logger.info(f"Total messages: {total_messages}")
        logger.info(f"Total files: {total_files}")
        
        return overall_summary

def main():
    """Main CLI function"""
    
    @click.command()
    @click.option('--user', default='me', help='User ID (default: me)')
    @click.option('--contact', help='Contact email/user ID for direct messages')
    @click.option('--channel', help='Channel ID for channel messages')
    @click.option('--all-users', is_flag=True, help='Extract from all users and their channels')
    @click.option('--days', default=30, help='Number of days to look back (default: 30)')
    @click.option('--output-dir', default='./chat_extraction', help='Output directory')
    @click.option('--no-files', is_flag=True, help='Skip downloading file attachments')
    @click.option('--no-inactive', is_flag=True, help='Skip inactive users (only for --all-users)')
    @click.option('--list-channels', is_flag=True, help='Just list channels and exit')
    def cli(user, contact, channel, all_users, days, output_dir, no_files, no_inactive, list_channels):
        """Simple Zoom Chat Extractor"""
        
        # Initialize authentication
        try:
            auth = get_auth_from_env()
            auth_headers = auth.get_auth_headers()
            logger.info("Authentication successful")
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return 1
        
        # Initialize extractor
        extractor = SimpleChatExtractor(auth_headers, output_dir)
        
        try:
            # List channels mode
            if list_channels:
                channels = extractor.get_user_channels(user)
                logger.info(f"Found {len(channels)} channels:")
                for channel_info in channels:
                    channel_id = channel_info.get("id")
                    channel_name = channel_info.get("name", "Unknown")
                    logger.info(f"  {channel_id}: {channel_name}")
                return 0
            
            # Validate arguments
            if not contact and not channel and not all_users:
                logger.error("Must specify either --contact, --channel, or --all-users")
                return 1
            
            download_files = not no_files
            include_inactive = not no_inactive
            
            # Extract based on mode
            if all_users:
                result = extractor.extract_all_users_all_channels(
                    days=days,
                    download_files=download_files,
                    include_inactive=include_inactive
                )
            elif contact:
                result = extractor.extract_contact_messages(
                    user_id=user,
                    contact=contact,
                    days=days,
                    download_files=download_files
                )
            elif channel:
                result = extractor.extract_channel_messages(
                    user_id=user,
                    channel_id=channel,
                    days=days,
                    download_files=download_files
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
