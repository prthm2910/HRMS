"""
Constants for the payroll app.
Contains all enums used in payroll models.
"""

from enum import Enum
from apps.base.constants import BaseEnum


class ComponentType(BaseEnum):
    """Salary component types"""
    EARNING = 'EARNING'
    DEDUCTION = 'DEDUCTION'
    BONUS = 'BONUS'


class CalculationMethod(BaseEnum):
    """Methods for calculating salary components"""
    FIXED = 'FIXED'
    PERCENTAGE = 'PERCENTAGE'

    _labels = {
        FIXED: "Fixed Amount",
        PERCENTAGE: "Percentage of Basic",
    }


class PayrollStatus(BaseEnum):
    """Payroll run status"""
    DRAFT = 'DRAFT'
    PROCESSING = 'PROCESSING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'
