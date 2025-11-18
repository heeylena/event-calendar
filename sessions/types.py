"""
Data types and constants for the session booking system.

This module contains:
- DTOs (Data Transfer Objects) for service layer operations
- Constants used across the application
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime, date, time


DEFAULT_DAYS_AHEAD = 7


@dataclass
class PatternUpdateData:
    """DTO for pattern update operations."""
    title: Optional[str] = None
    description: Optional[str] = None
    time_of_day: Optional[time] = None
    duration_minutes: Optional[int] = None
    end_date: Optional[date] = None
    is_active: Optional[bool] = None


@dataclass
class OccurrenceUpdateData:
    """DTO for occurrence update operations."""
    title: Optional[str] = None
    description: Optional[str] = None
    start_datetime: Optional[datetime] = None
    duration_minutes: Optional[int] = None
