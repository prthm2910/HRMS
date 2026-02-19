"""
AI Services - Validation Schemas

Pydantic models for validating AI service inputs and outputs.
"""
import logging
logger = logging.getLogger(__name__)
logger.debug("Initializing apps.ai_services.schemas package")

from apps.ai_services.schemas.ocr import HolidayExtraction, BulkHolidayExtraction

__all__ = ['HolidayExtraction', 'BulkHolidayExtraction']
