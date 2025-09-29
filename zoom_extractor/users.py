"""
User Enumeration Module

Handles listing and filtering Zoom users with pagination support.
"""

import logging
import requests
from typing import List, Dict, Optional, Iterator
from datetime import datetime

logger = logging.getLogger(__name__)


class UserEnumerator:
    """Handles enumeration of Zoom users with pagination and filtering."""
    
    def __init__(self, auth_headers: Dict[str, str]):
        """
        Initialize user enumerator.
        
        Args:
            auth_headers: Authorization headers for API requests
        """
        self.auth_headers = auth_headers
        self.base_url = "https://api.zoom.us/v2"
    
    def list_all_users(self, user_filter: Optional[List[str]] = None, 
                      user_type: str = "active") -> Iterator[Dict]:
        """
        List all users with pagination support.
        
        Args:
            user_filter: Optional list of user emails/IDs to filter by
            user_type: Type of users to list (active, inactive, pending)
            
        Yields:
            User dictionaries from the API
        """
        url = f"{self.base_url}/users"
        params = {
            "page_size": 30,  # Maximum allowed by Zoom API
            "status": user_type
        }
        
        next_page_token = None
        
        while True:
            if next_page_token:
                params["next_page_token"] = next_page_token
            
            logger.debug(f"Fetching users page with params: {params}")
            
            try:
                response = requests.get(url, headers=self.auth_headers, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                users = data.get("users", [])
                
                # Filter users if filter is provided
                if user_filter:
                    users = self._filter_users(users, user_filter)
                
                for user in users:
                    yield user
                
                # Check for next page
                next_page_token = data.get("next_page_token")
                if not next_page_token:
                    break
                    
                logger.debug(f"Found {len(users)} users, continuing to next page")
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to fetch users: {e}")
                raise
    
    def _filter_users(self, users: List[Dict], user_filter: List[str]) -> List[Dict]:
        """
        Filter users based on email or ID.
        
        Args:
            users: List of user dictionaries
            user_filter: List of emails or user IDs to filter by
            
        Returns:
            Filtered list of users
        """
        filtered_users = []
        
        for user in users:
            user_email = user.get("email", "").lower()
            user_id = user.get("id", "")
            
            # Check if user matches any filter criteria
            for filter_item in user_filter:
                filter_item = filter_item.lower().strip()
                if filter_item == user_email or filter_item == user_id:
                    filtered_users.append(user)
                    break
        
        logger.debug(f"Filtered {len(users)} users down to {len(filtered_users)} based on filter")
        return filtered_users
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """
        Get a specific user by email address.
        
        Args:
            email: User email address
            
        Returns:
            User dictionary if found, None otherwise
        """
        try:
            # URL encode the email
            from urllib.parse import quote
            encoded_email = quote(email, safe='')
            
            url = f"{self.base_url}/users/{encoded_email}"
            response = requests.get(url, headers=self.auth_headers, timeout=30)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to get user by email {email}: {e}")
            return None
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """
        Get a specific user by user ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User dictionary if found, None otherwise
        """
        try:
            url = f"{self.base_url}/users/{user_id}"
            response = requests.get(url, headers=self.auth_headers, timeout=30)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to get user by ID {user_id}: {e}")
            return None


def parse_user_filter(filter_string: Optional[str]) -> Optional[List[str]]:
    """
    Parse user filter string from environment variable.
    
    Args:
        filter_string: Comma-separated list of emails or user IDs
        
    Returns:
        List of filter items or None if no filter
    """
    if not filter_string or not filter_string.strip():
        return None
    
    # Split by comma and clean up whitespace
    filters = [item.strip() for item in filter_string.split(',') if item.strip()]
    return filters if filters else None
