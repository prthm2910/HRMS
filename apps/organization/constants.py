"""
Constants for the organization app.
Contains all enums used in organization models.
"""

from apps.base.constants import BaseEnum


class EmploymentType(BaseEnum):
    """Employment type choices for employees"""
    FULL_TIME = 'FULL_TIME'
    PART_TIME = 'PART_TIME'
    CONTRACT = 'CONTRACT'
    INTERN = 'INTERN'
