from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.audit.models import AuditLog
from apps.users.serializers import UserBasicSerializer

User = get_user_model()

class AuditLogSerializer(serializers.ModelSerializer):
    # Nested actor for GET requests
    actor = UserBasicSerializer(read_only=True)
    
    # actor_id for POST/PUT/PATCH requests
    actor_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='actor',
        write_only=True,
        required=False,
        allow_null=True
    )
    
    class Meta:
        model = AuditLog
        fields = '__all__'