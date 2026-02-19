import logging
from rest_framework import generics, permissions                
from django.contrib.auth import get_user_model

from apps.users.serializers import RegisterSerializer, UserSerializer

User = get_user_model()

logger = logging.getLogger(__name__)


# 1. Registration View
class RegisterView(generics.CreateAPIView):
    """
    Endpoint: /api/auth/register/
    Permission: AllowAny (Anyone can register)
    """
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer 


# 2. Profile View (Get "Me")
class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Endpoint: /api/auth/profile/
    Permission: IsAuthenticated (Must be logged in)
    Logic: Returns the profile of the CURRENT user (request.user)
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        # This overrides the default "lookup by ID" behavior.
        # Instead of looking for ID 5, it just returns "Me".
        logger.debug(f"Authorized profile access attempt | User ID: {self.request.user.id} | Action: {self.request.method}")
        return self.request.user