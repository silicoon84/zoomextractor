#!/usr/bin/env python3
"""
Zoom Chat Reports Extraction Script

This script extracts chat messages using the official Reports API which provides:
- All chat sessions for a given time period
- Complete chat messages for each session
- Edited and deleted messages
- File attachments and reactions
- Bot messages

The Reports API is more reliable than individual chat endpoints and provides
comprehensive coverage of all chat activity.

Prerequisites:
- Pro or higher Zoom plan
- report_chat:read:admin, imchat:read:admin scopes
- Rate limit: MEDIUM
"""

import os
import sys
import json
import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dateutil.relativedelta import relativedelta

# Add the zoom_extractor module to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from zoom_extractor.auth import get_auth_from_env
from zoom_extractor.rate_limiter import RateLimiter
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ChatReportsExtractor:
    """Extract chat messages using Zoom Reports API"""
    
    def __init__(self, auth_headers: Dict[str, str], output_dir: str):
        self.auth_headers = auth_headers
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.rate_limiter = RateLimiter()
        
        # Create subdirectories
        (self.output_dir / "sessions").mkdir(exist_ok=True)
        (self.output_dir / "messages").mkdir(exist_ok=True)
        (self.output_dir / "_metadata").mkdir(exist_ok=True)
        
        logger.info(f"[INFO] Chat reports will be saved to: {self.output_dir}")
    
    def extract_chat_reports(self, from_date: str, to_date: str, 
                           include_edited: bool = True, include_deleted: bool = True,
                           include_bot_messages: bool = True, include_reactions: bool = True) -> Dict[str, Any]:
        """Extract all chat reports for the specified date range"""
        
        logger.info(f"[START] Extracting chat reports from {from_date} to {to_date}")
        
        # Split into monthly chunks (Reports API requires monthly ranges)
        monthly_ranges = self._get_monthly_ranges(from_date, to_date)
        
        all_sessions = []
        all_messages = []
        extraction_stats = {
            "total_sessions": 0,
            "total_messages": 0,
            "total_edited_messages": 0,
            "total_deleted_messages": 0,
            "date_range": f"{from_date} to {to_date}",
            "monthly_ranges": len(monthly_ranges),
            "extraction_date": datetime.now().isoformat()
        }
        
        for i, (month_from, month_to) in enumerate(monthly_ranges, 1):
            logger.info(f"[MONTH] [{i}/{len(monthly_ranges)}] Processing {month_from} to {month_to}")
            
            try:
                # Get chat sessions for this month
                sessions = self._get_chat_sessions(month_from, month_to)
                logger.info(f"[SESSIONS] Found {len(sessions)} chat sessions for {month_from}")
                
                all_sessions.extend(sessions)
                extraction_stats["total_sessions"] += len(sessions)
                
                # Extract messages for each session
                for session in sessions:
                    session_id = session.get("id")
                    session_name = session.get("name", "Unknown")
                    session_type = session.get("type", "Unknown")
                    
                    logger.info(f"[SESSION] Processing session: {session_name} ({session_type})")
                    
                    try:
                        messages_data = self._get_session_messages(
                            session_id, month_from, month_to,
                            include_edited, include_deleted,
                            include_bot_messages, include_reactions
                        )
                        
                        if messages_data:
                            # Save session messages
                            self._save_session_messages(session, messages_data)
                            
                            # Count messages
                            messages = messages_data.get("messages", [])
                            edited = messages_data.get("edited_messages", [])
                            deleted = messages_data.get("deleted_messages", [])
                            
                            all_messages.extend(messages)
                            extraction_stats["total_messages"] += len(messages)
                            extraction_stats["total_edited_messages"] += len(edited)
                            extraction_stats["total_deleted_messages"] += len(deleted)
                            
                            logger.info(f"[MESSAGES] Extracted {len(messages)} messages, {len(edited)} edited, {len(deleted)} deleted")
                        
                    except Exception as e:
                        logger.error(f"[ERROR] Failed to extract messages for session {session_id}: {e}")
                        continue
                        
            except Exception as e:
                logger.error(f"[ERROR] Failed to process month {month_from}: {e}")
                continue
        
        # Save summary data
        self._save_extraction_summary(extraction_stats, all_sessions)
        
        logger.info(f"[COMPLETE] Chat reports extraction complete!")
        logger.info(f"[SUMMARY] Sessions: {extraction_stats['total_sessions']}, Messages: {extraction_stats['total_messages']}")
        
        return extraction_stats
    
    def _get_monthly_ranges(self, from_date: str, to_date: str) -> List[tuple]:
        """Split date range into monthly chunks as required by Reports API"""
        ranges = []
        
        start_date = datetime.strptime(from_date, "%Y-%m-%d")
        end_date = datetime.strptime(to_date, "%Y-%m-%d")
        
        current_date = start_date.replace(day=1)  # Start of month
        
        while current_date <= end_date:
            # Calculate month end
            next_month = current_date + relativedelta(months=1)
            month_end = min(next_month - timedelta(days=1), end_date)
            
            ranges.append((
                current_date.strftime("%Y-%m-%d"),
                month_end.strftime("%Y-%m-%d")
            ))
            
            current_date = next_month
        
        return ranges
    
    def _get_chat_sessions(self, from_date: str, to_date: str) -> List[Dict]:
        """Get chat sessions for the specified date range"""
        sessions = []
        
        try:
            url = "https://api.zoom.us/v2/report/chat/sessions"
            params = {
                "from": from_date,
                "to": to_date,
                "page_size": 300  # Max page size
            }
            
            next_page_token = None
            
            while True:
                if next_page_token:
                    params["next_page_token"] = next_page_token
                
                self.rate_limiter.sleep(0)
                response = requests.get(url, headers=self.auth_headers, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    page_sessions = data.get("sessions", [])
                    sessions.extend(page_sessions)
                    
                    next_page_token = data.get("next_page_token")
                    if not next_page_token:
                        break
                        
                elif response.status_code == 404:
                    logger.info(f"[INFO] No chat sessions found for {from_date} to {to_date}")
                    break
                else:
                    logger.error(f"[ERROR] Failed to fetch chat sessions: {response.status_code} - {response.text}")
                    break
                    
        except Exception as e:
            logger.error(f"[ERROR] Error getting chat sessions: {e}")
        
        return sessions
    
    def _get_session_messages(self, session_id: str, from_date: str, to_date: str,
                            include_edited: bool, include_deleted: bool,
                            include_bot_messages: bool, include_reactions: bool) -> Optional[Dict]:
        """Get messages for a specific chat session"""
        
        try:
            url = f"https://api.zoom.us/v2/report/chat/sessions/{session_id}"
            params = {
                "from": from_date,
                "to": to_date,
                "page_size": 100,
                "include_bot_message": include_bot_messages,
                "include_reactions": include_reactions,
                "query_all_modifications": True
            }
            
            # Add edited/deleted message fields
            include_fields = []
            if include_edited:
                include_fields.append("edited_messages")
            if include_deleted:
                include_fields.append("deleted_messages")
            
            if include_fields:
                params["include_fields"] = ",".join(include_fields)
            
            all_messages = []
            all_edited = []
            all_deleted = []
            next_page_token = None
            
            while True:
                if next_page_token:
                    params["next_page_token"] = next_page_token
                
                self.rate_limiter.sleep(0)
                response = requests.get(url, headers=self.auth_headers, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Collect messages
                    page_messages = data.get("messages", [])
                    page_edited = data.get("edited_messages", [])
                    page_deleted = data.get("deleted_messages", [])
                    
                    all_messages.extend(page_messages)
                    all_edited.extend(page_edited)
                    all_deleted.extend(page_deleted)
                    
                    next_page_token = data.get("next_page_token")
                    if not next_page_token:
                        break
                        
                elif response.status_code == 404:
                    logger.debug(f"[DEBUG] No messages found for session {session_id}")
                    break
                else:
                    logger.warning(f"[WARN] Failed to fetch messages for session {session_id}: {response.status_code}")
                    break
            
            return {
                "session_id": session_id,
                "from": from_date,
                "to": to_date,
                "messages": all_messages,
                "edited_messages": all_edited,
                "deleted_messages": all_deleted,
                "total_messages": len(all_messages),
                "total_edited": len(all_edited),
                "total_deleted": len(all_deleted)
            }
            
        except Exception as e:
            logger.error(f"[ERROR] Error getting session messages: {e}")
            return None
    
    def _save_session_messages(self, session: Dict, messages_data: Dict):
        """Save session messages to files"""
        try:
            session_id = session.get("id", "unknown")
            session_name = session.get("name", "Unknown")
            session_type = session.get("type", "Unknown")
            
            # Sanitize session name for filename
            safe_name = "".join(c for c in session_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_name = safe_name.replace(' ', '_')[:50]  # Limit length
            
            # Save session info
            session_file = self.output_dir / "sessions" / f"{session_id}_{safe_name}.json"
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "session_info": session,
                    "messages_data": messages_data
                }, f, indent=2, ensure_ascii=False)
            
            # Save messages separately for easier processing
            if messages_data.get("messages"):
                messages_file = self.output_dir / "messages" / f"{session_id}_messages.json"
                with open(messages_file, 'w', encoding='utf-8') as f:
                    json.dump(messages_data["messages"], f, indent=2, ensure_ascii=False)
            
            if messages_data.get("edited_messages"):
                edited_file = self.output_dir / "messages" / f"{session_id}_edited.json"
                with open(edited_file, 'w', encoding='utf-8') as f:
                    json.dump(messages_data["edited_messages"], f, indent=2, ensure_ascii=False)
            
            if messages_data.get("deleted_messages"):
                deleted_file = self.output_dir / "messages" / f"{session_id}_deleted.json"
                with open(deleted_file, 'w', encoding='utf-8') as f:
                    json.dump(messages_data["deleted_messages"], f, indent=2, ensure_ascii=False)
                    
        except Exception as e:
            logger.error(f"[ERROR] Error saving session messages: {e}")
    
    def _save_extraction_summary(self, stats: Dict, sessions: List[Dict]):
        """Save extraction summary"""
        try:
            # Save stats
            stats_file = self.output_dir / "_metadata" / "extraction_summary.json"
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2, ensure_ascii=False)
            
            # Save session summary
            session_summary = []
            for session in sessions:
                summary = {
                    "id": session.get("id"),
                    "name": session.get("name"),
                    "type": session.get("type"),
                    "status": session.get("status"),
                    "member_count": len(session.get("member_emails", [])),
                    "has_external_member": session.get("has_external_member", False),
                    "last_message_time": session.get("last_message_sent_time")
                }
                session_summary.append(summary)
            
            sessions_file = self.output_dir / "_metadata" / "sessions_summary.json"
            with open(sessions_file, 'w', encoding='utf-8') as f:
                json.dump(session_summary, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"[ERROR] Error saving extraction summary: {e}")

