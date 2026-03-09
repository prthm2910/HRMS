import logging
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.base.models import BaseModel
from apps.organization.models import Employee
from apps.payroll.constants import ComponentType, CalculationMethod, PayrollStatus
from django.utils.text import slugify
from apps.base.utils import get_month_name
from django.core.files.base import ContentFile
from apps.payroll.services.pdf_generator import generate_payslip_pdf

logger = logging.getLogger(__name__)


class SalaryComponent(BaseModel):
    """Define reusable salary components"""
    
    # Auto-generated slug from name (primary business identifier)
    code = models.SlugField(
        max_length=50,
        unique=True,
        db_index=True,
        blank=True,
        help_text="Auto-generated from name (e.g., basic-salary, hra, pf-deduction)"
    )
    
    # HRID identifier
    salary_component_id = models.CharField(
        max_length=20, 
        unique=True, 
        editable=False,
        null=True,
        help_text="Format: SCMXXXXXX"
    )
    _display_id_prefix = 'SCM'
    _display_id_field = 'salary_component_id'
    name = models.CharField(max_length=100, unique=True)
    component_type = models.CharField(
        max_length=20,
        choices=ComponentType.choices()
    )
    calculation_method = models.CharField(
        max_length=20,
        choices=CalculationMethod.choices(),
        default=CalculationMethod.FIXED.value
    )
    is_taxable = models.BooleanField(default=True)
    default_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    
    class Meta:
        db_table = 'salary_components'
        ordering = ['component_type', 'name']
    
    def save(self, *args, **kwargs):
        # Auto-generate code from name if not provided
        is_new = self._state.adding
        if not self.code:
            self.code = slugify(self.name)
            
            # Ensure uniqueness by appending number if needed
            original_code = self.code
            counter = 1
            while SalaryComponent.objects.filter(code=self.code).exclude(pk=self.pk).exists():
                self.code = f"{original_code}-{counter}"
                counter += 1
            logger.debug(f"Auto-generated code for salary component | Code: {self.code}")
        
        super().save(*args, **kwargs)
        if is_new:
            logger.info(f"New salary component created | Code: {self.code} | Type: {self.component_type}")
    
    def __str__(self):
        return f"{self.name} ({self.get_component_type_display()})"


class EmployeeSalaryStructure(BaseModel):
    """Employee-specific salary breakdown"""
    
    # Business identifier (exposed in APIs)
    employee_salary_structure_id = models.CharField(
        max_length=20, 
        unique=True, 
        editable=False,
        null=True,
        db_index=True,
        help_text="Format: ESSXXXXXX"
    )
    _display_id_prefix = 'ESS'
    _display_id_field = 'employee_salary_structure_id'
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='salary_structures'
    )
    salary_component = models.ForeignKey(
        SalaryComponent,
        on_delete=models.PROTECT,
        related_name='employee_structures'
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    effective_from_at = models.DateTimeField(
        help_text="Date and time from which this salary structure is effective"
    )
    effective_to_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Date and time when this salary structure expires"
    )
    
    class Meta:
        db_table = 'employee_salary_structures'
        ordering = ['-effective_from_at']
        unique_together = ['employee', 'salary_component', 'effective_from_at']
    
    def __str__(self):
        return f"{self.employee.user.get_full_name()} - {self.salary_component.name}"


class TaxRule(BaseModel):
    """Configurable tax slabs"""
    
    # Auto-generated slug from name (primary business identifier)
    code = models.SlugField(
        max_length=50,
        unique=True,
        db_index=True,
        blank=True,
        help_text="Auto-generated from name (e.g., india-tax-slab-1-0-3l)"
    )
    
    # HRID identifier
    tax_rule_id = models.CharField(
        max_length=20, 
        unique=True, 
        editable=False,
        null=True,
        help_text="Format: TAXXXXXXX"
    )
    _display_id_prefix = 'TAX'
    _display_id_field = 'tax_rule_id'
    name = models.CharField(max_length=100)
    country = models.CharField(max_length=2, default='IN')  # ISO country code
    min_income = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    max_income = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        null=True,
        blank=True
    )
    tax_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'tax_rules'
        ordering = ['country', 'min_income']
    
    def __str__(self):
        return f"{self.name} ({self.country}): {self.tax_percentage}%"
    
    def save(self, *args, **kwargs):
        # Auto-generate code from name if not provided
        is_new = self._state.adding
        if not self.code:
            from django.utils.text import slugify
            self.code = slugify(self.name)
            
            # Ensure uniqueness
            original_code = self.code
            counter = 1
            while TaxRule.objects.filter(code=self.code).exclude(pk=self.pk).exists():
                self.code = f"{original_code}-{counter}"
                counter += 1
            logger.debug(f"Auto-generated code for tax rule | Code: {self.code}")
        
        super().save(*args, **kwargs)
        if is_new:
            logger.info(f"New tax rule created | Code: {self.code} | Country: {self.country}")


