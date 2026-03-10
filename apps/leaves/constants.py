"""
Constants for the leaves app.
Contains all enums used in leave models.
"""

from apps.base.constants import BaseEnum


class LeaveType(BaseEnum):
    """Types of leave available"""
    SICK = 'SICK'
    CASUAL = 'CASUAL'
    EARNED = 'EARNED'
    UNPAID = 'UNPAID'


class HalfDayPeriod(BaseEnum):
    """Half-day period choices"""
    FIRST_HALF = 'FIRST_HALF'
    SECOND_HALF = 'SECOND_HALF'

    _labels = {
        FIRST_HALF: 'First Half (Morning)',
        SECOND_HALF: 'Second Half (Afternoon)',
    }


class LeaveRequestStatus(BaseEnum):
    """Leave request status choices"""
    PENDING = 'PENDING'
    APPROVED = 'APPROVED'
    REJECTED = 'REJECTED'
    CANCELLED = 'CANCELLED'
