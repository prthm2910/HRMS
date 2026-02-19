import logging
from datetime import timedelta
from django.utils import timezone
from rest_framework import serializers
from apps.payroll.models import (
    SalaryComponent,
    EmployeeSalaryStructure,
    TaxRule,
    PayrollRun,
    Payslip,
    PayslipComponent,
    PayrollAutomationConfig
)
from apps.organization.serializers import EmployeeSerializer
from apps.leaves.constants import LeaveType, LeaveRequestStatus
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes


logger = logging.getLogger(__name__)


class SalaryComponentSerializer(serializers.ModelSerializer):
    """Serializer for salary components (earnings, deductions, bonuses)"""
    
    class Meta:
        model = SalaryComponent
        fields = [
            'id',
            'code',
            'salary_component_id',
            'name',
            'component_type',
            'calculation_method',
            'is_taxable',
            'default_value',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'salary_component_id', 'created_at', 'updated_at']


class EmployeeSalaryStructureSerializer(serializers.ModelSerializer):
    """Serializer for employee salary breakdown"""
    
    employee_details = EmployeeSerializer(source='employee', read_only=True)
    component_details = SalaryComponentSerializer(source='salary_component', read_only=True)
    
    # Default effective_from_at to now if not provided
    effective_from_at = serializers.DateTimeField(default=serializers.CreateOnlyDefault(timezone.now))
    
    class Meta:
        model = EmployeeSalaryStructure
        fields = [
            'id',
            'employee_salary_structure_id',
            'employee',
            'employee_details',
            'salary_component',
            'component_details',
            'amount',
            'effective_from_at',
            'effective_to_at',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'employee_salary_structure_id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        """
        Auto-close old salary structure when creating new one
        for same employee + salary_component combination
        """
        
        employee = validated_data['employee']
        component = validated_data['salary_component']
        new_effective_from = validated_data.get('effective_from_at')
        
        if not new_effective_from:
            new_effective_from = timezone.now()
            
        # Find existing open structure for same employee+component
        old_structure = EmployeeSalaryStructure.objects.filter(
            employee=employee,
            salary_component=component,
            effective_to_at__isnull=True,
            is_deleted=False
        ).first()
        
        if old_structure and old_structure.effective_from_at < new_effective_from:
            # Auto-close old structure (1 second before new structure starts)
            old_structure.effective_to_at = new_effective_from - timedelta(seconds=1)
            old_structure.save()
            logger.info(f"Existing salary structure auto-closed | Structure ID: {old_structure.id} | Employee ID: {employee.employee_id}")
        
        # Create new structure
        logger.debug(f"Creating new salary structure | Employee ID: {employee.employee_id} | Component: {component.name}")
        return super().create(validated_data)


class TaxRuleSerializer(serializers.ModelSerializer):
    """Serializer for tax rules and slabs"""
    
    class Meta:
        model = TaxRule
        fields = [
            'id',
            'code',
            'tax_rule_id',
            'name',
            'country',
            'min_income',
            'max_income',
            'tax_percentage',
            'is_active',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'tax_rule_id', 'created_at', 'updated_at']


class PayrollRunSerializer(serializers.ModelSerializer):
    """Serializer for payroll run records"""
    
    processed_by_name = serializers.CharField(
        source='processed_by.get_full_name',
        read_only=True
    )
    payslip_count = serializers.SerializerMethodField()
    
    class Meta:
        model = PayrollRun
        fields = [
            'id',
            'code',
            'payroll_run_id',
            'month',
            'year',
            'status',
            'processed_at',
            'processed_by',
            'processed_by_name',
            'total_gross_salary',
            'total_deductions',
            'total_net_salary',
            'payslip_count',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id',
            'payroll_run_id',
            'processed_at',
            'processed_by',
            'total_gross_salary',
            'total_deductions',
            'total_net_salary',
            'created_at',
            'updated_at'
        ]
    
    def get_payslip_count(self, obj) -> int:
        return obj.payslips.count()


class PayslipComponentSerializer(serializers.ModelSerializer):
    """Serializer for payslip component breakdown"""
    
    class Meta:
        model = PayslipComponent
        fields = [
            'id',
            'payslip_component_id',
            'component_name',
            'component_type',
            'amount'
        ]
        read_only_fields = ['id', 'payslip_component_id']


class PayslipSerializer(serializers.ModelSerializer):
    """Serializer for employee payslips"""
    
    employee_details = EmployeeSerializer(source='employee', read_only=True)
    components = PayslipComponentSerializer(many=True, read_only=True)
    payroll_run_code = serializers.CharField(source='payroll_run.code', read_only=True)
    unpaid_leaves_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Payslip
        fields = [
            'id',
            'payslip_id',
            'payroll_run',
            'payroll_run_code',
            'employee',
            'employee_details',
            'month',
            'year',
            'gross_salary',
            'total_deductions',
            'net_salary',
            'leave_days_deducted',
            'unpaid_leaves_url',
            'pdf_file',
            'email_sent_at',
            'components',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id',
            'payslip_id',
            'pdf_file',
            'email_sent_at',
            'created_at',
            'updated_at'
        ]
    
    @extend_schema_field(OpenApiTypes.STR)
    def get_unpaid_leaves_url(self, obj):
        """
        Return URL to view unpaid leaves if deductions exist
        Provides transparency for leave deductions
        """
        if obj.leave_days_deducted and obj.leave_days_deducted > 0:
            return f"/api/leaves/my-leave-requests/?month={obj.month}&year={obj.year}&leave_type={LeaveType.UNPAID.value}&status={LeaveRequestStatus.APPROVED.value}"
        return None


class PayrollRunDetailSerializer(serializers.ModelSerializer):
    """Detailed payroll run serializer with nested user info"""
    from apps.users.serializers import UserBasicSerializer
    
    processed_by = UserBasicSerializer(read_only=True)
    
    class Meta:
        model = PayrollRun
        fields = '__all__'


class PayslipDetailSerializer(PayslipSerializer):
    """Detailed payslip serializer with all nested data"""
    payroll_run = PayrollRunDetailSerializer(read_only=True)
    
    class Meta(PayslipSerializer.Meta):
        pass


class PayrollAutomationConfigSerializer(serializers.ModelSerializer):
    """Serializer for payroll automation settings"""
    
    class Meta:
        model = PayrollAutomationConfig
        fields = [
            'id',
            'payroll_automation_config_id',
            'is_enabled',
            'run_day',
            'auto_email_payslips',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'payroll_automation_config_id', 'created_at', 'updated_at']
