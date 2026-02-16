"""
Payroll Processing Service
Handles complete payroll calculation including working days and unpaid leave deductions
"""

from decimal import Decimal
from django.utils import timezone
from datetime import date, timedelta
from django.db import transaction, models
from apps.payroll.models import PayrollRun, PayrollStatus, Payslip, PayslipComponent, EmployeeSalaryStructure, ComponentType
from apps.organization.models import Employee
from apps.leaves.models import LeaveRequest, LeaveType, LeaveRequestStatus
from apps.base.utils import calculate_working_and_non_working_days


class PayrollProcessor:
    """
    Main payroll processing service
    Calculates salaries, deductions, and generates payslips
    """
    
    def __init__(self, payroll_run: PayrollRun):
        self.payroll_run = payroll_run
        self.month = payroll_run.month
        self.year = payroll_run.year
        
        # Calculate working days for the month
        start_date = date(self.year, self.month, 1)
        # Get last day of month
        if self.month == 12:
            end_date = date(self.year, 12, 31)
        else:
            end_date = date(self.year, self.month + 1, 1) - timedelta(days=1)
        
        res = calculate_working_and_non_working_days(start_date, end_date)
        self.working_days = res['working_days']
    
    @transaction.atomic
    def process(self):
        """
        Main processing method
        Returns: dict with processing results
        """
        # Update status to PROCESSING
        self.payroll_run.status = PayrollStatus.PROCESSING.value
        self.payroll_run.save()
        
        try:
            # Get all active employees with related data preloaded
            # Optimization: select_related prevents N+1 queries when accessing employee.user or employee.department
            employees = Employee.objects.filter(
                is_active=True,
                is_deleted=False
            ).select_related('user', 'department')
            
            payslips_created = 0
            
            for employee in employees:
                # Check if payslip already exists (prevent duplicates)
                existing = Payslip.objects.filter(
                    employee=employee,
                    month=self.month,
                    year=self.year,
                    is_deleted=False
                ).exists()
                
                if existing:
                    continue  # Skip if already processed
                
                # Calculate salary for this employee
                salary_data = self.calculate_employee_salary(employee)
                
                if salary_data:
                    # Create payslip
                    self._create_payslip(employee, salary_data)
                    payslips_created += 1
            
            # Update status to COMPLETED
            self.payroll_run.status = PayrollStatus.COMPLETED.value
            self.payroll_run.total_employees = payslips_created
            self.payroll_run.save()
            
            return {
                'success': True,
                'count': payslips_created,
                'working_days': self.working_days
            }
            
        except Exception as e:
            # Update status to FAILED
            self.payroll_run.status = PayrollStatus.FAILED.value
            self.payroll_run.save()
            raise e
    
    def calculate_employee_salary(self, employee: Employee):
        """
        Calculate salary for one employee
        Returns: dict with salary breakdown or None if no salary structure
        """
        # Get active salary structures for this month
        structures = EmployeeSalaryStructure.objects.filter(
            employee=employee,
            effective_from_at__lte=timezone.now(),
            is_deleted=False
        ).filter(
            # Either no end date OR end date is after this month
            models.Q(effective_to__isnull=True) | 
            models.Q(effective_to__gte=date(self.year, self.month, 1))
        ).select_related('salary_component')
        
        if not structures.exists():
            return None  # No salary structure for this employee
        
        # Calculate earnings and deductions
        earnings = []
        deductions = []
        bonuses = []
        
        gross_salary = Decimal('0.00')
        total_deductions = Decimal('0.00')
        
        for structure in structures:
            component = structure.salary_component
            amount = structure.amount
            
            component_data = {
                'component': component,
                'amount': amount
            }
            
            if component.component_type == ComponentType.EARNING.value:
                earnings.append(component_data)
                gross_salary += amount
            elif component.component_type == ComponentType.DEDUCTION.value:
                deductions.append(component_data)
                total_deductions += amount
            elif component.component_type == ComponentType.BONUS.value:
                bonuses.append(component_data)
                gross_salary += amount
        
        # Get unpaid leave deduction
        unpaid_leaves = self.get_unpaid_leaves(employee)
        leave_deduction = Decimal('0.00')
        leave_days_count = 0
        
        if unpaid_leaves and self.working_days > 0:
            # Calculate total unpaid leave days
            for leave in unpaid_leaves:
                leave_days_count += leave.duration
            
            # Calculate per-day salary
            per_day_salary = gross_salary / Decimal(str(self.working_days))
            leave_deduction = per_day_salary * Decimal(str(leave_days_count))
            total_deductions += leave_deduction
        
        # Calculate net salary
        net_salary = gross_salary - total_deductions
        
        return {
            'gross_salary': gross_salary,
            'total_deductions': total_deductions,
            'net_salary': net_salary,
            'leave_days_deducted': leave_days_count,
            'leave_deduction': leave_deduction,
            'earnings': earnings,
            'deductions': deductions,
            'bonuses': bonuses
        }
    
    def get_unpaid_leaves(self, employee: Employee):
        """
        Get validated unpaid leaves for the month
        Only returns leaves that are:
        1. UNPAID type
        2. APPROVED status
        3. On working days (validated)
        """
        # Get unpaid approved leaves for this month
        leaves = LeaveRequest.objects.filter(
            employee=employee,
            leave_type=LeaveType.UNPAID.value,
            status=LeaveRequestStatus.APPROVED.value,
            started_at__year=self.year,
            started_at__month=self.month
        )
        
        # Filter to only working days
        # Note: The duration property already excludes weekends and holidays
        # So we can use it directly
        return leaves
    
    def _create_payslip(self, employee: Employee, salary_data: dict):
        """Create payslip and payslip components"""
        # Create payslip
        payslip = Payslip.objects.create(
            payroll_run=self.payroll_run,
            employee=employee,
            month=self.month,
            year=self.year,
            gross_salary=salary_data['gross_salary'],
            total_deductions=salary_data['total_deductions'],
            net_salary=salary_data['net_salary'],
            leave_days_deducted=salary_data['leave_days_deducted']
        )
        
        # Create payslip components using bulk_create for efficiency
        # Optimization: bulk_create reduces queries from 10N to 1 (where N = number of components)
        components_to_create = []
        
        # Add earnings
        for earning in salary_data['earnings']:
            components_to_create.append(
                PayslipComponent(
                    payslip=payslip,
                    component_name=earning['component'].name,
                    component_type='EARNING',
                    amount=earning['amount']
                )
            )
        
        # Add deductions
        for deduction in salary_data['deductions']:
            components_to_create.append(
                PayslipComponent(
                    payslip=payslip,
                    component_name=deduction['component'].name,
                    component_type='DEDUCTION',
                    amount=deduction['amount']
                )
            )
        
        # Add bonuses
        for bonus in salary_data['bonuses']:
            components_to_create.append(
                PayslipComponent(
                    payslip=payslip,
                    component_name=bonus['component'].name,
                    component_type='BONUS',
                    amount=bonus['amount']
                )
            )
        
        # Add leave deduction as a component if applicable
        if salary_data['leave_deduction'] > 0:
            components_to_create.append(
                PayslipComponent(
                    payslip=payslip,
                    component_name='Unpaid Leave Deduction',
                    component_type='DEDUCTION',
                    amount=salary_data['leave_deduction']
                )
            )
        
        # Bulk create all components in a single query
        if components_to_create:
            PayslipComponent.objects.bulk_create(components_to_create)
        
        return payslip
