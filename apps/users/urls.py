from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from apps.users.views import RegisterView, UserProfileView

# ==============================================================================
# AUTHENTICATION & IDENTITY URLS
# ==============================================================================
"""
    1. FIRST PRINCIPLES: The "Security Keycard Office"
    Registration is where you apply for a membership. Login is where 
    you get your "Self-Expiring Keycard" (JWT). Profile is where you 
    swipe that card to see your own data.

    2. TECHNICAL BREAKDOWN:
    - TokenObtainPairView: Validates username/password and returns 
      an 'Access' and a 'Refresh' token.
    - TokenRefreshView: Takes an old 'Refresh' token and gives you a 
      new 'Access' token so you don't have to log in again every hour.
    - JWT (JSON Web Token): A stateless way to prove identity. The 
      server doesn't need to "remember" you; it just verifies the 
      cryptographic signature on the card you're carrying.
"""

urlpatterns = [
    
    # Sign Up (Open to All)
    path('register/', RegisterView.as_view(), name='register'),

    # Login (Get the Keycard)
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    
    # Token Renewal (Get a new Access key)
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Self-Service (View/Edit my own details)
    path('profile/', UserProfileView.as_view(), name='user-profile'),
]