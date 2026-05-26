"""
AI Services - Service Layer

This module contains AI service implementations:
- OCR (Optical Character Recognition)
- Future: NLP, Computer Vision, etc.
"""
import logging
logger = logging.getLogger(__name__)
logger.debug("Initializing apps.ai_services.services package")

from apps.ai_services.services.ocr import GeminiOCRService

__all__ = ['GeminiOCRService']
