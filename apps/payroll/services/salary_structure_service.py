"""
Service for auto-calculating and syncing EmployeeSalaryStructure amounts.
Amounts are derived from SalaryComponent rules + Employee's annual CTC.
"""

import logging
from decimal import Decimal, ROUND_HALF_UP

from django.utils import timezone

logger = logging.getLogger(__name__)


class SalaryStructureService:
    """
    Calculation rules:
      FIXED                   → component.default_value (flat monthly amount)
      PERCENTAGE (basic)      → default_value/100 × (Employee.salary / 12)
      PERCENTAGE (non-basic)  → default_value/100 × monthly_basic_pay
    """

    @staticmethod
    def calculate_amount(employee, component) -> Decimal:
        """
        Compute the monthly amount for one employee + one component.
        Returns a Decimal rounded to 2 decimal places.
        """
        from apps.payroll.constants import CalculationMethod

        monthly_ctc = (employee.salary / Decimal('12')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )

        if component.calculation_method == CalculationMethod.FIXED.value:
            return component.default_value

        # PERCENTAGE
        if component.is_basic_salary:
            # Basic Salary = % of monthly CTC
            amount = (component.default_value / Decimal('100')) * monthly_ctc
        else:
            # Other PERCENTAGE components = % of monthly Basic Pay
            basic_pay = SalaryStructureService._get_monthly_basic(employee)
            amount = (component.default_value / Decimal('100')) * basic_pay

        return amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    @staticmethod
    def _get_monthly_basic(employee) -> Decimal:
        """Look up the basic salary component and compute its monthly value."""
        from apps.payroll.models import SalaryComponent
        from apps.payroll.constants import CalculationMethod

        basic_component = SalaryComponent.objects.filter(
            is_basic_salary=True,
            is_deleted=False
        ).first()

        if not basic_component:
            logger.error("No SalaryComponent with is_basic_salary=True found. Defaulting to 0.")
            return Decimal('0.00')

        monthly_ctc = (employee.salary / Decimal('12')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )

        if basic_component.calculation_method == CalculationMethod.PERCENTAGE.value:
            basic = (basic_component.default_value / Decimal('100')) * monthly_ctc
        else:
            basic = basic_component.default_value

        return basic.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    @staticmethod
    def sync_employee_structures(employee):
        """
        Create or update EmployeeSalaryStructure rows for ALL active
        SalaryComponents for the given employee.

        Called when:
          - A new employee is created
          - Employee.salary (CTC) changes
        """
        from apps.payroll.models import SalaryComponent, EmployeeSalaryStructure

        components = SalaryComponent.objects.filter(is_deleted=False)
        now = timezone.now()

        for component in components:
            amount = SalaryStructureService.calculate_amount(employee, component)

            # Find existing open structure for this employee + component
            existing = EmployeeSalaryStructure.objects.filter(
                employee=employee,
                salary_component=component,
                effective_to_at__isnull=True,
                is_deleted=False,
            ).first()

            if existing:
                if existing.amount != amount:
                    # Close old structure
                    existing.effective_to_at = now
                    existing.save(update_fields=['effective_to_at', 'updated_at'])

                    # Create new structure with updated amount
                    EmployeeSalaryStructure.objects.create(
                        employee=employee,
                        salary_component=component,
                        amount=amount,
                        effective_from_at=now,
                    )
                    logger.info(
                        f"Salary structure updated | Employee: {employee.employee_id} | "
                        f"Component: {component.code} | Old: {existing.amount} → New: {amount}"
                    )
                # else: amount unchanged, skip
            else:
                # No existing structure — create new
                EmployeeSalaryStructure.objects.create(
                    employee=employee,
                    salary_component=component,
                    amount=amount,
                    effective_from_at=now,
                )
                logger.info(
                    f"Salary structure created | Employee: {employee.employee_id} | "
                    f"Component: {component.code} | Amount: {amount}"
                )

    @staticmethod
    def sync_component_structures(component):
        """
        Recalculate EmployeeSalaryStructure amounts for ALL employees
        for the given component.

        Called when:
          - SalaryComponent.default_value changes
          - SalaryComponent.is_basic_salary changes
        """
        from apps.organization.models import Employee

        employees = Employee.objects.filter(is_deleted=False)

        for employee in employees:
            SalaryStructureService.sync_employee_structures(employee)

        logger.info(
            f"Bulk salary structure sync completed | Component: {component.code} | "
            f"Employees processed: {employees.count()}"
        )
