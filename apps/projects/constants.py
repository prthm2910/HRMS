"""
Constants for the projects app.
Contains all enums used in project models.
"""

from apps.base.constants import BaseEnum


class ProjectType(BaseEnum):
    """Types of Projects"""
    PERMANENT = 'PERMANENT'
    PROJECT = 'PROJECT'
    CLIENT = 'CLIENT'

    _labels = {
        PROJECT: "Project Based",
    }


class Position(BaseEnum):
    """Positions/Roles in a project"""
    LEADER = 'LEADER'
    CO_LEADER = 'CO_LEADER'
    MEMBER = 'MEMBER'

    _labels = {
        LEADER: "Project Leader",
        CO_LEADER: "Co-Leader",
    }
