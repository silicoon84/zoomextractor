"""
Zoom S2S OAuth Authentication Module

Handles OAuth token acquisition, caching, and refresh for Zoom Server-to-Server apps.
"""

import os
import json
import time
import base64
import requests
import logging
from typing import Dict, Optional, Tuple
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ZoomAuth:
    """Handles Zoom S2S OAuth authentication with automatic token refresh."""
    
    def __init__(self, account_id: str, client_id: str, client_secret: str, 
                 cache_dir: Optional[str] = None):
        """
        Initialize Zoom authentication.
        
        Args:
            account_id: Zoom account ID
            client_id: OAuth client ID
            client_secret: OAuth client secret
            cache_dir: Directory to cache tokens (defaults to ~/.zoom_extractor)
        """
        self.account_id = account_id
        self.client_id = client_id
        self.client_secret = client_secret
        
        # Set up cache directory
        if cache_dir is None:
            cache_dir = Path.home() / '.zoom_extractor'
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.token_cache_file = self.cache_dir / 'token_cache.json'
        self._token_cache: Dict = {}
        
        # Load existing token cache
        self._load_token_cache()
    
    def _load_token_cache(self) -> None:
        """Load token cache from disk."""
        try:
            if self.token_cache_file.exists():
                with open(self.token_cache_file, 'r') as f:
                    self._token_cache = json.load(f)
                logger.debug("Loaded token cache from disk")
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load token cache: {e}")
            self._token_cache = {}
    
    def _save_token_cache(self) -> None:
        """Save token cache to disk."""
        try:
            with open(self.token_cache_file, 'w') as f:
                json.dump(self._token_cache, f, indent=2)
            logger.debug("Saved token cache to disk")
        except IOError as e:
            logger.error(f"Failed to save token cache: {e}")
    
    def _is_token_valid(self, token_data: Dict) -> bool:
        """
        Check if a token is still valid.
        
        Args:
            token_data: Token data dictionary
            
        Returns:
            True if token is valid, False otherwise
        """
        if not token_data:
            return False
        
        expires_at = token_data.get('expires_at', 0)
        # Refresh token 5 minutes before expiry
        return time.time() < (expires_at - 300)
    
    def _generate_jwt_token(self) -> str:
        """
        Generate JWT token for S2S OAuth.
        
        Returns:
            JWT token string
        """
        import jwt
        
        # JWT header
        header = {
            "alg": "HS256",
            "typ": "JWT"
        }
        
        # JWT payload
        now = int(time.time())
        payload = {
            "iss": self.client_id,
            "exp": now + 3600,  # 1 hour expiry
            "aud": "zoom",
            "iat": now,
            "account_id": self.account_id
        }
        
        # Encode JWT
        token = jwt.encode(payload, self.client_secret, algorithm="HS256", headers=header)
        return token
    
    def get_access_token(self) -> str:
        """
        Get a valid access token, refreshing if necessary.
        
        Returns:
            Valid access token
            
        Raises:
            Exception: If token acquisition fails
        """
        # Check if we have a valid cached token
        cached_token = self._token_cache.get('access_token')
        if cached_token and self._is_token_valid(self._token_cache):
            logger.debug("Using cached access token")
            return cached_token
        
        logger.info("Acquiring new access token")
        
        # Generate JWT for authentication
        jwt_token = self._generate_jwt_token()
        
        # Request access token
        url = "https://zoom.us/oauth/token"
        headers = {
            "Authorization": f"Basic {base64.b64encode(f'{self.client_id}:{self.client_secret}'.encode()).decode()}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "grant_type": "account_credentials",
            "account_id": self.account_id
        }
        
        try:
            response = requests.post(url, headers=headers, data=data, timeout=30)
            response.raise_for_status()
            
            token_data = response.json()
            access_token = token_data['access_token']
            expires_in = token_data.get('expires_in', 3600)
            
            # Cache the token
            self._token_cache = {
                'access_token': access_token,
                'expires_at': time.time() + expires_in,
                'acquired_at': time.time()
            }
            self._save_token_cache()
            
            logger.info("Successfully acquired new access token")
            return access_token
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to acquire access token: {e}")
            raise Exception(f"Token acquisition failed: {e}")
        except KeyError as e:
            logger.error(f"Invalid token response format: {e}")
            raise Exception(f"Invalid token response: missing {e}")
    
    def get_auth_headers(self) -> Dict[str, str]:
        """
        Get authorization headers with valid access token.
        
        Returns:
            Dictionary with Authorization header
        """
        token = self.get_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def clear_cache(self) -> None:
        """Clear the token cache."""
        self._token_cache = {}
        try:
            if self.token_cache_file.exists():
                self.token_cache_file.unlink()
            logger.info("Cleared token cache")
        except IOError as e:
            logger.warning(f"Failed to clear token cache file: {e}")


def get_auth_from_env() -> ZoomAuth:
    """
    Create ZoomAuth instance from environment variables.
    
    Returns:
        ZoomAuth instance
        
    Raises:
        ValueError: If required environment variables are missing
    """
    account_id = os.getenv('ZOOM_ACCOUNT_ID')
    client_id = os.getenv('ZOOM_CLIENT_ID')
    client_secret = os.getenv('ZOOM_CLIENT_SECRET')
    
    if not all([account_id, client_id, client_secret]):
        missing = [var for var, value in [
            ('ZOOM_ACCOUNT_ID', account_id),
            ('ZOOM_CLIENT_ID', client_id),
            ('ZOOM_CLIENT_SECRET', client_secret)
        ] if not value]
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
    
    return ZoomAuth(account_id, client_id, client_secret)
