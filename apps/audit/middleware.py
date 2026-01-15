from rest_framework_simplejwt.authentication import JWTAuthentication 
# ^^^ IF THIS FAILS: pip install djangorestframework-simplejwt
# IF YOU USE STANDARD TOKENS: from rest_framework.authentication import TokenAuthentication

from apps.base.utils import set_audit_data, clear_audit_data

class AuditMiddleware:
    def __init__(self, get_response):
        """
        Initialize the middleware.

        :param get_response: Callable that returns the response from the parent middleware.
        :type get_response: Callable[[Request], Response]
        """
        self.get_response = get_response

    def __call__(self, request):
        # 1. Try to get the user from Standard Django Session
        """
        Intercept incoming requests, attempt to identify the user, capture request metadata, and persist audit logs.
        
        :param request: The incoming request object.
        :type request: Request
        :return: The response from the parent middleware.
        :rtype: Response
        """
        user = request.user

        # 2. IF user is not found, try to manually decode the API Token
        if not user or not user.is_authenticated:
            user = self.get_api_user(request)

        # 3. Capture Details
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        path = request.path

        # 4. Save to Thread for Signals
        set_audit_data(user, user_agent, path)

        response = self.get_response(request)

        # 5. Cleanup
        clear_audit_data()

        return response

    def get_api_user(self, request):
        """
        Manually attempts to authenticate the user via JWT Token
        because DRF Auth runs AFTER Middleware.
        """
        try:
            # Check for Authorization header
            header = request.headers.get('Authorization')
            if header:
                # Manually trigger the JWT Authentication
                # If you use TokenAuth, change this to: TokenAuthentication()
                authenticator = JWTAuthentication() 
                
                # authenticate() returns (user, token) or None
                auth_result = authenticator.authenticate(request)
                
                if auth_result:
                    return auth_result[0] # Return the User object
        except Exception:
            # Token might be invalid, expired, or malformed
            pass
        
        return None