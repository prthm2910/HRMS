from rest_framework import viewsets, permissions, status, mixins
from rest_framework.response import Response
from apps.base.utils import get_employee_profile
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes


class DeleteMixin:
    """
    Mixin to handle both soft and hard deletion of records.
    
    Default behavior: Soft Delete (is_deleted=True, is_active=False)
    Hard Delete: Superuser only + ?force=true query param
    """
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='force', 
                description='Set to "true" to permanently delete the record (Superuser only).', 
                required=False, 
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY
            )
        ]
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def perform_destroy(self, instance):
        # check for force=true (new standard) OR permanent=true (legacy/backward compat if needed)
        force = self.request.query_params.get('force') == 'true'
        
        # Hard Delete: Superuser + Flag
        if self.request.user.is_superuser and force:
            instance.delete()
        # Soft Delete: Default
        else:
            instance.is_deleted = True
            instance.is_active = False
            instance.save()
            
            # Also deactivate associated user accounts if they exist (e.g. for Employee)
            if hasattr(instance, 'user') and instance.user:
                instance.user.is_active = False
                instance.user.save()


class AdminWritePermissionMixin:
    """
    Mixin to restrict create/update/destroy actions to Superadmins only.
    Usage: Inherit this BEFORE the ViewSet class.
    """
    admin_forbidden_message = "Forbidden: Only Administrators have permission to perform this action."

    def create(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return Response(
                {"detail": self.admin_forbidden_message},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return Response(
                {"detail": self.admin_forbidden_message},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return Response(
                {"detail": self.admin_forbidden_message},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)


class BaseAuthenticatedViewSet(viewsets.ModelViewSet):
    """
    Base viewset requiring authentication for all operations.
    Use for standard authenticated CRUD operations.
    """
    permission_classes = [permissions.IsAuthenticated]


class BaseCreateOnlyAuthenticatedViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
    Base viewset for create-only operations requiring authentication.
    """
    permission_classes = [permissions.IsAuthenticated]


class BaseReadOnlyAuthenticatedViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Base read-only viewset requiring authentication.
    Use for views that should only allow GET operations.
    """
    permission_classes = [permissions.IsAuthenticated]


class BaseAdminViewSet(viewsets.ModelViewSet):
    """
    Base viewset requiring admin privileges for all operations.
    Use for admin-only CRUD operations.
    """
    permission_classes = [permissions.IsAdminUser]


class BaseReadOnlyAdminViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Base read-only viewset requiring admin privileges.
    Use for admin-only read operations (e.g., audit logs).
    """
    permission_classes = [permissions.IsAdminUser]


class BaseReadAuthWriteAdminViewSet(viewsets.ModelViewSet):
    """
    Base viewset with dynamic permissions:
    - Read (list, retrieve): Authenticated users
    - Write (create, update, delete): Admin/Staff only
    
    Use for resources that anyone can view but only admins can modify.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]


class RoleFilteredMixin:
    """
    Mixin for role-based queryset filtering.
    Admin sees all, Managers see team, Employees see self.
    """
    def get_queryset(self):
        user = self.request.user
        
        # 1. Admin/Staff bypass
        if user.is_superuser or user.is_staff:
            return self.get_admin_queryset()
        
        # 2. Get profile for regular users
        employee_profile = get_employee_profile(user)
        if not employee_profile:
            return self.get_queryset_model().objects.none()

        # 3. Apply standard role-based filtering
        return self.get_standard_user_queryset(employee_profile)

    def get_queryset_model(self):
        """Returns the model associated with this viewset's queryset."""
        return self.queryset.model

    def get_admin_queryset(self):
        """Returns the queryset for administrators."""
        return self.queryset

    def get_standard_user_queryset(self, employee_profile):
        """Must be implemented by subclasses to filter for regular users."""
        raise NotImplementedError("Subclasses must implement get_standard_user_queryset")


class BaseRoleFilteredViewSet(RoleFilteredMixin, BaseAuthenticatedViewSet):
    """
    Base viewset for role-based filtering (Read-Write).
    """
    pass


class BaseRoleFilteredReadOnlyViewSet(RoleFilteredMixin, BaseReadOnlyAuthenticatedViewSet):
    """
    Base viewset for role-based filtering (Read-Only).
    """
    pass


class BasePublicViewSet(viewsets.ModelViewSet):
    """
    Base viewset allowing public access (no authentication required).
    Use sparingly - only for truly public endpoints like registration.
    """
    permission_classes = [permissions.AllowAny]
