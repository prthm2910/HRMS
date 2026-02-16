"""
AI Services - OCR Service

Gemini AI-based OCR service for extracting structured data from images.
"""
import google.generativeai as genai
import json
from typing import Dict, Any, List, Optional
from apps.ai_services.services.base import BaseAIService
from apps.ai_services.config import AIServiceConfig
from apps.ai_services.schemas.ocr import HolidayExtraction
from apps.audit.constants import AIOperationType, AIOperationLogStatus


class GeminiOCRService(BaseAIService):
    """
    OCR service using Google Gemini AI for extracting holidays from images.
    
    This service handles:
    - Image processing via Gemini AI
    - Prompt engineering for holiday extraction
    - JSON parsing and validation
    - Error handling and logging
    """
    
    def __init__(self):
        """Initialize the Gemini OCR service"""
        super().__init__()
        self.config = AIServiceConfig.get_ocr_config()
        self._configure_gemini()
    
    def _configure_gemini(self):
        """Configure Gemini AI with API key"""
        gemini_config = self.config['gemini']
        genai.configure(api_key=gemini_config['api_key'])
        self.model = genai.GenerativeModel(gemini_config['model'])
    
    def extract_holidays_from_image(self, image_file, user=None, user_agent=None, path=None) -> Dict[str, Any]:
        """
        Extract holiday data from an uploaded image.
        
        Args:
            image_file: Django UploadedFile object
            user: User who initiated the request (for logging)
            user_agent: User agent string (for logging)
            path: Request path (for logging)
            
        Returns:
            dict: Result containing extracted holidays, status, and metadata
        """
        self.start_timer()
        
        try:
            # Validate input
            self.validate_input(image_file=image_file)
            
            # Read image data
            image_data = image_file.read()
            
            # Generate prompt
            prompt = self._generate_prompt()
            
            # Call Gemini API
            response = self.model.generate_content([
                prompt,
                {"mime_type": image_file.content_type, "data": image_data}
            ])
            
            # Parse response
            extracted_data = self._parse_response(response.text)
            
            # Validate extracted data
            all_holidays, has_errors = self._validate_extracted_data(extracted_data)
            
            self.stop_timer()
            
            result = {
                'status': AIOperationLogStatus.SUCCESS.value,
                'extracted_holidays': all_holidays,
                'total_count': len(all_holidays),
                'has_validation_errors': has_errors,
                'processing_time_ms': self.get_processing_time(),
                'model_used': self.config['gemini']['model']
            }
            
            # Log to audit system
            if user:
                self._log_to_audit(
                    user=user,
                    input_data={'image_name': image_file.name, 'size_bytes': image_file.size},
                    output_data={'holidays_count': len(all_holidays), 'has_errors': has_errors},
                    status=AIOperationLogStatus.SUCCESS.value,
                    processing_time_ms=self.get_processing_time(),
                    user_agent=user_agent,
                    path=path
                )
            
            return result
            
        except Exception as e:
            self.stop_timer()
            error_result = self.handle_error(e)
            
            # Log failure to audit system
            if user:
                self._log_to_audit(
                    user=user,
                    input_data={'image_name': image_file.name if image_file else 'unknown'},
                    output_data=None,
                    status=AIOperationLogStatus.FAILED.value,
                    processing_time_ms=self.get_processing_time(),
                    error_message=str(e),
                    user_agent=user_agent,
                    path=path
                )
            
            return error_result
    
    def validate_input(self, image_file=None, **kwargs) -> bool:
        """
        Validate image file before processing.
        
        Args:
            image_file: Uploaded image file
            
        Returns:
            bool: True if valid
            
        Raises:
            ValueError: If validation fails
        """
        if not image_file:
            raise ValueError("No image file provided")
        
        # Check file type
        if image_file.content_type not in self.config['supported_formats']:
            raise ValueError(
                f"Unsupported file format: {image_file.content_type}. "
                f"Supported formats: {', '.join(self.config['supported_formats'])}"
            )
        
        # Check file size
        max_size_bytes = self.config['max_file_size_mb'] * 1024 * 1024
        if image_file.size > max_size_bytes:
            raise ValueError(
                f"File size ({image_file.size / 1024 / 1024:.2f} MB) exceeds "
                f"maximum allowed size ({self.config['max_file_size_mb']} MB)"
            )
        
        return True
    
    def _generate_prompt(self) -> str:
        """
        Generate the prompt for Gemini AI to extract holiday data.
        
        Returns:
            str: Formatted prompt
        """
        return """
Analyze this handwritten or printed holiday list image and extract the following information for each holiday:

* Date (in YYYY-MM-DD format)
* Holiday name
* Type or description (if mentioned)
* Is it recurring yearly? (true/false as boolean)
* Region (if mentioned, e.g., Mumbai, Bangalore, All India)

Return the data in JSON format as an array of objects with keys: `date`, `name`, `description`, `is_recurring` (boolean), `region`.

**Example output:**

```json
[
  {
    "date": "2026-01-26",
    "name": "Republic Day",
    "description": "National Holiday",
    "is_recurring": true,
    "region": "All India"
  },
  {
    "date": "2026-08-15",
    "name": "Independence Day",
    "description": "",
    "is_recurring": true,
    "region": "All India"
  }
]
```

**Important Instructions:**

1. **Language & Translation:** The handwritten or printed text may be in an **Indian regional language** (e.g., Hindi, Marathi, Gujarati, Tamil, etc.). You **MUST translate** the holiday name and any descriptions into **English** for the JSON output.
2. **Format:** Only return valid JSON, no additional text.
3. **Dates:** Use YYYY-MM-DD format. If the year is not explicitly written on the page, infer it from the context or use the current year.
4. **Recurring:** Set `is_recurring` to boolean `true` or `false` (NOT "yes"/"no"). Use `true` for national holidays or holidays that repeat yearly on the same date.
5. **Region:** If the region is not mentioned, use an empty string "".
        """
    
    def _parse_response(self, response_text: str) -> List[Dict]:
        """
        Parse Gemini AI response and extract JSON.
        
        Args:
            response_text: Raw response from Gemini
            
        Returns:
            list: Parsed JSON data
            
        Raises:
            json.JSONDecodeError: If response is not valid JSON
        """
        # Clean up response text
        response_text = response_text.strip()
        
        # Remove markdown code blocks if present
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.startswith('```'):
            response_text = response_text[3:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        
        response_text = response_text.strip()
        
        # Parse JSON
        return json.loads(response_text)
    
    def _validate_extracted_data(self, extracted_data: List[Dict]) -> tuple:
        """
        Validate extracted data using Pydantic models.
        Returns ALL holidays (valid and invalid) with error markers.
        
        Args:
            extracted_data: List of extracted holiday dictionaries
            
        Returns:
            tuple: (all_holidays_with_errors, has_errors_flag)
        """
        all_holidays = []
        has_errors = False
        
        for idx, holiday_data in enumerate(extracted_data):
            try:
                # Validate each holiday using Pydantic
                holiday = HolidayExtraction(**holiday_data)
                # Convert to dict with JSON-serializable dates
                validated_data = holiday.model_dump(mode='json')
                # Add validation status
                validated_data['validation_error'] = None
                all_holidays.append(validated_data)
            except Exception as e:
                # Keep the invalid data but mark it with error
                has_errors = True
                invalid_data = holiday_data.copy()
                invalid_data['validation_error'] = str(e)
                all_holidays.append(invalid_data)
        
        return all_holidays, has_errors
    
    def _log_to_audit(self, user, input_data, output_data, status, processing_time_ms, 
                     error_message=None, user_agent=None, path=None):
        """
        Log AI operation to audit system.
        
        Args:
            user: Django User object
            input_data: Summary of input data
            output_data: Summary of output data
            status: Operation status
            processing_time_ms: Processing time in milliseconds (will be converted to seconds)
            error_message: Error message if failed
            user_agent: User agent string
            path: Request path
        """
        from apps.audit.utils import log_ai_operation
        from decimal import Decimal
        
        try:
            # Convert milliseconds to seconds
            processing_time_seconds = Decimal(str(processing_time_ms / 1000))
            
            log_ai_operation(
                operation_type=AIOperationType.OCR.value,
                user=user,
                input_data=input_data,
                output_data=output_data,
                status=status,
                processing_time_seconds=processing_time_seconds,
                model_used=self.config['gemini']['model'],
                error_message=error_message,
                user_agent=user_agent,
                path=path
            )
        except Exception as e:
            # Don't fail the operation if logging fails
            print(f"Failed to log AI operation: {e}")
    
    def process(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Main processing method (implements BaseAIService.process).
        
        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments (should include 'image_file')
            
        Returns:
            dict: Processing results
        """
        return self.extract_holidays_from_image(**kwargs)
