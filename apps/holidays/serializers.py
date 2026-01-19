from rest_framework import serializers
from pydantic import BaseModel, field_validator, ValidationError as PydanticValidationError
from typing import Optional, List
from datetime import date as date_type
from apps.holidays.models import Holiday
from apps.base.serializers import BaseTemplateSerializer


# ============================================================================
# Pydantic Models for OCR Validation
# ============================================================================

class HolidayExtraction(BaseModel):
    """
    Pydantic model for validating holiday data extracted from images via OCR.
    Used in the extract-from-image endpoint.
    """
    date: date_type
    name: str
    description: Optional[str] = ""
    is_recurring: bool = False
    region: Optional[str] = ""
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate holiday name"""
        if not v or len(v.strip()) < 3:
            raise ValueError('Holiday name must be at least 3 characters long')
        return v.strip().title()
    
    @field_validator('date')
    @classmethod
    def validate_date(cls, v: date_type) -> date_type:
        """Validate that date is not in the past"""
        if v < date_type.today():
            raise ValueError(f'Cannot add past holidays. Date {v} is in the past.')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "date": "2026-08-15",
                "name": "Independence Day",
                "description": "National Holiday",
                "is_recurring": True,
                "region": "All India"
            }
        }


class BulkHolidayExtraction(BaseModel):
    """
    Pydantic model for validating bulk holiday extraction.
    Ensures no duplicate dates within the batch.
    """
    holidays: List[HolidayExtraction]
    
    @field_validator('holidays')
    @classmethod
    def check_duplicates(cls, v: List[HolidayExtraction]) -> List[HolidayExtraction]:
        """Check for duplicate dates in the batch"""
        dates = [h.date for h in v]
        if len(dates) != len(set(dates)):
            raise ValueError('Duplicate dates found in the holiday list')
        return v
    
    @field_validator('holidays')
    @classmethod
    def check_not_empty(cls, v: List[HolidayExtraction]) -> List[HolidayExtraction]:
        """Ensure at least one holiday is provided"""
        if not v or len(v) == 0:
            raise ValueError('At least one holiday must be provided')
        return v


# ============================================================================
# Django REST Framework Serializers
# ============================================================================

class HolidaySerializer(BaseTemplateSerializer):
    """
    Main serializer for Holiday model.
    Used for CRUD operations via API.
    """
    
    class Meta:
        model = Holiday
        fields = BaseTemplateSerializer.Meta.fields + [
            'date',
            'name',
            'description',
            'is_recurring',
            'recurring_group_id',
            'region',
            'is_working_day'
        ]
        read_only_fields = ['recurring_group_id']
    
    def validate_name(self, value):
        """Validate holiday name"""
        if not value or len(value.strip()) < 3:
            raise serializers.ValidationError(
                "Holiday name must be at least 3 characters long."
            )
        return value.strip()
    
    def validate_date(self, value):
        """Validate that new holidays are not in the past"""
        # Only validate for creation, not updates
        if not self.instance and value < date_type.today():
            raise serializers.ValidationError(
                "Cannot create holidays for past dates."
            )
        return value
    
    def validate(self, data):
        """Cross-field validation"""
        # Check for duplicate date + region combination
        date_val = data.get('date')
        region_val = data.get('region', '')
        
        if date_val:
            # Build query
            query = Holiday.objects.filter(
                date=date_val,
                region=region_val,
                is_deleted=False
            )
            
            # Exclude current instance if updating
            if self.instance:
                query = query.exclude(pk=self.instance.pk)
            
            if query.exists():
                raise serializers.ValidationError({
                    'date': f'A holiday already exists on {date_val} for region "{region_val or "All"}"'
                })
        
        return data


class BulkHolidayCreateSerializer(serializers.Serializer):
    """
    Serializer for bulk creating holidays.
    Accepts an array of holiday data and creates multiple holidays at once.
    Skips duplicates and returns detailed response.
    """
    holidays = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=False,
        help_text="List of holiday objects to create"
    )
    
    def validate_holidays(self, value):
        """Validate each holiday in the list"""
        if not value:
            raise serializers.ValidationError("At least one holiday must be provided")
        
        validated_holidays = []
        errors = []
        
        for idx, holiday_data in enumerate(value):
            try:
                # Use HolidaySerializer to validate each item
                serializer = HolidaySerializer(data=holiday_data)
                if serializer.is_valid(raise_exception=True):
                    validated_holidays.append(serializer.validated_data)
            except serializers.ValidationError as e:
                errors.append({
                    'index': idx,
                    'data': holiday_data,
                    'errors': e.detail
                })
        
        if errors:
            raise serializers.ValidationError({
                'invalid_holidays': errors
            })
        
        return validated_holidays
    
    def create(self, validated_data):
        """
        Create multiple holidays, skipping duplicates.
        Returns dict with created and skipped holidays.
        """
        holidays_data = validated_data['holidays']
        created_holidays = []
        skipped_holidays = []
        
        for holiday_data in holidays_data:
            # Check if holiday already exists
            exists = Holiday.objects.filter(
                date=holiday_data['date'],
                region=holiday_data.get('region', ''),
                is_deleted=False
            ).exists()
            
            if exists:
                skipped_holidays.append({
                    'date': str(holiday_data['date']),
                    'name': holiday_data['name'],
                    'region': holiday_data.get('region', ''),
                    'reason': 'Holiday already exists on this date for this region'
                })
            else:
                # Create the holiday
                holiday = Holiday.objects.create(**holiday_data)
                created_holidays.append(holiday)
        
        return {
            'created': created_holidays,
            'skipped': skipped_holidays
        }


class HolidayListSerializer(HolidaySerializer):
    """
    Lightweight serializer for listing holidays.
    Excludes some fields for better performance.
    """
    class Meta(HolidaySerializer.Meta):
        fields = [
            'id',
            'date',
            'name',
            'region',
            'is_recurring',
            'is_active'
        ]


class ImageUploadSerializer(serializers.Serializer):
    """
    Serializer for image upload in extract-from-image endpoint.
    Used for Swagger UI documentation.
    """
    image = serializers.FileField(
        required=True,
        allow_empty_file=False,
        use_url=False,
        help_text="Upload an image containing holiday list (PNG, JPG, JPEG)"
    )
    
    class Meta:
        fields = ['image']
