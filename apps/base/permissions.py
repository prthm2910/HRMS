from rest_framework import permissions

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
        return request.user.is_superuser


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
            
        return request.user.is_staff or request.user.is_superuser
