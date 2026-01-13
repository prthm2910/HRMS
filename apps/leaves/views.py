from datetime import date
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from django.db.models import Q
from drf_spectacular.utils import extend_schema, OpenApiExample
from base.utils import get_employee_profile
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
        employee_profile = get_employee_profile(user)
        if not employee_profile:
            return LeaveBalance.objects.none()

        # 3. Manager/Junior Dev Logic
        # Managers see self + team; Juniors see only self
        return LeaveBalance.objects.filter(
            Q(employee=employee_profile) | Q(employee__manager=employee_profile)
        ).distinct().order_by('employee__user__first_name')


class MyLeaveRequestViewSet(viewsets.ReadOnlyModelViewSet):
    """
    View for employees to see their own leave requests.
    Returns all leave requests created by the authenticated user.
    
    Query Parameters:
        - status: Filter by status (pending, approved, rejected, cancelled)
        - Default: Returns all statuses, ordered by latest first
    """
    serializer_class = LeaveRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        
        # Get employee profile
        employee_profile = get_employee_profile(user)
        if not employee_profile:
            return LeaveRequest.objects.none()
        
        # Base queryset: only user's own requests
        queryset = LeaveRequest.objects.filter(employee=employee_profile)
        
        # Status filtering via query params
        status_filter = self.request.query_params.get('status', None)
        if status_filter and status_filter.upper() in dict(LeaveRequest.STATUS_CHOICES):
            queryset = queryset.filter(status=status_filter.upper())
        
        return queryset.order_by('-created_at')


class SubordinateLeaveRequestViewSet(viewsets.ReadOnlyModelViewSet):
    """
    View for managers to see leave requests from their subordinates.
    Returns leave requests from employees who report to the authenticated user.
    
    Query Parameters:
        - status: Filter by status (pending, approved, rejected, cancelled, all)
        - Default: Returns only PENDING requests, ordered by latest first
    """
    serializer_class = LeaveRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        
        # Admin bypass: see all requests
        if user.is_superuser or user.is_staff:
            queryset = LeaveRequest.objects.all()
        else:
            # Get employee profile
            employee_profile = get_employee_profile(user)
            if not employee_profile:
                return LeaveRequest.objects.none()
            
            # Base queryset: only subordinates' requests
            queryset = LeaveRequest.objects.filter(employee__manager=employee_profile)
        
        # Status filtering via query params (default: PENDING)
        status_filter = self.request.query_params.get('status', 'pending')
        
        if status_filter.lower() != 'all':
            if status_filter.upper() in dict(LeaveRequest.STATUS_CHOICES):
                queryset = queryset.filter(status=status_filter.upper())
        
        return queryset.order_by('-created_at')


