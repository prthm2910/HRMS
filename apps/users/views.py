from rest_framework import generics, permissions                
from django.contrib.auth import get_user_model
from apps.users.serializers import RegisterSerializer, UserSerializer

User = get_user_model()

# ==============================================================================
# USER API VIEWS (The Reception Desk)
# ==============================================================================

class RegisterView(generics.CreateAPIView):
    """
    1. FIRST PRINCIPLES: The "New Membership Window"
    Imagine you are at a gym. Most counters require a membership card, 
    but the "Sign Up" window is open to everyone (AllowAny). Once you 
    hand over your form (RegisterSerializer), the gym gives you your 
    new account.

    2. TECHNICAL BREAKDOWN:
    - generics.CreateAPIView: A pre-built "shortcut" view that handles 
      the logic of taking data and saving it to a database.
    - permission_classes: [AllowAny]: Critical for registration! It 
      allows users who aren't logged in to access this endpoint.
    """
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer 


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    1. FIRST PRINCIPLES: The "Self-Service Kiosk"
    Once you have a membership card, you can go to a kiosk to see 
    your own details. You don't need to tell the kiosk who you are 
    (no ID required in the URL) because your membership card 
    (JWT Token) already tells the machine that it's "Me".

    2. TECHNICAL BREAKDOWN:
    - RetrieveUpdateAPIView: A shortcut for "Looking up" and "Editing" data.
    - IsAuthenticated: The "Security Guard" that blocks anyone who 
      doesn't have a valid Login Token.
    - get_object(): Normally, Django looks for a specific person by 
      their ID (e.g., user/5/). By returning 'self.request.user', 
      we make the URL simpler (/api/auth/profile/)—it always returns 
      whoever is logged in.
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user