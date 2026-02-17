"""
AI Services - Image Utilities

Helper functions for image validation and preprocessing.
"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def validate_image_file(file) -> Dict[str, Any]:
    """
    Validate an uploaded image file with low-level logging.
    """
    file_name = file.name if file else 'None'
    logger.debug(f"Image Validation Start | File: {file_name}")
    
    # Supported image formats
    SUPPORTED_FORMATS = ['image/jpeg', 'image/png', 'image/jpg']
    MAX_FILE_SIZE_MB = 10
    
    if not file:
        logger.error("Image validation failed: No file object provided.")
        raise ValueError("No file provided")
    
    # Check content type
    if file.content_type not in SUPPORTED_FORMATS:
        logger.warning(f"Image Validation Rejected | Reason: Unsupported Format ({file.content_type}) | File: {file_name}")
        raise ValueError(
            f"Unsupported file format: {file.content_type}. "
            f"Supported formats: {', '.join(SUPPORTED_FORMATS)}"
        )
    
    # Check file size
    max_size_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
    if file.size > max_size_bytes:
        logger.warning(f"Image Validation Rejected | Reason: File too large ({file.size / 1024 / 1024:.2f} MB) | File: {file_name}")
        raise ValueError(
            f"File size ({file.size / 1024 / 1024:.2f} MB) exceeds "
            f"maximum allowed size ({MAX_FILE_SIZE_MB} MB)"
        )
    
    logger.info(f"Image Validation Success | File: {file_name} | Format: {file.content_type}")
    return {
        'valid': True,
        'content_type': file.content_type,
        'size_mb': file.size / 1024 / 1024,
        'name': file_name
    }