class PayrollRun(BaseModel):
    
    # Auto-generated slug from month/year (primary business identifier)
    code = models.SlugField(
        max_length=50,
        unique=True,
        db_index=True,
        blank=True,
        help_text="Auto-generated from month/year (e.g., pr-february-2026)"
    )
    
    # HRID identifier
    payroll_run_id = models.CharField(
        max_length=20, 
        unique=True, 
        editable=False,
        null=True,
        help_text="Format: PRNXXXXXX"
    )
    _display_id_prefix = 'PRN'
    _display_id_field = 'payroll_run_id'
    month = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    year = models.IntegerField(
        validators=[MinValueValidator(2020)]
    )
    status = models.CharField(
        max_length=20,
        choices=PayrollStatus.choices(),
        default=PayrollStatus.DRAFT.value
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='payroll_runs_processed'
    )
    total_gross_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    total_deductions = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    total_net_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    
    class Meta:
        db_table = 'payroll_runs'
        ordering = ['-year', '-month']
        unique_together = ['month', 'year']
    
    def __str__(self):
        return f"Payroll {self.month}/{self.year} - {self.get_status_display()}"
    
    def save(self, *args, **kwargs):
        """Auto-generate code from month/year if not provided"""
        is_new = self._state.adding
        if not self.code:
            
            month_name = get_month_name(self.month)
            self.code = slugify(f"pr-{month_name}-{self.year}")
            
            # Ensure uniqueness by appending version number if needed
            original_code = self.code
            counter = 1
            while PayrollRun.objects.filter(code=self.code).exclude(pk=self.pk).exists():
                self.code = f"{original_code}-v{counter}"
                counter += 1
            logger.debug(f"Auto-generated code for payroll run | Code: {self.code}")
        
        super().save(*args, **kwargs)
        if is_new:
            logger.info(f"New payroll run initialized | Code: {self.code} | Month: {self.month} | Year: {self.year}")


class Payslip(BaseModel):
    """Individual employee payslip"""
    
    # Business identifier (exposed in APIs)
    payslip_id = models.CharField(
        max_length=20, 
        unique=True, 
        editable=False,
        null=True,
        db_index=True,
        help_text="Format: PAYXXXXXX"
    )
    _display_id_prefix = 'PAY'
    _display_id_field = 'payslip_id'
    payroll_run = models.ForeignKey(
        PayrollRun,
        on_delete=models.CASCADE,
        related_name='payslips'
    )
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='payslips'
    )
    month = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    year = models.IntegerField(
        validators=[MinValueValidator(2020)]
    )
    gross_salary = models.DecimalField(max_digits=10, decimal_places=2)
    total_deductions = models.DecimalField(max_digits=10, decimal_places=2)
    net_salary = models.DecimalField(max_digits=10, decimal_places=2)
    leave_days_deducted = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )
    pdf_file = models.FileField(
        upload_to='payslips/%Y/%m/',
        null=True,
        blank=True
    )
    email_sent_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'payslips'
        ordering = ['-year', '-month']
        unique_together = ['employee', 'month', 'year']
    
    def __str__(self):
        return f"{self.employee.user.get_full_name()} - {self.month}/{self.year}"
    
    def generate_pdf(self):
        """
        Generate PDF payslip using hybrid approach (WeasyPrint + ReportLab)
        Saves the PDF to the pdf_file field
        """
        logger.info(f"Initiating PDF generation for payslip | ID: {self.payslip_id} | Employee: {self.employee.employee_id}")
        
        # Generate PDF bytes
        pdf_bytes = generate_payslip_pdf(self)
        
        # Save to file field
        filename = f"payslip_{self.employee.employee_id}_{self.year}_{self.month:02d}.pdf"
        self.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)
        
        return self.pdf_file



class PayslipComponent(BaseModel):
    """Breakdown of each payslip"""
    
    # ComponentType is imported from apps.payroll.constants
    
    # Business identifier (exposed in APIs)
    payslip_component_id = models.CharField(
        max_length=20, 
        unique=True, 
        editable=False,
        null=True,
        db_index=True,
        help_text="Format: PSCXXXXXX"
    )
    _display_id_prefix = 'PSC'
    _display_id_field = 'payslip_component_id'
    payslip = models.ForeignKey(
        Payslip,
        on_delete=models.CASCADE,
        related_name='components'
    )
    component_name = models.CharField(max_length=100)
    component_type = models.CharField(
        max_length=20,
        choices=ComponentType.choices()
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        db_table = 'payslip_components'
        ordering = ['component_type', 'component_name']
    
    def __str__(self):
        return f"{self.payslip} - {self.component_name}: {self.amount}"


class PayrollAutomationConfig(BaseModel):
    """Settings for automated payroll"""
    
    # Business identifier (exposed in APIs)
    payroll_automation_config_id = models.CharField(
        max_length=20, 
        unique=True, 
        editable=False,
        null=True,
        db_index=True,
        help_text="Format: PACXXXXXX"
    )
    _display_id_prefix = 'PAC'
    _display_id_field = 'payroll_automation_config_id'
    is_enabled = models.BooleanField(default=False)
    run_day = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(31)],
        default=1,
        help_text="Day of month to run automated payroll"
    )
    auto_email_payslips = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'payroll_automation_config'
        verbose_name = 'Payroll Automation Configuration'
        verbose_name_plural = 'Payroll Automation Configuration'
    
    def __str__(self):
        status = "Enabled" if self.is_enabled else "Disabled"
        return f"Payroll Automation: {status}"
