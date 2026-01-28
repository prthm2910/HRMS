from rest_framework.permissions import IsAuthenticated

class IsAdminOrReadOnly(IsAuthenticated):
    """
    Custom permission: Admin can do anything, regular users can only read.
    """
    def has_permission(self, request, view):
        # Check if user is authenticated
        if not super().has_permission(request, view):
            return False
        
        # Allow read-only for all authenticated users
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        
        # Write operations require admin/staff
        return request.user.is_staff or request.user.is_superuser