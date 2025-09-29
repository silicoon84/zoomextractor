"""
Directory Structure and File Naming Module

Handles deterministic folder structure and file naming for downloaded recordings.
"""

import os
import json
import logging
import re
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime
from urllib.parse import quote

logger = logging.getLogger(__name__)


class DirectoryStructure:
    """Handles directory structure and file naming for recordings."""
    
    def __init__(self, base_output_dir: str):
        """
        Initialize directory structure handler.
        
        Args:
            base_output_dir: Base output directory for all recordings
        """
        self.base_output_dir = Path(base_output_dir)
        self.base_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        self.meta_dir = self.base_output_dir / "_metadata"
        self.logs_dir = self.base_output_dir / "_logs"
        self.meta_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
    
    def sanitize_filename(self, filename: str, max_length: int = 200) -> str:
        """
        Sanitize filename for filesystem safety.
        
        Args:
            filename: Original filename
            max_length: Maximum filename length
            
        Returns:
            Sanitized filename
        """
        # Remove or replace invalid characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        # Remove control characters
        sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', sanitized)
        
        # Remove leading/trailing whitespace and dots
        sanitized = sanitized.strip(' .')
        
        # Replace multiple consecutive underscores with single underscore
        sanitized = re.sub(r'_+', '_', sanitized)
        
        # Truncate if too long
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        # Ensure filename is not empty
        if not sanitized:
            sanitized = "unnamed"
        
        return sanitized
    
    def get_user_directory(self, user: Dict) -> Path:
        """
        Get directory path for a user.
        
        Args:
            user: User dictionary from API
            
        Returns:
            Path to user directory
        """
        user_email = user.get("email", "unknown")
        user_id = user.get("id", "unknown")
        
        # Use email if available, otherwise use user ID
        if user_email and user_email != "unknown":
            directory_name = self.sanitize_filename(user_email, 100)
        else:
            directory_name = f"user_{user_id}"
        
        return self.base_output_dir / directory_name
    
    def get_meeting_directory(self, user: Dict, meeting: Dict) -> Path:
        """
        Get directory path for a meeting.
        
        Args:
            user: User dictionary from API
            meeting: Meeting dictionary from API
            
        Returns:
            Path to meeting directory
        """
        user_dir = self.get_user_directory(user)
        
        # Parse meeting start time
        start_time_str = meeting.get("start_time", "")
        try:
            start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            logger.warning(f"Invalid start_time format: {start_time_str}")
            start_time = datetime.utcnow()
        
        # Format timestamp
        timestamp = start_time.strftime("%Y%m%d_%H%M%S")
        
        # Get meeting topic
        topic = meeting.get("topic", "Untitled Meeting")
        sanitized_topic = self.sanitize_filename(topic, 100)
        
        # Get meeting ID
        meeting_id = meeting.get("id", meeting.get("uuid", "unknown"))
        if isinstance(meeting_id, str) and len(meeting_id) > 20:
            meeting_id = meeting_id[:20]  # Truncate long UUIDs
        
        # Create directory name
        dir_name = f"{timestamp}_{sanitized_topic}_{meeting_id}"
        dir_name = self.sanitize_filename(dir_name, 200)
        
        return user_dir / dir_name
    
    def get_file_path(self, user: Dict, meeting: Dict, file_info: Dict) -> Path:
        """
        Get file path for a recording file.
        
        Args:
            user: User dictionary from API
            meeting: Meeting dictionary from API
            file_info: File information dictionary
            
        Returns:
            Path to the file
        """
        meeting_dir = self.get_meeting_directory(user, meeting)
        
        # Parse recording start time if available
        recording_start_str = file_info.get("recording_start", "")
        if recording_start_str:
            try:
                recording_start = datetime.fromisoformat(recording_start_str.replace('Z', '+00:00'))
                timestamp = recording_start.strftime("%Y%m%d_%H%M%S")
            except (ValueError, AttributeError):
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        else:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        # Get file type and extension
        file_type = file_info.get("file_type", "unknown")
        file_extension = file_info.get("file_extension", "unknown")
        
        # Create filename
        filename = f"{timestamp}_{file_type.upper()}.{file_extension}"
        filename = self.sanitize_filename(filename, 200)
        
        return meeting_dir / filename
    
    def create_meeting_metadata(self, user: Dict, meeting: Dict, date_window: Tuple[datetime, datetime]) -> Dict:
        """
        Create metadata dictionary for a meeting.
        
        Args:
            user: User dictionary from API
            meeting: Meeting dictionary from API
            date_window: Date window tuple (start, end)
            
        Returns:
            Metadata dictionary
        """
        metadata = {
            "meeting": {
                "id": meeting.get("id"),
                "uuid": meeting.get("uuid"),
                "topic": meeting.get("topic"),
                "start_time": meeting.get("start_time"),
                "duration": meeting.get("duration"),
                "host_id": meeting.get("host_id"),
                "host_email": meeting.get("host_email"),
                "account_id": meeting.get("account_id"),
                "type": meeting.get("type")
            },
            "user": {
                "id": user.get("id"),
                "email": user.get("email"),
                "first_name": user.get("first_name"),
                "last_name": user.get("last_name"),
                "display_name": user.get("display_name")
            },
            "extraction": {
                "extracted_at": datetime.utcnow().isoformat() + "Z",
                "date_window_start": date_window[0].isoformat() + "Z",
                "date_window_end": date_window[1].isoformat() + "Z",
                "total_files": meeting.get("total_files", 0)
            },
            "files": []
        }
        
        return metadata
    
    def save_meeting_metadata(self, user: Dict, meeting: Dict, date_window: Tuple[datetime, datetime], 
                            file_results: List[Tuple[bool, Dict]]) -> Path:
        """
        Save meeting metadata to JSON file.
        
        Args:
            user: User dictionary from API
            meeting: Meeting dictionary from API
            date_window: Date window tuple (start, end)
            file_results: List of download results
            
        Returns:
            Path to metadata file
        """
        meeting_dir = self.get_meeting_directory(user, meeting)
        meeting_dir.mkdir(parents=True, exist_ok=True)
        
        metadata = self.create_meeting_metadata(user, meeting, date_window)
        
        # Add file information
        for success, file_stats in file_results:
            file_metadata = {
                "file_id": file_stats.get("file_id"),
                "file_type": file_stats.get("file_type"),
                "file_size": file_stats.get("file_size"),
                "expected_size": file_stats.get("expected_size"),
                "sha256": file_stats.get("sha256"),
                "download_status": file_stats.get("status"),
                "download_url": file_stats.get("download_url")
            }
            metadata["files"].append(file_metadata)
        
        # Save metadata file
        metadata_file = meeting_dir / "meta.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        logger.debug(f"Saved metadata to {metadata_file}")
        return metadata_file
    
    def save_files_csv(self, user: Dict, meeting: Dict, file_results: List[Tuple[bool, Dict]]) -> Optional[Path]:
        """
        Save files listing to CSV file.
        
        Args:
            user: User dictionary from API
            meeting: Meeting dictionary from API
            file_results: List of download results
            
        Returns:
            Path to CSV file or None if no files
        """
        if not file_results:
            return None
        
        meeting_dir = self.get_meeting_directory(user, meeting)
        
        csv_file = meeting_dir / "files.csv"
        
        with open(csv_file, 'w', encoding='utf-8') as f:
            # Write CSV header
            f.write("file_id,file_type,file_size,expected_size,sha256,status,download_url\n")
            
            # Write file data
            for success, file_stats in file_results:
                file_id = file_stats.get("file_id", "")
                file_type = file_stats.get("file_type", "")
                file_size = file_stats.get("file_size", "")
                expected_size = file_stats.get("expected_size", "")
                sha256 = file_stats.get("sha256", "")
                status = file_stats.get("status", "")
                download_url = file_stats.get("download_url", "")
                
                # Escape CSV values
                csv_line = f'"{file_id}","{file_type}","{file_size}","{expected_size}","{sha256}","{status}","{download_url}"\n'
                f.write(csv_line)
        
        logger.debug(f"Saved files CSV to {csv_file}")
        return csv_file
    
    def get_inventory_log_path(self) -> Path:
        """Get path for inventory log file."""
        return self.logs_dir / "inventory.jsonl"
    
    def get_state_file_path(self) -> Path:
        """Get path for state file."""
        return self.meta_dir / "extraction_state.json"
    
    def log_to_inventory(self, user: Dict, meeting: Dict, file_info: Dict, 
                        download_result: Tuple[bool, Dict], file_path: Path) -> None:
        """
        Log file download to inventory.
        
        Args:
            user: User dictionary from API
            meeting: Meeting dictionary from API
            file_info: File information dictionary
            download_result: Download result tuple (success, stats)
            file_path: Path to downloaded file
        """
        success, stats = download_result
        
        inventory_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "user": {
                "id": user.get("id"),
                "email": user.get("email")
            },
            "meeting": {
                "id": meeting.get("id"),
                "uuid": meeting.get("uuid"),
                "topic": meeting.get("topic"),
                "start_time": meeting.get("start_time")
            },
            "file": {
                "id": file_info.get("id"),
                "type": file_info.get("file_type"),
                "extension": file_info.get("file_extension"),
                "size": stats.get("file_size"),
                "expected_size": stats.get("expected_size"),
                "sha256": stats.get("sha256"),
                "path": str(file_path.relative_to(self.base_output_dir)),
                "status": stats.get("status"),
                "download_url": file_info.get("download_url")
            }
        }
        
        # Append to inventory log
        inventory_file = self.get_inventory_log_path()
        with open(inventory_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(inventory_entry, ensure_ascii=False) + '\n')
    
    def check_file_exists(self, user: Dict, meeting: Dict, file_info: Dict) -> Tuple[bool, Optional[Path]]:
        """
        Check if a file already exists and is valid.
        
        Args:
            user: User dictionary from API
            meeting: Meeting dictionary from API
            file_info: File information dictionary
            
        Returns:
            Tuple of (exists_and_valid, file_path)
        """
        file_path = self.get_file_path(user, meeting, file_info)
        
        if not file_path.exists():
            return False, file_path
        
        # Check file size
        expected_size = file_info.get("file_size")
        if expected_size:
            actual_size = file_path.stat().st_size
            if actual_size != expected_size:
                logger.debug(f"File {file_path} size mismatch: expected {expected_size}, got {actual_size}")
                return False, file_path
        
        logger.debug(f"File {file_path} already exists and is valid")
        return True, file_path
