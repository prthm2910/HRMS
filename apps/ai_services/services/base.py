"""
AI Services - Base Service Class

Abstract base class for all AI services providing common functionality.
"""
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from datetime import datetime
import time

logger = logging.getLogger(__name__)


class BaseAIService(ABC):
    """
    Abstract base class for AI services.
    
    Provides common functionality like:
    - Input validation
    - Error handling patterns
    - Performance tracking
    - Logging hooks
    """
    
    def __init__(self):
        """Initialize the AI service"""
        self.start_time = None
        self.end_time = None
    
    @abstractmethod
    def process(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Main processing method - must be implemented by subclasses.
        
        Returns:
            dict: Processing results with status, data, and metadata
        """
        pass
    
    def validate_input(self, *args, **kwargs) -> bool:
        """
        Validate input data before processing.
        Override in subclasses for specific validation logic.
        
        Returns:
            bool: True if valid, raises exception if invalid
        """
        return True
    
    def handle_error(self, error: Exception) -> Dict[str, Any]:
        """
        Standardized error handling with low-level details.
        
        Args:
            error: The exception that occurred
            
        Returns:
            dict: Error response with details
        """
        logger.error(f"AI Service Failure | Type: {type(error).__name__} | Details: {str(error)}", exc_info=True)
        return {
            'status': 'FAILED',
            'error': str(error),
            'error_type': type(error).__name__,
            'processing_time_ms': self.get_processing_time()
        }
    
    def start_timer(self):
        """Start performance timer"""
        self.start_time = time.time()
    
    def stop_timer(self):
        """Stop performance timer and log duration"""
        self.end_time = time.time()
        logger.debug(f"Operation internal timer stopped. Execution duration: {self.get_processing_time()}ms")
    
    def get_processing_time(self) -> int:
        """
        Get processing time in milliseconds.
        
        Returns:
            int: Processing time in milliseconds, or 0 if timer not started
        """
        if self.start_time and self.end_time:
            return int((self.end_time - self.start_time) * 1000)
        return 0
    
    def get_processing_time_seconds(self):
        """
        Get processing time in seconds as Decimal.
        
        Returns:
            Decimal: Processing time in seconds (e.g., 1.245)
        """
        from decimal import Decimal
        if self.start_time and self.end_time:
            time_diff = self.end_time - self.start_time
            return Decimal(str(round(time_diff, 3)))
        return Decimal('0.000')
    
    def log_operation(self, operation_type: str, user, input_data: Dict, 
                     output_data: Optional[Dict], status: str, model_used: str,
                     processing_time_ms: int, error_message: Optional[str] = None, 
                     user_agent: Optional[str] = None, path: Optional[str] = None):
        """
        Log AI operation to centralized audit system.
        
        This method integrates with apps.audit to provide unified audit logging
        for all AI service operations across the application.
        
        Args:
            operation_type: Type of AI operation (e.g., 'OCR', 'NLP', 'VISION')
            user: Django User object who initiated the operation
            input_data: Summary of input data (dict)
            output_data: Summary of output data (dict)
            status: Operation status ('SUCCESS', 'FAILED', 'PENDING')
            model_used: AI model identifier (e.g., 'gemini-1.5-flash')
            processing_time_ms: Processing time in milliseconds
            error_message: Error message if operation failed
            user_agent: User agent string from request
            path: Request path from request
        """
        from apps.audit.utils import log_ai_operation
        from decimal import Decimal
        
        try:
            # Convert milliseconds to seconds for audit storage
            processing_time_seconds = Decimal(str(processing_time_ms / 1000))
            
            log_ai_operation(
                operation_type=operation_type,
                user=user,
                input_data=input_data,
                output_data=output_data,
                status=status,
                processing_time_seconds=processing_time_seconds,
                model_used=model_used,
                error_message=error_message,
                user_agent=user_agent,
                path=path
            )
            logger.debug(f"Audit log created for {operation_type} operation by user {user.username if user else 'System'}")
        except Exception as e:
            # Don't fail the AI operation if audit logging fails
            logger.error(f"Failed to log AI operation to audit system: {str(e)}", exc_info=True)
