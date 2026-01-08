from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.base.serializers import BaseTemplateSerializer

# Get the custom User model defined in models.py
User = get_user_model()

# ------------------------------------------------------------------
# 0. User Basic Serializer (For Nested Display)
# ------------------------------------------------------------------
class UserBasicSerializer(BaseTemplateSerializer):
    """
    Lightweight serializer for displaying basic user info in nested contexts.
    Used by: AuditLogSerializer, EmployeeSerializer
    """
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'phone_number']
        read_only_fields = fields  # All fields are read-only for nested display


# ------------------------------------------------------------------
# 1. User Serializer (For Profiles)
# ------------------------------------------------------------------
class UserSerializer(BaseTemplateSerializer):
    class Meta:
        model = User
        # We explicitly list fields to expose in the API.
        # SECURITY: Never include 'password' here!
        fields = BaseTemplateSerializer.Meta.fields + ['username', 'email', 'phone_number', 'bio']


# ------------------------------------------------------------------
# 2. Registration Serializer (For Sign Up)
# ------------------------------------------------------------------
class RegisterSerializer(serializers.ModelSerializer):
    # We add a password field manually because we need special options (write_only)
    password = serializers.CharField(
        write_only=True, 
        required=True, 
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        # The fields the user must send to register
        fields = ['username', 'email', 'password', 'phone_number', 'bio']

    def create(self, validated_data):
        """
        Overriding the create method is CRITICAL for security.
        """
        # 1. Pop the password from the data (we don't want to save it raw!)
        password = validated_data.pop('password')
        
        # 2. Create the user instance without the password first
        user = User(**validated_data)
        
        # 3. Hash the password securely
        user.set_password(password)
        
        # 4. Save to DB
        user.save()
        
        return user