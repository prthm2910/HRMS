from rest_framework import serializers
from django.db import models
from datetime import date as date_type
from apps.holidays.models import Holiday
from apps.base.serializers import BaseSerializer



# ============================================================================
# Django REST Framework Serializers
# ============================================================================

class HolidaySerializer(BaseSerializer):
    """
    Main serializer for Holiday model.
    Used for CRUD operations via API.
    """
    
    class Meta:
        model = Holiday
        fields = BaseSerializer.Meta.fields + [
            'holiday_date',
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
    
    def validate_holiday_date(self, value):
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
        date_val = data.get('holiday_date')
        region_val = data.get('region', '')
        
        if date_val:
            # Build query
            query = Holiday.objects.filter(
                holiday_date=date_val,
                region=region_val,
                is_deleted=False
            )
            
            # Exclude current instance if updating
            if self.instance:
                query = query.exclude(pk=self.instance.pk)
            
            if query.exists():
                raise serializers.ValidationError({
                    'holiday_date': f'A holiday already exists on {date_val} for region "{region_val or "All"}"'
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
        
        # Optimization: Perform bulk duplicate check with a single query
        # Extract all date-region pairs for checking
        date_region_pairs = [(h['holiday_date'], h.get('region', '')) for h in holidays_data]
        
        # Single query to check all existing holidays
        existing_holidays = set(
            Holiday.objects.filter(
                is_deleted=False
            ).filter(
                models.Q(*[
                    models.Q(holiday_date=date, region=region) 
                    for date, region in date_region_pairs
                ])
            ).values_list('holiday_date', 'region')
        )
        
        # Separate holidays into create and skip lists
        holidays_to_create = []
        for holiday_data in holidays_data:
            date_region = (holiday_data['holiday_date'], holiday_data.get('region', ''))
            
            if date_region in existing_holidays:
                skipped_holidays.append({
                    'holiday_date': str(holiday_data['holiday_date']),
                    'name': holiday_data['name'],
                    'region': holiday_data.get('region', ''),
                    'reason': 'Holiday already exists on this date for this region'
                })
            else:
                holidays_to_create.append(Holiday(**holiday_data))
        
        # Optimization: Use bulk_create for all new holidays in a single query
        if holidays_to_create:
            created_holidays = Holiday.objects.bulk_create(holidays_to_create)
        
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
            'holiday_date',
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
