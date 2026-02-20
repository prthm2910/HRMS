from rest_framework import viewsets, permissions, mixins
from apps.base.utils import get_employee_profile
from apps.base.permissions import IsAdminUserOrReadOnly, IsAdminWriteOnly
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
import logging

logger = logging.getLogger(__name__)


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
        # check for force=true (new standard)
        force = self.request.query_params.get('force') == 'true'
        
        # Hard Delete: Superuser + Flag
        if self.request.user.is_superuser and force:
            logger.info(f"Hard deletion executed | Table: {instance._meta.model_name} | Record ID: {instance.pk} | Initiator ID: {self.request.user.id}")
            instance.delete()
        # Soft Delete: Default
        else:
            logger.info(f"Soft deletion executed | Table: {instance._meta.model_name} | Record ID: {instance.pk} | Initiator ID: {self.request.user.id}")
            instance.is_deleted = True
            instance.is_active = False
            instance.save()
            
            # Also deactivate associated user accounts if they exist (e.g. for Employee)
            if hasattr(instance, 'user') and instance.user:
                logger.debug(f"Deactivating associated user account | User ID: {instance.user.id}")
                instance.user.is_active = False
                instance.user.save()




class BaseAuthenticatedViewSet(viewsets.ModelViewSet):
    """
    Base viewset requiring authentication for all operations.
    Use for standard authenticated CRUD operations.
    """
    permission_classes = [permissions.IsAuthenticated]


class BaseFilteredViewSet(BaseAuthenticatedViewSet):
    """
    Base viewset with authentication AND filtering/search/ordering capabilities.
    Inherits from BaseAuthenticatedViewSet and adds filter backends.
    
    Provides:
    - DjangoFilterBackend: Field-based filtering (filterset_fields)
    - SearchFilter: Text search across fields (search_fields)
    - OrderingFilter: Result ordering (ordering_fields)
    
    Use this when you need filtering, search, or ordering in your viewset.
    Override filter_backends in subclass if you need a different combination.
    """
    from django_filters.rest_framework import DjangoFilterBackend
    from rest_framework.filters import SearchFilter, OrderingFilter
    
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]


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


class AdminWriteViewSet(viewsets.ModelViewSet):
    """
    Base viewset with dynamic permissions:
    - Read (list, retrieve): Authenticated users
    - Write (create, update, delete): Admin/Staff only
    """
    permission_classes = [IsAdminUserOrReadOnly]


class SuperadminViewSet(viewsets.ModelViewSet):
    """
    Base viewset with strict dynamic permissions:
    - Read (list, retrieve): Authenticated users
    - Write (create, update, delete): Superusers only
    """
    permission_classes = [IsAdminWriteOnly]


# --- Mixins ---

class RoleFilteredMixin:
    """
    Mixin for role-based queryset filtering.
    Admin sees all, Managers see team, Employees see self.
    """
    def get_queryset(self):
        user = self.request.user
        
        # Handle Schema Generation / Anonymous Users
        if getattr(self, "swagger_fake_view", False) or user.is_anonymous:
            return self.get_queryset_model().objects.none()
        
        # 1. Admin/Staff bypass
        if user.is_superuser or user.is_staff:
            logger.debug(f"Role Filter Bypass | Table: {self.get_queryset_model().__name__} | User ID: {user.id} | Role: Admin/Staff")
            return self.get_admin_queryset()
        
        # 2. Get profile for regular users
        employee_profile = get_employee_profile(user)
        if not employee_profile:
            logger.warning(f"Role Filter Denied | Table: {self.get_queryset_model().__name__} | User ID: {user.id} | Reason: No Employee Profile")
            return self.get_queryset_model().objects.none()

        # 3. Apply standard role-based filtering
        logger.debug(f"Applying Role Filtering | Table: {self.get_queryset_model().__name__} | User ID: {user.id} | Employee ID: {employee_profile.pk}")
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


# --- Specialized Superadmin ViewSets (IsAdminWriteOnly) ---

class SuperadminFilterViewSet(BaseFilteredViewSet):
    """Superadmin-Write + Filtering, Search, Ordering backends."""
    permission_classes = [IsAdminWriteOnly]


class SuperadminRoleViewSet(RoleFilteredMixin, SuperadminViewSet):
    """Superadmin-Write + Role Filtering (Admin sees all, Managers/Employees see limited)."""
    pass


class SuperadminFullViewSet(RoleFilteredMixin, SuperadminFilterViewSet):
    """Superadmin-Write + Role Filtering + Filtering/Search/Ordering backends."""
    pass


# --- Specialized Admin ViewSets (IsAdminUserOrReadOnly) ---

class AdminWriteFilterViewSet(BaseFilteredViewSet):
    """Admin-Write + Filtering, Search, Ordering backends."""
    permission_classes = [IsAdminUserOrReadOnly]


class AdminWriteRoleViewSet(RoleFilteredMixin, AdminWriteViewSet):
    """Admin-Write + Role Filtering."""
    pass


class AdminWriteFullViewSet(RoleFilteredMixin, AdminWriteFilterViewSet):
    """Admin-Write + Role Filtering + Filtering/Search/Ordering backends."""
    pass




class RoleViewSet(RoleFilteredMixin, BaseAuthenticatedViewSet):
    """
    Base viewset for role-based filtering (Read-Write).
    """
    pass


class RoleFullViewSet(RoleFilteredMixin, BaseFilteredViewSet):
    """
    Base viewset combining role-based filtering AND filter backends.
    Inherits from BaseFilteredViewSet (which provides filter_backends) and adds RoleFilteredMixin.
    
    Use this when you need BOTH:
    - Role-based queryset filtering (admin sees all, users see filtered data)
    - Filter backends (DjangoFilterBackend, SearchFilter, OrderingFilter)
    
    This is the DRY solution for viewsets that need both capabilities.
    """
    pass


class RoleReadOnlyViewSet(RoleFilteredMixin, BaseReadOnlyAuthenticatedViewSet):
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
