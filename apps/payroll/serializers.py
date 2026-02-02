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
            'effective_from',
            'effective_to',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'employee_salary_structure_id', 'created_at', 'updated_at']


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
    
    def get_payslip_count(self, obj):
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


class PayslipDetailSerializer(PayslipSerializer):
    """Detailed payslip serializer with all nested data"""
    
    class Meta(PayslipSerializer.Meta):
        depth = 2


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
