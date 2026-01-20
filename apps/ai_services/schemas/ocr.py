"""
AI Services - OCR Validation Schemas

Pydantic models for validating OCR extracted data.
Moved from apps.holidays.serializers to centralize AI-related validation.
"""
from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import date as date_type


class HolidayExtraction(BaseModel):
    """
    Pydantic model for validating holiday data extracted from images via OCR.
    Used in the extract-from-image endpoint.
    """
    date: date_type
    name: str
    description: Optional[str] = ""
    is_recurring: bool = False
    region: Optional[str] = ""
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate holiday name"""
        if not v or len(v.strip()) < 3:
            raise ValueError('Holiday name must be at least 3 characters long')
        return v.strip().title()
    
    @field_validator('date')
    @classmethod
    def validate_date(cls, v: date_type) -> date_type:
        """Validate that date is in the future (not today or past)"""
        if v <= date_type.today():
            raise ValueError(f'Cannot add holidays for today or past dates. Date {v} must be in the future.')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "date": "2026-08-15",
                "name": "Independence Day",
                "description": "National Holiday",
                "is_recurring": True,
                "region": "All India"
            }
        }


class BulkHolidayExtraction(BaseModel):
    """
    Pydantic model for validating bulk holiday extraction.
    Ensures no duplicate dates within the batch.
    """
    holidays: List[HolidayExtraction]
    
    @field_validator('holidays')
    @classmethod
    def check_duplicates(cls, v: List[HolidayExtraction]) -> List[HolidayExtraction]:
        """Check for duplicate dates in the batch"""
        dates = [h.date for h in v]
        if len(dates) != len(set(dates)):
            raise ValueError('Duplicate dates found in the holiday list')
        return v
    
    @field_validator('holidays')
    @classmethod
    def check_not_empty(cls, v: List[HolidayExtraction]) -> List[HolidayExtraction]:
        """Ensure at least one holiday is provided"""
        if not v or len(v) == 0:
            raise ValueError('At least one holiday must be provided')
        return v
