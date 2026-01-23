from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.base.serializers import BaseTemplateSerializer

# Get the custom User model defined in models.py
User = get_user_model()

# ==============================================================================
# USER SERIALIZERS (The Translators)
# ==============================================================================

class UserBasicSerializer(BaseTemplateSerializer):
    """
    1. FIRST PRINCIPLES: The "ID Card"
    Think of this as the front of an employee's ID badge. It only shows 
    the essentials (name, email, phone) so other departments can 
    identify them quickly without seeing their entire personal file.

    2. TECHNICAL BREAKDOWN:
    - BaseTemplateSerializer: Inherits global fields like 'id' and 'created_at'.
    - fields: A strict list of what we allow to be sent back as JSON.
    - read_only_fields: Makes sure this information cannot be changed 
      through this specific serializer.
    """
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'phone_number']
        read_only_fields = fields


class UserSerializer(BaseTemplateSerializer):
    """
    1. FIRST PRINCIPLES: The "Detailed Passport"
    When an employee looks at their own profile, they see more details 
    (like their bio). This is a more comprehensive version of the ID card.

    2. TECHNICAL BREAKDOWN:
    - SECURITY: We explicitly exclude 'password' here. Serializers 
      act as a security filter—if it's not in the 'fields' list, it 
      can't be leaked to the web.
    """
    class Meta:
        model = User
        fields = BaseTemplateSerializer.Meta.fields + ['username', 'email', 'phone_number', 'bio']


class RegisterSerializer(serializers.ModelSerializer):
    """
    1. FIRST PRINCIPLES: The "Enrollment Form"
    When a new person joins, they fill out a form (username, email, password). 
    The most important part is how the "Password" is handled—it's 
    written down on the form, but immediately put into a secure vault 
    so even the HR person can't read it again.

    2. TECHNICAL BREAKDOWN:
    - write_only=True: The password is sent to the server, but it is 
      NEVER sent back in a response. It's a "one-way street."
    - create(): We override this to handle the "Security Vault" logic.
    - set_password(): Django's built-in hashing function. It turns 
      "password123" into a scrambled string like "pbkdf2_sha256$..." 
      that cannot be reversed.
    """
    password = serializers.CharField(
        write_only=True, 
        required=True, 
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'phone_number', 'bio']

    def create(self, validated_data):
        # 1. Take the raw password out of the data
        password = validated_data.pop('password')
        
        # 2. Create a temporary user object with the other details
        user = User(**validated_data)
        
        # 3. Hash the password (put it in the vault)
        user.set_password(password)
        
        # 4. Save the finalized user to the database
        user.save()
        
        return user