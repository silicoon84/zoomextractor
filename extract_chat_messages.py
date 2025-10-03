#!/usr/bin/env python3
"""
Zoom Chat Messages Extraction Script

This script extracts chat messages from Zoom using the official Team Chat API.
It extracts one-on-one messages, group messages, channel messages, and space messages.
Meeting chat messages are handled separately via the recordings extraction.
"""

import os
import sys
import json
import logging
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add the zoom_extractor module to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from zoom_extractor.auth import get_auth_from_env
from zoom_extractor.users import UserEnumerator
from zoom_extractor.rate_limiter import RateLimiter
from zoom_extractor.structure import DirectoryStructure
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ChatMessageExtractor:
    """Extract chat messages from Zoom using the official Team Chat API"""
    
    def __init__(self, auth_headers: Dict[str, str], output_dir: str):
        self.auth_headers = auth_headers
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.rate_limiter = RateLimiter()
        self.structure = DirectoryStructure(self.output_dir)
        
        # Create subdirectories
        (self.output_dir / "one_on_one").mkdir(exist_ok=True)
        (self.output_dir / "group_chats").mkdir(exist_ok=True)
        (self.output_dir / "channels").mkdir(exist_ok=True)
        (self.output_dir / "spaces").mkdir(exist_ok=True)
        (self.output_dir / "_metadata").mkdir(exist_ok=True)
        
        logger.info(f"Chat messages will be saved to: {self.output_dir}")
    
    def extract_user_chat_messages(self, user_id: str, user_email: str, 
                                 from_date: str, to_date: str) -> Dict[str, Any]:
        """Extract chat messages for a specific user"""
        logger.info(f"[CHAT] Extracting chat messages for {user_email} ({user_id})")
        
        user_results = {
            "user_id": user_id,
            "user_email": user_email,
            "one_on_one_messages": [],
            "group_messages": [],
            "channel_messages": [],
            "space_messages": [],
            "meeting_chat_messages": [],
            "total_messages": 0,
            "extraction_date": datetime.now().isoformat(),
            "limitations": [],
            "api_notes": []
        }
        
        try:
            # Note: Zoom Chat API endpoints for direct message extraction are limited
            # Most chat functionality requires specific scopes that may not be available
            # Meeting chat messages are handled elsewhere in the recordings extraction
            
            logger.info("[INFO] Extracting chat messages (meeting chats handled elsewhere)")
            user_results["api_notes"].append("Meeting chat messages are extracted separately via recordings")
            
            # Skip meeting chat messages - handled elsewhere
            user_results["meeting_chat_messages"] = []
            
            # Try one-on-one messages using correct API endpoint
            try:
                one_on_one_messages = self._extract_one_on_one_messages(user_id, from_date, to_date)
                user_results["one_on_one_messages"] = one_on_one_messages
                logger.info(f"[OK] Extracted {len(one_on_one_messages)} one-on-one messages")
            except Exception as e:
                logger.warning(f"[WARN] One-on-one message extraction failed: {e}")
                user_results["limitations"].append(f"One-on-one messages: {str(e)}")
                user_results["one_on_one_messages"] = []
            
            # Try group messages using IM groups endpoint
            try:
                group_messages = self._extract_group_messages(user_id, from_date, to_date)
                user_results["group_messages"] = group_messages
                logger.info(f"[OK] Extracted {len(group_messages)} group messages")
            except Exception as e:
                logger.warning(f"[WARN] Group message extraction failed: {e}")
                user_results["limitations"].append(f"Group messages: {str(e)}")
                user_results["group_messages"] = []
            
            # Try channel messages using correct API endpoint
            try:
                channel_messages = self._extract_channel_messages(user_id, from_date, to_date)
                user_results["channel_messages"] = channel_messages
                logger.info(f"[OK] Extracted {len(channel_messages)} channel messages")
            except Exception as e:
                logger.warning(f"[WARN] Channel message extraction failed: {e}")
                user_results["limitations"].append(f"Channel messages: {str(e)}")
                user_results["channel_messages"] = []
            
            # Try space messages using chat spaces endpoint
            try:
                space_messages = self._extract_space_messages(user_id, from_date, to_date)
                user_results["space_messages"] = space_messages
                logger.info(f"[OK] Extracted {len(space_messages)} space messages")
            except Exception as e:
                logger.warning(f"[WARN] Space message extraction failed: {e}")
                user_results["limitations"].append(f"Space messages: {str(e)}")
                user_results["space_messages"] = []
            
            # Calculate total
            user_results["total_messages"] = (
                len(user_results["one_on_one_messages"]) +
                len(user_results["group_messages"]) + 
                len(user_results["channel_messages"]) +
                len(user_results["space_messages"])
            )
            
            logger.info(f"[OK] Extracted {user_results['total_messages']} chat messages for {user_email}")
            
        except Exception as e:
            logger.error(f"[ERROR] Error extracting chat messages for {user_email}: {e}")
            user_results["error"] = str(e)
        
        return user_results
    
    def _extract_one_on_one_messages(self, user_id: str, from_date: str, to_date: str) -> List[Dict]:
        """Extract one-on-one chat messages using the working method"""
        messages = []
        
        try:
            logger.info(f"[CHAT] Extracting one-on-one messages for user {user_id}")
            
            # First, get user's contacts
            contacts = self._get_user_contacts_official(user_id)
            
            if not contacts:
                logger.warning(f"[WARN] No contacts found for user {user_id}")
                return messages
            
            logger.info(f"[INFO] Found {len(contacts)} contacts, checking for messages...")
            
            # Extract messages with each contact using the working method
            for contact in contacts:
                contact_id = contact.get("identifier") or contact.get("id") or contact.get("email")
                if not contact_id:
                    continue
                    
                logger.debug(f"[DEBUG] Checking messages with contact: {contact_id}")
                
                url = f"https://api.zoom.us/v2/chat/users/{user_id}/messages"
                params = {
                    "page_size": "50",
                    "to_contact": contact_id,
                    "from": from_date,
                    "to": to_date,
                    "download_file_formats": "audio/mp4",
                    "include_deleted_and_edited_message": "true"
                }
                
                next_page_token = None
                contact_messages = []
                
                while True:
                    if next_page_token:
                        params["next_page_token"] = next_page_token
                    
                    self.rate_limiter.sleep(0)
                    response = requests.get(url, headers=self.auth_headers, params=params)
                    
                    if response.status_code == 200:
                        data = response.json()
                        page_messages = data.get("messages", [])
                        contact_messages.extend(page_messages)
                        
                        next_page_token = data.get("next_page_token")
                        if not next_page_token:
                            break
                            
                    elif response.status_code == 404:
                        logger.debug(f"[DEBUG] No messages found with contact {contact_id}")
                        break
                    elif response.status_code == 400 and "No permission to access" in response.text:
                        logger.warning(f"[WARN] No permission to access contact {contact_id}")
                        break
                    else:
                        logger.warning(f"[WARN] Failed to fetch messages with contact {contact_id}: {response.status_code} - {response.text}")
                        break
                
                if contact_messages:
                    logger.info(f"[CHAT] Found {len(contact_messages)} messages with contact: {contact_id}")
                    messages.extend(contact_messages)
                    
        except Exception as e:
            logger.error(f"[ERROR] Error extracting one-on-one messages: {e}")
        
        logger.info(f"[OK] Extracted {len(messages)} one-on-one messages")
        return messages
    
    def _get_user_contacts_official(self, user_id: str) -> List[Dict]:
        """Get user's contacts using the official GET /chat/users/me/contacts endpoint"""
        contacts = []
        
        try:
            logger.info(f"[INFO] Getting contacts for user {user_id}")
            
            # Use the official contacts endpoint
            url = "https://api.zoom.us/v2/chat/users/me/contacts"
            params = {
                "page_size": 50
            }
            
            next_page_token = None
            
            while True:
                if next_page_token:
                    params["next_page_token"] = next_page_token
                
                self.rate_limiter.sleep(0)
                response = requests.get(url, headers=self.auth_headers, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    page_contacts = data.get("contacts", [])
                    contacts.extend(page_contacts)
                    
                    logger.info(f"[INFO] Retrieved {len(page_contacts)} contacts from API")
                    
                    next_page_token = data.get("next_page_token")
                    if not next_page_token:
                        break
                        
                elif response.status_code == 404:
                    logger.info(f"[INFO] No contacts found for user {user_id}")
                    break
                else:
                    logger.error(f"[ERROR] Failed to fetch contacts: {response.status_code} - {response.text}")
                    break
                    
        except Exception as e:
            logger.error(f"[ERROR] Error getting contacts: {e}")
        
        logger.info(f"[OK] Found {len(contacts)} total contacts")
        return contacts
    
    def _extract_group_messages(self, user_id: str, from_date: str, to_date: str) -> List[Dict]:
        """Extract group chat messages using GET /im/groups"""
        messages = []
        
        try:
            logger.info(f"[GROUP] Extracting group messages for user {user_id}")
            
            # Get IM groups
            groups_url = f"https://api.zoom.us/v2/im/groups"
            self.rate_limiter.sleep(0)
            groups_response = requests.get(groups_url, headers=self.auth_headers)
            
            if groups_response.status_code == 200:
                groups_data = groups_response.json()
                groups = groups_data.get("groups", [])
                
                logger.info(f"[INFO] Found {len(groups)} IM groups")
                
                for group in groups:
                    group_id = group.get("id")
                    group_name = group.get("name", "Unknown Group")
                    
                    if group_id:
                        logger.info(f"[DEBUG] Checking group: {group_name}")
                        group_messages = self._extract_group_messages_by_id(
                            group_id, from_date, to_date
                        )
                        if group_messages:
                            logger.info(f"[CHAT] Found {len(group_messages)} messages in group: {group_name}")
                        messages.extend(group_messages)
                        
            elif groups_response.status_code == 404:
                logger.info(f"[INFO] No IM groups found")
            else:
                logger.error(f"[ERROR] Failed to fetch IM groups: {groups_response.status_code} - {groups_response.text}")
                
        except Exception as e:
            logger.error(f"[ERROR] Error extracting group messages: {e}")
        
        logger.info(f"[OK] Extracted {len(messages)} group messages")
        return messages
    
    def _extract_group_messages_by_id(self, group_id: str, from_date: str, to_date: str) -> List[Dict]:
        """Extract messages from a specific group chat using the working method"""
        messages = []
        
        try:
            logger.info(f"[GROUP] Extracting messages from group {group_id}")
            
            # Use the working method - try with group_id as channel
            url = f"https://api.zoom.us/v2/chat/users/me/messages"
            params = {
                "page_size": "50",
                "to_channel": group_id,
                "from": from_date,
                "to": to_date,
                "download_file_formats": "audio/mp4",
                "include_deleted_and_edited_message": "true"
            }
            
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
                    
                    next_page_token = data.get("next_page_token")
                    if not next_page_token:
                        break
                        
                elif response.status_code == 404:
                    logger.debug(f"[DEBUG] No messages found for group {group_id}")
                    break
                elif response.status_code == 400 and "No permission to access" in response.text:
                    logger.warning(f"[WARN] No permission to access group {group_id}")
                    break
                else:
                    logger.warning(f"[WARN] Failed to fetch messages for group {group_id}: {response.status_code} - {response.text}")
                    break
            
            if messages:
                logger.info(f"[GROUP] Found {len(messages)} messages in group {group_id}")
            
        except Exception as e:
            logger.error(f"[ERROR] Error extracting group messages for group {group_id}: {e}")
        
        return messages
    
    def _extract_channel_messages(self, user_id: str, from_date: str, to_date: str) -> List[Dict]:
        """Extract channel messages using GET /chat/users/{userId}/channels"""
        messages = []
        
        try:
            logger.info(f"[CHANNEL] Extracting channel messages for user {user_id}")
            
            # Get user's channels
            channels_url = f"https://api.zoom.us/v2/chat/users/{user_id}/channels"
            self.rate_limiter.sleep(0)
            channels_response = requests.get(channels_url, headers=self.auth_headers)
            
            if channels_response.status_code == 200:
                channels_data = channels_response.json()
                channels = channels_data.get("channels", [])
                
                logger.info(f"[INFO] Found {len(channels)} channels")
                
                for channel in channels:
                    channel_id = channel.get("id")
                    channel_name = channel.get("name", "Unknown Channel")
                    
                    if channel_id:
                        logger.info(f"[DEBUG] Checking channel: {channel_name}")
                        channel_messages = self._extract_channel_messages_by_id(
                            channel_id, from_date, to_date
                        )
                        if channel_messages:
                            logger.info(f"[CHAT] Found {len(channel_messages)} messages in channel: {channel_name}")
                        messages.extend(channel_messages)
                        
            elif channels_response.status_code == 404:
                logger.info(f"[INFO] No channels found for user {user_id}")
            else:
                logger.error(f"[ERROR] Failed to fetch channels: {channels_response.status_code} - {channels_response.text}")
                
        except Exception as e:
            logger.error(f"[ERROR] Error extracting channel messages: {e}")
        
        logger.info(f"[OK] Extracted {len(messages)} channel messages")
        return messages
    
    def _extract_channel_messages_by_id(self, channel_id: str, from_date: str, to_date: str) -> List[Dict]:
        """Extract messages from a specific channel using the working method"""
        messages = []
        
        try:
            logger.info(f"[CHANNEL] Extracting messages from channel {channel_id}")
            
            # Use the working method from our improved script
            url = f"https://api.zoom.us/v2/chat/users/me/messages"
            params = {
                "page_size": "50",
                "to_channel": channel_id,
                "from": from_date,
                "to": to_date,
                "download_file_formats": "audio/mp4",
                "include_deleted_and_edited_message": "true"
            }
            
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
                    
                    next_page_token = data.get("next_page_token")
                    if not next_page_token:
                        break
                        
                elif response.status_code == 404:
                    logger.debug(f"[DEBUG] No messages found for channel {channel_id}")
                    break
                elif response.status_code == 400 and "No permission to access" in response.text:
                    logger.warning(f"[WARN] No permission to access channel {channel_id}")
                    break
                else:
                    logger.warning(f"[WARN] Failed to fetch messages for channel {channel_id}: {response.status_code} - {response.text}")
                    break
            
            if messages:
                logger.info(f"[CHANNEL] Found {len(messages)} messages in channel {channel_id}")
            
        except Exception as e:
            logger.error(f"[ERROR] Error extracting channel messages for channel {channel_id}: {e}")
        
        return messages
    
    def _extract_space_messages(self, user_id: str, from_date: str, to_date: str) -> List[Dict]:
        """Extract messages from chat spaces using GET /chat/spaces"""
        messages = []
        
        try:
            logger.info(f"[SPACE] Extracting space messages for user {user_id}")
            
            # Get all spaces
            spaces_url = f"https://api.zoom.us/v2/chat/spaces"
            self.rate_limiter.sleep(0)
            spaces_response = requests.get(spaces_url, headers=self.auth_headers)
            
            if spaces_response.status_code == 200:
                spaces_data = spaces_response.json()
                spaces = spaces_data.get("spaces", [])
                
                logger.info(f"[INFO] Found {len(spaces)} chat spaces")
                
                for space in spaces:
                    space_id = space.get("id")
                    space_name = space.get("name", "Unknown Space")
                    
                    if space_id:
                        logger.info(f"[DEBUG] Checking space: {space_name}")
                        # Get channels in this space
                        space_channels = self._get_space_channels(space_id)
                        
                        for channel in space_channels:
                            channel_id = channel.get("id")
                            channel_name = channel.get("name", "Unknown Channel")
                            
                            if channel_id:
                                logger.info(f"  [CHANNEL] Checking space channel: {channel_name}")
                                channel_messages = self._extract_channel_messages_by_id(
                                    channel_id, from_date, to_date
                                )
                                if channel_messages:
                                    logger.info(f"  [CHAT] Found {len(channel_messages)} messages in space channel: {channel_name}")
                                messages.extend(channel_messages)
                        
            elif spaces_response.status_code == 404:
                logger.info(f"[INFO] No chat spaces found")
            else:
                logger.error(f"[ERROR] Failed to fetch chat spaces: {spaces_response.status_code} - {spaces_response.text}")
                
        except Exception as e:
            logger.error(f"[ERROR] Error extracting space messages: {e}")
        
        logger.info(f"[OK] Extracted {len(messages)} space messages")
        return messages
    
    def _get_space_channels(self, space_id: str) -> List[Dict]:
        """Get channels within a space using GET /chat/spaces/{spaceId}/channels"""
        try:
            url = f"https://api.zoom.us/v2/chat/spaces/{space_id}/channels"
            self.rate_limiter.sleep(0)
            response = requests.get(url, headers=self.auth_headers)
            
            if response.status_code == 200:
                data = response.json()
                return data.get("channels", [])
            else:
                logger.debug(f"[DEBUG] Failed to get channels for space {space_id}: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"[ERROR] Error getting space channels: {e}")
            return []
    
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
            
            # Save space messages
            if chat_data.get("space_messages"):
                space_file = self.output_dir / "spaces" / f"{safe_email}_spaces.json"
                with open(space_file, 'w', encoding='utf-8') as f:
                    json.dump(chat_data["space_messages"], f, indent=2, ensure_ascii=False)
            
            # Skip saving meeting chat messages - handled elsewhere
            
            # Save summary
            summary_file = self.output_dir / "_metadata" / f"{safe_email}_chat_summary.json"
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(chat_data, f, indent=2, ensure_ascii=False)
                
            logger.info(f"[OK] Saved chat data for {user_email}")
            
        except Exception as e:
            logger.error(f"[ERROR] Error saving chat data for {user_email}: {e}")

def extract_all_chat_messages(
    output_dir: str = "./zoom_chat_messages",
    user_filter: Optional[List[str]] = None,
    from_date: str = "2020-01-01",
    to_date: Optional[str] = None,
    include_inactive_users: bool = True,
    dry_run: bool = False
):
    """Main function to extract all chat messages"""
    
    logger.info("[START] Starting Zoom Chat Messages Extraction")
    logger.info(f"[DIR] Output Directory: {output_dir}")
    logger.info(f"[DATE] Date Range: {from_date} to {to_date or datetime.now().strftime('%Y-%m-%d')}")
    
    if dry_run:
        logger.info("[DRY] DRY RUN MODE - No data will be extracted")
    
    # Initialize authentication
    try:
        auth = get_auth_from_env()
        auth_headers = auth.get_auth_headers()
        logger.info("[OK] Authentication successful")
    except Exception as e:
        logger.error(f"[ERROR] Authentication failed: {e}")
        return False
    
    # Initialize extractor
    extractor = ChatMessageExtractor(auth_headers, output_dir)
    
    # Initialize user enumerator
    user_enumerator = UserEnumerator(auth_headers)
    
    # Get users to process
    all_users = []
    
    if user_filter:
        logger.info(f"[USERS] Processing filtered users: {user_filter}")
        
        # Get active users
        print("[INFO] Getting active users...")
        try:
            active_users = list(user_enumerator.list_all_users(user_filter, user_type="active"))
            all_users.extend(active_users)
            print(f"   Found {len(active_users)} active users")
        except Exception as e:
            print(f"   [WARN] Could not get active users: {e}")
        
        # Get inactive users if requested
        if include_inactive_users:
            print("[INFO] Getting inactive users...")
            try:
                inactive_users = list(user_enumerator.list_all_users(user_filter, user_type="inactive"))
                all_users.extend(inactive_users)
                print(f"   Found {len(inactive_users)} inactive users")
            except Exception as e:
                print(f"   [WARN] Could not get inactive users: {e}")
        
        # Get pending users if requested
        print("[INFO] Getting pending users...")
        try:
            pending_users = list(user_enumerator.list_all_users(user_filter, user_type="pending"))
            all_users.extend(pending_users)
            print(f"   Found {len(pending_users)} pending users")
        except Exception as e:
            print(f"   [WARN] Could not get pending users: {e}")
            
    else:
        logger.info("[USERS] Processing all users")
        
        # Get active users
        print("[INFO] Getting active users...")
        try:
            active_users = list(user_enumerator.list_all_users(user_type="active"))
            all_users.extend(active_users)
            print(f"   Found {len(active_users)} active users")
        except Exception as e:
            print(f"   [WARN] Could not get active users: {e}")
        
        # Get inactive users if requested
        if include_inactive_users:
            print("[INFO] Getting inactive users...")
            try:
                inactive_users = list(user_enumerator.list_all_users(user_type="inactive"))
                all_users.extend(inactive_users)
                print(f"   Found {len(inactive_users)} inactive users")
            except Exception as e:
                print(f"   [WARN] Could not get inactive users: {e}")
        
        # Get pending users if requested
        print("[INFO] Getting pending users...")
        try:
            pending_users = list(user_enumerator.list_all_users(user_type="pending"))
            all_users.extend(pending_users)
            print(f"   Found {len(pending_users)} pending users")
        except Exception as e:
            print(f"   [WARN] Could not get pending users: {e}")
    
    logger.info(f"[TARGET] Found {len(all_users)} users to process")
    
    if dry_run:
        logger.info("[DRY] DRY RUN: Would extract chat messages for:")
        for i, user in enumerate(all_users[:10], 1):  # Show first 10
            logger.info(f"  {i}. {user.get('email')} ({user.get('id')})")
        return True
    
    # Process users
    processed_users = 0
    total_messages = 0
    
    for i, user in enumerate(all_users, 1):
        user_email = user.get("email")
        user_id = user.get("id")
        
        if not user_email or not user_id:
            logger.warning(f"[WARN] Skipping user {i} - missing email or ID")
            continue
        
        logger.info(f"[USER] [{i}/{len(all_users)}] Processing {user_email}")
        
        try:
            # Extract chat messages
            chat_data = extractor.extract_user_chat_messages(
                user_id, user_email, from_date, to_date or datetime.now().strftime('%Y-%m-%d')
            )
            
            # Meeting chat messages are handled elsewhere - skip
            
            # Save data
            extractor.save_user_chat_data(user_email, chat_data)
            
            total_messages += chat_data.get("total_messages", 0)
            processed_users += 1
            
        except Exception as e:
            logger.error(f"[ERROR] Error processing user {user_email}: {e}")
            continue
    
    # Save extraction summary
    summary = {
        "extraction_date": datetime.now().isoformat(),
        "total_users": len(all_users),
        "processed_users": processed_users,
        "total_messages": total_messages,
        "output_directory": str(extractor.output_dir),
        "date_range": f"{from_date} to {to_date or datetime.now().strftime('%Y-%m-%d')}"
    }
    
    summary_file = extractor.output_dir / "_metadata" / "extraction_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    logger.info("[COMPLETE] Chat Messages Extraction Complete!")
    logger.info(f"[SUMMARY] Summary:")
    logger.info(f"  [USERS] Users processed: {processed_users}/{len(all_users)}")
    logger.info(f"  [CHAT] Total messages: {total_messages}")
    logger.info(f"  [DIR] Output directory: {extractor.output_dir}")
    
    return True

if __name__ == "__main__":
    import click
    
    @click.command()
    @click.option('--user-filter', multiple=True, help='Email addresses of users to extract chat messages for')
    @click.option('--all-users', is_flag=True, help='Extract chat messages for all users')
    @click.option('--from-date', default='2020-01-01', help='Start date for extraction (YYYY-MM-DD)')
    @click.option('--to-date', help='End date for extraction (YYYY-MM-DD)')
    @click.option('--output-dir', default='./zoom_chat_messages', help='Output directory for chat messages')
    @click.option('--include-inactive', is_flag=True, default=True, help='Include inactive users')
    @click.option('--dry-run', is_flag=True, help='Show what would be extracted without actually extracting')
    def main(user_filter, all_users, from_date, to_date, output_dir, include_inactive, dry_run):
        """Extract Zoom chat messages using the official Team Chat API"""
        
        # Validate arguments
        if not user_filter and not all_users:
            logger.error("[ERROR] Please specify either --user-filter or --all-users")
            return 1
        
        try:
            success = extract_all_chat_messages(
                output_dir=output_dir,
                user_filter=list(user_filter) if user_filter else None,
                from_date=from_date,
                to_date=to_date,
                include_inactive_users=include_inactive,
                dry_run=dry_run
            )
            
            return 0 if success else 1
            
        except KeyboardInterrupt:
            logger.info("[STOP] Extraction interrupted by user")
            return 1
        except Exception as e:
            logger.error(f"[ERROR] Unexpected error: {e}")
            return 1
    
    sys.exit(main())
