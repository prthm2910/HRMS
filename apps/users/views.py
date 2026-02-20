import logging
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from django.contrib.auth import get_user_model

from apps.users.serializers import RegisterSerializer, UserSerializer
from apps.users.serializers import LogoutSerializer

from drf_spectacular.utils import extend_schema


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


# 3. Logout View (Blacklist JWT)

@extend_schema(tags=['Authentication'])
class LogoutView(generics.GenericAPIView):
    """
    Endpoint: /api/auth/logout/
    Permission: IsAuthenticated
    Logic: Blacklists the provided refresh token.
    """
    serializer_class = LogoutSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        logger.info(f"User logged out successfully | User ID: {request.user.id}")
        return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)