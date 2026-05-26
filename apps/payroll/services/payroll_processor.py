"""
Payroll Processing Service
Handles complete payroll calculation including working days and unpaid leave deductions
"""

import logging

from decimal import Decimal
from django.utils import timezone
from datetime import date, timedelta
from django.db import transaction, models
from apps.payroll.models import PayrollRun, PayrollStatus, Payslip, PayslipComponent, EmployeeSalaryStructure, ComponentType
from apps.organization.models import Employee
from apps.leaves.models import LeaveRequest, LeaveType, LeaveRequestStatus
from apps.base.utils import calculate_working_and_non_working_days

logger = logging.getLogger(__name__)


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
        logger.info(f"Initialized PayrollProcessor for Month: {self.month} | Year: {self.year} | System Working Days: {self.working_days}")
    
    @transaction.atomic
    def process(self):
        """
        Main processing method
        Returns: dict with processing results
        """
        # Update status to PROCESSING
        logger.info(f"Starting execution of payroll processing | Run ID: {self.payroll_run.payroll_run_id}")
        self.payroll_run.status = PayrollStatus.PROCESSING.value
        self.payroll_run.save()
        
        try:
            # Get all active employees with related data preloaded
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
                    logger.debug(f"Payslip already exists for employee {employee.employee_id}, skipping.")
                    continue
                
                # Calculate salary for this employee
                salary_data = self.calculate_employee_salary(employee)
                
                if salary_data:
                    # Create payslip
                    self._create_payslip(employee, salary_data)
                    payslips_created += 1
                    logger.debug(f"Generated payslip for {employee.employee_id}. Net: {salary_data['net_salary']}")
            
            # Aggregate totals for the PayrollRun
            totals = Payslip.objects.filter(
                payroll_run=self.payroll_run,
                is_deleted=False
            ).aggregate(
                gross=models.Sum('gross_salary'),
                deductions=models.Sum('total_deductions'),
                net=models.Sum('net_salary')
            )
            
            # Update status and totals
            self.payroll_run.status = PayrollStatus.COMPLETED.value
            self.payroll_run.total_gross_salary = totals['gross'] or 0
            self.payroll_run.total_deductions = totals['deductions'] or 0
            self.payroll_run.total_net_salary = totals['net'] or 0
            self.payroll_run.save()
            
            logger.info(
                f"Payroll processing COMPLETED for run {self.payroll_run.payroll_run_id}. "
                f"Total payslips: {payslips_created} | Total Net: {self.payroll_run.total_net_salary}"
            )
            
            return {
                'success': True,
                'count': payslips_created,
                'working_days': self.working_days
            }
            
        except Exception as e:
            # Update status to FAILED
            logger.error(f"Payroll processing FAILED | Run ID: {self.payroll_run.payroll_run_id} | Error: {str(e)}", exc_info=True)
            self.payroll_run.status = PayrollStatus.FAILED.value
            self.payroll_run.save()
            raise e
    
    def calculate_employee_salary(self, employee: Employee):
        """
        Calculate salary for one employee
        Returns: dict with salary breakdown or None if no salary structure
        """
        # Get active salary structures for this month
        # We look for structures that were active at any point during this month
        month_start = timezone.make_aware(timezone.datetime(self.year, self.month, 1))
        
        structures = EmployeeSalaryStructure.objects.filter(
            employee=employee,
            effective_from_at__lte=timezone.now(),
            is_deleted=False
        ).filter(
            models.Q(effective_to_at__isnull=True) | 
            models.Q(effective_to_at__gte=month_start)
        ).select_related('salary_component')
        
        if not structures.exists():
            logger.warning(f"Calculations skipped: No active salary structure found | Employee ID: {employee.employee_id} | Period: {self.month}/{self.year}")
            return None
        
        # Calculate earnings and deductions
        earnings = []
        deductions = []
        bonuses = []
        employer_contributions = []
        
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
            elif component.component_type == ComponentType.EMPLOYER_CONTRIBUTION.value:
                employer_contributions.append(component_data)
                # Employer contributions do NOT add to gross salary (CTC != Gross)
                # but they are part of the total cost to company.
        
        # Get unpaid leave deduction
        unpaid_leaves = self.get_unpaid_leaves(employee)
        leave_deduction = Decimal('0.00')
        leave_days_count = 0
        
        if unpaid_leaves and self.working_days > 0:
            for leave in unpaid_leaves:
                leave_days_count += leave.duration
            
            # Calculate per-day salary based on Gross
            per_day_salary = gross_salary / Decimal(str(self.working_days))
            leave_deduction = per_day_salary * Decimal(str(leave_days_count))
            total_deductions += leave_deduction
            logger.debug(f"Unpaid leave deduction computed | Employee ID: {employee.employee_id} | Days: {leave_days_count}")
        
        # Calculate net salary
        net_salary = gross_salary - total_deductions
        
        return {
            'gross_salary': gross_salary.quantize(Decimal('0.01')),
            'total_deductions': total_deductions.quantize(Decimal('0.01')),
            'net_salary': net_salary.quantize(Decimal('0.01')),
            'leave_days_deducted': leave_days_count,
            'leave_deduction': leave_deduction.quantize(Decimal('0.01')),
            'earnings': earnings,
            'deductions': deductions,
            'bonuses': bonuses,
            'employer_contributions': employer_contributions
        }
    
    def get_unpaid_leaves(self, employee: Employee):
        """Get validated unpaid leaves for the month"""
        return LeaveRequest.objects.filter(
            employee=employee,
            leave_type=LeaveType.UNPAID.value,
            status=LeaveRequestStatus.APPROVED.value,
            started_at__year=self.year,
            started_at__month=self.month
        )
    
    def _create_payslip(self, employee: Employee, salary_data: dict):
        """Create payslip and payslip components"""
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
        
        components_to_create = []
        
        # Add earnings
        for earning in salary_data['earnings']:
            components_to_create.append(
                PayslipComponent(
                    payslip=payslip,
                    component_name=earning['component'].name,
                    component_type=ComponentType.EARNING.value,
                    amount=earning['amount']
                )
            )
        
        # Add deductions
        for deduction in salary_data['deductions']:
            components_to_create.append(
                PayslipComponent(
                    payslip=payslip,
                    component_name=deduction['component'].name,
                    component_type=ComponentType.DEDUCTION.value,
                    amount=deduction['amount']
                )
            )
        
        # Add bonuses
        for bonus in salary_data['bonuses']:
            components_to_create.append(
                PayslipComponent(
                    payslip=payslip,
                    component_name=bonus['component'].name,
                    component_type=ComponentType.BONUS.value,
                    amount=bonus['amount']
                )
            )

        # Add employer contributions
        for contrib in salary_data['employer_contributions']:
            components_to_create.append(
                PayslipComponent(
                    payslip=payslip,
                    component_name=contrib['component'].name,
                    component_type=ComponentType.EMPLOYER_CONTRIBUTION.value,
                    amount=contrib['amount']
                )
            )
        
        # Add leave deduction as a component if applicable
        if salary_data['leave_deduction'] > 0:
            components_to_create.append(
                PayslipComponent(
                    payslip=payslip,
                    component_name='Unpaid Leave Deduction',
                    component_type=ComponentType.DEDUCTION.value,
                    amount=salary_data['leave_deduction']
                )
            )
        
        if components_to_create:
            PayslipComponent.objects.bulk_create(components_to_create)
        
        return payslip
