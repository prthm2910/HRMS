from django.contrib import admin
from apps.payroll.models import (
    SalaryComponent,
    EmployeeSalaryStructure,
    TaxRule,
    PayrollRun,
    Payslip,
    PayslipComponent,
    PayrollAutomationConfig
)


@admin.register(SalaryComponent)
class SalaryComponentAdmin(admin.ModelAdmin):
    list_display = ['name', 'component_type', 'calculation_method', 'is_taxable', 'default_value', 'created_at']
    list_filter = ['component_type', 'calculation_method', 'is_taxable']
    search_fields = ['name']
    ordering = ['component_type', 'name']


@admin.register(EmployeeSalaryStructure)
class EmployeeSalaryStructureAdmin(admin.ModelAdmin):
    list_display = ['employee', 'salary_component', 'amount', 'effective_from', 'effective_to']
    list_filter = ['salary_component', 'effective_from']
    search_fields = ['employee__user__first_name', 'employee__user__last_name', 'employee__employee_id']
    raw_id_fields = ['employee', 'salary_component']
    date_hierarchy = 'effective_from'


@admin.register(TaxRule)
class TaxRuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'country', 'min_income', 'max_income', 'tax_percentage', 'is_active']
    list_filter = ['country', 'is_active']
    search_fields = ['name']
    ordering = ['country', 'min_income']


@admin.register(PayrollRun)
class PayrollRunAdmin(admin.ModelAdmin):
    list_display = ['month', 'year', 'status', 'total_gross_salary', 'total_deductions', 'total_net_salary', 'processed_at', 'processed_by']
    list_filter = ['status', 'year', 'month']
    search_fields = ['year', 'month']
    readonly_fields = ['processed_at', 'processed_by', 'total_gross_salary', 'total_deductions', 'total_net_salary']
    ordering = ['-year', '-month']


@admin.register(Payslip)
class PayslipAdmin(admin.ModelAdmin):
    list_display = ['employee', 'month', 'year', 'gross_salary', 'total_deductions', 'net_salary', 'email_sent_at']
    list_filter = ['year', 'month', 'payroll_run']
    search_fields = ['employee__user__first_name', 'employee__user__last_name', 'employee__employee_id']
    raw_id_fields = ['employee', 'payroll_run']
    readonly_fields = ['email_sent_at']
    date_hierarchy = 'created_at'


class PayslipComponentInline(admin.TabularInline):
    model = PayslipComponent
    extra = 0
    readonly_fields = ['component_name', 'component_type', 'amount']


@admin.register(PayslipComponent)
class PayslipComponentAdmin(admin.ModelAdmin):
    list_display = ['payslip', 'component_name', 'component_type', 'amount']
    list_filter = ['component_type']
    search_fields = ['payslip__employee__user__first_name', 'payslip__employee__user__last_name', 'component_name']
    raw_id_fields = ['payslip']


@admin.register(PayrollAutomationConfig)
class PayrollAutomationConfigAdmin(admin.ModelAdmin):
    list_display = ['is_enabled', 'run_day', 'auto_email_payslips', 'updated_at']
    
    def has_add_permission(self, request):
        # Only allow one config instance
        return not PayrollAutomationConfig.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Don't allow deletion
        return False
