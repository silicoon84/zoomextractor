#!/usr/bin/env python3
"""
Extract Direct Messages from All Users' Perspectives

This script extracts direct messages (DMs) from every user's perspective,
ensuring complete coverage of all one-on-one conversations.
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

class DMExtractor:
    """Extract direct messages from all users' perspectives"""
    
    def __init__(self, auth_headers: Dict[str, str], output_dir: str = "./dm_extraction"):
        self.auth_headers = auth_headers
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.rate_limiter = RateLimiter()
        
        # Create subdirectories
        (self.output_dir / "conversations").mkdir(exist_ok=True)
        (self.output_dir / "files").mkdir(exist_ok=True)
        (self.output_dir / "_metadata").mkdir(exist_ok=True)
        
        logger.info(f"DM extraction output: {self.output_dir}")
    
    def get_messages(self, user_id: str, to_contact: str, from_date: str, to_date: str, 
                    include_files: bool = True) -> List[Dict]:
        """Get direct messages between user and contact"""
        
        messages = []
        
        try:
            logger.info(f"Getting DM messages: {user_id} ↔ {to_contact}")
            
            url = f"https://api.zoom.us/v2/chat/users/{user_id}/messages"
            params = {
                "to_contact": to_contact,
                "from": from_date,
                "to": to_date,
                "page_size": 50,
                "download_file_formats": "mp4" if include_files else None
            }
            
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
                    
                    next_page_token = data.get("next_page_token")
                    if not next_page_token:
                        break
                        
                elif response.status_code == 404:
                    logger.debug(f"No DM messages found between {user_id} and {to_contact}")
                    break
                else:
                    logger.warning(f"Failed to get DM messages: {response.status_code} - {response.text}")
                    break
                    
        except Exception as e:
            logger.error(f"Error getting DM messages: {e}")
        
        return messages
    
    def download_file(self, file_info: Dict) -> Optional[str]:
        """Download a file attachment"""
        try:
            download_url = file_info.get("download_url")
            file_name = file_info.get("file_name", "unknown_file")
            file_id = file_info.get("file_id", "unknown_id")
            
            if not download_url:
                return None
            
            self.rate_limiter.sleep(0)
            response = requests.get(download_url, headers=self.auth_headers)
            
            if response.status_code == 200:
                safe_filename = "".join(c for c in file_name if c.isalnum() or c in ('.', '-', '_')).strip()
                file_path = self.output_dir / "files" / f"{file_id}_{safe_filename}"
                
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                
                return str(file_path)
            else:
                logger.error(f"Failed to download file {file_name}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            return None
    
    def extract_user_dms(self, user_id: str, user_email: str, all_users: List[Dict], 
                        days: int, download_files: bool) -> Dict[str, Any]:
        """Extract all DMs for a specific user"""
        
        # Calculate date range
        to_date = datetime.now().isoformat() + "Z"
        from_date = (datetime.now() - timedelta(days=days)).isoformat() + "Z"
        
        logger.info(f"Extracting DMs for user: {user_email} ({user_id})")
        
        user_dm_results = {
            "user_id": user_id,
            "user_email": user_email,
            "date_range": f"{from_date} to {to_date}",
            "conversations": [],
            "total_messages": 0,
            "total_files": 0
        }
        
        # Get DMs with each other user
        for other_user in all_users:
            other_user_id = other_user.get("id")
            other_user_email = other_user.get("email")
            
            if not other_user_id or not other_user_email or other_user_id == user_id:
                continue
            
            try:
                # Get messages between these two users
                messages = self.get_messages(
                    user_id=user_id,
                    to_contact=other_user_email,
                    from_date=from_date,
                    to_date=to_date,
                    include_files=download_files
                )
                
                if messages:
                    # Download files if requested
                    downloaded_files = []
                    if download_files:
                        for message in messages:
                            files = message.get("files", [])
                            for file_info in files:
                                file_path = self.download_file(file_info)
                                if file_path:
                                    downloaded_files.append(file_path)
                    
                    # Save conversation
                    safe_other_email = other_user_email.replace("@", "_").replace(".", "_")
                    conversation_file = self.output_dir / "conversations" / f"{user_email.replace('@', '_').replace('.', '_')}_to_{safe_other_email}.json"
                    
                    conversation_data = {
                        "user1_email": user_email,
                        "user1_id": user_id,
                        "user2_email": other_user_email,
                        "user2_id": other_user_id,
                        "message_count": len(messages),
                        "downloaded_files": downloaded_files,
                        "messages": messages
                    }
                    
                    with open(conversation_file, 'w', encoding='utf-8') as f:
                        json.dump(conversation_data, f, indent=2, ensure_ascii=False)
                    
                    user_dm_results["conversations"].append({
                        "with_user": other_user_email,
                        "message_count": len(messages),
                        "downloaded_files": len(downloaded_files),
                        "conversation_file": str(conversation_file)
                    })
                    
                    user_dm_results["total_messages"] += len(messages)
                    user_dm_results["total_files"] += len(downloaded_files)
                    
                    logger.info(f"  DM with {other_user_email}: {len(messages)} messages, {len(downloaded_files)} files")
                
            except Exception as e:
                logger.error(f"Error extracting DM between {user_email} and {other_user_email}: {e}")
                continue
        
        return user_dm_results
    
    def extract_all_dms(self, days: int = 30, download_files: bool = True,
                       include_inactive: bool = True) -> Dict[str, Any]:
        """Extract direct messages from all users' perspectives"""
        
        logger.info("Starting comprehensive DM extraction from all users' perspectives")
        
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
            return {"users": [], "total_conversations": 0, "total_messages": 0, "total_files": 0}
        
        # Process each user
        user_results = []
        total_conversations = 0
        total_messages = 0
        total_files = 0
        processed_users = 0
        
        for i, user in enumerate(tqdm(all_users, desc="Processing users"), 1):
            user_email = user.get("email")
            user_id = user.get("id")
            
            if not user_email or not user_id:
                logger.warning(f"Skipping user {i} - missing email or ID")
                continue
            
            logger.info(f"[{i}/{len(all_users)}] Processing user: {user_email} ({user_id})")
            
            try:
                # Extract DMs for this user
                user_result = self.extract_user_dms(
                    user_id=user_id,
                    user_email=user_email,
                    all_users=all_users,
                    days=days,
                    download_files=download_files
                )
                
                user_results.append(user_result)
                total_conversations += len(user_result.get("conversations", []))
                total_messages += user_result.get("total_messages", 0)
                total_files += user_result.get("total_files", 0)
                processed_users += 1
                
                logger.info(f"User {user_email}: {len(user_result.get('conversations', []))} conversations, {user_result.get('total_messages', 0)} messages")
                
            except Exception as e:
                logger.error(f"Error processing user {user_email}: {e}")
                continue
        
        # Create overall summary
        overall_summary = {
            "extraction_date": datetime.now().isoformat(),
            "total_users_found": len(all_users),
            "processed_users": processed_users,
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "total_files": total_files,
            "date_range_days": days,
            "include_inactive": include_inactive,
            "download_files": download_files,
            "user_results": user_results
        }
        
        # Save overall summary
        summary_file = self.output_dir / "_metadata" / "dm_extraction_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(overall_summary, f, indent=2, ensure_ascii=False)
        
        logger.info(f"DM extraction complete!")
        logger.info(f"Processed {processed_users}/{len(all_users)} users")
        logger.info(f"Total conversations: {total_conversations}")
        logger.info(f"Total messages: {total_messages}")
        logger.info(f"Total files: {total_files}")
        
        return overall_summary

def main():
    """Main CLI function"""
    
    @click.command()
    @click.option('--days', default=30, help='Number of days to look back (default: 30)')
    @click.option('--output-dir', default='./dm_extraction', help='Output directory')
    @click.option('--no-files', is_flag=True, help='Skip downloading file attachments')
    @click.option('--no-inactive', is_flag=True, help='Skip inactive users')
    def cli(days, output_dir, no_files, no_inactive):
        """Extract Direct Messages from All Users' Perspectives"""
        
        # Initialize authentication
        try:
            auth = get_auth_from_env()
            auth_headers = auth.get_auth_headers()
            logger.info("Authentication successful")
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return 1
        
        # Initialize extractor
        extractor = DMExtractor(auth_headers, output_dir)
        
        try:
            download_files = not no_files
            include_inactive = not no_inactive
            
            # Extract all DMs
            result = extractor.extract_all_dms(
                days=days,
                download_files=download_files,
                include_inactive=include_inactive
            )
            
            logger.info("DM extraction completed successfully!")
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
