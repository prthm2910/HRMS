from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from django.db.models import Q
from .models import LeaveRequest, LeaveBalance
from .serializers import (
    LeaveRequestSerializer, 
    LeaveBalanceSerializer, 
    LeaveUpdateSerializer, 
    LeaveActionSerializer
)

class LeaveBalanceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    View to check remaining leaves. 
    Strictly Read-Only for everyone.
    """
    serializer_class = LeaveBalanceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # 1. Admin bypass: They see ALL balances immediately
        if user.is_superuser or user.is_staff:
            return LeaveBalance.objects.all().order_by('employee__user__first_name')

        # 2. Regular User check: Must have a profile to see anything
        employee_profile = getattr(user, 'employee_profile', None) or getattr(user, 'employee', None)
        if not employee_profile:
            return LeaveBalance.objects.none()

        # 3. Manager/Junior Dev Logic
        # Managers see self + team; Juniors see only self
        return LeaveBalance.objects.filter(
            Q(employee=employee_profile) | Q(employee__manager=employee_profile)
        ).distinct().order_by('employee__user__first_name')


class LeaveRequestViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # 1. Admin bypass: Check this FIRST so Admin doesn't need an Employee profile
        if user.is_superuser or user.is_staff:
            return LeaveRequest.objects.all().order_by('-created_at')

        # 2. Profile check for everyone else
        employee_profile = getattr(user, 'employee_profile', None) or getattr(user, 'employee', None)
        if not employee_profile:
            return LeaveRequest.objects.none()

        # 3. Junior Devs see only their own. Managers see their own + subordinates.
        return LeaveRequest.objects.filter(
            Q(employee=employee_profile) | 
            Q(employee__manager=employee_profile)
        ).distinct().order_by('-created_at')

    def get_serializer_class(self):
        # FIX: Schema Generation Bypass
        # When generating docs, there is no 'pk' in the URL, so get_object() fails.
        # We simply return the default serializer to satisfy the schema generator.
        if getattr(self, 'swagger_fake_view', False):
            return LeaveRequestSerializer

        if self.action in ['update', 'partial_update']:
            instance = self.get_object()
            user_employee = getattr(self.request.user, 'employee_profile', None) or getattr(self.request.user, 'employee', None)
            
            # Use Action Serializer if user is the Manager OR Admin
            if (user_employee and instance.employee.manager == user_employee) or self.request.user.is_superuser:
                return LeaveActionSerializer
            
            return LeaveUpdateSerializer

        return LeaveRequestSerializer

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        user = request.user
        user_employee = getattr(user, 'employee_profile', None) or getattr(user, 'employee', None)

        # 1. Admin full access
        if user.is_superuser:
            return super().update(request, *args, **kwargs)

        # 2. Block Junior Devs from editing their own leaves (POST only)
        if instance.employee == user_employee:
            return Response(
                {"detail": "Forbidden: Employees are only allowed to apply (POST). To edit, contact your manager."},
                status=status.HTTP_403_FORBIDDEN
            )

        # 3. Managers can only change status/reason for their team
        if user_employee and instance.employee.manager == user_employee:
            allowed_fields = ['status', 'rejection_reason']
            if any(key not in allowed_fields for key in request.data.keys()):
                 return Response(
                    {"detail": "Forbidden: Managers can only modify status or rejection reason."},
                    status=status.HTTP_403_FORBIDDEN
                )
            return super().update(request, *args, **kwargs)

        return Response(
            {"detail": "You do not have permission to modify this request."},
            status=status.HTTP_403_FORBIDDEN
        )

    def destroy(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return Response(
                {"detail": "Forbidden: Deletion is restricted to Administrators."},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)

    def perform_update(self, serializer):
        user_employee = getattr(self.request.user, 'employee_profile', None) or getattr(self.request.user, 'employee', None)
        
        if isinstance(serializer, LeaveActionSerializer):
            validated_data = serializer.validated_data or {}
            new_status = validated_data.get('status') # type: ignore

            if new_status in ['APPROVED', 'REJECTED']:
                serializer.save(action_by=user_employee)
            else:
                serializer.save()
        else:
            serializer.save()