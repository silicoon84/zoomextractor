"""
Date Window Module

Handles month-by-month date window iteration for Zoom recordings API.
"""

import logging
from typing import Iterator, Tuple, Optional
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)


class DateWindowGenerator:
    """Generates month-by-month date windows for Zoom recordings API."""
    
    def __init__(self, from_date: Optional[str] = None, to_date: Optional[str] = None):
        """
        Initialize date window generator.
        
        Args:
            from_date: Start date in YYYY-MM-DD format (defaults to 30 days ago)
            to_date: End date in YYYY-MM-DD format (defaults to today)
        """
        self.from_date = self._parse_date(from_date) if from_date else self._get_default_from_date()
        self.to_date = self._parse_date(to_date) if to_date else datetime.utcnow()
        
        # Ensure from_date is not after to_date
        if self.from_date > self.to_date:
            raise ValueError("from_date cannot be after to_date")
        
        logger.info(f"Date range: {self.from_date.strftime('%Y-%m-%d')} to {self.to_date.strftime('%Y-%m-%d')}")
    
    def _parse_date(self, date_string: str) -> datetime:
        """
        Parse date string in YYYY-MM-DD format.
        
        Args:
            date_string: Date string to parse
            
        Returns:
            Parsed datetime object
            
        Raises:
            ValueError: If date format is invalid
        """
        try:
            return datetime.strptime(date_string.strip(), "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Invalid date format: {date_string}. Expected YYYY-MM-DD")
    
    def _get_default_from_date(self) -> datetime:
        """Get default from_date (30 days ago)."""
        return datetime.utcnow() - timedelta(days=30)
    
    def generate_monthly_windows(self) -> Iterator[Tuple[datetime, datetime]]:
        """
        Generate month-by-month date windows.
        
        Yields:
            Tuples of (start_date, end_date) for each month
        """
        current_start = self.from_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        while current_start <= self.to_date:
            # Calculate end of month for current window
            next_month = current_start + relativedelta(months=1)
            window_end = min(next_month - timedelta(days=1), self.to_date)
            
            # Ensure we don't go beyond to_date
            if current_start > self.to_date:
                break
            
            # Set end time to 23:59:59 for the last day
            window_end = window_end.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            logger.debug(f"Generated window: {current_start.strftime('%Y-%m-%d %H:%M:%S')} to {window_end.strftime('%Y-%m-%d %H:%M:%S')}")
            
            yield (current_start, window_end)
            
            # Move to next month
            current_start = next_month
    
    def get_total_months(self) -> int:
        """
        Get total number of months in the date range.
        
        Returns:
            Number of months
        """
        start = self.from_date.replace(day=1)
        end = self.to_date.replace(day=1)
        
        months = 0
        current = start
        while current <= end:
            months += 1
            current += relativedelta(months=1)
        
        return months
    
    def get_current_window_info(self) -> Tuple[int, int]:
        """
        Get current window information for progress tracking.
        
        Returns:
            Tuple of (current_window, total_windows)
        """
        total_months = self.get_total_months()
        current_month = 1
        
        for window_start, window_end in self.generate_monthly_windows():
            if window_start <= datetime.utcnow() <= window_end:
                return (current_month, total_months)
            current_month += 1
        
        return (total_months, total_months)


def parse_date_range(from_date: Optional[str] = None, to_date: Optional[str] = None) -> DateWindowGenerator:
    """
    Parse date range from environment variables or command line arguments.
    
    Args:
        from_date: Start date string (YYYY-MM-DD)
        to_date: End date string (YYYY-MM-DD)
        
    Returns:
        DateWindowGenerator instance
    """
    return DateWindowGenerator(from_date, to_date)
