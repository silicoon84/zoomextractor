"""
Rate Limiting and Retry Logic Module

Handles rate limiting, exponential backoff, and retry logic for API calls.
"""

import time
import logging
import requests
from typing import Dict, Optional, Callable, Any
from functools import wraps
import random

logger = logging.getLogger(__name__)


class RateLimiter:
    """Handles rate limiting with exponential backoff and jitter."""
    
    def __init__(self, base_delay: float = 1.0, max_delay: float = 60.0, 
                 backoff_factor: float = 2.0, jitter: bool = True):
        """
        Initialize rate limiter.
        
        Args:
            base_delay: Base delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
            backoff_factor: Factor to multiply delay by on each retry
            jitter: Whether to add random jitter to delays
        """
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
    
    def get_delay(self, attempt: int) -> float:
        """
        Calculate delay for given attempt number.
        
        Args:
            attempt: Attempt number (0-based)
            
        Returns:
            Delay in seconds
        """
        delay = self.base_delay * (self.backoff_factor ** attempt)
        delay = min(delay, self.max_delay)
        
        if self.jitter:
            # Add ±25% jitter
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)
        
        return max(0, delay)
    
    def sleep(self, attempt: int) -> None:
        """
        Sleep for the calculated delay.
        
        Args:
            attempt: Attempt number (0-based)
        """
        delay = self.get_delay(attempt)
        if delay > 0:
            logger.debug(f"Rate limiting: sleeping for {delay:.2f} seconds (attempt {attempt + 1})")
            time.sleep(delay)


