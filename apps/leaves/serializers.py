from rest_framework import serializers
from django.db.models import Q
from datetime import date
from apps.base.serializers import BaseTemplateSerializer
from apps.base.utils import calculate_working_days, is_weekend, is_holiday, get_non_working_days_info, get_employee_profile
from apps.leaves.models import LeaveRequest, LeaveBalance
from apps.organization.models import Employee
from apps.organization.serializers import EmployeeBasicSerializer

# Note: EmployeeBasicSerializer is now imported from organization.serializers
# It already includes nested department field

class LeaveBalanceSerializer(BaseTemplateSerializer):
    leave_type_display = serializers.CharField(source='get_leave_type_display', read_only=True)
    
    # Remaining leaves calculation (supports half-days: e.g., 9.5)
    remaining_leaves = serializers.DecimalField(max_digits=5, decimal_places=1, read_only=True)
    
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
    # Duration in days (considers half-days: 0.5 for half-day, working days for full-day)
    duration = serializers.FloatField(read_only=True)
    
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
    
    # Half-day fields
    half_day_period_display = serializers.CharField(source='get_half_day_period_display', read_only=True)
    
    # Non-working days info (holidays and weekends) for UX
    non_working_days_info = serializers.SerializerMethodField()
    
    class Meta:
        model = LeaveRequest
        fields = BaseTemplateSerializer.Meta.fields + [
            'employee', 'employee_id',
            'leave_type', 'start_date', 'end_date', 'reason',
            'status', 'rejection_reason', 
            'action_by_details',
            'duration',
            'is_half_day', 'half_day_period', 'half_day_period_display',
            'non_working_days_info'
        ]
        # CRITICAL: 'status' is now Read-Only by default
        read_only_fields = ['employee', 'action_by_details', 'status', 'rejection_reason', 'non_working_days_info']
    
    def get_non_working_days_info(self, obj):
        """
        Get information about holidays and weekends in the leave period.
        Helps employees and approvers understand actual working days.
        """
        if not obj.start_date or not obj.end_date:
            return {'total_count': 0, 'details': []}
        
        return get_non_working_days_info(obj.start_date, obj.end_date)

    def validate(self, data):
        start = data.get('start_date')
        end = data.get('end_date')
        
        request = self.context.get('request')
        user = request.user if request else None
        employee = get_employee_profile(user)

        # 1. Date Order & Future Check
        if start and end:
            if start > end:
                raise serializers.ValidationError({
                    "end_date": "End date cannot be before start date."
                })
            
            # Allow same-day half-day leaves for emergencies
            is_half_day = data.get('is_half_day', False)
            
            if not is_half_day:
                # Full-day leaves must be in the future
                if start < date.today():
                    raise serializers.ValidationError({
                        "start_date": "Full-day leave requests must be for future dates. For same-day emergencies, please use half-day leave."
                    })
            else:
                # Half-day leaves can be on the same day, but not in the past
                if start < date.today():
                    raise serializers.ValidationError({
                        "start_date": "Half-day leave cannot be applied for past dates."
                    })
        
        # 2. WEEKEND VALIDATION - Reject if start or end date is on weekend
        if start and is_weekend(start):
            raise serializers.ValidationError({
                "start_date": f"Start date cannot be on a weekend. {start.strftime('%Y-%m-%d')} is a {start.strftime('%A')}."
            })
        
        if end and is_weekend(end):
            raise serializers.ValidationError({
                "end_date": f"End date cannot be on a weekend. {end.strftime('%Y-%m-%d')} is a {end.strftime('%A')}."
            })
        
        # 3. HOLIDAY VALIDATION - Reject leaves starting or ending on holidays
        if start:
            is_start_holiday, start_holiday_info = is_holiday(start)
            if is_start_holiday:
                holiday_name = start_holiday_info.get('name', 'Holiday')
                raise serializers.ValidationError({
                    "start_date": f"Cannot start leave on {start.strftime('%Y-%m-%d')} as it is a declared holiday ({holiday_name})."
                })
        
        if end:
            is_end_holiday, end_holiday_info = is_holiday(end)
            if is_end_holiday:
                holiday_name = end_holiday_info.get('name', 'Holiday')
                raise serializers.ValidationError({
                    "end_date": f"Cannot end leave on {end.strftime('%Y-%m-%d')} as it is a declared holiday ({holiday_name})."
                })

        # 4. HALF-DAY VALIDATIONS
        is_half_day = data.get('is_half_day', False)
        half_day_period = data.get('half_day_period')
        
        if is_half_day:
            # Half-day must have same start and end date
            if start and end and start != end:
                raise serializers.ValidationError({
                    "end_date": "Half-day leave must have the same start and end date."
                })
            
            # Half-day period is required
            if not half_day_period:
                raise serializers.ValidationError({
                    "half_day_period": "Please specify which half of the day (First Half or Second Half)."
                })
        
        # 5. OVERLAP CHECK (including half-day specific validation)
        if start and end and employee:
            is_half_day = data.get('is_half_day', False)
            half_day_period = data.get('half_day_period')
            
            # For half-day leaves, check if there's already a half-day request on the same date
            if is_half_day and start == end:
                # Check for exact same half-day period
                same_half_requests = LeaveRequest.objects.filter(
                    employee=employee,
                    start_date=start,
                    end_date=end,
                    is_half_day=True,
                    half_day_period=half_day_period,
                    status__in=['PENDING', 'APPROVED']
                )
                
                if self.instance:
                    same_half_requests = same_half_requests.exclude(id=self.instance.id)
                
                if same_half_requests.exists():
                    period_display = 'First Half' if half_day_period == 'FIRST_HALF' else 'Second Half'
                    raise serializers.ValidationError(
                        f"You already have a {period_display} leave request for {start.strftime('%Y-%m-%d')}."
                    )
                
                # Check if both halves are already taken
                other_half_period = 'SECOND_HALF' if half_day_period == 'FIRST_HALF' else 'FIRST_HALF'
                other_half_requests = LeaveRequest.objects.filter(
                    employee=employee,
                    start_date=start,
                    end_date=end,
                    is_half_day=True,
                    half_day_period=other_half_period,
                    status__in=['PENDING', 'APPROVED']
                )
                
                if self.instance:
                    other_half_requests = other_half_requests.exclude(id=self.instance.id)
                
                if other_half_requests.exists():
                    raise serializers.ValidationError(
                        f"You already have a leave request for the other half of {start.strftime('%Y-%m-%d')}. Both halves cannot be taken as separate requests."
                    )
            
            # Standard overlap check for all leave types
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

        # 6. Balance Check (Only on CREATE)
        if request and request.method == 'POST' and employee:
            if start and end:
                leave_type = data.get('leave_type')
                is_half_day = data.get('is_half_day', False)
                
                # Calculate days requested based on half-day or full-day
                if is_half_day:
                    days_requested = 0.5
                    excluded_holidays = []
                else:
                    # Use utility function for working days calculation (now returns tuple)
                    days_requested, excluded_holidays = calculate_working_days(start, end)
                    days_requested = float(days_requested)
                    
                    # Reject if all days are non-working days (weekends/holidays)
                    if days_requested == 0:
                        calendar_days = (end - start).days + 1
                        raise serializers.ValidationError(
                            f"Cannot apply for leave from {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}. "
                            f"All {calendar_days} day(s) in this period are weekends or holidays."
                        )
                
                # Print holiday notification to terminal if holidays were excluded
                if excluded_holidays:
                    calendar_days = (end - start).days + 1
                    print("\n" + "="*70)
                    print(f"📅 LEAVE REQUEST NOTIFICATION")
                    print("="*70)
                    print(f"Employee: {employee.employee_id} - {employee.user.get_full_name()}")
                    print(f"Period: {start} to {end}")
                    print(f"Calendar Days: {calendar_days}")
                    print(f"Working Days: {int(days_requested)}")
                    print(f"\nYou're taking {calendar_days} calendar days but only {int(days_requested)} working days because:")
                    for holiday in excluded_holidays:
                        print(f"  - {holiday['date']} ({holiday['name']}) is a holiday")
                    print("="*70 + "\n")
                
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
        fields = ['start_date', 'end_date', 'reason', 'leave_type', 'is_half_day', 'half_day_period']

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