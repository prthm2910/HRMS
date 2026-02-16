"""
Constants for the audit app.
Contains all enums used in audit and AI operation models.
"""

from enum import Enum
from apps.base.constants import BaseEnum


class AuditAction(BaseEnum):
    """Audit log action choices"""
    CREATE = 'CREATE'
    UPDATE = 'UPDATE'
    DELETE = 'DELETE'
    HARD_DELETE = 'HARD_DELETE'
    AI_SERVICE = 'AI_SERVICE'
    CHAT = 'CHAT'

    _labels = {
        AI_SERVICE: "AI Service Call",
    }


class AIOperationType(BaseEnum):
    """AI operation type choices"""
    OCR = 'OCR'
    NLP = 'NLP'
    VISION = 'VISION'
    CLASSIFICATION = 'CLASSIFICATION'
    GENERATION = 'GENERATION'


class AIOperationLogStatus(BaseEnum):
    """AI operation status choices"""
    SUCCESS = 'SUCCESS'
    FAILED = 'FAILED'
    PENDING = 'PENDING'
