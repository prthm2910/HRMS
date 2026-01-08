from rest_framework import serializers
from django.db.models import Q
from datetime import date
from apps.base.serializers import BaseTemplateSerializer
from .models import LeaveRequest, LeaveBalance
from organization.models import Employee
from organization.serializers import EmployeeBasicSerializer, DepartmentBasicSerializer

# Note: EmployeeBasicSerializer is now imported from organization.serializers
# It already includes nested department field

class LeaveBalanceSerializer(BaseTemplateSerializer):
    leave_type_display = serializers.CharField(source='get_leave_type_display', read_only=True)
    
    # FIX 1: Explicitly define IntegerField to resolve type hint warning
    remaining_leaves = serializers.IntegerField(read_only=True)
    
    # Nested employee for GET requests
    employee = EmployeeBasicSerializer(read_only=True)
    
    # employee_id for POST/PUT/PATCH requests
    employee_id = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        source='employee',
        write_only=True,
        required=True
    )

    class Meta:
        model = LeaveBalance
        fields = BaseTemplateSerializer.Meta.fields + [
            'employee', 'employee_id',
            'leave_type', 'leave_type_display', 
            'total_allocated', 'used_leaves', 'remaining_leaves'
        ]


class LeaveRequestSerializer(BaseTemplateSerializer):
    """
    Default Serializer for List and Create.
    Security: 'status' is Read-Only here so no one can create an 'APPROVED' leave directly.
    """
    # FIX 2: Explicitly define IntegerField for duration
    duration_days = serializers.IntegerField(source='duration', read_only=True)
    
    # Nested employee for GET requests
    employee = EmployeeBasicSerializer(read_only=True)
    
    # employee_id for POST/PUT/PATCH requests (optional since it's auto-set from request.user)
    employee_id = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        source='employee',
        write_only=True,
        required=False,
        allow_null=True
    )
    
    # Nested serializer for action_by field to show employee details
    action_by_details = EmployeeBasicSerializer(
        source='action_by',
        read_only=True
    )
    
    # action_by_id for write operations (managers/admins)
    action_by_id = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(),
        source='action_by',
        write_only=True,
        required=False,
        allow_null=True
    )
    
    class Meta:
        model = LeaveRequest
        fields = BaseTemplateSerializer.Meta.fields + [
            'employee', 'employee_id',
            'leave_type', 'start_date', 'end_date', 'reason',
            'status', 'rejection_reason', 
            'action_by_details', 'action_by_id',
            'duration_days'
        ]
        # CRITICAL: 'status' is now Read-Only by default
        read_only_fields = ['employee', 'action_by_details', 'status', 'rejection_reason']

    def validate(self, data):
        start = data.get('start_date')
        end = data.get('end_date')
        
        request = self.context.get('request')
        user = request.user if request else None
        employee = getattr(user, 'employee_profile', None)

        # 1. Date Order & Future Check
        if start and end:
            if start > end:
                raise serializers.ValidationError({"end_date": "End date cannot be before start date."})
            
            if request and request.method == 'POST':
                if start <= date.today():
                    raise serializers.ValidationError({
                        "start_date": "You cannot apply for past or current dates. Please apply at least 1 day in advance."
                    })

        # 2. OVERLAP CHECK
        if start and end and employee:
            overlapping_requests = LeaveRequest.objects.filter(
                employee=employee,
                status__in=['PENDING', 'APPROVED']
            ).filter(
                Q(start_date__lte=end) & Q(end_date__gte=start)
            )
            
            if self.instance:
                overlapping_requests = overlapping_requests.exclude(id=self.instance.id)

            if overlapping_requests.exists():
                conflict = overlapping_requests.first()
                if conflict:
                    raise serializers.ValidationError(
                        f"You already have a leave request for this period ({conflict.start_date} to {conflict.end_date})." 
                    )

        # 3. Balance Check (Only on CREATE)
        if request and request.method == 'POST' and employee:
            if start and end:
                leave_type = data.get('leave_type')
                days_requested = (end - start).days + 1
                
                try:
                    balance_record = LeaveBalance.objects.get(
                        employee=employee, 
                        leave_type=leave_type
                    )
                    
                    if balance_record.remaining_leaves < days_requested:
                        raise serializers.ValidationError(
                            f"Insufficient Balance. You have {balance_record.remaining_leaves} {leave_type} leaves left."
                        )
                except LeaveBalance.DoesNotExist:
                     raise serializers.ValidationError(f"Leave balance record not found for {leave_type}.")

        return data

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['employee'] = user.employee_profile
        return super().create(validated_data)


class LeaveUpdateSerializer(LeaveRequestSerializer):
    """
    For Employees to edit their own requests.
    Explicitly blocks 'status' changes with a clear error message.
    """
    class Meta(LeaveRequestSerializer.Meta):
        fields = ['start_date', 'end_date', 'reason', 'leave_type']

    def validate(self, data):
        # We look at the raw request data to see if 'status' was sent
        request = self.context.get('request')
        
        # If the user tried to send 'status' in their PATCH/PUT body
        if request and 'status' in request.data:
            raise serializers.ValidationError({
                "status": "Security Error: You do not have permission to modify the status of a leave request."
            })
            
        # Continue with standard date and balance validation from parent
        return super().validate(data)


class LeaveActionSerializer(serializers.ModelSerializer):
    """
    For Managers to Approve/Reject.
    Only allows changing status and rejection reason.
    """
    class Meta:
        model = LeaveRequest
        fields = ['status', 'rejection_reason']

    def validate_status(self, value):
        if value not in ['APPROVED', 'REJECTED']:
            raise serializers.ValidationError("Managers can only set status to APPROVED or REJECTED.")
        return value