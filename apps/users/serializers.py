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
# 2. Logout Serializer (For JWT Blacklisting)
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