def extract_chat_reports(
    from_date: str,
    to_date: str,
    output_dir: str = "./zoom_chat_reports",
    include_edited: bool = True,
    include_deleted: bool = True,
    include_bot_messages: bool = True,
    include_reactions: bool = True
) -> bool:
    """Main function to extract chat reports"""
    
    logger.info("[START] Starting Zoom Chat Reports Extraction")
    logger.info(f"[DIR] Output Directory: {output_dir}")
    logger.info(f"[DATE] Date Range: {from_date} to {to_date}")
    
    # Initialize authentication
    try:
        auth = get_auth_from_env()
        auth_headers = auth.get_auth_headers()
        logger.info("[OK] Authentication successful")
    except Exception as e:
        logger.error(f"[ERROR] Authentication failed: {e}")
        return False
    
    # Initialize extractor
    extractor = ChatReportsExtractor(auth_headers, output_dir)
    
    try:
        # Extract chat reports
        stats = extractor.extract_chat_reports(
            from_date, to_date,
            include_edited, include_deleted,
            include_bot_messages, include_reactions
        )
        
        logger.info("[COMPLETE] Chat Reports Extraction Complete!")
        logger.info(f"[SUMMARY] Final Statistics:")
        logger.info(f"  [SESSIONS] Total sessions: {stats['total_sessions']}")
        logger.info(f"  [MESSAGES] Total messages: {stats['total_messages']}")
        logger.info(f"  [EDITED] Edited messages: {stats['total_edited_messages']}")
        logger.info(f"  [DELETED] Deleted messages: {stats['total_deleted_messages']}")
        logger.info(f"  [DIR] Output directory: {output_dir}")
        
        return True
        
    except Exception as e:
        logger.error(f"[ERROR] Chat reports extraction failed: {e}")
        return False

