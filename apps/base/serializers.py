from rest_framework import serializers


class BaseTemplateSerializer(serializers.ModelSerializer):
    """
    A foundational serializer that provides common read-only fields for all other serializers.
    This serializer automatically includes fields from BaseTemplateModel.
    """
    
    # Make common fields read-only
    id = serializers.UUIDField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    is_deleted = serializers.BooleanField(read_only=True)
    
    class Meta:
        abstract = True
        # These fields will be automatically included in any serializer that inherits from this
        fields = ['id', 'created_at', 'updated_at', 'is_active', 'is_deleted']
