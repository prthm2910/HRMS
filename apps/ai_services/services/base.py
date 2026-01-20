"""
AI Services - Base Service Class

Abstract base class for all AI services providing common functionality.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from datetime import datetime
import time


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
        Standardized error handling.
        
        Args:
            error: The exception that occurred
            
        Returns:
            dict: Error response with details
        """
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
        """Stop performance timer"""
        self.end_time = time.time()
    
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
    
    def log_operation(self, operation_type: str, status: str, input_data: Dict, 
                     output_data: Optional[Dict] = None, error_message: Optional[str] = None):
        """
        Log AI operation to audit system.
        
        This method can be overridden to integrate with your audit/logging system.
        
        Args:
            operation_type: Type of AI operation (e.g., 'OCR', 'NLP')
            status: Operation status ('SUCCESS', 'FAILED', 'PENDING')
            input_data: Input data summary
            output_data: Output data summary
            error_message: Error message if failed
        """
        # Future: Integrate with audit system
        # For now, this is a placeholder for logging
        pass
