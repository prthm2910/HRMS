"""
Constants for the holidays app.
Contains all enums used in holiday models.
"""

from apps.base.constants import BaseEnum


class HolidayExtractionStatus(BaseEnum):
    """Status of holiday extraction from uploaded images"""
    SUCCESS = 'SUCCESS'
    FAILED = 'FAILED'
    PENDING = 'PENDING'
