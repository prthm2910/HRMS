from datetime import date
from rest_framework import status
from rest_framework.response import Response
from django.db.models import Q
from drf_spectacular.utils import extend_schema, OpenApiExample
from apps.base.utils import get_employee_profile
from apps.base.views import (
    BaseReadOnlyAuthenticatedViewSet,
    BaseRoleFilteredViewSet,
    BaseRoleFilteredReadOnlyViewSet,
    AdminWritePermissionMixin,
    BaseCreateOnlyAuthenticatedViewSet
)
from apps.leaves.models import LeaveRequest, LeaveBalance
from apps.leaves.serializers import (
    LeaveRequestSerializer, 
    LeaveBalanceSerializer, 
    LeaveUpdateSerializer, 
    LeaveActionSerializer,
    BulkLeaveRequestSerializer,
    BulkLeaveResponseSerializer
)

@extend_schema(tags=['leaves'])
class LeaveBalanceViewSet(BaseRoleFilteredReadOnlyViewSet):
    """
    View to check remaining leaves. 
    Strictly Read-Only for everyone.
    """
    queryset = LeaveBalance.objects.all()
    serializer_class = LeaveBalanceSerializer

    def get_admin_queryset(self):
        return self.queryset.order_by('employee__user__first_name')

    def get_standard_user_queryset(self, employee_profile):
        # Managers see self + team; Juniors see only self
        return self.queryset.filter(
            Q(employee=employee_profile) | Q(employee__manager=employee_profile)
        ).distinct().order_by('employee__user__first_name')


@extend_schema(tags=['leaves'])
class MyLeaveRequestViewSet(BaseReadOnlyAuthenticatedViewSet):
    """
    View for employees to see their own leave requests.
    Returns all leave requests created by the authenticated user.
    """
    serializer_class = LeaveRequestSerializer

    def get_queryset(self):
        user = self.request.user
        employee_profile = get_employee_profile(user)
        if not employee_profile:
            return LeaveRequest.objects.none()
        
        queryset = LeaveRequest.objects.filter(employee=employee_profile)
        
        status_filter = self.request.query_params.get('status')
        if status_filter and status_filter.upper() in dict(LeaveRequest.STATUS_CHOICES):
            queryset = queryset.filter(status=status_filter.upper())
        
        return queryset.order_by('-created_at')


@extend_schema(tags=['leaves'])
class SubordinateLeaveRequestViewSet(BaseReadOnlyAuthenticatedViewSet):
    """
    View for managers to see leave requests from their subordinates.
    """
    serializer_class = LeaveRequestSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.is_staff:
            queryset = LeaveRequest.objects.all()
        else:
            employee_profile = get_employee_profile(user)
            if not employee_profile:
                return LeaveRequest.objects.none()
            queryset = LeaveRequest.objects.filter(employee__manager=employee_profile)
        
        status_filter = self.request.query_params.get('status', 'pending')
        if status_filter.lower() != 'all':
            if status_filter.upper() in dict(LeaveRequest.STATUS_CHOICES):
                queryset = queryset.filter(status=status_filter.upper())
        
        return queryset.order_by('-created_at')


@extend_schema(tags=['leaves'])
class LeaveApplyViewSet(AdminWritePermissionMixin, BaseRoleFilteredViewSet):
    """
    Endpoint for applying for leave and managing leave requests.
    - POST: Apply for new leave
    - PATCH/PUT: Managers can approve/reject subordinate requests
    - DELETE: Admin only
    """
    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer
    admin_forbidden_message = "Forbidden: Deletion is restricted to Administrators."

    def get_admin_queryset(self):
        return self.queryset.order_by('-created_at')

    def get_standard_user_queryset(self, employee_profile):
        return self.queryset.filter(
            Q(employee=employee_profile) | 
            Q(employee__manager=employee_profile)
        ).distinct().order_by('-created_at')

    def get_serializer_class(self):
        if getattr(self, 'swagger_fake_view', False):
            return LeaveRequestSerializer

        if self.action in ['update', 'partial_update']:
            instance = self.get_object()
            user_employee = get_employee_profile(self.request.user)
            
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
                        'description': 'Employee: Edit pending leave request'
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
        # We need to keep update/partial_update because they have very specific business logic 
        # that isn't just "is_superuser". 
        # But we now get the benefit of AdminWritePermissionMixin for destroy().
        instance = self.get_object()
        user = request.user
        user_employee = get_employee_profile(user)

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

    def perform_update(self, serializer):
        user_employee = get_employee_profile(self.request.user)
        if isinstance(serializer, LeaveActionSerializer):
            validated_data = serializer.validated_data or {}
            new_status = validated_data.get('status')
            if new_status in ['APPROVED', 'REJECTED']:
                serializer.save(action_by=user_employee)
            else:
                serializer.save()
        else:
            serializer.save()


