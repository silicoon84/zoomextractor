"""
Zoom Recordings Extractor - Main Orchestrator

Main script that orchestrates the entire extraction process.
"""

import os
import sys
import logging
import click
from typing import List, Optional, Dict, Iterator
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Import our modules
from .auth import ZoomAuth, get_auth_from_env
from .users import UserEnumerator, parse_user_filter
from .dates import DateWindowGenerator, parse_date_range
from .recordings import RecordingsLister
from .downloader import FileDownloader
from .structure import DirectoryStructure
from .state import ExtractionState, InventoryLogger
from .edge_cases import EdgeCaseHandler
from .rate_limiter import default_rate_limiter

# Load environment variables
load_dotenv()

# Configure logging
def setup_logging(log_level: str, log_file: Optional[str] = None) -> None:
    """Setup logging configuration."""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Set log level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configure root logger
    logging.basicConfig(
        level=numeric_level,
        format=log_format,
        handlers=[]
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_formatter = logging.Formatter(log_format)
    console_handler.setFormatter(console_formatter)
    
    # File handler (if specified)
    handlers = [console_handler]
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_formatter = logging.Formatter(log_format)
        file_handler.setFormatter(file_formatter)
        handlers.append(file_handler)
    
    # Add handlers to root logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    for handler in handlers:
        root_logger.addHandler(handler)


class ZoomExtractor:
    """Main orchestrator class for Zoom recordings extraction."""
    
    def __init__(self, output_dir: str, user_filter: Optional[List[str]] = None,
                 from_date: Optional[str] = None, to_date: Optional[str] = None,
                 max_concurrent: int = 2, include_trash: bool = True,
                 dry_run: bool = False):
        """
        Initialize Zoom extractor.
        
        Args:
            output_dir: Output directory for recordings
            user_filter: List of user emails/IDs to filter by
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            max_concurrent: Maximum concurrent downloads
            include_trash: Whether to include recordings in trash
            dry_run: If True, don't actually download files
        """
        self.output_dir = Path(output_dir)
        self.user_filter = user_filter
        self.from_date = from_date
        self.to_date = to_date
        self.max_concurrent = max_concurrent
        self.include_trash = include_trash
        self.dry_run = dry_run
        
        # Initialize components
        self.auth = get_auth_from_env()
        self.auth_headers = self.auth.get_auth_headers()
        
        self.user_enumerator = UserEnumerator(self.auth_headers)
        self.date_generator = DateWindowGenerator(from_date, to_date)
        self.recordings_lister = RecordingsLister(self.auth_headers)
        self.downloader = FileDownloader(self.auth_headers, max_concurrent)
        self.structure = DirectoryStructure(str(self.output_dir))
        self.edge_handler = EdgeCaseHandler(self.auth_headers)
        
        # State management
        self.state = ExtractionState(self.structure.get_state_file_path())
        self.inventory = InventoryLogger(self.structure.get_inventory_log_path())
        
        self.logger = logging.getLogger(__name__)
    
    def extract_all_recordings(self) -> Dict:
        """
        Extract all recordings according to configuration.
        
        Returns:
            Summary of extraction results
        """
        self.logger.info("Starting Zoom recordings extraction")
        
        try:
            # Get all users (active + inactive for comprehensive coverage)
            active_users = list(self.user_enumerator.list_all_users(self.user_filter, user_type="active"))
            inactive_users = list(self.user_enumerator.list_all_users(self.user_filter, user_type="inactive"))
            
            users = active_users + inactive_users
            self.logger.info(f"Found {len(active_users)} active users and {len(inactive_users)} inactive users ({len(users)} total)")
            
            if not users:
                self.logger.warning("No users found to process")
                return {"error": "No users found"}
            
            # Set totals for progress tracking
            total_meetings = 0
            total_files = 0
            
            # Count total meetings and files (for progress tracking)
            for user in users:
                user_id = user["id"]
                user_email = user.get("email", "unknown")
                
                self.logger.info(f"Counting recordings for user: {user_email}")
                
                for start_date, end_date in self.date_generator.generate_monthly_windows():
                    try:
                        meetings = list(self.recordings_lister.list_user_recordings(
                            user_id, start_date, end_date, self.include_trash
                        ))
                        total_meetings += len(meetings)
                        
                        for meeting in meetings:
                            total_files += len(meeting.get("processed_files", []))
                    
                    except Exception as e:
                        self.logger.error(f"Failed to count recordings for {user_email}: {e}")
            
            self.state.set_totals(len(users), total_meetings, total_files)
            
            # Process each user and date window
            processed_meetings = 0
            processed_files = 0
            
            for user in users:
                user_id = user["id"]
                user_email = user.get("email", "unknown")
                
                # Skip if user already processed
                if self.state.is_user_processed(user_id):
                    self.logger.info(f"Skipping already processed user: {user_email}")
                    continue
                
                self.logger.info(f"Processing user: {user_email}")
                
                for start_date, end_date in self.date_generator.generate_monthly_windows():
                    window_key = f"{user_id}:{start_date.strftime('%Y-%m-%d')}:{end_date.strftime('%Y-%m-%d')}"
                    
                    # Skip if date window already processed
                    if self.state.is_date_window_processed(user_id, 
                                                          start_date.strftime('%Y-%m-%d'), 
                                                          end_date.strftime('%Y-%m-%d')):
                        self.logger.info(f"Skipping already processed date window: {window_key}")
                        continue
                    
                    self.logger.info(f"Processing date window: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
                    
                    try:
                        meetings = self.recordings_lister.list_user_recordings(
                            user_id, start_date, end_date, self.include_trash
                        )
                        
                        for meeting in meetings:
                            meeting_uuid = meeting.get("uuid")
                            
                            # Skip if meeting already processed
                            if self.state.is_meeting_processed(meeting_uuid):
                                self.logger.info(f"Skipping already processed meeting: {meeting.get('topic', 'Unknown')}")
                                continue
                            
                            # Process meeting
                            result = self._process_meeting(user, meeting, (start_date, end_date))
                            processed_meetings += 1
                            
                            # Update progress
                            if processed_meetings % 10 == 0:
                                self._log_progress()
                    
                    except Exception as e:
                        self.logger.error(f"Failed to process date window for {user_email}: {e}")
                        self.state.add_error({
                            "type": "date_window_error",
                            "user_id": user_id,
                            "window": window_key,
                            "error": str(e)
                        })
                
                # Mark user as processed
                self.state.mark_user_processed(user_id)
            
            # Final summary
            summary = self._generate_summary()
            self.logger.info("Extraction completed")
            return summary
            
        except Exception as e:
            self.logger.error(f"Extraction failed: {e}")
            return {"error": str(e)}
    
    def _process_meeting(self, user: Dict, meeting: Dict, date_window: tuple) -> Dict:
        """
        Process a single meeting and download its recordings.
        
        Args:
            user: User dictionary
            meeting: Meeting dictionary
            date_window: Date window tuple
            
        Returns:
            Processing result dictionary
        """
        meeting_uuid = meeting.get("uuid")
        meeting_topic = meeting.get("topic", "Unknown Meeting")
        
        self.logger.info(f"Processing meeting: {meeting_topic} ({meeting_uuid})")
        
        # Check for edge cases
        warnings = self.edge_handler.check_account_restrictions(user)
        if warnings:
            for warning in warnings:
                self.logger.warning(f"Account restriction warning: {warning}")
        
        meeting_warnings = self.edge_handler.handle_meeting_type_restrictions(meeting)
        if meeting_warnings:
            for warning in meeting_warnings:
                self.logger.warning(f"Meeting restriction warning: {warning}")
        
        # Process each file in the meeting
        file_results = []
        processed_files = meeting.get("processed_files", [])
        
        if not processed_files:
            self.logger.warning(f"No files to download for meeting: {meeting_topic}")
            return {"status": "no_files", "meeting": meeting_topic}
        
        for file_info in processed_files:
            file_id = file_info.get("id")
            
            # Skip if file already processed
            if self.state.is_file_processed(file_id):
                self.logger.info(f"Skipping already processed file: {file_id}")
                continue
            
            # Check if file already exists and is valid
            exists, file_path = self.structure.check_file_exists(user, meeting, file_info)
            if exists:
                self.logger.info(f"File already exists: {file_path}")
                file_results.append((True, {
                    "file_id": file_id,
                    "file_type": file_info.get("file_type"),
                    "file_size": file_path.stat().st_size,
                    "expected_size": file_info.get("file_size"),
                    "sha256": None,  # Would need to calculate
                    "download_url": file_info.get("download_url"),
                    "status": "skipped"
                }))
                self.state.mark_file_processed(file_id, "skipped")
                continue
            
            # Download file
            if not self.dry_run:
                try:
                    success, stats = self.downloader.download_file(
                        file_info, file_path, self.auth.get_access_token()
                    )
                    file_results.append((success, stats))
                    
                    # Log to inventory
                    self.inventory.log_file(user, meeting, file_info, file_path, (success, stats))
                    
                    # Update state
                    status = "downloaded" if success else "failed"
                    self.state.mark_file_processed(file_id, status)
                    
                    if success:
                        self.logger.info(f"Downloaded: {file_path}")
                    else:
                        self.logger.error(f"Failed to download: {file_path}")
                
                except Exception as e:
                    self.logger.error(f"Error downloading file {file_id}: {e}")
                    file_results.append((False, {
                        "file_id": file_id,
                        "file_type": file_info.get("file_type"),
                        "file_size": 0,
                        "expected_size": file_info.get("file_size"),
                        "sha256": None,
                        "download_url": file_info.get("download_url"),
                        "status": "error",
                        "error": str(e)
                    }))
                    self.state.mark_file_processed(file_id, "failed")
            else:
                self.logger.info(f"[DRY RUN] Would download: {file_path}")
                file_results.append((True, {
                    "file_id": file_id,
                    "file_type": file_info.get("file_type"),
                    "file_size": file_info.get("file_size"),
                    "expected_size": file_info.get("file_size"),
                    "sha256": None,
                    "download_url": file_info.get("download_url"),
                    "status": "dry_run"
                }))
        
        # Save meeting metadata
        if not self.dry_run:
            self.structure.save_meeting_metadata(user, meeting, date_window, file_results)
            self.structure.save_files_csv(user, meeting, file_results)
        
        # Mark meeting as processed
        self.state.mark_meeting_processed(meeting_uuid)
        
        return {
            "status": "completed",
            "meeting": meeting_topic,
            "files_processed": len(file_results),
            "files_successful": sum(1 for success, _ in file_results if success)
        }
    
    def _log_progress(self) -> None:
        """Log current progress."""
        summary = self.state.get_progress_summary()
        
        self.logger.info(f"Progress: {summary['files']['downloaded'] + summary['files']['skipped']}/{summary['files']['total']} files processed "
                        f"({summary['files']['progress_percent']:.1f}%)")
    
    def _generate_summary(self) -> Dict:
        """Generate final extraction summary."""
        return self.state.get_progress_summary()


@click.command()
@click.option('--output-dir', '-o', 
              default=lambda: os.getenv('ZOOM_OUTDIR', './zoom_recordings'),
              help='Output directory for recordings')
@click.option('--user-filter', '-u',
              default=lambda: os.getenv('ZOOM_USER_FILTER'),
              help='Comma-separated list of user emails or IDs to filter by')
@click.option('--from-date', '-f',
              default=lambda: os.getenv('ZOOM_FROM'),
              help='Start date (YYYY-MM-DD)')
@click.option('--to-date', '-t',
              default=lambda: os.getenv('ZOOM_TO'),
              help='End date (YYYY-MM-DD)')
@click.option('--max-concurrent', '-c',
              default=int(os.getenv('MAX_CONCURRENT_DOWNLOADS', '2')),
              help='Maximum concurrent downloads')
@click.option('--include-trash', is_flag=True,
              help='Include recordings in trash')
@click.option('--dry-run', is_flag=True,
              help='Don\'t actually download files, just show what would be done')
@click.option('--log-level', '-l',
              default='INFO',
              type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']),
              help='Logging level')
@click.option('--log-file',
              help='Log file path (optional)')
@click.option('--resume', is_flag=True,
              help='Resume previous extraction')
def main(output_dir: str, user_filter: Optional[str], from_date: Optional[str], 
         to_date: Optional[str], max_concurrent: int, include_trash: bool, 
         dry_run: bool, log_level: str, log_file: Optional[str], resume: bool):
    """
    Zoom Recordings Extractor
    
    Extract all cloud recordings from your Zoom account with organized storage,
    resume capability, and rate limiting.
    """
    # Setup logging
    setup_logging(log_level, log_file)
    logger = logging.getLogger(__name__)
    
    try:
        # Parse user filter
        user_filter_list = None
        if user_filter:
            user_filter_list = [email.strip() for email in user_filter.split(',') if email.strip()]
        
        # Initialize extractor
        extractor = ZoomExtractor(
            output_dir=output_dir,
            user_filter=user_filter_list,
            from_date=from_date,
            to_date=to_date,
            max_concurrent=max_concurrent,
            include_trash=include_trash,
            dry_run=dry_run
        )
        
        # Show configuration
        logger.info("=== Zoom Recordings Extractor Configuration ===")
        logger.info(f"Output Directory: {output_dir}")
        logger.info(f"User Filter: {user_filter_list or 'All users'}")
        logger.info(f"Date Range: {from_date or '30 days ago'} to {to_date or 'now'}")
        logger.info(f"Max Concurrent Downloads: {max_concurrent}")
        logger.info(f"Include Trash: {include_trash}")
        logger.info(f"Dry Run: {dry_run}")
        logger.info("================================================")
        
        # Run extraction
        if dry_run:
            logger.info("DRY RUN MODE - No files will be downloaded")
        
        summary = extractor.extract_all_recordings()
        
        # Show final summary
        logger.info("=== Extraction Summary ===")
        if "error" in summary:
            logger.error(f"Extraction failed: {summary['error']}")
            sys.exit(1)
        else:
            logger.info(f"Users processed: {summary['users']['processed']}/{summary['users']['total']}")
            logger.info(f"Meetings processed: {summary['meetings']['processed']}/{summary['meetings']['total']}")
            logger.info(f"Files downloaded: {summary['files']['downloaded']}")
            logger.info(f"Files skipped: {summary['files']['skipped']}")
            logger.info(f"Files failed: {summary['files']['failed']}")
            logger.info(f"Progress: {summary['files']['progress_percent']:.1f}%")
            logger.info(f"Errors encountered: {summary['errors']}")
            logger.info("========================")
    
    except KeyboardInterrupt:
        logger.info("Extraction interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
