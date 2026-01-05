from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    # Login Endpoint (Get Access + Refresh Token)
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    
    # Refresh Endpoint (Get new Access Token using Refresh Token)
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]