"""
Recordings Listing Module

Handles listing recordings per user and date window with pagination support.
"""

import logging
import requests
from typing import List, Dict, Optional, Iterator, Tuple
from datetime import datetime
from urllib.parse import quote

logger = logging.getLogger(__name__)


class RecordingsLister:
    """Handles listing of Zoom recordings with pagination and filtering."""
    
    def __init__(self, auth_headers: Dict[str, str]):
        """
        Initialize recordings lister.
        
        Args:
            auth_headers: Authorization headers for API requests
        """
        self.auth_headers = auth_headers
        self.base_url = "https://api.zoom.us/v2"
    
    def list_user_recordings(self, user_id: str, start_date: datetime, end_date: datetime,
                           include_trash: bool = False) -> Iterator[Dict]:
        """
        List recordings for a specific user within a date range.
        
        Args:
            user_id: Zoom user ID
            start_date: Start date for recordings
            end_date: End date for recordings
            include_trash: Whether to include recordings in trash
            
        Yields:
            Recording dictionaries from the API
        """
        # Format dates for API
        from_date = start_date.strftime('%Y-%m-%d')
        to_date = end_date.strftime('%Y-%m-%d')
        
        url = f"{self.base_url}/users/{user_id}/recordings"
        params = {
            "from": from_date,
            "to": to_date,
            "page_size": 30  # Reduced page size for better compatibility
        }
        
        if include_trash:
            params["trash_type"] = "meeting_recordings"
        
        next_page_token = None
        
        while True:
            if next_page_token:
                params["next_page_token"] = next_page_token
            
            logger.debug(f"Fetching recordings for user {user_id} from {from_date} to {to_date}, page token: {next_page_token}")
            
            try:
                response = requests.get(url, headers=self.auth_headers, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                meetings = data.get("meetings", [])
                
                for meeting in meetings:
                    # Process recording files for each meeting
                    processed_meeting = self._process_meeting_recordings(meeting, user_id)
                    if processed_meeting:
                        yield processed_meeting
                
                # Check for next page
                next_page_token = data.get("next_page_token")
                if not next_page_token:
                    break
                    
                logger.debug(f"Found {len(meetings)} meetings, continuing to next page")
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to fetch recordings for user {user_id}: {e}")
                raise
    
    def _process_meeting_recordings(self, meeting: Dict, user_id: str) -> Optional[Dict]:
        """
        Process a meeting's recording files and metadata.
        
        Args:
            meeting: Meeting data from API
            user_id: User ID for the meeting
            
        Returns:
            Processed meeting with recording files, or None if no recordings
        """
        recording_files = meeting.get("recording_files", [])
        
        if not recording_files:
            logger.debug(f"No recording files found for meeting {meeting.get('uuid', 'unknown')}")
            return None
        
        # Filter and categorize recording files
        processed_files = []
        for file_info in recording_files:
            processed_file = self._process_recording_file(file_info)
            if processed_file:
                processed_files.append(processed_file)
        
        if not processed_files:
            logger.debug(f"No valid recording files found for meeting {meeting.get('uuid', 'unknown')}")
            return None
        
        # Add processed files to meeting data
        meeting["processed_files"] = processed_files
        meeting["user_id"] = user_id
        meeting["total_files"] = len(processed_files)
        
        return meeting
    
    def _process_recording_file(self, file_info: Dict) -> Optional[Dict]:
        """
        Process individual recording file information.
        
        Args:
            file_info: File information from API
            
        Returns:
            Processed file information or None if invalid
        """
        # Extract file type and determine extension
        file_type_raw = file_info.get("file_type", "")
        file_type = str(file_type_raw).lower() if file_type_raw else ""
        file_extension = file_info.get("file_extension", "")
        
        # Map file types to extensions if not provided
        if not file_extension:
            extension_map = {
                "mp4": "mp4",
                "m4a": "m4a", 
                "timeline": "json",
                "transcript": "vtt",
                "chat": "txt",
                "cc": "vtt",
                "audio_transcript": "vtt"
            }
            file_extension = extension_map.get(file_type, "unknown")
        
        # Skip files without download URLs
        download_url = file_info.get("download_url")
        if not download_url:
            logger.warning(f"File {file_info.get('id', 'unknown')} has no download URL")
            return None
        
        # Skip files that are not ready for download
        status_raw = file_info.get("status", "")
        status = str(status_raw).lower() if status_raw else ""
        if status == "processing":
            logger.debug(f"File {file_info.get('id', 'unknown')} is still processing")
            return None
        
        processed_file = {
            "id": file_info.get("id"),
            "file_type": file_type,
            "file_extension": file_extension,
            "file_size": file_info.get("file_size", 0),
            "download_url": download_url,
            "status": status,
            "recording_start": file_info.get("recording_start"),
            "recording_end": file_info.get("recording_end"),
            "play_url": file_info.get("play_url")
        }
        
        return processed_file
    
    def get_meeting_recordings_by_uuid(self, meeting_uuid: str) -> Optional[Dict]:
        """
        Get recordings for a specific meeting by UUID.
        
        Args:
            meeting_uuid: Meeting UUID (may need double URL encoding)
            
        Returns:
            Meeting with recordings or None if not found
        """
        # Double URL encode the UUID if it contains forward slashes
        if "/" in meeting_uuid:
            encoded_uuid = quote(quote(meeting_uuid, safe=""), safe="")
        else:
            encoded_uuid = quote(meeting_uuid, safe="")
        
        url = f"{self.base_url}/meetings/{encoded_uuid}/recordings"
        
        try:
            response = requests.get(url, headers=self.auth_headers, timeout=30)
            response.raise_for_status()
            
            meeting = response.json()
            
            # Process the meeting's recording files
            processed_meeting = self._process_meeting_recordings(meeting, meeting.get("host_id", "unknown"))
            return processed_meeting
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to get recordings for meeting {meeting_uuid}: {e}")
            return None
    
    def list_all_recordings(self, users: Iterator[Dict], date_windows: Iterator[Tuple[datetime, datetime]],
                          include_trash: bool = False) -> Iterator[Tuple[Dict, Dict, Tuple[datetime, datetime]]]:
        """
        List all recordings across all users and date windows.
        
        Args:
            users: Iterator of user dictionaries
            date_windows: Iterator of (start_date, end_date) tuples
            include_trash: Whether to include recordings in trash
            
        Yields:
            Tuples of (user, meeting, date_window)
        """
        users_list = list(users)  # Convert to list to avoid iterator exhaustion
        
        for user in users_list:
            user_id = user["id"]
            user_email = user.get("email", "unknown")
            
            logger.info(f"Processing user: {user_email} ({user_id})")
            
            for start_date, end_date in date_windows:
                logger.info(f"Processing date window: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
                
                try:
                    for meeting in self.list_user_recordings(user_id, start_date, end_date, include_trash):
                        yield (user, meeting, (start_date, end_date))
                        
                except Exception as e:
                    logger.error(f"Failed to process recordings for user {user_email} in window {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}: {e}")
                    continue
