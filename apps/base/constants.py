from enum import Enum

class BaseEnum(Enum):
    """
    Base Enum class for all HRMS Enums.
    Provides a centralized choices() method for Django compatibility.

    Usage Example:
        class Status(BaseEnum):
            PENDING = 'PENDING'
            ACTIVE = 'ACTIVE'

        # Default Label: Title Case (e.g., 'Pending', 'Active')
        print(Status.choices()) 

    Custom Label Example:
        class Priority(BaseEnum):
            HIGH = 'HIGH'
            _labels = {HIGH: 'High Priority'}
    """
    @classmethod
    def choices(cls):
        """
        Generates Django-compatible choices [(value, label), ...].
        Uses _labels dict if defined, otherwise defaults to .title() name.
        """
        labels = getattr(cls, '_labels', {})
        return [
            (
                member.value, 
                labels.get(member, member.name.replace('_', ' ').title())
            ) 
            for member in cls
        ]
