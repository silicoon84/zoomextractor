"""
File Download Module

Handles downloading recording files with resume capability, rate limiting, and retry logic.
"""

import os
import hashlib
import logging
import requests
import time
from typing import Dict, Optional, Tuple
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class FileDownloader:
    """Handles downloading files with resume capability and rate limiting."""
    
    def __init__(self, auth_headers: Dict[str, str], max_concurrent: int = 2, 
                 chunk_size: int = 8388608, timeout: int = 300, auth=None):
        """
        Initialize file downloader.
        
        Args:
            auth_headers: Authorization headers for requests
            max_concurrent: Maximum concurrent downloads
            chunk_size: Chunk size for streaming downloads (default 8MB)
            timeout: Request timeout in seconds
            auth: Optional ZoomAuth instance for automatic token refresh
        """
        self.auth_headers = auth_headers
        self.auth = auth
        self.max_concurrent = max_concurrent
        self.chunk_size = chunk_size
        self.timeout = timeout
        self._rate_limit_lock = threading.Lock()
        self._last_request_time = 0
        self._min_request_interval = 0.1  # 100ms between requests
    
    def _get_headers(self) -> Dict[str, str]:
        """Get fresh auth headers, refreshing token if needed."""
        if self.auth:
            return self.auth.get_auth_headers()
        return self.auth_headers
    
    def _apply_rate_limit(self) -> None:
        """Apply rate limiting between requests."""
        with self._rate_limit_lock:
            current_time = time.time()
            time_since_last = current_time - self._last_request_time
            
            if time_since_last < self._min_request_interval:
                sleep_time = self._min_request_interval - time_since_last
                time.sleep(sleep_time)
            
            self._last_request_time = time.time()
    
    def _get_download_url_with_auth(self, download_url: str, access_token: str) -> str:
        """
        Prepare download URL with authentication.
        
        Args:
            download_url: Original download URL
            access_token: OAuth access token
            
        Returns:
            URL with authentication applied
        """
        # Try Authorization header first (preferred method)
        # If that fails, we'll fall back to query parameter
        
        # Check if URL already has query parameters
        parsed_url = urlparse(download_url)
        if parsed_url.query:
            # URL already has query params, append access_token
            separator = "&" if "?" in download_url else "?"
            return f"{download_url}{separator}access_token={access_token}"
        else:
            # No existing query params
            return f"{download_url}?access_token={access_token}"
    
    def _download_with_headers(self, url: str, file_path: Path, expected_size: Optional[int] = None) -> bool:
        """
        Download file using Authorization header (preferred method).
        
        Args:
            url: Download URL
            file_path: Target file path
            expected_size: Expected file size for validation
            
        Returns:
            True if download successful, False otherwise
        """
        try:
            self._apply_rate_limit()
            
            headers = self._get_headers().copy()
            
            # Check if file already exists and get current size for resume
            resume_header = {}
            initial_pos = 0
            if file_path.exists():
                initial_pos = file_path.stat().st_size
                if expected_size and initial_pos == expected_size:
                    logger.debug(f"File {file_path} already exists with correct size, skipping")
                    return True
                if initial_pos > 0:
                    resume_header["Range"] = f"bytes={initial_pos}-"
            
            headers.update(resume_header)
            
            logger.debug(f"Downloading {url} to {file_path} (resume from {initial_pos})")
            
            with requests.get(url, headers=headers, stream=True, timeout=self.timeout) as response:
                # Handle different response codes
                if response.status_code == 206:  # Partial content (resume)
                    logger.debug(f"Resuming download from byte {initial_pos}")
                    mode = "ab"
                elif response.status_code == 200:  # Full content
                    if initial_pos > 0:
                        # Server doesn't support resume, start over
                        logger.warning(f"Server doesn't support resume for {url}, starting over")
                        initial_pos = 0
                    mode = "wb"
                else:
                    logger.error(f"Unexpected response code {response.status_code} for {url}")
                    return False
                
                # Validate content length if provided
                content_length = response.headers.get("content-length")
                if content_length:
                    total_size = int(content_length) + initial_pos
                    if expected_size and total_size != expected_size:
                        logger.warning(f"Size mismatch: expected {expected_size}, got {total_size}")
                
                # Download file
                with open(file_path, mode) as f:
                    for chunk in response.iter_content(chunk_size=self.chunk_size):
                        if chunk:
                            f.write(chunk)
                
                logger.debug(f"Downloaded {url} to {file_path}")
                return True
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download {url} with headers: {e}")
            return False
    
    def _download_with_query_param(self, download_url: str, file_path: Path, 
                                 access_token: str, expected_size: Optional[int] = None) -> bool:
        """
        Download file using access_token query parameter (fallback method).
        
        Args:
            download_url: Original download URL
            file_path: Target file path
            access_token: OAuth access token
            expected_size: Expected file size for validation
            
        Returns:
            True if download successful, False otherwise
        """
        try:
            self._apply_rate_limit()
            
            # Add access_token to URL
            url = self._get_download_url_with_auth(download_url, access_token)
            
            logger.debug(f"Downloading {url} to {file_path} (using query param auth)")
            
            with requests.get(url, stream=True, timeout=self.timeout) as response:
                if response.status_code != 200:
                    logger.error(f"Unexpected response code {response.status_code} for {url}")
                    return False
                
                # Download file
                with open(file_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=self.chunk_size):
                        if chunk:
                            f.write(chunk)
                
                logger.debug(f"Downloaded {url} to {file_path}")
                return True
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download {url} with query param: {e}")
            return False
    
    def download_file(self, file_info: Dict, target_path: Path, access_token: str) -> Tuple[bool, Dict]:
        """
        Download a single file with retry logic and multiple auth methods.
        
        Args:
            file_info: File information dictionary
            target_path: Target file path
            access_token: OAuth access token
            
        Returns:
            Tuple of (success, file_stats)
        """
        download_url = file_info["download_url"]
        expected_size = file_info.get("file_size")
        file_id = file_info.get("id", "unknown")
        
        # Create target directory
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Use temporary file during download
        temp_path = target_path.with_suffix(target_path.suffix + ".part")
        
        # Try Authorization header method first (preferred)
        success = self._download_with_headers(download_url, temp_path, expected_size)
        
        # If that fails, try query parameter method
        if not success:
            logger.warning(f"Header auth failed for {file_id}, trying query param auth")
            success = self._download_with_query_param(download_url, temp_path, access_token, expected_size)
        
        if success:
            # Validate file size
            actual_size = temp_path.stat().st_size
            if expected_size and actual_size != expected_size:
                logger.warning(f"Size mismatch for {file_id}: expected {expected_size}, got {actual_size}")
            
            # Calculate SHA-256 hash
            file_hash = self._calculate_file_hash(temp_path)
            
            # Atomically rename temp file to final name
            if temp_path.exists():
                temp_path.rename(target_path)
            
            # Return success with file stats
            stats = {
                "file_id": file_id,
                "file_type": file_info.get("file_type"),
                "file_size": actual_size,
                "expected_size": expected_size,
                "sha256": file_hash,
                "download_url": download_url,
                "status": "success"
            }
            
            logger.info(f"Successfully downloaded {file_id} ({actual_size} bytes)")
            return True, stats
        
        else:
            # Clean up temp file on failure
            if temp_path.exists():
                temp_path.unlink()
            
            logger.error(f"Failed to download {file_id}")
            return False, {
                "file_id": file_id,
                "file_type": file_info.get("file_type"),
                "file_size": 0,
                "expected_size": expected_size,
                "sha256": None,
                "download_url": download_url,
                "status": "failed"
            }
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """
        Calculate SHA-256 hash of a file.
        
        Args:
            file_path: Path to file
            
        Returns:
            SHA-256 hash as hex string
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    def download_files_concurrent(self, downloads: list, access_token: str) -> list:
        """
        Download multiple files concurrently with rate limiting.
        
        Args:
            downloads: List of (file_info, target_path) tuples
            access_token: OAuth access token
            
        Returns:
            List of download results
        """
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
            # Submit all download tasks
            future_to_download = {
                executor.submit(self.download_file, file_info, target_path, access_token): (file_info, target_path)
                for file_info, target_path in downloads
            }
            
            # Process completed downloads
            for future in as_completed(future_to_download):
                file_info, target_path = future_to_download[future]
                try:
                    success, stats = future.result()
                    results.append((success, stats))
                except Exception as e:
                    logger.error(f"Download task failed for {file_info.get('id', 'unknown')}: {e}")
                    results.append((False, {
                        "file_id": file_info.get("id", "unknown"),
                        "file_type": file_info.get("file_type"),
                        "file_size": 0,
                        "expected_size": file_info.get("file_size"),
                        "sha256": None,
                        "download_url": file_info.get("download_url"),
                        "status": "error",
                        "error": str(e)
                    }))
        
        return results