@extend_schema(tags=['leaves'])
class BulkLeaveApplyViewSet(BaseCreateOnlyAuthenticatedViewSet):
    """
    ViewSet for bulk leave application.
    Allows submitting up to 5 leave requests at once.
    """
    queryset = LeaveRequest.objects.none()  # Satisfy drf-spectacular introspection
    serializer_class = BulkLeaveRequestSerializer
    
    @extend_schema(
        request=BulkLeaveRequestSerializer,
        responses={201: BulkLeaveResponseSerializer, 400: BulkLeaveResponseSerializer},
        examples=[
            OpenApiExample(
                'Bulk Leave Application',
                description='Submit multiple leave requests at once (max 5 requests)',
                value={
                    "requests": [
                        {
                            "leave_type": "CASUAL",
                            "start_date": "2026-02-10",
                            "end_date": "2026-02-12",
                            "reason": "Family function",
                            "is_half_day": False
                        },
                        {
                            "leave_type": "SICK",
                            "start_date": "2026-03-05",
                            "end_date": "2026-03-05",
                            "reason": "Medical appointment",
                            "is_half_day": True,
                            "half_day_period": "FIRST_HALF"
                        },
                        {
                            "leave_type": "EARNED",
                            "start_date": "2026-04-15",
                            "end_date": "2026-04-18",
                            "reason": "Vacation",
                            "is_half_day": False
                        }
                    ]
                },
                request_only=True,
            ),
        ],
        description="""
        **Submit multiple leave requests at once (max 5)**
        
        **Request Body Structure:**
        ```json
        {
          "requests": [
            {
              "leave_type": "CASUAL|SICK|EARNED|UNPAID",
              "start_date": "YYYY-MM-DD",
              "end_date": "YYYY-MM-DD",
              "reason": "string",
              "is_half_day": true|false,
              "half_day_period": "FIRST_HALF|SECOND_HALF" (required if is_half_day=true)
            }
          ]
        }
        ```
        
        **Response:**
        - Returns partial success with detailed results for each request
        - `successful`: Array of successfully created leave requests
        - `failed`: Array of failed requests with validation errors
        - `summary`: Total, successful, and failed counts
        
        **Validation:**
        - Each request is validated independently
        - Failed requests don't prevent successful ones from being created
        - Same validation rules apply as single leave requests
        """
    )
    def create(self, request):
        """
        Bulk leave application endpoint.
        Creates multiple leave requests and returns partial success.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        successful_requests = []
        failed_requests = []
        
        for idx, leave_data in enumerate(serializer.validated_data['requests']):
            try:
                leave_serializer = LeaveRequestSerializer(
                    data=leave_data,
                    context={'request': request}
                )
                
                if leave_serializer.is_valid():
                    leave_request = leave_serializer.save()
                    successful_requests.append({
                        'index': idx,
                        'id': leave_request.id,
                        'dates': f"{leave_request.start_date} to {leave_request.end_date}",
                        'leave_type': leave_request.leave_type,
                        'status': leave_request.status
                    })
                else:
                    failed_requests.append({
                        'index': idx,
                        'data': leave_data,
                        'errors': leave_serializer.errors
                    })
                    
            except Exception as e:
                failed_requests.append({
                    'index': idx,
                    'data': leave_data,
                    'errors': {'error': str(e)}
                })
        
        response_data = {
            'successful': successful_requests,
            'failed': failed_requests,
            'summary': {
                'total': len(serializer.validated_data['requests']),
                'successful': len(successful_requests),
                'failed': len(failed_requests)
            }
        }
        
        # Use response serializer for consistent output
        response_serializer = BulkLeaveResponseSerializer(data=response_data)
        response_serializer.is_valid(raise_exception=True)
        
        status_code = status.HTTP_201_CREATED if successful_requests else status.HTTP_400_BAD_REQUEST
        return Response(response_serializer.validated_data, status=status_code)
