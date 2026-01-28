from rest_framework import permissions

class IsProjectAdminOrHODOrReadOnly(permissions.BasePermission):
    """
    - Admin: Full Access.
    - HOD: Write Access (Create/Update/Delete)
    - Employee: Read Only
    """
    def has_permission(self, request, view):
        # Allow all read operations
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Allow all write operations for superusers
        if request.user.is_superuser:
            return True
        
        # Check if user is an HOD
        if not hasattr(request.user, 'employee_profile'):
            return False
        
        employee_profile = request.user.employee_profile
        if hasattr(employee_profile, 'hod_profile'):
            return True
        
        return False

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        if request.user.is_superuser:
            return True
            
        # For HOD, ensure object belongs to their department
        employee = request.user.employee_profile
        if hasattr(employee, 'hod_profile'):
            # Handle Project Object
            if hasattr(obj, 'department'):
                return obj.department == employee.hod_profile.department
            # Handle ProjectMember Object
            if hasattr(obj, 'project'):
                return obj.project.department == employee.hod_profile.department
                
        return False
