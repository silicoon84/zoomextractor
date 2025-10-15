"""
State Management and Inventory Logging Module

Handles extraction state persistence and inventory logging for resumable operations.
"""

import json
import logging
import sqlite3
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path
from datetime import datetime
import threading

logger = logging.getLogger(__name__)


class ExtractionState:
    """Manages extraction state for resumable operations."""
    
    def __init__(self, state_file: Path):
        """
        Initialize extraction state manager.
        
        Args:
            state_file: Path to state file
        """
        self.state_file = state_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._state = self._load_state()
    
    def _load_state(self) -> Dict:
        """Load state from file."""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                logger.debug(f"Loaded extraction state from {self.state_file}")
                return state
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load state file: {e}")
        
        # Return default state
        return {
            "extraction_id": datetime.utcnow().strftime("%Y%m%d_%H%M%S"),
            "start_time": datetime.utcnow().isoformat() + "Z",
            "last_update": datetime.utcnow().isoformat() + "Z",
            "settings": {},
            "progress": {
                "users_processed": [],
                "date_windows_processed": [],
                "meetings_processed": [],
                "files_processed": [],
                "total_users": 0,
                "total_meetings": 0,
                "total_files": 0,
                "files_downloaded": 0,
                "files_skipped": 0,
                "files_failed": 0
            },
            "errors": []
        }
    
    def _save_state(self) -> None:
        """Save state to file."""
        try:
            self._state["last_update"] = datetime.utcnow().isoformat() + "Z"
            
            # Create backup of existing state file
            if self.state_file.exists():
                backup_file = self.state_file.with_suffix('.bak')
                # Remove existing backup if it exists (Windows compatibility)
                if backup_file.exists():
                    backup_file.unlink()
                self.state_file.rename(backup_file)
            
            # Write new state
            with open(self.state_file, 'w') as f:
                json.dump(self._state, f, indent=2)
            
            logger.debug(f"Saved extraction state to {self.state_file}")
            
        except IOError as e:
            logger.error(f"Failed to save state file: {e}")
    
    def update_settings(self, settings: Dict) -> None:
        """Update extraction settings in state."""
        with self._lock:
            self._state["settings"] = settings
            self._save_state()
    
    def set_totals(self, total_users: int, total_meetings: int, total_files: int) -> None:
        """Set total counts for progress tracking."""
        with self._lock:
            self._state["progress"]["total_users"] = total_users
            self._state["progress"]["total_meetings"] = total_meetings
            self._state["progress"]["total_files"] = total_files
            self._save_state()
    
    def mark_user_processed(self, user_id: str) -> None:
        """Mark a user as processed."""
        with self._lock:
            if user_id not in self._state["progress"]["users_processed"]:
                self._state["progress"]["users_processed"].append(user_id)
                self._save_state()
    
    def mark_date_window_processed(self, user_id: str, start_date: str, end_date: str) -> None:
        """Mark a date window as processed."""
        with self._lock:
            window_key = f"{user_id}:{start_date}:{end_date}"
            if window_key not in self._state["progress"]["date_windows_processed"]:
                self._state["progress"]["date_windows_processed"].append(window_key)
                self._save_state()
    
    def mark_meeting_processed(self, meeting_uuid: str) -> None:
        """Mark a meeting as processed."""
        with self._lock:
            if meeting_uuid not in self._state["progress"]["meetings_processed"]:
                self._state["progress"]["meetings_processed"].append(meeting_uuid)
                self._save_state()
    
    def mark_file_processed(self, file_id: str, status: str) -> None:
        """Mark a file as processed with status."""
        with self._lock:
            self._state["progress"]["files_processed"].append({
                "file_id": file_id,
                "status": status,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })
            
            # Update counters
            if status == "downloaded":
                self._state["progress"]["files_downloaded"] += 1
            elif status == "skipped":
                self._state["progress"]["files_skipped"] += 1
            elif status == "failed":
                self._state["progress"]["files_failed"] += 1
            
            self._save_state()
    
    def add_error(self, error: Dict) -> None:
        """Add an error to the state."""
        with self._lock:
            error["timestamp"] = datetime.utcnow().isoformat() + "Z"
            self._state["errors"].append(error)
            self._save_state()
    
    def is_user_processed(self, user_id: str) -> bool:
        """Check if a user has been processed."""
        return user_id in self._state["progress"]["users_processed"]
    
    def is_date_window_processed(self, user_id: str, start_date: str, end_date: str) -> bool:
        """Check if a date window has been processed."""
        window_key = f"{user_id}:{start_date}:{end_date}"
        return window_key in self._state["progress"]["date_windows_processed"]
    
    def is_meeting_processed(self, meeting_uuid: str) -> bool:
        """Check if a meeting has been processed."""
        return meeting_uuid in self._state["progress"]["meetings_processed"]
    
    def is_file_processed(self, file_id: str) -> bool:
        """Check if a file has been processed."""
        for file_record in self._state["progress"]["files_processed"]:
            if file_record["file_id"] == file_id:
                return True
        return False
    
    def get_progress_summary(self) -> Dict:
        """Get progress summary."""
        progress = self._state["progress"]
        
        total_files = progress["total_files"]
        downloaded = progress["files_downloaded"]
        skipped = progress["files_skipped"]
        failed = progress["files_failed"]
        remaining = total_files - (downloaded + skipped + failed)
        
        return {
            "extraction_id": self._state["extraction_id"],
            "start_time": self._state["start_time"],
            "last_update": self._state["last_update"],
            "users": {
                "processed": len(progress["users_processed"]),
                "total": progress["total_users"]
            },
            "meetings": {
                "processed": len(progress["meetings_processed"]),
                "total": progress["total_meetings"]
            },
            "files": {
                "total": total_files,
                "downloaded": downloaded,
                "skipped": skipped,
                "failed": failed,
                "remaining": remaining,
                "progress_percent": (downloaded + skipped) / total_files * 100 if total_files > 0 else 0
            },
            "errors": len(self._state["errors"])
        }
    
    def reset(self) -> None:
        """Reset extraction state."""
        with self._lock:
            self._state = self._load_state()
            self._save_state()
        logger.info("Extraction state reset")


