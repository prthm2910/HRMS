"""
Service for managing EmployeeSalaryStructure.
Supports HR-led curation with strict CTC validation.
"""

import logging
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.utils import timezone

from apps.payroll.constants import CalculationMethod, ComponentType

logger = logging.getLogger(__name__)


class SalaryStructureService:
    """
    Handles retrieval of suggested salary structures and 
    validated updates of curated employee structures.
    """

    @staticmethod
    def calculate_suggested_amount(employee, component) -> Decimal:
        """
        Compute the suggested monthly amount based on Master Library rules.
        """
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
            # Note: For suggestion, we calculate basic pay on the fly
            basic_pay = SalaryStructureService._get_suggested_monthly_basic(employee)
            amount = (component.default_value / Decimal('100')) * basic_pay

        return amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    @staticmethod
    def _get_suggested_monthly_basic(employee) -> Decimal:
        """Look up the master basic salary component and compute its monthly value."""
        from apps.payroll.models import SalaryComponent

        basic_component = SalaryComponent.objects.filter(
            is_basic_salary=True,
            is_deleted=False
        ).first()

        if not basic_component:
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
    def get_suggested_structure(employee):
        """
        Returns a list of suggested components for an employee.
        Used by the UI to pre-fill the curation form.
        """
        from apps.payroll.models import SalaryComponent
        
        components = SalaryComponent.objects.filter(is_deleted=False)
        suggestions = []
        
        for comp in components:
            suggestions.append({
                'component_id': comp.salary_component_id,
                'code': comp.code,
                'name': comp.name,
                'type': comp.component_type,
                'suggested_amount': SalaryStructureService.calculate_suggested_amount(employee, comp)
            })
            
        return suggestions

    @staticmethod
    @transaction.atomic
    def update_employee_structure(employee, components_data):
        """
        Validates and saves a curated salary structure for an employee.
        'components_data': list of {'salary_component': ID, 'amount': Decimal}
        """
        from apps.payroll.models import SalaryComponent, EmployeeSalaryStructure

        now = timezone.now()
        monthly_ctc = (employee.salary / Decimal('12')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )

        # 1. Load components and calculate totals
        total_for_ctc = Decimal('0.00')
        processed_structures = []

        for item in components_data:
            comp_id = item.get('salary_component')
            amount = Decimal(str(item.get('amount', 0)))
            
            try:
                component = SalaryComponent.objects.get(pk=comp_id, is_deleted=False)
            except SalaryComponent.DoesNotExist:
                raise ValueError(f"Salary Component with ID {comp_id} does not exist.")

            # Rule: Earnings + Employer Contributions count towards CTC
            if component.component_type in [ComponentType.EARNING.value, ComponentType.EMPLOYER_CONTRIBUTION.value]:
                total_for_ctc += amount

            processed_structures.append({
                'component': component,
                'amount': amount
            })

        # 2. Validate CTC match
        # We allow a small tolerance (1 INR) for rounding differences
        diff = abs(total_for_ctc - monthly_ctc)
        if diff > Decimal('1.00'):
            raise ValueError(
                f"Validation Failed: Total monthly components ({total_for_ctc}) "
                f"must match monthly CTC ({monthly_ctc}). Difference: {diff}"
            )

        # 3. Close old records
        EmployeeSalaryStructure.objects.filter(
            employee=employee,
            effective_to_at__isnull=True,
            is_deleted=False
        ).update(effective_to_at=now, updated_at=now)

        # 4. Create new records
        new_records = []
        for item in processed_structures:
            new_records.append(EmployeeSalaryStructure(
                employee=employee,
                salary_component=item['component'],
                amount=item['amount'],
                effective_from_at=now
            ))
        
        EmployeeSalaryStructure.objects.bulk_create(new_records)
        
        logger.info(f"Salary structure curated for employee {employee.employee_id} | Total monthly: {total_for_ctc}")
        return True
