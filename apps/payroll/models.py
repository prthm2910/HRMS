import uuid
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.base.models import BaseTemplateModel
from apps.organization.models import Employee


class SalaryComponent(BaseTemplateModel):
    """Define reusable salary components"""
    
    class ComponentType(models.TextChoices):
        EARNING = 'EARNING', 'Earning'
        DEDUCTION = 'DEDUCTION', 'Deduction'
        BONUS = 'BONUS', 'Bonus'
    
    class CalculationMethod(models.TextChoices):
        FIXED = 'FIXED', 'Fixed Amount'
        PERCENTAGE = 'PERCENTAGE', 'Percentage of Base'
    
    # Auto-generated slug from name (primary business identifier)
    code = models.SlugField(
        max_length=50,
        unique=True,
        db_index=True,
        blank=True,
        help_text="Auto-generated from name (e.g., basic-salary, hra, pf-deduction)"
    )
    
    # UUID fallback identifier
    salary_component_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True
    )
    name = models.CharField(max_length=100, unique=True)
    component_type = models.CharField(
        max_length=20,
        choices=ComponentType.choices
    )
    calculation_method = models.CharField(
        max_length=20,
        choices=CalculationMethod.choices,
        default=CalculationMethod.FIXED
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
        if not self.code:
            from django.utils.text import slugify
            self.code = slugify(self.name)
            
            # Ensure uniqueness by appending number if needed
            original_code = self.code
            counter = 1
            while SalaryComponent.objects.filter(code=self.code).exclude(pk=self.pk).exists():
                self.code = f"{original_code}-{counter}"
                counter += 1
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.name} ({self.get_component_type_display()})"


class EmployeeSalaryStructure(BaseTemplateModel):
    """Employee-specific salary breakdown"""
    
    # Business identifier (exposed in APIs)
    employee_salary_structure_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True
    )
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
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    
    class Meta:
        db_table = 'employee_salary_structures'
        ordering = ['-effective_from']
        unique_together = ['employee', 'salary_component', 'effective_from']
    
    def __str__(self):
        return f"{self.employee.user.get_full_name()} - {self.salary_component.name}"


class TaxRule(BaseTemplateModel):
    """Configurable tax slabs"""
    
    # Auto-generated slug from name (primary business identifier)
    code = models.SlugField(
        max_length=50,
        unique=True,
        db_index=True,
        blank=True,
        help_text="Auto-generated from name (e.g., india-tax-slab-1-0-3l)"
    )
    
    # UUID fallback identifier
    tax_rule_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True
    )
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
        if not self.code:
            from django.utils.text import slugify
            self.code = slugify(self.name)
            
            # Ensure uniqueness
            original_code = self.code
            counter = 1
            while TaxRule.objects.filter(code=self.code).exclude(pk=self.pk).exists():
                self.code = f"{original_code}-{counter}"
                counter += 1
        
        super().save(*args, **kwargs)


class PayrollStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    PROCESSING = 'PROCESSING', 'Processing'
    COMPLETED = 'COMPLETED', 'Completed'
    FAILED = 'FAILED', 'Failed'


class PayrollRun(BaseTemplateModel):
    
    # Auto-generated slug from month/year (primary business identifier)
    code = models.SlugField(
        max_length=50,
        unique=True,
        db_index=True,
        blank=True,
        help_text="Auto-generated from month/year (e.g., pr-february-2026)"
    )
    
    # UUID fallback identifier
    payroll_run_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True
    )
    month = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    year = models.IntegerField(
        validators=[MinValueValidator(2020)]
    )
    status = models.CharField(
        max_length=20,
        choices=PayrollStatus.choices,
        default=PayrollStatus.DRAFT
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
        if not self.code:
            from apps.base.utils import get_month_name
            from django.utils.text import slugify
            
            month_name = get_month_name(self.month)
            self.code = slugify(f"pr-{month_name}-{self.year}")
            
            # Ensure uniqueness by appending version number if needed
            original_code = self.code
            counter = 1
            while PayrollRun.objects.filter(code=self.code).exclude(pk=self.pk).exists():
                self.code = f"{original_code}-v{counter}"
                counter += 1
        
        super().save(*args, **kwargs)


class Payslip(BaseTemplateModel):
    """Individual employee payslip"""
    
    # Business identifier (exposed in APIs)
    payslip_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True
    )
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
        from django.core.files.base import ContentFile
        from apps.payroll.services.pdf_generator import generate_payslip_pdf
        
        # Generate PDF bytes
        pdf_bytes = generate_payslip_pdf(self)
        
        # Save to file field
        filename = f"payslip_{self.employee.employee_id}_{self.year}_{self.month:02d}.pdf"
        self.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)
        
        return self.pdf_file



class PayslipComponent(BaseTemplateModel):
    """Breakdown of each payslip"""
    
    class ComponentType(models.TextChoices):
        EARNING = 'EARNING', 'Earning'
        DEDUCTION = 'DEDUCTION', 'Deduction'
        BONUS = 'BONUS', 'Bonus'
    
    # Business identifier (exposed in APIs)
    payslip_component_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True
    )
    payslip = models.ForeignKey(
        Payslip,
        on_delete=models.CASCADE,
        related_name='components'
    )
    component_name = models.CharField(max_length=100)
    component_type = models.CharField(
        max_length=20,
        choices=ComponentType.choices
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        db_table = 'payslip_components'
        ordering = ['component_type', 'component_name']
    
    def __str__(self):
        return f"{self.payslip} - {self.component_name}: {self.amount}"


class PayrollAutomationConfig(BaseTemplateModel):
    """Settings for automated payroll"""
    
    # Business identifier (exposed in APIs)
    payroll_automation_config_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        db_index=True
    )
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
