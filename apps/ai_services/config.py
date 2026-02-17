"""
AI Services Configuration

Centralized configuration for all AI services (OCR, NLP, Vision, etc.)
"""
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class AIServiceConfig:
    """
    Configuration class for AI services.
    Provides centralized access to API keys, model settings, and service parameters.
    """
    
    @staticmethod
    def get_gemini_config():
        """
        Get Gemini AI configuration for OCR and other services.
        
        Returns:
            dict: Configuration dictionary with API key, model name, and timeout
        """
        logger.debug("Gemini Engine Config | Fetching from Django settings.")
        config = {
            'api_key': settings.GEMINI_API_KEY,
            'model': getattr(settings, 'GEMINI_MODEL', 'gemini-1.5-flash'),
            'timeout': getattr(settings, 'GEMINI_TIMEOUT', 30),
        }
        logger.debug(f"Gemini Engine Config | Model: {config['model']} | Timeout: {config['timeout']}s")
        return config
    
    @staticmethod
    def get_ocr_config():
        """
        Get OCR-specific configuration.
        
        Returns:
            dict: OCR configuration including supported formats and max file size
        """
        logger.debug("OCR Service Config | Loading defaults and model settings.")
        config = {
            'supported_formats': ['image/jpeg', 'image/png', 'image/jpg'],
            'max_file_size_mb': 10,
            'gemini': AIServiceConfig.get_gemini_config(),
        }
        logger.info(f"OCR Service Config | Successfully loaded. Max Size: {config['max_file_size_mb']}MB | Supported: {len(config['supported_formats'])} formats")
        return config
