import logging
from rest_framework import permissions

logger = logging.getLogger(__name__)

class IsAdminWriteOnly(permissions.BasePermission):
    """
    Permission class that allows:
    - GET, HEAD, OPTIONS (Safe methods) for any authenticated user.
    - POST, PUT, PATCH, DELETE for Superusers only.
    """
    def has_permission(self, request, view):
        # Must be authenticated
        if not (request.user and request.user.is_authenticated):
            return False
            
        # Safe methods are allowed for all authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True
            
        # Write operations require superuser status
        is_superuser = request.user.is_superuser
        if not is_superuser:
            logger.warning(
                f"Permission Denied (Superuser Required) | User ID: {request.user.id} | "
                f"Action: {request.method} | View: {view.__class__.__name__}"
            )
            # Set custom message if provided by the view
            self.message = getattr(view, 'admin_forbidden_message', "Forbidden: Only Administrators have permission to perform this action.")
            
        return is_superuser


class IsAdminUserOrReadOnly(permissions.BasePermission):
    """
    Permission class that allows:
    - Read operations for authenticated users.
    - Write operations for Admin/Staff users.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
            
        if request.method in permissions.SAFE_METHODS:
            return True
            
        is_admin = request.user.is_staff or request.user.is_superuser
        if not is_admin:
            logger.warning(
                f"Permission Denied (Admin Required) | User ID: {request.user.id} | "
                f"Action: {request.method} | View: {view.__class__.__name__}"
            )
            # Set custom message if provided by the view
            self.message = getattr(view, 'admin_forbidden_message', "Forbidden: You do not have permission to perform this action.")
            
        return is_admin
