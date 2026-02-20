import logging
from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.base.serializers import BaseSerializer
from apps.organization.serializers import EmployeeBasicSerializer

# Get the custom User model defined in models.py
User = get_user_model()

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# 0. User Basic Serializer (For Nested Display)
# ------------------------------------------------------------------
class UserBasicSerializer(BaseSerializer):
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
class UserSerializer(BaseSerializer):
    employee_profile = EmployeeBasicSerializer(read_only=True)
    
    class Meta:
        model = User
        # We explicitly list fields to expose in the API.
        # SECURITY: Never include 'password' here!
        fields = BaseSerializer.Meta.fields + ['username', 'email', 'phone_number', 'bio', 'employee_profile']


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
        logger.debug(f"Initiating secure user creation process | Username: {validated_data.get('username')}")
        # 1. Pop the password from the data (we don't want to save it raw!)
        password = validated_data.pop('password')
        
        # 2. Create the user instance without the password first
        user = User(**validated_data)
        
        # 3. Hash the password securely
        logger.debug(f"Executing password hashing for new user | Username: {user.username}")
        user.set_password(password)
        
        # 4. Save to DB
        user.save()
        logger.info(f"User registration record saved successfully | User ID: {user.id} | Email Status: Provided")
        
        return user


# ------------------------------------------------------------------
# 3. Logout Serializer (For JWT Blacklisting)
# ------------------------------------------------------------------
class LogoutSerializer(serializers.Serializer):
    """
    Serializer to handle logout by blacklisting the refresh token.
    """
    refresh = serializers.CharField(
        help_text="The refresh token to be blacklisted"
    )

    default_error_messages = {
        'bad_token': 'Token is invalid or expired'
    }

    def validate(self, attrs):
        self.token = attrs['refresh']
        return attrs

    def save(self, **kwargs):
        from rest_framework_simplejwt.tokens import RefreshToken, TokenError
        try:
            RefreshToken(self.token).blacklist()
        except TokenError:
            self.fail('bad_token')