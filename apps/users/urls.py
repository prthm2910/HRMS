from django.urls import path
from rest_framework_simplejwt.views import (
     TokenObtainPairView,
     TokenRefreshView,
)
from rest_framework.permissions import AllowAny
from apps.users.views import  UserProfileView

urlpatterns = [
    # Login Endpoint (Get Access + Refresh Token)
    path('login/', TokenObtainPairView.as_view(permission_classes=[AllowAny]), name='token_obtain_pair'),
    
    # Refresh Endpoint (Get new Access Token using Refresh Token)
    path('token/refresh/', TokenRefreshView.as_view(permission_classes=[AllowAny]), name='token_refresh'),

    # Self-Service (View/Edit my own details)
    path('profile/', UserProfileView.as_view(), name='user-profile'),
]