class InventoryLogger:
    """Manages inventory logging for downloaded files."""
    
    def __init__(self, inventory_file: Path):
        """
        Initialize inventory logger.
        
        Args:
            inventory_file: Path to inventory log file
        """
        self.inventory_file = inventory_file
        self.inventory_file.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        
        # Initialize SQLite database for efficient querying
        self.db_file = inventory_file.with_suffix('.db')
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize SQLite database for inventory."""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Create inventory table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS inventory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    user_email TEXT,
                    meeting_id TEXT NOT NULL,
                    meeting_uuid TEXT,
                    meeting_topic TEXT,
                    meeting_start_time TEXT,
                    file_id TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_extension TEXT,
                    file_size INTEGER,
                    expected_size INTEGER,
                    sha256 TEXT,
                    file_path TEXT NOT NULL,
                    download_url TEXT,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    UNIQUE(file_id, meeting_id)
                )
            ''')
            
            # Create indexes for efficient querying
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON inventory(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_meeting_id ON inventory(meeting_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_file_id ON inventory(file_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON inventory(status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON inventory(timestamp)')
            
            conn.commit()
            conn.close()
            
            logger.debug(f"Initialized inventory database at {self.db_file}")
            
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize inventory database: {e}")
    
    def log_file(self, user: Dict, meeting: Dict, file_info: Dict, 
                file_path: Path, download_result: Tuple[bool, Dict], 
                error_message: Optional[str] = None) -> None:
        """
        Log a file download to inventory.
        
        Args:
            user: User dictionary
            meeting: Meeting dictionary
            file_info: File information dictionary
            file_path: Path to downloaded file
            download_result: Download result tuple (success, stats)
            error_message: Error message if download failed
        """
        success, stats = download_result
        
        with self._lock:
            # Write to JSONL file for human readability
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
                    "size": stats.get("file_size", 0),
                    "expected_size": stats.get("expected_size"),
                    "sha256": stats.get("sha256"),
                    "path": str(file_path),
                    "download_url": file_info.get("download_url"),
                    "status": stats.get("status", "failed"),
                    "error": error_message
                }
            }
            
            # Append to JSONL file
            with open(self.inventory_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(inventory_entry, ensure_ascii=False) + '\n')
            
            # Insert into SQLite database
            try:
                conn = sqlite3.connect(self.db_file)
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO inventory (
                        timestamp, user_id, user_email, meeting_id, meeting_uuid,
                        meeting_topic, meeting_start_time, file_id, file_type,
                        file_extension, file_size, expected_size, sha256,
                        file_path, download_url, status, error_message
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    inventory_entry["timestamp"],
                    user.get("id"),
                    user.get("email"),
                    meeting.get("id"),
                    meeting.get("uuid"),
                    meeting.get("topic"),
                    meeting.get("start_time"),
                    file_info.get("id"),
                    file_info.get("file_type"),
                    file_info.get("file_extension"),
                    stats.get("file_size", 0),
                    stats.get("expected_size"),
                    stats.get("sha256"),
                    str(file_path),
                    file_info.get("download_url"),
                    stats.get("status", "failed"),
                    error_message
                ))
                
                conn.commit()
                conn.close()
                
            except sqlite3.Error as e:
                logger.error(f"Failed to insert into inventory database: {e}")
    
    def get_file_status(self, file_id: str) -> Optional[Dict]:
        """
        Get status of a file by ID.
        
        Args:
            file_id: File ID to look up
            
        Returns:
            File status dictionary or None if not found
        """
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT file_id, file_type, file_size, sha256, file_path, status, error_message
                FROM inventory WHERE file_id = ?
            ''', (file_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    "file_id": row[0],
                    "file_type": row[1],
                    "file_size": row[2],
                    "sha256": row[3],
                    "file_path": row[4],
                    "status": row[5],
                    "error_message": row[6]
                }
            
        except sqlite3.Error as e:
            logger.error(f"Failed to query inventory database: {e}")
        
        return None
    
    def get_user_summary(self, user_id: str) -> Dict:
        """
        Get summary of files for a user.
        
        Args:
            user_id: User ID to summarize
            
        Returns:
            User summary dictionary
        """
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT status, COUNT(*), SUM(file_size)
                FROM inventory WHERE user_id = ? GROUP BY status
            ''', (user_id,))
            
            results = cursor.fetchall()
            conn.close()
            
            summary = {
                "user_id": user_id,
                "total_files": 0,
                "downloaded": 0,
                "failed": 0,
                "total_size": 0
            }
            
            for status, count, size in results:
                summary["total_files"] += count
                summary["total_size"] += size or 0
                
                if status == "success":
                    summary["downloaded"] = count
                elif status == "failed":
                    summary["failed"] = count
            
            return summary
            
        except sqlite3.Error as e:
            logger.error(f"Failed to get user summary: {e}")
            return {"user_id": user_id, "error": str(e)}
    
    def get_statistics(self) -> Dict:
        """
        Get overall statistics from inventory.
        
        Returns:
            Statistics dictionary
        """
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Get overall stats
            cursor.execute('''
                SELECT status, COUNT(*), SUM(file_size)
                FROM inventory GROUP BY status
            ''')
            
            results = cursor.fetchall()
            
            # Get unique users and meetings
            cursor.execute('SELECT COUNT(DISTINCT user_id) FROM inventory')
            unique_users = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(DISTINCT meeting_id) FROM inventory')
            unique_meetings = cursor.fetchone()[0]
            
            conn.close()
            
            stats = {
                "total_files": 0,
                "downloaded": 0,
                "failed": 0,
                "total_size": 0,
                "unique_users": unique_users,
                "unique_meetings": unique_meetings
            }
            
            for status, count, size in results:
                stats["total_files"] += count
                stats["total_size"] += size or 0
                
                if status == "success":
                    stats["downloaded"] = count
                elif status == "failed":
                    stats["failed"] = count
            
            return stats
            
        except sqlite3.Error as e:
            logger.error(f"Failed to get statistics: {e}")
            return {"error": str(e)}
