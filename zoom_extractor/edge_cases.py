"""
Edge Cases Handling Module

Handles various edge cases and "gotchas" mentioned in the specification.
"""

import logging
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from urllib.parse import quote, urlparse, parse_qs

logger = logging.getLogger(__name__)


class EdgeCaseHandler:
    """Handles various edge cases and special scenarios."""
    
    def __init__(self, auth_headers: Dict[str, str]):
        """
        Initialize edge case handler.
        
        Args:
            auth_headers: Authorization headers for API requests
        """
        self.auth_headers = auth_headers
        self.base_url = "https://api.zoom.us/v2"
    
    def check_recording_in_trash(self, meeting_uuid: str) -> Tuple[bool, Optional[Dict]]:
        """
        Check if a recording is in trash and cannot be downloaded.
        
        Args:
            meeting_uuid: Meeting UUID to check
            
        Returns:
            Tuple of (in_trash, trash_info)
        """
        try:
            # Try to get recording info
            url = f"{self.base_url}/meetings/{meeting_uuid}/recordings"
            response = requests.get(url, headers=self.auth_headers, timeout=30)
            
            if response.status_code == 404:
                # Recording not found, might be in trash
                logger.warning(f"Recording {meeting_uuid} not found, may be in trash")
                return True, {"status": "not_found", "message": "Recording may be in trash"}
            
            elif response.status_code == 200:
                # Recording exists and is accessible
                return False, None
            
            else:
                logger.warning(f"Unexpected status {response.status_code} for recording {meeting_uuid}")
                return False, None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to check trash status for {meeting_uuid}: {e}")
            return False, {"error": str(e)}
    
    def handle_double_encoded_uuid(self, meeting_uuid: str) -> str:
        """
        Handle double URL encoding for UUIDs containing forward slashes.
        
        Args:
            meeting_uuid: Original meeting UUID
            
        Returns:
            Double-encoded UUID if needed
        """
        if "/" in meeting_uuid:
            # Double URL encode UUIDs containing forward slashes
            double_encoded = quote(quote(meeting_uuid, safe=""), safe="")
            logger.debug(f"Double-encoded UUID: {meeting_uuid} -> {double_encoded}")
            return double_encoded
        
        return meeting_uuid
    
    def check_download_auth_methods(self, download_url: str, access_token: str) -> Tuple[str, str]:
        """
        Determine the best authentication method for download URL.
        
        Args:
            download_url: Original download URL
            access_token: OAuth access token
            
        Returns:
            Tuple of (method, url) where method is 'header' or 'query_param'
        """
        # Check if URL already has query parameters
        parsed_url = urlparse(download_url)
        
        if parsed_url.query:
            # URL has existing query params, use Authorization header
            return "header", download_url
        else:
            # No existing query params, can use either method
            # Prefer Authorization header, but query param is fallback
            return "header", download_url
    
    def handle_passcode_protected_recording(self, download_url: str, access_token: str) -> Optional[str]:
        """
        Handle recordings that require passcode authentication.
        
        Args:
            download_url: Download URL
            access_token: OAuth access token
            
        Returns:
            Modified download URL or None if handling failed
        """
        try:
            # First, try with Authorization header
            headers = self.auth_headers.copy()
            response = requests.head(download_url, headers=headers, timeout=30, allow_redirects=True)
            
            # Check if we get redirected to a passcode page
            final_url = response.url
            if "passcode" in final_url.lower() or "auth" in final_url.lower():
                logger.warning(f"Recording may require passcode: {final_url}")
                
                # Try with access_token as query parameter
                if "?" in download_url:
                    modified_url = f"{download_url}&access_token={access_token}"
                else:
                    modified_url = f"{download_url}?access_token={access_token}"
                
                return modified_url
            
            return download_url
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to check passcode protection: {e}")
            return download_url
    
    def check_recording_retention_policy(self, meeting_start_time: str) -> Tuple[bool, Optional[str]]:
        """
        Check if recording might be affected by retention policy.
        
        Args:
            meeting_start_time: Meeting start time string
            
        Returns:
            Tuple of (might_be_deleted, warning_message)
        """
        try:
            # Parse meeting start time
            if meeting_start_time.endswith('Z'):
                meeting_time = datetime.fromisoformat(meeting_start_time[:-1])
            else:
                meeting_time = datetime.fromisoformat(meeting_start_time)
            
            # Check if recording is older than 1 year (common retention period)
            one_year_ago = datetime.utcnow() - timedelta(days=365)
            
            if meeting_time < one_year_ago:
                warning_msg = f"Recording from {meeting_time.strftime('%Y-%m-%d')} may be affected by retention policy"
                logger.warning(warning_msg)
                return True, warning_msg
            
            return False, None
            
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse meeting start time {meeting_start_time}: {e}")
            return False, None
    
    def validate_recording_file(self, file_info: Dict) -> Tuple[bool, Optional[str]]:
        """
        Validate recording file information for common issues.
        
        Args:
            file_info: File information dictionary
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check required fields
        if not file_info.get("download_url"):
            return False, "Missing download_url"
        
        if not file_info.get("file_type"):
            return False, "Missing file_type"
        
        # Check file size
        file_size = file_info.get("file_size", 0)
        if file_size == 0:
            logger.warning(f"File {file_info.get('id', 'unknown')} has zero size")
        
        # Check file status
        status_raw = file_info.get("status", "")
        status = str(status_raw).lower() if status_raw else ""
        if status == "processing":
            return False, "File is still processing"
        
        # Validate download URL
        download_url = file_info.get("download_url")
        try:
            parsed_url = urlparse(download_url)
            if not parsed_url.scheme or not parsed_url.netloc:
                return False, f"Invalid download URL: {download_url}"
        except Exception as e:
            return False, f"Invalid download URL format: {e}"
        
        return True, None
    
    def handle_concurrent_download_limit(self, current_downloads: int, max_concurrent: int) -> int:
        """
        Handle concurrent download limits to avoid 429 errors.
        
        Args:
            current_downloads: Current number of active downloads
            max_concurrent: Maximum concurrent downloads allowed
            
        Returns:
            Recommended delay in seconds before starting next download
        """
        if current_downloads >= max_concurrent:
            # Calculate delay based on current load
            delay = min(5.0, current_downloads * 0.5)
            logger.debug(f"Rate limiting: {current_downloads}/{max_concurrent} downloads active, waiting {delay}s")
            return delay
        
        return 0
    
    def check_account_restrictions(self, user_info: Dict) -> List[str]:
        """
        Check for account-level restrictions that might affect downloads.
        
        Args:
            user_info: User information dictionary
            
        Returns:
            List of restriction warnings
        """
        warnings = []
        
        # Check user type
        user_type_raw = user_info.get("type", "")
        user_type = str(user_type_raw).lower() if user_type_raw else ""
        if user_type == "basic":
            warnings.append("User has basic account type, may have recording limitations")
        
        # Check user status
        status_raw = user_info.get("status", "")
        status = str(status_raw).lower() if status_raw else ""
        if status != "active":
            warnings.append(f"User status is '{status}', may affect recording access")
        
        # Check role
        role_name_raw = user_info.get("role_name", "")
        role_name = str(role_name_raw).lower() if role_name_raw else ""
        if "admin" not in role_name and "owner" not in role_name:
            warnings.append("User may not have admin privileges for downloading recordings")
        
        return warnings
    
    def handle_meeting_type_restrictions(self, meeting_info: Dict) -> List[str]:
        """
        Check for meeting type restrictions that might affect downloads.
        
        Args:
            meeting_info: Meeting information dictionary
            
        Returns:
            List of restriction warnings
        """
        warnings = []
        
        # Check meeting type
        meeting_type_raw = meeting_info.get("type", "")
        meeting_type = str(meeting_type_raw).lower() if meeting_type_raw else ""
        if meeting_type == "webinar":
            warnings.append("Webinar recordings may have different access restrictions")
        
        # Check recording settings
        recording_count = meeting_info.get("recording_count", 0)
        if recording_count == 0:
            warnings.append("No recordings found for this meeting")
        
        # Check meeting duration
        duration = meeting_info.get("duration", 0)
        if duration < 1:
            warnings.append("Meeting duration is very short, may not have recordings")
        
        return warnings
    
    def get_download_fallback_options(self, download_url: str, access_token: str) -> List[Dict]:
        """
        Get fallback options for download if primary method fails.
        
        Args:
            download_url: Original download URL
            access_token: OAuth access token
            
        Returns:
            List of fallback download options
        """
        options = []
        
        # Option 1: Authorization header (preferred)
        options.append({
            "method": "header",
            "url": download_url,
            "headers": self.auth_headers,
            "description": "Authorization header method"
        })
        
        # Option 2: Query parameter
        if "?" in download_url:
            fallback_url = f"{download_url}&access_token={access_token}"
        else:
            fallback_url = f"{download_url}?access_token={access_token}"
        
        options.append({
            "method": "query_param",
            "url": fallback_url,
            "headers": {"User-Agent": "Zoom-Extractor/1.0"},
            "description": "Query parameter method"
        })
        
        return options
    
    def log_edge_case(self, case_type: str, details: Dict) -> None:
        """
        Log edge case occurrence for analysis.
        
        Args:
            case_type: Type of edge case
            details: Details about the edge case
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "case_type": case_type,
            "details": details
        }
        
        logger.info(f"Edge case detected: {case_type} - {details}")
        
        # Could also write to a dedicated edge cases log file
        # This helps with troubleshooting and improving the extractor
