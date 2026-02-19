"""
AI Services - OCR Service

Gemini AI-based OCR service for extracting structured data from images.
"""
import google.generativeai as genai
import json
import logging
from typing import Dict, Any, List
from apps.ai_services.services.base import BaseAIService
from apps.ai_services.config import AIServiceConfig
from apps.ai_services.schemas.ocr import HolidayExtraction
from apps.audit.constants import AIOperationType, AIOperationLogStatus

logger = logging.getLogger(__name__)


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
        logger.debug("Initializing GeminiOCRService instance for vision-based extraction.")
        self.config = AIServiceConfig.get_ocr_config()
        self._configure_gemini()
    
    def _configure_gemini(self):
        """Configure Gemini AI with API key"""
        logger.debug(f"Configuring Gemini AI model connection. Target model: {self.config['gemini']['model']}")
        gemini_config = self.config['gemini']
        genai.configure(api_key=gemini_config['api_key'])
        self.model = genai.GenerativeModel(gemini_config['model'])
        logger.info(f"Gemini AI engine successfully configured with model: {gemini_config['model']}")
    
    def extract_holidays_from_image(self, image_file, user=None, user_agent=None, path=None) -> Dict[str, Any]:
        """
        Extract holiday data from an uploaded image with detailed logging.
        """
        file_name = image_file.name if image_file else 'unknown_file'
        logger.debug(f"Starting holiday extraction process for file: {file_name}")
        self.start_timer()
        
        try:
            # Validate input
            logger.debug(f"Validating image file constraints for: {file_name}")
            self.validate_input(image_file=image_file)
            
            # Read image data
            image_data = image_file.read()
            
            # Generate prompt
            logger.debug(f"Constructing extraction prompt for Gemini AI model: {self.config['gemini']['model']}")
            prompt = self._generate_prompt()
            
            # Call Gemini API
            logger.info(f"Calling Gemini API for OCR extraction on file: {file_name}")
            response = self.model.generate_content([
                prompt,
                {"mime_type": image_file.content_type, "data": image_data}
            ])
            
            # Parse response
            logger.debug("Gemini API response received. Parsing structured JSON output.")
            extracted_data = self._parse_response(response.text)
            
            # Validate extracted data
            logger.debug(f"Validating {len(extracted_data)} candidate holiday entries against schema.")
            all_holidays, has_errors = self._validate_extracted_data(extracted_data)
            
            self.stop_timer()
            processing_time = self.get_processing_time()
            logger.info(f"OCR processing completed in {processing_time:.2f}ms. Total holidays extracted: {len(all_holidays)}")
            
            if has_errors:
                logger.warning(f"Metadata: OCR for file '{file_name}' completed with partial schema validation errors.")
            
            result = {
                'status': AIOperationLogStatus.SUCCESS.value,
                'extracted_holidays': all_holidays,
                'total_count': len(all_holidays),
                'has_validation_errors': has_errors,
                'processing_time_ms': processing_time,
                'model_used': self.config['gemini']['model']
            }
            
            # Log to audit system
            if user:
                logger.debug(f"Submitting AI operation audit log for User ID: {user.id}")
                self.log_operation(
                    operation_type=AIOperationType.OCR.value,
                    user=user,
                    input_data={'image_name': file_name, 'size_bytes': image_file.size},
                    output_data={'holidays_count': len(all_holidays), 'has_errors': has_errors},
                    status=AIOperationLogStatus.SUCCESS.value,
                    model_used=self.config['gemini']['model'],
                    processing_time_ms=processing_time,
                    error_message=None,
                    user_agent=user_agent,
                    path=path
                )
            
            return result
            
        except Exception as e:
            self.stop_timer()
            logger.error(f"AI OCR processing failed: {str(e)}", exc_info=True)
            error_result = self.handle_error(e)
            
            # Log failure to audit system
            if user:
                self.log_operation(
                    operation_type=AIOperationType.OCR.value,
                    user=user,
                    input_data={'image_name': image_file.name if image_file else 'unknown'},
                    output_data=None,
                    status=AIOperationLogStatus.FAILED.value,
                    model_used=self.config['gemini']['model'],
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
        logger.debug("Attempting to parse cleaned response text as JSON.")
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
                logger.warning(f"Validation failed for extracted holiday at index {idx}: {str(e)}")
                invalid_data = holiday_data.copy()
                invalid_data['validation_error'] = str(e)
                all_holidays.append(invalid_data)
        
        return all_holidays, has_errors
    

    
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
