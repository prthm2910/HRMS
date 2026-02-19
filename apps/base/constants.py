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
        # Search through class hierarchy to find _labels
        # Note: _labels may be converted to an enum member, so we need to access .value
        labels = {}
        for klass in cls.__mro__:
            if '_labels' in klass.__dict__:
                """Why not just use hasattr(klass, '_labels')?
                This is because hasattr() checks if the class has the attribute anywhere in its inheritance chain. If a parent class has _labels but the child doesn't, hasattr will still return True,
                while __dict__ This checks only that specific class. It returns True only if _labels was explicitly written inside that class's definition.
                """
                labels_attr = klass.__dict__['_labels']
                # If _labels was converted to an enum member, get its value
                if isinstance(labels_attr, cls):
                    labels = labels_attr.value
                else:
                    labels = labels_attr
                break
        
        return [
            (
                member.value, 
                labels.get(member, labels.get(member.name, member.name.replace('_', ' ').title()))
            ) 
            for member in cls 
            if not member.name.startswith('_')
        ]
