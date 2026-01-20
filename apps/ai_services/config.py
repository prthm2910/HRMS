"""
AI Services Configuration

Centralized configuration for all AI services (OCR, NLP, Vision, etc.)
"""
from django.conf import settings


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
        return {
            'api_key': settings.GEMINI_API_KEY,
            'model': getattr(settings, 'GEMINI_MODEL', 'gemini-3-flash-preview'),
            'timeout': getattr(settings, 'GEMINI_TIMEOUT', 30),
        }
    
    @staticmethod
    def get_ocr_config():
        """
        Get OCR-specific configuration.
        
        Returns:
            dict: OCR configuration including supported formats and max file size
        """
        return {
            'supported_formats': ['image/jpeg', 'image/png', 'image/jpg'],
            'max_file_size_mb': 10,
            'gemini': AIServiceConfig.get_gemini_config(),
        }
    
    # Future: Add configurations for other AI services
    # @staticmethod
    # def get_nlp_config():
    #     """Get NLP service configuration"""
    #     pass
    
    # @staticmethod
    # def get_vision_config():
    #     """Get computer vision service configuration"""
    #     pass