class LeaveApplyViewSet(viewsets.ModelViewSet):
    """
    Endpoint for applying for leave and managing leave requests.
    - POST: Apply for new leave
    - PATCH/PUT: Managers can approve/reject subordinate requests
    - DELETE: Admin only
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # Admin bypass
        if user.is_superuser or user.is_staff:
            return LeaveRequest.objects.all().order_by('-created_at')

        # Get employee profile
        employee_profile = getattr(user, 'employee_profile', None) or getattr(user, 'employee', None)
        if not employee_profile:
            return LeaveRequest.objects.none()

        # Users can only access their own requests or subordinates' requests
        return LeaveRequest.objects.filter(
            Q(employee=employee_profile) | 
            Q(employee__manager=employee_profile)
        ).distinct().order_by('-created_at')

    def get_serializer_class(self):
        # Schema generation bypass
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


    @extend_schema(
        request={
            'application/json': {
                'oneOf': [
                    {
                        'type': 'object',
                        'properties': {
                            'status': {'type': 'string', 'enum': ['APPROVED', 'REJECTED']},
                            'rejection_reason': {'type': 'string', 'nullable': True}
                        },
                        'required': ['status'],
                        'description': 'Manager: Approve or reject leave request'
                    },
                    {
                        'type': 'object',
                        'properties': {
                            'start_date': {'type': 'string', 'format': 'date'},
                            'end_date': {'type': 'string', 'format': 'date'},
                            'reason': {'type': 'string'},
                            'leave_type': {'type': 'string', 'enum': ['SICK', 'CASUAL', 'EARNED', 'UNPAID']},
                            'is_half_day': {'type': 'boolean'},
                            'half_day_period': {'type': 'string', 'enum': ['FIRST_HALF', 'SECOND_HALF'], 'nullable': True}
                        },
                        'description': 'Employee: Edit pending leave request (only if status=PENDING and start_date is future)'
                    }
                ]
            }
        },
        examples=[
            OpenApiExample(
                'Manager: Approve Leave',
                description='Manager approves a subordinate\'s leave request',
                value={'status': 'APPROVED'},
                request_only=True,
            ),
            OpenApiExample(
                'Manager: Reject Leave',
                description='Manager rejects a subordinate\'s leave request',
                value={'status': 'REJECTED', 'rejection_reason': 'Insufficient coverage during this period'},
                request_only=True,
            ),
            OpenApiExample(
                'Employee: Edit Leave Dates',
                description='Employee edits their own pending leave request',
                value={
                    'start_date': '2026-02-20',
                    'end_date': '2026-02-23',
                    'reason': 'Updated: Medical appointment rescheduled'
                },
                request_only=True,
            ),
        ],
        description="""
        **Update a leave request (different permissions for managers vs employees)**
        
        **Managers can:**
        - Change `status` to APPROVED or REJECTED
        - Add `rejection_reason` when rejecting
        
        **Employees can:**
        - Edit their own PENDING requests if start_date is in the future
        - Change: start_date, end_date, reason, leave_type, is_half_day, half_day_period
        - Cannot change: status (only managers can approve/reject)
        
        **Restrictions:**
        - Employees cannot edit APPROVED/REJECTED/CANCELLED requests
        - Employees cannot edit requests that have already started
        """
    )
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        user = request.user
        user_employee = getattr(user, 'employee_profile', None) or getattr(user, 'employee', None)

        # 1. Admin full access
        if user.is_superuser:
            return super().update(request, *args, **kwargs)

        # 2. Employee editing their own request
        if instance.employee == user_employee:
            # Check if status is PENDING
            if instance.status != 'PENDING':
                return Response(
                    {"detail": f"Cannot edit: Leave request is already {instance.status}. Contact your manager for changes."},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Check if start_date is in the future
            if instance.start_date <= date.today():
                return Response(
                    {"detail": "Cannot edit: Leave has already started or is in the past."},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Check if trying to change status
            if 'status' in request.data:
                return Response(
                    {"detail": "Forbidden: You cannot change the status. Only your manager can approve/reject."},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Allow editing other fields
            return super().update(request, *args, **kwargs)

        # 3. Managers can only change status/reason for their team
        if user_employee and instance.employee.manager == user_employee:
            allowed_fields = ['status', 'rejection_reason']
            disallowed_fields = [key for key in request.data.keys() if key not in allowed_fields]
            
            if disallowed_fields:
                print(f"🚫 Disallowed fields sent: {disallowed_fields}")
                print(f"   Allowed fields: {allowed_fields}")
                print(f"   Request data keys: {list(request.data.keys())}")
                return Response(
                    {
                        "detail": f"Forbidden: Managers can only modify 'status' or 'rejection_reason'. You sent: {', '.join(disallowed_fields)}"
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            return super().update(request, *args, **kwargs)

        return Response(
            {"detail": "You do not have permission to modify this request."},
            status=status.HTTP_403_FORBIDDEN
        )

    @extend_schema(
        request={
            'application/json': {
                'oneOf': [
                    {
                        'type': 'object',
                        'properties': {
                            'status': {'type': 'string', 'enum': ['APPROVED', 'REJECTED']},
                            'rejection_reason': {'type': 'string', 'nullable': True}
                        },
                        'required': ['status'],
                        'description': 'Manager: Approve or reject leave request'
                    },
                    {
                        'type': 'object',
                        'properties': {
                            'start_date': {'type': 'string', 'format': 'date'},
                            'end_date': {'type': 'string', 'format': 'date'},
                            'reason': {'type': 'string'},
                            'leave_type': {'type': 'string', 'enum': ['SICK', 'CASUAL', 'EARNED', 'UNPAID']},
                            'is_half_day': {'type': 'boolean'},
                            'half_day_period': {'type': 'string', 'enum': ['FIRST_HALF', 'SECOND_HALF'], 'nullable': True}
                        },
                        'description': 'Employee: Edit pending leave request (only if status=PENDING and start_date is future)'
                    }
                ]
            }
        },
        examples=[
            OpenApiExample(
                'Manager: Approve Leave',
                description='Manager approves a subordinate\'s leave request',
                value={'status': 'APPROVED'},
                request_only=True,
            ),
            OpenApiExample(
                'Manager: Reject Leave',
                description='Manager rejects a subordinate\'s leave request',
                value={'status': 'REJECTED', 'rejection_reason': 'Insufficient coverage during this period'},
                request_only=True,
            ),
            OpenApiExample(
                'Employee: Edit Leave Dates',
                description='Employee edits their own pending leave request',
                value={
                    'start_date': '2026-02-20',
                    'end_date': '2026-02-23',
                    'reason': 'Updated: Medical appointment rescheduled'
                },
                request_only=True,
            ),
        ],
        description="""
        **Update a leave request (different permissions for managers vs employees)**
        
        **Managers can:**
        - Change `status` to APPROVED or REJECTED
        - Add `rejection_reason` when rejecting
        
        **Employees can:**
        - Edit their own PENDING requests if start_date is in the future
        - Change: start_date, end_date, reason, leave_type, is_half_day, half_day_period
        - Cannot change: status (only managers can approve/reject)
        
        **Restrictions:**
        - Employees cannot edit APPROVED/REJECTED/CANCELLED requests
        - Employees cannot edit requests that have already started
        """
    )
    def partial_update(self, request, *args, **kwargs):
        """PATCH method - same logic as update"""
        return self.update(request, *args, **kwargs)

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