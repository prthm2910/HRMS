"""
AI Services - Validation Schemas

Pydantic models for validating AI service inputs and outputs.
"""

from apps.ai_services.schemas.ocr import HolidayExtraction, BulkHolidayExtraction

__all__ = ['HolidayExtraction', 'BulkHolidayExtraction']
