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
        (self.output_dir / "spaces").mkdir(exist_ok=True)
        (self.output_dir / "_metadata").mkdir(exist_ok=True)
        
        logger.info(f"Chat messages will be saved to: {self.output_dir}")
    
    def extract_user_chat_messages(self, user_id: str, user_email: str, 
                                 from_date: str, to_date: str) -> Dict[str, Any]:
        """Extract chat messages for a specific user"""
        logger.info(f"📱 Extracting chat messages for {user_email} ({user_id})")
        
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
            
            logger.info("ðŸ“ Extracting chat messages (meeting chats handled elsewhere)")
            user_results["api_notes"].append("Meeting chat messages are extracted separately via recordings")
            
            # Skip meeting chat messages - handled elsewhere
            user_results["meeting_chat_messages"] = []
            
            # Try one-on-one messages using correct API endpoint
            try:
                one_on_one_messages = self._extract_one_on_one_messages(user_id, from_date, to_date)
                user_results["one_on_one_messages"] = one_on_one_messages
                logger.info(f"âœ… Extracted {len(one_on_one_messages)} one-on-one messages")
            except Exception as e:
                logger.warning(f"âš ï¸ One-on-one message extraction failed: {e}")
                user_results["limitations"].append(f"One-on-one messages: {str(e)}")
                user_results["one_on_one_messages"] = []
            
            # Try group messages using IM groups endpoint
            try:
                group_messages = self._extract_group_messages(user_id, from_date, to_date)
                user_results["group_messages"] = group_messages
                logger.info(f"âœ… Extracted {len(group_messages)} group messages")
            except Exception as e:
                logger.warning(f"âš ï¸ Group message extraction failed: {e}")
                user_results["limitations"].append(f"Group messages: {str(e)}")
                user_results["group_messages"] = []
            
            # Try channel messages using correct API endpoint
            try:
                channel_messages = self._extract_channel_messages(user_id, from_date, to_date)
                user_results["channel_messages"] = channel_messages
                logger.info(f"âœ… Extracted {len(channel_messages)} channel messages")
            except Exception as e:
                logger.warning(f"âš ï¸ Channel message extraction failed: {e}")
                user_results["limitations"].append(f"Channel messages: {str(e)}")
                user_results["channel_messages"] = []
            
            # Try space messages using chat spaces endpoint
            try:
                space_messages = self._extract_space_messages(user_id, from_date, to_date)
                user_results["space_messages"] = space_messages
                logger.info(f"âœ… Extracted {len(space_messages)} space messages")
            except Exception as e:
                logger.warning(f"âš ï¸ Space message extraction failed: {e}")
                user_results["limitations"].append(f"Space messages: {str(e)}")
                user_results["space_messages"] = []
            
            
            # Calculate total
            user_results["total_messages"] = (
                len(user_results["one_on_one_messages"]) +
                len(user_results["group_messages"]) + 
                len(user_results["channel_messages"]) +
                len(user_results["space_messages"])
            )
            
            logger.info(f"âœ… Extracted {user_results['total_messages']} chat messages for {user_email}")
            
        except Exception as e:
            logger.error(f"âŒ Error extracting chat messages for {user_email}: {e}")
            user_results["error"] = str(e)
        
        return user_results
    
    def _extract_one_on_one_messages(self, user_id: str, from_date: str, to_date: str) -> List[Dict]:
        """Extract one-on-one chat messages using GET /chat/users/{userId}/messages with contacts"""
        messages = []
        
        try:
            logger.info(f"ðŸ’¬ Extracting one-on-one messages for user {user_id}")
            
            # First, get user's contacts
            contacts = self._get_user_contacts_official(user_id)
            
            if not contacts:
                logger.warning(f"ðŸ“­ No contacts found for user {user_id}")
                return messages
            
            logger.info(f"ðŸ“‹ Found {len(contacts)} contacts, checking for messages...")
            
            # Extract messages with each contact
            for contact in contacts:
                contact_id = contact.get("identifier") or contact.get("id") or contact.get("email")
                if not contact_id:
                    continue
                    
                logger.debug(f"ðŸ” Checking messages with contact: {contact_id}")
                
                url = f"https://api.zoom.us/v2/chat/users/{user_id}/messages"
                params = {
                    "to_contact": contact_id,  # Required parameter according to API spec
                    "from": from_date,
                    "to": to_date,
                    "page_size": 50
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
                        logger.debug(f"ðŸ“­ No messages found with contact {contact_id}")
                        break
                    else:
                        logger.warning(f"âš ï¸ Failed to fetch messages with contact {contact_id}: {response.status_code}")
                        break
                
                if contact_messages:
                    logger.info(f"ðŸ’¬ Found {len(contact_messages)} messages with contact: {contact_id}")
                    messages.extend(contact_messages)
                    
        except Exception as e:
            logger.error(f"âŒ Error extracting one-on-one messages: {e}")
        
        logger.info(f"âœ… Extracted {len(messages)} one-on-one messages")
        return messages
    
    def _get_user_contacts(self, user_id: str) -> List[Dict]:
        """Get user's contacts for one-on-one messaging"""
        contacts = []
        
        try:
            # Note: The /chat/users/{userId}/contacts endpoint requires team_chat:read:list_contacts scope
            # which may not be available. As an alternative, we can try to get contacts from other sources
            # or use a different approach for one-on-one message extraction.
            
            # For now, we'll return an empty list and log the limitation
            logger.warning(f"Contact discovery not available for user {user_id} - requires additional scope")
            logger.info("One-on-one message extraction may be limited without contact discovery")
            
            # Alternative approach: Try to get all users and treat them as potential contacts
            # This is a simplified approach that may not capture all one-on-one messages
            try:
                from zoom_extractor.users import UserEnumerator
                user_enumerator = UserEnumerator(self.auth_headers)
                all_users = list(user_enumerator.list_all_users(user_type="active"))
                
                # Filter out the current user and create contact-like entries
                for user in all_users:
                    if user.get("id") != user_id:
                        contact = {
                            "id": user.get("id"),
                            "email": user.get("email"),
                            "first_name": user.get("first_name"),
                            "last_name": user.get("last_name")
                        }
                        contacts.append(contact)
                
                logger.info(f"Using {len(contacts)} active users as potential contacts for user {user_id}")
                
            except Exception as e:
                logger.warning(f"Could not get users as contacts: {e}")
                
        except Exception as e:
            logger.error(f"Error in contact discovery for user {user_id}: {e}")
        
        return contacts
    
    def _get_user_contacts_official(self, user_id: str) -> List[Dict]:
        """Get user's contacts using the official GET /chat/users/me/contacts endpoint"""
        contacts = []
        
        try:
            logger.info(f"ðŸ“‹ Getting contacts for user {user_id}")
            
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
                    
                    logger.info(f"ðŸ“¥ Retrieved {len(page_contacts)} contacts from API")
                    
                    next_page_token = data.get("next_page_token")
                    if not next_page_token:
                        break
                        
                elif response.status_code == 404:
                    logger.info(f"ðŸ“­ No contacts found for user {user_id}")
                    break
                else:
                    logger.error(f"âŒ Failed to fetch contacts: {response.status_code} - {response.text}")
                    break
                    
        except Exception as e:
            logger.error(f"âŒ Error getting contacts: {e}")
        
        logger.info(f"âœ… Found {len(contacts)} total contacts")
        return contacts
    
    def _extract_messages_with_contact(self, user_id: str, contact: Dict, from_date: str, to_date: str) -> List[Dict]:
        """Extract messages between user and a specific contact"""
        messages = []
        
        try:
            contact_id = contact.get("id") or contact.get("email")
            if not contact_id:
                return messages
            
            url = f"https://api.zoom.us/v2/chat/users/{user_id}/messages"
            params = {
                "from": from_date,
                "to": to_date,
                "to_contact": contact_id,
                "page_size": 50,
                "include_fields": "message,date_time,sender,receiver,message_type"
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
                    break
                else:
                    logger.warning(f"Failed to fetch messages with contact {contact_id}: {response.status_code}")
                    break
                    
        except Exception as e:
            logger.error(f"Error extracting messages with contact {contact_id}: {e}")
        
        return messages
    
    def _extract_group_messages(self, user_id: str, from_date: str, to_date: str) -> List[Dict]:
        """Extract group chat messages using GET /im/groups"""
        messages = []
        
        try:
            logger.info(f"ðŸ‘¥ Extracting group messages for user {user_id}")
            
            # Get IM groups
            groups_url = f"https://api.zoom.us/v2/im/groups"
            self.rate_limiter.sleep(0)
            groups_response = requests.get(groups_url, headers=self.auth_headers)
            
            if groups_response.status_code == 200:
                groups_data = groups_response.json()
                groups = groups_data.get("groups", [])
                
                logger.info(f"ðŸ“Š Found {len(groups)} IM groups")
                
                for group in groups:
                    group_id = group.get("id")
                    group_name = group.get("name", "Unknown Group")
                    
                    if group_id:
                        logger.info(f"ðŸ” Checking group: {group_name}")
                        group_messages = self._extract_group_messages_by_id(
                            group_id, from_date, to_date
                        )
                        if group_messages:
                            logger.info(f"ðŸ’¬ Found {len(group_messages)} messages in group: {group_name}")
                        messages.extend(group_messages)
                        
            elif groups_response.status_code == 404:
                logger.info(f"ðŸ“­ No IM groups found")
            else:
                logger.error(f"âŒ Failed to fetch IM groups: {groups_response.status_code} - {groups_response.text}")
                
        except Exception as e:
            logger.error(f"âŒ Error extracting group messages: {e}")
        
        logger.info(f"âœ… Extracted {len(messages)} group messages")
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
                    break
                else:
                    logger.error(f"Failed to fetch group messages: {response.status_code}")
                    break
                    
        except Exception as e:
            logger.error(f"Error extracting group messages for group {group_id}: {e}")
        
        return messages
    
    def _extract_channel_messages(self, user_id: str, from_date: str, to_date: str) -> List[Dict]:
        """Extract channel messages using GET /chat/users/{userId}/channels"""
        messages = []
        
        try:
            logger.info(f"ðŸ“¢ Extracting channel messages for user {user_id}")
            
            # Get user's channels
            channels_url = f"https://api.zoom.us/v2/chat/users/{user_id}/channels"
            self.rate_limiter.sleep(0)
            channels_response = requests.get(channels_url, headers=self.auth_headers)
            
            if channels_response.status_code == 200:
                channels_data = channels_response.json()
                channels = channels_data.get("channels", [])
                
                logger.info(f"ðŸ“Š Found {len(channels)} channels")
                
                for channel in channels:
                    channel_id = channel.get("id")
                    channel_name = channel.get("name", "Unknown Channel")
                    
                    if channel_id:
                        logger.info(f"ðŸ” Checking channel: {channel_name}")
                        channel_messages = self._extract_channel_messages_by_id(
                            channel_id, from_date, to_date
                        )
                        if channel_messages:
                            logger.info(f"ðŸ’¬ Found {len(channel_messages)} messages in channel: {channel_name}")
                        messages.extend(channel_messages)
                        
            elif channels_response.status_code == 404:
                logger.info(f"ðŸ“­ No channels found for user {user_id}")
            else:
                logger.error(f"âŒ Failed to fetch channels: {channels_response.status_code} - {channels_response.text}")
                
        except Exception as e:
            logger.error(f"âŒ Error extracting channel messages: {e}")
        
        logger.info(f"âœ… Extracted {len(messages)} channel messages")
        return messages
    
    def _extract_space_messages(self, user_id: str, from_date: str, to_date: str) -> List[Dict]:
        """Extract messages from chat spaces using GET /chat/spaces"""
        messages = []
        
        try:
            logger.info(f"ðŸŒŒ Extracting space messages for user {user_id}")
            
            # Get all spaces
            spaces_url = f"https://api.zoom.us/v2/chat/spaces"
            self.rate_limiter.sleep(0)
            spaces_response = requests.get(spaces_url, headers=self.auth_headers)
            
            if spaces_response.status_code == 200:
                spaces_data = spaces_response.json()
                spaces = spaces_data.get("spaces", [])
                
                logger.info(f"ðŸ“Š Found {len(spaces)} chat spaces")
                
                for space in spaces:
                    space_id = space.get("id")
                    space_name = space.get("name", "Unknown Space")
                    
                    if space_id:
                        logger.info(f"ðŸ” Checking space: {space_name}")
                        # Get channels in this space
                        space_channels = self._get_space_channels(space_id)
                        
                        for channel in space_channels:
                            channel_id = channel.get("id")
                            channel_name = channel.get("name", "Unknown Channel")
                            
                            if channel_id:
                                logger.info(f"  ðŸ“¢ Checking space channel: {channel_name}")
                                channel_messages = self._extract_channel_messages_by_id(
                                    channel_id, from_date, to_date
                                )
                                if channel_messages:
                                    logger.info(f"  ðŸ’¬ Found {len(channel_messages)} messages in space channel: {channel_name}")
                                messages.extend(channel_messages)
                        
            elif spaces_response.status_code == 404:
                logger.info(f"ðŸ“­ No chat spaces found")
            else:
                logger.error(f"âŒ Failed to fetch chat spaces: {spaces_response.status_code} - {spaces_response.text}")
                
        except Exception as e:
            logger.error(f"âŒ Error extracting space messages: {e}")
        
        logger.info(f"âœ… Extracted {len(messages)} space messages")
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
                logger.debug(f"Failed to get channels for space {space_id}: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting space channels: {e}")
            return []
    
    def _extract_channel_messages_by_id(self, channel_id: str, from_date: str, to_date: str) -> List[Dict]:
        """Extract messages from a specific channel"""
        messages = []
        
        try:
            # For channel messages, we need to use the user endpoint with to_channel parameter
            # This is a simplified approach - in practice, you'd need the user_id
            url = f"https://api.zoom.us/v2/chat/channels/{channel_id}/messages"
            params = {
                "from": from_date,
                "to": to_date,
                "page_size": 50,
                "include_fields": "message,date_time,sender,receiver,message_type"
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
                    break
                else:
                    logger.warning(f"Failed to fetch channel messages: {response.status_code} - {response.text}")
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
                
            logger.info(f"ðŸ’¾ Saved chat data for {user_email}")
            
        except Exception as e:
            logger.error(f"Error saving chat data for {user_email}: {e}")

def extract_all_chat_messages(
    output_dir: str = "./zoom_chat_messages",
    user_filter: Optional[List[str]] = None,
    from_date: str = "2020-01-01",
    to_date: Optional[str] = None,
    include_inactive_users: bool = True,
    dry_run: bool = False
):
    """Main function to extract all chat messages"""
    
    logger.info("ðŸš€ Starting Zoom Chat Messages Extraction")
    logger.info(f"ðŸ“ Output Directory: {output_dir}")
    logger.info(f"ðŸ“… Date Range: {from_date} to {to_date or datetime.now().strftime('%Y-%m-%d')}")
    
    if dry_run:
        logger.info("ðŸ§ª DRY RUN MODE - No data will be extracted")
    
    # Initialize authentication
    try:
        auth = get_auth_from_env()
        auth_headers = auth.get_auth_headers()
        logger.info("âœ… Authentication successful")
    except Exception as e:
        logger.error(f"âŒ Authentication failed: {e}")
        return False
    
    # Initialize extractor
    extractor = ChatMessageExtractor(auth_headers, output_dir)
    
    # Get users to process
    user_enumerator = UserEnumerator(auth_headers)
    
    # Get all users (active + inactive if requested)
    all_users = []
    
    if user_filter:
        logger.info(f"ðŸ‘¥ Processing filtered users: {user_filter}")
        
        # Get active users
        print("ðŸ“‹ Getting active users...")
        try:
            active_users = list(user_enumerator.list_all_users(user_filter, user_type="active"))
            all_users.extend(active_users)
            print(f"   Found {len(active_users)} active users")
        except Exception as e:
            print(f"   âš ï¸  Could not get active users: {e}")
        
        # Get inactive users if requested
        if include_inactive_users:
            print("ðŸ“‹ Getting inactive users...")
            try:
                inactive_users = list(user_enumerator.list_all_users(user_filter, user_type="inactive"))
                all_users.extend(inactive_users)
                print(f"   Found {len(inactive_users)} inactive users")
            except Exception as e:
                print(f"   âš ï¸  Could not get inactive users: {e}")
        
        # Get pending users if requested
        print("ðŸ“‹ Getting pending users...")
        try:
            pending_users = list(user_enumerator.list_all_users(user_filter, user_type="pending"))
            all_users.extend(pending_users)
            print(f"   Found {len(pending_users)} pending users")
        except Exception as e:
            print(f"   âš ï¸  Could not get pending users: {e}")
            
    else:
        logger.info("ðŸ‘¥ Processing all users")
        
        # Get active users
        print("ðŸ“‹ Getting active users...")
        try:
            active_users = list(user_enumerator.list_all_users(user_type="active"))
            all_users.extend(active_users)
            print(f"   Found {len(active_users)} active users")
        except Exception as e:
            print(f"   âš ï¸  Could not get active users: {e}")
        
        # Get inactive users if requested
        if include_inactive_users:
            print("ðŸ“‹ Getting inactive users...")
            try:
                inactive_users = list(user_enumerator.list_all_users(user_type="inactive"))
                all_users.extend(inactive_users)
                print(f"   Found {len(inactive_users)} inactive users")
            except Exception as e:
                print(f"   âš ï¸  Could not get inactive users: {e}")
        
        # Get pending users if requested
        print("ðŸ“‹ Getting pending users...")
        try:
            pending_users = list(user_enumerator.list_all_users(user_type="pending"))
            all_users.extend(pending_users)
            print(f"   Found {len(pending_users)} pending users")
        except Exception as e:
            print(f"   âš ï¸  Could not get pending users: {e}")
    
    logger.info(f"ðŸŽ¯ Found {len(all_users)} users to process")
    
    if dry_run:
        logger.info("ðŸ§ª DRY RUN: Would extract chat messages for:")
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
            logger.warning(f"âš ï¸ Skipping user {i} - missing email or ID")
            continue
        
        logger.info(f"ðŸ‘¤ [{i}/{len(all_users)}] Processing {user_email}")
        
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
            logger.error(f"âŒ Error processing user {user_email}: {e}")
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
    
    logger.info("ðŸŽ‰ Chat Messages Extraction Complete!")
    logger.info(f"ðŸ“Š Summary:")
    logger.info(f"  ðŸ‘¥ Users processed: {processed_users}/{len(all_users)}")
    logger.info(f"  ðŸ’¬ Total messages: {total_messages}")
    logger.info(f"  ðŸ“ Output directory: {extractor.output_dir}")
    
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
        logger.error("âŒ Please specify either --user-filter or --all-users")
        return 1
    
    try:
        success = extract_all_chat_messages(
            output_dir=args.output_dir,
            user_filter=args.user_filter,
            from_date=args.from_date,
            to_date=args.to_date,
            include_inactive_users=args.include_inactive,
            dry_run=args.dry_run
        )
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        logger.info("ðŸ›‘ Extraction interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"âŒ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
