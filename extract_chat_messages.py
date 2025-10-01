#!/usr/bin/env python3
"""
Zoom Chat Messages Extractor

This script extracts all types of chat messages from Zoom:
- One-on-one chats
- Group chats  
- Chat channels
- In-meeting chat messages (from recordings)

Usage:
    python extract_chat_messages.py --help
    python extract_chat_messages.py --user-filter user@example.com --from-date 2020-01-01
    python extract_chat_messages.py --all-users --from-date 2020-01-01 --include-meeting-chats
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import requests
from dateutil.parser import parse as parse_date
from tqdm import tqdm
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import our existing modules
from zoom_extractor.auth import get_auth_from_env
from zoom_extractor.users import UserEnumerator
from zoom_extractor.dates import DateWindowGenerator
from zoom_extractor.state import ExtractionState
from zoom_extractor.structure import DirectoryStructure
from zoom_extractor.rate_limiter import RateLimiter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ChatMessageExtractor:
    """Extract chat messages from Zoom API"""
    
    def __init__(self, auth_headers: Dict[str, str], output_dir: str = "./zoom_chat_messages"):
        self.auth_headers = auth_headers
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.rate_limiter = RateLimiter()
        self.structure = DirectoryStructure(self.output_dir)
        
        # Create subdirectories
        (self.output_dir / "one_on_one").mkdir(exist_ok=True)
        (self.output_dir / "group_chats").mkdir(exist_ok=True)
        (self.output_dir / "channels").mkdir(exist_ok=True)
        (self.output_dir / "meeting_chats").mkdir(exist_ok=True)
        (self.output_dir / "_metadata").mkdir(exist_ok=True)
        
        logger.info(f"Chat messages will be saved to: {self.output_dir}")
    
    def extract_user_chat_messages(self, user_id: str, user_email: str, 
                                 from_date: str, to_date: str) -> Dict[str, Any]:
        """Extract all chat messages for a specific user"""
        logger.info(f"📱 Extracting chat messages for {user_email} ({user_id})")
        
        user_results = {
            "user_id": user_id,
            "user_email": user_email,
            "one_on_one_messages": [],
            "group_messages": [],
            "channel_messages": [],
            "meeting_chat_messages": [],
            "total_messages": 0,
            "extraction_date": datetime.now().isoformat()
        }
        
        try:
            # Extract one-on-one chat messages
            one_on_one = self._extract_one_on_one_messages(user_id, from_date, to_date)
            user_results["one_on_one_messages"] = one_on_one
            
            # Extract group chat messages
            group_messages = self._extract_group_messages(user_id, from_date, to_date)
            user_results["group_messages"] = group_messages
            
            # Extract channel messages
            channel_messages = self._extract_channel_messages(user_id, from_date, to_date)
            user_results["channel_messages"] = channel_messages
            
            # Calculate total
            user_results["total_messages"] = (
                len(one_on_one) + len(group_messages) + len(channel_messages)
            )
            
            logger.info(f"✅ Extracted {user_results['total_messages']} chat messages for {user_email}")
            
        except Exception as e:
            logger.error(f"❌ Error extracting chat messages for {user_email}: {e}")
            user_results["error"] = str(e)
        
        return user_results
    
    def _extract_one_on_one_messages(self, user_id: str, from_date: str, to_date: str) -> List[Dict]:
        """Extract one-on-one chat messages"""
        messages = []
        
        try:
            url = f"https://api.zoom.us/v2/chat/users/{user_id}/messages"
            params = {
                "from": from_date,
                "to": to_date,
                "page_size": 50,
                "include_fields": "message,date_time,sender,receiver,message_type"
            }
            
            next_page_token = None
            page_count = 0
            
            while True:
                if next_page_token:
                    params["next_page_token"] = next_page_token
                
                self.rate_limiter.wait()
                response = requests.get(url, headers=self.auth_headers, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    page_messages = data.get("messages", [])
                    
                    # Filter for one-on-one messages (not group/channel)
                    for msg in page_messages:
                        if self._is_one_on_one_message(msg):
                            messages.append(msg)
                    
                    page_count += 1
                    logger.debug(f"Fetched page {page_count} of one-on-one messages")
                    
                    next_page_token = data.get("next_page_token")
                    if not next_page_token:
                        break
                        
                elif response.status_code == 404:
                    logger.debug(f"No one-on-one messages found for user {user_id}")
                    break
                else:
                    logger.error(f"Failed to fetch one-on-one messages: {response.status_code} - {response.text}")
                    break
                    
        except Exception as e:
            logger.error(f"Error extracting one-on-one messages: {e}")
        
        return messages
    
    def _extract_group_messages(self, user_id: str, from_date: str, to_date: str) -> List[Dict]:
        """Extract group chat messages"""
        messages = []
        
        try:
            # First, get list of chat groups for the user
            groups_url = f"https://api.zoom.us/v2/chat/users/{user_id}/groups"
            self.rate_limiter.wait()
            groups_response = requests.get(groups_url, headers=self.auth_headers)
            
            if groups_response.status_code == 200:
                groups_data = groups_response.json()
                groups = groups_data.get("groups", [])
                
                for group in groups:
                    group_id = group.get("id")
                    if group_id:
                        group_messages = self._extract_group_messages_by_id(
                            group_id, from_date, to_date
                        )
                        messages.extend(group_messages)
                        
            elif groups_response.status_code == 404:
                logger.debug(f"No group chats found for user {user_id}")
            else:
                logger.error(f"Failed to fetch group chats: {groups_response.status_code}")
                
        except Exception as e:
            logger.error(f"Error extracting group messages: {e}")
        
        return messages
    
    def _extract_group_messages_by_id(self, group_id: str, from_date: str, to_date: str) -> List[Dict]:
        """Extract messages from a specific group chat"""
        messages = []
        
        try:
            url = f"https://api.zoom.us/v2/chat/groups/{group_id}/messages"
            params = {
                "from": from_date,
                "to": to_date,
                "page_size": 50
            }
            
            next_page_token = None
            
            while True:
                if next_page_token:
                    params["next_page_token"] = next_page_token
                
                self.rate_limiter.wait()
                response = requests.get(url, headers=self.auth_headers, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    page_messages = data.get("messages", [])
                    messages.extend(page_messages)
                    
                    next_page_token = data.get("next_page_token")
                    if not next_page_token:
                        break
                        
                elif response.status_code == 404:
                    break
                else:
                    logger.error(f"Failed to fetch group messages: {response.status_code}")
                    break
                    
        except Exception as e:
            logger.error(f"Error extracting group messages for group {group_id}: {e}")
        
        return messages
    
    def _extract_channel_messages(self, user_id: str, from_date: str, to_date: str) -> List[Dict]:
        """Extract channel messages"""
        messages = []
        
        try:
            # First, get list of channels for the user
            channels_url = f"https://api.zoom.us/v2/chat/users/{user_id}/channels"
            self.rate_limiter.wait()
            channels_response = requests.get(channels_url, headers=self.auth_headers)
            
            if channels_response.status_code == 200:
                channels_data = channels_response.json()
                channels = channels_data.get("channels", [])
                
                for channel in channels:
                    channel_id = channel.get("id")
                    if channel_id:
                        channel_messages = self._extract_channel_messages_by_id(
                            channel_id, from_date, to_date
                        )
                        messages.extend(channel_messages)
                        
            elif channels_response.status_code == 404:
                logger.debug(f"No channels found for user {user_id}")
            else:
                logger.error(f"Failed to fetch channels: {channels_response.status_code}")
                
        except Exception as e:
            logger.error(f"Error extracting channel messages: {e}")
        
        return messages
    
    def _extract_channel_messages_by_id(self, channel_id: str, from_date: str, to_date: str) -> List[Dict]:
        """Extract messages from a specific channel"""
        messages = []
        
        try:
            url = f"https://api.zoom.us/v2/chat/channels/{channel_id}/messages"
            params = {
                "from": from_date,
                "to": to_date,
                "page_size": 50
            }
            
            next_page_token = None
            
            while True:
                if next_page_token:
                    params["next_page_token"] = next_page_token
                
                self.rate_limiter.wait()
                response = requests.get(url, headers=self.auth_headers, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    page_messages = data.get("messages", [])
                    messages.extend(page_messages)
                    
                    next_page_token = data.get("next_page_token")
                    if not next_page_token:
                        break
                        
                elif response.status_code == 404:
                    break
                else:
                    logger.error(f"Failed to fetch channel messages: {response.status_code}")
                    break
                    
        except Exception as e:
            logger.error(f"Error extracting channel messages for channel {channel_id}: {e}")
        
        return messages
    
    def _is_one_on_one_message(self, message: Dict) -> bool:
        """Determine if a message is one-on-one (not group/channel)"""
        # Check if message has specific one-on-one indicators
        receiver = message.get("receiver", "")
        message_type = message.get("message_type", "")
        
        # One-on-one messages typically have a specific receiver and type
        return (
            message_type == "chat" and 
            receiver and 
            "@" in receiver  # Email address indicates one-on-one
        )
    
    def extract_meeting_chat_messages(self, user_id: str, user_email: str,
                                    from_date: str, to_date: str) -> List[Dict]:
        """Extract in-meeting chat messages from recordings"""
        logger.info(f"🎥 Extracting meeting chat messages for {user_email}")
        
        meeting_chats = []
        
        try:
            # Get user's recordings to find chat files
            recordings_url = f"https://api.zoom.us/v2/users/{user_id}/recordings"
            params = {
                "from": from_date,
                "to": to_date,
                "page_size": 30
            }
            
            next_page_token = None
            
            while True:
                if next_page_token:
                    params["next_page_token"] = next_page_token
                
                self.rate_limiter.wait()
                response = requests.get(recordings_url, headers=self.auth_headers, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    meetings = data.get("meetings", [])
                    
                    for meeting in meetings:
                        meeting_id = meeting.get("uuid")
                        if meeting_id:
                            # Get detailed recording info
                            recording_details = self._get_meeting_recording_details(meeting_id)
                            if recording_details:
                                chat_files = self._extract_chat_from_recording_files(
                                    recording_details, user_email
                                )
                                meeting_chats.extend(chat_files)
                    
                    next_page_token = data.get("next_page_token")
                    if not next_page_token:
                        break
                        
                elif response.status_code == 404:
                    logger.debug(f"No recordings found for user {user_id}")
                    break
                else:
                    logger.error(f"Failed to fetch recordings: {response.status_code}")
                    break
                    
        except Exception as e:
            logger.error(f"Error extracting meeting chat messages: {e}")
        
        return meeting_chats
    
    def _get_meeting_recording_details(self, meeting_uuid: str) -> Optional[Dict]:
        """Get detailed recording information for a meeting"""
        try:
            url = f"https://api.zoom.us/v2/meetings/{meeting_uuid}/recordings"
            self.rate_limiter.wait()
            response = requests.get(url, headers=self.auth_headers)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.debug(f"No recording details for meeting {meeting_uuid}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting recording details: {e}")
            return None
    
    def _extract_chat_from_recording_files(self, recording_data: Dict, user_email: str) -> List[Dict]:
        """Extract chat messages from recording files"""
        chat_messages = []
        
        try:
            files = recording_data.get("recording_files", [])
            
            for file_info in files:
                file_type = file_info.get("file_type", "").lower()
                
                if file_type == "chat" or "chat" in file_info.get("file_name", "").lower():
                    # This is a chat file - in a real implementation, you'd download and parse it
                    chat_info = {
                        "meeting_uuid": recording_data.get("uuid"),
                        "meeting_id": recording_data.get("id"),
                        "topic": recording_data.get("topic"),
                        "start_time": recording_data.get("start_time"),
                        "chat_file": file_info,
                        "extracted_by": user_email,
                        "extraction_date": datetime.now().isoformat()
                    }
                    chat_messages.append(chat_info)
                    
        except Exception as e:
            logger.error(f"Error extracting chat from recording files: {e}")
        
        return chat_messages
    
    def save_user_chat_data(self, user_email: str, chat_data: Dict):
        """Save chat data for a user to files"""
        try:
            # Sanitize email for filename
            safe_email = user_email.replace("@", "_").replace(".", "_")
            
            # Save one-on-one messages
            if chat_data.get("one_on_one_messages"):
                one_on_one_file = self.output_dir / "one_on_one" / f"{safe_email}_one_on_one.json"
                with open(one_on_one_file, 'w', encoding='utf-8') as f:
                    json.dump(chat_data["one_on_one_messages"], f, indent=2, ensure_ascii=False)
            
            # Save group messages
            if chat_data.get("group_messages"):
                group_file = self.output_dir / "group_chats" / f"{safe_email}_groups.json"
                with open(group_file, 'w', encoding='utf-8') as f:
                    json.dump(chat_data["group_messages"], f, indent=2, ensure_ascii=False)
            
            # Save channel messages
            if chat_data.get("channel_messages"):
                channel_file = self.output_dir / "channels" / f"{safe_email}_channels.json"
                with open(channel_file, 'w', encoding='utf-8') as f:
                    json.dump(chat_data["channel_messages"], f, indent=2, ensure_ascii=False)
            
            # Save meeting chat messages
            if chat_data.get("meeting_chat_messages"):
                meeting_file = self.output_dir / "meeting_chats" / f"{safe_email}_meetings.json"
                with open(meeting_file, 'w', encoding='utf-8') as f:
                    json.dump(chat_data["meeting_chat_messages"], f, indent=2, ensure_ascii=False)
            
            # Save summary
            summary_file = self.output_dir / "_metadata" / f"{safe_email}_chat_summary.json"
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(chat_data, f, indent=2, ensure_ascii=False)
                
            logger.info(f"💾 Saved chat data for {user_email}")
            
        except Exception as e:
            logger.error(f"Error saving chat data for {user_email}: {e}")

def extract_all_chat_messages(
    output_dir: str = "./zoom_chat_messages",
    user_filter: Optional[List[str]] = None,
    from_date: str = "2020-01-01",
    to_date: Optional[str] = None,
    include_inactive: bool = True,
    include_meeting_chats: bool = True,
    dry_run: bool = False
):
    """Main function to extract all chat messages"""
    
    logger.info("🚀 Starting Zoom Chat Messages Extraction")
    logger.info(f"📁 Output Directory: {output_dir}")
    logger.info(f"📅 Date Range: {from_date} to {to_date or datetime.now().strftime('%Y-%m-%d')}")
    
    if dry_run:
        logger.info("🧪 DRY RUN MODE - No data will be extracted")
    
    # Initialize authentication
    try:
        auth_headers = get_auth_from_env()
        logger.info("✅ Authentication successful")
    except Exception as e:
        logger.error(f"❌ Authentication failed: {e}")
        return False
    
    # Initialize extractor
    extractor = ChatMessageExtractor(auth_headers, output_dir)
    
    # Get users to process
    user_enumerator = UserEnumerator(auth_headers)
    
    if user_filter:
        logger.info(f"👥 Processing filtered users: {user_filter}")
        all_users = []
        for user_email in user_filter:
            # Find user by email
            users = user_enumerator.list_all_users(status="active")
            user = next((u for u in users if u.get("email") == user_email), None)
            if user:
                all_users.append(user)
            else:
                logger.warning(f"⚠️ User {user_email} not found in active users")
                
            if include_inactive:
                inactive_users = user_enumerator.list_all_users(status="inactive")
                user = next((u for u in inactive_users if u.get("email") == user_email), None)
                if user:
                    all_users.append(user)
    else:
        logger.info("👥 Processing all users")
        all_users = user_enumerator.list_all_users(status="active")
        if include_inactive:
            inactive_users = user_enumerator.list_all_users(status="inactive")
            all_users.extend(inactive_users)
    
    logger.info(f"🎯 Found {len(all_users)} users to process")
    
    if dry_run:
        logger.info("🧪 DRY RUN: Would extract chat messages for:")
        for i, user in enumerate(all_users[:10], 1):  # Show first 10
            logger.info(f"  {i}. {user.get('email')} ({user.get('id')})")
        if len(all_users) > 10:
            logger.info(f"  ... and {len(all_users) - 10} more users")
        return True
    
    # Process each user
    total_messages = 0
    processed_users = 0
    
    for i, user in enumerate(tqdm(all_users, desc="Processing users"), 1):
        user_email = user.get("email")
        user_id = user.get("id")
        
        if not user_email or not user_id:
            logger.warning(f"⚠️ Skipping user {i} - missing email or ID")
            continue
        
        logger.info(f"👤 [{i}/{len(all_users)}] Processing {user_email}")
        
        try:
            # Extract chat messages
            chat_data = extractor.extract_user_chat_messages(
                user_id, user_email, from_date, to_date or datetime.now().strftime('%Y-%m-%d')
            )
            
            # Extract meeting chat messages if requested
            if include_meeting_chats:
                meeting_chats = extractor.extract_meeting_chat_messages(
                    user_id, user_email, from_date, to_date or datetime.now().strftime('%Y-%m-%d')
                )
                chat_data["meeting_chat_messages"] = meeting_chats
                chat_data["total_messages"] += len(meeting_chats)
            
            # Save data
            extractor.save_user_chat_data(user_email, chat_data)
            
            total_messages += chat_data.get("total_messages", 0)
            processed_users += 1
            
        except Exception as e:
            logger.error(f"❌ Error processing user {user_email}: {e}")
            continue
    
    # Save extraction summary
    summary = {
        "extraction_date": datetime.now().isoformat(),
        "total_users_processed": processed_users,
        "total_users_found": len(all_users),
        "total_messages_extracted": total_messages,
        "date_range": {"from": from_date, "to": to_date or datetime.now().strftime('%Y-%m-%d')},
        "output_directory": str(extractor.output_dir)
    }
    
    summary_file = extractor.output_dir / "_metadata" / "extraction_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    logger.info("🎉 Chat Messages Extraction Complete!")
    logger.info(f"📊 Summary:")
    logger.info(f"  👥 Users processed: {processed_users}/{len(all_users)}")
    logger.info(f"  💬 Total messages: {total_messages}")
    logger.info(f"  📁 Output directory: {extractor.output_dir}")
    
    return True

def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description="Enhanced Zoom Chat Messages Extractor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python extract_chat_messages.py --help
  python extract_chat_messages.py --user-filter user@example.com --from-date 2020-01-01
  python extract_chat_messages.py --all-users --from-date 2020-01-01 --include-meeting-chats
  python extract_chat_messages.py --dry-run --from-date 2024-01-01
        """
    )
    
    parser.add_argument(
        "--output-dir",
        default="./zoom_chat_messages",
        help="Output directory for chat messages"
    )
    
    parser.add_argument(
        "--user-filter",
        nargs="*",
        help="Filter by user emails/IDs (space-separated)"
    )
    
    parser.add_argument(
        "--all-users",
        action="store_true",
        help="Extract chat messages for all users"
    )
    
    parser.add_argument(
        "--from-date",
        default="2020-01-01",
        help="Start date (YYYY-MM-DD)"
    )
    
    parser.add_argument(
        "--to-date",
        help="End date (YYYY-MM-DD, defaults to today)"
    )
    
    parser.add_argument(
        "--include-inactive",
        action="store_true",
        default=True,
        help="Include inactive users"
    )
    
    parser.add_argument(
        "--include-meeting-chats",
        action="store_true",
        default=True,
        help="Include in-meeting chat messages from recordings"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode - show what would be extracted"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.user_filter and not args.all_users:
        logger.error("❌ Please specify either --user-filter or --all-users")
        return 1
    
    try:
        success = extract_all_chat_messages(
            output_dir=args.output_dir,
            user_filter=args.user_filter,
            from_date=args.from_date,
            to_date=args.to_date,
            include_inactive=args.include_inactive,
            include_meeting_chats=args.include_meeting_chats,
            dry_run=args.dry_run
        )
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        logger.info("🛑 Extraction interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
