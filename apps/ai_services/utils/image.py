"""
AI Services - Image Utilities

Helper functions for image validation and preprocessing.
"""
from typing import Dict, Any


def validate_image_file(file) -> Dict[str, Any]:
    """
    Validate an uploaded image file.
    
    Args:
        file: Django UploadedFile object
        
    Returns:
        dict: Validation result with metadata
        
    Raises:
        ValueError: If validation fails
    """
    # Supported image formats
    SUPPORTED_FORMATS = ['image/jpeg', 'image/png', 'image/jpg']
    MAX_FILE_SIZE_MB = 10
    
    if not file:
        raise ValueError("No file provided")
    
    # Check content type
    if file.content_type not in SUPPORTED_FORMATS:
        raise ValueError(
            f"Unsupported file format: {file.content_type}. "
            f"Supported formats: {', '.join(SUPPORTED_FORMATS)}"
        )
    
    # Check file size
    max_size_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
    if file.size > max_size_bytes:
        raise ValueError(
            f"File size ({file.size / 1024 / 1024:.2f} MB) exceeds "
            f"maximum allowed size ({MAX_FILE_SIZE_MB} MB)"
        )
    
    return {
        'valid': True,
        'content_type': file.content_type,
        'size_mb': file.size / 1024 / 1024,
        'name': file.name
    }


# Future: Add image preprocessing functions
# def preprocess_image(file):
#     """
#     Preprocess image for better OCR results.
#     - Resize if too large
#     - Enhance contrast
#     - Rotate if needed
#     """
#     pass

# def get_image_metadata(file):
#     """
#     Extract EXIF data and image metadata.
#     """
#     pass