class RetryHandler:
    """Handles retry logic for API calls with rate limiting."""
    
    def __init__(self, max_retries: int = 5, rate_limiter: Optional[RateLimiter] = None):
        """
        Initialize retry handler.
        
        Args:
            max_retries: Maximum number of retry attempts
            rate_limiter: Rate limiter instance (creates default if None)
        """
        self.max_retries = max_retries
        self.rate_limiter = rate_limiter or RateLimiter()
    
    def should_retry(self, response: requests.Response, exception: Optional[Exception] = None) -> bool:
        """
        Determine if a request should be retried.
        
        Args:
            response: HTTP response object
            exception: Exception that occurred (if any)
            
        Returns:
            True if request should be retried
        """
        # Retry on network exceptions
        if exception is not None:
            return isinstance(exception, (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.RequestException
            ))
        
        # Retry on specific HTTP status codes
        if response.status_code in [429, 500, 502, 503, 504]:
            return True
        
        # Retry on rate limiting
        if response.status_code == 429:
            return True
        
        return False
    
    def get_retry_after(self, response: requests.Response) -> Optional[float]:
        """
        Extract Retry-After header value.
        
        Args:
            response: HTTP response object
            
        Returns:
            Retry-After value in seconds, or None if not present
        """
        retry_after = response.headers.get('Retry-After')
        if retry_after:
            try:
                # Retry-After can be either seconds (int) or HTTP date
                if retry_after.isdigit():
                    return float(retry_after)
                else:
                    # Parse HTTP date (RFC 2822)
                    from email.utils import parsedate_to_datetime
                    retry_time = parsedate_to_datetime(retry_after)
                    return (retry_time.timestamp() - time.time())
            except (ValueError, TypeError):
                logger.warning(f"Invalid Retry-After header: {retry_after}")
        
        return None
    
    def retry_request(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function with retry logic.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If all retries are exhausted
        """
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                response = func(*args, **kwargs)
                
                # Check if we should retry
                if not self.should_retry(response):
                    return response
                
                # Check for rate limiting with Retry-After header
                if response.status_code == 429:
                    retry_after = self.get_retry_after(response)
                    if retry_after and retry_after > 0:
                        logger.warning(f"Rate limited, waiting {retry_after:.2f} seconds as requested by server")
                        time.sleep(retry_after)
                        continue
                
                # If this is the last attempt, raise the error
                if attempt == self.max_retries:
                    logger.error(f"Max retries ({self.max_retries}) exceeded")
                    response.raise_for_status()
                
                # Log retry attempt
                logger.warning(f"Request failed with status {response.status_code}, retrying (attempt {attempt + 1}/{self.max_retries})")
                
            except requests.exceptions.RequestException as e:
                last_exception = e
                
                # If this is the last attempt, raise the exception
                if attempt == self.max_retries:
                    logger.error(f"Max retries ({self.max_retries}) exceeded, last error: {e}")
                    raise
                
                # Log retry attempt
                logger.warning(f"Request failed with exception {type(e).__name__}: {e}, retrying (attempt {attempt + 1}/{self.max_retries})")
            
            # Apply rate limiting delay
            self.rate_limiter.sleep(attempt)
        
        # This should never be reached, but just in case
        if last_exception:
            raise last_exception
        
        raise Exception("Unexpected retry logic error")


def with_retry(max_retries: int = 5, rate_limiter: Optional[RateLimiter] = None):
    """
    Decorator for adding retry logic to functions.
    
    Args:
        max_retries: Maximum number of retry attempts
        rate_limiter: Rate limiter instance (creates default if None)
        
    Returns:
        Decorated function
    """
    retry_handler = RetryHandler(max_retries, rate_limiter)
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return retry_handler.retry_request(func, *args, **kwargs)
        return wrapper
    return decorator


class APIClient:
    """API client with built-in rate limiting and retry logic."""
    
    def __init__(self, auth_headers: Dict[str, str], rate_limiter: Optional[RateLimiter] = None):
        """
        Initialize API client.
        
        Args:
            auth_headers: Authorization headers for requests
            rate_limiter: Rate limiter instance (creates default if None)
        """
        self.auth_headers = auth_headers
        self.rate_limiter = rate_limiter or RateLimiter()
        self.retry_handler = RetryHandler(rate_limiter=self.rate_limiter)
    
    @with_retry(max_retries=5)
    def get(self, url: str, params: Optional[Dict] = None, timeout: int = 30) -> requests.Response:
        """
        Make GET request with retry logic.
        
        Args:
            url: Request URL
            params: Query parameters
            timeout: Request timeout
            
        Returns:
            HTTP response
        """
        return requests.get(url, headers=self.auth_headers, params=params, timeout=timeout)
    
    @with_retry(max_retries=5)
    def post(self, url: str, data: Optional[Dict] = None, json: Optional[Dict] = None, 
             timeout: int = 30) -> requests.Response:
        """
        Make POST request with retry logic.
        
        Args:
            url: Request URL
            data: Form data
            json: JSON data
            timeout: Request timeout
            
        Returns:
            HTTP response
        """
        return requests.post(url, headers=self.auth_headers, data=data, json=json, timeout=timeout)
    
    def download_with_retry(self, url: str, stream: bool = True, timeout: int = 300) -> requests.Response:
        """
        Download file with retry logic.
        
        Args:
            url: Download URL
            stream: Whether to stream the response
            timeout: Request timeout
            
        Returns:
            HTTP response
        """
        last_exception = None
        
        for attempt in range(5):  # Max 5 retries for downloads
            try:
                response = requests.get(url, headers=self.auth_headers, stream=stream, timeout=timeout)
                
                # For downloads, we might want to retry on certain status codes
                if response.status_code in [429, 500, 502, 503, 504]:
                    if attempt < 4:  # Don't retry on last attempt
                        logger.warning(f"Download failed with status {response.status_code}, retrying (attempt {attempt + 1}/5)")
                        self.rate_limiter.sleep(attempt)
                        continue
                
                return response
                
            except requests.exceptions.RequestException as e:
                last_exception = e
                if attempt < 4:  # Don't retry on last attempt
                    logger.warning(f"Download failed with exception {type(e).__name__}: {e}, retrying (attempt {attempt + 1}/5)")
                    self.rate_limiter.sleep(attempt)
                else:
                    logger.error(f"Download failed after 5 attempts: {e}")
                    raise
        
        if last_exception:
            raise last_exception
        
        raise Exception("Unexpected download retry logic error")


# Global rate limiter instance
default_rate_limiter = RateLimiter(
    base_delay=1.0,
    max_delay=60.0,
    backoff_factor=2.0,
    jitter=True
)