if __name__ == "__main__":
    import click
    
    @click.command()
    @click.option('--from-date', required=True, help='Start date for extraction (YYYY-MM-DD)')
    @click.option('--to-date', required=True, help='End date for extraction (YYYY-MM-DD)')
    @click.option('--output-dir', default='./zoom_chat_reports', help='Output directory for chat reports')
    @click.option('--no-edited', is_flag=True, help='Exclude edited messages')
    @click.option('--no-deleted', is_flag=True, help='Exclude deleted messages')
    @click.option('--no-bot', is_flag=True, help='Exclude bot messages')
    @click.option('--no-reactions', is_flag=True, help='Exclude message reactions')
    def main(from_date, to_date, output_dir, no_edited, no_deleted, no_bot, no_reactions):
        """Extract Zoom chat reports using the official Reports API"""
        
        try:
            success = extract_chat_reports(
                from_date=from_date,
                to_date=to_date,
                output_dir=output_dir,
                include_edited=not no_edited,
                include_deleted=not no_deleted,
                include_bot_messages=not no_bot,
                include_reactions=not no_reactions
            )
            
            return 0 if success else 1
            
        except KeyboardInterrupt:
            logger.info("[STOP] Extraction interrupted by user")
            return 1
        except Exception as e:
            logger.error(f"[ERROR] Unexpected error: {e}")
            return 1
    
    sys.exit(main())
